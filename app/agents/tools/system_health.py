# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""System health tool for the Executive agent.

Provides a user-facing view of agent system health by querying
the telemetry service for agent performance, tool usage, and error patterns.
"""

import logging
from datetime import datetime, timezone

from app.services.telemetry import get_telemetry_service

logger = logging.getLogger(__name__)


async def get_system_health(window_hours: int = 24) -> dict:
    """Get a summary of agent system health.

    Shows agent success rates, most-used tools, error hotspots,
    and recommendations. Use when users ask about system status,
    performance, or "how is the system doing?"

    Args:
        window_hours: How many hours back to analyze (default 24).

    Returns:
        Dictionary with agent_health, tool_hotspots, error_patterns,
        and recommendations sections.
    """
    try:
        service = get_telemetry_service()

        # Get health for all known agents
        agent_names = [
            "ExecutiveAgent",
            "FinancialAnalysisAgent",
            "ContentCreationAgent",
            "StrategicPlanningAgent",
            "SalesIntelligenceAgent",
            "MarketingAutomationAgent",
            "OperationsOptimizationAgent",
            "HRRecruitmentAgent",
            "ComplianceRiskAgent",
            "CustomerSupportAgent",
            "DataAnalysisAgent",
        ]

        agent_health = []
        for name in agent_names:
            try:
                health = await service.get_agent_health(name, window_hours)
                if health.total_calls > 0:
                    agent_health.append(
                        {
                            "agent": health.agent_name,
                            "total_calls": health.total_calls,
                            "success_rate": round(health.success_rate * 100, 1),
                            "avg_duration_ms": round(health.avg_duration_ms)
                            if health.avg_duration_ms
                            else None,
                            "errors": health.error_count,
                        }
                    )
            except Exception:
                continue

        # Get tool usage
        tool_usage = []
        try:
            usage = await service.get_tool_usage(window_hours)
            tool_usage = [
                {
                    "tool": u.tool_name,
                    "agent": u.agent_name,
                    "calls": u.call_count,
                    "errors": u.error_count,
                    "avg_ms": round(u.avg_duration_ms) if u.avg_duration_ms else None,
                }
                for u in usage[:10]  # Top 10
            ]
        except Exception:
            pass

        # Generate recommendations
        recommendations = []
        for ah in agent_health:
            if ah["success_rate"] < 80:
                recommendations.append(
                    f"{ah['agent']} has a {ah['success_rate']}% success rate — investigate error patterns"
                )
            if ah.get("avg_duration_ms") and ah["avg_duration_ms"] > 30000:
                recommendations.append(
                    f"{ah['agent']} averaging {ah['avg_duration_ms']}ms — consider optimizing or splitting tasks"
                )

        for tu in tool_usage:
            if tu["errors"] > 0 and tu["calls"] > 0:
                error_rate = tu["errors"] / tu["calls"] * 100
                if error_rate > 20:
                    recommendations.append(
                        f"Tool '{tu['tool']}' has {error_rate:.0f}% error rate — check configuration"
                    )

        if not agent_health and not tool_usage:
            return {
                "status": "no_data",
                "message": f"No telemetry data found for the last {window_hours} hours. The system is running but hasn't processed any requests in this window.",
                "window_hours": window_hours,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "status": "healthy"
            if all(ah["success_rate"] >= 80 for ah in agent_health)
            else "degraded",
            "window_hours": window_hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_health": sorted(
                agent_health, key=lambda x: x["total_calls"], reverse=True
            ),
            "tool_hotspots": tool_usage,
            "recommendations": recommendations
            if recommendations
            else ["All systems operating normally"],
        }

    except Exception as exc:
        logger.warning("Failed to get system health: %s", exc)
        return {
            "status": "unavailable",
            "message": f"Could not retrieve system health: {exc}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


SYSTEM_HEALTH_TOOLS = [get_system_health]
