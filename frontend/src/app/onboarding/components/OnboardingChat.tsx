'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { PersonaType } from '@/services/onboarding';
import { PersonaRevealCard } from './PersonaRevealCard';
import { DashboardPreview } from './DashboardPreview';
import { PreferencesInlineForm } from './PreferencesInlineForm';
import { FirstActionPicker } from './FirstActionPicker';
import { OnboardingTransition } from './OnboardingTransition';

// ============================================================================
// Types
// ============================================================================

type OnboardingPhase =
  | 'greeting'
  | 'agent_name'
  | 'agent_name_confirm'
  | 'discovery'
  | 'discovery_followup_1'
  | 'discovery_followup_2'
  | 'extracting'
  | 'persona_reveal'
  | 'preferences'
  | 'first_action'
  | 'completing';

interface ChatMessage {
  id: string;
  role: 'agent' | 'user';
  content: string;
  timestamp: number;
  widget?: 'persona_reveal' | 'preferences' | 'first_action' | 'transition';
  widgetData?: Record<string, unknown>;
}

interface OnboardingState {
  phase: OnboardingPhase;
  messages: ChatMessage[];
  agentName: string;
  discoveryMessages: string[];
  persona: PersonaType | null;
  extractedContext: Record<string, unknown> | null;
  preferences: { tone: string; verbosity: string } | null;
  firstAction: string | null;
  firstActionId: string | null;
}

// ============================================================================
// Persona-specific conversation scripts
// ============================================================================

const AGENT_NAME_SUGGESTIONS = ['Atlas', 'Nova', 'Sage', 'Aria', 'Max', 'Echo', 'Iris', 'Kai'];

const DISCOVERY_QUESTIONS: Record<string, { opener: string; followups: string[] }> = {
  default: {
    opener: "Now tell me \u2014 what are you building or working on? I'd love to hear about your business, your idea, or even just what's been on your mind lately.",
    followups: [
      "That sounds exciting! How big is your team right now? Is it just you, or do you have people working with you?",
      "And what's the one thing you most want to achieve in the next few months? What would make you feel like you're really winning?",
    ],
  },
};

const PERSONA_REVEAL_MESSAGES: Record<PersonaType, string> = {
  solopreneur: "From what you've shared, it sounds like you're building this on your own \u2014 and honestly, that takes serious guts. I've configured myself as your **Solopreneur co-pilot**. That means I'll keep things lean, focus on what moves the needle this week, and never bury you in unnecessary process.",
  startup: "You're clearly in growth mode \u2014 I love that energy! I've set myself up as your **Startup co-pilot**. I'll focus on helping you move fast, validate ideas, track what matters, and keep your team aligned as you scale.",
  sme: "You've built something real and substantial. I've configured myself as your **SME operations partner**. I'll help you optimize what's working, keep departments coordinated, and make sure nothing falls through the cracks as you grow.",
  enterprise: "You're operating at scale \u2014 that comes with both enormous opportunity and complexity. I've set myself up as your **Enterprise strategist**. I'll focus on governance, stakeholder visibility, risk management, and making sure your teams execute with precision.",
};

// ============================================================================
// Session Storage Persistence
// ============================================================================

const STORAGE_KEY = 'pikar_onboarding_state';

const saveState = (state: OnboardingState) => {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Silent fail for SSR or storage full
  }
};

const loadState = (): OnboardingState | null => {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
};

const clearState = () => {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Silent fail
  }
};

// ============================================================================
// Component
// ============================================================================

