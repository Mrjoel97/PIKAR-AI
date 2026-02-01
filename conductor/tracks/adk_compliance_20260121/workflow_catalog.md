# Pikar AI Workflow Catalog - Complete Design Document

**Status:** PENDING APPROVAL  
**Version:** 1.1  
**Date:** 2026-01-21  
**Total Workflows:** 53 + Dynamic Workflow Generator

---

## Overview

This document defines 52 ADK-compliant workflow agents mapped to PRD user journeys, Agent-Eco-System patterns, and all 11 system agents. Each workflow uses ADK patterns:

- **SequentialAgent** - Linear multi-step execution
- **ParallelAgent** - Concurrent execution
- **LoopAgent** - Iterative refinement with EscalationChecker
- **Consensus Pattern** - Multiple agents analyze, one synthesizes

---

## Category 1: Initiative & Project Lifecycle (6 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 1 | **InitiativeIdeationPipeline** | Sequential | Strategic → Content → Data | Brainstorm and validate initiative ideas |
| 2 | **InitiativeValidationPipeline** | Parallel + Sequential | [Data + Financial + Strategic] → Executive | Multi-perspective feasibility analysis |
| 3 | **InitiativeBuildPipeline** | Sequential | Strategic → Operations → HR | Plan resources and execution timeline |
| 4 | **InitiativeTestPipeline** | Loop | Operations → Data → Compliance (loop until pass) | Iterative quality and compliance check |
| 5 | **InitiativeLaunchPipeline** | Sequential + Parallel | [Marketing + Sales + Content] → Executive | Coordinated go-to-market execution |
| 6 | **InitiativeScalePipeline** | Sequential | Data → Financial → Strategic → Operations | Growth optimization post-launch |

---

## Category 2: Product & Service Creation (5 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 7 | **ProductIdeationPipeline** | Sequential | Strategic → Data → Content | Market-informed product concept |
| 8 | **ProductValidationPipeline** | Consensus | Financial + Data + Strategic → Executive | ROI and market viability assessment |
| 9 | **ServiceDesignPipeline** | Sequential | Strategic → Operations → Financial | Service blueprint and pricing |
| 10 | **ProductLaunchPipeline** | Sequential + Parallel | Strategic → [Marketing + Sales + Content] → Executive | Full product launch coordination |
| 11 | **ProductIterationPipeline** | Loop | Data → Content → Strategic (loop on feedback) | Continuous product improvement |

---

## Category 3: Lead Generation & Sales (7 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 12 | **LeadGenerationPipeline** | Sequential | Marketing → Content → Data | Generate and qualify leads |
| 13 | **LeadScoringPipeline** | Sequential | Data → Sales → Financial | Score and prioritize leads |
| 14 | **LeadNurturingPipeline** | Loop | Content → Sales → Data (loop until converted) | Automated lead nurture sequence |
| 15 | **SalesFunnelCreationPipeline** | Sequential | Strategic → Marketing → Sales → Content | Build complete sales funnel |
| 16 | **DealQualificationPipeline** | Conditional | Sales → IF score>80: Financial, IF <50: Support | Smart deal routing |
| 17 | **OutreachSequencePipeline** | Sequential | Sales → Content → Marketing | Multi-touch outreach campaign |
| 18 | **CustomerJourneyPipeline** | Sequential | Data → Marketing → Sales → Support | Full customer lifecycle mapping |

---

## Category 4: Marketing & Content (8 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 19 | **ContentCampaignPipeline** | Sequential | Strategic → Content → Marketing | End-to-end content campaign |
| 20 | **EmailSequencePipeline** | Sequential | Marketing → Content → Data | Automated email drip campaigns |
| 21 | **SocialMediaPipeline** | Sequential | Content → Marketing → Data | Social content creation & scheduling |
| 22 | **NewsletterPipeline** | Sequential | Content → Marketing | Weekly/monthly newsletter creation |
| 23 | **BlogContentPipeline** | Sequential | Strategic → Content → Data | SEO-optimized blog creation |
| 24 | **BrandVoicePipeline** | Sequential | Content → Marketing → Strategic | Establish and refine brand voice |
| 25 | **CampaignAnalyticsPipeline** | Sequential | Data → Marketing → Executive | Campaign performance analysis |
| 26 | **ABTestingPipeline** | Loop | Marketing → Data → Content (loop until winner) | Iterative A/B optimization |

---

## Category 5: Goal Setting & Monitoring (4 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 27 | **OKRCreationPipeline** | Sequential | Strategic → Data → Executive | Create objectives and key results |
| 28 | **GoalTrackingPipeline** | Loop | Data → Strategic → Executive (weekly loop) | Continuous goal progress monitoring |
| 29 | **KPIDashboardPipeline** | Parallel | [Data + Financial + Sales] → Executive | Real-time KPI aggregation |
| 30 | **QuarterlyReviewPipeline** | Sequential | Data → Financial → Strategic → Executive | Quarterly business review |

---

## Category 6: Evaluation & Analysis (6 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 31 | **BusinessEvaluationPipeline** | Consensus | Financial + Data + Strategic → Executive | 360° business health assessment |
| 32 | **ProjectEvaluationPipeline** | Sequential | Data → Operations → Financial | Post-project analysis |
| 33 | **UserActivityAnalysisPipeline** | Sequential | Data → Marketing → Sales | User behavior insights |
| 34 | **GrowthEvaluationPipeline** | Sequential | Data → Financial → Strategic | Growth trajectory analysis |
| 35 | **CompetitorAnalysisPipeline** | Sequential | Strategic → Data → Sales | Competitive intelligence |
| 36 | **MarketResearchPipeline** | Parallel + Sequential | [Data + Strategic] → Marketing → Content | Comprehensive market analysis |

