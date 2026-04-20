# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

import logging
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.personas.policy_registry import list_persona_policies
from app.services.cache import get_cache_service
from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client
from app.services.user_agent_factory import get_user_agent_factory
from supabase import Client

logger = logging.getLogger(__name__)

_ONBOARDING_BRIEF_CATEGORY = "Onboarding Brief"
_ONBOARDING_BRIEF_FILENAME = "onboarding-business-brief.md"


class UserPersona(Enum):
    SOLOPRENEUR = "solopreneur"
    STARTUP = "startup"
    SME = "sme"
    ENTERPRISE = "enterprise"


class BusinessContextInput(BaseModel):
    company_name: str
    industry: str
    description: str
    goals: list[str]
    team_size: str | None = None
    role: str | None = None
    website: str | None = None


class UserPreferencesInput(BaseModel):
    tone: str = "professional"
    verbosity: str = "concise"
    communication_style: str = "direct"
    notification_frequency: str = "daily"


class AgentSetupInput(BaseModel):
    agent_name: str
    focus_areas: list[str] | None = None


class OnboardingStatus(BaseModel):
    is_completed: bool
    current_step: int
    total_steps: int = 4
    business_context_completed: bool
    preferences_completed: bool
    agent_setup_completed: bool
    persona: str | None = None
    agent_name: str | None = None


