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

"""Knowledge & Brain Dump Workflows (Category 10).

This module implements 4 workflow agents for knowledge management:
50. BrainDumpProcessingPipeline - Process and categorize brain dumps
51. KnowledgeExtractionPipeline - Extract insights from documents
52. IdeaValidationPipeline - Validate user ideas across dimensions
53. KnowledgeBaseIngestionPipeline - Process documents/URLs for knowledge base

Architecture Note: Uses factory functions to create fresh agent instances for each
workflow to avoid ADK's single-parent constraint.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

from app.agents.specialized_agents import (
    create_strategic_agent,
    create_content_agent,
    create_data_agent,
    create_financial_agent,
    create_compliance_agent,
)


# =============================================================================
# 50. BrainDumpProcessingPipeline
# =============================================================================

def create_brain_dump_processing_pipeline() -> SequentialAgent:
    """Create BrainDumpProcessingPipeline with fresh agent instances."""
    return SequentialAgent(
        name="BrainDumpProcessingPipeline",
        description="Process and categorize brain dumps into actionable insights",
        sub_agents=[
            create_content_agent(),
            create_data_agent(),
            create_strategic_agent(),
        ],
    )


# =============================================================================
# 51. KnowledgeExtractionPipeline
# =============================================================================

def create_knowledge_extraction_pipeline() -> SequentialAgent:
    """Create KnowledgeExtractionPipeline with fresh agent instances."""
    return SequentialAgent(
        name="KnowledgeExtractionPipeline",
        description="Extract insights from documents with data and content analysis",
        sub_agents=[
            create_data_agent(),
            create_content_agent(),
        ],
    )


# =============================================================================
# 52. IdeaValidationPipeline (Consensus Pattern)
# =============================================================================

def create_idea_validation_pipeline() -> SequentialAgent:
    """Create IdeaValidationPipeline with fresh agent instances."""
    idea_validation_parallel = ParallelAgent(
        name="IdeaValidationConsensus",
        description="Parallel idea validation from strategic, financial, and data perspectives",
        sub_agents=[
            create_strategic_agent(),
            create_financial_agent(),
            create_data_agent(),
        ],
    )
    return SequentialAgent(
        name="IdeaValidationPipeline",
        description="Validate user ideas across dimensions with multi-perspective consensus",
        sub_agents=[idea_validation_parallel],
    )


# =============================================================================
# 53. KnowledgeBaseIngestionPipeline
# =============================================================================

def create_knowledge_base_ingestion_pipeline() -> LoopAgent:
    """Create KnowledgeBaseIngestionPipeline with fresh agent instances."""
    ingestion_process = SequentialAgent(
        name="IngestionProcess",
        description="Single iteration of content extraction and validation",
        sub_agents=[
            create_data_agent(),
            create_content_agent(),
            create_compliance_agent(),
        ],
    )
    return LoopAgent(
        name="KnowledgeBaseIngestionPipeline",
        description="Process documents, URLs, Google Drive files for knowledge base with validation loop",
        sub_agents=[ingestion_process],
        max_iterations=3,
    )


# =============================================================================
# Exports
# =============================================================================

KNOWLEDGE_WORKFLOW_FACTORIES = {
    "BrainDumpProcessingPipeline": create_brain_dump_processing_pipeline,
    "KnowledgeExtractionPipeline": create_knowledge_extraction_pipeline,
    "IdeaValidationPipeline": create_idea_validation_pipeline,
    "KnowledgeBaseIngestionPipeline": create_knowledge_base_ingestion_pipeline,
}

__all__ = [
    "create_brain_dump_processing_pipeline",
    "create_knowledge_extraction_pipeline",
    "create_idea_validation_pipeline",
    "create_knowledge_base_ingestion_pipeline",
    "KNOWLEDGE_WORKFLOW_FACTORIES",
]
