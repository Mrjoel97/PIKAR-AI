# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Knowledge Injection Tools for Executive Agent.

These tools allow the Executive Agent to automatically ingest user business
context and knowledge into the Knowledge Vault RAG system.

All tools are async because the underlying ingestion functions are async,
and Google ADK runs tools inside an async event loop. Using sync wrappers
(loop.run_until_complete) fails with "This event loop is already running".
"""

import logging

logger = logging.getLogger(__name__)


async def add_business_knowledge(
    content: str, title: str, category: str | None = None
) -> dict:
    """Add business knowledge or context to the Knowledge Vault.

    Use this tool when the user wants to:
    - Add information about their company, products, or services
    - Store business context for future reference
    - Train agents with company-specific knowledge
    - Share policies, procedures, or guidelines

    Args:
        content: The knowledge content to add (e.g., company description,
                 product info, policies, FAQs, or any business context).
        title: A short descriptive title for this knowledge item.
        category: Optional category like 'company_info', 'product', 'policy',
                  'faq', 'process', 'competitor', or 'market'.

    Returns:
        Dictionary with ingestion results including success status and chunk count.

    Example:
        add_business_knowledge(
            content="Our company Acme Corp was founded in 2020. We sell AI tools to SMBs.",
            title="Company Overview",
            category="company_info"
        )
    """
    from app.rag.knowledge_vault import ingest_brain_dump

    # Build metadata
    metadata = {}
    if category:
        metadata["category"] = category

    try:
        result = await ingest_brain_dump(
            content=content, title=title, metadata=metadata
        )

        if result.get("success"):
            return {
                "success": True,
                "message": f"Successfully added '{title}' to Knowledge Vault. "
                f"Created {result.get('chunk_count', 0)} searchable chunks.",
                "chunk_count": result.get("chunk_count", 0),
                "embedding_ids": result.get("embedding_ids", []),
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error during ingestion"),
            }
    except Exception as e:
        logger.error(f"Failed to add knowledge '{title}': {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to add knowledge: {e!s}",
            "hint": "Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.",
        }


async def add_product_info(
    product_name: str,
    description: str,
    pricing: str | None = None,
    features: str | None = None,
    target_audience: str | None = None,
) -> dict:
    """Add product or service information to the Knowledge Vault.

    Use this tool when the user wants to add details about their products
    or services so agents can provide accurate information.

    Args:
        product_name: Name of the product or service.
        description: Description of what the product does.
        pricing: Optional pricing information (e.g., "$99/month", "Free tier available").
        features: Optional key features (e.g., "AI-powered, 24/7 support, API access").
        target_audience: Optional target audience description.

    Returns:
        Dictionary with ingestion results.
    """
    # Build structured content
    content_parts = [
        f"Product/Service: {product_name}",
        f"Description: {description}",
    ]

    if pricing:
        content_parts.append(f"Pricing: {pricing}")
    if features:
        content_parts.append(f"Features: {features}")
    if target_audience:
        content_parts.append(f"Target Audience: {target_audience}")

    content = "\n".join(content_parts)

    return await add_business_knowledge(
        content=content, title=f"Product: {product_name}", category="product"
    )


async def add_company_info(
    company_name: str,
    description: str,
    mission: str | None = None,
    industry: str | None = None,
    founded_year: str | None = None,
    employee_count: str | None = None,
) -> dict:
    """Add company information to the Knowledge Vault.

    Use this tool when the user wants to add details about their company
    so agents understand the business context.

    Args:
        company_name: Name of the company.
        description: Brief company description.
        mission: Optional company mission statement.
        industry: Optional industry (e.g., "SaaS", "Healthcare", "Finance").
        founded_year: Optional year founded.
        employee_count: Optional number of employees.

    Returns:
        Dictionary with ingestion results.
    """
    content_parts = [
        f"Company Name: {company_name}",
        f"Description: {description}",
    ]

    if mission:
        content_parts.append(f"Mission: {mission}")
    if industry:
        content_parts.append(f"Industry: {industry}")
    if founded_year:
        content_parts.append(f"Founded: {founded_year}")
    if employee_count:
        content_parts.append(f"Employees: {employee_count}")

    content = "\n".join(content_parts)

    return await add_business_knowledge(
        content=content, title=f"Company: {company_name}", category="company_info"
    )


async def add_process_or_policy(
    title: str, content: str, process_type: str = "policy"
) -> dict:
    """Add a business process, SOP, or policy to the Knowledge Vault.

    Use this tool when the user wants to document:
    - Standard Operating Procedures (SOPs)
    - Company policies
    - Workflows and processes
    - Guidelines and best practices

    Args:
        title: Title of the process or policy.
        content: The full content of the process/policy document.
        process_type: Type - 'policy', 'sop', 'workflow', or 'guideline'.

    Returns:
        Dictionary with ingestion results.
    """
    return await add_business_knowledge(
        content=content, title=title, category=process_type
    )


async def add_faq(question: str, answer: str) -> dict:
    """Add a frequently asked question and answer to the Knowledge Vault.

    Use this tool when the user wants to add Q&A pairs that agents
    can use to answer common questions.

    Args:
        question: The frequently asked question.
        answer: The answer to the question.

    Returns:
        Dictionary with ingestion results.
    """
    content = f"Question: {question}\n\nAnswer: {answer}"

    return await add_business_knowledge(
        content=content, title=f"FAQ: {question[:50]}...", category="faq"
    )


def list_knowledge() -> dict:
    """List all knowledge items in the Knowledge Vault.

    Use this tool to show the user what knowledge has been added.

    Returns:
        Dictionary with list of knowledge items.
    """
    from app.rag.knowledge_vault import list_agent_content

    try:
        items = list_agent_content(limit=50)

        if not items:
            return {
                "success": True,
                "message": "No knowledge items found. Use add_business_knowledge to add content.",
                "items": [],
            }

        # Format for display
        formatted_items = []
        for item in items:
            formatted_items.append(
                {
                    "id": item.get("id"),
                    "title": item.get("metadata", {}).get("title", "Untitled"),
                    "category": item.get("metadata", {}).get("category", "general"),
                    "created_at": item.get("created_at"),
                }
            )

        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Export all tools
KNOWLEDGE_INJECTION_TOOLS = [
    add_business_knowledge,
    add_product_info,
    add_company_info,
    add_process_or_policy,
    add_faq,
    list_knowledge,
]