class UserOnboardingService:
    """Service to handle user onboarding flow."""

    def __init__(self):
        try:
            self.supabase: Client = get_service_client()
        except ValueError as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
        self._agent_factory = get_user_agent_factory()
        self._cache = get_cache_service()

    def _determine_persona(self, context: dict) -> UserPersona:
        """Determine user persona based on business context."""
        size = context.get("team_size", "").lower()
        role = context.get("role", "").lower()
        industry = context.get("industry", "").lower()

        # Explicit Frontend ID Checks
        if size == "solo":
            return UserPersona.SOLOPRENEUR
        if size == "enterprise":
            return UserPersona.ENTERPRISE
        if size in ["sme-small", "sme-large"]:
            return UserPersona.SME
        if size == "startup":
            return UserPersona.STARTUP

        # Fallback Heuristics (for legacy or text inputs)
        # Enterprise Rules
        if "200+" in size or "enterprise" in size or "500+" in size:
            return UserPersona.ENTERPRISE
        if "corporate" in industry and (
            "vp" in role or "chief" in role or "head" in role
        ):
            return UserPersona.ENTERPRISE

        # SME Rules
        if "51-200" in size:
            return UserPersona.SME
        if "11-50" in size and "manufacturing" in industry:
            return UserPersona.SME

        # Solopreneur Rules
        if size in ["1", "just me", "freelancer", "solopreneur"]:
            return UserPersona.SOLOPRENEUR
        if "freelance" in role or "consultant" in role:
            return UserPersona.SOLOPRENEUR

        # Default to Startup
        return UserPersona.STARTUP

    @staticmethod
    def _format_markdown_list(values: list[Any] | None) -> list[str]:
        if not values:
            return ["- None provided"]
        cleaned = [str(value).strip() for value in values if str(value).strip()]
        return [f"- {value}" for value in cleaned] or ["- None provided"]

    @staticmethod
    def _sanitize_filename_fragment(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
        return normalized.strip("-") or "business"

    async def _backfill_onboarding_brief_if_missing(
        self,
        *,
        user_id: str,
        profile_data: dict[str, Any],
        agent_data: dict[str, Any],
    ) -> None:
        """Backfill the onboarding brief for users who completed onboarding earlier."""
        business_context = profile_data.get("business_context") or {}
        company_name = business_context.get("company_name") or "business"
        company_slug = self._sanitize_filename_fragment(company_name)
        file_path = f"{user_id}/system/{company_slug}-{_ONBOARDING_BRIEF_FILENAME}"

        existing = await execute_async(
            self.supabase.table("vault_documents")
            .select("id")
            .eq("user_id", user_id)
            .eq("file_path", file_path)
            .limit(1),
            op_name="onboarding.status.brief_lookup",
        )
        if existing.data:
            return

        stored_configuration = agent_data.get("configuration") or {}
        agent_setup = (
            stored_configuration.get("agent_setup")
            if isinstance(stored_configuration, dict)
            else {}
        ) or {}
        await self._sync_onboarding_brief_to_vault(
            user_id=user_id,
            persona=profile_data.get("persona", "startup"),
            business_context=business_context,
            preferences=profile_data.get("preferences") or {},
            agent_name=agent_data.get("agent_name"),
            agent_setup=agent_setup,
        )

    def _build_onboarding_brief_markdown(
        self,
        *,
        business_context: dict[str, Any],
        preferences: dict[str, Any],
        persona: str,
        agent_name: str | None,
        agent_setup: dict[str, Any],
    ) -> str:
        """Render the user's onboarding answers into a durable vault brief."""
        company_name = business_context.get("company_name") or "Untitled Business"
        description = business_context.get("description") or "No description provided."
        lines: list[str] = [
            f"# {company_name} Onboarding Brief",
            "",
            "> Generated automatically from the user's onboarding answers so agents can continue from existing context instead of restarting discovery.",
            "",
            "## Business Snapshot",
            f"- Company: {company_name}",
            f"- Persona: {persona}",
            f"- Industry: {business_context.get('industry') or 'Not specified'}",
            f"- Team size: {business_context.get('team_size') or 'Not specified'}",
            f"- Role: {business_context.get('role') or 'Not specified'}",
            f"- Website: {business_context.get('website') or 'Not specified'}",
            "",
            "## Description",
            description,
            "",
            "## Primary Goals",
            *self._format_markdown_list(business_context.get("goals")),
            "",
            "## Communication Preferences",
            f"- Tone: {preferences.get('tone') or 'Not specified'}",
            f"- Verbosity: {preferences.get('verbosity') or 'Not specified'}",
            f"- Communication style: {preferences.get('communication_style') or 'Not specified'}",
            f"- Notification frequency: {preferences.get('notification_frequency') or 'Not specified'}",
            "",
            "## Agent Personalization",
            f"- Chosen agent name: {agent_name or 'Not specified'}",
            f"- Focus areas: {', '.join(agent_setup.get('focus_areas') or []) or 'Not specified'}",
            "",
            "## Working Rules For Future Sessions",
            "- Start from this saved business context and the latest vault knowledge before asking new discovery questions.",
            "- Ask focused follow-up questions only when something important is missing or has changed.",
            "- Use the onboarding brief, knowledge vault, and prior brainstorm artifacts together when planning work.",
        ]
        return "\n".join(lines).strip() + "\n"

    async def _sync_onboarding_brief_to_vault(
        self,
        *,
        user_id: str,
        persona: str,
        business_context: dict[str, Any],
        preferences: dict[str, Any],
        agent_name: str | None,
        agent_setup: dict[str, Any],
    ) -> None:
        """Create or update a visible/searchable onboarding brief in the vault."""
        from app.rag.knowledge_vault import ingest_document_content

        company_name = business_context.get("company_name") or "Business"
        title = f"{company_name} Onboarding Brief"
        onboarding_brief = self._build_onboarding_brief_markdown(
            business_context=business_context,
            preferences=preferences,
            persona=persona,
            agent_name=agent_name,
            agent_setup=agent_setup,
        )
        company_slug = self._sanitize_filename_fragment(company_name)
        file_path = f"{user_id}/system/{company_slug}-{_ONBOARDING_BRIEF_FILENAME}"
        metadata = {
            "source": "onboarding",
            "persona": persona,
            "agent_name": agent_name,
            "file_path": file_path,
        }

        self.supabase.storage.from_("knowledge-vault").upload(
            file_path,
            onboarding_brief.encode("utf-8"),
            {"content-type": "text/markdown", "upsert": "true"},
        )

        existing = await execute_async(
            self.supabase.table("vault_documents")
            .select("id")
            .eq("user_id", user_id)
            .eq("file_path", file_path)
            .limit(1),
            op_name="onboarding.complete.brief_lookup",
        )
        payload = {
            "user_id": user_id,
            "filename": f"{company_slug}-{_ONBOARDING_BRIEF_FILENAME}",
            "file_path": file_path,
            "file_type": "text/markdown",
            "size_bytes": len(onboarding_brief.encode("utf-8")),
            "category": _ONBOARDING_BRIEF_CATEGORY,
            "is_processed": False,
            "embedding_count": 0,
            "metadata": metadata,
        }
        existing_rows = existing.data or []
        document_id: str | None = None
        if existing_rows:
            document_id = existing_rows[0].get("id")
            await execute_async(
                self.supabase.table("vault_documents")
                .update(payload)
                .eq("id", document_id)
                .eq("user_id", user_id),
                op_name="onboarding.complete.brief_update",
            )
        else:
            inserted = await execute_async(
                self.supabase.table("vault_documents").insert(payload),
                op_name="onboarding.complete.brief_insert",
            )
            inserted_rows = inserted.data or []
            if inserted_rows:
                document_id = inserted_rows[0].get("id")

        try:
            await execute_async(
                self.supabase.table("embeddings")
                .delete()
                .eq("user_id", user_id)
                .filter("metadata->>file_path", "eq", file_path),
                op_name="onboarding.complete.brief_embedding_cleanup",
            )
        except Exception as exc:
            logger.warning(
                "Could not clear previous onboarding brief embeddings for %s: %s",
                user_id,
                exc,
            )

        ingest_result = await ingest_document_content(
            content=onboarding_brief,
            title=title,
            document_type=_ONBOARDING_BRIEF_CATEGORY,
            user_id=user_id,
            metadata=metadata,
        )

        finalize_payload = {
            "is_processed": True,
            "embedding_count": ingest_result.get("chunk_count", 0),
            "metadata": {
                **metadata,
                "document_id": document_id,
            },
        }
        target_query = self.supabase.table("vault_documents").update(finalize_payload)
        if document_id:
            target_query = target_query.eq("id", document_id)
        else:
            target_query = target_query.eq("user_id", user_id).eq("file_path", file_path)

        await execute_async(
            target_query,
            op_name="onboarding.complete.brief_finalize",
        )

    async def get_onboarding_status(self, user_id: str) -> OnboardingStatus:
        """Get the current onboarding status for a user."""
        try:
            profile_response = await execute_async(
                self.supabase.table("users_profile").select("*").eq("user_id", user_id),
                op_name="onboarding.status.profile",
            )
            agent_response = await execute_async(
                self.supabase.table("user_executive_agents")
                .select("agent_name, onboarding_completed, configuration")
                .eq("user_id", user_id),
                op_name="onboarding.status.agent",
            )

            agent_data = agent_response.data[0] if agent_response.data else {}
            profile_data = profile_response.data[0] if profile_response.data else {}

            bc_completed = bool(profile_data.get("business_context"))
            pref_completed = bool(profile_data.get("preferences"))
            agent_setup_done = bool(agent_data.get("agent_name"))

            step = 0
            if bc_completed:
                step = 1
            if pref_completed:
                step = 2
            if agent_setup_done:
                step = 3
            if agent_data.get("onboarding_completed"):
                step = 4

            if agent_data.get("onboarding_completed") and bc_completed:
                try:
                    await self._backfill_onboarding_brief_if_missing(
                        user_id=user_id,
                        profile_data=profile_data,
                        agent_data=agent_data,
                    )
                except Exception as exc:
                    logger.warning(
                        "Onboarding brief backfill failed for %s: %s",
                        user_id,
                        exc,
                    )

            return OnboardingStatus(
                is_completed=agent_data.get("onboarding_completed", False),
                current_step=step,
                business_context_completed=bc_completed,
                preferences_completed=pref_completed,
                agent_setup_completed=agent_setup_done,
                persona=profile_data.get("persona"),
                agent_name=agent_data.get("agent_name"),
            )
        except Exception as e:
            logger.error(f"Error fetching onboarding status: {e}")
            raise

    async def start_onboarding(self, user_id: str) -> bool:
        """Initialize user record if not exists."""
        try:
            profile_data = {
                "user_id": user_id,
                "storage_bucket_id": "user-content",
                "storage_path_prefix": f"{user_id}/",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await execute_async(
                self.supabase.table("users_profile").upsert(
                    profile_data,
                    on_conflict="user_id",
                    ignore_duplicates=True,
                ),
                op_name="onboarding.start.profile_upsert",
            )

            agent_data = {
                "user_id": user_id,
                "onboarding_completed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await execute_async(
                self.supabase.table("user_executive_agents").upsert(
                    agent_data,
                    on_conflict="user_id",
                    ignore_duplicates=True,
                ),
                op_name="onboarding.start.agent_upsert",
            )

            return True
        except Exception as e:
            logger.error(f"Error starting onboarding: {e}")
            raise

    async def submit_business_context(
        self, user_id: str, context: BusinessContextInput
    ) -> bool:
        """Save business context to users_profile."""
        try:
            logger.info(
                f"Received business context for user {user_id}: {context.dict()}"
            )
            await self.start_onboarding(user_id)

            persona = self._determine_persona(context.dict())
            logger.info(
                f"Determined persona {persona.value} for user {user_id} during business context submission"
            )

            await execute_async(
                self.supabase.table("users_profile")
                .update(
                    {
                        "business_context": context.dict(),
                        "persona": persona.value,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("user_id", user_id),
                op_name="onboarding.business_context.update",
            )

            await self._cache.invalidate_user_config(user_id)
            await self._cache.invalidate_user_persona(user_id)
            return True
        except Exception as e:
            logger.error(f"Error submitting business context: {e}")
            raise

    async def submit_preferences(
        self, user_id: str, prefs: UserPreferencesInput
    ) -> bool:
        """Save user preferences to users_profile."""
        try:
            await self.start_onboarding(user_id)
            await execute_async(
                self.supabase.table("users_profile")
                .update(
                    {
                        "preferences": prefs.dict(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("user_id", user_id),
                op_name="onboarding.preferences.update",
            )

            await self._cache.invalidate_user_config(user_id)
            return True
        except Exception as e:
            logger.error(f"Error submitting user preferences: {e}")
            raise

    async def submit_agent_setup(self, user_id: str, setup: "AgentSetupInput") -> bool:
        """Save agent setup configuration."""
        try:
            await self.start_onboarding(user_id)
            current_config = await self._get_user_config(user_id)
            current_config["agent_setup"] = setup.dict()

            await execute_async(
                self.supabase.table("user_executive_agents")
                .update(
                    {
                        "configuration": current_config,
                        "agent_name": setup.agent_name,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("user_id", user_id),
                op_name="onboarding.agent_setup.update",
            )

            await self._cache.invalidate_user_config(user_id)
            self._agent_factory.invalidate_cache(user_id)
            return True
        except Exception as e:
            logger.error(f"Error submitting agent setup: {e}")
            raise

    async def complete_onboarding(self, user_id: str) -> bool:
        """Finalize onboarding, schedule drip emails, and init in-app checklist."""
        try:
            profile = await execute_async(
                self.supabase.table("users_profile")
                .select("business_context, persona, preferences")
                .eq("user_id", user_id)
                .single(),
                op_name="onboarding.complete.profile",
            )
            agent = await execute_async(
                self.supabase.table("user_executive_agents")
                .select("agent_name, configuration")
                .eq("user_id", user_id)
                .single(),
                op_name="onboarding.complete.agent_profile",
            )

            if not profile.data or not profile.data.get("business_context"):
                raise ValueError("Cannot complete onboarding: Missing business context")

            persona = profile.data.get("persona", "startup")
            business_context = profile.data.get("business_context", {}) or {}
            preferences = profile.data.get("preferences", {}) or {}
            agent_row = agent.data or {}
            stored_configuration = agent_row.get("configuration") or {}
            agent_setup = (
                stored_configuration.get("agent_setup")
                if isinstance(stored_configuration, dict)
                else {}
            ) or {}
            agent_name = agent_row.get("agent_name")
            update_data = {
                "onboarding_completed": True,
                "persona": persona,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await execute_async(
                self.supabase.table("user_executive_agents")
                .update(update_data)
                .eq("user_id", user_id),
                op_name="onboarding.complete.agent_update",
            )

            await self._cache.invalidate_user_all(user_id)
            self._agent_factory.invalidate_cache(user_id)

            try:
                await self._sync_onboarding_brief_to_vault(
                    user_id=user_id,
                    persona=persona,
                    business_context=business_context,
                    preferences=preferences,
                    agent_name=agent_name,
                    agent_setup=agent_setup,
                )
            except Exception as e:
                logger.warning(
                    "Onboarding brief sync failed for %s (non-fatal): %s",
                    user_id,
                    e,
                )

            # Schedule post-onboarding drip emails and init checklist (non-blocking)
            try:
                await self._schedule_post_onboarding(user_id, persona, business_context)
            except Exception as e:
                logger.warning(f"Post-onboarding setup failed for {user_id} (non-fatal): {e}")

            return True
        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            raise

    async def _schedule_post_onboarding(
        self, user_id: str, persona: str, business_context: dict
    ) -> None:
        """Schedule drip emails and initialize in-app checklist after onboarding."""
        now = datetime.now(timezone.utc)

        # Get user email from Supabase auth
        email = None
        first_name = None
        try:
            user_response = self.supabase.auth.admin.get_user_by_id(user_id)
            if user_response and user_response.user:
                email = user_response.user.email
        except Exception as e:
            logger.warning(f"Could not fetch auth user for drip scheduling: {e}")

        if not email:
            logger.warning(f"No email found for user {user_id}, skipping drip emails")
        else:
            # Extract first name from business context
            full_name = business_context.get("company_name", "")
            role = business_context.get("role", "")
            # Use role if it looks like a name, otherwise skip
            if role and not any(kw in role.lower() for kw in ["ceo", "cto", "founder", "director", "manager", "vp", "head"]):
                first_name = role.split()[0] if role else None

            # Schedule 3 drip emails: Day 0, Day 3, Day 7
            drip_schedule = [
                {"drip_key": "welcome", "drip_day": 0, "scheduled_at": now.isoformat()},
                {"drip_key": "tips", "drip_day": 3, "scheduled_at": (now + timedelta(days=3)).isoformat()},
                {"drip_key": "checkin", "drip_day": 7, "scheduled_at": (now + timedelta(days=7)).isoformat()},
            ]

            drip_rows = [
                {
                    "user_id": user_id,
                    "email": email,
                    "first_name": first_name,
                    "persona": persona,
                    **drip,
                }
                for drip in drip_schedule
            ]

            try:
                await execute_async(
                    self.supabase.table("onboarding_drip_emails").upsert(
                        drip_rows,
                        on_conflict="user_id,drip_key",
                        ignore_duplicates=True,
                    ),
                    op_name="onboarding.complete.schedule_drips",
                )
                logger.info(f"Scheduled {len(drip_rows)} drip emails for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to schedule drip emails for {user_id}: {e}")

        # Initialize in-app onboarding checklist
        checklist_items = self._get_checklist_items_for_persona(persona)
        try:
            await execute_async(
                self.supabase.table("onboarding_checklist").upsert(
                    {
                        "user_id": user_id,
                        "persona": persona,
                        "items": checklist_items,
                        "updated_at": now.isoformat(),
                    },
                    on_conflict="user_id",
                    ignore_duplicates=True,
                ),
                op_name="onboarding.complete.init_checklist",
            )
            logger.info(f"Initialized onboarding checklist for user {user_id} ({persona})")
        except Exception as e:
            logger.warning(f"Failed to init checklist for {user_id}: {e}")

    @staticmethod
    def _get_checklist_items_for_persona(persona: str) -> list[dict]:
        """Return persona-specific checklist items (matches frontend definitions)."""
        items_map: dict[str, list[dict]] = {
            "solopreneur": [
                {"id": "revenue_strategy", "icon": "💰", "title": "Map your revenue strategy", "description": "Identify your best income opportunities", "completed": False},
                {"id": "brain_dump", "icon": "🧠", "title": "Do a brain dump", "description": "Get all your ideas organized", "completed": False},
                {"id": "weekly_plan", "icon": "📋", "title": "Plan your week", "description": "Create a focused 7-day action plan", "completed": False},
                {"id": "first_workflow", "icon": "⚡", "title": "Run your first workflow", "description": "Automate a repetitive task", "completed": False},
                {"id": "content_piece", "icon": "✍️", "title": "Create your first content piece", "description": "Generate a blog post or social update", "completed": False},
            ],
            "startup": [
                {"id": "growth_experiment", "icon": "🚀", "title": "Design a growth experiment", "description": "Test a hypothesis to accelerate growth", "completed": False},
                {"id": "pitch_review", "icon": "🎯", "title": "Review your pitch", "description": "Sharpen your value proposition", "completed": False},
                {"id": "burn_rate", "icon": "📊", "title": "Check your burn rate", "description": "Understand your runway", "completed": False},
                {"id": "team_update", "icon": "👥", "title": "Write a team update", "description": "Align your team on priorities", "completed": False},
                {"id": "first_workflow", "icon": "⚡", "title": "Run your first workflow", "description": "Automate a repeatable process", "completed": False},
            ],
            "sme": [
                {"id": "dept_health", "icon": "🏥", "title": "Run a department health check", "description": "See how each team is performing", "completed": False},
                {"id": "process_audit", "icon": "⚙️", "title": "Audit your processes", "description": "Find bottlenecks and optimize", "completed": False},
                {"id": "compliance_review", "icon": "🛡️", "title": "Run a compliance review", "description": "Ensure nothing falls through cracks", "completed": False},
                {"id": "kpi_dashboard", "icon": "📊", "title": "Set up KPI tracking", "description": "Define and monitor key metrics", "completed": False},
                {"id": "first_workflow", "icon": "⚡", "title": "Run your first workflow", "description": "Automate a department process", "completed": False},
            ],
            "enterprise": [
                {"id": "stakeholder_briefing", "icon": "📋", "title": "Prepare a stakeholder briefing", "description": "Strategic update for leadership", "completed": False},
                {"id": "risk_assessment", "icon": "⚠️", "title": "Run a risk assessment", "description": "Identify and prioritize risks", "completed": False},
                {"id": "portfolio_review", "icon": "📈", "title": "Review initiative portfolio", "description": "Evaluate portfolio health", "completed": False},
                {"id": "approval_workflow", "icon": "✅", "title": "Set up an approval workflow", "description": "Configure governance controls", "completed": False},
                {"id": "first_workflow", "icon": "⚡", "title": "Run your first workflow", "description": "Automate an enterprise process", "completed": False},
            ],
        }
        return items_map.get(persona, items_map["startup"])

    async def switch_persona(self, user_id: str, new_persona: str) -> bool:
        """Allow user to switch their persona manually."""
        try:
            valid_personas = list(list_persona_policies().keys())
            if new_persona not in valid_personas:
                raise ValueError(
                    f"Invalid persona: {new_persona}. Must be one of {valid_personas}"
                )

            logger.info(f"User {user_id} switching persona to {new_persona}")

            await execute_async(
                self.supabase.table("users_profile")
                .update(
                    {
                        "persona": new_persona,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("user_id", user_id),
                op_name="onboarding.persona.profile_update",
            )
            await execute_async(
                self.supabase.table("user_executive_agents")
                .update(
                    {
                        "persona": new_persona,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("user_id", user_id),
                op_name="onboarding.persona.agent_update",
            )

            await self._cache.invalidate_user_persona(user_id)
            await self._cache.invalidate_user_config(user_id)
            self._agent_factory.invalidate_cache(user_id)
            return True
        except Exception as e:
            logger.error(f"Error switching persona for user {user_id}: {e}")
            raise

    async def _get_user_config(self, user_id: str) -> dict:
        """Construct the legacy config shape from profile and agent rows."""
        cached = await self._cache.get_user_config(user_id)
        if cached.found and isinstance(cached.value, dict):
            return cached.value

        profile = await execute_async(
            self.supabase.table("users_profile")
            .select("*")
            .eq("user_id", user_id)
            .single(),
            op_name="onboarding.config.profile",
        )
        agent = await execute_async(
            self.supabase.table("user_executive_agents")
            .select("configuration")
            .eq("user_id", user_id)
            .single(),
            op_name="onboarding.config.agent",
        )

        config: dict = {}
        if profile.data:
            config["business_context"] = profile.data.get("business_context")
            config["preferences"] = profile.data.get("preferences")

        if agent.data and agent.data.get("configuration"):
            config["agent_setup"] = (agent.data.get("configuration") or {}).get(
                "agent_setup"
            )

        await self._cache.set_user_config(user_id, config)
        return config

    async def get_user_persona(self, user_id: str) -> str | None:
        """Get user persona with caching from users_profile."""
        cached = await self._cache.get_user_persona(user_id)
        if cached.found:
            return cached.value

        try:
            response = await execute_async(
                self.supabase.table("users_profile")
                .select("persona")
                .eq("user_id", user_id)
                .single(),
                op_name="onboarding.persona.get",
            )
            if response.data:
                persona = response.data.get("persona")
                if persona:
                    await self._cache.set_user_persona(user_id, persona)
                return persona
        except Exception as e:
            logger.warning(f"Failed to get user persona for {user_id}: {e}")
            return None
        return None


_service_instance = None


def get_user_onboarding_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = UserOnboardingService()
    return _service_instance
