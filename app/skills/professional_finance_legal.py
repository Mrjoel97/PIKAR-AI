"""Professional Finance & Legal/Compliance Skills.

This module provides professional-grade skills for the Finance and
Legal/Compliance agents covering accounting close processes, SOX testing,
contract review, NDA triage, and legal risk frameworks.

Total: 16 skills (7 finance, 9 compliance).
"""

from app.skills.registry import AgentID, Skill, skills_registry


# =============================================================================
# Finance Skills
# =============================================================================

financial_statements_generation = Skill(
    name="financial_statements_generation",
    description="Generate income statements, balance sheets, and cash flow statements with period comparisons and common-size analysis.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.EXEC],
    knowledge_summary=(
        "End-to-end framework for producing the three core financial statements. "
        "Covers revenue recognition, COGS calculation, current/non-current classification, "
        "direct vs indirect cash flow methods, and common-size (vertical %) and horizontal (YoY) analysis."
    ),
    knowledge="""
## Financial Statements Generation Framework

### 1. Income Statement (Profit & Loss)

#### Revenue Recognition (ASC 606 / IFRS 15 Five-Step Model)
1. **Identify the contract** with the customer.
2. **Identify performance obligations** (distinct goods/services).
3. **Determine the transaction price** (variable consideration, discounts, financing).
4. **Allocate the price** to each performance obligation (standalone selling price).
5. **Recognize revenue** when (or as) each obligation is satisfied.

**Common pitfalls:** Recognizing revenue before delivery, ignoring variable consideration constraints, failing to separate bundled obligations.

#### Cost of Goods Sold (COGS) Calculation
- **Manufacturing:** Direct materials + Direct labor + Manufacturing overhead
- **Services:** Direct labor + Direct subcontractor costs + Direct project costs
- **SaaS:** Hosting costs + Third-party license fees + Customer support costs + Implementation costs
- **Retail:** Beginning inventory + Purchases - Ending inventory (FIFO, LIFO, or weighted average)

#### Operating vs Non-Operating Items
| Operating | Non-Operating |
|-----------|---------------|
| Revenue from core business | Interest income/expense |
| COGS, SG&A, R&D | Gains/losses on asset sales |
| Depreciation & amortization | FX gains/losses (non-operational) |
| Restructuring charges (if recurring) | Impairment charges (unusual) |
| Stock-based compensation | Discontinued operations |

#### Income Statement Template
```
Revenue                                         $X,XXX
  Less: Cost of Goods Sold                      (X,XXX)
Gross Profit                                     X,XXX
  Gross Margin %                                  XX.X%

Operating Expenses:
  Selling, General & Administrative              (X,XXX)
  Research & Development                         (X,XXX)
  Depreciation & Amortization                    (X,XXX)
Total Operating Expenses                        (X,XXX)

Operating Income (EBIT)                          X,XXX
  Operating Margin %                              XX.X%

  Interest Expense                               (X,XXX)
  Other Income / (Expense)                        X,XXX
Income Before Tax                                X,XXX

  Income Tax Expense                             (X,XXX)
  Effective Tax Rate %                            XX.X%
Net Income                                       X,XXX
  Net Margin %                                    XX.X%

Earnings Per Share (Basic)                       $X.XX
Earnings Per Share (Diluted)                     $X.XX
```

### 2. Balance Sheet

#### Current vs Non-Current Classification
- **Current assets:** Cash, marketable securities, accounts receivable, inventory, prepaid expenses (convertible to cash within 12 months).
- **Non-current assets:** Property/plant/equipment (PP&E), intangible assets, goodwill, long-term investments, deferred tax assets.
- **Current liabilities:** Accounts payable, accrued expenses, short-term debt, current portion of long-term debt, deferred revenue (current), taxes payable.
- **Non-current liabilities:** Long-term debt, deferred tax liabilities, pension obligations, long-term lease liabilities.

#### Balance Sheet Template
```
ASSETS
Current Assets:
  Cash and Cash Equivalents                      $X,XXX
  Short-Term Investments                          X,XXX
  Accounts Receivable, net                        X,XXX
  Inventory                                       X,XXX
  Prepaid Expenses                                X,XXX
Total Current Assets                              X,XXX

Non-Current Assets:
  Property, Plant & Equipment, net                X,XXX
  Goodwill                                        X,XXX
  Intangible Assets, net                          X,XXX
  Other Long-Term Assets                          X,XXX
Total Non-Current Assets                          X,XXX

TOTAL ASSETS                                      X,XXX

LIABILITIES & EQUITY
Current Liabilities:
  Accounts Payable                                X,XXX
  Accrued Expenses                                X,XXX
  Short-Term Debt                                 X,XXX
  Deferred Revenue (current)                      X,XXX
Total Current Liabilities                         X,XXX

Non-Current Liabilities:
  Long-Term Debt                                  X,XXX
  Deferred Tax Liabilities                        X,XXX
  Other Long-Term Liabilities                     X,XXX
Total Non-Current Liabilities                     X,XXX

TOTAL LIABILITIES                                 X,XXX

Shareholders' Equity:
  Common Stock                                    X,XXX
  Additional Paid-In Capital                      X,XXX
  Retained Earnings                               X,XXX
  Accumulated Other Comprehensive Income          X,XXX
  Treasury Stock                                 (X,XXX)
Total Shareholders' Equity                        X,XXX

TOTAL LIABILITIES & EQUITY                        X,XXX
```

### 3. Cash Flow Statement

#### Direct vs Indirect Method
- **Indirect method** (most common): Start with net income, adjust for non-cash items and changes in working capital.
- **Direct method:** Report actual cash receipts (collections from customers) and cash payments (to suppliers, employees). More transparent but rarely used.

#### Cash Flow Statement Template (Indirect Method)
```
OPERATING ACTIVITIES
  Net Income                                      $X,XXX
  Adjustments for non-cash items:
    Depreciation & Amortization                    X,XXX
    Stock-Based Compensation                       X,XXX
    Deferred Income Taxes                          X,XXX
    Other non-cash items                           X,XXX
  Changes in working capital:
    (Increase)/Decrease in Accounts Receivable    (X,XXX)
    (Increase)/Decrease in Inventory              (X,XXX)
    Increase/(Decrease) in Accounts Payable        X,XXX
    Increase/(Decrease) in Deferred Revenue        X,XXX
    Other working capital changes                  X,XXX
Net Cash from Operating Activities                 X,XXX

INVESTING ACTIVITIES
  Capital Expenditures                            (X,XXX)
  Acquisitions                                    (X,XXX)
  Purchases of Investments                        (X,XXX)
  Proceeds from Sales of Investments               X,XXX
Net Cash from Investing Activities                (X,XXX)

FINANCING ACTIVITIES
  Proceeds from Debt Issuance                      X,XXX
  Repayments of Debt                              (X,XXX)
  Proceeds from Stock Issuance                     X,XXX
  Share Repurchases                               (X,XXX)
  Dividends Paid                                  (X,XXX)
Net Cash from Financing Activities                (X,XXX)

Net Change in Cash                                 X,XXX
Cash at Beginning of Period                        X,XXX
Cash at End of Period                             $X,XXX

Free Cash Flow = Operating Cash Flow - CapEx      $X,XXX
```

### 4. Period-Over-Period Comparison

#### Common-Size Analysis (Vertical %)
Express every line item as a percentage of a base:
- Income statement: each item as % of Revenue
- Balance sheet: each item as % of Total Assets

**Use case:** Compare companies of different sizes; spot margin shifts.

#### Horizontal Analysis (YoY Change)
For each line item calculate:
- **Dollar change:** Current Period - Prior Period
- **Percentage change:** (Current - Prior) / Prior * 100
- **Flag items:** >10% change or >$X threshold for management narrative

#### Trend Analysis
- Calculate 3-year or 5-year CAGR for key metrics (revenue, EBITDA, net income, free cash flow).
- Plot quarterly trends to identify seasonality.
- Compare growth rates across segments.
""",
)


variance_analysis = Skill(
    name="variance_analysis",
    description="Decompose financial variances into actionable drivers with price, volume, mix, and FX analysis.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.DATA, AgentID.STRAT],
    knowledge_summary=(
        "Framework for decomposing budget-vs-actual variances into price, volume, mix, and FX components. "
        "Includes waterfall methodology, materiality thresholds, narrative templates, and root cause categories."
    ),
    knowledge="""
## Variance Analysis Framework

### 1. Budget vs Actual vs Forecast Framework

| Comparison | Purpose | Frequency |
|------------|---------|-----------|
| **Actual vs Budget** | Accountability to annual plan | Monthly |
| **Actual vs Forecast** | Accuracy of latest outlook | Monthly |
| **Forecast vs Budget** | Explain plan trajectory changes | Quarterly |
| **Actual vs Prior Year** | Year-over-year trend assessment | Monthly |

### 2. Variance Decomposition

#### Price Variance
```
Price Variance = (Actual Price - Budgeted Price) x Actual Volume
```
**Drivers:** Pricing changes, discount levels, promotional activity, contract renegotiations.

#### Volume Variance
```
Volume Variance = (Actual Volume - Budgeted Volume) x Budgeted Price
```
**Drivers:** Demand shifts, new customer wins/losses, seasonality, market share changes.

#### Mix Variance
```
Mix Variance = (Actual Mix % - Budgeted Mix %) x Actual Total Volume x Budgeted Margin
```
**Drivers:** Product/service mix shift toward higher or lower margin offerings, geographic mix, channel mix.

#### FX Variance (for multinational businesses)
```
FX Variance = Actual Local Currency Revenue x (Actual FX Rate - Budgeted FX Rate)
```
**Constant currency growth:** Calculate growth using prior period exchange rates to isolate operational performance from currency effects.

#### Combined Decomposition Example
```
Total Revenue Variance:        +$500K favorable
  Price Variance:              +$200K (price increase took effect in Q2)
  Volume Variance:             +$400K (new enterprise client onboarded)
  Mix Variance:                -$150K (higher share of standard vs premium tier)
  FX Variance:                 +$50K  (EUR strengthened vs USD)
```

### 3. Waterfall Analysis Methodology

Build a waterfall chart moving from Budget to Actual:
1. Start bar: Budget amount
2. Sequential bridges: Each variance driver as positive (green) or negative (red) bar
3. End bar: Actual amount
4. Order drivers by magnitude (largest impact first)

**Best practice:** Limit to 5-8 drivers. Combine small items into "Other" bucket.

### 4. Materiality Thresholds

| Metric | Material If | Action Required |
|--------|------------|-----------------|
| Revenue line item | > 5% or > $100K | Full root cause analysis |
| Expense line item | > 10% or > $50K | Manager explanation |
| Gross margin % | > 200 bps | Executive briefing |
| Any line item | > 20% | Investigate immediately |

**De minimis rule:** Variances under $10K AND under 3% need no narrative.

### 5. Narrative Explanation Templates

**Revenue favorable:**
> "Revenue was ${amount} ({pct}%) above plan, driven primarily by {driver_1} (+${amount_1}), partially offset by {driver_2} (-${amount_2}). {Forward-looking implication}."

**Expense unfavorable:**
> "{Category} expense exceeded budget by ${amount} ({pct}%), primarily due to {driver} which was {root_cause}. Management action: {corrective_action}. Expected normalization by {timeline}."

**On plan:**
> "{Line item} tracked to plan within {threshold}%. No material variances to report."

### 6. Root Cause Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Timing** | Expense/revenue shifted between periods | Delayed project launch pushed Q3 revenue to Q4 |
| **Volume** | Units sold/produced differ from plan | Higher-than-expected demand from new segment |
| **Rate** | Price/cost per unit differs | Supplier renegotiation lowered unit cost by 8% |
| **One-time** | Non-recurring item not in budget | Legal settlement, one-time bonus, asset write-down |
| **Structural** | Permanent business change | New product line, acquisition, divestiture |
| **FX** | Currency movement impact | EUR depreciation vs USD reduced translated revenue |
| **Accounting** | Reclassification or methodology change | Changed capitalization policy for software dev costs |

### 7. Variance Analysis Process

1. **Extract data:** Pull actual, budget, and forecast from GL/ERP.
2. **Calculate variances:** Dollar and percentage for each line.
3. **Filter material items:** Apply materiality thresholds.
4. **Decompose drivers:** Break material variances into price/volume/mix/FX.
5. **Gather narrative:** Contact budget owners for root cause explanations.
6. **Assess trend:** Compare current month variance direction to prior months.
7. **Recommend action:** Propose corrective actions for unfavorable structural variances.
8. **Package output:** Waterfall chart + executive summary + detail appendix.
""",
)


