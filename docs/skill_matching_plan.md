# Skill Matching Implementation Plan

## Overview
This document outlines the plan to map the remaining "unmapped" skills from the Antigravity Awesome Skills repository to the Pikar AI agents.
Currently, **75 skills** have been successfully mapped and registered in the database.
There are **191 skills** remaining in the filesystem that are not yet assigned to any agent.

## Current State
- **Mapped Skills**: 75 (Populated in `skills` table)
- **Unmapped Skills**: 191 (Available in `antigravity-awesome-skills/skills/`)
- **Agents**: 10 Core Agents (EXEC, STRAT, FIN, CONT, MKT, SALES, OPS, HR, LEGAL, SUPP, DATA)

## Matching Strategy

We will likely use a heuristic semi-automated approach to proposing mappings, followed by manual review.

### Category-Based Mapping Table
We can map general skill categories (inferred from names/content) to agents:

| Skill Keyword/Category | Suggested Agent | Agent ID |
|------------------------|-----------------|----------|
| `seo`, `ads`, `marketing`, `viral` | Marketing Automation | `MKT` |
| `copy`, `blog`, `writing`, `design` | Content Creation | `CONT` |
| `finance`, `budget`, `forecast` | Financial Analysis | `FIN` |
| `recruit`, `onboard`, `interview` | HR Recruitment | `HR` |
| `legal`, `gdpr`, `audit`, `policy` | Compliance Risk | `LEGAL` |
| `sales`, `lead`, `deal`, `crm` | Sales Intelligence | `SALES` |
| `data`, `analytics`, `etl`, `python` | Data Analysis | `DATA` |
| `dev`, `code`, `react`, `debug` | Operations (or Dev/Ops) | `OPS`/`DATA` |
| `plan`, `strategy`, `manage` | Strategic Planning | `STRAT` / `EXEC` |
| `support`, `ticket`, `help` | Customer Support | `SUPP` |

## Proposed Workflow for Unmapped Skills

1.  **Automated Classification**:
    *   Create a script to parse the `description` and `content` of each unmapped skill.
    *   Use an LLM (or keyword matching) to suggest the best 1-2 agents for each skill.
    *   Generate a `proposed_mappings.json` file.

2.  **Review Process**:
    *   Review the JSON file.
    *   Approve or edit specific mappings.

3.  **Registration**:
    *   Once approved, update `app/skills/external_skills.py` (or a new `additional_skills.py`) to formally define these skills as `Skill` objects with the assigned `agent_ids`.
    *   Run the database seed script again to upsert the new mappings.

## Immediate Next Steps (For Approval)
1.  **Approve** the current 75 mapped skills in the database.
2.  **Authorize** the creation of the classification script to categorize the remaining 191 skills.
3.  **Review** the generated mapping proposal before final implementation.

## List of Selected Unmapped Skills (Examples)
- `active-directory-attacks` (Security/Ops?)
- `docker-expert` (Ops)
- `react-best-practices` (Ops/Data/Cont?)
- `salesforce-development` (Sales/Ops)
- `stripe-integration` (Fin/Ops)
