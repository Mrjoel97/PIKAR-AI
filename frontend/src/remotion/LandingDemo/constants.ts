export const VIDEO_FPS = 30;
export const VIDEO_WIDTH = 1920;
export const VIDEO_HEIGHT = 1080;

// Resolution presets
export const RESOLUTION = {
  hd: { width: 1920, height: 1080 },
  '4k': { width: 3840, height: 2160 },
} as const;

// Scene durations in seconds
export const INTRO_DURATION = 8;
export const BRIEFING_DURATION = 16;
export const WORKFLOW_DURATION = 14;
export const CONTENT_DURATION = 14;
export const RESEARCH_DURATION = 14;
export const ORCHESTRATION_DURATION = 14;
export const DASHBOARD_DURATION = 12;
export const OUTRO_DURATION = 8;
export const TRANSITION_FRAMES = 12; // 0.4s cross-dissolve

// All scene durations in order (for duration.ts)
export const SCENE_DURATIONS = [
  INTRO_DURATION,
  BRIEFING_DURATION,
  WORKFLOW_DURATION,
  CONTENT_DURATION,
  RESEARCH_DURATION,
  ORCHESTRATION_DURATION,
  DASHBOARD_DURATION,
  OUTRO_DURATION,
] as const;

// Agent definitions
export const AGENTS = [
  { name: 'Financial', emoji: '\u{1F4CA}' },
  { name: 'Content', emoji: '\u{270D}\u{FE0F}' },
  { name: 'Strategic', emoji: '\u{1F9ED}' },
  { name: 'Sales', emoji: '\u{1F4B0}' },
  { name: 'Marketing', emoji: '\u{1F4E3}' },
  { name: 'Operations', emoji: '\u{2699}\u{FE0F}' },
  { name: 'HR', emoji: '\u{1F465}' },
  { name: 'Compliance', emoji: '\u{1F6E1}\u{FE0F}' },
  { name: 'Support', emoji: '\u{1F4AC}' },
  { name: 'Data', emoji: '\u{1F4C8}' },
] as const;

// Real Pikar AI brand palette (from globals.css)
export const COLORS = {
  // Core teal palette
  teal50: '#99e2b4',
  teal100: '#75d9a1',
  teal200: '#56ccaa',
  teal300: '#45c4a0',
  teal400: '#3bbf97',
  teal500: '#2ba88f',
  teal600: '#24957e',
  teal700: '#1a8a6e',
  teal800: '#107860',
  teal900: '#036666',

  // Semantic
  primary: '#56ab91',
  accent: '#3bbf97',
  accentDark: '#1a8a6e',

  // Backgrounds
  bgDark: '#0a2e2e',
  bgCard: '#1a2f32',
  bgHero: '#036666',
  bgSection: '#f5f8f8',
  bgSectionDark: '#101f22',

  // Text
  textPrimary: '#ffffff',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  textDark: '#0f1419',

  // Borders
  border: '#e2e8f0',
  borderDark: 'rgba(255,255,255,0.06)',

  // Persona badge colors (matching real app Header component)
  solopreneur: { badge: '#f3e8ff', text: '#7c3aed', gradient: ['#8b5cf6', '#a855f7'], accent: '#7c3aed' },
  startup: { badge: '#dbeafe', text: '#2563eb', gradient: ['#3b82f6', '#60a5fa'], accent: '#2563eb' },
  sme: { badge: '#dcfce7', text: '#16a34a', gradient: ['#22c55e', '#4ade80'], accent: '#16a34a' },
  enterprise: { badge: '#fff7ed', text: '#ea580c', gradient: ['#f97316', '#fb923c'], accent: '#ea580c' },
} as const;

// Fonts (matching real app - Outfit for display, DM Sans for body)
export const FONTS = {
  display: 'Outfit, system-ui, sans-serif',
  body: 'DM Sans, system-ui, sans-serif',
  mono: 'Inter, monospace',
} as const;

export type PersonaId = 'solopreneur' | 'startup' | 'sme' | 'enterprise';