journal_entry_preparation = Skill(
    name="journal_entry_preparation",
    description="Prepare proper journal entries with double-entry fundamentals, accruals, deferrals, and month-end standard entries.",
    category="finance",
    agent_ids=[AgentID.FIN],
    knowledge_summary=(
        "Comprehensive journal entry preparation guide covering double-entry accounting, "
        "common entry types (accruals, deferrals, depreciation, FX revaluation, intercompany), "
        "supporting documentation, approval workflows, and month-end standard entry checklists."
    ),
    knowledge="""
## Journal Entry Preparation Guide

### 1. Double-Entry Accounting Fundamentals

Every transaction affects at least two accounts. Total debits must equal total credits.

**Account Types and Normal Balances:**
| Account Type | Normal Balance | Debit Increases | Credit Increases |
|-------------|---------------|-----------------|------------------|
| Assets | Debit | Yes | No |
| Liabilities | Credit | No | Yes |
| Equity | Credit | No | Yes |
| Revenue | Credit | No | Yes |
| Expenses | Debit | Yes | No |
| Contra-Assets | Credit | No | Yes |

**Golden Rules:**
- Assets = Liabilities + Equity (must always balance)
- Revenue increases equity; Expenses decrease equity
- Every journal entry needs: date, accounts, amounts, description, supporting reference

### 2. Common Journal Entry Types

#### Accruals (recognize before cash moves)
```
Accrued Revenue:
  DR  Accounts Receivable        $10,000
    CR  Revenue                            $10,000
  Ref: Service delivered per SOW #1234, invoice pending

Accrued Expense:
  DR  Professional Fees Expense  $5,000
    CR  Accrued Liabilities               $5,000
  Ref: Legal services received Dec, invoice expected Jan
```

#### Deferrals (cash moves before recognition)
```
Prepaid Expense (at payment):
  DR  Prepaid Insurance          $12,000
    CR  Cash                               $12,000
  Ref: Annual insurance premium, policy #INS-2025

Monthly Amortization of Prepaid:
  DR  Insurance Expense          $1,000
    CR  Prepaid Insurance                  $1,000
  Ref: Monthly amortization of annual premium (1/12)

Deferred Revenue (at collection):
  DR  Cash                       $24,000
    CR  Deferred Revenue                   $24,000
  Ref: Annual SaaS subscription collected upfront

Monthly Revenue Recognition:
  DR  Deferred Revenue           $2,000
    CR  Subscription Revenue               $2,000
  Ref: Monthly recognition of annual subscription (1/12)
```

#### Depreciation & Amortization
```
Depreciation:
  DR  Depreciation Expense       $2,500
    CR  Accumulated Depreciation           $2,500
  Ref: Monthly depreciation, server equipment, 4-yr SL

Amortization of Intangibles:
  DR  Amortization Expense       $1,667
    CR  Accumulated Amortization           $1,667
  Ref: Patent amortization, 5-yr SL, acquired Jan 2024
```

#### Provisions
```
Bad Debt Provision:
  DR  Bad Debt Expense           $3,000
    CR  Allowance for Doubtful Accounts    $3,000
  Ref: Monthly provision based on aging analysis (2% of 90+ day AR)

Warranty Provision:
  DR  Warranty Expense           $8,000
    CR  Warranty Provision Liability        $8,000
  Ref: Estimated warranty claims, 1.5% of monthly revenue
```

#### FX Revaluation
```
Unrealized FX Gain:
  DR  Accounts Receivable (EUR)  $1,200
    CR  FX Gain (Unrealized)               $1,200
  Ref: Month-end revaluation, EUR/USD 1.08 -> 1.10

Unrealized FX Loss:
  DR  FX Loss (Unrealized)      $800
    CR  Accounts Payable (GBP)             $800
  Ref: Month-end revaluation, GBP/USD 1.27 -> 1.26
```

#### Intercompany Entries
```
Parent books:
  DR  Intercompany Receivable - Sub A     $50,000
    CR  Management Fee Revenue                     $50,000

Subsidiary A books:
  DR  Management Fee Expense              $50,000
    CR  Intercompany Payable - Parent              $50,000
  Ref: Monthly management fee per intercompany agreement
```

#### Tax Provision
```
Current Tax:
  DR  Income Tax Expense         $25,000
    CR  Income Tax Payable                 $25,000

Deferred Tax (timing difference):
  DR  Deferred Tax Asset         $3,000
    CR  Deferred Tax Benefit               $3,000
  Ref: Temporary difference from depreciation method variance
```

### 3. Supporting Documentation Requirements

Every journal entry must have:
1. **Entry ID** (auto-generated or sequential)
2. **Posting date** and **period**
3. **Preparer name** and **date prepared**
4. **Approver name** and **date approved**
5. **Description/purpose** (clear enough for an auditor)
6. **Supporting calculation** or invoice reference
7. **Account codes** (per chart of accounts)
8. **Attachment:** Invoice, contract, calculation workbook, or email approval

### 4. Approval Workflow

| Entry Amount | Preparer | Approver |
|-------------|----------|----------|
| < $5,000 | Staff Accountant | Senior Accountant |
| $5,000 - $50,000 | Senior Accountant | Accounting Manager |
| $50,000 - $250,000 | Accounting Manager | Controller |
| > $250,000 | Controller | CFO |
| Non-standard/unusual (any amount) | Any | Controller + CFO |

### 5. Reversing Entries
- Accruals made at month-end should auto-reverse on Day 1 of the next month.
- Tag reversing entries with "AUTO-REV" prefix.
- Verify reversals posted before recording new accruals.
- Never reverse: depreciation, amortization, provisions (unless explicitly released).

### 6. Month-End Standard Entries Checklist

| # | Entry | Frequency | Owner |
|---|-------|-----------|-------|
| 1 | Revenue accruals | Monthly | Revenue Accountant |
| 2 | Expense accruals (vendors, payroll) | Monthly | AP / Payroll |
| 3 | Prepaid amortization | Monthly | GL Accountant |
| 4 | Depreciation & amortization | Monthly | Fixed Assets |
| 5 | Bad debt provision | Monthly | AR Manager |
| 6 | Inventory reserves | Monthly | Cost Accountant |
| 7 | FX revaluation | Monthly | Treasury |
| 8 | Intercompany entries | Monthly | IC Accountant |
| 9 | Tax provision (current + deferred) | Monthly/Quarterly | Tax |
| 10 | Deferred revenue recognition | Monthly | Revenue Accountant |
| 11 | Lease accounting (ASC 842) | Monthly | GL Accountant |
| 12 | Stock-based compensation | Monthly | Equity Admin |
""",
)


month_end_close_management = Skill(
    name="month_end_close_management",
    description="Manage the month-end close process with task sequencing, checklists, and close calendar.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.OPS],
    knowledge_summary=(
        "Complete month-end close management framework with a Day 1-10 calendar, "
        "task dependencies, pre-close/close/post-close checklists, critical path items, "
        "KPIs (close duration, error rate), and continuous improvement practices."
    ),
    knowledge="""
## Month-End Close Management Framework

### 1. Standard Close Calendar (10 Business Day Target)

#### Pre-Close (Business Day -3 to Day 0 = last day of month)
| Day | Task | Owner | Dependency |
|-----|------|-------|------------|
| BD-3 | Send close schedule & reminders to all departments | Controller | None |
| BD-2 | Confirm all vendor invoices received or accrued | AP Manager | None |
| BD-1 | Complete bank reconciliation through prior day | Treasury | Bank feeds |
| BD-1 | Cut off: no new POs without Controller approval | Procurement | None |
| Day 0 | Final revenue cut-off applied | Revenue Accounting | Billing system |
| Day 0 | Final cash receipts posted | AR / Treasury | Bank feed |

#### Close Period (Business Day 1-7)
| Day | Task | Owner | Dependency |
|-----|------|-------|------------|
| BD1 | Post auto-reversing entries from prior month | GL Accountant | System job |
| BD1 | Complete subledger close (AP, AR, FA, Inventory) | Subledger Owners | Cutoff |
| BD2 | Post payroll journal entries | Payroll | Payroll processing |
| BD2 | Post depreciation and amortization | Fixed Assets | FA subledger close |
| BD3 | Post revenue accruals and deferred revenue | Revenue Accounting | Revenue cutoff |
| BD3 | Post expense accruals | AP / GL | Invoice cutoff |
| BD3 | Post intercompany entries | IC Accountant | Subledger closes |
| BD4 | Complete intercompany reconciliation | IC Accountant | IC entries posted |
| BD4 | Post FX revaluation entries | Treasury | Month-end rates |
| BD5 | Complete all balance sheet reconciliations | GL Team | All entries posted |
| BD5 | Perform flux analysis (P&L and BS) | FP&A / GL | Trial balance ready |
| BD6 | Post adjusting entries from reconciliation review | GL Accountant | Recon review |
| BD6 | Post tax provision (current + deferred) | Tax | Pre-tax income final |
| BD7 | Final trial balance review | Controller | All entries posted |
| BD7 | Lock the period in ERP | Controller | Final review |

#### Post-Close (Business Day 8-10)
| Day | Task | Owner | Dependency |
|-----|------|-------|------------|
| BD8 | Prepare management reporting package | FP&A | Locked period |
| BD8 | Generate financial statements | FP&A / GL | Locked period |
| BD9 | Variance analysis and commentary | FP&A | Statements ready |
| BD9 | Distribute flash report to leadership | FP&A | Variance analysis |
| BD10 | Close retrospective meeting | Controller | All deliverables |
| BD10 | Update close checklist for next month | GL Manager | Retrospective |

### 2. Critical Path Items

These items gate downstream tasks. Delays here cascade through the entire close:
1. **Revenue cutoff** (gates all P&L analysis)
2. **Subledger closes** (gates GL reconciliation)
3. **Intercompany reconciliation** (gates consolidated reporting)
4. **Tax provision** (gates final net income)
5. **Controller final review** (gates period lock)

### 3. Pre-Close Checklist

- [ ] All bank accounts reconciled through month-end
- [ ] Subledger balances agree to GL (AP, AR, FA, Inventory)
- [ ] All recurring journal entries templates reviewed and updated
- [ ] Accrual estimates reviewed (compare prior month actuals to accruals)
- [ ] Intercompany balances confirmed bilaterally
- [ ] Cutoff procedures communicated to business units
- [ ] FX rates sourced and loaded
- [ ] Payroll processing complete
- [ ] Credit card statements imported and coded

### 4. Close Checklist

- [ ] All standard monthly journal entries posted
- [ ] All adjusting entries posted with supporting documentation
- [ ] All balance sheet accounts reconciled (100% coverage)
- [ ] Flux analysis completed for all P&L line items (>5% threshold)
- [ ] Flux analysis completed for all BS line items (>10% threshold)
- [ ] Intercompany eliminations posted
- [ ] Consolidated trial balance balanced
- [ ] Management review completed and sign-off obtained
- [ ] Period locked in ERP

### 5. Post-Close Checklist

- [ ] Financial statements generated and distributed
- [ ] Variance commentary provided for all material items
- [ ] Flash report sent to leadership
- [ ] Board reporting package updated (if applicable)
- [ ] Deferred items logged for next month
- [ ] Close retrospective conducted
- [ ] Process improvements documented

### 6. KPIs for Close Process

| KPI | Target | Measurement |
|-----|--------|-------------|
| Close duration | <= 7 business days | Period lock date - month end |
| Post-close adjustments | < 3 per month | Count of entries after period lock |
| Reconciliation completion | 100% by BD5 | % of accounts reconciled on time |
| Flux items explained | 100% of material | % of flagged items with narrative |
| Error rate | < 1% | Correcting entries / total entries |
| On-time task completion | > 95% | Tasks done by scheduled day |

### 7. Continuous Improvement

- **Automate recurring entries:** Template them in ERP; review annually.
- **Reduce manual reconciliations:** Implement auto-matching rules (80/20).
- **Shorten close by 1 day each quarter:** Identify and eliminate the longest bottleneck.
- **Post-mortem every close:** What went wrong? What can we automate? What took longest?
- **Stagger hard closes:** Close subledgers 1 day earlier each quarter.
""",
)


