---
name: marketing
description: "Research-led go-to-market and approval-first channel operations for Pikar-AI. Always begin with deep market, niche, competitor, channel, and viral-content research before creating strategy, content, campaigns, social calendars, emails, ads, or channel operations. Use this skill when the user mentions marketing, GTM, launch strategy, social media, content calendars, waiting lists, email sequences, competitive analysis, channel growth, or when Codex should draft, queue, schedule, monitor, and report on marketing channels based on what is already working in the market instead of guessing from scratch."
---

# Pikar-AI Marketing Command Center

Use this skill to run research-led marketing for Pikar-AI. The operating philosophy is simple: do not create from a blank page when the market is already teaching us what works.

## Research-First Rule

Before the skill creates anything, it must build a fresh research pack.

That means:
- analyze the niche and audience language
- map direct and indirect competitors
- inspect competitor websites, offers, social accounts, ads, email flows, and landing pages
- identify best-performing posts, top content themes, recurring hooks, CTAs, emotional triggers, and proof structures
- study viral content patterns in the niche and adjacent niches
- turn the findings into a reusable pattern library

Do not jump straight to content calendars, posts, campaigns, or channel plans. If the user asks for those, do the research first and explain that the deliverables will be grounded in what is already working.

## Codex Adaptation

Use Codex tools as follows:

- Interpret `WebSearch` and `WebFetch` as web search plus opening the relevant pages.
- Interpret `Agent(...)` blocks as pseudocode for Codex `spawn_agent` calls.
- Run the Market Researcher first, wait for its output, then launch the selected specialist subagents in parallel.
- Keep discovery short and only ask blocking questions.
- Treat social and channel operations as approval-gated. Draft, queue, schedule, monitor, and report, but do not publish posts, send emails, reply from brand accounts, or change paid spend without explicit approval in the current turn.
- If the user wants help inside a social dashboard, scheduler, or analytics UI, use browser automation when available, but stop before the final publish or send action unless the user explicitly approves it.
- If the user explicitly asks for recurring monitoring, suggest or create a Codex automation for daily or weekly reporting instead of relying on memory.

## Phase 0: Discovery Interview

Before dispatching any specialists, gather enough context to scope the research correctly.

### Required Context

1. Where are we in the journey?
   - pre-launch
   - launch
   - post-launch / growth
2. What is the main goal right now?
   - waiting list
   - launch preparation
   - first paying customers
   - organic growth
   - thought leadership
   - ongoing channel operations
3. Which channels matter most right now?
   - LinkedIn
   - X/Twitter
   - Instagram
   - TikTok
   - YouTube
   - Reddit
   - email / newsletter
   - PR
   - community
   - paid ads
4. Budget and execution reality:
   - monthly budget range
   - who will execute
   - time pressure
5. Existing assets inventory:
   - landing page
   - email list size
   - social accounts and follower counts
   - videos, demos, blog posts, testimonials
6. Channel operations readiness:
   - which channels should Codex help operate now?
   - what scheduler or native platform tools already exist?
   - who approves posts, replies, email sends, or budget changes?
   - what reporting cadence is expected?

### Product Context (Pre-loaded)

The orchestrator already knows Pikar-AI's core positioning:

- Product: multi-agent AI executive system with 10 specialized agents
- Stack: Google ADK + Gemini, FastAPI, Next.js, Supabase
- Value prop: one AI system that handles the work of an executive team
- Target: founders, CEOs, and operators who need executive-level leverage without executive-level headcount
- Differentiator: not one chatbot, but a coordinated team of specialists with business tool integrations

## Phase 1: Build The Research Pack

This phase is non-negotiable. No strategy, content, social plan, ad plan, or channel operations work should start until the research pack exists.

### What The Research Pack Must Contain

1. Market landscape
   - direct competitors
   - indirect competitors
   - category framing
   - pricing and offer benchmarks
2. Audience and niche intelligence
   - where the target audience spends time
   - the exact language they use
   - pain points, desires, objections, and buying triggers
3. Channel benchmark
   - which channels competitors and adjacent winners use
   - account structure and positioning by platform
   - posting cadence, format mix, and CTA patterns
4. Competitor content and ad teardown
   - best-performing posts
   - strongest landing pages
   - ad angles and hooks
   - social proof and proof mechanisms
5. Viral content analysis
   - top-performing posts or ads in the niche and adjacent niches
   - repeatable frameworks, structures, and content beats
   - what made them spread or convert
