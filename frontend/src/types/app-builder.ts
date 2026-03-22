/**
 * App Builder types — single source of truth for GSD stage values,
 * question definitions, and project shape.
 */

/** GSD_STAGES must match the DB CHECK constraint exactly (7 values). */
export const GSD_STAGES = [
  { id: 'questioning', label: 'Questioning', icon: 'HelpCircle' },
  { id: 'research',    label: 'Research',    icon: 'Search' },
  { id: 'brief',       label: 'Brief',       icon: 'FileText' },
  { id: 'building',    label: 'Building',    icon: 'Hammer' },
  { id: 'verifying',   label: 'Verifying',   icon: 'CheckCircle' },
  { id: 'shipping',    label: 'Shipping',    icon: 'Rocket' },
  { id: 'done',        label: 'Done',        icon: 'Star' },
] as const;

export type GsdStage = (typeof GSD_STAGES)[number]['id'];

export interface AppProject {
  id: string;
  user_id: string;
  title: string;
  status: 'draft' | 'generating' | 'ready' | 'exported';
  stage: GsdStage;
  creative_brief: Record<string, string>;
  design_system?: Record<string, unknown>;
  sitemap?: SitemapPage[];
  build_plan?: BuildPlanPhase[];
  created_at: string;
  updated_at: string;
}

export interface DesignBrief {
  colors: Array<{ hex: string; name: string }>;
  typography: { heading: string; body: string; scale?: string };
  spacing: { base_unit: string; section_padding?: string; card_padding?: string };
  raw_markdown: string;
}

export interface SitemapPage {
  page: string;
  title: string;
  sections: string[];
  device_targets: string[];
}

export interface BuildPlanPhase {
  phase: number;
  label: string;
  screens: Array<{ name: string; page: string; device: string }>;
  dependencies: number[];
}

export interface ResearchEvent {
  step: 'searching' | 'synthesizing' | 'saving' | 'ready' | 'error';
  message?: string;
  data?: {
    colors?: DesignBrief['colors'];
    typography?: DesignBrief['typography'];
    spacing?: DesignBrief['spacing'];
    raw_markdown?: string;
    sitemap?: SitemapPage[];
  };
}

export interface Question {
  id: string;
  prompt: string;
  choices: string[];
}

/** QUESTIONS must be used in this exact order. Last question (name) has no choices — free text. */
export const QUESTIONS: Question[] = [
  { id: 'what',    prompt: 'What do you want to build?',        choices: ['Landing page', 'Web app', 'Mobile app', 'Portfolio', 'E-commerce'] },
  { id: 'who',     prompt: 'Who is this for?',                  choices: ['My business', 'A client', 'My personal brand', 'Just experimenting'] },
  { id: 'purpose', prompt: 'What should visitors do?',          choices: ['Book a call', 'Sign up', 'Buy something', 'Learn about me', 'Browse content'] },
  { id: 'vibe',    prompt: 'Pick a style vibe',                 choices: ['Clean & minimal', 'Bold & energetic', 'Warm & friendly', 'Professional & serious', 'Creative & playful'] },
  { id: 'name',    prompt: 'Give your project a working title', choices: [] },
];
