# Plan: Specialized Agent Capabilities

## Goal
Replace mock tools with real, database-backed services (`app/services/`) to enable functional specialized agents.

## Phase 1: Financial Service (FinancialAnalysisAgent)
- [x] Scaffold `financial_service` feature (TDD) [f25ac35]
- [x] Implement `FinancialService` class (Supabase connection) [7459a57]
- [x] Implement `get_revenue_stats` and `get_expense_stats` real logic [e2cf14d]
- [x] Update `FinancialAnalysisAgent` to use `FinancialService` [0fa0863]

## Phase 2: Task & CRM Service (Sales/Operations Agents)
- [x] Scaffold `task_service` feature (TDD) [a49166e]
- [x] Implement `TaskService` (CRUD for `ai_jobs` or new `tasks` table) [c310eaf]
- [x] Update `SalesAgent` and `OperationsAgent` to use `TaskService` [d13aaf5]

## Phase 3: Content Service (ContentCreationAgent)
- [x] Scaffold `content_service` feature (TDD) [ea476a8]
- [x] Enhance `KnowledgeVault` for content generation/storage [689cce7]
- [x] Update `ContentCreationAgent` [c6de4a9]


## Phase Checkpoint [checkpoint: d04d444]
**Summary**: agent_capabilities track complete: Phase 1 (Financial Service), Phase 2 (TaskService CRUD for SalesAgent/OperationsAgent), Phase 3 (ContentService CRUD for ContentCreationAgent, KnowledgeVault enhancement)
