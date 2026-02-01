# Pikar-Ai Skill Registry

This file maps development tasks to the specific agent skills available in `.agent/skills`.
The agent should consult this file to determine which skill to utilize for a given request.

| Task Category | Skill Name | Trigger / Description |
| :--- | :--- | :--- |
| **Database** | `database-schema-designer` | Designing SQL schemas, tables, relationships. |
| **Dependencies** | `dependency-updater` | Updating `package.json`, `pyproject.toml`. |
| **API Design** | `api-design-principles` | Validating API consistency, REST/RPC choice. |
| **Security/Spec** | `spec-to-code-compliance` | Ensuring implementation matches spec (TDD/Formal). |
| **Context** | `audit-context-building` | Analyzing codebase context depth. |
| **Architecture** | `architecture-patterns` | High-level system design, ADRs. |
| **Monorepo** | `monorepo-management` | Managing workspace dependencies (mapped to `dependency-management`). |
| **Supabase** | `supabase-best-practices` | Security policies, RLS, Clerk integration. |
| **Testing** | `python-testing-patterns` | Pytest strategies, fixtures (mapped to `python-patterns`). |
| **Backend (Node)** | `nodejs-backend-patterns` | Node.js architecture, best practices. |
| **RAG/AI** | `rag-implementation` | Vector search, embeddings, retrieval logic. |
| **Packaging** | `python-packaging` | `pip`, `uv`, `pyproject.toml` standards. |
| **Workflow** | `workflow-orchestration-patterns` | Temporal, n8n, durable execution. |
| **Backend (FastAPI)**| `fastapi-templates` | API Templates (mapped to `api-patterns`). |
| **MCP** | `mcp-builder` | Building custom MCP servers. |
| **DevOps** | `gcp-cloud-run` | Deploying to Google Cloud Run. |
