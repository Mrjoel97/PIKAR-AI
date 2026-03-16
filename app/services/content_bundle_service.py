from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from app.services.request_context import (
    get_current_session_id,
    get_current_workflow_execution_id,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

WorkspaceMode = Literal["embedded", "focus", "grid", "split", "compare"]


def _clean_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


class ContentBundleService:
    """Persist normalized bundle, deliverable, and workspace references for media outputs."""

    def __init__(self, client: Any | None = None):
        try:
            self.client = client or get_service_client()
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Content bundle service unavailable: %s", exc)
            self.client = None

    async def register_media_output(
        self,
        *,
        user_id: str,
        asset_id: str,
        asset_type: str,
        title: str,
        prompt: str | None = None,
        file_url: str | None = None,
        thumbnail_url: str | None = None,
        editable_url: str | None = None,
        source: str = "agent_media",
        bundle_id: str | None = None,
        deliverable_key: str = "primary",
        workspace_mode: WorkspaceMode = "focus",
        session_id: str | None = None,
        workflow_execution_id: str | None = None,
        platform_profile: str | None = None,
        widget_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session_id = session_id or get_current_session_id()
        workflow_execution_id = workflow_execution_id or get_current_workflow_execution_id()
        contract = {
            "session_id": session_id,
            "workflow_execution_id": workflow_execution_id,
            "workspace_mode": workspace_mode,
        }
        if not self.client or not user_id or not asset_id:
            return contract

        bundle_id = bundle_id or str(uuid.uuid4())
        metadata = dict(metadata or {})
        bundle_row = {
            "id": bundle_id,
            "user_id": user_id,
            "created_by": user_id,
            "source": source,
            "title": title,
            "prompt": prompt,
            "bundle_type": asset_type if asset_type in {"image", "video", "audio"} else "mixed",
            "status": "ready",
            "session_id": session_id,
            "workflow_execution_id": workflow_execution_id,
            "metadata": _clean_dict(
                {
                    "asset_id": asset_id,
                    "asset_type": asset_type,
                    "platform_profile": platform_profile,
                    **metadata,
                }
            ),
        }
        deliverable_row = {
            "id": str(uuid.uuid4()),
            "bundle_id": bundle_id,
            "user_id": user_id,
            "created_by": user_id,
            "source_key": asset_id,
            "deliverable_key": deliverable_key,
            "asset_type": asset_type,
            "media_asset_id": asset_id,
            "title": title,
            "prompt": prompt,
            "file_url": file_url,
            "thumbnail_url": thumbnail_url,
            "editable_url": editable_url,
            "platform_profile": platform_profile,
            "variant_label": deliverable_key,
            "metadata": _clean_dict(metadata),
        }

        try:
            bundle_result = await execute_async(
                self.client.table("content_bundles").upsert(bundle_row, on_conflict="id"),
                op_name="content_bundle_service.bundle_upsert",
            )
            bundle = bundle_result.data[0] if getattr(bundle_result, "data", None) else bundle_row
            deliverable_result = await execute_async(
                self.client.table("content_bundle_deliverables").upsert(
                    deliverable_row,
                    on_conflict="source_key",
                ),
                op_name="content_bundle_service.deliverable_upsert",
            )
            deliverable = deliverable_result.data[0] if getattr(deliverable_result, "data", None) else deliverable_row

            workspace_source_key = f"{session_id or 'global'}:{deliverable.get('id')}"
            workspace_row = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "created_by": user_id,
                "bundle_id": bundle.get("id"),
                "deliverable_id": deliverable.get("id"),
                "source_key": workspace_source_key,
                "session_id": session_id,
                "workflow_execution_id": workflow_execution_id,
                "item_type": widget_type or asset_type,
                "widget_type": widget_type or asset_type,
                "title": title,
                "layout_mode": workspace_mode,
                "widget_payload": _clean_dict(
                    {
                        "asset_id": asset_id,
                        "bundle_id": bundle.get("id"),
                        "deliverable_id": deliverable.get("id"),
                        "file_url": file_url,
                        "thumbnail_url": thumbnail_url,
                        "editable_url": editable_url,
                        "platform_profile": platform_profile,
                    }
                ),
                "metadata": _clean_dict(metadata),
            }
            workspace_result = await execute_async(
                self.client.table("workspace_items").upsert(
                    workspace_row,
                    on_conflict="source_key",
                ),
                op_name="content_bundle_service.workspace_upsert",
            )
            workspace_item = workspace_result.data[0] if getattr(workspace_result, "data", None) else workspace_row
        except Exception as exc:
            logger.warning("Failed to persist content bundle contract for asset %s: %s", asset_id, exc)
            return contract

        contract.update(
            {
                "bundle_id": bundle.get("id"),
                "deliverable_id": deliverable.get("id"),
                "workspace_item_id": workspace_item.get("id"),
            }
        )
        return contract

    def attach_widget_contract(
        self,
        widget: dict[str, Any],
        *,
        contract: dict[str, Any],
        workspace_mode: WorkspaceMode | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        widget_copy = dict(widget)
        data = dict(widget_copy.get("data") or {})
        data.update(
            _clean_dict(
                {
                    "bundle_id": contract.get("bundle_id"),
                    "deliverable_id": contract.get("deliverable_id"),
                    "workspace_item_id": contract.get("workspace_item_id"),
                    "session_id": contract.get("session_id"),
                    "workflow_execution_id": contract.get("workflow_execution_id"),
                }
            )
        )
        if extra_data:
            data.update(_clean_dict(extra_data))
        widget_copy["data"] = data

        workspace = dict(widget_copy.get("workspace") or {})
        workspace.update(
            _clean_dict(
                {
                    "mode": workspace_mode or contract.get("workspace_mode") or workspace.get("mode") or "focus",
                    "bundleId": contract.get("bundle_id"),
                    "deliverableId": contract.get("deliverable_id"),
                    "workspaceItemId": contract.get("workspace_item_id"),
                    "sessionId": contract.get("session_id"),
                    "workflowExecutionId": contract.get("workflow_execution_id"),
                }
            )
        )
        widget_copy["workspace"] = workspace
        return widget_copy