6. Pattern library
   - proven hooks
   - narrative arcs
   - offer structures
   - visual formats
   - CTA styles
   - variables worth testing

### Evidence Rules

- Every meaningful claim should tie back to a source, a page, a post, a search query, or a visible metric.
- Prefer recent evidence for channels and content patterns because these change quickly.
- For channel work, inspect real competitor or adjacent-market accounts, not just company homepages.
- When engagement or view data is visible, capture it.
- Separate what is observed from what is inferred.

### Required Research Outputs

Save or synthesize these outputs before moving on:

- `marketing-outputs/research/market-research-brief.md`
- `marketing-outputs/research/competitor-teardowns.md`
- `marketing-outputs/research/channel-benchmark.md`
- `marketing-outputs/research/viral-framework-library.md`
- `marketing-outputs/research/research-summary.md`

Read `references/research-led-content-analysis.md` when doing niche, competitor, account, ad, or viral content teardown work.

### Research Freshness Rule

If the task is channel-specific or time-sensitive and the research is older than roughly 30 days, refresh the key competitors, channels, and viral examples before creating new work.

## Phase 2: Strategy Synthesis

After discovery and research, create a Marketing Brief grounded in the research pack.

### Marketing Brief Template

```markdown
# Pikar-AI Marketing Brief

## Positioning
- One-liner:
- Target audience:
- Key differentiators:
- Tone of voice:

## Current State
- Stage:
- Assets:
- Gaps:
- Ops mode: [strategy only / draft + approve / draft + schedule + monitor]

## Research-Led Insights
- What competitors are proving already works:
- What adjacent winners are proving already works:
- What Pikar-AI should deliberately avoid copying:
- Which frameworks or structures we will adapt first:

## Campaign Goals
- Primary:
- Secondary:
- Timeline:

## Channel Strategy
- Primary channels:
- Budget allocation:
- Organic vs paid mix:
- Approval owner:
- Reporting cadence:

## Success Metrics
- Metric 1 + target:
- Metric 2 + target:
- Metric 3 + target:

## Baselines For Testing
- Baseline pattern we are borrowing:
- Variable 1 to test:
- Variable 2 to test:
```

Present this brief to the user for approval before proceeding.

## Phase 3: Dispatch Specialist Agents

Only dispatch creation specialists after the research pack exists.

### Agent Dispatch Rules

| User Goal | Agents To Dispatch |
|---|---|
| Waiting list / demand gen | Market Researcher, Competitive Intel, Growth Hacker, Content Marketer, Social Media Manager, Channel Operator |
| Launch campaign | Market Researcher, Competitive Intel, Brand Strategist, Content Marketer, Growth Hacker, Social Media Manager, PR Specialist, Community Builder, Channel Operator as needed |
| Organic growth | Market Researcher, Competitive Intel, Content Marketer, Social Media Manager, Community Builder, Channel Operator |
| Paid acquisition | Market Researcher, Competitive Intel, Growth Hacker, Content Marketer |
| Brand / thought leadership | Market Researcher, Competitive Intel, Brand Strategist, Content Marketer, Social Media Manager |
| Community building | Market Researcher, Competitive Intel, Community Builder, Social Media Manager, Content Marketer, Channel Operator |
| Ongoing channel ops | Market Researcher, Competitive Intel, Social Media Manager, Channel Operator, Community Builder if community is in scope |
| Competitive analysis only | Market Researcher, Competitive Intel |

### Dispatch Inputs

Each specialist receives:
1. The Marketing Brief
2. The Market Research Brief
3. The competitor teardowns
4. The channel benchmark
5. The viral framework library
6. Their specialist brief from `agents/`
7. `references/marketing-psychology.md`
8. `references/research-led-content-analysis.md` for research-derived creation or teardown work
9. `references/channel-ops-runbook.md` when approval queues, scheduling, monitoring, or reporting are involved

### Agent Roster

0. **Market Researcher** (`agents/market-researcher.md`)
   - Runs first and builds the research pack
   - Deliverables: market brief, niche analysis, channel benchmark, viral framework library

0b. **Competitive Intelligence** (`agents/competitive-intel.md`)
   - Deep competitor marketing and channel teardown
   - Deliverables: competitor audits, account structure analysis, ad teardown, steal-and-improve map, monitoring plan

1. **Brand Strategist** (`agents/brand-strategist.md`)
   - Converts research into positioning and messaging
   - Deliverables: messaging matrix, brand guide, differentiated angle

