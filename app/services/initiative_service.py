"""InitiativeService - CRUD operations for strategic initiatives and OKRs.

This service provides Create, Read, Update, Delete operations for initiatives
stored in the initiatives table in Supabase with proper RLS authentication.
Used by StrategicPlanningAgent.

Status vocabulary (unified):
    not_started, in_progress, completed, blocked, on_hold

Phase vocabulary:
    ideation, validation, prototype, build, scale
"""

from typing import Optional, Any
from datetime import datetime, timezone
from app.services.base_service import BaseService, AdminService
from app.services.request_context import get_current_user_id

# Unified status and phase constants
INITIATIVE_STATUSES = ["not_started", "in_progress", "completed", "blocked", "on_hold"]
INITIATIVE_PHASES = ["ideation", "validation", "prototype", "build", "scale"]
CHECKLIST_ITEM_STATUSES = ["pending", "in_progress", "completed", "blocked", "skipped"]


def _build_initiative_report_row(user_id: str, initiative: dict) -> dict:
    """Build a user_reports row from an initiative for the Reports page."""
    title = (initiative.get("title") or "Initiative").strip() or "Initiative"
    meta = initiative.get("metadata") or {}
    phase = initiative.get("phase") or "ideation"
    status = initiative.get("status") or "not_started"
    desired = (meta.get("desired_outcomes") or "")[:500] if isinstance(meta.get("desired_outcomes"), str) else ""
    timeline = (meta.get("timeline") or "")[:200] if isinstance(meta.get("timeline"), str) else ""
    summary_parts = [f"Phase: {phase}. Status: {status}."]
    if desired:
        summary_parts.append(f" Outcomes: {desired[:200]}{'…' if len(desired) > 200 else ''}")
    if timeline:
        summary_parts.append(f" Timeline: {timeline}")
    summary = " ".join(summary_parts)
    content_parts = [initiative.get("description") or "", f"\nPhase: {phase}", f"Status: {status}"]
    if desired:
        content_parts.append(f"\nDesired outcomes: {desired}")
    if timeline:
        content_parts.append(f"\nTimeline: {timeline}")
    content = "\n".join(p for p in content_parts if p)
    return {
        "user_id": user_id,
        "title": title,
        "category": "Initiative",
        "status": "Completed",
        "summary": summary,
        "content": content or summary,
        "source_type": "initiative",
        "source_id": initiative.get("id"),
        "metadata": {"phase": phase, "status": status},
    }


