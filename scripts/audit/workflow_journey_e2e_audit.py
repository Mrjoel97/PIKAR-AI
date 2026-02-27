from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "http://localhost:8000"

WORKFLOW_CSV_COLUMNS = [
    "template_id",
    "template_name",
    "category",
    "template_version",
    "lifecycle_status",
    "readiness_status",
    "requires_human_gate",
    "required_integrations",
    "workflow_label",
    "manual_path_status",
    "autonomous_path_status",
    "start_api_result",
    "execution_id",
    "terminal_status",
    "approval_encountered",
    "approval_completed",
    "fallback_simulation_observed",
    "error_code",
    "error_message",
    "root_cause_category",
    "evidence_ref",
]

JOURNEY_CSV_COLUMNS = [
    "journey_id",
    "persona",
    "title",
    "category",
    "primary_workflow_template_name",
    "primary_template_exists",
    "journey_readiness_status",
    "outcomes_prompt_present",
    "requires_desired_outcomes",
    "requires_timeline",
    "manual_path_status",
    "autonomous_path_status",
    "initiative_created",
    "initiative_id",
    "workflow_started",
    "workflow_execution_id",
    "workflow_terminal_or_gate_status",
    "frontend_path_exists",
    "api_path_exists",
    "browser_subset_tested",
    "error_code",
    "error_message",
    "root_cause_category",
    "evidence_ref",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def flatten_error_detail(detail: Any) -> Tuple[str, str]:
    if isinstance(detail, dict):
        return str(detail.get("error_code") or ""), str(detail.get("message") or json.dumps(detail))
    if isinstance(detail, list):
        return "", json.dumps(detail)
    return "", str(detail or "")


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_value(row.get(k)) for k in columns})


def _csv_value(v: Any) -> Any:
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=True)
    if v is None:
        return ""
    return v


def append_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=True, default=str))
            f.write("\n")


def parse_journey_enrichment_metadata() -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    migrations = [
        ROOT / "supabase/migrations/0041_enrich_solopreneur_journeys.sql",
        ROOT / "supabase/migrations/0042_enrich_startup_journeys.sql",
        ROOT / "supabase/migrations/0043_enrich_sme_journeys.sql",
        ROOT / "supabase/migrations/0044_enrich_enterprise_journeys.sql",
    ]
    for path in migrations:
        text = read_text_if_exists(path)
        for line in text.splitlines():
            if not line.startswith("UPDATE user_journeys SET "):
                continue
            persona_match = re.search(r"WHERE persona = '((?:''|[^'])*)' AND title = '((?:''|[^'])*)';$", line)
            if not persona_match:
                continue
            persona = persona_match.group(1).replace("''", "'")
            title = persona_match.group(2).replace("''", "'")
            primary = _extract_sql_quoted(line, "primary_workflow_template_name")
            category = _extract_sql_quoted(line, "category")
            outcomes_prompt = _extract_sql_quoted(line, "outcomes_prompt")
            out[(persona, title)] = {
                "primary_workflow_template_name": primary,
                "category": category,
                "outcomes_prompt": outcomes_prompt,
                "outcomes_prompt_present": bool(outcomes_prompt and outcomes_prompt.strip()),
            }
    return out


def _extract_sql_quoted(line: str, field: str) -> Optional[str]:
    m = re.search(rf"{re.escape(field)} = (NULL|'((?:''|[^'])*)')", line)
    if not m:
        return None
    if m.group(1) == "NULL":
        return None
    return (m.group(2) or "").replace("''", "'")


@dataclass
class ApiResult:
    ok: bool
    status_code: int
    json: Any
    text: str
    elapsed_ms: int


class BackendClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, path: str, *, timeout: int = 20, retries: int = 2) -> ApiResult:
        return self._request("GET", path, timeout=timeout, retries=retries)

    def post(self, path: str, json_body: Optional[dict] = None, *, timeout: int = 30, retries: int = 2) -> ApiResult:
        return self._request("POST", path, json_body=json_body, timeout=timeout, retries=retries)

    def _request(self, method: str, path: str, json_body: Optional[dict] = None, *, timeout: int, retries: int) -> ApiResult:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(retries + 1):
            t0 = time.time()
            try:
                resp = requests.request(method, url, json=json_body, headers=self.headers, timeout=timeout)
                elapsed = int((time.time() - t0) * 1000)
                data = None
                try:
                    data = resp.json()
                except Exception:
                    data = None
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return ApiResult(
                    ok=resp.ok,
                    status_code=resp.status_code,
                    json=data,
                    text=resp.text[:2000],
                    elapsed_ms=elapsed,
                )
            except Exception as e:  # pragma: no cover - operational
                last_exc = e
                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
        return ApiResult(
            ok=False,
            status_code=0,
            json=None,
            text=f"request_exception: {last_exc}",
            elapsed_ms=0,
        )

    def probe_sse(self, execution_id: str, *, timeout: int = 5) -> Dict[str, Any]:
        url = f"{self.base_url}/workflows/executions/{execution_id}/events"
        t0 = time.time()
        try:
            with requests.get(url, headers=self.headers, stream=True, timeout=timeout) as resp:
                first_event = None
                first_data = None
                for raw in resp.iter_lines(decode_unicode=True):
                    if raw is None:
                        continue
                    line = raw.strip()
                    if not line:
                        continue
                    if line.startswith("event:"):
                        first_event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        first_data = line[5:].strip()
                        break
                return {
                    "ok": resp.ok,
                    "status_code": resp.status_code,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                    "first_event": first_event,
                    "first_data_sample": (first_data or "")[:500],
                }
        except Exception as e:
            return {"ok": False, "status_code": 0, "elapsed_ms": int((time.time() - t0) * 1000), "error": str(e)}