2. **Content Marketer** (`agents/content-marketer.md`)
   - Builds research-led content from proven structures
   - Deliverables: content calendar, articles, emails, lead magnets tied to proven patterns

3. **Growth Hacker** (`agents/growth-hacker.md`)
   - Builds funnels and experiments from proven market patterns
   - Deliverables: funnels, landing-page ideas, test plan, growth loops

4. **Social Media Manager** (`agents/social-media-manager.md`)
   - Builds channel content from niche and competitor research first
   - Deliverables: platform strategy, approval-ready posting queue, monitoring hooks, pattern-based content plan

4b. **Channel Operator** (`agents/channel-operator.md`)
   - Turns approved strategy into approval-first channel operations
   - Deliverables: approval queue, scheduling plan, monitoring checklist, reporting pack

5. **PR Specialist** (`agents/pr-specialist.md`)
   - Builds launch angles and press materials from competitive whitespace and market timing

6. **Community Builder** (`agents/community-builder.md`)
   - Builds community programs using proven engagement patterns from comparable communities

## Phase 4: Research-Led Creation Rules

Every deliverable should show its lineage.

For each major piece of content, strategy, or campaign, identify:
- the source pattern or competitor example
- why it worked there
- what we are keeping
- what we are changing to make it specific to Pikar-AI
- which variable we are testing first

### Blank-Page Rule

Do not invent generic posts, ads, or email sequences just to fill a calendar. Start from:
- a proven hook
- a proven format
- a proven content structure
- a proven CTA pattern
- a proven emotional trigger

Then adapt it for Pikar-AI's audience and differentiation.

### A/B Testing Rule

Do not test random variations. Use a proven baseline from the research pack, then isolate one variable at a time, such as:
- hook framing
- proof mechanism
- CTA wording
- format length
- angle or persona lens

This makes testing faster and easier to interpret.

## Phase 5: Approval-First Channel Operations

Use this phase when the user wants Codex to help run active marketing channels, not just plan them.

### Research Prerequisite

Do not queue, schedule, or monitor a channel blindly. Use a fresh research pack first so operations are anchored to real market patterns.

### Operating Modes

- **Draft only** — prepare post copy, assets briefs, CTAs, links, and reply drafts for approval
- **Draft + queue** — prepare an approval queue with dates, channels, assets, and ready-to-schedule entries
- **Draft + schedule + monitor** — use an existing scheduler or native platform drafts to queue approved content, then monitor comments, mentions, inboxes, and analytics

### Mandatory Guardrails

1. Never publish or send anything from a brand account without explicit approval in the current turn.
2. Never reply to comments, DMs, or community threads as the brand without approval.
3. Never change paid budgets or campaign settings without approval.
4. Prefer existing schedulers, dashboards, and authenticated browser sessions.
5. Track every asset in an approval queue or operations log.
6. Keep the research source pattern attached to each scheduled item so later analysis is easy.

### Channel Ops Workflow

1. Build a channel inventory.
2. Create an approval queue for every candidate asset.
3. Attach the source pattern and test variable to each queued item.
4. After approval, schedule the approved items.
5. Monitor channel health and log replies, risks, and wins.
6. Produce a short operations report with the next 3 actions.

## Phase 6: Execution Planning

Once strategy and research-led deliverables are approved, create an execution timeline.

The timeline should state:
- what goes live first and why
- which proven pattern each item comes from
- which metrics define success
- which variables will be tested next

## Waiting List And PMF Work

When the user wants waiting-list or PMF work:
- use the research pack to identify which offers, headlines, incentives, and signup flows are already converting in the category
- identify the best-performing competitor and adjacent-market signup patterns
- adapt those mechanics before inventing new ones

If the user wants implementation built, coordinate with the codebase or browser automation flow — but keep approval gates for anything that would publish, send, or materially change a live channel.

## Important Principles

- **Research before creation** — observe first, create second.
- **Use what works as the starting point** — adapt proven patterns instead of guessing from zero.
- **Separate observation from inference** — be clear about what was seen versus what is concluded.
- **Actionable over abstract** — every output should help the team ship something.
- **Approval before publication** — draft boldly, publish cautiously.
- **Test from proven baselines** — make A/B testing easier by changing one variable at a time from a known-good structure.
- **Use current evidence** — marketing channels change quickly, so recent research matters.
- **AI-native positioning** — demonstrate the product's intelligence, not just describe it.
