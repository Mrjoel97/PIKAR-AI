'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Circle, X, ChevronDown, ChevronUp, Sparkles, ArrowRight } from 'lucide-react';
import { PersonaType } from '@/services/onboarding';

// ─── Persona-specific checklist items ───────────────────────────────────────

export interface ChecklistItem {
  id: string;
  icon: string;
  title: string;
  description: string;
  prompt: string; // Pre-filled chat prompt when clicked
  completed: boolean;
}

type ChecklistTemplate = Omit<ChecklistItem, 'completed'>;

const PERSONA_CHECKLISTS: Record<PersonaType, ChecklistTemplate[]> = {
  solopreneur: [
    { id: 'revenue_strategy', icon: '💰', title: 'Map your revenue strategy', description: 'Identify your best income opportunities', prompt: 'Use my saved onboarding brief, profile, and vault context to map my current revenue strategy, identify the strongest income opportunities, and tell me the next practical move to increase revenue.' },
    { id: 'brain_dump', icon: '🧠', title: 'Do a brain dump', description: 'Get all your ideas organized', prompt: 'I want to do a brain dump. Start from what you already know from my onboarding, profile, and knowledge vault so I do not have to repeat myself, then help me turn my ideas, tasks, and thoughts into a prioritized action plan.' },
    { id: 'weekly_plan', icon: '📋', title: 'Plan your week', description: 'Create a focused 7-day action plan', prompt: 'Use my onboarding brief and recent context to build a focused 7-day plan for me. I want a realistic weekly plan with priorities, quick wins, and what to ignore for now.' },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate a repetitive task', prompt: 'Use what you already know about my business and help me choose and launch the best first workflow for me. Show me the workflow templates that fit my current goals and guide me step by step.' },
    { id: 'content_piece', icon: '✍️', title: 'Create your first content piece', description: 'Generate a blog post or social update', prompt: 'Using my onboarding brief, business context, and existing vault knowledge, help me create my first content piece and explain why it is the right thing to publish first.' },
  ],
  startup: [
    { id: 'growth_experiment', icon: '🚀', title: 'Design a growth experiment', description: 'Test a hypothesis to accelerate growth', prompt: 'Help me design a growth experiment. I want to identify a hypothesis we can test quickly to learn what drives growth for our startup.' },
    { id: 'pitch_review', icon: '🎯', title: 'Review your pitch', description: 'Sharpen your value proposition', prompt: 'I want to work on my pitch. Help me sharpen our value proposition and story for investors and customers.' },
    { id: 'burn_rate', icon: '📊', title: 'Check your burn rate', description: 'Understand your runway', prompt: 'Help me analyze our burn rate and runway. I want to understand our financial health and make smart spending decisions.' },
    { id: 'team_update', icon: '👥', title: 'Write a team update', description: 'Align your team on priorities', prompt: 'Help me write a weekly team update. I want to communicate our wins, learnings, and priorities for next week.' },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate a repeatable process', prompt: 'What workflows can you help me automate? Show me the available workflow templates for startups.' },
  ],
  sme: [
    { id: 'dept_health', icon: '🏥', title: 'Run a department health check', description: 'See how each team is performing', prompt: 'Run a department health check across my organization. I want to understand how each team is performing and where we need attention.' },
    { id: 'process_audit', icon: '⚙️', title: 'Audit your processes', description: 'Find bottlenecks and optimize', prompt: 'Help me audit our key business processes. I want to find bottlenecks, inefficiencies, and opportunities to streamline operations.' },
    { id: 'compliance_review', icon: '🛡️', title: 'Run a compliance review', description: 'Ensure nothing falls through cracks', prompt: 'Run a compliance review for our business. I want to make sure we are meeting all regulatory requirements and nothing is falling through the cracks.' },
    { id: 'kpi_dashboard', icon: '📊', title: 'Set up KPI tracking', description: 'Define and monitor key metrics', prompt: 'Help me set up KPI tracking for my departments. I want to define the key metrics we should monitor and create a reporting cadence.' },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate a department process', prompt: 'What workflows can you help me automate? Show me the available workflow templates for SME operations.' },
  ],
  enterprise: [
    { id: 'stakeholder_briefing', icon: '📋', title: 'Prepare a stakeholder briefing', description: 'Strategic update for leadership', prompt: 'Help me prepare a stakeholder briefing. I need a strategic update covering our key initiatives, risks, and progress for the leadership team.' },
    { id: 'risk_assessment', icon: '⚠️', title: 'Run a risk assessment', description: 'Identify and prioritize risks', prompt: 'Run a comprehensive risk assessment for our organization. I want to identify, categorize, and prioritize the key risks we need to manage.' },
    { id: 'portfolio_review', icon: '📈', title: 'Review initiative portfolio', description: 'Evaluate portfolio health', prompt: 'Help me review our initiative portfolio. I want to evaluate which initiatives are on track, which need attention, and how resources are allocated.' },
    { id: 'approval_workflow', icon: '✅', title: 'Set up an approval workflow', description: 'Configure governance controls', prompt: 'Help me set up an approval workflow for high-impact decisions. I want governance that adds visibility without slowing us down.' },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate an enterprise process', prompt: 'What workflows can you help me automate? Show me the available workflow templates for enterprise operations.' },
  ],
};

