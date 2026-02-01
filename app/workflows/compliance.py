# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Compliance & Risk Workflows (Category 7).

This module implements 4 workflow agents for compliance management:
37. ComplianceAuditPipeline - Iterative compliance verification
38. RiskAssessmentPipeline - Business risk evaluation
39. PolicyReviewPipeline - Policy update and distribution
40. VendorCompliancePipeline - Third-party compliance check

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, LoopAgent

from app.agents.specialized_agents import (
    create_strategic_agent,
    create_financial_agent,
    create_operations_agent,
    create_hr_agent,
    create_compliance_agent,
)


# =============================================================================
# 37. ComplianceAuditPipeline
# =============================================================================

def create_compliance_audit_pipeline() -> LoopAgent:
    """Create ComplianceAuditPipeline with fresh agent instances."""
    compliance_check = SequentialAgent(
        name="ComplianceCheck",
        description="Single iteration of compliance verification",
        sub_agents=[
            create_compliance_agent(),
            create_operations_agent(),
        ],
    )
    return LoopAgent(
        name="ComplianceAuditPipeline",
        description="Iterative compliance verification until all criteria pass",
        sub_agents=[compliance_check],
        max_iterations=5,
    )


# =============================================================================
# 38. RiskAssessmentPipeline
# =============================================================================

def create_risk_assessment_pipeline() -> SequentialAgent:
    """Create RiskAssessmentPipeline with fresh agent instances."""
    return SequentialAgent(
        name="RiskAssessmentPipeline",
        description="Business risk evaluation through compliance, financial, and strategic analysis",
        sub_agents=[
            create_compliance_agent(),
            create_financial_agent(),
            create_strategic_agent(),
        ],
    )


# =============================================================================
# 39. PolicyReviewPipeline
# =============================================================================

def create_policy_review_pipeline() -> SequentialAgent:
    """Create PolicyReviewPipeline with fresh agent instances."""
    return SequentialAgent(
        name="PolicyReviewPipeline",
        description="Policy update and distribution through compliance and HR channels",
        sub_agents=[
            create_compliance_agent(),
            create_hr_agent(),
        ],
    )


# =============================================================================
# 40. VendorCompliancePipeline
# =============================================================================

def create_vendor_compliance_pipeline() -> SequentialAgent:
    """Create VendorCompliancePipeline with fresh agent instances."""
    return SequentialAgent(
        name="VendorCompliancePipeline",
        description="Third-party vendor compliance verification",
        sub_agents=[
            create_compliance_agent(),
            create_operations_agent(),
            create_financial_agent(),
        ],
    )


# =============================================================================
# Exports
# =============================================================================

COMPLIANCE_WORKFLOW_FACTORIES = {
    "ComplianceAuditPipeline": create_compliance_audit_pipeline,
    "RiskAssessmentPipeline": create_risk_assessment_pipeline,
    "PolicyReviewPipeline": create_policy_review_pipeline,
    "VendorCompliancePipeline": create_vendor_compliance_pipeline,
}

__all__ = [
    "create_compliance_audit_pipeline",
    "create_risk_assessment_pipeline",
    "create_policy_review_pipeline",
    "create_vendor_compliance_pipeline",
    "COMPLIANCE_WORKFLOW_FACTORIES",
]
