# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for plain-English persona-aware budget pacing messages."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# format_budget_pacing_message tests
# ---------------------------------------------------------------------------


class TestFormatBudgetPacingMessage:
    """format_budget_pacing_message returns persona-appropriate language."""

    def _call(self, **kwargs):
        """Import and call format_budget_pacing_message with defaults."""
        from app.services.ad_performance_sync_service import (
            format_budget_pacing_message,
        )

        defaults = {
            "platform": "Google Ads",
            "daily_avg": 50.0,
            "monthly_cap": 1000.0,
            "month_spend": 500.0,
            "projected_total": 1230.0,
            "projected_cap_date": "April 20",
            "persona": "solopreneur",
        }
        defaults.update(kwargs)
        return format_budget_pacing_message(**defaults)

    def test_solopreneur_casual_language(self):
        """Solopreneur persona gets casual, encouraging language."""
        msg = self._call(persona="solopreneur")
        assert "heads up" in msg.lower() or "hey" in msg.lower() or "running hot" in msg.lower()
        # Should NOT sound corporate
        assert "expenditure" not in msg.lower()

    def test_enterprise_formal_language(self):
        """Enterprise persona gets formal, data-driven language."""
        msg = self._call(persona="enterprise")
        assert (
            "budget alert" in msg.lower()
            or "expenditure" in msg.lower()
            or "allocation" in msg.lower()
        )
        # Should NOT sound casual
        assert "heads up" not in msg.lower()

    def test_startup_balanced_tone(self):
        """Startup persona gets balanced, action-oriented language."""
        msg = self._call(persona="startup")
        assert (
            "pacing" in msg.lower()
            or "budget" in msg.lower()
            or "on track" in msg.lower()
            or "overshoot" in msg.lower()
            or "above target" in msg.lower()
        )

    def test_sme_professional_tone(self):
        """SME persona gets professional, detail-oriented language."""
        msg = self._call(persona="sme")
        assert (
            "pacing" in msg.lower()
            or "trending" in msg.lower()
            or "alert" in msg.lower()
        )

    def test_message_includes_all_data_points(self):
        """Message includes platform, daily avg, monthly cap, projected total, and cap date."""
        msg = self._call(
            platform="Google Ads",
            daily_avg=50.0,
            monthly_cap=1000.0,
            month_spend=500.0,
            projected_total=1230.0,
            projected_cap_date="April 20",
            persona="solopreneur",
        )
        assert "Google Ads" in msg
        assert "$50" in msg or "50" in msg
        assert "$1,000" in msg or "1,000" in msg or "1000" in msg
        assert "$500" in msg or "500" in msg

    def test_severe_overshoot_recommends_pausing(self):
        """Overshoot >50% recommends pausing low-performing campaigns."""
        msg = self._call(
            monthly_cap=1000.0,
            projected_total=1600.0,  # 60% overshoot
        )
        assert "paus" in msg.lower()

    def test_moderate_overshoot_recommends_review(self):
        """Overshoot 20-50% recommends reviewing budgets."""
        msg = self._call(
            monthly_cap=1000.0,
            projected_total=1300.0,  # 30% overshoot
        )
        assert "review" in msg.lower()

    def test_mild_overshoot_recommends_monitoring(self):
        """Overshoot 0-20% recommends keeping an eye on spending."""
        msg = self._call(
            monthly_cap=1000.0,
            projected_total=1100.0,  # 10% overshoot
        )
        assert "eye" in msg.lower() or "adjust" in msg.lower() or "monitor" in msg.lower()

    def test_default_persona_is_solopreneur(self):
        """When persona is not provided, defaults to solopreneur tone."""
        from app.services.ad_performance_sync_service import (
            format_budget_pacing_message,
        )

        msg = format_budget_pacing_message(
            platform="Google Ads",
            daily_avg=50.0,
            monthly_cap=1000.0,
            month_spend=500.0,
            projected_total=1230.0,
            projected_cap_date="April 20",
        )
        # Should use casual tone (solopreneur default)
        assert "expenditure" not in msg.lower()

    def test_spend_summary_included(self):
        """Message always includes how much has been spent of the monthly budget."""
        msg = self._call(month_spend=750.0, monthly_cap=2000.0)
        assert "$750" in msg or "750" in msg
        assert "$2,000" in msg or "2,000" in msg or "2000" in msg
