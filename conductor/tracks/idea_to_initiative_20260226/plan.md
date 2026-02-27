# Plan: Idea to Initiative Workflow

This plan outlines the steps to implement the "Idea to Initiative" workflow.

## Phase 1: Backend - Workflow and Tool Creation

- [x] Task: Create a new workflow template for the "Idea to Initiative" workflow in the database.
- [x] Task: Create a new tool for the `strategic_agent` that encapsulates the logic for the "Idea to Initiative" workflow. This tool will take a `braindump_id` as input and will perform the initiative scoping and task generation.
- [ ] Task: Conductor - User Manual Verification 'Backend - Workflow and Tool Creation' (Protocol in workflow.md)

## Phase 2: Frontend - "Create Initiative" Button

- [x] Task: Add a "Create Initiative" button to the `BrainDumpInterface` component.
- [x] Task: When the button is clicked, it should call a new function in `frontend/src/services/initiatives.ts` that triggers the "Idea to Initiative" workflow on the backend.
- [ ] Task: Conductor - User Manual Verification 'Frontend - "Create Initiative" Button' (Protocol in workflow.md)

## Phase 3: Frontend - Workflow Progress and Redirection

- [ ] Task: Implement a mechanism to provide real-time feedback to the user about the progress of the workflow. This can be done using the existing SSE connection.
- [ ] Task: After the workflow is completed, redirect the user to the page for the newly created initiative.
- [ ] Task: Conductor - User Manual Verification 'Frontend - Workflow Progress and Redirection' (Protocol in workflow.md)