account_reconciliation = Skill(
    name="account_reconciliation",
    description="Reconcile bank accounts, subledgers, and intercompany balances with aging analysis and exception handling.",
    category="finance",
    agent_ids=[AgentID.FIN],
    knowledge_summary=(
        "Account reconciliation methodology covering bank reconciliation, subledger-to-GL, "
        "intercompany, three-way match, aging analysis, auto-reconciliation rules, "
        "escalation thresholds, and exception handling procedures."
    ),
    knowledge="""
## Account Reconciliation Methodology

### 1. Core Reconciliation Principle

```
Opening Balance + Additions - Deductions = Closing Balance

GL Balance +/- Reconciling Items = External/Subledger Balance
```

Every reconciliation proves that two independent records of the same balance agree, or that differences are identified, explained, and tracked to resolution.

### 2. Bank Reconciliation Process

**Step-by-step:**
1. Obtain bank statement (electronic feed or PDF) as of month-end.
2. Obtain GL cash balance as of month-end.
3. Match cleared items (deposits, withdrawals, fees) between bank and GL.
4. Identify reconciling items:

```
Bank Statement Balance                          $XXX,XXX
  Add: Deposits in Transit (recorded in GL,
       not yet on bank statement)               + $X,XXX
  Less: Outstanding Checks (recorded in GL,
        not yet cleared at bank)                - $X,XXX
  Other: Bank errors                            +/- $XXX
Adjusted Bank Balance                           $XXX,XXX

GL Cash Balance                                 $XXX,XXX
  Add: Interest earned (on bank stmt,
       not yet in GL)                           + $XXX
  Less: Bank fees (on bank stmt,
        not yet in GL)                          - $XXX
  Other: Book errors                            +/- $XXX
Adjusted Book Balance                           $XXX,XXX

** Adjusted Bank Balance MUST equal Adjusted Book Balance **
```

5. Investigate stale items (outstanding checks > 90 days, deposits in transit > 5 days).
6. Post adjusting entries for items on bank statement not yet in GL.
7. Document, sign, and file.

### 3. Subledger-to-GL Reconciliation

| Subledger | GL Account(s) | Key Checks |
|-----------|---------------|------------|
| Accounts Receivable | AR Control | Aging = GL balance, credit balances reviewed |
| Accounts Payable | AP Control | Open items = GL balance, debit balances reviewed |
| Fixed Assets | FA accounts + Accum Depr | Additions/disposals tie to support; depreciation calc verified |
| Inventory | Inventory Control | Quantities match warehouse; reserves reviewed |
| Payroll | Payroll liability | Net pay + taxes + benefits = GL postings |

**Process:**
1. Run subledger trial balance as of month-end.
2. Run GL trial balance for the control account.
3. Agree totals; if different, identify the gap.
4. Common discrepancies: timing (entry in subledger but not GL), posting errors, duplicate entries, unposted batches.

### 4. Intercompany Reconciliation

1. Each entity reports its intercompany receivable/payable by counterparty.
2. Match bilaterally: Entity A's receivable from B = Entity B's payable to A.
3. Tolerance: Differences < $100 (or local equivalent) may be auto-resolved.
4. Above tolerance: Investigate (timing, FX rate differences, unrecorded transactions).
5. Both entities must agree before elimination entries are posted.

### 5. Three-Way Match (Procurement)

```
Purchase Order (PO)  <-->  Goods Receipt (GR)  <-->  Vendor Invoice

All three must agree on:
  - Quantity
  - Unit price
  - Total amount
  - Item description
```

**Exception handling:**
| Mismatch Type | Threshold | Action |
|---------------|-----------|--------|
| Price variance | < 2% or < $50 | Auto-approve |
| Price variance | 2-10% or $50-$500 | Buyer review |
| Price variance | > 10% or > $500 | Manager approval required |
| Quantity variance | +/- 5% | Receiving verification |
| Quantity variance | > 5% | Buyer + receiving investigation |

### 6. Reconciliation Template

```
Account: [Account Name - Account Number]
Period: [Month Year]
Preparer: [Name]          Date: [Date]
Reviewer: [Name]          Date: [Date]

Section A: Balance Comparison
  GL Balance (per trial balance):               $XX,XXX.XX
  External/Subledger Balance:                   $XX,XXX.XX
  Difference:                                   $XX,XXX.XX

Section B: Reconciling Items
  # | Description | Amount | Aging | Status | Expected Resolution
  1 | [item]      | $X,XXX | 15 days | Open | [date / action]
  2 | [item]      | $X,XXX | 45 days | Escalated | [date / action]
  Total Reconciling Items:                      $XX,XXX.XX

Section C: Adjusted Balance Comparison
  GL Balance + Adjustments:                     $XX,XXX.XX
  External Balance + Adjustments:               $XX,XXX.XX
  Net Difference (must be $0):                  $0.00

Section D: Sign-off
  Preparer Certification: Reconciliation is complete and accurate.
  Reviewer Certification: Reviewed and approved.
```

### 7. Aging Analysis for Reconciling Items

| Age Bucket | Status | Required Action |
|------------|--------|-----------------|
| 0-30 days | Current | Monitor; expected to clear |
| 31-60 days | Aging | Investigate; document root cause |
| 61-90 days | Escalated | Manager review; remediation plan |
| > 90 days | Critical | Controller review; write-off consideration |

### 8. Auto-Reconciliation Rules

Configure ERP/reconciliation tool to auto-match:
- **Exact match:** Same date, same amount, same reference -> auto-clear.
- **Tolerance match:** Same reference, amount within $1 -> auto-clear, post rounding entry.
- **One-to-many:** One bank deposit matches multiple GL entries summing to same amount.
- **Many-to-one:** Multiple small checks match one bank clearing entry.
- **Rule-based:** Recurring items (monthly bank fees, interest) -> template match.

**Target auto-reconciliation rate:** >80% of line items matched automatically.

### 9. Escalation Thresholds

| Condition | Escalate To | Timeline |
|-----------|-------------|----------|
| Reconciling item > $10K | Accounting Manager | Within 2 business days |
| Reconciling item > $50K | Controller | Within 1 business day |
| Unresolved item > 60 days | Controller | Immediate |
| Suspected fraud indicator | Controller + Internal Audit | Immediate |
| Account cannot be reconciled | Controller | Same day |
""",
)


sox_testing_methodology = Skill(
    name="sox_testing_methodology",
    description="SOX 404 compliance testing with control identification, risk assessment, sample selection, and deficiency classification.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.LEGAL],
    knowledge_summary=(
        "SOX 404 testing framework covering control identification (preventive/detective, manual/automated), "
        "risk assessment, sample selection methodology, testing procedures, deficiency classification "
        "(deficiency/significant deficiency/material weakness), and documentation standards."
    ),
    knowledge="""
## SOX 404 Compliance Testing Methodology

### 1. Control Identification

#### Control Classification Matrix
| Dimension | Types | Examples |
|-----------|-------|---------|
| **Timing** | Preventive / Detective | Approval before payment (P) vs Bank recon review (D) |
| **Nature** | Manual / Automated / IT-Dependent Manual | Manual review (M) vs System edit check (A) vs System-generated report reviewed manually (ITDM) |
| **Frequency** | Transaction-level / Periodic | Each invoice approved (T) vs Monthly reconciliation (P) |
| **Assertion** | Existence, Completeness, Valuation, Rights, Presentation | Revenue cutoff (Completeness, Existence) |

#### Key Controls vs Non-Key Controls
- **Key control:** Failure could reasonably result in a material misstatement not being prevented or detected.
- **Non-key control:** Provides comfort but is not the primary control preventing material misstatement.
- **Focus testing on key controls.** Non-key controls documented but tested only if compensating.

### 2. Risk Assessment (What Could Go Wrong - WCGW)

For each significant account / business process:
1. **Identify assertions at risk** (existence, completeness, valuation, rights & obligations, presentation).
2. **Determine what could go wrong:**
   - Revenue: Fictitious revenue recorded, revenue recognized in wrong period, returns not recorded.
   - Expenses: Unauthorized purchases, duplicate payments, unrecorded liabilities.
   - Cash: Unauthorized disbursements, unrecorded receipts, misappropriation.
3. **Map controls to WCGW:** Each WCGW must have at least one key control.
4. **Assess inherent risk** (High/Medium/Low) and **control risk** (based on design and operating effectiveness).

### 3. Sample Selection Methodology

#### Population and Sample Sizes

| Control Frequency | Population Size | Sample Size (Low Risk) | Sample Size (High Risk) |
|-------------------|----------------|----------------------|------------------------|
| Annual | 1 | 1 | 1 |
| Quarterly | 4 | 2 | 4 |
| Monthly | 12 | 2-4 | 5-6 |
| Weekly | 52 | 5-10 | 15-20 |
| Daily | ~250 | 20-25 | 25-40 |
| Per transaction | Varies | See below | See below |

**Transaction-level controls (per occurrence):**
| Population Size | Minimum Sample |
|----------------|---------------|
| 1-5 items | All items |
| 6-50 items | 5-8 items |
| 51-250 items | 10-15 items |
| 251-1,000 items | 20-25 items |
| > 1,000 items | 25-40 items |

#### Selection Methods
- **Random:** Use random number generator; ensure coverage across full period.
- **Systematic:** Every Nth item (e.g., every 10th transaction).
- **Haphazard:** Select without pattern; acceptable for small populations.
- **Stratified:** Divide population into strata (e.g., by amount), sample from each.
- **Judgmental:** Target specific items (high-risk, unusual, period-end); supplement with random.

### 4. Testing Procedures

#### Inquiry
- Interview control owner about how the control operates.
- **Alone, inquiry is never sufficient** -- must be corroborated by another procedure.
- Document: Who was interviewed, date, key statements made.

#### Observation
- Watch the control being performed in real time.
- Useful for: physical controls, system demonstrations, segregation of duties.
- Document: What was observed, date, who performed the control.

#### Inspection (Examination of Evidence)
- Review documents and records that provide evidence of control performance.
- Look for: signatures, dates, evidence of review (checkmarks, initials, comments), system timestamps.
- Document: What was inspected, whether evidence was present, any exceptions.

#### Re-performance
- Independently re-execute the control to verify the same conclusion.
- Strongest form of evidence.
- Examples: Re-perform a reconciliation, re-calculate a formula, re-run a report and compare.
- Document: Steps performed, results, whether they agreed with original.

### 5. Deficiency Classification

```
         Control     Significant     Material
        Deficiency   Deficiency      Weakness
           |             |              |
  Minor gap in      Reasonable       Reasonable
  control design    possibility      possibility
  or operation.     that a more-     that a MATERIAL
  Low likelihood    than-trivial     misstatement
  of material       misstatement     will not be
  misstatement.     not prevented    prevented or
                    or detected.     detected.
```

| Classification | Severity | Reporting | Remediation |
|---------------|----------|-----------|-------------|
| **Control Deficiency** | Low | Internal reporting to management | Fix within 90 days |
| **Significant Deficiency** | Medium | Report to Audit Committee | Fix within 60 days; compensating controls |
| **Material Weakness** | High | Public disclosure in 10-K/10-Q | Immediate remediation plan; restatement risk |

**Aggregation:** Multiple control deficiencies in the same process area or affecting the same assertion may aggregate to a significant deficiency or material weakness.

### 6. Remediation Tracking

For each deficiency found:
1. **Description:** What is the gap?
2. **Root cause:** Why did it happen? (Training, system, process, people, oversight)
3. **Remediation plan:** Specific steps to fix (redesign control, add review, implement system check)
4. **Owner:** Who is responsible for the fix?
5. **Target date:** When will remediation be complete?
6. **Validation:** How will we confirm the fix works? (Re-test after implementation)
7. **Status:** Open / In Progress / Remediated / Validated

### 7. Documentation Standards (Who/What/When/How)

Every test must document:
- **Who:** Tester name and qualifications.
- **What:** Control tested, assertion addressed, WCGW mitigated.
- **When:** Test date, period covered, sample items tested (with references).
- **How:** Procedures performed (inquiry + inspection + re-performance).
- **Result:** Pass / Fail / Exception noted.
- **Conclusion:** Control is operating effectively / deficiency identified.
- **Evidence:** Attached or cross-referenced to workpaper.

**Workpaper retention:** 7 years minimum for SOX documentation.
""",
)


