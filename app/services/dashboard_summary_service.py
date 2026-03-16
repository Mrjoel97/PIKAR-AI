"""Dashboard summary service for persona-aware home screens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.personas.policy_registry import get_persona_policy, normalize_persona
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async


_ACTIVE_WORKFLOW_STATUSES = ["pending", "running", "waiting_approval"]
_ACTIVE_INITIATIVE_STATUSES = ["in_progress", "blocked", "not_started"]
_OPEN_TASK_STATUSES = ["pending", "running"]
_BRAIN_DUMP_CATEGORIES = [
    "Brain Dump",
    "Brain Dump Transcript",
    "Validation Plan",
    "Brain Dump Analysis",
    "Research",
]


class DashboardSummaryService:
    def __init__(self):
        self.client = get_service_client()

    def _effective_persona(self, persona: str | None) -> str:
        return normalize_persona(persona) or "startup"

    def _format_currency(self, amount: float | None, currency: str = "USD") -> str:
        if amount is None:
            return "No data"
        symbol = "$" if currency.upper() == "USD" else f"{currency.upper()} "
        return f"{symbol}{amount:,.0f}"

    def _format_months(self, months: float | None) -> str:
        if months is None:
            return "TBD"
        return f"{months:.1f} mo"

    async def _safe_rows(self, query: Any) -> list[dict[str, Any]]:
        try:
            response = await execute_async(query, op_name="dashboard_summary.query")
            return response.data or []
        except Exception:
            return []

    async def _pending_approvals(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("approval_requests")
            .select("id, action_type, created_at, payload")
            .eq("status", "PENDING")
            .order("created_at", desc=True)
            .limit(10)
        )
        scoped: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("payload") or {}
            if not isinstance(payload, dict):
                continue
            if payload.get("requester_user_id") != user_id and payload.get("user_id") != user_id:
                continue
            scoped.append(
                {
                    "id": row.get("id"),
                    "title": row.get("action_type") or "Approval required",
                    "created_at": row.get("created_at"),
                    "token": payload.get("public_token"),
                }
            )
        return scoped

    async def _active_workflows(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("workflow_executions")
            .select("id, name, status, updated_at, context")
            .eq("user_id", user_id)
            .in_("status", _ACTIVE_WORKFLOW_STATUSES)
            .order("updated_at", desc=True)
            .limit(6)
        )
        return [
            {
                "id": row.get("id"),
                "title": (row.get("context") or {}).get("topic") or row.get("name") or "Workflow",
                "status": row.get("status") or "pending",
                "updated_at": row.get("updated_at"),
            }
            for row in rows
        ]

    async def _recent_completed_workflows(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("workflow_executions")
            .select("id, name, completed_at, outcome_summary")
            .eq("user_id", user_id)
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(5)
        )
        return [
            {
                "id": row.get("id"),
                "title": row.get("name") or "Completed workflow",
                "completed_at": row.get("completed_at"),
                "summary": (row.get("outcome_summary") or {}).get("summary"),
            }
            for row in rows
        ]

    async def _initiatives(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("initiatives")
            .select("id, title, status, phase, progress, updated_at, workflow_execution_id")
            .eq("user_id", user_id)
            .in_("status", _ACTIVE_INITIATIVE_STATUSES)
            .order("updated_at", desc=True)
            .limit(6)
        )
        return [
            {
                "id": row.get("id"),
                "title": row.get("title") or "Initiative",
                "status": row.get("status") or "in_progress",
                "phase": row.get("phase") or "ideation",
                "progress": row.get("progress") or 0,
                "updated_at": row.get("updated_at"),
                "workflow_execution_id": row.get("workflow_execution_id"),
            }
            for row in rows
        ]

    async def _open_tasks(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("ai_jobs")
            .select("id, status, input_data, created_at")
            .eq("user_id", user_id)
            .eq("job_type", "task")
            .in_("status", _OPEN_TASK_STATUSES)
            .order("created_at", desc=True)
            .limit(6)
        )
        return [
            {
                "id": row.get("id"),
                "title": ((row.get("input_data") or {}).get("description") or "Task").strip(),
                "status": row.get("status") or "pending",
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    async def _brain_dumps(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("vault_documents")
            .select("id, filename, category, created_at")
            .eq("user_id", user_id)
            .in_("category", _BRAIN_DUMP_CATEGORIES)
            .order("created_at", desc=True)
            .limit(4)
        )
        return [
            {
                "id": row.get("id"),
                "title": row.get("filename") or row.get("category") or "Brain dump",
                "category": row.get("category") or "Brain Dump",
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    async def _content_queue(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("vault_documents")
            .select("id, title, category, document_type, created_at")
            .eq("user_id", user_id)
            .eq("document_type", "generated_content")
            .order("created_at", desc=True)
            .limit(4)
        )
        return [
            {
                "id": row.get("id"),
                "title": row.get("title") or row.get("category") or "Content asset",
                "category": row.get("category") or "Content",
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    async def _reports(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("user_reports")
            .select("id, title, category, created_at, summary")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(4)
        )
        return [
            {
                "id": row.get("id"),
                "title": row.get("title") or "Report",
                "category": row.get("category") or "Report",
                "created_at": row.get("created_at"),
                "summary": row.get("summary") or "",
            }
            for row in rows
        ]

    async def _departments(self) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("departments")
            .select("id, name, type, status, state, last_heartbeat")
            .order("name")
            .limit(6)
        )
        departments: list[dict[str, Any]] = []
        for row in rows:
            state = row.get("state") or {}
            last_activity = state.get("last_activity") if isinstance(state, dict) else None
            departments.append(
                {
                    "id": row.get("id"),
                    "title": row.get("name") or "Department",
                    "category": row.get("type") or "Department",
                    "status": row.get("status") or "PAUSED",
                    "summary": last_activity or "No recent activity recorded.",
                    "updated_at": row.get("last_heartbeat"),
                }
            )
        return departments

    async def _compliance_audits(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("compliance_audits")
            .select("id, title, scope, status, scheduled_date, created_at")
            .eq("user_id", user_id)
            .order("scheduled_date", desc=True)
            .limit(5)
        )
        return [
            {
                "id": row.get("id"),
                "title": row.get("title") or "Audit",
                "category": row.get("scope") or "Audit",
                "status": row.get("status") or "scheduled",
                "summary": f"Scope: {row.get('scope') or 'General'}",
                "created_at": row.get("scheduled_date") or row.get("created_at"),
            }
            for row in rows
        ]

    async def _compliance_risks(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._safe_rows(
            self.client.table("compliance_risks")
            .select("id, title, severity, status, owner, created_at")
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(5)
        )
        risks: list[dict[str, Any]] = []
        for row in rows:
            owner = row.get("owner") or "Owner unassigned"
            severity = row.get("severity") or "unknown"
            risks.append(
                {
                    "id": row.get("id"),
                    "title": row.get("title") or "Risk",
                    "category": severity,
                    "status": row.get("status") or "active",
                    "summary": f"{severity.title()} severity · {owner}",
                    "created_at": row.get("created_at"),
                }
            )
        return risks

    def _format_audit_summary(self, metadata: Any) -> str:
        if not isinstance(metadata, dict):
            return "Tracked in audit trail"
        summary_parts: list[str] = []
        for key in ("step_name", "decision", "status", "phase"):
            value = metadata.get(key)
            if value:
                summary_parts.append(str(value))
        return " · ".join(summary_parts) if summary_parts else "Tracked in audit trail"

    async def _workflow_execution_audit(self, user_id: str) -> list[dict[str, Any]]:
        executions = await self._safe_rows(
            self.client.table("workflow_executions")
            .select("id, name")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(10)
        )
        execution_lookup = {
            row.get("id"): row.get("name") or "Workflow"
            for row in executions
            if row.get("id")
        }
        if not execution_lookup:
            return []
        rows = await self._safe_rows(
            self.client.table("workflow_execution_audit")
            .select("execution_id, action, metadata, created_at")
            .in_("execution_id", list(execution_lookup.keys()))
            .order("created_at", desc=True)
            .limit(6)
        )
        return [
            {
                "id": f"{row.get('execution_id')}:{row.get('action')}:{row.get('created_at')}",
                "title": execution_lookup.get(row.get("execution_id"), "Workflow"),
                "category": str(row.get("action") or "audit").replace("_", " ").title(),
                "status": str(row.get("action") or "audit"),
                "summary": self._format_audit_summary(row.get("metadata")),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    async def _workflow_template_audit(self, user_id: str) -> list[dict[str, Any]]:
        templates = await self._safe_rows(
            self.client.table("workflow_templates")
            .select("id, name")
            .eq("created_by", user_id)
            .order("created_at", desc=True)
            .limit(10)
        )
        template_lookup = {
            row.get("id"): row.get("name") or "Workflow template"
            for row in templates
            if row.get("id")
        }
        if not template_lookup:
            return []
        rows = await self._safe_rows(
            self.client.table("workflow_template_audit")
            .select("template_id, action, metadata, created_at")
            .in_("template_id", list(template_lookup.keys()))
            .order("created_at", desc=True)
            .limit(6)
        )
        return [
            {
                "id": f"{row.get('template_id')}:{row.get('action')}:{row.get('created_at')}",
                "title": template_lookup.get(row.get("template_id"), "Workflow template"),
                "category": str(row.get("action") or "audit").replace("_", " ").title(),
                "status": str(row.get("action") or "audit"),
                "summary": self._format_audit_summary(row.get("metadata")),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    async def _financial_summary(self, user_id: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ninety_days_ago = now - timedelta(days=90)
        rows = await self._safe_rows(
            self.client.table("financial_records")
            .select("amount, transaction_type, currency, transaction_date")
            .eq("user_id", user_id)
            .gte("transaction_date", ninety_days_ago.isoformat())
            .order("transaction_date", desc=True)
            .limit(500)
        )
        currency = "USD"
        revenue = 0.0
        inflows = 0.0
        outflows = 0.0
        recent_expenses = 0.0
        expense_window_count = 0
        for row in rows:
            amount = row.get("amount")
            if not isinstance(amount, (int, float)):
                continue
            numeric = float(amount)
            currency = row.get("currency") or currency
            record_type = str(row.get("transaction_type") or "").strip().lower()
            raw_date = str(row.get("transaction_date") or "")
            record_date = None
            if raw_date:
                try:
                    record_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except Exception:
                    record_date = None
            if record_type in {"expense", "burn", "cost", "payroll", "debit"}:
                outflows += abs(numeric)
                recent_expenses += abs(numeric)
                expense_window_count += 1
            else:
                inflows += numeric
                if record_type == "revenue" and record_date and record_date >= current_month_start:
                    revenue += numeric
        cash_position = inflows - outflows
        monthly_burn = (recent_expenses / 3.0) if expense_window_count else 0.0
        runway_months = (cash_position / monthly_burn) if monthly_burn > 0 else None
        return {
            "currency": currency,
            "revenue": round(revenue, 2),
            "cash_position": round(cash_position, 2),
            "monthly_burn": round(monthly_burn, 2),
            "runway_months": round(runway_months, 2) if runway_months is not None else None,
        }

    def _recommended_action(
        self,
        *,
        persona: str,
        approvals: list[dict[str, Any]],
        workflows: list[dict[str, Any]],
        initiatives: list[dict[str, Any]],
        brain_dumps: list[dict[str, Any]],
    ) -> dict[str, str]:
        if approvals:
            return {
                "title": "Clear pending approvals",
                "description": f"{len(approvals)} approval item(s) are waiting before more work can move.",
                "href": "/dashboard/workflows/active",
            }
        if workflows:
            return {
                "title": "Finish the active workflow",
                "description": f"Focus on {workflows[0]['title']} to move execution forward today.",
                "href": "/dashboard/workflows/active",
            }
        if initiatives:
            return {
                "title": "Push the lead initiative forward",
                "description": f"{initiatives[0]['title']} is the clearest next place to create momentum.",
                "href": f"/dashboard/initiatives/{initiatives[0]['id']}",
            }
        if brain_dumps:
            return {
                "title": "Continue your latest brain dump",
                "description": "Turn captured ideas into a concrete initiative or workflow.",
                "href": f"/dashboard/workspace?braindump_id={brain_dumps[0]['id']}",
            }
        defaults = {
            "solopreneur": ("Capture the next revenue move", "Turn your next idea into an initiative or workflow.", "/dashboard/braindump"),
            "startup": ("Launch the next experiment", "Start a workflow that tightens your growth loop this week.", "/dashboard/workflows/templates"),
            "sme": ("Review operational ownership", "Check the teams, tasks, and approvals that need a clear owner.", "/departments"),
            "enterprise": ("Review governance queue", "Start with approvals and stakeholder-safe reporting before expanding scope.", "/dashboard/workflows/active"),
        }
        title, description, href = defaults.get(persona, defaults["startup"])
        return {"title": title, "description": description, "href": href}

    def _build_kpis(
        self,
        *,
        persona: str,
        finance: dict[str, Any],
        workflows: list[dict[str, Any]],
        initiatives: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        approvals: list[dict[str, Any]],
        reports: list[dict[str, Any]],
        content_queue: list[dict[str, Any]],
        departments: list[dict[str, Any]],
        audits: list[dict[str, Any]],
        risks: list[dict[str, Any]],
        execution_audit: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        if persona == "solopreneur":
            return [
                {"label": "Revenue this month", "value": self._format_currency(finance.get("revenue"), finance.get("currency", "USD")), "tone": "teal"},
                {"label": "Cash position", "value": self._format_currency(finance.get("cash_position"), finance.get("currency", "USD")), "tone": "emerald"},
                {"label": "Quick tasks", "value": str(len(tasks)), "tone": "amber"},
                {"label": "Content queue", "value": str(len(content_queue)), "tone": "blue"},
            ]
        if persona == "startup":
            return [
                {"label": "Revenue this month", "value": self._format_currency(finance.get("revenue"), finance.get("currency", "USD")), "tone": "indigo"},
                {"label": "Runway", "value": self._format_months(finance.get("runway_months")), "tone": "amber"},
                {"label": "Active initiatives", "value": str(len(initiatives)), "tone": "teal"},
                {"label": "Pending approvals", "value": str(len(approvals)), "tone": "rose"},
            ]
        if persona == "sme":
            running_departments = sum(1 for item in departments if str(item.get("status")).upper() == "RUNNING")
            return [
                {"label": "Departments running", "value": str(running_departments), "tone": "blue"},
                {"label": "Open risks", "value": str(len(risks)), "tone": "rose"},
                {"label": "Pending approvals", "value": str(len(approvals)), "tone": "amber"},
                {"label": "Recent reports", "value": str(len(reports)), "tone": "slate"},
            ]
        return [
            {"label": "Governance queue", "value": str(len(approvals)), "tone": "slate"},
            {"label": "Execution audit", "value": str(len(execution_audit)), "tone": "blue"},
            {"label": "Executive reports", "value": str(len(reports)), "tone": "teal"},
            {"label": "Open risks", "value": str(len(risks) + len(audits)), "tone": "amber"},
        ]

    async def get_home_summary(self, *, user_id: str, persona: str | None) -> dict[str, Any]:
        effective_persona = self._effective_persona(persona)
        policy = get_persona_policy(effective_persona)

        approvals = await self._pending_approvals(user_id)
        workflows = await self._active_workflows(user_id)
        completed_workflows = await self._recent_completed_workflows(user_id)
        initiatives = await self._initiatives(user_id)
        tasks = await self._open_tasks(user_id)
        brain_dumps = await self._brain_dumps(user_id)
        content_queue = await self._content_queue(user_id)
        reports = await self._reports(user_id)
        departments = await self._departments()
        audits = await self._compliance_audits(user_id)
        risks = await self._compliance_risks(user_id)
        execution_audit = await self._workflow_execution_audit(user_id)
        template_audit = await self._workflow_template_audit(user_id)
        finance = await self._financial_summary(user_id)
        recommendation = self._recommended_action(
            persona=effective_persona,
            approvals=approvals,
            workflows=workflows,
            initiatives=initiatives,
            brain_dumps=brain_dumps,
        )

        headlines = {
            "solopreneur": ("Run the next revenue move", "Your home is tuned for quick execution, cash awareness, and fewer loose ends."),
            "startup": ("Keep the growth loop tight", "Track runway, experiments, launches, and approvals without slowing the team."),
            "sme": ("Operate with clearer ownership", "Use this view to keep teams, checklists, compliance, and reporting on track."),
            "enterprise": ("Lead with governance and visibility", "Stay on top of approvals, workflow readiness, audit signals, and stakeholder-safe reporting."),
        }
        headline, subheadline = headlines.get(effective_persona, headlines["startup"])

        return {
            "persona": effective_persona,
            "label": policy.label if policy else effective_persona.title(),
            "summary": policy.summary if policy else "",
            "headline": headline,
            "subheadline": subheadline,
            "brief": {
                "title": recommendation["title"],
                "body": recommendation["description"],
            },
            "kpis": self._build_kpis(
                persona=effective_persona,
                finance=finance,
                workflows=workflows,
                initiatives=initiatives,
                tasks=tasks,
                approvals=approvals,
                reports=reports,
                content_queue=content_queue,
                departments=departments,
                audits=audits,
                risks=risks,
                execution_audit=execution_audit,
            ),
            "recommended_action": recommendation,
            "collections": {
                "initiatives": initiatives,
                "workflows": workflows,
                "completed_workflows": completed_workflows,
                "tasks": tasks,
                "approvals": approvals,
                "brain_dumps": brain_dumps,
                "content_queue": content_queue,
                "reports": reports,
                "departments": departments,
                "audits": audits,
                "risks": risks,
                "execution_audit": execution_audit,
                "template_audit": template_audit,
            },
            "signals": {
                "active_workflows": len(workflows),
                "active_initiatives": len(initiatives),
                "open_tasks": len(tasks),
                "pending_approvals": len(approvals),
                "recent_reports": len(reports),
                "active_departments": sum(1 for item in departments if str(item.get("status")).upper() == "RUNNING"),
                "scheduled_audits": len(audits),
                "open_risks": len(risks),
                "recent_execution_audit": len(execution_audit),
            },
            "finance": finance,
        }


_dashboard_summary_service: DashboardSummaryService | None = None


def get_dashboard_summary_service() -> DashboardSummaryService:
    global _dashboard_summary_service
    if _dashboard_summary_service is None:
        _dashboard_summary_service = DashboardSummaryService()
    return _dashboard_summary_service