export function getChecklistItemsForPersona(persona: PersonaType): ChecklistItem[] {
  const templates = PERSONA_CHECKLISTS[persona] || PERSONA_CHECKLISTS.startup;
  return templates.map(t => ({ ...t, completed: false }));
}

function buildGenericPrompt(item: Pick<ChecklistItem, 'title' | 'description'>): string {
  return `Use my saved onboarding brief, profile, and knowledge vault context to help me complete "${item.title}". Guide me step by step, ask only focused follow-up questions, and do not make me repeat information I already provided. Context: ${item.description}`;
}

export function enrichChecklistItems(persona: PersonaType, items: Array<Partial<ChecklistItem> & { id: string }>): ChecklistItem[] {
  const templates = PERSONA_CHECKLISTS[persona] || PERSONA_CHECKLISTS.startup;
  const templatesById = new Map(templates.map((template) => [template.id, template]));

  return items.map((item) => {
    const template = templatesById.get(item.id);
    const title = item.title || template?.title || item.id;
    const description = item.description || template?.description || 'Complete this onboarding step with agent guidance.';

    return {
      id: item.id,
      icon: item.icon || template?.icon || '✨',
      title,
      description,
      prompt: item.prompt || template?.prompt || buildGenericPrompt({ title, description }),
      completed: item.completed === true,
    };
  });
}

export function getRecommendedChecklistItem(items: ChecklistItem[]): ChecklistItem | null {
  return items.find((item) => !item.completed) ?? null;
}

// ─── Component ──────────────────────────────────────────────────────────────

interface OnboardingChecklistProps {
  persona: PersonaType;
  userId: string;
  onActionClick?: (prompt: string) => void;
}

export default function OnboardingChecklist({ persona, userId, onActionClick }: OnboardingChecklistProps) {
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);

  // Fetch checklist state from API
  useEffect(() => {
    const fetchChecklist = async () => {
      try {
        const res = await fetch('/api/onboarding-checklist');
        if (res.status === 404) {
          // No checklist exists — user completed onboarding before this feature
          setDismissed(true);
          return;
        }
        if (!res.ok) throw new Error('Failed to fetch checklist');
        const data = await res.json() as { items: Array<Partial<ChecklistItem> & { id: string }>; dismissed: boolean };
        if (data.dismissed) {
          setDismissed(true);
          return;
        }
        setItems(enrichChecklistItems(persona, data.items));
      } catch {
        // Silently fail — don't block dashboard
        setDismissed(true);
      } finally {
        setLoading(false);
      }
    };
    fetchChecklist();
  }, [persona, userId]);

  const completedCount = items.filter(i => i.completed).length;
  const totalCount = items.length;
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  const allDone = completedCount === totalCount && totalCount > 0;
  const recommendedItem = getRecommendedChecklistItem(items);

  const handleDismiss = useCallback(async () => {
    setDismissed(true);
    try {
      await fetch('/api/onboarding-checklist', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dismiss: true }),
      });
    } catch {
      // Don't revert — user intent is clear
    }
  }, []);

  const handleActionClick = (item: ChecklistItem) => {
    onActionClick?.(item.prompt);
  };

  if (loading || dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="mx-4 sm:mx-6 mt-6 mb-4"
      >
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 bg-gradient-to-r from-teal-50 to-emerald-50 border-b border-slate-100">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-3 flex-1 text-left"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shadow-sm">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800">
                  {allDone ? 'All done! You\'re set up.' : 'Get started with Pikar AI'}
                </h3>
                <p className="text-xs text-slate-500">
                  {completedCount} of {totalCount} completed automatically as you finish work
                </p>
              </div>
              {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
            </button>

            <button
              onClick={handleDismiss}
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-white/60 rounded-lg transition-colors ml-2"
              title="Dismiss checklist"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-slate-100">
            <motion.div
              className="h-full bg-gradient-to-r from-teal-500 to-emerald-500"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>

          {/* Items */}
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {recommendedItem && (
                  <div className="px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-teal-50/90 to-emerald-50/90">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-teal-700">
                          Recommended Next Step
                        </p>
                        <p className="mt-1 text-sm font-semibold text-slate-800">
                          {recommendedItem.title}
                        </p>
                        <p className="mt-1 text-xs text-slate-600">
                          {recommendedItem.description} The system marks this complete automatically when your work is detected.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleActionClick(recommendedItem)}
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-700"
                      >
                        Let the agent guide me
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
                <div className="divide-y divide-slate-100">
                  {items.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleActionClick(item)}
                      className={`w-full flex items-center gap-4 px-5 py-3.5 text-left transition-colors group ${
                        item.completed
                          ? 'bg-slate-50/50'
                          : 'hover:bg-teal-50/50'
                      }`}
                    >
                      {/* Check icon */}
                      <div className="flex-shrink-0">
                        {item.completed ? (
                          <CheckCircle2 className="w-5 h-5 text-teal-500" />
                        ) : (
                          <Circle className="w-5 h-5 text-slate-300 group-hover:text-teal-400 transition-colors" />
                        )}
                      </div>

                      {/* Icon */}
                      <span className={`text-xl flex-shrink-0 ${item.completed ? 'opacity-50' : ''}`}>
                        {item.icon}
                      </span>

                      {/* Text */}
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-semibold ${item.completed ? 'text-slate-400 line-through' : 'text-slate-700'}`}>
                          {item.title}
                        </p>
                        <p className={`text-xs ${item.completed ? 'text-slate-300' : 'text-slate-500'}`}>
                          {item.description}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
