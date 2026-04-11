"""Tests for the Knowledge Vault eval runner contract.

Validates the runner script's CLI interface and result structure
before the implementation file exists.

Run the full eval with:
    uv run python tests/rag/run_knowledge_vault_eval.py \
        --dataset tests/eval_datasets/knowledge_vault_eval.json \
        --min-relevance 0.8 \
        --max-latency-ms 2000
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "tests" / "eval_datasets" / "knowledge_vault_eval.json"
RUNNER_PATH = REPO_ROOT / "tests" / "rag" / "run_knowledge_vault_eval.py"


class TestEvalDatasetStructure:
    """The named eval dataset must have the required structure."""

    def test_dataset_file_exists(self):
        """The eval dataset JSON file must exist."""
        assert DATASET_PATH.exists(), f"Dataset not found: {DATASET_PATH}"

    def test_dataset_has_required_keys(self):
        """Dataset must contain description, documents, queries, and thresholds."""
        data = json.loads(DATASET_PATH.read_text())
        assert "documents" in data, "Dataset must have 'documents'"
        assert "queries" in data, "Dataset must have 'queries'"
        assert "thresholds" in data, "Dataset must have 'thresholds'"

    def test_dataset_has_minimum_queries(self):
        """Dataset must have at least 5 queries for statistical validity."""
        data = json.loads(DATASET_PATH.read_text())
        assert len(data["queries"]) >= 5, "Dataset must have at least 5 queries"

    def test_dataset_has_minimum_documents(self):
        """Dataset must have at least 3 documents."""
        data = json.loads(DATASET_PATH.read_text())
        assert len(data["documents"]) >= 3, "Dataset must have at least 3 documents"

    def test_each_query_has_relevant_docs(self):
        """Every query must reference at least one relevant document."""
        data = json.loads(DATASET_PATH.read_text())
        doc_ids = {d["id"] for d in data["documents"]}
        for q in data["queries"]:
            assert "relevant_doc_ids" in q, f"Query {q['id']} missing relevant_doc_ids"
            assert len(q["relevant_doc_ids"]) >= 1, f"Query {q['id']} has no relevant docs"
            for ref_id in q["relevant_doc_ids"]:
                assert ref_id in doc_ids, (
                    f"Query {q['id']} references unknown doc_id '{ref_id}'"
                )

    def test_thresholds_match_contract(self):
        """Dataset thresholds must match the governed contract values."""
        data = json.loads(DATASET_PATH.read_text())
        thresholds = data["thresholds"]
        assert thresholds.get("min_relevance") == 0.8, (
            "min_relevance must be 0.8"
        )
        assert thresholds.get("max_latency_ms") == 2000, (
            "max_latency_ms must be 2000"
        )

    def test_document_ids_are_unique(self):
        """Document IDs must be unique within the dataset."""
        data = json.loads(DATASET_PATH.read_text())
        ids = [d["id"] for d in data["documents"]]
        assert len(ids) == len(set(ids)), "Duplicate document IDs found"

    def test_query_ids_are_unique(self):
        """Query IDs must be unique within the dataset."""
        data = json.loads(DATASET_PATH.read_text())
        ids = [q["id"] for q in data["queries"]]
        assert len(ids) == len(set(ids)), "Duplicate query IDs found"


class TestEvalRunnerExists:
    """The runner script must exist and be importable."""

    def test_runner_file_exists(self):
        """The eval runner script must exist at the specified path."""
        assert RUNNER_PATH.exists(), f"Runner not found: {RUNNER_PATH}"

    def test_runner_has_main_guard(self):
        """Runner must have a __main__ guard for direct execution."""
        source = RUNNER_PATH.read_text()
        assert '__main__' in source, "Runner must have if __name__ == '__main__' guard"

    def test_runner_accepts_dataset_flag(self):
        """Runner must accept --dataset flag (check --help works)."""
        result = subprocess.run(
            [sys.executable, str(RUNNER_PATH), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"--help failed: {result.stderr}"
        assert "--dataset" in result.stdout, "--dataset flag must be documented in --help"

    def test_runner_accepts_min_relevance_flag(self):
        """Runner must accept --min-relevance flag."""
        result = subprocess.run(
            [sys.executable, str(RUNNER_PATH), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert "--min-relevance" in result.stdout, "--min-relevance must be in --help"

    def test_runner_accepts_max_latency_flag(self):
        """Runner must accept --max-latency-ms flag."""
        result = subprocess.run(
            [sys.executable, str(RUNNER_PATH), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert "--max-latency-ms" in result.stdout, "--max-latency-ms must be in --help"