audit_support_framework = Skill(
    name="audit_support_framework",
    description="Support internal and external audits with PBC list management, walkthrough preparation, and finding remediation.",
    category="finance",
    agent_ids=[AgentID.FIN, AgentID.LEGAL],
    knowledge_summary=(
        "End-to-end audit support framework covering preparation checklists, PBC list management, "
        "document organization, walkthrough preparation, common audit requests by area, "
        "response timeline management, and finding remediation tracking."
    ),
    knowledge="""
## Audit Support Framework

### 1. Audit Preparation Checklist

**8 Weeks Before Audit Fieldwork:**
- [ ] Confirm audit scope, timing, and team with auditors
- [ ] Designate internal audit liaison (single point of contact)
- [ ] Reserve conference room / set up virtual workspace for auditors
- [ ] Review prior year findings and confirm remediation status
- [ ] Update process narratives and flowcharts
- [ ] Confirm SOX control documentation is current
- [ ] Pre-populate PBC list with standing items

**4 Weeks Before:**
- [ ] Distribute PBC list to all preparers with deadlines
- [ ] Schedule walkthrough sessions with process owners
- [ ] Prepare opening trial balance and financial statements
- [ ] Organize supporting schedules (roll-forwards, reconciliations)
- [ ] Test all system access for auditors (read-only ERP/GL access)
- [ ] Brief department heads on audit timeline and expectations

**1 Week Before:**
- [ ] Confirm all PBC items are collected or have firm delivery dates
- [ ] Conduct dry-run walkthroughs with process owners
- [ ] Verify all reconciliations are complete and reviewed
- [ ] Prepare "state of the business" brief for opening meeting
- [ ] Confirm auditor logistics (badge access, Wi-Fi, parking)

### 2. PBC (Prepared by Client) List Management

#### PBC Tracking Template
| # | Item Description | Area | Preparer | Reviewer | Due Date | Status | Delivered Date | Notes |
|---|-----------------|------|----------|----------|----------|--------|---------------|-------|
| 1 | Bank confirmations | Cash | Treasury | Controller | Week 1 | Delivered | 01/15 | Sent directly to auditor |
| 2 | AR aging at 12/31 | Revenue | AR Mgr | Controller | Week 1 | In Progress | -- | Generating from system |

**Status codes:** Not Started / In Progress / Under Review / Delivered / N/A

**Best practices:**
- Use a shared tracker (SharePoint, Google Sheets) with real-time status.
- Assign every item a single preparer AND reviewer.
- Build in 3-day buffer before auditor due date.
- Provide items in a consistent format (PDF for final, Excel for supporting data).
- Name files systematically: `PBC-[###]-[Description]-[Period].xlsx`

### 3. Document Organization

**Folder structure for audit:**
```
/Audit-FY2025/
  /01-Financial-Statements/
    Trial-balance-12-31-2025.xlsx
    Income-statement-FY2025.pdf
    Balance-sheet-12-31-2025.pdf
    Cash-flow-statement-FY2025.pdf
  /02-Revenue/
    Revenue-detail-by-month.xlsx
    Top-20-customers-confirmation.pdf
    Deferred-revenue-rollforward.xlsx
    Revenue-recognition-memos/
  /03-Expenses/
    Expense-detail-by-account.xlsx
    Vendor-confirmations/
    Accrual-support/
  /04-Cash/
    Bank-reconciliations/
    Bank-confirmations/
    Investment-statements/
  /05-Fixed-Assets/
    FA-rollforward.xlsx
    Addition-support/
    Disposal-support/
    Depreciation-schedule.xlsx
  /06-Payroll/
    Payroll-registers/
    Benefits-reconciliation/
    Headcount-analysis.xlsx
  /07-Equity/
    Stock-option-activity.xlsx
    Share-repurchase-support/
  /08-Tax/
    Tax-provision-workpaper.xlsx
    Deferred-tax-rollforward.xlsx
  /09-SOX-Controls/
    Control-matrix.xlsx
    Test-workpapers/
    Deficiency-tracker.xlsx
  /10-Other/
    Management-representation-letter.docx
    Legal-confirmations/
    Related-party-transactions/
```

### 4. Walkthrough Preparation

**What auditors expect in a walkthrough:**
- Process owner explains the process end-to-end (from initiation to recording).
- Live demonstration in the system (show actual transactions).
- Show control evidence (approvals, reconciliations, review sign-offs).
- Explain how exceptions are handled.
- Identify key reports and their sources.

**Preparation steps:**
1. Review process narrative and flowchart for accuracy.
2. Select 1-2 representative transactions to walk through.
3. Ensure all supporting documents are accessible.
4. Brief the process owner: answer questions factually; say "I'll follow up" if unsure.
5. Have the control matrix available to reference control points.

### 5. Common Audit Requests by Area

| Area | Typical Requests |
|------|-----------------|
| **Revenue** | Top customer contracts, revenue recognition policy memo, deferred revenue rollforward, credit memo listing, sales returns analysis |
| **Expenses** | Vendor listing, top 25 vendor spend, expense accrual support, consulting/legal fee detail, travel & entertainment sample |
| **Payroll** | Headcount reconciliation, payroll register, benefits enrollment, commission calculations, severance agreements |
| **Inventory** | Physical count procedures and results, inventory valuation, reserve analysis, slow-moving/obsolete items, standard cost updates |
| **Fixed Assets** | Additions/disposals listing with support, depreciation schedule, impairment analysis, lease agreements (ASC 842), capital vs expense policy |
| **Cash** | Bank reconciliations, outstanding check listing, wire transfer log, cash forecast vs actual, debt covenant calculations |
| **Equity** | Cap table, option/RSU activity, board minutes authorizing repurchases, EPS calculation workpaper |
| **Tax** | Effective tax rate reconciliation, uncertain tax positions, transfer pricing documentation, R&D credit support |

### 6. Response Timeline Management

| Urgency | Response SLA | Examples |
|---------|-------------|---------|
| Standard PBC item | By scheduled due date | Recurring items, schedules |
| Auditor follow-up question | Within 2 business days | Clarifications on submitted items |
| Urgent / blocking item | Within 1 business day | Items blocking audit procedures |
| Confirmation requests (external) | Send within 5 business days | Bank, legal, customer, vendor confirmations |

**Escalation:** If any item will miss its deadline, notify the audit liaison immediately with a revised delivery date.

### 7. Finding Remediation Tracking

| Finding # | Area | Description | Severity | Management Response | Owner | Remediation Date | Status |
|-----------|------|-------------|----------|--------------------|----|------------------|--------|
| 2025-01 | Revenue | Incomplete documentation of revenue recognition for 3 contracts | Significant Deficiency | Will implement contract checklist | Revenue Mgr | Q1 2026 | In Progress |

**For each finding:**
1. **Acknowledge or dispute** the finding with evidence.
2. **Document root cause** (not just the symptom).
3. **Design remediation** that addresses root cause.
4. **Assign owner and date** (realistic, not aspirational).
5. **Test remediation** before claiming completion.
6. **Report status** to Audit Committee quarterly.

### 8. Management Representation Letter Considerations

The management rep letter is a standard audit requirement. Key items to verify before signing:
- All known litigation disclosed to auditors
- All related party transactions identified
- No unrecorded liabilities
- No fraud or suspected fraud involving management
- All minutes of board/committee meetings provided
- Subsequent events through signing date evaluated
- Going concern assessment completed (if applicable)

**The Controller or CFO should review the rep letter carefully. It carries legal weight.**
""",
)


# =============================================================================
# Legal / Compliance Skills
# =============================================================================

contract_review_framework = Skill(
    name="contract_review_framework",
    description="Systematic contract review methodology with checklists, red flags, negotiation playbook, and turnaround standards.",
    category="compliance",
    agent_ids=[AgentID.LEGAL],
    knowledge_summary=(
        "Complete contract review framework with a clause-by-clause checklist, red flag indicators, "
        "negotiation playbook (must-have vs nice-to-have terms), and turnaround time standards by contract type."
    ),
    knowledge="""
## Contract Review Framework

### 1. Review Checklist (Clause-by-Clause)

#### Essential Provisions
| Clause | What to Verify | Risk if Missing/Weak |
|--------|---------------|---------------------|
| **Parties** | Legal names correct, authority to sign, correct entity | Unenforceability |
| **Effective Date / Term** | Start date, initial term, renewal mechanism | Ambiguity on obligations |
| **Scope of Work / Services** | Clear deliverables, acceptance criteria, milestones | Scope creep, disputes |
| **Pricing / Payment Terms** | Amount, currency, payment schedule, late fees, price escalation | Cash flow risk |
| **IP Ownership** | Who owns work product, background IP carve-outs, license grants | Loss of IP rights |
| **Confidentiality** | Scope, duration, carve-outs, return/destruction obligations | Trade secret exposure |
| **Indemnification** | Mutual or one-way, scope (IP, negligence, breach), caps, procedures | Unlimited exposure |
| **Limitation of Liability** | Cap (typically 12 months fees), exclusions (consequential, punitive), carve-outs | Unlimited financial risk |
| **Termination** | For cause (cure period), for convenience (notice period), effect on accrued rights | Lock-in risk |
| **Governing Law** | Jurisdiction, venue, arbitration vs litigation | Unfavorable forum |
| **Dispute Resolution** | Negotiation -> Mediation -> Arbitration/Litigation, seat, rules | Costly litigation |
| **Force Majeure** | Defined events, notice requirements, termination right if prolonged | Performance risk |
| **Assignment** | Consent required? Change of control trigger? | Unwanted counterparty |
| **Insurance** | Types (CGL, E&O, cyber), minimum amounts, additional insured | Uninsured claims |
| **Representations & Warranties** | Authority, no conflicts, compliance with laws, no litigation | Hidden risks |
| **Non-Solicitation** | Duration, scope (employees, customers, both) | Talent/business loss |

### 2. Red Flag Indicators

**STOP and escalate if any of these appear:**

| Red Flag | Why It Matters | Recommended Position |
|----------|---------------|---------------------|
| Unlimited liability | No cap on financial exposure | Cap at 12 months fees (24 months max) |
| Unilateral amendment rights | Counterparty can change terms at will | Require mutual written consent |
| Auto-renewal without notice | Trapped in unfavorable contract | 60-90 day notice window; annual term |
| Broad IP assignment | Lose rights to background IP | License only; retain background IP |
| Unreasonable non-compete | Restricts future business | Limit scope, geography, duration |
| No limitation on indemnity | Indemnification bypasses liability cap | Include in overall liability cap |
| Audit rights without limits | Disruption, cost, fishing expeditions | Annual audit, 30-day notice, business hours, NDA |
| Most-favored-nation clause | Must match best pricing to all | Reject or limit to same volume/scope |
| Exclusive dealing | Cannot use competitors | Reject for most vendor agreements |
| Broad termination for convenience | Can be dropped without cause or notice | Require 90-day notice + wind-down |

### 3. Negotiation Playbook

#### Must-Have Terms (Walk Away Without)
- Limitation of liability (capped)
- Mutual indemnification for own negligence/breach
- Termination for cause with cure period
- IP ownership/license clarity
- Governing law in our jurisdiction (or neutral)
- Confidentiality with reasonable duration (2-3 years post-termination)
- Assignment requires consent

#### Nice-to-Have Terms (Negotiate but Accept Compromise)
- Termination for convenience (our side)
- Price escalation cap (e.g., CPI + 2%)
- Broader force majeure definition
- Audit rights
- Service level credits
- Step-in rights

#### Acceptable Concessions
- Extend term from 1 year to 2 years (if pricing is favorable)
- Accept one-way indemnification on IP if we are the customer
- Accept vendor's governing law if jurisdiction is reasonable
- Agree to auto-renewal with adequate notice window (90 days)

### 4. Turnaround Time Standards

| Contract Type | Complexity | Target Turnaround |
|--------------|-----------|-------------------|
| Standard NDA (mutual) | Low | 1 business day |
| Standard NDA (non-standard) | Medium | 2-3 business days |
| SaaS subscription (click-through) | Low | 2 business days |
| Vendor services agreement | Medium | 5 business days |
| Customer enterprise contract | High | 7-10 business days |
| Partnership / JV agreement | High | 10-15 business days |
| M&A / Investment documents | Critical | Dedicated counsel, timeline varies |

**Expedited review:** Available for time-sensitive deals. Requires business sponsor to identify urgency. Target: 50% of standard turnaround.

### 5. Review Process Workflow

1. **Intake:** Requestor submits via legal intake form (parties, type, value, urgency).
2. **Triage:** Legal ops assigns based on type and complexity.
3. **First review:** Reviewer completes checklist, flags issues, redlines.
4. **Internal alignment:** Discuss red flags with business sponsor.
5. **Counterparty negotiation:** Send marked-up version with positions memo.
6. **Final review:** Verify all agreed changes are reflected.
7. **Approval:** Route per delegation of authority.
8. **Execution:** E-signature routing (see e_signature_routing skill).
9. **Filing:** Store executed copy in contract management system.

### 6. Post-Execution Obligations Tracking

After signing, extract and calendar:
- Payment milestones and deadlines
- Deliverable due dates
- Renewal / termination notice windows
- Insurance certificate renewal dates
- Compliance reporting obligations
- Audit rights exercise windows
""",
)


