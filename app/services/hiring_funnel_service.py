# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""HiringFunnelService - Hiring funnel aggregation and visualization data.

Aggregates candidate counts by hiring stage for each open position,
computes conversion rates between stages, and provides summary views
across all active jobs.
"""

from __future__ import annotations

import logging

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Ordered funnel stages (excluding rejected which is tracked separately)
FUNNEL_STAGES = ["applied", "screening", "interviewing", "offer", "hired"]


class HiringFunnelService(BaseService):
    """Service for aggregating hiring funnel data per job position.

    Queries recruitment_candidates grouped by status and computes
    stage counts and conversion rates for visualization.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the hiring funnel service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._candidates_table = "recruitment_candidates"
        self._jobs_table = "recruitment_jobs"

    async def get_funnel_for_job(
        self, job_id: str, user_id: str | None = None
    ) -> dict:
        """Get the hiring funnel data for a specific job.

        Queries recruitment_candidates grouped by status for the given job_id,
        returns stage counts in funnel order and conversion rates between stages.

        Args:
            job_id: The job posting ID.
            user_id: Optional user ID for scoping (falls back to request context).

        Returns:
            Dictionary with job_id, stages list, rejected count, total,
            and conversion_rates between adjacent stages.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client

        query = (
            client.table(self._candidates_table)
            .select("status")
            .eq("job_id", job_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query)
        candidates = response.data or []

        return self._build_funnel(job_id, candidates)

    async def get_funnel_summary(self, user_id: str | None = None) -> list[dict]:
        """Get funnel summaries for all open/published jobs.

        Queries all published jobs, then for each job aggregates
        candidate counts by stage.

        Args:
            user_id: Optional user ID for scoping.

        Returns:
            List of dicts with job_id, title, department, and funnel data.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client

        # Get open jobs
        jobs_query = (
            client.table(self._jobs_table)
            .select("id, title, department")
            .in_("status", ["published", "draft"])
        )
        if not self.is_authenticated and effective_user_id:
            jobs_query = jobs_query.eq("user_id", effective_user_id)

        jobs_response = await execute_async(jobs_query)
        jobs = jobs_response.data or []

        results = []
        for job in jobs:
            job_id = job["id"]
            # Get candidates for this job
            cand_query = (
                client.table(self._candidates_table)
                .select("status")
                .eq("job_id", job_id)
            )
            if not self.is_authenticated and effective_user_id:
                cand_query = cand_query.eq("user_id", effective_user_id)

            cand_response = await execute_async(cand_query)
            candidates = cand_response.data or []

            funnel = self._build_funnel(job_id, candidates)
            results.append(
                {
                    "job_id": job_id,
                    "title": job.get("title", ""),
                    "department": job.get("department", ""),
                    "funnel": funnel,
                }
            )

        return results

    @staticmethod
    def _build_funnel(job_id: str, candidates: list[dict]) -> dict:
        """Build funnel data from a list of candidate status records.

        Args:
            job_id: The job posting ID.
            candidates: List of dicts with at least a 'status' key.

        Returns:
            Funnel dict with stages, rejected count, total, conversion_rates.
        """
        # Count candidates per status
        status_counts: dict[str, int] = {}
        for candidate in candidates:
            status = candidate.get("status", "applied")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Build ordered stages
        stages = []
        for stage_name in FUNNEL_STAGES:
            stages.append({"name": stage_name, "count": status_counts.get(stage_name, 0)})

        rejected = status_counts.get("rejected", 0)
        total = sum(s["count"] for s in stages) + rejected

        # Compute conversion rates between adjacent stages
        conversion_rates: dict[str, float] = {}
        for i in range(len(FUNNEL_STAGES) - 1):
            current_stage = FUNNEL_STAGES[i]
            next_stage = FUNNEL_STAGES[i + 1]
            current_count = status_counts.get(current_stage, 0)
            next_count = status_counts.get(next_stage, 0)

            rate_key = f"{current_stage}_to_{next_stage}"
            if current_count > 0:
                conversion_rates[rate_key] = next_count / current_count
            else:
                conversion_rates[rate_key] = 0

        return {
            "job_id": job_id,
            "stages": stages,
            "rejected": rejected,
            "total": total,
            "conversion_rates": conversion_rates,
        }
