# Knowledge Vault: How to Add Business Context to RAG

This guide explains how to add your business knowledge to Pikar-AI's Knowledge Vault so that agents can retrieve relevant context during conversations.

## Quick Start

### Option 1: Brain Dumps (Fastest)

For quick, unstructured knowledge ingestion:

```python
import asyncio
from app.rag.knowledge_vault import ingest_brain_dump

async def add_my_knowledge():
    result = await ingest_brain_dump(
        content="""
        Our company, Acme Corp, was founded in 2020.
        We sell AI-powered business tools.
        Our target market is SMBs with 10-100 employees.
        Our main competitors are TechCo and AITools Inc.
        Our pricing is $99/month for starter, $299/month for pro.
        """,
        title="Company Overview",
        user_id="user_123",  # Optional: for multi-tenant isolation
        metadata={"category": "company_info"}
    )
    print(f"Ingested {result['chunk_count']} chunks")

asyncio.run(add_my_knowledge())
```

### Option 2: Structured Documents

For formal documents with titles and types:

```python
from app.rag.knowledge_vault import ingest_document_content

async def add_document():
    result = await ingest_document_content(
        content="""
        # Product Launch Playbook
        
        ## Phase 1: Pre-Launch (4 weeks before)
        - Finalize pricing and packaging
        - Create marketing materials
        - Set up analytics tracking
        
        ## Phase 2: Launch Week
        - Send announcement emails
        - Publish blog post
        - Activate social media campaigns
        """,
        title="Product Launch Playbook",
        document_type="playbook",
        user_id="user_123",
        agent_id="MarketingAutomationAgent",  # Agent-specific knowledge
        metadata={"version": "1.0", "author": "Product Team"}
    )
    print(f"Ingested document with {result['chunk_count']} chunks")
```

---

## API Endpoints (Coming Soon)

For REST API access, the following endpoints will be available:

### POST /api/knowledge/brain-dump
```json
{
  "content": "Your brain dump text here...",
  "title": "Optional Title",
  "metadata": {"category": "business"}
}
```

### POST /api/knowledge/document
```json
{
  "content": "Document content...",
  "title": "Document Title",
  "document_type": "policy|playbook|faq|other",
  "agent_id": "optional_agent_id"
}
```

### GET /api/knowledge/search?q=query&top_k=5

---

## How It Works

```
┌─────────────────────┐
│   Your Content      │
│  (Brain Dump/Doc)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Ingestion Service  │
│  - Chunk text       │
│  - 500 chars/chunk  │
│  - 50 char overlap  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Embedding Service  │
│  - Vertex AI        │
│  - text-embedding   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Supabase Vector    │
│  - pgvector         │
│  - agent_knowledge  │
└─────────────────────┘
```

---

## What Knowledge to Add

### High-Value Knowledge Types

| Type | Example | Benefit |
|------|---------|---------|
| Company Overview | Mission, values, history | Agents understand your context |
| Product Info | Features, pricing, positioning | Sales/Support accuracy |
| Processes | SOPs, workflows | Operations consistency |
| Policies | HR, compliance, legal | Risk reduction |
| Customer FAQs | Common questions/answers | Faster support |
| Brand Voice | Tone, messaging guidelines | Content consistency |

### Knowledge by Agent

| Agent | Recommended Knowledge |
|-------|----------------------|
| ExecutiveAgent | Vision, strategy, OKRs |
| FinancialAgent | Budgets, financial policies |
| ContentAgent | Brand voice, style guides |
| SalesAgent | Sales playbooks, objection handling |
| MarketingAgent | Campaign history, audience personas |
| HRAgent | Job descriptions, policies |
| ComplianceAgent | Regulations, audit history |
| CustomerSupport | FAQs, known issues |

---

## Searching Knowledge

Agents automatically search the Knowledge Vault using `search_business_knowledge`:

```python
# This is what agents do internally
from app.rag.knowledge_vault import search_knowledge

results = search_knowledge(
    query="What is our pricing for enterprise customers?",
    top_k=5,
    user_id="user_123"  # Optional filtering
)

for result in results["results"]:
    print(f"Relevance: {result['similarity']:.2f}")
    print(f"Content: {result['content'][:200]}...")
```

---

## Multi-Tenant Isolation

All knowledge is isolated by `user_id`:

```python
# User A's knowledge
await ingest_brain_dump(content="...", user_id="user_a")

# User B's knowledge  
await ingest_brain_dump(content="...", user_id="user_b")

# Searches are automatically filtered
search_knowledge("pricing", user_id="user_a")  # Only sees user_a's docs
```

---

## Best Practices

1. **Be Specific**: "Our enterprise pricing is $999/month" > "We have enterprise plans"
2. **Add Context**: Include dates, versions, and sources
3. **Update Regularly**: Keep knowledge current
4. **Use Titles**: Makes content easier to find
5. **Tag by Agent**: Use `agent_id` for specialized knowledge
6. **Chunk Wisely**: System auto-chunks, but consider document structure

---

## Example: Full Onboarding Script

```python
import asyncio
from app.rag.knowledge_vault import ingest_brain_dump, ingest_document_content

async def onboard_new_customer(user_id: str, company_info: dict):
    """Add initial business knowledge during user onboarding."""
    
    # 1. Company Overview
    await ingest_brain_dump(
        content=f"""
        Company Name: {company_info['name']}
        Industry: {company_info['industry']}
        Size: {company_info['employee_count']} employees
        Founded: {company_info['founded_year']}
        Mission: {company_info['mission']}
        """,
        title="Company Profile",
        user_id=user_id,
        metadata={"source": "onboarding"}
    )
    
    # 2. Products/Services
    for product in company_info.get('products', []):
        await ingest_document_content(
            content=product['description'],
            title=f"Product: {product['name']}",
            document_type="product_info",
            user_id=user_id,
        )
    
    # 3. Key Metrics
    if company_info.get('revenue'):
        await ingest_brain_dump(
            content=f"Annual Revenue: {company_info['revenue']}",
            title="Financial Overview",
            user_id=user_id,
            metadata={"category": "finance"}
        )
    
    print(f"✅ Onboarded {company_info['name']} with initial knowledge")

# Usage
asyncio.run(onboard_new_customer(
    user_id="user_123",
    company_info={
        "name": "Acme Corp",
        "industry": "SaaS",
        "employee_count": 50,
        "founded_year": 2020,
        "mission": "Make AI accessible to SMBs",
        "products": [
            {"name": "AI Assistant", "description": "24/7 customer support bot"},
            {"name": "Analytics Pro", "description": "Business intelligence dashboard"}
        ],
        "revenue": "$2M ARR"
    }
))
```

---

## Troubleshooting

### "Knowledge Vault not configured"
- Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set
- Run migrations: `supabase db push` or apply manually

### Agents not finding knowledge
- Check `user_id` matches in search and ingestion
- Increase `top_k` for broader search
- Verify content was chunked (check `chunk_count` in response)

### Empty search results
- Knowledge Vault may be empty for this user
- Try broader queries
- Check embedding service is working