nda_triage = Skill(
    name="nda_triage",
    description="Rapid NDA classification system with GREEN/YELLOW/RED triage, standard template comparison, and turnaround SLAs.",
    category="compliance",
    agent_ids=[AgentID.LEGAL],
    knowledge_summary=(
        "NDA triage system: GREEN (standard mutual, auto-approve), YELLOW (non-standard terms, counsel review), "
        "RED (unlimited duration, no carve-outs, senior counsel). Includes template comparison checklist and SLAs."
    ),
    knowledge="""
## NDA Triage Classification System

### 1. Triage Decision Matrix

#### GREEN -- Auto-Approve with Standard Template
**Criteria (ALL must be met):**
- [x] Mutual NDA (both parties bound equally)
- [x] Term: 1-2 years, with 2-3 year survival of confidentiality obligations
- [x] Standard carve-outs present (publicly available info, independently developed, rightfully received from third party, legally required disclosure)
- [x] Purpose clearly defined and limited
- [x] Return/destruction obligation at termination
- [x] No non-compete or non-solicitation provisions
- [x] Governing law is our jurisdiction or a neutral US state (DE, NY)
- [x] No residuals clause
- [x] Our standard template or substantially equivalent

**Action:** Auto-approve. Execute within 1 business day.
**Who:** Legal coordinator or business sponsor (with template training).

#### YELLOW -- Counsel Review Required
**Triggers (ANY one triggers YELLOW):**
- [ ] One-way NDA (only one party bound)
- [ ] Non-standard definition of "Confidential Information" (too broad or too narrow)
- [ ] Term > 3 years
- [ ] Unusual scope (includes employees' personal information, trade secrets beyond deal scope)
- [ ] Non-standard governing law (foreign jurisdiction)
- [ ] Missing standard carve-outs
- [ ] Includes liquidated damages for breach
- [ ] Includes mandatory arbitration in counterparty's city
- [ ] Modifications to our standard template

**Action:** Route to legal counsel with specific flags highlighted.
**Target turnaround:** 2-3 business days.
**Who:** Associate or mid-level counsel.

#### RED -- Senior Counsel Review
**Triggers (ANY one triggers RED):**
- [ ] Unlimited or perpetual duration of confidentiality obligations
- [ ] No carve-outs for publicly available information
- [ ] Overly broad definition capturing all information ever exchanged
- [ ] Residuals clause (allows mental retention and use of confidential info)
- [ ] Non-compete buried in NDA (restricts business activities)
- [ ] Requires disclosure of source code or core IP before deal closes
- [ ] Non-standard remedy provisions (injunctive relief without bond, specific performance)
- [ ] Counterparty is a known litigious entity or competitor
- [ ] Government or regulatory counterparty (FOIA risk, sovereign immunity)

**Action:** Escalate to senior counsel or General Counsel.
**Target turnaround:** 3-5 business days.
**Who:** Senior counsel or General Counsel.

### 2. Standard NDA Template Comparison Checklist

When reviewing a counterparty NDA against our standard template:

| Provision | Our Standard | Their Version | Acceptable? | Notes |
|-----------|-------------|---------------|-------------|-------|
| Parties | Mutual | [ ] Mutual / [ ] One-way | | |
| Definition of Confidential Info | Marked or described in writing within 30 days | | | |
| Standard Carve-outs | All 4 present | | | |
| Term | 2 years | | | |
| Survival | 2 years post-termination | | | |
| Purpose | Evaluating potential business relationship | | | |
| Non-compete | Not included | | | |
| Non-solicitation | Not included | | | |
| Residuals | Not included | | | |
| Return/Destroy | Within 30 days of request or termination | | | |
| Governing Law | [Our state] | | | |
| Dispute Resolution | State/federal courts in [our city] | | | |
| Assignment | Not without consent | | | |
| Remedies | Equitable relief available | | | |

### 3. Common Modification Requests (and Responses)

| Their Ask | Risk Level | Our Response |
|-----------|-----------|-------------|
| One-way (only we are bound) | YELLOW | Counter with mutual; if rejected, ensure scope is narrow |
| Perpetual confidentiality | RED | Counter with 3-year survival max |
| Remove "publicly available" carve-out | RED | Reject -- this is fundamental |
| Add non-solicitation of employees | YELLOW | Accept if mutual and limited to 12 months |
| Add residuals clause | RED | Reject -- defeats purpose of NDA |
| Expand definition to "all information" | YELLOW | Narrow to "information marked confidential or reasonably understood to be" |
| Their governing law (foreign) | YELLOW | Counter with our jurisdiction; compromise on neutral (DE/NY) |
| Add liquidated damages ($X per breach) | YELLOW | Reject; agree to "equitable relief" language instead |

### 4. Turnaround SLAs

| Triage Level | First Response | Final Execution |
|-------------|---------------|-----------------|
| GREEN | Same business day | 1 business day |
| YELLOW | 1 business day | 2-3 business days |
| RED | 1 business day (acknowledgment) | 3-5 business days |

### 5. NDA Tracking

Maintain an NDA register:
| # | Counterparty | Type | Triage | Effective Date | Expiry | Purpose | Status |
|---|-------------|------|--------|---------------|--------|---------|--------|

**Review quarterly:** Identify expiring NDAs that may need renewal if the relationship continues.
""",
)


legal_risk_assessment = Skill(
    name="legal_risk_assessment",
    description="Legal risk classification with severity-likelihood matrix, mitigation strategies, and board reporting thresholds.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.EXEC, AgentID.STRAT],
    knowledge_summary=(
        "5x5 severity-by-likelihood legal risk matrix with risk categories (regulatory, contractual, IP, "
        "employment, litigation, data privacy, antitrust), escalation criteria, mitigation strategy types, "
        "and insurance coverage mapping."
    ),
    knowledge="""
## Legal Risk Assessment Framework

### 1. 5x5 Severity-by-Likelihood Matrix

**Likelihood Scale:**
| Score | Label | Description |
|-------|-------|-------------|
| 1 | Rare | < 5% probability; unprecedented |
| 2 | Unlikely | 5-20% probability; has happened elsewhere |
| 3 | Possible | 20-50% probability; has happened to us before |
| 4 | Likely | 50-80% probability; expected to occur |
| 5 | Almost Certain | > 80% probability; imminent or recurring |

**Severity Scale:**
| Score | Label | Financial Impact | Operational Impact | Reputational Impact |
|-------|-------|-----------------|-------------------|-------------------|
| 1 | Negligible | < $10K | No disruption | No external attention |
| 2 | Minor | $10K - $100K | Minor delay | Local/trade media |
| 3 | Moderate | $100K - $1M | Partial disruption | Industry media |
| 4 | Major | $1M - $10M | Significant disruption | National media |
| 5 | Critical | > $10M | Business continuity threat | Major public backlash |

**Risk Score = Severity x Likelihood**

| | Likelihood 1 | Likelihood 2 | Likelihood 3 | Likelihood 4 | Likelihood 5 |
|---|---|---|---|---|---|
| **Severity 5** | 5 (Medium) | 10 (High) | 15 (Critical) | 20 (Critical) | 25 (Critical) |
| **Severity 4** | 4 (Low) | 8 (Medium) | 12 (High) | 16 (Critical) | 20 (Critical) |
| **Severity 3** | 3 (Low) | 6 (Medium) | 9 (Medium) | 12 (High) | 15 (Critical) |
| **Severity 2** | 2 (Low) | 4 (Low) | 6 (Medium) | 8 (Medium) | 10 (High) |
| **Severity 1** | 1 (Low) | 2 (Low) | 3 (Low) | 4 (Low) | 5 (Medium) |

**Action by risk level:**
- **Low (1-4):** Monitor; include in quarterly review.
- **Medium (5-9):** Active mitigation plan; review monthly.
- **High (10-15):** Escalate to General Counsel; report to executive team.
- **Critical (16-25):** Immediate board notification; dedicated response team.

### 2. Risk Categories

| Category | Sub-Categories | Example Risks |
|----------|---------------|--------------|
| **Regulatory** | Federal, state, local, international | Non-compliance with new data privacy law; FTC enforcement action |
| **Contractual** | Customer, vendor, partner, employment | Breach of SLA; failure to deliver on contract terms |
| **Intellectual Property** | Patents, trademarks, copyrights, trade secrets | Patent infringement claim; employee takes trade secrets to competitor |
| **Employment** | Discrimination, wrongful termination, wage/hour, safety | Class action wage claim; harassment allegation |
| **Litigation** | Active, threatened, potential | Customer lawsuit; securities class action |
| **Data Privacy** | GDPR, CCPA, HIPAA, breach notification | Data breach affecting >10K records; cross-border transfer violation |
| **Antitrust** | Price fixing, market allocation, tying | Price coordination allegation; monopoly investigation |

### 3. Escalation Criteria

**Material risk (requires executive notification):**
- Severity >= 4 AND Likelihood >= 3 (risk score >= 12)
- Any government investigation or subpoena
- Any litigation with potential exposure > $1M
- Any data breach affecting > 1,000 individuals
- Any allegation of fraud, bribery, or corruption
- Any whistleblower complaint

**Board reporting threshold:**
- Risk score >= 16 (Critical)
- Any matter requiring public disclosure
- Any matter potentially affecting financial statements
- Any matter with regulatory sanction risk > $5M
- Any matter involving senior leadership

### 4. Risk Register Template

| ID | Category | Description | Severity | Likelihood | Score | Level | Owner | Mitigation Strategy | Status | Last Review |
|----|----------|-------------|----------|------------|-------|-------|-------|-------------------|--------|------------|
| LR-001 | Data Privacy | GDPR compliance gap in marketing tools | 4 | 3 | 12 | High | DPO | Implement consent management platform | In Progress | 2025-03 |

### 5. Mitigation Strategy Types

| Strategy | When to Use | Examples |
|----------|------------|---------|
| **Avoid** | Risk is unacceptable and activity is discretionary | Exit market, discontinue product, decline deal |
| **Transfer / Insure** | Risk can be shifted to third party | Purchase D&O insurance, contractual indemnification, outsource to specialist |
| **Mitigate / Control** | Reduce severity or likelihood through action | Implement compliance program, add controls, training, monitoring |
| **Accept / Monitor** | Risk is within appetite and cost of mitigation exceeds benefit | Document acceptance, set monitoring triggers, review quarterly |

### 6. Cost-Benefit Analysis for Mitigation

```
Mitigation Justified When:
  Expected Loss (without mitigation) > Cost of Mitigation

Expected Loss = Severity ($) x Likelihood (%)
Net Benefit = Expected Loss Avoided - Mitigation Cost

Example:
  Risk: Data breach (Severity: $2M, Likelihood: 30%)
  Expected Loss: $2M x 30% = $600K
  Mitigation: Implement encryption + monitoring ($150K)
  Net Benefit: $600K - $150K = $450K --> PROCEED
```

### 7. Insurance Coverage Mapping

| Risk Category | Insurance Type | Typical Coverage | Key Exclusions |
|--------------|---------------|-----------------|----------------|
| General liability | CGL | Bodily injury, property damage | Intentional acts, professional services |
| Professional errors | E&O / Professional Liability | Negligent acts, errors, omissions | Known claims, intentional misconduct |
| Cyber/data breach | Cyber Liability | Breach response, regulatory fines, business interruption | Unencrypted devices (some policies), war/terrorism |
| Employment claims | EPLI | Discrimination, harassment, wrongful termination | Intentional acts, WARN Act violations |
| Directors & Officers | D&O | Shareholder suits, regulatory investigations | Fraud, personal profit |
| IP infringement | IP Liability | Defense costs, damages | Willful infringement (sometimes) |

**Review insurance annually:** Ensure coverage limits match current risk profile. Update after material acquisitions, new markets, or regulatory changes.
""",
)


