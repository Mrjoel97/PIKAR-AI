// frontend/src/remotion/LandingDemo/constants.ts
export const VIDEO_FPS = 30;
export const VIDEO_WIDTH = 1920;
export const VIDEO_HEIGHT = 1080;

// Scene durations in seconds
export const INTRO_DURATION = 8;
export const PERSONA_DURATION = 25;
export const EXECUTIVE_DURATION = 30;
export const OUTRO_DURATION = 8;
export const TRANSITION_FRAMES = 15; // 0.5s cross-dissolve

// Brand colors
export const COLORS = {
  bgDark: '#0a0f1a',
  bgCard: '#111827',
  accent: '#0dccf2',
  accentDark: '#0891b2',
  textPrimary: '#ffffff',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  solopreneur: { gradient: ['#f97316', '#f59e0b'], accent: '#f97316' },
  founder: { gradient: ['#8b5cf6', '#a855f7'], accent: '#8b5cf6' },
  owner: { gradient: ['#3b82f6', '#06b6d4'], accent: '#3b82f6' },
  executive: { gradient: ['#475569', '#1e293b'], accent: '#475569' },
} as const;

// Scene start frame lookup (populated at runtime by composition)
export type PersonaId = 'solopreneur' | 'founder' | 'owner' | 'executive';
