#!/usr/bin/env python
"""Knowledge Vault relevance and latency evaluator.

Runs a threshold-based pass/fail eval against a named dataset, measuring
cosine similarity between query embeddings and document embeddings. Exits
non-zero if relevance drops below --min-relevance or latency exceeds
--max-latency-ms on any query.

Usage
-----
    # Governed contract check (run from repo root):
    python tests/rag/run_knowledge_vault_eval.py \\
        --dataset tests/eval_datasets/knowledge_vault_eval.json \\
        --min-relevance 0.8 \\
        --max-latency-ms 2000

    # Debug with verbose output:
    python tests/rag/run_knowledge_vault_eval.py \\
        --dataset tests/eval_datasets/knowledge_vault_eval.json \\
        --min-relevance 0.8 \\
        --max-latency-ms 2000 \\
        --verbose

Design notes
------------
- Uses cosine similarity between generated embeddings (no live Supabase required).
- Embeddings are generated via app.rag.embedding_service.generate_embedding, which
  falls back to zero vectors when no Google API credentials are available. In that
  case all similarities will be 0.0 and the eval fails loudly rather than silently
  passing — intentional, so CI reveals credential gaps rather than hiding them.
- Latency measures the real embedding + similarity computation path, not a mock.
- Output is machine-readable JSON on stdout; human summary on stderr.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Cosine similarity helper
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors.

    Returns 0.0 for zero vectors to avoid division-by-zero.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------

def evaluate_dataset(
    dataset_path: Path,
    min_relevance: float,
    max_latency_ms: float,
    verbose: bool = False,
) -> dict:
    """Run the full relevance and latency evaluation.

    Args:
        dataset_path: Path to the JSON eval dataset.
        min_relevance: Minimum cosine similarity required for a result to be
            considered relevant (0.0–1.0).
        max_latency_ms: Maximum allowed latency per query in milliseconds.
        verbose: Print per-query detail to stderr.

    Returns:
        Result dict with keys: passed, relevance_pass, latency_pass, queries,
        summary. Suitable for JSON serialisation.
    """
    # Import embedding service from the real app path
    # Add repo root to sys.path so the import works when called from any cwd
    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from app.rag.embedding_service import generate_embedding  # noqa: PLC0415

    data = json.loads(dataset_path.read_text())
    documents = data["documents"]
    queries = data["queries"]

    if verbose:
        print(
            f"[eval] dataset={dataset_path.name} docs={len(documents)} "
            f"queries={len(queries)} min_relevance={min_relevance} "
            f"max_latency_ms={max_latency_ms}",
            file=sys.stderr,
        )

    # Pre-compute document embeddings (excluded from per-query latency)
    doc_embeddings: dict[str, list[float]] = {}
    for doc in documents:
        doc_embeddings[doc["id"]] = generate_embedding(doc["content"])

    query_results = []
    relevance_failures: list[str] = []
    latency_failures: list[str] = []

    for q in queries:
        qid = q["id"]
        query_text = q["query"]
        relevant_ids = set(q.get("relevant_doc_ids", []))

        # Measure query embedding + similarity computation time
        t_start = time.perf_counter()
        query_emb = generate_embedding(query_text)

        # Compute similarity against all documents
        sims = {
            doc_id: cosine_similarity(query_emb, doc_emb)
            for doc_id, doc_emb in doc_embeddings.items()
        }

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        # Relevance: the max similarity across the known-relevant documents
        relevant_sims = [sims[did] for did in relevant_ids if did in sims]
        best_relevance = max(relevant_sims) if relevant_sims else 0.0

        relevance_ok = best_relevance >= min_relevance
        latency_ok = elapsed_ms <= max_latency_ms

        result = {
            "query_id": qid,
            "query": query_text,
            "best_relevance": round(best_relevance, 4),
            "latency_ms": round(elapsed_ms, 2),
            "relevance_pass": relevance_ok,
            "latency_pass": latency_ok,
        }
        query_results.append(result)

        if not relevance_ok:
            relevance_failures.append(qid)
        if not latency_ok:
            latency_failures.append(qid)

        if verbose:
            status = "PASS" if (relevance_ok and latency_ok) else "FAIL"
            print(
                f"  [{status}] {qid} relevance={best_relevance:.4f} "
                f"latency={elapsed_ms:.1f}ms",
                file=sys.stderr,
            )

    passed = not relevance_failures and not latency_failures
    avg_relevance = (
        sum(r["best_relevance"] for r in query_results) / len(query_results)
        if query_results
        else 0.0
    )
    avg_latency = (
        sum(r["latency_ms"] for r in query_results) / len(query_results)
        if query_results
        else 0.0
    )

    return {
        "passed": passed,
        "relevance_pass": len(relevance_failures) == 0,
        "latency_pass": len(latency_failures) == 0,
        "relevance_failures": relevance_failures,
        "latency_failures": latency_failures,
        "summary": {
            "total_queries": len(queries),
            "relevance_failures": len(relevance_failures),
            "latency_failures": len(latency_failures),
            "avg_relevance": round(avg_relevance, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "min_relevance_threshold": min_relevance,
            "max_latency_ms_threshold": max_latency_ms,
        },
        "queries": query_results,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Knowledge Vault relevance and latency evaluator. "
            "Exits non-zero if relevance < --min-relevance or "
            "latency > --max-latency-ms on any query."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the eval dataset JSON file.",
    )
    parser.add_argument(
        "--min-relevance",
        type=float,
        default=0.8,
        help="Minimum cosine similarity required to pass relevance check (0.0–1.0).",
    )
    parser.add_argument(
        "--max-latency-ms",
        type=float,
        default=2000.0,
        help="Maximum allowed query latency in milliseconds.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print per-query detail to stderr.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path to write machine-readable JSON results.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0 = pass, 1 = fail)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    results = evaluate_dataset(
        dataset_path=dataset_path,
        min_relevance=args.min_relevance,
        max_latency_ms=args.max_latency_ms,
        verbose=args.verbose,
    )

    # Machine-readable output on stdout
    print(json.dumps(results, indent=2))

    # Human summary on stderr
    s = results["summary"]
    status_str = "PASSED" if results["passed"] else "FAILED"
    print(
        f"\n[eval] {status_str} — "
        f"avg_relevance={s['avg_relevance']} "
        f"(threshold={s['min_relevance_threshold']}) | "
        f"avg_latency={s['avg_latency_ms']}ms "
        f"(threshold={s['max_latency_ms_threshold']}ms) | "
        f"relevance_failures={s['relevance_failures']} "
        f"latency_failures={s['latency_failures']}",
        file=sys.stderr,
    )

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2))

    return 0 if results["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