export function OnboardingChat() {
  const [state, setState] = useState<OnboardingState>(() => {
    const saved = typeof window !== 'undefined' ? loadState() : null;
    return saved || {
      phase: 'greeting',
      messages: [],
      agentName: '',
      discoveryMessages: [],
      persona: null,
      extractedContext: null,
      preferences: null,
      firstAction: null,
      firstActionId: null,
    };
  });

  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasInitialized = useRef(false);
  const activeTimeouts = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      activeTimeouts.current.forEach(clearTimeout);
    };
  }, []);

  // Persist state changes
  useEffect(() => {
    saveState(state);
  }, [state]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages]);

  // Tracked setTimeout that cleans up on unmount
  const safeTimeout = useCallback((fn: () => void, delay: number) => {
    const id = setTimeout(() => {
      activeTimeouts.current = activeTimeouts.current.filter((t) => t !== id);
      fn();
    }, delay);
    activeTimeouts.current.push(id);
    return id;
  }, []);

  // Add agent message with typing animation
  const addAgentMessage = useCallback((content: string, widget?: ChatMessage['widget'], widgetData?: Record<string, unknown>) => {
    setIsTyping(true);

    // Simulate typing delay based on message length (min 600ms, max 2000ms)
    const delay = Math.min(Math.max(content.length * 15, 600), 2000);

    safeTimeout(() => {
      setState((prev) => ({
        ...prev,
        messages: [
          ...prev.messages,
          {
            id: `agent-${Date.now()}`,
            role: 'agent',
            content,
            timestamp: Date.now(),
            widget,
            widgetData,
          },
        ],
      }));
      setIsTyping(false);
    }, delay);
  }, [safeTimeout]);

  // Add user message
  const addUserMessage = useCallback((content: string) => {
    setState((prev) => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          id: `user-${Date.now()}`,
          role: 'user',
          content,
          timestamp: Date.now(),
        },
      ],
    }));
  }, []);

  // Shared logic for processing agent name (Fix #6: DRY)
  const processAgentName = useCallback((name: string) => {
    const capitalized = name.charAt(0).toUpperCase() + name.slice(1);
    setState((prev) => ({ ...prev, agentName: capitalized, phase: 'agent_name_confirm' }));

    safeTimeout(() => {
      addAgentMessage(
        `${capitalized} \u2014 I love it! Great to officially meet you. \u{1F60A}\n\n${DISCOVERY_QUESTIONS.default.opener}`
      );
      safeTimeout(() => {
        setState((prev) => ({ ...prev, phase: 'discovery' }));
      }, 1500);
    }, 300);
  }, [addAgentMessage, safeTimeout]);

  // Initialize greeting
  useEffect(() => {
    if (hasInitialized.current) return;
    if (state.messages.length > 0) {
      hasInitialized.current = true;
      return; // Restored from storage
    }
    hasInitialized.current = true;

    addAgentMessage(
      "Hey! I'm really excited to meet you. I'm going to be your AI executive partner \u2014 helping you think through strategy, manage operations, and grow your business.\n\nBut first, I'd love a name. What would you like to call me?"
    );

    // After greeting, show name suggestions
    safeTimeout(() => {
      setState((prev) => ({ ...prev, phase: 'agent_name' }));
    }, 2200);
  }, [state.messages.length, addAgentMessage, safeTimeout]);

  // Handle user message submission
  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const message = inputValue.trim();
    if (!message || isTyping) return;

    setInputValue('');
    addUserMessage(message);

    // Process based on current phase
    switch (state.phase) {
      case 'agent_name': {
        processAgentName(message);
        break;
      }

      case 'discovery': {
        setState((prev) => ({
          ...prev,
          discoveryMessages: [...prev.discoveryMessages, message],
          phase: 'discovery_followup_1',
        }));

        safeTimeout(() => {
          addAgentMessage(DISCOVERY_QUESTIONS.default.followups[0]);
        }, 300);
        break;
      }

      case 'discovery_followup_1': {
        setState((prev) => ({
          ...prev,
          discoveryMessages: [...prev.discoveryMessages, message],
          phase: 'discovery_followup_2',
        }));

        safeTimeout(() => {
          addAgentMessage(DISCOVERY_QUESTIONS.default.followups[1]);
        }, 300);
        break;
      }

      case 'discovery_followup_2': {
        setState((prev) => ({
          ...prev,
          discoveryMessages: [...prev.discoveryMessages, message],
          phase: 'extracting',
        }));

        // Call extract-context API
        safeTimeout(() => {
          addAgentMessage("Give me just a moment to process everything you've shared...");
        }, 300);

        try {
          const { extractContext } = await import('@/services/onboarding');
          const allMessages = [...state.discoveryMessages, message];
          const result = await extractContext(allMessages);

          const persona = result.persona_preview as PersonaType;

          setState((prev) => ({
            ...prev,
            persona,
            extractedContext: result.extracted_context as Record<string, unknown>,
            phase: 'persona_reveal',
          }));

          // Show persona reveal
          safeTimeout(() => {
            const revealMessage = PERSONA_REVEAL_MESSAGES[persona] || PERSONA_REVEAL_MESSAGES.startup;
            addAgentMessage(revealMessage, 'persona_reveal', { persona });
          }, 1500);

        } catch (error) {
          console.error('Context extraction failed:', error);
          // Fallback to startup persona
          setState((prev) => ({
            ...prev,
            persona: 'startup',
            extractedContext: { goals: ['growth'] },
            phase: 'persona_reveal',
          }));

          safeTimeout(() => {
            addAgentMessage(
              PERSONA_REVEAL_MESSAGES.startup,
              'persona_reveal',
              { persona: 'startup' }
            );
          }, 1500);
        }
        break;
      }

      default:
        break;
    }
  };

  // Handle name suggestion click (Fix #3: removed dead setInputValue calls)
  const handleNameClick = (name: string) => {
    addUserMessage(name);
    processAgentName(name);
  };

  // Handle preferences submission
  const handlePreferencesSubmit = (prefs: { tone: string; verbosity: string }) => {
    setState((prev) => ({ ...prev, preferences: prefs, phase: 'first_action' }));

    const agentName = state.agentName || 'Your agent';
    addAgentMessage(
      `Perfect! I'll keep that in mind every time we talk.\n\nNow here's the fun part \u2014 let's actually do something useful right now. ${agentName} isn't just about setup; I want to help you make progress today. Pick one to get started:`,
      'first_action',
      { persona: state.persona }
    );
  };

  // Handle first action selection (Fix #17: accept both id and prompt)
  const handleFirstAction = (actionId: string, actionPrompt: string) => {
    setState((prev) => ({
      ...prev,
      firstAction: actionPrompt,
      firstActionId: actionId,
      phase: 'completing',
    }));
    addAgentMessage(
      'Great choice! Let me set up your workspace and we\'ll dive right in.',
      'transition',
      { agentName: state.agentName, persona: state.persona, firstAction: actionPrompt, firstActionId: actionId }
    );
  };

  // Handle persona reveal continue
  const handlePersonaRevealContinue = () => {
    setState((prev) => ({ ...prev, phase: 'preferences' }));

    addAgentMessage(
      "Two quick things before we dive in \u2014 how would you like me to communicate with you?",
      'preferences',
      { persona: state.persona }
    );
  };

  // Determine placeholder based on phase
  const getPlaceholder = () => {
    switch (state.phase) {
      case 'agent_name':
        return 'Type a name or pick one below...';
      case 'discovery':
        return 'Tell me about your business or idea...';
      case 'discovery_followup_1':
      case 'discovery_followup_2':
        return 'Type your answer...';
      default:
        return '';
    }
  };

  // Should show input?
  const showInput = ['agent_name', 'discovery', 'discovery_followup_1', 'discovery_followup_2'].includes(state.phase);

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-120px)]">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {state.messages.map((msg) => (
          <div key={msg.id}>
            {/* Message bubble */}
            <div
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-[fadeInUp_0.3s_ease-out_both]`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
                  msg.role === 'user'
                    ? 'bg-teal-600 text-white rounded-br-md'
                    : 'bg-slate-100 text-slate-800 rounded-bl-md'
                }`}
              >
                {msg.role === 'agent' && state.agentName && (
                  <div className="text-xs font-semibold text-teal-600 mb-1">
                    {state.agentName}
                  </div>
                )}
                <div className="text-[15px] leading-relaxed whitespace-pre-wrap">
                  {msg.content.split('**').map((part, i) =>
                    i % 2 === 1 ? (
                      <strong key={i} className="font-semibold">{part}</strong>
                    ) : (
                      <span key={i}>{part}</span>
                    )
                  )}
                </div>
              </div>
            </div>

            {/* Inline widgets */}
            {msg.widget === 'persona_reveal' && msg.widgetData?.persona && (
              <div className="mt-4 space-y-4 animate-[fadeInUp_0.4s_ease-out_both]">
                <PersonaRevealCard
                  persona={msg.widgetData.persona as PersonaType}
                  onContinue={handlePersonaRevealContinue}
                />
                <DashboardPreview
                  persona={msg.widgetData.persona as PersonaType}
                />
              </div>
            )}

            {msg.widget === 'preferences' && (
              <div className="mt-4 animate-[fadeInUp_0.4s_ease-out_both]">
                <PreferencesInlineForm
                  persona={state.persona}
                  onSubmit={handlePreferencesSubmit}
                />
              </div>
            )}

            {msg.widget === 'first_action' && (
              <div className="mt-4 animate-[fadeInUp_0.4s_ease-out_both]">
                <FirstActionPicker
                  persona={state.persona || 'startup'}
                  onSelect={handleFirstAction}
                />
              </div>
            )}

            {msg.widget === 'transition' && (
              <div className="mt-4 animate-[fadeInUp_0.4s_ease-out_both]">
                <OnboardingTransition
                  agentName={state.agentName}
                  persona={state.persona || 'startup'}
                  firstAction={state.firstAction || ''}
                  firstActionId={state.firstActionId || ''}
                  extractedContext={state.extractedContext}
                  preferences={state.preferences}
                  onComplete={clearState}
                />
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex justify-start animate-[fadeInUp_0.2s_ease-out_both]">
            <div className="bg-slate-100 rounded-2xl rounded-bl-md px-5 py-3.5">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Name suggestions (only in agent_name phase) */}
      {state.phase === 'agent_name' && !isTyping && (
        <div className="px-4 pb-2">
          <div className="flex flex-wrap gap-2 justify-center">
            {AGENT_NAME_SUGGESTIONS.map((name) => (
              <button
                key={name}
                onClick={() => handleNameClick(name)}
                className="px-4 py-2 bg-white border border-slate-200 rounded-full text-sm font-medium text-slate-700 hover:bg-teal-50 hover:border-teal-300 hover:text-teal-700 transition-all duration-200 shadow-sm hover:shadow-md"
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      {showInput && (
        <div className="border-t border-slate-200 bg-white px-4 py-4">
          <form onSubmit={handleSubmit} className="flex items-center gap-3 max-w-3xl mx-auto">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={getPlaceholder()}
              disabled={isTyping}
              autoFocus
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400 disabled:opacity-50 transition-all"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isTyping}
              className="w-11 h-11 flex items-center justify-center rounded-xl bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>
      )}

      {/* Extracting indicator */}
      {state.phase === 'extracting' && (
        <div className="border-t border-slate-200 bg-white px-4 py-4">
          <div className="flex items-center justify-center gap-3 text-slate-500">
            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-sm">Understanding your business...</span>
          </div>
        </div>
      )}
    </div>
  );
}
