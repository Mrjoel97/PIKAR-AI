# Pikar AI Engine - Unified Product Requirements & Technical Specification

**Version:** 1.0  
**Status:** Final Draft  
**Created:** 2026-01-15  
**Authors:** Product & Engineering Teams

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision & Mission](#2-product-vision--mission)
3. [The 11 AI Agents](#3-the-11-ai-agents)
4. [Executive AI Assistant](#4-executive-ai-assistant)
5. [Multi-Agent Orchestration](#5-multi-agent-orchestration)
6. [Knowledge Vault (RAG System)](#6-knowledge-vault-rag-system)
7. [Agent Configuration & Training](#7-agent-configuration--training)
8. [Agent Monitoring & Analytics](#8-agent-monitoring--analytics)
9. [User Experience Journeys](#9-user-experience-journeys)
10. [Tier-Based Capabilities](#10-tier-based-capabilities)
11. [Technical Architecture](#11-technical-architecture)
12. [API Infrastructure & Architecture](#12-api-infrastructure--architecture)
13. [Media Generation (Images & Videos)](#13-media-generation-images--videos)
14. [Data Models & Schema](#14-data-models--schema)
15. [Safety, Privacy & Reliability](#15-safety-privacy--reliability)
16. [Implementation Roadmap](#16-implementation-roadmap)
17. [Success Metrics](#17-success-metrics)
18. [Future Vision](#18-future-vision)

---

## 1. Executive Summary

The **Pikar AI Engine** is the intelligent core powering the Pikar AI platform. It transforms business operations by providing an AI workforce that thinks, learns, and acts like a team of expert consultants—available 24/7.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **11 Specialized Agents** | Purpose-built AI experts for every business function |
| **Executive AI Assistant** | Personal AI Chief of Staff with generative AND agentic abilities |
| **Multi-Agent Orchestration** | Agents collaborate on complex, multi-step tasks |
| **Knowledge Vault (RAG)** | Semantic memory that learns your business context |
| **Custom Agent Training** | Users train agents with their own documents and data |
| **Intelligent Automation** | AI executes tasks, not just provides suggestions |

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Sophistication First** | No "basic chat" - every interaction is context-aware and actionable |
| **Agentic by Default** | AI doesn't just respond, it **acts** (creates tasks, updates CRM, schedules content) |
| **Agent Collaboration** | Executive Assistant delegates to specialized agents |
| **User Empowerment** | Users train agents with their own knowledge, not just prompts |
| **Human-Centric** | AI augments human decision-making, never replaces it |

---

## 2. Product Vision & Mission

### Mission Statement
> "Empower every business—from solopreneurs to enterprises—with an AI workforce that thinks, learns, and acts like a team of expert consultants, available 24/7."

### Core Promise
The Pikar AI Engine transforms business operations by providing intelligent automation that:
- **Understands** your business goals, challenges, and context
- **Thinks** through complex problems using specialized AI agents
- **Learns** from every interaction to improve recommendations
- **Acts** by automating tasks, generating content, and providing insights
- **Coordinates** multiple AI agents to solve multi-faceted problems

### How Users Experience It

| Interaction Type | Description |
|-----------------|-------------|
| **Natural Conversations** | Chat with AI agents in plain English |
| **Smart Suggestions** | Proactive recommendations based on activity |
| **Automated Actions** | Tasks completed without manual intervention |
| **Intelligent Insights** | Data analysis and strategic recommendations |
| **Content Generation** | Marketing materials, emails, reports created instantly |

---

## 3. The 11 AI Agents

Each agent is a specialized AI expert trained for specific business functions:

### Agent Availability by Tier

| # | Agent | Role | Solopreneur | Startup | SME | Enterprise |
|---|-------|------|:-----------:|:-------:|:---:|:----------:|
| 1 | **Executive Agent** | Personal AI Chief of Staff | ✅ | ✅ | ✅ | ✅ |
| 2 | **Marketing Automation Agent** | Campaign & Content Planning | ✅ | ✅ | ✅ | ✅ |
| 3 | **Content Creation Agent** | Writing & Creation | ✅ | ✅ | ✅ | ✅ |
| 4 | **Strategic Planning Agent** | Planning & Analysis | ❌ | ✅ | ✅ | ✅ |
| 5 | **Data Analysis Agent** | Analytics & Forecasting | ❌ | ✅ | ✅ | ✅ |
| 6 | **Financial Analysis Agent** | Finance & Accounting | ❌ | ✅ | ✅ | ✅ |
| 7 | **Customer Support Agent** | Customer Service | ❌ | ✅ | ✅ | ✅ |
| 8 | **Sales Intelligence Agent** | Lead & Deal Management | ❌ | ✅ | ✅ | ✅ |
| 9 | **HR & Recruitment Agent** | Recruitment & Talent | ❌ | ✅ | ✅ | ✅ |
| 10 | **Compliance & Risk Agent** | Risk & Audit | ❌ | ❌ | ✅ | ✅ |
| 11 | **Operations Optimization Agent** | Process Optimization | ❌ | ❌ | ✅ | ✅ |

### Agent Capabilities Detail

#### Executive Agent (All Tiers)
- **Role:** Personal AI assistant and strategic advisor
- **Capabilities:** Strategic planning, coordinates other agents, executive summaries, daily priorities
- **Unique:** The only agent that can delegate to and orchestrate other agents

#### Marketing Automation Agent (All Tiers)
- **Role:** Campaign strategist and content planner
- **Capabilities:** Multi-channel campaigns, content calendars, email sequences, A/B testing

#### Content Creation Agent (All Tiers)
- **Role:** Brand storyteller and content producer
- **Capabilities:** Blog posts, newsletters, social media, reports, adapts to brand voice

#### Strategic Planning Agent (Startup+)
- **Role:** Business strategist and market analyst
- **Capabilities:** Market analysis, competitive research, OKRs, strategic roadmaps

#### Data Analysis Agent (Startup+)
- **Role:** Business intelligence analyst
- **Capabilities:** Sales/marketing analysis, trend forecasting, anomaly detection

#### Financial Analysis Agent (Startup+)
- **Role:** Financial advisor and modeler
- **Capabilities:** Financial models, ROI evaluation, scenario planning, cash flow

#### Customer Support Agent (Startup+)
- **Role:** Support specialist and knowledge manager
- **Capabilities:** Ticket triage, response drafting, knowledge base updates

#### Sales Intelligence Agent (Startup+)
- **Role:** Sales strategist and deal advisor
- **Capabilities:** Lead scoring, sales playbooks, account analysis, competitive intel

#### HR & Recruitment Agent (Startup+)
- **Role:** Talent acquisition specialist
- **Capabilities:** Resume screening, candidate evaluation, interview prep

#### Compliance & Risk Agent (SME+)
- **Role:** Compliance officer and risk manager
- **Capabilities:** Regulatory validation, risk assessment, audit management

#### Operations Optimization Agent (SME+)
- **Role:** Process engineer and efficiency expert
- **Capabilities:** Workflow analysis, bottleneck identification, process improvement

---

## 4. Executive AI Assistant

The Executive AI Assistant is the user's primary interface—not just a chatbot, but an AI-powered Chief of Staff with both **generative** and **agentic** capabilities.

### Capability Matrix

| Capability | Generative | Agentic | Example |
|------------|:----------:|:-------:|---------|
| Answer Questions | ✅ | | "What's my revenue this month?" |
| Create Tasks | | ✅ | "Remind me to call John" → Creates task |
| Draft Content | ✅ | | "Write a LinkedIn post about my course" |
| Schedule Posts | | ✅ | "Schedule that for Friday 9am" → Schedules |
| Delegate to Agents | | ✅ | "Have Marketing Agent create a campaign" |
| Run Workflows | | ✅ | "Execute the lead qualification pipeline" |
| Train Agents | ✅ | ✅ | "Teach Content Agent my brand voice" |
| Search Knowledge | ✅ | | "What did I brainstorm about pricing?" |

### Available Tools

```typescript
const executiveTools = {
    // GENERATIVE
    thinkAndRespond: "Answer questions using context and knowledge",
    
    // AGENTIC (CRUD)
    createTask: "Create tasks in user's task list",
    updateContact: "Update CRM contacts",
    schedulePost: "Schedule social media posts",
    createGoal: "Create goals and OKRs",
    sendEmail: "Send emails on user's behalf",
    
    // ORCHESTRATION
    delegateToAgent: "Assign tasks to specialized agents",
    executeWorkflow: "Run predefined multi-step workflows",
    
    // KNOWLEDGE
    searchKnowledge: "Query the Knowledge Vault via RAG",
    trainAgent: "Add knowledge to train agents"
};
```

### User Flow: Executive Delegation

```
User: "Create a launch campaign for my new course"
    ↓
Executive Assistant receives message
    ↓
Recognizes: This is a marketing-specialized task
    ↓
Delegates: delegateToAgent("marketing", "Create launch campaign...")
    ↓
Marketing Agent executes:
    - Retrieves brand voice from Knowledge Vault
    - Generates 4-week campaign plan
    - Creates content calendar
    - Returns to Executive
    ↓
Executive presents result to user
```

---

## 5. Multi-Agent Orchestration

### Orchestration Patterns

The AI Engine coordinates multiple agents using four primary patterns:

#### 1. Sequential Orchestration
**When:** Tasks requiring step-by-step progression  
**How:** Agent A → Agent B → Agent C

**Example: Product Launch Plan**
1. Strategic Planning Agent → Market analysis
2. Marketing Agent → Campaign strategy
3. Content Agent → Content calendar
4. Financial Agent → Budget allocation
5. Executive Agent → Final synthesis

#### 2. Parallel Orchestration
**When:** Independent tasks that can run simultaneously  
**How:** Multiple agents work concurrently, results combined

**Example: Quarterly Board Meeting Prep**
- Data Agent → Performance metrics (parallel)
- Financial Agent → Financial statements (parallel)
- Strategic Agent → Market update (parallel)
- Executive Agent → Combines into deck

#### 3. Consensus Orchestration
**When:** Important decisions requiring multiple perspectives  
**How:** Multiple agents analyze same question, AI synthesizes

**Example: Price Increase Decision**
- Financial Agent → Revenue impact (recommends: Yes)
- Data Agent → Churn prediction (recommends: Caution)
- Sales Agent → Deal impact (recommends: Partial)
- Executive Agent → Synthesizes balanced recommendation

#### 4. Conditional Orchestration
**When:** Workflows with decision points and branching  
**How:** Agent decisions determine next steps

**Example: Lead Qualification**
1. Sales Agent → Scores lead
2. IF score > 80 → Financial Agent (ROI modeling)
3. IF score < 50 → Support Agent (nurture sequence)
4. Executive Agent → Delivers appropriate action

---

## 6. Knowledge Vault (RAG System)

### Purpose

The Knowledge Vault is a centralized, RAG-powered repository that enables all agents to access user-specific context and memory.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE VAULT                              │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  GLOBAL KNOWLEDGE │  │  AGENT-SPECIFIC  │  │  AUTO-INDEXED  │ │
│  │  (All Agents)     │  │  (Per Agent)     │  │  (Real-time)   │ │
│  │                   │  │                   │  │                │ │
│  │  • Brand Voice     │  │  • Agent Prompts  │  │  • Brain Dumps │ │
│  │  • Target Audience │  │  • Examples       │  │  • Tasks       │ │
│  │  • Uploaded Docs   │  │  • Instructions   │  │  • Content     │ │
│  │  • Business Context│  │  • Training Data  │  │  • Goals       │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                │                                 │
│                                ▼                                 │
│        ┌──────────────────────────────────────────────┐         │
│        │            EMBEDDINGS (pgvector)              │         │
│        │   Semantic search across all knowledge        │         │
│        └──────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Knowledge Sources

| Source Type | Description | Auto-Indexed |
|-------------|-------------|:------------:|
| Brain Dumps | User's captured thoughts and ideas | ✅ |
| Business Context | Brand voice, target audience, core offer | ✅ |
| Documents | Uploaded PDFs, policies, guidelines | Manual |
| Content History | Past blogs, emails, social posts | ✅ |
| Tasks | Completed tasks with context | ✅ |
| Agent Knowledge | Training data specific to an agent | Manual |

### RAG Query Flow

```
User asks: "What pricing ideas have I brainstormed?"
    ↓
1. Generate embedding for query
2. Semantic search in embeddings table
3. Filter by user_id and source_type
4. Return top 5 matches with similarity scores
5. Agent incorporates into response context
```

---

## 7. Agent Configuration & Training

### System Agents vs Custom Agents

| Aspect | System Agents (11 Built-in) | Custom Agents (User-created) |
|--------|:---------------------------:|:----------------------------:|
| **Who Controls** | Admin only | End users |
| **Configuration** | Admin Panel | User's Agent Training Page |
| **Visibility** | All users (by tier) | Only the creating user |
| **Training** | Admin uploads knowledge | User uploads knowledge |
| **System Prompt** | Admin edits | User edits |

### Admin-Only Control for Built-in Agents

Built-in (system) agents are **exclusively managed by admins** via the Admin Panel. End users can use these agents but cannot modify them.

#### Admin Panel Features

| Feature | What Admin Can Do |
|---------|-------------------|
| **System Prompt Editor** | Edit/improve prompts for all 11 agents |
| **Model Selection** | Change base model (Gemini 1.5 Pro, Gemini 1.5 Flash) |
| **Temperature Tuning** | Adjust creativity per agent |
| **Tool Permissions** | Enable/disable which tools each agent can use |
| **Knowledge Upload** | Add global training documents to agents |
| **Performance Review** | See success rates, tweak based on failures |

#### How Built-in Agents Are "Trained"

Built-in agents are trained through **prompt engineering**, not document uploads:

1. **System Prompts** - Expert-crafted prompts defining agent expertise
2. **Tool Permissions** - Specific tools assigned per agent role
3. **Temperature Settings** - Creativity levels tuned per agent
4. **User Context at Runtime** - Agents access Knowledge Vault during execution

```typescript
// Example: Marketing Agent configuration (Admin-controlled)
const marketingAgent = {
    name: "Marketing Agent",
    system_prompt: `You are an expert Marketing Strategist with 15+ years experience.
        Your specialties: Campaign planning, audience targeting, content calendars.
        Your tone: Strategic, data-informed, creative...`,
    base_model: "gemini-1.5-pro",
    temperature: 0.7,
    enabled_tools: ["createContent", "schedulePost", "analyzeCampaign"],
    is_system: true  // Admin-only
};
```

#### Access Control (RLS)

```sql
-- Users can READ system agents, but NOT update them
CREATE POLICY "users_read_system_agents" ON agents
    FOR SELECT USING (is_system = true);

-- Only admins can UPDATE system agents
CREATE POLICY "admins_update_system_agents" ON agents
    FOR UPDATE USING (
        is_system = true 
        AND auth.jwt() ->> 'role' = 'admin'
    );
```

### Custom Agent Creation (User-Controlled)

End users create custom agents via the Agent Builder:

1. **Define Identity**: Name, role, avatar
2. **Select Base Model**: Gemini 1.5 Pro, Gemini 1.5 Flash
3. **Set Behavior**: Temperature (creativity), tone, style
4. **Assign Tools**: Which CRUD/API actions the agent can perform
5. **Upload Knowledge**: Files, URLs, or text to train the agent

### Custom Agent Training Pipeline

```
[User uploads "Sales_Playbook.pdf" to Agent Training]
    ↓
Frontend: POST /functions/v1/train-agent { agent_id, file }
    ↓
Edge Function: train-agent
    1. Extract text from PDF
    2. Chunk into ~500 token segments
    3. Generate embeddings (Google text-embedding-004)
    4. Store in embeddings table with agent_id
    5. Mark agent_knowledge.is_processed = true
    ↓
Agent now retrieves this knowledge via RAG when executing tasks
```

### Custom Agent Limits by Tier

| Tier | Custom Agents |
|------|:-------------:|
| Solopreneur | 1 |
| Startup | 5 |
| SME | 15 |
| Enterprise | Unlimited |

---

## 8. Agent Monitoring & Analytics

### Overview

Admins and users can monitor agent usage, performance, and issues through multiple data sources and dashboards.

### Data Sources

| Data Source | What It Tracks | Who Can See |
|-------------|----------------|-------------|
| `agent_activity` | Real-time agent actions | User (own), Admin (all) |
| `ai_jobs` | Job execution status, errors | User (own), Admin (all) |
| `agents` table | Performance metrics | User (own), Admin (all) |

### Agent Metrics (In `agents` Table)

| Metric | Description |
|--------|-------------|
| `tasks_completed` | Total successful executions |
| `success_rate` | % of tasks completed without errors |
| `avg_response_time_ms` | Speed performance |
| `status` | active, idle, paused |

### AI Jobs Tracking

```sql
-- Every AI execution is logged
SELECT 
    agent_id,
    job_type,
    status,          -- pending, running, completed, failed
    error_message,   -- if failed, shows why
    input_data,
    output_data,
    created_at,
    completed_at
FROM ai_jobs WHERE user_id = '...';
```

### Admin Dashboard Views

| View | Metrics Shown |
|------|---------------|
| **Usage** | Messages/month, RAG queries, workflow runs per tier |
| **Performance** | Response times, success rates by agent |
| **Issues** | Failed jobs with error logs, retry counts |
| **Cost** | Token usage, API costs per agent |
| **User Activity** | Active users, top agents, trends |

### User Dashboard (Agent Hub)

- ✅ Tasks completed count
- ⏱ Uptime percentage
- 📊 Success rate
- 🔴 Status indicator
- 📋 Recent activity feed

### Error Monitoring Query

```sql
-- Find all failed agent jobs for investigation
SELECT 
    a.name as agent_name,
    j.error_message, 
    j.input_data, 
    j.created_at
FROM ai_jobs j
JOIN agents a ON j.agent_id = a.id
WHERE j.status = 'failed'
ORDER BY j.created_at DESC;
```

---

## 9. User Experience Journeys

### Solopreneur: Monday Morning Planning (15 minutes)

| Time | Action |
|------|--------|
| 9:00 | Open dashboard → Executive greets with week overview |
| 9:05 | Ask "What should I prioritize?" → Strategic recommendations |
| 9:10 | "Create LinkedIn post about my new service" → Content Agent drafts |
| 9:15 | Marketing Agent suggests newsletter → Auto-drafts with case studies |

**Result:** Complete week planned + content created (normally 2+ hours)

### Startup: Product Launch Campaign (4 weeks)

| Week | Activities |
|------|------------|
| 1 | Strategic Agent analyzes market → 4-week roadmap |
| 2 | Content Agent generates assets → Marketing Agent creates calendar |
| 3 | Data Agent identifies segments → Sales Agent creates playbooks |
| 4 | All agents coordinate execution → Executive provides daily summaries |

**Result:** 3x content volume in 25% of the time

### SME: Quarterly Business Review (1 week)

| Day | Activities |
|-----|------------|
| 1 | Data + Financial Agents gather and compile data |
| 2-3 | Strategic + Compliance Agents analyze and assess |
| 4 | Financial Agent models 3 growth scenarios |
| 5 | Executive Agent synthesizes into board presentation |

**Result:** Complete QBR in 1 week vs. 4-6 weeks manually

---

## 10. Tier-Based Capabilities

### Comprehensive Tier Comparison

| Feature | Solopreneur | Startup | SME | Enterprise |
|---------|:-----------:|:-------:|:---:|:----------:|
| **Pricing** | $99/mo | $297/mo | $597/mo | Custom |
| **AI Agents** | 3 | 8 | 11 | 11 + Custom |
| **Custom Agents** | 1 | 5 | 15 | Unlimited |
| **AI Actions/Month** | 1,000 | 10,000 | 50,000 | Unlimited |
| **Knowledge Vault** | 50MB | 500MB | 5GB | 50GB |
| **RAG Queries/Month** | 500 | 5,000 | 25,000 | Unlimited |
| **Workflow Runs/Month** | 100 | 1,000 | 10,000 | Unlimited |
| **Multi-Agent Orchestration** | Basic | Full | Full | Full |
| **Predictive Analytics** | ❌ | ✅ | ✅ | ✅ |
| **Custom Workflows** | ❌ | ❌ | ✅ | ✅ |
| **API Access** | ❌ | ❌ | ✅ | ✅ |
| **Dedicated Capacity** | ❌ | ❌ | ❌ | ✅ |
| **White-Label** | ❌ | ❌ | ❌ | ✅ |

### Best Fit by Tier

| Tier | Best For |
|------|----------|
| **Solopreneur** | Solo entrepreneurs, freelancers, content creators |
| **Startup** | Growing startups (5-20 employees), sales-driven orgs |
| **SME** | Established businesses (20-200 employees), regulated industries |
| **Enterprise** | Large enterprises (200+), global operations, custom requirements |

---

## 11. Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ Executive   │  │ Agent Hub    │  │ Agent       │  │ Orchestration    │   │
│  │ Chat Panel  │  │ (All Agents) │  │ Training    │  │ Dashboard        │   │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └────────┬─────────┘   │
└─────────┼────────────────┼─────────────────┼──────────────────┼─────────────┘
          │                │                 │                  │
          ▼                ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI VERTEX ENGINE (Backend)                           │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    EXECUTIVE AI ASSISTANT                              │  │
│  │  • Generative: Answers, Drafts, Ideas                                  │  │
│  │  • Agentic: Creates Tasks, Schedules, Updates CRM                      │  │
│  │  • Orchestrator: Delegates to specialized agents                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│              ┌─────────────────────┼─────────────────────┐                   │
│              ▼                     ▼                     ▼                   │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐            │
│  │  SYSTEM AGENTS  │   │  CUSTOM AGENTS  │   │  KNOWLEDGE      │            │
│  │  (11 Built-in)  │   │  (User Created) │   │  VAULT (RAG)    │            │
│  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘            │
│           │                     │                     │                      │
│           └─────────────────────┼─────────────────────┘                      │
│                                 ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        TOOL REGISTRY                                   │  │
│  │  CRUD Operations | External APIs | Workflow Steps | Agent Delegation  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SUPABASE DATABASE                                  │
│  profiles | agents | agent_knowledge | embeddings | ai_jobs | workflows    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, TailwindCSS |
| Backend | Supabase Edge Functions (Deno) |
| Database | PostgreSQL with pgvector |
| Auth | Supabase Auth |
| AI Models | Google Gemini 1.5 Pro, Google Gemini 1.5 Flash |
| Embeddings | Google text-embedding-004 (768 dimensions) |
| Real-time | Supabase Realtime |

### Edge Functions

| Function | Purpose |
|----------|---------|
| `ai-chat` | Executive AI Assistant (main chat interface) |
| `ai-orchestrator` | Job routing and agent dispatch |
| `execute-workflow` | Multi-step workflow execution |
| `train-agent` | Document processing and embedding |
| `embed-content` | Auto-embedding pipeline |
| `process-brain-dump` | Brain dump classification |

---

## 12. API Infrastructure & Architecture

### API Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                 │
│                                                                               │
│   useAIChat()   useAgents()   useWorkflows()   useKnowledge()   useAdmin()   │
│        │             │              │                │              │         │
│        └─────────────┴──────────────┴────────────────┴──────────────┘         │
│                                     │                                         │
│                              api.ts / aiApi                                   │
└─────────────────────────────────────┼─────────────────────────────────────────┘
                                      │ HTTP/WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE EDGE FUNCTIONS                              │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  ai-chat    │  │ ai-vertex   │  │ train-agent │  │ execute-workflow    │ │
│  │  (Main)     │  │ (Orchestr.) │  │ (Training)  │  │ (Multi-step)        │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │embed-content│  │ admin-agents│  │ agent-stats │  │ rag-search          │ │
│  │ (Embeddings)│  │ (Admin API) │  │ (Metrics)   │  │ (Knowledge Query)   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SUPABASE DATABASE                                 │
│                                                                              │
│   agents │ ai_jobs │ embeddings │ agent_knowledge │ workflows │ ai_messages │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Backend APIs (Edge Functions)

#### Core AI Functions

| Function | Endpoint | Purpose | Method |
|----------|----------|---------|--------|
| `ai-chat` | `/functions/v1/ai-chat` | Executive AI Assistant chat | POST (streaming) |
| `ai-vertex` | `/functions/v1/ai-vertex` | Agent orchestration engine | POST |
| `execute-workflow` | `/functions/v1/execute-workflow` | Multi-step workflow execution | POST |

#### Agent Management Functions

| Function | Endpoint | Purpose | Method |
|----------|----------|---------|--------|
| `train-agent` | `/functions/v1/train-agent` | Process documents → embeddings | POST |
| `embed-content` | `/functions/v1/embed-content` | Auto-embed content | POST |
| `admin-agents` | `/functions/v1/admin-agents` | Admin CRUD for system agents | POST |

#### Knowledge/RAG Functions

| Function | Endpoint | Purpose | Method |
|----------|----------|---------|--------|
| `rag-search` | `/functions/v1/rag-search` | Semantic search in Knowledge Vault | POST |

#### Analytics Functions

| Function | Endpoint | Purpose | Method |
|----------|----------|---------|--------|
| `agent-stats` | `/functions/v1/agent-stats` | Usage & performance metrics | GET |

### Frontend API Layer

#### Extended API Structure

```typescript
// lib/api/ai.ts
export const aiApi = {
    // Executive AI Chat (streaming)
    chat: {
        send: (message, conversationId) => streamResponse('/ai-chat', { message, conversationId }),
        getHistory: (conversationId) => supabase.from('ai_messages').select('*').eq('conversation_id', conversationId),
    },
    
    // Agent Delegation
    agents: {
        delegate: (agentId, task, priority) => invokeFunction('ai-vertex', { agent_id: agentId, task, priority }),
        getStatus: (jobId) => supabase.from('ai_jobs').select('*').eq('id', jobId).single(),
    },
    
    // Knowledge Vault
    knowledge: {
        search: (query, filters) => invokeFunction('rag-search', { query, ...filters }),
        upload: (agentId, file) => invokeFunction('train-agent', { agent_id: agentId, file }),
        list: (agentId) => supabase.from('agent_knowledge').select('*').eq('agent_id', agentId),
    },
    
    // Workflows
    workflows: {
        execute: (workflowId, payload) => invokeFunction('execute-workflow', { workflow_id: workflowId, ...payload }),
        getStatus: (executionId) => supabase.from('workflow_executions').select('*').eq('id', executionId).single(),
        list: () => supabase.from('workflow_definitions').select('*'),
    },
};

// lib/api/admin.ts (Admin-only)
export const adminApi = {
    agents: {
        list: () => supabase.from('agents').select('*').eq('is_system', true),
        update: (agentId, config) => invokeFunction('admin-agents', { action: 'update', agent_id: agentId, ...config }),
        getStats: (agentId) => invokeFunction('agent-stats', { agent_id: agentId }),
    },
    
    analytics: {
        usage: (dateRange) => invokeFunction('agent-stats', { type: 'usage', ...dateRange }),
        errors: (limit) => supabase.from('ai_jobs').select('*').eq('status', 'failed').limit(limit),
    },
};
```

### React Hooks Layer

```typescript
// hooks/useAIChat.ts (existing, enhanced)
export function useAIChat() {
    // Streaming chat with Executive AI
    // Tool call handling
    // Agent delegation feedback
}

// hooks/useAgentDelegation.ts (NEW)
export function useAgentDelegation() {
    const delegateTask = async (agentId: string, task: string) => { ... };
    const { status, result } = useJobPolling(jobId);
    return { delegateTask, status, result };
}

// hooks/useKnowledgeVault.ts (NEW)
export function useKnowledgeVault() {
    const search = async (query: string) => { ... };
    const upload = async (file: File, agentId?: string) => { ... };
    return { search, upload, results, isSearching };
}

// hooks/useAdminAgents.ts (NEW - Admin only)
export function useAdminAgents() {
    const updateSystemAgent = async (agentId: string, config: AgentConfig) => { ... };
    const getStats = async () => { ... };
    return { agents, updateSystemAgent, stats };
}
```

### Database RPCs (Postgres Functions)

| RPC | Purpose | Called By |
|-----|---------|-----------|r
| `match_documents(query_embedding, threshold, limit)` | RAG semantic search | `rag-search` |
| `match_agent_documents(agent_id, query_embedding, ...)` | Agent-specific RAG | `ai-vertex` |
| `get_tier_limits(user_id)` | Check usage vs tier limits | `ai-chat`, `ai-vertex` |
| `increment_usage(user_id, type)` | Track message/RAG usage | All AI functions |

### Real-time Subscriptions

```typescript
// Frontend subscribes to real-time updates
const channel = supabase
    .channel('ai-updates')
    .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'agent_activity',
    }, (payload) => {
        // Update live activity feed
    })
    .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'ai_jobs',
        filter: `id=eq.${jobId}`,
    }, (payload) => {
        // Update job status (for long-running tasks)
    })
    .subscribe();
```

### Implementation Status

#### Backend (Edge Functions)

| Status | Function |
|:------:|----------|
| ✅ Exists | `ai-chat`, `execute-workflow`, `process-brain-dump` |
| 🔧 Enhance | `ai-chat` → add tool calling, delegation |
| 🆕 New | `ai-vertex`, `train-agent`, `embed-content`, `rag-search`, `admin-agents`, `agent-stats` |

#### Frontend (API + Hooks)

| Status | Component |
|:------:|----------|
| ✅ Exists | `aiApi.chat`, `useAIChat` |
| 🔧 Enhance | `api.ts` → add delegation, knowledge, workflows |
| 🆕 New | `adminApi`, `useAgentDelegation`, `useKnowledgeVault`, `useAdminAgents` |

#### Database

| Status | Item |
|:------:|------|
| ✅ Exists | `agents`, `ai_jobs`, `agent_activity` |
| 🆕 New | `embeddings`, `agent_knowledge`, RPCs for RAG |

---

## 13. Media Generation (Images & Videos)

### Overview

Pikar AI integrates advanced media generation models to help users create visual content for social media, marketing, and brand assets without needing design skills.

### Available Models

| Model | Provider | Purpose | Output |
|-------|----------|---------|--------|
| **Imagen 3** | Google | Image generation | 1024x1024 to 2048x2048 |
| **Veo 2** | Google | Video generation | 8-16 second clips |


### Media Generation Flow

```
User: "Create a LinkedIn post image for my coaching business"
                           │
                           ▼
            ┌─────────────────────────────────────┐
            │      CONTENT AGENT (Text LLM)       │
            │  1. Understand user intent          │
            │  2. Generate optimized image prompt │
            │  3. Generate post caption           │
            └──────────────────┼──────────────────┘
                              │
               ┌─────────────┼─────────────┐
               ▼                             ▼
    ┌───────────────────┐       ┌───────────────────┐
    │   IMAGEN 3 API    │       │   VEO 2 API       │
    │   (Image Gen)     │       │   (Video Gen)     │
    └─────────┼─────────┘       └─────────┼─────────┘
              │                             │
              └─────────────┬─────────────┘
                            ▼
            ┌─────────────────────────────────────┐
            │        SUPABASE STORAGE             │
            │  Store generated media for access   │
            └─────────────────────────────────────┘
```

### Edge Functions

| Function | Endpoint | Purpose |
|----------|----------|---------|
| `generate-image` | `/functions/v1/generate-image` | Create images via Imagen 3 |
| `generate-video` | `/functions/v1/generate-video` | Create videos via Veo 2 |

### Content Agent Tools

```typescript
const contentAgentTools = {
    generateImage: {
        description: "Create an image for social media or marketing",
        parameters: {
            prompt: "Image description",
            aspect_ratio: "1:1 (square), 16:9 (landscape), 9:16 (stories)",
            style: "photo, illustration, 3d-render, digital-art"
        }
    },
    generateVideo: {
        description: "Create a short video for social media",
        parameters: {
            prompt: "Video description",
            duration: "5-16 seconds",
            aspect_ratio: "16:9 (YouTube), 9:16 (TikTok/Reels), 1:1 (Feed)"
        }
    }
};
```

### Supported Formats

| Platform | Image Aspect | Video Aspect | Video Duration |
|----------|--------------|--------------|----------------|
| LinkedIn | 1:1, 1.91:1 | 16:9, 1:1 | 3-10 min |
| Instagram Feed | 1:1, 4:5 | 1:1, 4:5 | 3-60 sec |
| Instagram Stories/Reels | 9:16 | 9:16 | 15-90 sec |
| TikTok | 9:16 | 9:16 | 15-60 sec |
| YouTube | 16:9 | 16:9 | Any |
| Twitter/X | 16:9, 1:1 | 16:9, 1:1 | 0-140 sec |

### Cost Estimates

| Model | Cost per Generation | Notes |
|-------|---------------------|-------|
| **Imagen 3** | ~$0.02-0.04/image | Higher res = higher cost |
| **Veo 2** | ~$0.10-0.50/video | Depends on duration |


### Tier-Based Media Limits

| Tier | Images/Month | Videos/Month |
|------|:------------:|:------------:|
| Solopreneur | 50 | 10 |
| Startup | 500 | 100 |
| SME | 2,000 | 500 |
| Enterprise | Unlimited | Unlimited |

---

## 14. Data Models & Schema

### Core Tables

#### agents
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    description TEXT,
    avatar TEXT,
    is_system BOOLEAN DEFAULT false,
    tier_required TEXT DEFAULT 'solopreneur',
    base_model TEXT DEFAULT 'gemini-1.5-pro',
    temperature DECIMAL(3,2) DEFAULT 0.7,
    system_prompt TEXT,
    enabled_tools TEXT[],
    status TEXT DEFAULT 'active',
    tasks_completed INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 100.0,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### agent_knowledge
```sql
CREATE TABLE agent_knowledge (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    user_id UUID REFERENCES auth.users(id),
    source_type TEXT NOT NULL, -- 'document', 'url', 'text', 'example'
    title TEXT,
    content TEXT,
    file_path TEXT,
    is_processed BOOLEAN DEFAULT false,
    chunk_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### embeddings
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    source_type TEXT NOT NULL, -- 'brain_dump', 'content', 'task', 'document'
    source_id UUID NOT NULL,
    agent_id UUID REFERENCES agents(id), -- Optional, for agent-specific
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

#### ai_jobs
```sql
CREATE TABLE ai_jobs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    agent_id UUID REFERENCES agents(id),
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

---

## 15. Safety, Privacy & Reliability

### Content Safety

| Protection | Implementation |
|------------|----------------|
| No harmful content | Content filtering and moderation |
| Brand compliance | Brand voice validation |
| Factual accuracy | Source verification |
| Privacy | PII detection and redaction |

### Decision Support Philosophy

> **The AI Engine provides recommendations and insights, but humans make final decisions.**

- AI presents options with pros/cons
- Explains reasoning behind recommendations
- Highlights risks and uncertainties
- Defers to human judgment on critical decisions

### Transparency & Explainability

Every AI response includes:
- Which agent(s) provided the response
- What data sources were used
- Confidence level in recommendations
- Assumptions made in analysis
- Limitations and uncertainties

### Data Privacy & Security

| Protection | Implementation |
|------------|----------------|
| Encryption | At rest and in transit |
| Access Control | RLS policies per user |
| Audit Logging | All AI interactions logged |
| Compliance | GDPR, CCPA, SOC 2 ready |
| User Control | Choose data access, delete history, export data |

---

## 16. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

- [ ] Enable `pgvector` extension
- [ ] Create `embeddings` table with RLS
- [ ] Create `agent_knowledge` table
- [ ] Deploy `embed-content` Edge Function
- [ ] Set up auto-embed triggers for brain_dumps, content, tasks
- [ ] Implement `match_documents` RPC

### Phase 2: Agent Infrastructure (Weeks 3-4)

- [ ] Enhance `agents` table schema
- [ ] Create 11 system agents during user onboarding
- [ ] Implement `train-agent` Edge Function
- [ ] Connect AgentBuilderTab to backend
- [ ] Connect AgentTrainingPage to backend

### Phase 3: Executive AI Enhancement (Weeks 5-6)

- [ ] Upgrade `ai-chat` to full Vertex Engine
- [ ] Implement `delegateToAgent` tool
- [ ] Implement `searchKnowledge` tool (RAG)
- [ ] Implement `trainAgent` tool
- [ ] Add streaming support for long-running tasks

### Phase 4: Orchestration (Weeks 7-8)

- [ ] Add `agent` step type to `execute-workflow`
- [ ] Add `human_approval` step type
- [ ] Connect OrchestrationTab to real workflows
- [ ] Implement workflow templates

### Phase 5: Tier Integration (Week 9)

- [ ] Implement tier-based agent gating
- [ ] Implement usage tracking (messages, RAG queries, workflow runs)
- [ ] Add upgrade prompts in UI
- [ ] End-to-end testing all tiers

**Total Estimated Time:** 9 weeks

---

## 17. Success Metrics

### User Efficiency

| Metric | Target | Benchmark |
|--------|--------|-----------|
| Time Saved | 10-20 hrs/week per user | Solopreneur: 15 hrs, Enterprise: 100+ hrs |
| Task Automation | 40% of repetitive tasks | 60% for high-frequency tasks |
| Decision Speed | 50% faster strategic decisions | Board decisions in days vs. weeks |

### Business Impact

| Metric | Target | Benchmark |
|--------|--------|-----------|
| Revenue Growth | 25% increase from AI initiatives | 30% higher marketing ROI |
| Cost Reduction | 20% operational cost savings | $50K-$500K annual savings |
| Customer Satisfaction | 15% improvement in CSAT | 60% faster support response |

### AI Performance

| Metric | Target | Benchmark |
|--------|--------|-----------|
| Accuracy | 90%+ prediction accuracy | Sales forecasts within 10% |
| Relevance | 85%+ recommendations rated relevant | 90% content used with minor edits |
| Response Time | <5s simple, <30s complex | 95% within target |
| User Satisfaction | 4.5/5 average rating | 80% rate as "very helpful" |

---

## 18. Future Vision

### Near-Term (6-12 Months)

- **Voice Interaction**: Speak to AI agents naturally
- **Proactive AI**: AI initiates conversations with timely suggestions
- **Mobile-First**: Full AI capabilities on mobile devices

### Mid-Term (1-2 Years)

- **Industry-Specific Agents**: Healthcare, Legal, Manufacturing, Retail
- **Multi-User AI Sessions**: Team brainstorming with AI
- **Autonomous Workflows**: AI executes without human intervention

### Long-Term (2-5 Years)

- **AI-First Business OS**: AI as central nervous system of operations
- **Predictive Business Management**: AI anticipates needs before they arise
- **Global AI Network**: Cross-business insights (anonymized benchmarking)

---

## Conclusion

The Pikar AI Engine represents a fundamental shift from manual, reactive processes to intelligent, proactive automation. By combining 11 specialized AI agents with advanced orchestration, learning, and personalization capabilities, Pikar AI delivers an AI workforce that thinks, learns, and acts like a team of expert consultants.

### Key Takeaways

1. **Accessible Intelligence**: Natural language makes AI accessible to everyone
2. **Specialized Expertise**: 11 purpose-built agents across all business functions
3. **Intelligent Orchestration**: Multi-agent collaboration for complex problems
4. **Continuous Learning**: AI gets smarter about your business over time
5. **Tier-Appropriate Power**: Capabilities scale with business needs
6. **Human-Centric Design**: AI augments, never replaces, human decision-making
7. **Safe & Reliable**: Built-in safeguards ensure accuracy, privacy, and transparency

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-15  
**Status:** Ready for Approval  
**Next Steps:** Proceed to Phase 1 implementation upon approval