---

## Category 7: Compliance & Risk (4 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 37 | **ComplianceAuditPipeline** | Loop | Compliance → Operations (loop until pass) | Iterative compliance verification |
| 38 | **RiskAssessmentPipeline** | Sequential | Compliance → Financial → Strategic | Business risk evaluation |
| 39 | **PolicyReviewPipeline** | Sequential | Compliance → HR → Executive | Policy update and distribution |
| 40 | **VendorCompliancePipeline** | Sequential | Compliance → Operations → Financial | Third-party compliance check |

---

## Category 8: Team & HR (4 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 41 | **TeamTrainingPipeline** | Sequential | HR → Content → Operations | Training program creation |
| 42 | **RecruitmentPipeline** | Sequential | HR → Data → Executive | End-to-end hiring workflow |
| 43 | **OnboardingPipeline** | Sequential | HR → Content → Operations | New employee onboarding |
| 44 | **PerformanceReviewPipeline** | Sequential | HR → Data → Executive | Employee performance analysis |

---

## Category 9: Documentation & Reporting (5 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 45 | **BusinessDocumentationPipeline** | Sequential | Strategic → Content → Compliance | Business process documentation |
| 46 | **ProjectDocumentationPipeline** | Sequential | Operations → Content → Data | Project documentation |
| 47 | **ReportCreationPipeline** | Parallel + Sequential | [Data + Financial] → Content → Executive | Custom report generation |
| 48 | **BoardPresentationPipeline** | Parallel | [Data + Financial + Strategic] → Executive | Board meeting preparation |
| 49 | **WeeklyBriefingPipeline** | Sequential | Data → Strategic → Executive | Automated weekly executive brief |

---

## Category 10: Knowledge & Brain Dump (4 Workflows)

| # | Workflow | Pattern | Agents | Description |
|---|----------|---------|--------|-------------|
| 50 | **BrainDumpProcessingPipeline** | Sequential | Content → Data → Strategic | Process and categorize brain dumps |
| 51 | **KnowledgeExtractionPipeline** | Sequential | Data → Content → Executive | Extract insights from documents |
| 52 | **IdeaValidationPipeline** | Consensus | [Strategic + Financial + Data] → Executive | Validate user ideas across dimensions |
| 53 | **KnowledgeBaseIngestionPipeline** | Sequential + Loop | Data → Content → Compliance (loop for validation) | Process documents, links, Google Drive files for knowledge base |

### KnowledgeBaseIngestionPipeline Details

**Purpose:** Process and classify user-uploaded knowledge (documents, URLs, Google Drive files) for agent access.

**Flow:**
```
User uploads document/link/Google Drive file
    ↓
Data Agent: Extract content (PDF parsing, web scraping, Drive API)
    ↓
Content Agent: Chunk and classify content
    ↓
Data Agent: Generate embeddings (text-embedding-004)
    ↓
Compliance Agent: Validate content quality (loop if fails)
    ↓
Store in Knowledge Vault (embeddings table)
    ↓
Available to all agents via RAG search
```

**Supported Sources:**
- PDF/DOC documents
- Website URLs (with content extraction)
- Google Drive files (Docs, Sheets, Slides)
- Plain text/markdown
- Audio transcriptions

---

## Category 11: Dynamic Workflow Generation (SPECIAL)

| # | Workflow | Pattern | Description |
|---|----------|---------|-------------|
| 53 | **DynamicWorkflowGenerator** | Custom BaseAgent | Creates new workflows from user requests |

### How DynamicWorkflowGenerator Works

```python
class DynamicWorkflowGenerator(BaseAgent):
    """
    Analyzes user request and dynamically composes a workflow
    from available agents using the appropriate pattern.
    """
    async def _run_async_impl(self, ctx):
        user_request = ctx.session.state.get("user_request")
        
        # 1. Analyze intent → determine required agents
        # 2. Select pattern (Sequential/Parallel/Loop/Consensus)
        # 3. Construct workflow dynamically
        # 4. Execute and return results
```

This allows the system to create **unlimited custom workflows** based on any user inquiry.

---

## ADK Pattern Usage Summary

| Pattern | Count | Use Case |
|---------|-------|----------|
| **SequentialAgent** | 35 | Linear step-by-step workflows |
| **ParallelAgent** | 10 | Concurrent data gathering |
| **LoopAgent** | 5 | Iterative refinement |
| **Consensus** | 4 | Multi-perspective analysis |
| **Conditional** | 1 | Dynamic routing |

---

## Agent Coverage

All 11 agents are used across workflows:

| Agent | Workflow Count |
|-------|----------------|
| Executive | 22 (synthesis/coordination) |
| Strategic Planning | 18 |
| Data Analysis | 20 |
| Content Creation | 16 |
| Marketing Automation | 14 |
| Financial Analysis | 12 |
| Sales Intelligence | 10 |
| Operations Optimization | 10 |
| Compliance & Risk | 6 |
| HR & Recruitment | 6 |
| Customer Support | 4 |

---

## Next Steps (Awaiting Approval)

1. Create `app/workflows/` directory structure
2. Implement each workflow as ADK workflow agent
3. Implement DynamicWorkflowGenerator
4. Add workflow tests
5. Update Conductor plan.md

**APPROVAL REQUIRED BEFORE IMPLEMENTATION**