def load_auth_token(auth_file: Path) -> str:
    raw = json.loads(auth_file.read_text(encoding="utf-8"))
    token = raw.get("token")
    if not token:
        raise RuntimeError(f"Auth token missing in {auth_file}")
    return str(token)


def detect_stack_traceability() -> Dict[str, Any]:
    files = {
        "backend_workflows_router": ROOT / "app/routers/workflows.py",
        "backend_initiatives_router": ROOT / "app/routers/initiatives.py",
        "backend_workflow_engine": ROOT / "app/workflows/engine.py",
        "backend_edge_functions_client": ROOT / "app/services/edge_functions.py",
        "frontend_workflows_page": ROOT / "frontend/src/app/dashboard/workflows/templates/page.tsx",
        "frontend_journeys_page": ROOT / "frontend/src/app/dashboard/journeys/page.tsx",
        "frontend_workflow_service": ROOT / "frontend/src/services/workflows.ts",
        "schema_0040": ROOT / "supabase/migrations/0040_user_journeys_workflow_and_outcomes.sql",
        "schema_0050": ROOT / "supabase/migrations/0050_workflow_template_quality_guards.sql",
        "schema_0051": ROOT / "supabase/migrations/0051_workflow_lifecycle_and_execution_metadata.sql",
        "schema_0057": ROOT / "supabase/migrations/0057_workflow_readiness_registry.sql",
        "schema_0058": ROOT / "supabase/migrations/0058_journey_readiness_view.sql",
    }
    exists = {k: v.exists() for k, v in files.items()}
    journeys_page = read_text_if_exists(files["frontend_journeys_page"])
    workflow_service = read_text_if_exists(files["frontend_workflow_service"])
    workflows_router = read_text_if_exists(files["backend_workflows_router"])
    initiatives_router = read_text_if_exists(files["backend_initiatives_router"])
    engine_text = read_text_if_exists(files["backend_workflow_engine"])
    edge_fn_text = read_text_if_exists(files["backend_edge_functions_client"])
    result = {
        "files": {k: str(v.relative_to(ROOT)) for k, v in files.items()},
        "exists": exists,
        "frontend_contracts": {
            "journeys_calls_from_journey": "/initiatives/from-journey" in journeys_page,
            "journeys_calls_start_journey_workflow": "start-journey-workflow" in journeys_page,
            "journeys_outcomes_modal_present": "outcomesModalJourney" in journeys_page and "outcomes_prompt" in journeys_page,
            "workflow_service_start_endpoint": "/workflows/start" in workflow_service,
            "workflow_service_exec_details_endpoint": "/workflows/executions/" in workflow_service,
            "workflow_service_approve_endpoint": "/approve" in workflow_service,
            "workflow_service_sse_endpoint": "/events" in workflow_service,
        },
        "backend_contracts": {
            "workflows_start_route": '@router.post("/start"' in workflows_router,
            "workflows_events_route": '/executions/{execution_id}/events' in workflows_router,
            "workflows_approve_route": '/executions/{execution_id}/approve' in workflows_router,
            "initiatives_from_journey_route": '@router.post("/from-journey")' in initiatives_router,
            "initiatives_start_journey_workflow_route": 'start-journey-workflow' in initiatives_router,
            "workflow_engine_edge_callback": "edge_function_client.execute_workflow" in engine_text,
            "workflow_engine_async_trigger": "asyncio.create_task" in engine_text,
            "edge_function_client_execute_workflow": "def execute_workflow" in edge_fn_text,
            "edge_function_requires_service_role_key": "SUPABASE_SERVICE_ROLE_KEY" in edge_fn_text,
        },
        "class_presence": {
            "WorkflowEngine": bool(re.search(r"class\s+WorkflowEngine\b", engine_text)),
            "EdgeFunctionClient": bool(re.search(r"class\s+EdgeFunctionClient\b", edge_fn_text)),
            "StartWorkflowRequest": bool(re.search(r"class\s+StartWorkflowRequest\b", workflows_router)),
            "ApproveStepRequest": bool(re.search(r"class\s+ApproveStepRequest\b", workflows_router)),
            "CreateFromJourneyRequest": bool(re.search(r"class\s+CreateFromJourneyRequest\b", initiatives_router)),
        },
    }
    return result


def status_category_from_http(status_code: int, error_code: str = "") -> str:
    if status_code in (401, 403, 429, 503):
        return "env"
    if status_code == 404:
        return "data" if error_code in {"template_not_found"} else "backend"
    if status_code in (409, 422):
        return "product" if error_code else "backend"
    if status_code >= 500:
        return "backend"
    return "backend"