class InitiativeService(BaseService):
    """Service for managing initiatives and OKRs.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the initiative service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "initiatives"

    async def create_initiative(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        user_id: Optional[str] = None,
        phase: str = "ideation",
        template_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a new initiative.
        
        Args:
            title: Initiative title.
            description: Initiative description.
            priority: Priority level (low, medium, high, critical).
            user_id: Optional user ID who owns the initiative.
            phase: Starting phase (default: ideation).
            template_id: Optional template ID this was created from.
            metadata: Optional metadata dict (OKRs, milestones, etc.).
            
        Returns:
            The created initiative record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for initiative creation")

        data = {
            "title": title,
            "description": description,
            "priority": priority,
            "status": "not_started",
            "progress": 0,
            "phase": phase,
            "phase_progress": {p: 0 for p in INITIATIVE_PHASES},
            "user_id": effective_user_id,
            "metadata": metadata or {},
        }
        if template_id:
            data["template_id"] = template_id

        client = self.client if self.is_authenticated else AdminService().client
        response = client.table(self._table_name).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_initiative(self, initiative_id: str, user_id: Optional[str] = None) -> dict:
        """Retrieve a single initiative by ID.
        
        Args:
            initiative_id: The unique initiative ID.
            
        Returns:
            The initiative record.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._table_name)
            .select("*")
            .eq("id", initiative_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = query.single().execute()
        return response.data

    async def update_initiative(
        self,
        initiative_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        phase: Optional[str] = None,
        phase_progress: Optional[dict] = None,
        metadata: Optional[dict] = None,
        workflow_execution_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """Update an initiative's status, progress, or phase.
        
        Args:
            initiative_id: The unique initiative ID.
            status: New status (not_started, in_progress, completed, blocked, on_hold).
            progress: Overall progress percentage (0-100).
            title: New title.
            description: New description.
            phase: Current initiative phase (ideation, validation, prototype, build, scale).
            phase_progress: Per-phase progress dict.
            metadata: Metadata dict (merged with existing).
            workflow_execution_id: Link to workflow execution.
            
        Returns:
            The updated initiative record.
        """
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if progress is not None:
            update_data["progress"] = progress
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if phase is not None:
            update_data["phase"] = phase
        if phase_progress is not None:
            update_data["phase_progress"] = phase_progress
        if metadata is not None:
            # Merge with existing metadata so journey_id and other keys are preserved
            existing = await self.get_initiative(initiative_id, user_id)
            existing_meta = (existing or {}).get("metadata") or {}
            if not isinstance(existing_meta, dict):
                existing_meta = {}
            update_data["metadata"] = {**existing_meta, **metadata}
        if workflow_execution_id is not None:
            update_data["workflow_execution_id"] = workflow_execution_id
            
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._table_name)
            .update(update_data)
            .eq("id", initiative_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = query.execute()
        if response.data:
            updated = response.data[0]
            try:
                report_user_id = effective_user_id or updated.get("user_id")
                if report_user_id and updated.get("id"):
                    row = _build_initiative_report_row(report_user_id, updated)
                    client.table("user_reports").upsert(
                        row,
                        on_conflict="user_id,source_type,source_id",
                    ).execute()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Failed to upsert initiative report: %s", e)
            return updated
        raise Exception("No data returned from update")

    async def advance_phase(
        self,
        initiative_id: str,
        user_id: Optional[str] = None
    ) -> dict:
        """Advance an initiative to the next phase.
        
        Args:
            initiative_id: The unique initiative ID.
            
        Returns:
            The updated initiative record.
        """
        initiative = await self.get_initiative(initiative_id, user_id)
        current_phase = initiative.get("phase", "ideation")
        
        try:
            idx = INITIATIVE_PHASES.index(current_phase)
        except ValueError:
            idx = 0
        
        if idx < len(INITIATIVE_PHASES) - 1:
            next_phase = INITIATIVE_PHASES[idx + 1]
            # Mark current phase as 100% and move to next
            phase_progress = initiative.get("phase_progress", {})
            phase_progress[current_phase] = 100
            
            # Calculate overall progress based on phases completed
            overall = int(((idx + 1) / len(INITIATIVE_PHASES)) * 100)
            
            return await self.update_initiative(
                initiative_id,
                phase=next_phase,
                phase_progress=phase_progress,
                progress=overall,
                status="in_progress",
                user_id=user_id,
            )
        else:
            # Already at last phase, mark as completed
            phase_progress = initiative.get("phase_progress", {})
            phase_progress[current_phase] = 100
            return await self.update_initiative(
                initiative_id,
                phase_progress=phase_progress,
                progress=100,
                status="completed",
                user_id=user_id,
            )

    async def delete_initiative(self, initiative_id: str, user_id: Optional[str] = None) -> bool:
        """Delete an initiative by ID.
        
        Args:
            initiative_id: The unique initiative ID.
            
        Returns:
            True if deletion was successful.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._table_name)
            .delete()
            .eq("id", initiative_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = query.execute()
        return len(response.data) > 0

    async def list_initiatives(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        priority: Optional[str] = None,
        phase: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """List initiatives with optional filters.
        
        Args:
            status: Filter by initiative status.
            user_id: Filter by user ID.
            priority: Filter by priority.
            phase: Filter by initiative phase.
            limit: Maximum number of results (default 50).
            
        Returns:
            List of initiative records.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*")
        
        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
        if priority:
            query = query.eq("priority", priority)
        if phase:
            query = query.eq("phase", phase)
            
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data

    async def list_templates(
        self,
        persona: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list:
        """List initiative templates with optional filters.
        
        Args:
            persona: Filter by persona (solopreneur, startup, sme, enterprise).
            category: Filter by category.
            
        Returns:
            List of initiative template records.
        """
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("initiative_templates").select("*")
        
        if persona:
            query = query.eq("persona", persona)
        if category:
            query = query.eq("category", category)
            
        response = query.order("title").execute()
        return response.data

    async def list_checklist_items(
        self,
        initiative_id: str,
        user_id: Optional[str] = None,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        include_deleted: bool = False,
        owner_label: Optional[str] = None,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "sort_order",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        """List checklist items for an initiative."""
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        sort_by_allowed = {"sort_order", "created_at", "updated_at", "due_at", "status", "title"}
        if sort_by not in sort_by_allowed:
            raise ValueError(f"Invalid sort_by '{sort_by}'")
        normalized_order = (sort_order or "asc").lower()
        if normalized_order not in {"asc", "desc"}:
            raise ValueError(f"Invalid sort_order '{sort_order}'")
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise ValueError("Missing user_id")
        await self.get_initiative(initiative_id, effective_user_id)
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table("initiative_checklist_items")
            .select("*")
            .eq("initiative_id", initiative_id)
            .eq("user_id", effective_user_id)
        )
        if not include_deleted:
            query = query.eq("is_deleted", False)
        if phase:
            query = query.eq("phase", phase)
        if status:
            query = query.eq("status", status)
        if owner_label:
            query = query.ilike("owner_label", f"%{owner_label}%")
        if due_before:
            query = query.lte("due_at", due_before)
        if due_after:
            query = query.gte("due_at", due_after)
        response = (
            query
            .order(sort_by, desc=(normalized_order == "desc"))
            .order("created_at", desc=False)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []

    async def list_checklist_events(
        self,
        initiative_id: str,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        item_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List checklist audit events for an initiative."""
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise ValueError("Missing user_id")
        await self.get_initiative(initiative_id, effective_user_id)
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table("initiative_checklist_item_events")
            .select("*")
            .eq("initiative_id", initiative_id)
            .eq("user_id", effective_user_id)
        )
        if event_type:
            query = query.eq("event_type", event_type)
        if item_id:
            query = query.eq("item_id", item_id)
        if actor_user_id:
            query = query.eq("actor_user_id", actor_user_id)
        response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return response.data or []

    async def create_checklist_item(
        self,
        initiative_id: str,
        *,
        title: str,
        phase: str,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        status: str = "pending",
        owner_user_id: Optional[str] = None,
        owner_label: Optional[str] = None,
        due_at: Optional[str] = None,
        evidence: Optional[list[Any]] = None,
        sort_order: int = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a checklist item and audit event."""
        if phase not in INITIATIVE_PHASES:
            raise ValueError(f"Invalid phase '{phase}'")
        if status not in CHECKLIST_ITEM_STATUSES:
            raise ValueError(f"Invalid status '{status}'")
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise ValueError("Missing user_id")
        await self.get_initiative(initiative_id, effective_user_id)
        client = self.client if self.is_authenticated else AdminService().client
        payload = {
            "initiative_id": initiative_id,
            "user_id": effective_user_id,
            "phase": phase,
            "title": title,
            "description": description,
            "status": status,
            "owner_user_id": owner_user_id,
            "owner_label": owner_label,
            "due_at": due_at,
            "evidence": evidence or [],
            "sort_order": sort_order,
            "metadata": metadata or {},
            "created_by": effective_user_id,
            "updated_by": effective_user_id,
        }
        response = client.table("initiative_checklist_items").insert(payload).execute()
        if not response.data:
            raise Exception("No data returned from checklist insert")
        item = response.data[0]
        await self._log_checklist_event(
            item_id=item["id"],
            initiative_id=initiative_id,
            user_id=effective_user_id,
            event_type="created",
            payload={"after": item},
            actor_user_id=effective_user_id,
        )
        return item

    async def update_checklist_item(
        self,
        initiative_id: str,
        item_id: str,
        *,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        owner_label: Optional[str] = None,
        due_at: Optional[str] = None,
        evidence: Optional[list[Any]] = None,
        sort_order: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Update a checklist item and write audit event."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise ValueError("Missing user_id")
        await self.get_initiative(initiative_id, effective_user_id)
        client = self.client if self.is_authenticated else AdminService().client
        before_res = (
            client.table("initiative_checklist_items")
            .select("*")
            .eq("id", item_id)
            .eq("initiative_id", initiative_id)
            .eq("user_id", effective_user_id)
            .eq("is_deleted", False)
            .limit(1)
            .execute()
        )
        if not before_res.data:
            raise ValueError("Checklist item not found")
        before = before_res.data[0]

        patch: dict[str, Any] = {"updated_by": effective_user_id}
        if title is not None:
            patch["title"] = title
        if description is not None:
            patch["description"] = description
        if phase is not None:
            if phase not in INITIATIVE_PHASES:
                raise ValueError(f"Invalid phase '{phase}'")
            patch["phase"] = phase
        if status is not None:
            if status not in CHECKLIST_ITEM_STATUSES:
                raise ValueError(f"Invalid status '{status}'")
            patch["status"] = status
        if owner_user_id is not None:
            patch["owner_user_id"] = owner_user_id
        if owner_label is not None:
            patch["owner_label"] = owner_label
        if due_at is not None:
            patch["due_at"] = due_at
        if evidence is not None:
            patch["evidence"] = evidence
        if sort_order is not None:
            patch["sort_order"] = sort_order
        if metadata is not None:
            existing_meta = before.get("metadata") or {}
            if not isinstance(existing_meta, dict):
                existing_meta = {}
            patch["metadata"] = {**existing_meta, **metadata}

        response = (
            client.table("initiative_checklist_items")
            .update(patch)
            .eq("id", item_id)
            .eq("initiative_id", initiative_id)
            .eq("user_id", effective_user_id)
            .execute()
        )
        if not response.data:
            raise Exception("No data returned from checklist update")
        item = response.data[0]
        event_type = "updated"
        if status is not None and status != before.get("status"):
            event_type = "status_changed"
        await self._log_checklist_event(
            item_id=item_id,
            initiative_id=initiative_id,
            user_id=effective_user_id,
            event_type=event_type,
            payload={"before": before, "after": item},
            actor_user_id=effective_user_id,
        )
        return item

    async def delete_checklist_item(
        self,
        initiative_id: str,
        item_id: str,
        *,
        user_id: Optional[str] = None,
    ) -> bool:
        """Soft-delete checklist item and write audit event."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise ValueError("Missing user_id")
        await self.get_initiative(initiative_id, effective_user_id)
        client = self.client if self.is_authenticated else AdminService().client
        before_res = (
            client.table("initiative_checklist_items")
            .select("*")
            .eq("id", item_id)
            .eq("initiative_id", initiative_id)
            .eq("user_id", effective_user_id)
            .eq("is_deleted", False)
            .limit(1)
            .execute()
        )
        if not before_res.data:
            return False
        before = before_res.data[0]
        response = (
            client.table("initiative_checklist_items")
            .update(
                {
                    "is_deleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                    "updated_by": effective_user_id,
                }
            )
            .eq("id", item_id)
            .eq("initiative_id", initiative_id)
            .eq("user_id", effective_user_id)
            .execute()
        )
        if not response.data:
            return False
        await self._log_checklist_event(
            item_id=item_id,
            initiative_id=initiative_id,
            user_id=effective_user_id,
            event_type="deleted",
            payload={"before": before},
            actor_user_id=effective_user_id,
        )
        return True

    async def _log_checklist_event(
        self,
        *,
        item_id: Optional[str],
        initiative_id: str,
        user_id: str,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
        actor_user_id: Optional[str] = None,
    ) -> None:
        """Best-effort checklist audit event log."""
        try:
            client = self.client if self.is_authenticated else AdminService().client
            client.table("initiative_checklist_item_events").insert(
                {
                    "item_id": item_id,
                    "initiative_id": initiative_id,
                    "user_id": user_id,
                    "event_type": event_type,
                    "payload": payload or {},
                    "actor_user_id": actor_user_id,
                }
            ).execute()
        except Exception:
            # Checklist operations should not fail solely due to audit write issues.
            pass

    async def create_from_template(
        self,
        template_id: str,
        user_id: Optional[str] = None,
        title_override: Optional[str] = None,
    ) -> dict:
        """Create an initiative from a template.
        
        Args:
            template_id: The template ID to use.
            user_id: The user who owns the initiative.
            title_override: Optional custom title.
            
        Returns:
            The created initiative record.
        """
        client = self.client if self.is_authenticated else AdminService().client
        template_response = client.table("initiative_templates").select("*").eq("id", template_id).single().execute()
        template = template_response.data
        
        if not template:
            raise Exception(f"Template {template_id} not found")
        
        return await self.create_initiative(
            title=title_override or template["title"],
            description=template.get("description", ""),
            priority=template.get("priority", "medium"),
            user_id=user_id,
            phase="ideation",
            template_id=template_id,
            metadata={
                "template_title": template["title"],
                "phases": template.get("phases", []),
                "suggested_workflows": template.get("suggested_workflows", []),
                "kpis": template.get("kpis", []),
            },
        )
