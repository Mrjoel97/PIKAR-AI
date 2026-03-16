# Discovery Companion Onboarding System — Design Spec

**Date:** 2026-03-15
**Status:** Approved
**Scope:** Complete onboarding redesign — form wizard to conversational discovery

---

## 1. Problem Statement

The current onboarding is a 4-step form wizard that feels like a system, not a companion. For non-technical users (solopreneurs, startup founders, SME operators, enterprise executives), the first impression is cold and administrative. Every persona sees identical forms. There is no discovery of the user's vision, no warmth, no "first productive moment."

**Key gaps:**
- No middleware enforcing onboarding completion
- Every persona gets the same onboarding experience
- No post-onboarding first-time experience
- No business discovery or idea exploration
- Agent naming happens after setup, not as a relationship-building moment
- No onboarding state persistence on refresh
- Settings page has no backend integration

## 2. Solution: The Discovery Companion

Combine three approaches into one unified flow:

- **Vision-First Discovery (C)** — Opening act: user talks about their business/ideas
- **Conversational Model (A)** — Interaction model: chat-driven, not form-driven
- **Hybrid Structure (B)** — Backbone: structured data collection via inline widgets in chat

## 3. Conversation State Machine

```
GREETING → AGENT_NAME → DISCOVERY → PERSONA_REVEAL → PREFERENCES → FIRST_ACTION → COMPLETING
```

### Phase Details

| Phase | What Happens | Data Collected | UI Element |
|-------|-------------|----------------|------------|
| GREETING | Agent introduces itself warmly | none | Chat message |
| AGENT_NAME | "What would you like to call me?" | agent_name | Text input + name suggestions |
| DISCOVERY | Agent asks about business/vision, 2-3 follow-ups | company_name, industry, description, team_size, role, goals | Chat messages, NLP extraction |
| PERSONA_REVEAL | Agent celebrates persona match, shows preview | persona (auto-determined) | PersonaRevealCard + DashboardPreview |
| PREFERENCES | Quick inline form: tone + detail level | tone, verbosity, communication_style | PreferencesInlineForm widget |
| FIRST_ACTION | 3 persona-specific starting actions | first_action_choice, focus_areas (auto) | FirstActionPicker widget |
| COMPLETING | Background save, workspace provision, transition | onboarding_completed=true | OnboardingTransition animation |

### Persona-Specific Variations

| Moment | Solopreneur | Startup | SME | Enterprise |
|--------|-------------|---------|-----|------------|
| Opening question | "What's the big idea you're working on?" | "Tell me about what you're building and where you're at" | "What's the biggest operational challenge in your business right now?" | "What strategic priorities are keeping you up at night?" |
| Reveal tone | Excited, scrappy partner | Growth-obsessed co-founder | Steady operational advisor | Executive strategist |
| First actions | Revenue strategy, Brain dump, Weekly plan | Growth experiment, Pitch review, Burn rate check | Dept health check, Process audit, Compliance review | Stakeholder briefing, Risk assessment, Portfolio review |
| Preference defaults | Casual + Concise | Enthusiastic + Balanced | Professional + Detailed | Professional + Detailed |

## 4. Frontend Architecture

### New File Structure

```
frontend/src/app/onboarding/
├── page.tsx                    (single-page conversational onboarding)
├── layout.tsx                  (minimal chrome, clean canvas)
└── components/
    ├── OnboardingChat.tsx       (state machine + message rendering)
    ├── PersonaRevealCard.tsx    (animated persona celebration)
    ├── PreferencesInlineForm.tsx(inline tone + detail picker)
    ├── FirstActionPicker.tsx    (3 persona-specific action cards)
    ├── DashboardPreview.tsx     (mini dashboard preview)
    └── OnboardingTransition.tsx (smooth transition to dashboard)
```

### OnboardingChat State Machine

```typescript
type OnboardingPhase =
  | 'greeting'
  | 'agent_name'
  | 'discovery'
  | 'discovery_followup'
  | 'persona_reveal'
  | 'preferences'
  | 'first_action'
  | 'completing';

interface OnboardingState {
  phase: OnboardingPhase;
  messages: OnboardingMessage[];
  agentName: string | null;
  discoveryMessages: string[];
  extractedContext: BusinessContextInput | null;
  persona: Persona | null;
  preferences: { tone: string; verbosity: string } | null;
  firstAction: string | null;
  isProcessing: boolean;
  error: string | null;
}
```