compliance_check_framework = Skill(
    name="compliance_check_framework",
    description="Run compliance checks on business actions with pre-launch checklists, regulatory mapping, and approval workflows.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.OPS],
    knowledge_summary=(
        "Compliance check framework for business actions: pre-launch checklists (data privacy, advertising, "
        "accessibility), feature-level assessment questions, regulatory mapping by jurisdiction, "
        "documentation requirements, and self-certify vs counsel review approval workflows."
    ),
    knowledge="""
## Compliance Check Framework

### 1. Pre-Launch Compliance Checklist

Before launching any product, feature, campaign, or business initiative, complete the following:

#### Data Privacy
- [ ] What personal data is collected? (names, emails, IP addresses, device IDs, location, biometrics)
- [ ] Legal basis for processing identified? (consent, legitimate interest, contract, legal obligation)
- [ ] Privacy notice updated to cover new data collection?
- [ ] Data Processing Agreement (DPA) in place with all processors?
- [ ] Data retention period defined and documented?
- [ ] Right to deletion / data portability supported?
- [ ] Cross-border data transfer mechanism in place? (SCCs, adequacy decision, binding corporate rules)
- [ ] Data Protection Impact Assessment (DPIA) required? (high-risk processing, profiling, large-scale)
- [ ] Cookie consent mechanism implemented? (banner, preference center)

#### Consumer Protection
- [ ] Pricing is transparent and not misleading?
- [ ] Subscription terms clearly disclosed (auto-renewal, cancellation process)?
- [ ] Refund/return policy prominently displayed?
- [ ] No dark patterns in UI (hidden costs, forced consent, trick questions)?
- [ ] Terms of service and privacy policy accessible before purchase?

#### Advertising Standards
- [ ] Claims are truthful and substantiated?
- [ ] Testimonials/endorsements properly disclosed (FTC guidelines)?
- [ ] Comparative advertising is factual and not misleading?
- [ ] Influencer relationships properly disclosed (#ad, #sponsored)?
- [ ] Email marketing compliant (CAN-SPAM: unsubscribe link, physical address, no deceptive subject lines)?

#### Accessibility
- [ ] WCAG 2.1 AA compliance verified?
- [ ] Screen reader compatible?
- [ ] Keyboard navigation functional?
- [ ] Color contrast ratios meet minimum (4.5:1 for normal text)?
- [ ] Alt text on all images?
- [ ] Closed captions on video content?

#### Export Controls & Sanctions
- [ ] Product/service not restricted under EAR/ITAR?
- [ ] Customer/counterparty screened against OFAC SDN list?
- [ ] Geo-blocking implemented for embargoed countries?
- [ ] Encryption classification reviewed (if applicable)?

### 2. Feature-Level Assessment Questions

For each new feature or change, answer these screening questions:

| Question | If YES | Action |
|----------|--------|--------|
| Does this collect PII? | Yes | Privacy review required |
| Does this process payments? | Yes | PCI-DSS review required |
| Does this target users under 16? | Yes | COPPA / Age-gating review |
| Does this make health claims? | Yes | FDA / FTC substantiation review |
| Does this use AI/ML for decisions? | Yes | Bias audit, explainability review |
| Does this process biometric data? | Yes | State biometric law review (IL BIPA, TX, WA) |
| Does this involve user-generated content? | Yes | DMCA / content moderation review |
| Does this send commercial emails/SMS? | Yes | CAN-SPAM / TCPA review |
| Does this operate in the EU? | Yes | GDPR review |
| Does this operate in California? | Yes | CCPA/CPRA review |
| Does this involve financial data? | Yes | GLBA / SOX review |
| Does this involve health data? | Yes | HIPAA review |

### 3. Regulatory Mapping by Jurisdiction

| Jurisdiction | Key Regulations | Trigger |
|-------------|----------------|---------|
| **United States (Federal)** | FTC Act, CAN-SPAM, COPPA, FCRA, GLBA, HIPAA, ADA | Customers or operations in US |
| **California** | CCPA/CPRA, CalOPPA, Prop 65 | CA residents' data or CA sales |
| **Illinois** | BIPA (biometric data) | Collecting biometrics of IL residents |
| **European Union** | GDPR, ePrivacy Directive, Digital Services Act, AI Act | EU residents' data or EU operations |
| **United Kingdom** | UK GDPR, Data Protection Act 2018 | UK residents' data |
| **Canada** | PIPEDA, CASL (anti-spam), AIDA (proposed AI) | Canadian residents |
| **Brazil** | LGPD | Brazilian residents' data |
| **Australia** | Privacy Act 1988, Spam Act 2003 | Australian residents |

### 4. Documentation Requirements

For every compliance check:
1. **Assessment date** and assessor name
2. **Feature/product description** (what it does, who it serves)
3. **Data flow diagram** (what data, from where, stored where, shared with whom)
4. **Checklist completion** (all items checked with Y/N/NA)
5. **Risk items identified** and mitigation actions
6. **Approval decision** (approved / approved with conditions / rejected)
7. **Conditions for ongoing compliance** (monitoring, re-assessment triggers)

### 5. Approval Workflow

| Risk Level | Self-Certify? | Required Approver | Timeline |
|-----------|--------------|-------------------|----------|
| **Low** (no PII, no payments, domestic only) | Yes, with checklist | Business owner | 1 business day |
| **Medium** (PII collected, standard processing) | No | Legal counsel | 3 business days |
| **High** (sensitive data, new jurisdiction, AI decisions) | No | Senior counsel + DPO | 5-7 business days |
| **Critical** (health data, children, biometrics, financial) | No | General Counsel + external opinion | 10+ business days |

### 6. Ongoing Monitoring Obligations

Post-launch, maintain compliance through:
- **Quarterly:** Review data processing activities against privacy notices
- **Semi-annually:** Re-screen vendor compliance (SOC 2, DPA, insurance)
- **Annually:** Full compliance re-assessment for each product/feature
- **Triggered:** Re-assess when regulations change, new jurisdictions entered, or material feature changes
- **Continuous:** Monitor regulatory enforcement actions in your industry for emerging risks
""",
)


vendor_agreement_check = Skill(
    name="vendor_agreement_check",
    description="Check vendor agreement status with inventory tracking, key dates, compliance verification, and risk tiering.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.OPS],
    knowledge_summary=(
        "Vendor agreement management: agreement inventory checklist (MSA, SOW, DPA, NDA, SLA), "
        "key date tracking, compliance verification (insurance, SOC 2), risk tier classification, "
        "renegotiation triggers, and termination planning."
    ),
    knowledge="""
## Vendor Agreement Status Check Framework

### 1. Agreement Inventory Checklist

For each vendor, verify the following agreements are in place and current:

| Agreement | Purpose | Required For |
|-----------|---------|-------------|
| **MSA (Master Service Agreement)** | Governs overall relationship, liability, IP, termination | All vendors |
| **SOW (Statement of Work)** | Defines specific deliverables, timeline, pricing | Project-based vendors |
| **DPA (Data Processing Agreement)** | GDPR/CCPA compliance for data processors | Any vendor handling PII |
| **BAA (Business Associate Agreement)** | HIPAA compliance | Vendors with PHI access |
| **NDA (Non-Disclosure Agreement)** | Protects confidential information | Vendors with access to proprietary info |
| **SLA (Service Level Agreement)** | Defines uptime, response times, remedies | SaaS, hosting, critical service vendors |
| **Insurance Certificate** | Proof of coverage (CGL, E&O, cyber) | All vendors above Tier 3 |
| **SOC 2 Report** | Security and availability controls | SaaS, cloud, data processing vendors |

### 2. Key Date Tracking

| Date Type | Lead Time | Action |
|-----------|-----------|--------|
| **Contract expiration** | 120 days before | Begin renewal evaluation |
| **Renewal notice deadline** | Per contract (typically 60-90 days) | Send renewal or non-renewal notice |
| **Price escalation date** | 30 days before | Review escalation terms; negotiate if above CPI |
| **Insurance certificate renewal** | 30 days before expiry | Request updated certificate |
| **SOC 2 report period end** | Annually | Request new report when available |
| **DPA review** | Annually or on regulation change | Verify DPA covers current processing activities |
| **Background check refresh** | Per policy (typically 3-5 years) | Re-run for vendors with facility/system access |

**Calendar automation:** Set recurring reminders at each lead time threshold. Assign ownership to procurement or legal ops.

### 3. Compliance Verification

#### Quarterly Verification Checklist
- [ ] Insurance certificates current and meet minimum requirements
- [ ] No material adverse changes disclosed by vendor
- [ ] SLA performance meets thresholds (review vendor reports)
- [ ] Vendor has not appeared on sanctions lists (OFAC, EU sanctions)
- [ ] No security incidents reported by vendor
- [ ] Subprocessor list unchanged (or changes approved per DPA)

#### Annual Verification Checklist
- [ ] SOC 2 Type II report received and reviewed (or equivalent)
- [ ] Business continuity / disaster recovery plan confirmed
- [ ] Vendor financial health assessed (credit report, public filings)
- [ ] Background checks refreshed (if applicable)
- [ ] Compliance certifications current (ISO 27001, PCI-DSS, HIPAA)
- [ ] DPA still covers all processing activities
- [ ] Performance against contract terms evaluated (SLA scorecard)

### 4. Risk Tier Classification

| Tier | Criteria | Due Diligence Level | Review Frequency |
|------|---------|-------------------|-----------------|
| **Tier 1: Critical** | Sole-source, core operations, handles sensitive data, >$500K annual spend, failure causes business disruption | Full due diligence, SOC 2, BCP review, quarterly business reviews | Quarterly |
| **Tier 2: Important** | Alternatives exist but switching costly, handles some PII, $100K-$500K spend | Standard due diligence, SOC 2 or equivalent, annual business review | Semi-annually |
| **Tier 3: Commodity** | Easily replaceable, no sensitive data access, <$100K spend | Basic due diligence, insurance verification | Annually |

### 5. Renegotiation Triggers

Initiate contract renegotiation when:
- [ ] Contract expires within 120 days (standard renewal)
- [ ] Price increase exceeds CPI by >2%
- [ ] Vendor SLA breach rate > 5% over trailing 6 months
- [ ] Material change in scope (>20% increase/decrease in usage)
- [ ] Vendor acquired by competitor or private equity
- [ ] New regulatory requirement not covered by current terms
- [ ] Vendor security incident affecting our data
- [ ] Market rate analysis shows >15% overpayment
- [ ] Internal restructuring changes business needs
- [ ] Technology obsolescence (better alternatives available)

### 6. Termination Planning Checklist

When preparing to terminate a vendor relationship:

**30-60 Days Before Notice:**
- [ ] Review termination clause (notice period, cure period, penalties)
- [ ] Identify replacement vendor(s) and confirm readiness
- [ ] Assess data migration requirements and timeline
- [ ] Calculate early termination fees (if applicable)
- [ ] Document cause (if terminating for cause -- SLA breaches, security incidents)

**At Notice:**
- [ ] Send formal termination notice per contract requirements (certified mail / email per terms)
- [ ] Request data return or certification of destruction per DPA
- [ ] Revoke vendor system access credentials
- [ ] Notify internal stakeholders of transition timeline

**Post-Termination:**
- [ ] Confirm data return received (or destruction certificate)
- [ ] Verify no ongoing data processing by terminated vendor
- [ ] Remove vendor from authorized vendor list
- [ ] Complete final payment reconciliation
- [ ] Archive all contract documents per retention policy
- [ ] Conduct lessons learned for vendor management improvement
""",
)


