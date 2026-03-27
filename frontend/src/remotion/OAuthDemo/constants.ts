// OAuth Verification Video Constants
// Reuses brand palette from LandingDemo

export const VIDEO_FPS = 30;
export const VIDEO_WIDTH = 1920;
export const VIDEO_HEIGHT = 1080;

// Scene durations in seconds
export const INTRO_DURATION = 6;
export const APP_IDENTITY_DURATION = 10;
export const CONSENT_SCREEN_DURATION = 12;
export const GMAIL_READONLY_DURATION = 10;
export const GMAIL_MODIFY_DURATION = 8;
export const GMAIL_SEND_DURATION = 8;
export const CALENDAR_DURATION = 8;
export const SECURITY_DURATION = 8;
export const OUTRO_DURATION = 5;

export const SCENE_DURATIONS = [
  INTRO_DURATION,
  APP_IDENTITY_DURATION,
  CONSENT_SCREEN_DURATION,
  GMAIL_READONLY_DURATION,
  GMAIL_MODIFY_DURATION,
  GMAIL_SEND_DURATION,
  CALENDAR_DURATION,
  SECURITY_DURATION,
  OUTRO_DURATION,
] as const;

export const TRANSITION_FRAMES = 10; // ~0.33s cross-dissolve

export const TOTAL_DURATION_FRAMES =
  SCENE_DURATIONS.reduce((sum, d) => sum + d * VIDEO_FPS, 0) -
  (SCENE_DURATIONS.length - 1) * TRANSITION_FRAMES;

// Brand colors (from LandingDemo constants)
export const COLORS = {
  teal500: '#2ba88f',
  teal600: '#24957e',
  teal700: '#1a8a6e',
  teal900: '#036666',
  primary: '#56ab91',
  accent: '#3bbf97',
  accentDark: '#1a8a6e',
  bgDark: '#0a2e2e',
  bgCard: '#1a2f32',
  textPrimary: '#ffffff',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  textDark: '#0f1419',
  border: '#e2e8f0',

  // Scope classification colors
  scopeRestricted: '#ef4444',
  scopeRestrictedBg: '#fef2f2',
  scopeSensitive: '#f59e0b',
  scopeSensitiveBg: '#fffbeb',
  scopeBasic: '#22c55e',
  scopeBasicBg: '#f0fdf4',

  // Google brand
  googleBlue: '#4285f4',
  googleRed: '#ea4335',
  googleYellow: '#fbbc04',
  googleGreen: '#34a853',
} as const;

export const FONTS = {
  display: 'Outfit, system-ui, sans-serif',
  body: 'DM Sans, system-ui, sans-serif',
  mono: 'JetBrains Mono, monospace',
} as const;

// OAuth scope definitions
export const SCOPES = [
  {
    scope: 'email',
    label: 'Email Address',
    classification: 'basic' as const,
    description: 'View your email address',
    appUsage: 'Account identification and login',
  },
  {
    scope: 'profile',
    label: 'Profile Info',
    classification: 'basic' as const,
    description: 'View your basic profile info',
    appUsage: 'Display name and avatar in dashboard',
  },
  {
    scope: 'gmail.readonly',
    label: 'Read Gmail',
    classification: 'restricted' as const,
    description: 'View your email messages and settings',
    appUsage: 'Daily briefings, inbox triage, email classification',
    icon: '📨',
  },
  {
    scope: 'gmail.modify',
    label: 'Manage Gmail',
    classification: 'restricted' as const,
    description: 'Manage your email labels and archive',
    appUsage: 'Archive processed emails, manage labels after triage',
    icon: '📂',
  },
  {
    scope: 'gmail.send',
    label: 'Send Gmail',
    classification: 'restricted' as const,
    description: 'Send email on your behalf',
    appUsage: 'AI agents send emails with user approval',
    icon: '📤',
  },
  {
    scope: 'calendar',
    label: 'Google Calendar',
    classification: 'sensitive' as const,
    description: 'View and edit events on your calendars',
    appUsage: 'Schedule meetings, view upcoming events, check availability',
    icon: '📅',
  },
] as const;