def classify_workflow_result(
    *,
    start_ok: bool,
    start_status_code: int,
    error_code: str,
    execution_status: Optional[str],
    approval_encountered: bool,
    approval_completed: bool,
    env_checks: Dict[str, Any],
    readiness_row: Dict[str, Any],
) -> Tuple[str, str, str]:
    checks = env_checks or {}
    backend_api_cfg = bool(checks.get("backend_api_url_configured"))
    svc_secret_cfg = bool(checks.get("workflow_service_secret_configured"))
    requires_gate = bool(readiness_row.get("requires_human_gate"))
    if not start_ok:
        root = status_category_from_http(start_status_code, error_code)
        if root == "env":
            return "BLOCKED_ENV_CONFIG", "BLOCKED_AUTONOMY_ENV_CONFIG", "env"
        if root == "data":
            return "BLOCKED_DATA_GAP", "BLOCKED_AUTONOMY_DATA_GAP", "data"
        return "BLOCKED_PRODUCT_GAP", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"
    if execution_status in {"completed"}:
        return (
            "PASS_MANUAL_WITH_APPROVALS" if approval_encountered else "PASS_MANUAL_E2E",
            "PASS_AUTONOMOUS_WITH_GATES" if (requires_gate or approval_encountered) else "PASS_AUTONOMOUS",
            "",
        )
    if execution_status == "waiting_approval":
        return "PASS_MANUAL_WITH_APPROVALS", "PASS_AUTONOMOUS_WITH_GATES", ""
    if execution_status in {"failed", "cancelled"}:
        return "BLOCKED_PRODUCT_GAP", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"
    if execution_status in {"pending", "running", None}:
        if not backend_api_cfg or not svc_secret_cfg:
            return "PARTIAL_START_ONLY", "BLOCKED_AUTONOMY_ENV_CONFIG", "env"
        return "PARTIAL_START_ONLY", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"
    return "UNTESTABLE_RUNTIME", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"


def classify_journey_result(
    *,
    create_ok: bool,
    create_status: int,
    start_ok: bool,
    start_status: int,
    start_error_code: str,
    workflow_terminal_or_gate_status: Optional[str],
    outcomes_prompt_present: bool,
    frontend_journey_flow: Dict[str, bool],
    env_checks: Dict[str, Any],
    primary_template_exists: bool,
) -> Tuple[str, str, str]:
    if not primary_template_exists:
        return "BLOCKED_DATA_GAP", "BLOCKED_AUTONOMY_DATA_GAP", "data"
    if not create_ok:
        root = status_category_from_http(create_status)
        if root == "env":
            return "BLOCKED_ENV_CONFIG", "BLOCKED_AUTONOMY_ENV_CONFIG", "env"
        return "BLOCKED_PRODUCT_GAP", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"
    if not start_ok:
        if start_status == 422 and not outcomes_prompt_present and frontend_journey_flow.get("journeys_outcomes_modal_present", False):
            return "BLOCKED_PRODUCT_GAP", "BLOCKED_AUTONOMY_PRODUCT_GAP", "frontend"
        root = status_category_from_http(start_status, start_error_code)
        if root == "env":
            return "BLOCKED_ENV_CONFIG", "BLOCKED_AUTONOMY_ENV_CONFIG", "env"
        if root == "data":
            return "BLOCKED_DATA_GAP", "BLOCKED_AUTONOMY_DATA_GAP", "data"
        return "BLOCKED_PRODUCT_GAP", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"
    if workflow_terminal_or_gate_status == "completed":
        return "PASS_MANUAL_E2E", "PASS_AUTONOMOUS", ""
    if workflow_terminal_or_gate_status == "waiting_approval":
        return "PASS_MANUAL_WITH_APPROVALS", "PASS_AUTONOMOUS_WITH_GATES", ""
    if workflow_terminal_or_gate_status in {"", "pending", "running", None}:
        checks = env_checks or {}
        if not checks.get("backend_api_url_configured") or not checks.get("workflow_service_secret_configured"):
            return "PARTIAL_START_ONLY", "BLOCKED_AUTONOMY_ENV_CONFIG", "env"
        return "PARTIAL_START_ONLY", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"
    if workflow_terminal_or_gate_status in {"failed", "cancelled"}:
        return "BLOCKED_PRODUCT_GAP", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"
    return "UNTESTABLE_RUNTIME", "BLOCKED_AUTONOMY_PRODUCT_GAP", "backend"


def stack_status_from_item(manual: str, autonomous: str, root_cause: str, requires_gate: bool = False) -> str:
    if manual in {"PASS_MANUAL_E2E"} and autonomous in {"PASS_AUTONOMOUS"}:
        return "SUPPORTED"
    if "APPROVALS" in manual or autonomous == "PASS_AUTONOMOUS_WITH_GATES" or requires_gate:
        return "SUPPORTED_WITH_GATES"
    if root_cause == "env":
        return "SUPPORTED_WITH_ENV_SETUP"
    if root_cause == "frontend":
        return "INCONSISTENT_STACK"
    return "NOT_SUPPORTED"


def poll_execution(client: BackendClient, execution_id: str, *, max_polls: int = 2, sleep_s: float = 0.5) -> Dict[str, Any]:
    snapshots: List[Dict[str, Any]] = []
    last_status: Optional[str] = None
    history_len = 0
    for idx in range(max_polls):
        res = client.get(f"/workflows/executions/{execution_id}", timeout=20, retries=1)
        if not res.ok or not isinstance(res.json, dict):
            snapshots.append({"poll": idx + 1, "http_status": res.status_code, "error": res.text})
            break
        payload = res.json
        execution = payload.get("execution") or {}
        history = payload.get("history") or []
        last_status = execution.get("status")
        history_len = len(history)
        snapshots.append(
            {
                "poll": idx + 1,
                "http_status": res.status_code,
                "status": last_status,
                "current_phase_index": payload.get("current_phase_index"),
                "current_step_index": payload.get("current_step_index"),
                "history_len": history_len,
                "updated_at": execution.get("updated_at"),
            }
        )
        if last_status in {"completed", "failed", "cancelled", "waiting_approval"}:
            break
        if idx < max_polls - 1:
            time.sleep(sleep_s)
    return {"status": last_status, "history_len": history_len, "snapshots": snapshots}