e_signature_routing = Skill(
    name="e_signature_routing",
    description="E-signature preparation and routing with pre-signature checklists, signing order, and international execution considerations.",
    category="compliance",
    agent_ids=[AgentID.LEGAL],
    knowledge_summary=(
        "E-signature preparation guide covering pre-signature checklists, signing order configuration, "
        "signer identification, witness/notarization requirements, document retention, "
        "execution page formatting, and international execution considerations."
    ),
    knowledge="""
## E-Signature Routing Guide

### 1. Pre-Signature Checklist

Before routing any document for signature:

- [ ] **Final version confirmed:** All redlines resolved, tracked changes accepted, comments removed
- [ ] **Version control:** Document marked as "Final" with date and version number
- [ ] **Internal approvals obtained:** Per delegation of authority matrix
  - [ ] Business sponsor approval
  - [ ] Legal review completed
  - [ ] Finance review (if financial commitment)
  - [ ] Compliance review (if applicable)
- [ ] **Authority verified:** Confirm each signer has authority to bind their organization
  - Check corporate resolution, power of attorney, or delegation of authority
  - For counterparties: verify through public filings, LinkedIn, or direct confirmation
- [ ] **All exhibits/schedules attached:** SOWs, pricing appendices, data processing addenda
- [ ] **Execution page present:** Signature blocks with correct names, titles, entity names
- [ ] **Effective date:** Confirmed (date of last signature, specific date, or to be filled)

### 2. Signing Order Configuration

| Pattern | When to Use | Setup |
|---------|------------|-------|
| **Sequential (default)** | Standard contracts, one party signs first | Party A signs -> Party B signs -> completed |
| **Parallel** | Multiple internal approvers at same level | All approvers sign simultaneously -> then counterparty |
| **Counter-sign** | We sign first to show commitment | Our authorized signer -> counterparty |
| **Multi-party sequential** | Complex deals with multiple parties | Party A -> Party B -> Party C -> completed |

**Recommended default:** We sign last (gives us control and ensures counterparty commitment first).

**Exception:** Send our signed copy first when we are the party seeking the deal and want to demonstrate commitment.

### 3. Signer Identification Requirements

For each signer, collect and verify:

| Field | Required | Notes |
|-------|----------|-------|
| Full legal name | Yes | As it appears on government ID |
| Title | Yes | Must reflect signing authority |
| Company (legal entity name) | Yes | Exact legal entity, not DBA |
| Email address | Yes | Corporate email preferred for authentication |
| Phone number | Recommended | For SMS authentication (add if supported) |
| Signing capacity | If applicable | "as authorized representative of," "in their personal capacity" |

### 4. Authentication Methods

| Method | Security Level | When to Use |
|--------|---------------|------------|
| Email link only | Basic | Low-value, low-risk agreements |
| Email + access code | Medium | Standard commercial agreements |
| Email + SMS verification | High | Agreements > $100K or sensitive |
| Knowledge-based authentication (KBA) | High | Real estate, financial services |
| Government ID verification | Highest | Regulated transactions, high-value |

### 5. Witness and Notarization Requirements

| Document Type | Witness Required? | Notarization Required? |
|--------------|------------------|----------------------|
| Standard commercial contract | No (in most US jurisdictions) | No |
| Real property deed/lease | Sometimes (varies by state) | Yes (most states) |
| Power of attorney | Yes (many jurisdictions) | Yes (recommended) |
| Corporate resolution | No (but secretary certification) | No |
| Will / Estate documents | Yes (2 witnesses typical) | Yes |
| Sworn affidavit | No | Yes (or before commissioner) |
| Loan documents | Varies | Often yes |

### 6. Document Retention Policy

| Document Type | Retention Period | Format |
|--------------|-----------------|--------|
| Executed contracts (active) | Life of contract + 7 years | Original electronic + PDF |
| Executed contracts (expired) | 7 years post-expiration | PDF in archive |
| NDAs | Life + 3 years | PDF |
| Employment agreements | Termination + 7 years | PDF |
| Real property documents | Life + 10 years | Original + PDF |
| Government filings | Permanent | PDF + original if paper |
| Audit trail / signature certificates | Same as underlying document | Platform export + PDF |

**Always retain the signature certificate / audit trail** from the e-signature platform -- it proves who signed, when, from what IP address, and with what authentication.

### 7. Execution Page Formatting

```
IN WITNESS WHEREOF, the parties have executed this Agreement
as of the date last signed below.

[COMPANY A LEGAL NAME]            [COMPANY B LEGAL NAME]

By: ________________________      By: ________________________
Name: [Full Name]                 Name: [Full Name]
Title: [Title]                    Title: [Title]
Date: ________________________    Date: ________________________
```

**For e-signatures:** Configure signature fields to auto-populate name, title, and date upon signing. Use "anchor text" tags if the e-signature platform supports them.

### 8. International Execution Considerations

| Jurisdiction | E-Signature Valid? | Special Requirements |
|-------------|-------------------|---------------------|
| **United States** | Yes (ESIGN Act, UETA) | Exceptions: wills, certain UCC, court orders |
| **European Union** | Yes (eIDAS Regulation) | Simple e-sig valid; Qualified e-sig = handwritten equivalent |
| **United Kingdom** | Yes (Electronic Communications Act 2000) | Deeds require witnesses (can be virtual in some cases) |
| **Canada** | Yes (PIPEDA, provincial statutes) | Varies by province; some land transactions excluded |
| **China** | Yes (E-Signature Law 2005) | Reliable e-sig has same legal effect; government certified CA preferred |
| **Japan** | Yes (Act on Electronic Signatures) | Company seal (hanko) still expected in practice for formal agreements |
| **India** | Yes (IT Act 2000) | Aadhaar e-sign available; certain documents require wet ink |
| **Brazil** | Yes (MP 2200-2/2001) | ICP-Brasil certified signature = highest validity |

**Wet-ink jurisdictions / exceptions:** Some document types in some jurisdictions still require physical (wet-ink) signatures. When in doubt, check with local counsel. Common exceptions: notarized documents, government filings, certain real estate transfers.

**Practical tip:** When counterparty insists on wet ink, prepare a PDF for printing, signing, scanning, and returning. Maintain both the scanned copy and the courier-shipped original.
""",
)


legal_meeting_briefing = Skill(
    name="legal_meeting_briefing",
    description="Prepare structured legal meeting briefings with agenda, risk assessment, recommended positions, and action tracking.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.EXEC],
    knowledge_summary=(
        "Legal meeting briefing framework with templates for attendees, agenda, risk assessment, "
        "recommended and fallback positions, preparation checklists, post-meeting action tracking, "
        "and privilege considerations."
    ),
    knowledge="""
## Legal Meeting Briefing Framework

### 1. Briefing Template

```
LEGAL MEETING BRIEFING
========================================
PRIVILEGED AND CONFIDENTIAL
ATTORNEY-CLIENT PRIVILEGED

Meeting: [Title / Matter Name]
Date/Time: [Date] at [Time] [Timezone]
Location: [Room / Video Link]
Duration: [Estimated duration]
Prepared by: [Attorney name]
Date prepared: [Date]

========================================
ATTENDEES
========================================
Internal:
  - [Name], [Title] -- [Role in meeting]
  - [Name], [Title] -- [Role in meeting]

External:
  - [Name], [Title], [Organization] -- [Role]

========================================
AGENDA
========================================
1. [Topic] (XX minutes) -- [Discussion / Decision / Update]
2. [Topic] (XX minutes) -- [Discussion / Decision / Update]
3. [Topic] (XX minutes) -- [Discussion / Decision / Update]
4. Action items and next steps (10 minutes)

========================================
BACKGROUND / CONTEXT
========================================
[2-3 paragraph summary of the matter, its history, and why this
meeting is happening now. Reference prior meetings if applicable.]

Key dates:
  - [Date]: [Milestone/event]
  - [Date]: [Deadline/filing]

========================================
KEY ISSUES FOR DISCUSSION
========================================

ISSUE 1: [Title]
  Background: [Brief context]
  Risk Assessment: [Low / Medium / High / Critical]
  Options:
    A. [Option] -- Pros: [list] / Cons: [list]
    B. [Option] -- Pros: [list] / Cons: [list]
  Recommended Position: [Our recommendation and rationale]
  Fallback Position: [If recommendation is not accepted]

ISSUE 2: [Title]
  [Same structure]

========================================
RISK ASSESSMENT
========================================
Overall matter risk: [Low / Medium / High / Critical]
Financial exposure: [$X - $Y range]
Reputational risk: [Low / Medium / High]
Timeline pressure: [Urgent / Standard / No deadline]

========================================
RECOMMENDED POSITIONS
========================================
1. [Position on Issue 1 with rationale]
2. [Position on Issue 2 with rationale]

========================================
FALLBACK POSITIONS
========================================
1. [If primary position rejected, our minimum acceptable outcome]
2. [Concessions we are willing to make and their limits]

========================================
ACTION ITEMS FROM PRIOR MEETING
========================================
| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | [action] | [name] | [date] | [Complete/Open/Overdue] |

========================================
PREPARATION NOTES
========================================
[Any specific preparation instructions for attendees]

Do NOT disclose: [sensitive items to avoid discussing]
Key message: [What we want the counterparty to take away]
```

### 2. Preparation Checklist

**48 Hours Before Meeting:**
- [ ] Draft briefing document and circulate to internal attendees
- [ ] Review all prior correspondence and meeting notes on this matter
- [ ] Check agreement status (current version, open issues, redlines)
- [ ] Identify decision points that need resolution at this meeting
- [ ] Prepare supporting documents (draft agreements, term sheets, data)
- [ ] Confirm attendee availability and send calendar invite with agenda

**Day of Meeting:**
- [ ] Print briefing documents (if in-person) or share screen-ready versions
- [ ] Test video/audio setup (if virtual)
- [ ] Review action items from last meeting and prepare status updates
- [ ] Brief executives on key talking points (5-minute pre-meeting huddle)
- [ ] Have relevant agreements / documents open and accessible

### 3. Post-Meeting Action Tracking

Within 24 hours of the meeting:

1. **Circulate meeting summary** (internal only, privileged):
   - Key decisions made
   - Positions agreed upon
   - Action items with owners and deadlines
   - Next meeting date/topic

2. **Action item template:**

| # | Action Item | Owner | Deadline | Priority | Status |
|---|------------|-------|----------|----------|--------|
| 1 | Draft revised term sheet per agreed positions | [Attorney] | [Date] | High | Open |
| 2 | Obtain board approval for settlement range | [GC] | [Date] | Critical | Open |
| 3 | Send counterparty our updated redline | [Paralegal] | [Date] | Medium | Open |

3. **Follow-up cadence:** Review action items at next internal sync. Escalate overdue items within 48 hours.

### 4. Confidentiality & Privilege Reminders

- **Mark all briefings:** "PRIVILEGED AND CONFIDENTIAL - ATTORNEY-CLIENT PRIVILEGED"
- **Limit distribution:** Only to those with a need to know.
- **Do NOT forward to counterparties** or external parties without counsel approval.
- **During meeting:** Remind attendees that discussions are privileged.
- **Meeting notes:** Keep them factual and professional; assume they could be discoverable if privilege is waived.
- **External counsel:** If outside attorneys are present, note their role to preserve work product protection.

### 5. Meeting Types and Adapted Formats

| Meeting Type | Key Adaptations |
|-------------|----------------|
| **Negotiation session** | Emphasize positions/fallbacks, BATNA, concession strategy |
| **Board/Audit Committee** | Executive summary format, focus on risk and financial impact |
| **Regulatory meeting** | Prepare talking points carefully; assume everything could be quoted |
| **Litigation strategy** | Detailed risk/exposure analysis, settlement range, timeline to trial |
| **Internal compliance review** | Findings summary, remediation status, resource requests |
| **Vendor/partner review** | Performance data, contract status, renewal/termination recommendation |
""",
)