**Key behaviors:**
- Agent messages are pre-scripted per phase (fast, predictable)
- Only DISCOVERY phase calls backend for NLP extraction
- Phase transitions triggered by user actions (message send, button click, form submit)
- State persisted to sessionStorage on every change (survives refresh)
- Typing animation on agent messages for natural feel (40ms per character)

### Component Specifications

**PersonaRevealCard:** Animated card with persona icon, gradient, title, description. Fade-in + scale animation. Shows "Here's what this means for you" with 3 bullet points.

**PreferencesInlineForm:** Horizontal card with two rows of 3 toggle buttons each. Pre-selected based on persona defaults. Confirm button advances to next phase.

**FirstActionPicker:** 3 cards in a row with icon, title, 1-line description. Hover effect. Click triggers COMPLETING phase and stores chosen action.

**DashboardPreview:** Mini screenshot/mockup of persona-specific dashboard. Shows key sections (KPI cards, main panels). Subtle glow/shadow effect.

**OnboardingTransition:** Full-screen overlay with agent name. 3 progress steps with checkmarks. Auto-redirects on completion. Error state with retry.

## 5. Backend Architecture

### New Endpoint: POST /onboarding/extract-context

```python
class ConversationExtractionInput(BaseModel):
    messages: list[str]

class ExtractionResult(BaseModel):
    extracted_context: BusinessContextInput
    persona_preview: str
    confidence: float

@router.post("/onboarding/extract-context")
async def extract_context(
    payload: ConversationExtractionInput,
    user_id: str = Depends(get_current_user_id),
) -> ExtractionResult:
    # Uses Gemini Flash to parse natural language into structured data
    # Returns extracted business context + persona preview + confidence
```

### New Middleware: Onboarding Guard

**Backend** (`app/middleware/onboarding_guard.py`):
- FastAPI middleware checking onboarding_completed for authenticated users
- Excluded paths: /auth, /onboarding, /health, /a2a, /docs, /openapi
- Returns 302 redirect to /onboarding for incomplete users

**Frontend** (`frontend/src/middleware.ts`):
- Next.js middleware for client-side route protection
- Checks onboarding status cookie or API call
- Redirects to /onboarding for dashboard routes when incomplete

### Data Flow

```
User types in chat
       ↓
OnboardingChat state machine processes message
       ↓ (DISCOVERY phase only)
POST /onboarding/extract-context → Gemini Flash parses → structured context
       ↓
Frontend stores extracted data in state
       ↓ (COMPLETING phase)
POST /onboarding/business-context  (extracted context)
POST /onboarding/preferences       (selected preferences)
POST /onboarding/agent-setup       (agent name + auto focus areas)
POST /onboarding/complete          (mark completed)
       ↓
Redirect to /dashboard/command-center?firstAction={chosen_action}
```

## 6. Existing Code Integration

### What stays the same:
- All existing backend endpoints (business-context, preferences, agent-setup, complete)
- Database schema (users_profile, user_executive_agents)
- PersonaContext provider
- UserOnboardingService business logic
- Persona determination logic
- Dashboard persona-specific layouts

### What changes:
- `frontend/src/app/onboarding/page.tsx` — Rewritten as conversational
- `frontend/src/app/onboarding/layout.tsx` — Simplified (no step indicators)
- `frontend/src/services/onboarding.ts` — Add extractContext() API function
- `app/routers/onboarding.py` — Add extract-context endpoint
- `app/fast_api_app.py` — Add onboarding guard middleware

### What's new:
- 6 new frontend components in onboarding/components/
- `frontend/src/middleware.ts` — Next.js middleware
- `app/middleware/onboarding_guard.py` — Backend middleware

## 7. Error Handling

- Network failures during extraction: Show retry button, allow manual fallback form
- Low confidence extraction (<0.6): Agent asks clarifying question
- Auth failures during save: Redirect to login with return URL
- Partial completion on refresh: Restore from sessionStorage state

## 8. Constraints

- Old onboarding pages kept for backward compatibility (not deleted)
- Backend data model unchanged — only collection method changes
- Use existing constants (PERSONA_INFO, TEAM_SIZES, INDUSTRIES, GOALS)
- Chat in onboarding is scripted, NOT the real AI agent
- Only DISCOVERY phase calls backend for NLP extraction