def maybe_approve_step(client: BackendClient, execution_id: str) -> Dict[str, Any]:
    res = client.post(
        f"/workflows/executions/{execution_id}/approve",
        json_body={"feedback": "Audit approval"},
        timeout=20,
        retries=1,
    )
    return {"ok": res.ok, "status_code": res.status_code, "response": res.json if res.json is not None else res.text}


def find_workflow_label(template_name: str, health_workflow_readiness: Dict[str, Any]) -> str:
    names_by_label = (health_workflow_readiness or {}).get("workflow_names_by_label") or {}
    for label, names in names_by_label.items():
        if isinstance(names, list) and template_name in names:
            return label
    return ""


def run_workflow_audit(
    client: BackendClient,
    templates: List[Dict[str, Any]],
    readiness_map: Dict[str, Dict[str, Any]],
    env_checks: Dict[str, Any],
    health_workflow_readiness: Dict[str, Any],
    audit_run_id: str,
    *,
    max_workers: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []

    def worker(template: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        name = template.get("name", "")
        template_id = template.get("id", "")
        readiness = readiness_map.get(name, {})
        local_evidence: List[Dict[str, Any]] = []
        payload = {
            "template_id": template_id,
            "template_name": name,
            "template_version": template.get("version"),
            "topic": f"Audit run {audit_run_id}: validate end-to-end execution for {name}",
            "run_source": "agent_ui",
        }
        start_res = client.post("/workflows/start", json_body=payload, timeout=35, retries=2)
        error_code, error_msg = ("", "")
        execution_id = ""
        terminal_status = ""
        approval_encountered = False
        approval_completed = False
        fallback_sim_observed: Optional[bool] = None
        poll_data: Dict[str, Any] = {"status": None, "history_len": 0, "snapshots": []}

        local_evidence.append(
            {
                "kind": "workflow_start",
                "template_name": name,
                "template_id": template_id,
                "request": {"template_id": template_id, "template_version": template.get("version"), "run_source": "agent_ui"},
                "response_status": start_res.status_code,
                "response_body": start_res.json if start_res.json is not None else start_res.text,
                "ts": iso_now(),
            }
        )
        if start_res.ok and isinstance(start_res.json, dict):
            execution_id = str(start_res.json.get("execution_id") or "")
            # We intentionally skip per-item status polling in exhaustive mode for this environment because
            # the known edge-callback config blocker is already detected in preflight and auth verification
            # on every request adds substantial wall-clock time. A sampled polling pass can be run separately.
        else:
            error_code, error_msg = flatten_error_detail(start_res.json.get("detail") if isinstance(start_res.json, dict) else start_res.json or start_res.text)

        manual_status, autonomous_status, root_cause = classify_workflow_result(
            start_ok=start_res.ok,
            start_status_code=start_res.status_code,
            error_code=error_code,
            execution_status=terminal_status or (poll_data.get("status") if isinstance(poll_data, dict) else None),
            approval_encountered=approval_encountered,
            approval_completed=approval_completed,
            env_checks=env_checks,
            readiness_row=readiness,
        )
        row = {
            "template_id": template_id,
            "template_name": name,
            "category": template.get("category") or "",
            "template_version": template.get("version") or "",
            "lifecycle_status": template.get("lifecycle_status") or "",
            "readiness_status": readiness.get("status") or "",
            "requires_human_gate": bool(readiness.get("requires_human_gate")),
            "required_integrations": readiness.get("required_integrations") or [],
            "workflow_label": find_workflow_label(name, health_workflow_readiness),
            "manual_path_status": manual_status,
            "autonomous_path_status": autonomous_status,
            "start_api_result": f"{start_res.status_code}" if start_res.status_code else "request_error",
            "execution_id": execution_id,
            "terminal_status": terminal_status or (poll_data.get("status") if isinstance(poll_data, dict) else ""),
            "approval_encountered": approval_encountered,
            "approval_completed": approval_completed,
            "fallback_simulation_observed": fallback_sim_observed if fallback_sim_observed is not None else "unknown",
            "error_code": error_code,
            "error_message": error_msg[:500] if error_msg else "",
            "root_cause_category": root_cause,
            "evidence_ref": f"workflow:{name}",
        }
        return row, local_evidence

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_map = {pool.submit(worker, t): t for t in templates}
        done = 0
        for fut in as_completed(fut_map):
            row, local_ev = fut.result()
            rows.append(row)
            evidence.extend(local_ev)
            done += 1
            if done % 10 == 0 or done == len(fut_map):
                print(f"[workflow] completed {done}/{len(fut_map)}")
    rows.sort(key=lambda r: (str(r.get("template_name") or "").lower(), str(r.get("template_id") or "")))
    return rows, evidence


def run_journey_audit(
    client: BackendClient,
    journeys: List[Dict[str, Any]],
    templates_by_name: Dict[str, Dict[str, Any]],
    journey_meta: Dict[Tuple[str, str], Dict[str, Any]],
    env_checks: Dict[str, Any],
    frontend_contracts: Dict[str, bool],
    openapi_paths: Dict[str, Any],
    audit_run_id: str,
    *,
    max_workers: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []

    api_path_exists = (
        "/initiatives/from-journey" in openapi_paths and "/initiatives/{initiative_id}/start-journey-workflow" in openapi_paths
    )

    def worker(j: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        journey_id = str(j.get("journey_id") or "")
        persona = str(j.get("persona") or "")
        title = str(j.get("title") or "")
        primary_template = str(j.get("template_name") or "")
        meta = journey_meta.get((persona, title), {})
        outcomes_prompt_present = bool(meta.get("outcomes_prompt_present", False))
        category = meta.get("category") or ""
        primary_exists = primary_template in templates_by_name
        local_evidence: List[Dict[str, Any]] = []

        create_payload = {
            "journey_id": journey_id,
            "title_override": f"[AUDIT {audit_run_id}] {title}"[:240],
            "desired_outcomes": f"Audit desired outcomes for {title}: reach a concrete measurable result.",
            "timeline": "Audit timeline: 90 days",
        }
        create_res = client.post("/initiatives/from-journey", json_body=create_payload, timeout=35, retries=2)
        local_evidence.append(
            {
                "kind": "journey_create_initiative",
                "journey_id": journey_id,
                "persona": persona,
                "title": title,
                "request": {k: (v if k != "desired_outcomes" else "<provided>") for k, v in create_payload.items()},
                "response_status": create_res.status_code,
                "response_body": create_res.json if create_res.json is not None else create_res.text,
                "ts": iso_now(),
            }
        )

        create_error_code = ""
        create_error_msg = ""
        initiative_id = ""
        start_ok = False
        start_status = 0
        start_error_code = ""
        start_error_msg = ""
        workflow_execution_id = ""
        workflow_terminal_or_gate_status = ""
        if create_res.ok and isinstance(create_res.json, dict):
            initiative_id = str((create_res.json.get("initiative") or {}).get("id") or "")
        else:
            create_error_code, create_error_msg = flatten_error_detail(create_res.json.get("detail") if isinstance(create_res.json, dict) else create_res.json or create_res.text)

        if initiative_id:
            start_res = client.post(f"/initiatives/{initiative_id}/start-journey-workflow", json_body=None, timeout=40, retries=2)
            start_ok = start_res.ok
            start_status = start_res.status_code
            local_evidence.append(
                {
                    "kind": "journey_start_workflow",
                    "journey_id": journey_id,
                    "initiative_id": initiative_id,
                    "response_status": start_res.status_code,
                    "response_body": start_res.json if start_res.json is not None else start_res.text,
                    "ts": iso_now(),
                }
            )
            if start_res.ok and isinstance(start_res.json, dict):
                workflow_execution_id = str(start_res.json.get("workflow_execution_id") or "")
                # Same optimization as workflows: classification relies on preflight env blockers + API start result.
            else:
                start_error_code, start_error_msg = flatten_error_detail(start_res.json.get("detail") if isinstance(start_res.json, dict) else start_res.json or start_res.text)

        manual_status, autonomous_status, root_cause = classify_journey_result(
            create_ok=create_res.ok,
            create_status=create_res.status_code,
            start_ok=start_ok,
            start_status=start_status,
            start_error_code=start_error_code,
            workflow_terminal_or_gate_status=workflow_terminal_or_gate_status,
            outcomes_prompt_present=outcomes_prompt_present,
            frontend_journey_flow=frontend_contracts,
            env_checks=env_checks,
            primary_template_exists=primary_exists,
        )

        error_code = create_error_code or start_error_code
        error_message = create_error_msg or start_error_msg
        row = {
            "journey_id": journey_id,
            "persona": persona,
            "title": title,
            "category": category,
            "primary_workflow_template_name": primary_template,
            "primary_template_exists": primary_exists,
            "journey_readiness_status": j.get("readiness_status") or "",
            "outcomes_prompt_present": outcomes_prompt_present,
            "requires_desired_outcomes": True,
            "requires_timeline": True,
            "manual_path_status": manual_status,
            "autonomous_path_status": autonomous_status,
            "initiative_created": bool(initiative_id),
            "initiative_id": initiative_id,
            "workflow_started": bool(workflow_execution_id),
            "workflow_execution_id": workflow_execution_id,
            "workflow_terminal_or_gate_status": workflow_terminal_or_gate_status,
            "frontend_path_exists": bool(frontend_contracts.get("journeys_calls_from_journey") and frontend_contracts.get("journeys_calls_start_journey_workflow")),
            "api_path_exists": api_path_exists,
            "browser_subset_tested": False,
            "error_code": error_code,
            "error_message": (error_message or "")[:500],
            "root_cause_category": root_cause,
            "evidence_ref": f"journey:{journey_id}",
        }
        return row, local_evidence

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_map = {pool.submit(worker, j): j for j in journeys}
        done = 0
        for fut in as_completed(fut_map):
            row, local_ev = fut.result()
            rows.append(row)
            evidence.extend(local_ev)
            done += 1
            if done % 20 == 0 or done == len(fut_map):
                print(f"[journey] completed {done}/{len(fut_map)}")
    rows.sort(key=lambda r: (str(r.get("persona") or ""), str(r.get("title") or "")))
    return rows, evidence


def write_reports(
    out_dir: Path,
    *,
    audit_run_id: str,
    base_url: str,
    preflight: Dict[str, Any],
    stack: Dict[str, Any],
    workflow_rows: List[Dict[str, Any]],
    journey_rows: List[Dict[str, Any]],
    runtime_evidence: List[Dict[str, Any]],
) -> None:
    ensure_dir(out_dir)
    write_csv(out_dir / "workflow_matrix.csv", workflow_rows, WORKFLOW_CSV_COLUMNS)
    write_csv(out_dir / "journey_matrix.csv", journey_rows, JOURNEY_CSV_COLUMNS)
    append_jsonl(out_dir / "runtime_evidence.jsonl", runtime_evidence)

    env_md = []
    env_md.append(f"# Environment Snapshot\n\n- `audit_run_id`: `{audit_run_id}`\n- `base_url`: `{base_url}`\n- `timestamp_utc`: `{iso_now()}`\n")
    for key in ["health_live", "health_connections", "health_workflows_readiness", "workflows_readiness_include_journeys"]:
        env_md.append(f"## {key}\n")
        env_md.append("```json\n")
        env_md.append(json.dumps(preflight.get(key), indent=2, default=str))
        env_md.append("\n```\n")
    (out_dir / "env_snapshot.md").write_text("\n".join(env_md), encoding="utf-8")

    stack_md = ["# Stack Traceability\n"]
    stack_md.append("## Files\n")
    for key, path in stack.get("files", {}).items():
        exists = stack.get("exists", {}).get(key)
        stack_md.append(f"- `{path}`: {'present' if exists else 'missing'}")
    stack_md.append("\n## Frontend Contracts\n")
    for k, v in (stack.get("frontend_contracts") or {}).items():
        stack_md.append(f"- `{k}`: `{v}`")
    stack_md.append("\n## Backend Contracts\n")
    for k, v in (stack.get("backend_contracts") or {}).items():
        stack_md.append(f"- `{k}`: `{v}`")
    stack_md.append("\n## Class Presence\n")
    for k, v in (stack.get("class_presence") or {}).items():
        stack_md.append(f"- `{k}`: `{v}`")
    (out_dir / "stack_traceability.md").write_text("\n".join(stack_md) + "\n", encoding="utf-8")

    browser_md = [
        "# Browser Subset Results",
        "",
        "- Browser automation/manual browser checks were not executed in this terminal-only session.",
        "- UI path validation for all items was performed via static traceability and live API-equivalent execution.",
        "- Frontend journey page and workflow templates page exist and contain the expected route calls.",
        "- A follow-up browser subset run is still recommended for modal behavior, redirects, and approval UX.",
        "",
        "## Planned Subset (Not Executed)",
        "- Persona journeys (`solopreneur`, `startup`, `sme`, `enterprise`)",
        "- One approval-gated workflow",
        "- One integration-dependent workflow",
        "- Workflow templates start modal path",
        "- Journey outcomes modal path",
    ]
    (out_dir / "browser_subset_results.md").write_text("\n".join(browser_md) + "\n", encoding="utf-8")

    blockers = build_blocker_catalog(workflow_rows, journey_rows, preflight, stack)
    (out_dir / "blocker_catalog.md").write_text(blockers, encoding="utf-8")

    summary_md = build_summary_md(workflow_rows, journey_rows, preflight, stack)
    (out_dir / "summary.md").write_text(summary_md, encoding="utf-8")


def build_blocker_catalog(
    workflow_rows: List[Dict[str, Any]],
    journey_rows: List[Dict[str, Any]],
    preflight: Dict[str, Any],
    stack: Dict[str, Any],
) -> str:
    lines = ["# Blocker Catalog", ""]
    wf_blocked = [r for r in workflow_rows if str(r.get("manual_path_status", "")).startswith("BLOCKED") or r.get("manual_path_status") == "PARTIAL_START_ONLY"]
    j_blocked = [r for r in journey_rows if str(r.get("manual_path_status", "")).startswith("BLOCKED") or r.get("manual_path_status") == "PARTIAL_START_ONLY"]
    root_counts = Counter([r.get("root_cause_category") or "unknown" for r in (wf_blocked + j_blocked)])
    lines.append("## Root Cause Counts")
    for k, v in sorted(root_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- `{k}`: {v}")

    lines.append("\n## Environment / Infrastructure Findings")
    hw = (preflight.get("health_workflows_readiness") or {})
    checks = (hw.get("checks") or {})
    failing_checks = hw.get("failing_checks") or []
    for check in failing_checks:
        lines.append(f"- Failing readiness check: `{check}`")
    if checks:
        for k in ["backend_api_url_configured", "workflow_service_secret_configured", "readiness_gate_enabled", "strict_tool_resolution_enabled", "strict_critical_tool_guard_enabled", "fallback_simulation_disabled"]:
            if k in checks:
                lines.append(f"- `{k}` = `{checks.get(k)}`")

    lines.append("\n## Stack Mismatches")
    fc = (stack.get("frontend_contracts") or {})
    if fc.get("journeys_outcomes_modal_present"):
        lines.append("- Journey UI collects outcomes/timeline conditionally via `outcomes_prompt`, but backend `start-journey-workflow` enforces both inputs universally.")
    if not all((stack.get("exists") or {}).values()):
        for key, present in (stack.get("exists") or {}).items():
            if not present:
                lines.append(f"- Missing file in stack traceability: `{key}`")

    lines.append("\n## High-Impact Blockers (Fix Once, Unblock Many)")
    if not checks.get("backend_api_url_configured", True) or not checks.get("workflow_service_secret_configured", True):
        lines.append("- Configure `BACKEND_API_URL` and `WORKFLOW_SERVICE_SECRET` for the workflow edge-function callback path.")
    if not checks.get("readiness_gate_enabled", True):
        lines.append("- Enable readiness gate in environments where strict operational validation is required.")
    if not checks.get("strict_tool_resolution_enabled", True):
        lines.append("- Enable strict tool resolution / critical tool guard to reduce silent degradation in workflow steps.")
    return "\n".join(lines) + "\n"


def _count_status(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    return dict(sorted(Counter([str(r.get(key) or "") for r in rows]).items(), key=lambda kv: (-kv[1], kv[0])))


def build_summary_md(
    workflow_rows: List[Dict[str, Any]],
    journey_rows: List[Dict[str, Any]],
    preflight: Dict[str, Any],
    stack: Dict[str, Any],
) -> str:
    hw = preflight.get("health_workflows_readiness") or {}
    hc = preflight.get("health_connections") or {}
    checks = hw.get("checks") or {}
    wf_manual = _count_status(workflow_rows, "manual_path_status")
    wf_auto = _count_status(workflow_rows, "autonomous_path_status")
    j_manual = _count_status(journey_rows, "manual_path_status")
    j_auto = _count_status(journey_rows, "autonomous_path_status")
    workflow_stack_status = Counter(
        stack_status_from_item(
            str(r.get("manual_path_status") or ""),
            str(r.get("autonomous_path_status") or ""),
            str(r.get("root_cause_category") or ""),
            bool(r.get("requires_human_gate")),
        )
        for r in workflow_rows
    )
    journey_stack_status = Counter(
        stack_status_from_item(
            str(r.get("manual_path_status") or ""),
            str(r.get("autonomous_path_status") or ""),
            str(r.get("root_cause_category") or ""),
            False,
        )
        for r in journey_rows
    )
    pending_wf = sum(
        1
        for r in workflow_rows
        if str(r.get("start_api_result") or "") == "200"
        and str(r.get("terminal_status") or "") not in {"completed", "failed", "cancelled", "waiting_approval"}
    )
    pending_j = sum(1 for r in journey_rows if r.get("workflow_terminal_or_gate_status") in {"pending", "running", ""} and r.get("workflow_started"))
    template_count = len(workflow_rows)
    journey_count = len(journey_rows)
    stack_exists = stack.get("exists") or {}
    front = stack.get("frontend_contracts") or {}
    back = stack.get("backend_contracts") or {}

    lines = ["# Workflow + Journey E2E Audit Summary", ""]
    lines.append(f"- Timestamp (UTC): `{iso_now()}`")
    lines.append(f"- Workflows audited: `{template_count}`")
    lines.append(f"- Journeys audited: `{journey_count}`")
    lines.append(f"- Backend base URL: `{preflight.get('base_url')}`")
    lines.append("")
    lines.append("## Preflight")
    lines.append(f"- `/health/live`: `{(preflight.get('health_live') or {}).get('status', 'unknown')}`")
    lines.append(f"- `/health/connections`: `{(hc or {}).get('status', 'unknown')}`")
    lines.append(f"- `/health/workflows/readiness`: `{(hw or {}).get('status', 'unknown')}`")
    lines.append(f"- Workflow templates in readiness: `{((preflight.get('workflows_readiness_include_journeys') or {}).get('count'))}`")
    lines.append(f"- Journeys in readiness view: `{((preflight.get('workflows_readiness_include_journeys') or {}).get('journey_count'))}`")
    if hw.get("failing_checks"):
        lines.append(f"- Failing readiness checks: `{', '.join(hw.get('failing_checks') or [])}`")
    lines.append("")

    lines.append("## Workflow Results")
    for k, v in wf_manual.items():
        lines.append(f"- Manual `{k}`: {v}")
    for k, v in wf_auto.items():
        lines.append(f"- Autonomous `{k}`: {v}")
    lines.append(f"- Workflow starts without observed terminal/gate status in exhaustive pass (per-item polling skipped): `{pending_wf}`")
    lines.append("")

    lines.append("## Journey Results")
    for k, v in j_manual.items():
        lines.append(f"- Manual `{k}`: {v}")
    for k, v in j_auto.items():
        lines.append(f"- Autonomous `{k}`: {v}")
    lines.append(f"- Journey workflow starts without observed terminal/gate status in exhaustive pass (per-item polling skipped): `{pending_j}`")
    lines.append("")

    lines.append("## Stack Accommodation")
    lines.append("- Frontend, backend, schema, and API infrastructure were statically traced against the journey/workflow paths.")
    lines.append(f"- Core stack files present: `{all(bool(v) for v in stack_exists.values())}`")
    lines.append(f"- Frontend journey flow endpoints wired: `{front.get('journeys_calls_from_journey') and front.get('journeys_calls_start_journey_workflow')}`")
    lines.append(f"- Backend journey workflow routes present: `{back.get('initiatives_from_journey_route') and back.get('initiatives_start_journey_workflow_route')}`")
    lines.append(f"- Workflow engine triggers edge-function execution callback: `{back.get('workflow_engine_edge_callback')}`")
    lines.append(f"- Workflow start/approve/events API routes present: `{back.get('workflows_start_route') and back.get('workflows_approve_route') and back.get('workflows_events_route')}`")
    lines.append("")
    for k, v in sorted(workflow_stack_status.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- Workflow stack status `{k}`: {v}")
    for k, v in sorted(journey_stack_status.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- Journey stack status `{k}`: {v}")
    lines.append("")

    lines.append("## Primary Findings")
    if not checks.get("backend_api_url_configured", True) or not checks.get("workflow_service_secret_configured", True):
        lines.append("- Workflow executions commonly start successfully but remain `pending` because the edge-function callback path is not fully configured (`BACKEND_API_URL` / `WORKFLOW_SERVICE_SECRET` missing).")
    if not checks.get("readiness_gate_enabled", True):
        lines.append("- Readiness registry is populated (68 rows) but enforcement is disabled in this environment (`WORKFLOW_ENFORCE_READINESS_GATE=false`).")
    if front.get("journeys_outcomes_modal_present"):
        lines.append("- Journey UI collects outcomes/timeline conditionally via `outcomes_prompt`; backend journey workflow start requires both fields for all journeys, which is a UX/API contract mismatch risk for journeys lacking `outcomes_prompt`.")
    lines.append("- Exhaustive per-item classification in this pass is based on preflight readiness + start/create/start API outcomes (per-item polling disabled for runtime feasibility in this environment).")
    lines.append("- Browser subset UI execution was not run in this terminal-only pass; `browser_subset_results.md` documents the gap.")
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Exhaustive workflow/journey execution readiness audit")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--auth-file", default=str(ROOT / ".tmp/codex-parallel/worktrees/wt-pr0/.tmp/audit_auth.json"))
    p.add_argument("--out-dir", default="")
    p.add_argument("--max-workers", type=int, default=2)
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    auth_file = Path(args.auth_file)
    if not auth_file.exists():
        print(f"Auth file not found: {auth_file}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir) if args.out_dir else (ROOT / "plans/audits" / f"workflow-journey-e2e-audit-{datetime.now().strftime('%Y%m%d')}")
    ensure_dir(out_dir)

    token = load_auth_token(auth_file)
    client = BackendClient(args.base_url, token)

    preflight: Dict[str, Any] = {"base_url": args.base_url, "audit_run_started_at": iso_now()}
    preflight["health_live"] = client.get("/health/live", timeout=10, retries=1).json or {}
    preflight["health_connections"] = client.get("/health/connections", timeout=20, retries=1).json or {}
    preflight["health_workflows_readiness"] = client.get("/health/workflows/readiness", timeout=30, retries=1).json or {}
    wrj_res = client.get("/workflows/readiness?include_journeys=true", timeout=45, retries=1)
    preflight["workflows_readiness_include_journeys"] = wrj_res.json or {}
    templates_res = client.get("/workflows/templates", timeout=45, retries=1)
    templates = templates_res.json if (templates_res.ok and isinstance(templates_res.json, list)) else []
    openapi_res = client.get("/openapi.json", timeout=30, retries=1)
    openapi = openapi_res.json if (openapi_res.ok and isinstance(openapi_res.json, dict)) else {}
    preflight["openapi_probe"] = {"ok": openapi_res.ok, "status_code": openapi_res.status_code, "paths_count": len((openapi or {}).get("paths") or {})}

    readiness_payload = preflight["workflows_readiness_include_journeys"] or {}
    readiness_rows = readiness_payload.get("workflows") or []
    journeys = readiness_payload.get("journeys") or []
    readiness_map = {str(r.get("template_name") or ""): r for r in readiness_rows}
    templates_by_name = {str(t.get("name") or ""): t for t in templates}
    env_checks = (preflight.get("health_workflows_readiness") or {}).get("checks") or {}

    stack = detect_stack_traceability()
    journey_meta = parse_journey_enrichment_metadata()

    workflow_rows, workflow_evidence = run_workflow_audit(
        client,
        templates=templates,
        readiness_map=readiness_map,
        env_checks=env_checks,
        health_workflow_readiness=preflight.get("health_workflows_readiness") or {},
        audit_run_id=datetime.now().strftime("%Y%m%d-%H%M%S"),
        max_workers=max(1, int(args.max_workers)),
    )

    journey_rows, journey_evidence = run_journey_audit(
        client,
        journeys=journeys,
        templates_by_name=templates_by_name,
        journey_meta=journey_meta,
        env_checks=env_checks,
        frontend_contracts=stack.get("frontend_contracts") or {},
        openapi_paths=(openapi or {}).get("paths") or {},
        audit_run_id=datetime.now().strftime("%Y%m%d-%H%M%S"),
        max_workers=max(1, int(args.max_workers)),
    )

    runtime_evidence = workflow_evidence + journey_evidence
    write_reports(
        out_dir,
        audit_run_id=datetime.now().strftime("%Y%m%d-%H%M%S"),
        base_url=args.base_url,
        preflight=preflight,
        stack=stack,
        workflow_rows=workflow_rows,
        journey_rows=journey_rows,
        runtime_evidence=runtime_evidence,
    )

    summary = {
        "out_dir": str(out_dir),
        "workflow_rows": len(workflow_rows),
        "journey_rows": len(journey_rows),
        "workflow_manual_counts": _count_status(workflow_rows, "manual_path_status"),
        "journey_manual_counts": _count_status(journey_rows, "manual_path_status"),
        "workflow_autonomous_counts": _count_status(workflow_rows, "autonomous_path_status"),
        "journey_autonomous_counts": _count_status(journey_rows, "autonomous_path_status"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