legal_inquiry_response = Skill(
    name="legal_inquiry_response",
    description="Respond to common legal inquiries with templates, escalation criteria, SLAs, and privilege markings.",
    category="compliance",
    agent_ids=[AgentID.LEGAL],
    knowledge_summary=(
        "Legal inquiry response framework with response templates by category (employment, contract, "
        "compliance, IP, litigation holds), escalation criteria for outside counsel, response time SLAs, "
        "disclaimer language, and documentation requirements."
    ),
    knowledge="""
## Legal Inquiry Response Framework

### 1. Response Templates by Category

#### Employment Questions
```
Subject: RE: [Employment Question - Brief Topic]
PRIVILEGED AND CONFIDENTIAL

Thank you for your inquiry regarding [topic].

[Substantive response based on company policy and applicable law]

Key considerations:
- [Point 1]
- [Point 2]

Recommended action:
- [Action step with timeline]

Please note this guidance is based on current policy and [state/federal] law.
If the situation changes, please consult legal before proceeding.
```

**Common employment topics and guidance frameworks:**
| Topic | Key References | Standard Guidance |
|-------|---------------|-------------------|
| Termination | Employment agreement, at-will doctrine, state law | Review agreement terms, document performance issues, consult HR |
| Non-compete enforceability | State law (varies widely), FTC rule | Analyze state-specific enforceability, narrow scope |
| Accommodation request | ADA, state disability laws | Engage in interactive process, document good faith efforts |
| Wage/hour classification | FLSA, state wage laws | Apply economic reality test, document analysis |
| Leave of absence | FMLA, state leave laws, company policy | Confirm eligibility, calculate entitlement, document |

#### Contract Interpretation
```
Subject: RE: Contract Question - [Agreement Name]
PRIVILEGED AND CONFIDENTIAL

Re: [Agreement] between [Party A] and [Party B] dated [Date]

You asked about [specific question].

Based on my review of Section [X] of the Agreement:
[Analysis of relevant provision]

Interpretation: [Clear statement of what the provision means]

Risk: [Any ambiguity or risk in this interpretation]

Recommendation: [Proposed course of action]

If you plan to take action based on this interpretation that could
affect the counterparty relationship, please loop in legal first.
```

#### Compliance Inquiries
```
Subject: RE: Compliance Question - [Topic]
PRIVILEGED AND CONFIDENTIAL

Thank you for flagging this compliance question.

Applicable regulation(s): [List]
Company policy: [Reference]

Analysis:
[Assessment of whether proposed action complies]

Compliance status: [Compliant / Non-compliant / Needs modification]

Required steps to ensure compliance:
1. [Step]
2. [Step]

Deadline for action: [If time-sensitive]
```

#### IP Questions
```
Subject: RE: IP Question - [Topic]
PRIVILEGED AND CONFIDENTIAL

Re: [Description of IP issue]

IP type: [Patent / Trademark / Copyright / Trade Secret]
Ownership status: [Company-owned / Licensed / Third-party / Unclear]

Analysis:
[Assessment of rights, risks, and obligations]

Recommendation:
[Action steps to protect/enforce/comply]

If this involves potential infringement (by us or of our rights),
please do not take external action until we discuss next steps.
```

#### Litigation Hold Notices
```
Subject: LITIGATION HOLD NOTICE - ACTION REQUIRED
PRIVILEGED AND CONFIDENTIAL

A legal hold is now in effect regarding [brief description of matter].

YOU MUST:
1. PRESERVE all documents, emails, files, messages (including texts,
   Slack, Teams) related to [subject matter].
2. DO NOT delete, modify, or destroy any potentially relevant materials.
3. SUSPEND any automatic deletion policies for relevant data.
4. Confirm receipt of this notice by [date].

Scope: Materials related to [description] from [date range].

This hold supersedes any document retention policies. Failure to
comply may result in legal sanctions.

If you have questions, contact [Attorney name] at [email].

Please confirm receipt by replying to this email.
```

### 2. Escalation Criteria (When to Involve Outside Counsel)

| Trigger | Action | Timeline |
|---------|--------|----------|
| Threatened or actual litigation | Engage litigation counsel | Immediate |
| Government investigation / subpoena | Engage regulatory counsel | Immediate |
| Potential exposure > $500K | Consult outside counsel | Within 24 hours |
| Novel legal issue (no internal expertise) | Research or engage specialist | Within 1 week |
| Cross-border issue (unfamiliar jurisdiction) | Engage local counsel | Within 1 week |
| Whistleblower complaint involving leadership | Engage independent counsel | Immediate |
| M&A / investment transaction | Engage deal counsel | At LOI stage |
| Patent infringement (accused or accusing) | Engage IP litigation counsel | Within 48 hours |

### 3. Response Time SLAs

| Priority | Response Time | Examples |
|----------|-------------|---------|
| **Urgent** | Same business day | Litigation hold, government inquiry, data breach, employee safety |
| **High** | 1 business day | Contract deadline within 1 week, regulatory filing due, active negotiation |
| **Standard** | 2 business days | General contract questions, policy interpretation, vendor review |
| **Informational** | 5 business days | Research requests, policy drafting, template updates, training materials |

**Acknowledgment:** All inquiries receive acknowledgment within 4 business hours, even if the substantive response takes longer. Include estimated response date.

### 4. Disclaimer Language

**Standard internal disclaimer:**
> "This response is intended as general legal guidance for internal purposes only and does not constitute legal advice to any individual. The analysis is based on the facts as presented. If facts change, please consult legal before relying on this guidance."

**Privilege marking (on all legal communications):**
> "PRIVILEGED AND CONFIDENTIAL - ATTORNEY-CLIENT COMMUNICATION. This communication is protected by the attorney-client privilege and/or work product doctrine. Do not forward to external parties without legal approval."

### 5. Documentation Requirements

For every legal inquiry:
1. **Log the inquiry** in legal matter management system:
   - Date received, requestor, department, topic, priority
2. **Document the analysis** (even if brief):
   - Facts considered, law/policy applied, conclusion reached
3. **Record the response:**
   - Date responded, substance of advice, any conditions or caveats
4. **Track follow-up:**
   - Whether advice was followed, outcome, any subsequent issues
5. **Retention:** Legal inquiry files retained for 7 years minimum

**Why document everything:** Protects the company if a decision is later questioned; demonstrates good faith; creates institutional knowledge for similar future inquiries.
""",
)


legal_briefing_generation = Skill(
    name="legal_briefing_generation",
    description="Generate contextual legal briefings including daily updates, topic research, and incident response formats.",
    category="compliance",
    agent_ids=[AgentID.LEGAL, AgentID.EXEC],
    knowledge_summary=(
        "Legal briefing generation framework with daily briefing format (regulatory updates, deadlines, "
        "active matters), topic research format, incident response briefing templates, "
        "and executive summary best practices."
    ),
    knowledge="""
## Legal Briefing Generation Framework

### 1. Daily Legal Briefing Format

```
DAILY LEGAL BRIEFING
Date: [Date]
Prepared by: [Legal team member]
Distribution: [GC, CLO, Legal team]

========================================
REGULATORY UPDATES
========================================
[List new regulations, proposed rules, enforcement actions relevant to the business]

1. [Regulation/Update]: [Brief description]
   Impact: [How it affects us]
   Action needed: [None / Monitor / Analyze / Implement by X date]
   Owner: [Assigned team member]

2. [Regulation/Update]: [Brief description]
   [Same format]

========================================
PENDING DEADLINES (Next 14 Days)
========================================
| Date | Matter | Deadline | Owner | Status |
|------|--------|----------|-------|--------|
| [Date] | [Matter] | [What's due] | [Name] | [On track / At risk] |

========================================
ACTIVE MATTERS STATUS
========================================
[Brief status update on each active legal matter]

Matter: [Name/Reference]
  Status: [Active / Paused / Settling / Closing]
  Last activity: [What happened]
  Next step: [What's coming] by [Date]
  Risk level: [Low / Medium / High / Critical]

========================================
NEW REQUESTS (Past 24 Hours)
========================================
| # | Requestor | Topic | Priority | Assigned To | Target Date |
|---|-----------|-------|----------|-------------|-------------|
| [#] | [Name] | [Brief topic] | [Urgent/Standard] | [Attorney] | [Date] |

========================================
UPCOMING MEETINGS
========================================
[Today/this week's legal meetings with brief prep notes]

========================================
FYI / INDUSTRY WATCH
========================================
[Notable legal developments in the industry -- cases, settlements,
regulatory trends that don't require immediate action but should
be tracked]
```

### 2. Topic Research Briefing Format

```
LEGAL RESEARCH BRIEFING
========================================
PRIVILEGED AND CONFIDENTIAL
ATTORNEY WORK PRODUCT

Topic: [Research question / issue title]
Requested by: [Name, Title]
Date: [Date]
Prepared by: [Attorney name]

========================================
ISSUE STATEMENT
========================================
[Clear, concise statement of the legal question being researched.
Frame as a yes/no question if possible.]

Example: "Can we lawfully implement a mandatory return-to-office
policy for employees who were hired as fully remote?"

========================================
SHORT ANSWER
========================================
[1-3 sentences with the conclusion. Lead with the answer.]

Example: "Yes, with conditions. The company can generally modify
work arrangements, but must honor existing contractual commitments,
provide reasonable notice, and engage in the ADA interactive process
for employees requesting remote work as an accommodation."

========================================
APPLICABLE LAW
========================================
[List and briefly describe relevant statutes, regulations, and
case law]

Federal:
- [Statute/Regulation]: [Brief description of relevance]

State ([applicable state]):
- [Statute/Regulation]: [Brief description]

Key cases:
- [Case name, citation]: [Holding and relevance]

========================================
ANALYSIS
========================================
[Detailed analysis applying the law to our facts. Organize by
sub-issue if multiple legal questions are involved.]

Sub-issue 1: [Title]
  [Analysis]

Sub-issue 2: [Title]
  [Analysis]

========================================
RISK ASSESSMENT
========================================
Risk level: [Low / Medium / High]
Potential exposure: [$X - $Y]
Likelihood of challenge: [Low / Medium / High]
Key risk factors:
  - [Factor 1]
  - [Factor 2]

========================================
RECOMMENDATION
========================================
[Clear, actionable recommendation. Include both the recommended
course of action and specific steps to implement it.]

1. [Recommended action]
2. [Implementation step]
3. [Ongoing monitoring/compliance step]

========================================
ALTERNATIVES CONSIDERED
========================================
[Other approaches considered and why they were not recommended]

Option B: [Description] -- Not recommended because [reason]
Option C: [Description] -- Not recommended because [reason]

========================================
LIMITATIONS
========================================
[Any caveats, assumptions, or areas where additional research
or outside counsel input is recommended]
```

### 3. Incident Response Legal Briefing

```
INCIDENT RESPONSE LEGAL BRIEFING
========================================
PRIVILEGED AND CONFIDENTIAL
ATTORNEY-CLIENT / WORK PRODUCT

Incident: [Brief description]
Date discovered: [Date/Time]
Severity: [Low / Medium / High / Critical]
Briefing prepared: [Date/Time]
Prepared by: [Attorney]

========================================
WHAT HAPPENED
========================================
[Factual summary of the incident based on current information.
Be precise about what is known vs. suspected vs. unknown.]

Timeline:
  [Date/Time]: [Event]
  [Date/Time]: [Event]
  [Date/Time]: [Discovery]

What we know: [Confirmed facts]
What we suspect: [Unconfirmed information]
What we don't know: [Gaps in information]

========================================
LEGAL EXPOSURE
========================================

Regulatory:
  - [Regulation]: [How incident may violate; potential penalty]
  - [Regulation]: [Same]

Contractual:
  - [Agreement]: [Breach potential; notification requirements]
  - [Agreement]: [Same]

Litigation:
  - [Potential claim type]: [Who could sue; estimated exposure]

Total estimated exposure range: [$X - $Y]

========================================
IMMEDIATE ACTIONS (First 72 Hours)
========================================
| Priority | Action | Owner | Deadline | Status |
|----------|--------|-------|----------|--------|
| 1 | [Contain the incident -- stop ongoing harm] | [Name] | [ASAP] | [Status] |
| 2 | [Preserve evidence -- litigation hold] | [Legal] | [24 hrs] | [Status] |
| 3 | [Assess notification obligations] | [Legal] | [48 hrs] | [Status] |
| 4 | [Notify insurance carrier] | [Risk/Legal] | [48 hrs] | [Status] |
| 5 | [Engage outside counsel / forensics] | [GC] | [48 hrs] | [Status] |

========================================
NOTIFICATION OBLIGATIONS
========================================

| Regulation | Trigger | Deadline | Method | Status |
|-----------|---------|----------|--------|--------|
| GDPR Art 33 | Personal data breach | 72 hours from awareness | Supervisory authority | [Status] |
| GDPR Art 34 | High risk to individuals | Without undue delay | Direct to individuals | [Status] |
| State breach laws | PII of state residents | Varies (30-90 days) | AG + individuals | [Status] |
| Contractual | Per DPA/MSA terms | Per contract (typically 24-72 hrs) | Written notice | [Status] |
| SEC (if public) | Material event | 4 business days (8-K) | SEC filing | [Status] |

========================================
COMMUNICATION PLAN
========================================

Internal:
  - Board/Audit Committee: [When and how to notify]
  - Employees: [If/when to communicate]

External:
  - Affected individuals: [Notification content and timing]
  - Regulators: [Which regulators, when, what to disclose]
  - Media: [Holding statement; spokesperson designated]
  - Customers/Partners: [Proactive or reactive communication]

Key message: [Core message across all communications]
Do NOT say: [Specific language to avoid]

========================================
PRESERVATION OBLIGATIONS
========================================
- Litigation hold issued: [Yes/No -- Date]
- Systems/data preserved: [List]
- Forensic imaging: [Status]
- Third-party preservation: [Vendors notified]
```

### 4. Executive Summary Best Practices

**Structure: Inverted pyramid**
1. **Conclusion first:** State the bottom line in the first sentence.
2. **Key supporting points:** 2-3 bullet points with the most important analysis.
3. **Risk/financial impact:** Quantify where possible.
4. **Recommended action:** Clear, specific next steps.
5. **Detailed analysis:** Available in appendix for those who want depth.

**Writing guidelines:**
- Use plain language, not legalese.
- Quantify risk in dollar ranges, not just "high/medium/low."
- Be direct: "We recommend X" not "It might be advisable to consider X."
- Limit executive summary to 1 page (half page preferred).
- Use bullet points and tables over paragraphs.
- Bold key conclusions and action items.
- Include a clear "decision needed by [date]" if time-sensitive.

**Common mistake:** Burying the conclusion after pages of analysis. Executives read the first paragraph. Put your answer there.
""",
)


# =============================================================================
# Registration
# =============================================================================

def register_finance_legal_skills() -> None:
    """Register all professional finance and legal/compliance skills."""
    all_skills = [
        # Finance
        financial_statements_generation,
        variance_analysis,
        journal_entry_preparation,
        month_end_close_management,
        account_reconciliation,
        sox_testing_methodology,
        audit_support_framework,
        # Legal / Compliance
        contract_review_framework,
        nda_triage,
        legal_risk_assessment,
        compliance_check_framework,
        vendor_agreement_check,
        e_signature_routing,
        legal_meeting_briefing,
        legal_inquiry_response,
        legal_briefing_generation,
    ]

    for skill in all_skills:
        skills_registry.register(skill)


# Auto-register when module is imported
register_finance_legal_skills()
