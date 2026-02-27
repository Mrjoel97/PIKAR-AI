# Operational Excellence Standards

## 1. Systematic Debugging (`systematic-debugging`)
**Iron Law:** NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.

### The 4-Phase Protocol:
1.  **Root Cause Investigation:**
    -   Read error messages.
    -   Reproduce the issue.
    -   Trace data flow.
    -   **STOP** if guessing.
2.  **Pattern Analysis:**
    -   Compare with working code.
    -   Identify differences.
3.  **Hypothesis & Testing:**
    -   Form *one* hypothesis.
    -   Test minimally.
4.  **Implementation:**
    -   **Write Failing Test First.**
    -   Fix.
    -   Verify.

**Red Flags (STOP IMMEDIATELY):**
-   "Just try this..."
-   "I'll write the test later."
-   3+ failed fix attempts (Question Architecture).

## 2. Test-Driven Development
-   **Red:** Write failing test.
-   **Green:** Make it pass.
-   **Refactor:** Clean up.
-   **Coverage:** Aim for >80%.
