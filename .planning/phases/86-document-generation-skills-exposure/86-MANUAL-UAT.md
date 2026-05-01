# Phase 86 Manual UAT — SC4/SC5 (real Gemini routing)

**Phase:** 86 — Document Generation Skills Exposure
**Requirement:** HOTFIX-04 SC4 + SC5 (LLM-routing portion)
**Why manual:** Cannot unit-test "Gemini selects this tool from natural-language prompt" without mocking the entire ADK runtime — brittle, low signal/cost ratio.
**Run after:** Task 2 GREEN + lint + deploy to staging (or `make local-backend` + frontend dev for local UAT).

## Setup
- [ ] Backend running (`make local-backend` OR staging deploy)
- [ ] Frontend dev running (`cd frontend && npm run dev`) OR ADK playground (`make playground`, port 8501, select 'app' folder)
- [ ] Logged in as a test user with at least one initiative/session

## Test 1: PDF report routing (SC4)

**Prompt:** `Create a financial report PDF for Q1 2026 revenue.`

**Expected:**
- [ ] `generate_pdf_report` tool call appears in the trace (frontend network tab OR ADK playground trace pane)
- [ ] Tool call uses `template="financial_report"`
- [ ] Chat response surfaces a downloadable PDF widget (download card)
- [ ] Clicking the widget downloads a `.pdf` file

**Result:** ⬜ PASS / ⬜ FAIL
**Notes:**
**Screenshot / log link:**

## Test 2: Pitch deck routing (SC5)

**Prompt:** `Build me a pitch deck for an AI scheduling startup.`

**Expected:**
- [ ] `generate_pitch_deck` tool call appears in the trace
- [ ] Chat response surfaces a downloadable PPTX widget
- [ ] Clicking the widget downloads a `.pptx` file

**Result:** ⬜ PASS / ⬜ FAIL
**Notes:**
**Screenshot / log link:**

## Sign-off

- [ ] Both tests PASS → SC4 and SC5 LLM-routing portion closed
- [ ] Date executed:
- [ ] Executed by:
- [ ] Build / deploy under test (commit SHA or staging URL):
