# Project: pikar-ai

## Vision
To be the ultimate AI "Chief of Staff" and business growth engine, empowering non-technical users to transform vague ideas into thriving autonomous ventures through a highly orchestrated ecosystem of specialized agents.

## Core Goals
1. **Intelligent Orchestration:** Seamlessly delegate complex business tasks from a central Executive Agent to specialized domain experts (Finance, Marketing, Strategy, etc.).
2. **Autonomous Growth:** Provide a structured, agent-led pathway for evolving business concepts into operational entities.
3. **Operational Excellence:** Harden existing workflows and agentic protocols to ensure deterministic and reliable business management.
4. **Interoperable Ecosystem:** Utilize the A2A protocol for cross-framework agent collaboration.

## High-Level Architecture
- **Executive Layer:** Root ADK `LlmAgent` orchestrating sub-agents and tool calls.
- **Service Layer:** FastAPI backend providing SSE streaming, task management, and API routing.
- **Workflow Layer:** YAML-defined dynamic workflows executed via a centralized engine.
- **Persistence Layer:** Supabase (PostgreSQL) for state, session, and task storage, with Redis for performance acceleration.
- **Client Layer:** Next.js (TypeScript) frontend with real-time interactive widgets.

## Key Stakeholders
- **Primary Users:** Non-technical entrepreneurs and business owners.
- **Developers:** Senior AI/Backend Engineers focused on agentic reliability and framework extension.
