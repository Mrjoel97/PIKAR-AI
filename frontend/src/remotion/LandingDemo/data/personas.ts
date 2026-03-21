import { type PersonaId } from '../constants';

export interface AgentInfo {
  name: string;
  emoji: string;
  role: string;
}

export interface ChatMessage {
  sender: 'user' | 'agent';
  agentName?: string;
  text: string;
  delaySeconds: number;
}

export interface PersonaSceneData {
  id: PersonaId;
  title: string;
  subtitle: string;
  emoji: string;
  gradient: [string, string];
  agents: AgentInfo[];
  chatMessages: ChatMessage[];
  caption: string;
  dashboardMetrics?: { label: string; value: string; trend: 'up' | 'down' | 'flat' }[];
}

export const PERSONA_SCENES: PersonaSceneData[] = [
  {
    id: 'solopreneur',
    title: 'Solopreneur',
    subtitle: 'Maximize efficiency for one',
    emoji: '\u{1F680}',
    gradient: ['#8b5cf6', '#a855f7'],
    agents: [
      { name: 'Content Agent', emoji: '\u{270D}\u{FE0F}', role: 'Drafting pitch deck' },
      { name: 'Sales Agent', emoji: '\u{1F4B0}', role: 'Lead scoring' },
      { name: 'Strategic Agent', emoji: '\u{1F9ED}', role: 'Week planning' },
    ],
    chatMessages: [
      { sender: 'user', text: 'Help me plan my week and draft a pitch deck for investors.', delaySeconds: 2 },
      { sender: 'agent', agentName: 'Strategic Agent', text: "I've analyzed your calendar. You have 3 open slots this week. I'll draft a priority plan while Content works on your deck.", delaySeconds: 5 },
      { sender: 'agent', agentName: 'Content Agent', text: 'Pitch deck draft ready \u2014 12 slides covering problem, solution, traction, and ask. Shall I refine the financial projections slide?', delaySeconds: 10 },
      { sender: 'agent', agentName: 'Sales Agent', text: "4 warm leads identified from your LinkedIn. I've ranked them by likelihood to respond this week.", delaySeconds: 15 },
    ],
    caption: 'One person. Ten agents. Zero overhead.',
    dashboardMetrics: [
      { label: 'Tasks Automated', value: '47', trend: 'up' },
      { label: 'Hours Saved', value: '12.5h', trend: 'up' },
      { label: 'Lead Score', value: '8.4/10', trend: 'up' },
    ],
  },
  {
    id: 'startup',
    title: 'Startup',
    subtitle: 'Scale from MVP to Series A',
    emoji: '\u{26A1}',
    gradient: ['#3b82f6', '#60a5fa'],
    agents: [
      { name: 'Financial Agent', emoji: '\u{1F4CA}', role: 'Series A projections' },
      { name: 'Data Agent', emoji: '\u{1F4C8}', role: 'Metrics dashboard' },
      { name: 'Strategic Agent', emoji: '\u{1F9ED}', role: 'Board deck prep' },
    ],
    chatMessages: [
      { sender: 'user', text: 'Prepare my Series A board deck with updated financial projections.', delaySeconds: 2 },
      { sender: 'agent', agentName: 'Financial Agent', text: 'Revenue model updated: projecting $2.4M ARR by Q4 based on current growth rate of 18% MoM. Burn rate extended to 14 months.', delaySeconds: 5 },
      { sender: 'agent', agentName: 'Data Agent', text: 'Key metrics compiled: CAC dropped 23% since last quarter, LTV:CAC ratio now 4.2x. Charts ready for the deck.', delaySeconds: 10 },
      { sender: 'agent', agentName: 'Strategic Agent', text: 'Board deck structured: 15 slides with narrative arc. Investor-ready PDF and speaker notes attached.', delaySeconds: 15 },
    ],
    caption: 'From raw data to investor-ready in minutes.',
    dashboardMetrics: [
      { label: 'ARR Projected', value: '$2.4M', trend: 'up' },
      { label: 'Burn Rate', value: '14mo', trend: 'up' },
      { label: 'LTV:CAC', value: '4.2x', trend: 'up' },
    ],
  },
  {
    id: 'sme',
    title: 'SME',
    subtitle: 'Operational stability you can trust',
    emoji: '\u{1F3E2}',
    gradient: ['#22c55e', '#4ade80'],
    agents: [
      { name: 'Operations Agent', emoji: '\u{2699}\u{FE0F}', role: 'Monthly review' },
      { name: 'HR Agent', emoji: '\u{1F465}', role: 'Team pulse check' },
      { name: 'Compliance Agent', emoji: '\u{1F6E1}\u{FE0F}', role: 'Audit prep' },
    ],
    chatMessages: [
      { sender: 'user', text: 'Run my monthly ops review and flag anything off-track.', delaySeconds: 2 },
      { sender: 'agent', agentName: 'Operations Agent', text: 'Monthly review complete. Supply chain costs up 8% \u2014 flagged for immediate review. 2 projects ahead of schedule, 1 at risk.', delaySeconds: 5 },
      { sender: 'agent', agentName: 'HR Agent', text: 'Team pulse: 87% satisfaction. Engineering flagged workload concerns. Recommending 2 additional hires for Q2.', delaySeconds: 10 },
      { sender: 'agent', agentName: 'Compliance Agent', text: 'Q1 audit checklist: 94% complete. 3 items pending \u2014 data retention policy, SOC2 evidence, vendor assessments. Deadline in 12 days.', delaySeconds: 15 },
    ],
    caption: 'Every department. One command. Full visibility.',
    dashboardMetrics: [
      { label: 'Ops Score', value: '94%', trend: 'up' },
      { label: 'Team Health', value: '87%', trend: 'flat' },
      { label: 'Compliance', value: '94%', trend: 'up' },
    ],
  },
  {
    id: 'enterprise',
    title: 'Enterprise',
    subtitle: 'Enterprise-grade intelligence',
    emoji: '\u{1F3DB}\u{FE0F}',
    gradient: ['#f97316', '#fb923c'],
    agents: [
      { name: 'Executive Agent', emoji: '\u{1F451}', role: 'Morning briefing' },
      { name: 'Financial Agent', emoji: '\u{1F4CA}', role: 'P&L summary' },
      { name: 'Strategic Agent', emoji: '\u{1F9ED}', role: 'Market analysis' },
      { name: 'Operations Agent', emoji: '\u{2699}\u{FE0F}', role: 'KPI dashboard' },
      { name: 'Data Agent', emoji: '\u{1F4C8}', role: 'Anomaly detection' },
      { name: 'Compliance Agent', emoji: '\u{1F6E1}\u{FE0F}', role: 'Risk assessment' },
    ],
    chatMessages: [
      { sender: 'user', text: 'Give me a morning briefing across all departments.', delaySeconds: 2 },
      { sender: 'agent', agentName: 'Executive Agent', text: "Good morning. I've coordinated with all 10 agents. Here's your briefing:", delaySeconds: 4 },
      { sender: 'agent', agentName: 'Financial Agent', text: 'Revenue up 12% MoM. Margin pressure from Q1 hiring \u2014 tracking to plan.', delaySeconds: 8 },
      { sender: 'agent', agentName: 'Operations Agent', text: 'All systems green. Warehouse throughput +15%. One vendor SLA breach flagged.', delaySeconds: 12 },
      { sender: 'agent', agentName: 'Data Agent', text: 'Anomaly detected: Customer churn spike in APAC region. Recommending deep-dive.', delaySeconds: 16 },
      { sender: 'agent', agentName: 'Executive Agent', text: '3 decisions need your attention today. Approvals queued in priority order.', delaySeconds: 20 },
    ],
    caption: 'All 10 agents. One orchestrator. Total command.',
    dashboardMetrics: [
      { label: 'Revenue', value: '+12%', trend: 'up' },
      { label: 'Ops Status', value: 'Green', trend: 'flat' },
      { label: 'Decisions', value: '3 pending', trend: 'flat' },
    ],
  },
];
