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

export type DeviceType = 'DESKTOP' | 'MOBILE' | 'TABLET';

export interface ScreenVariant {
  id: string;
  screen_id: string;
  variant_index: number;
  screenshot_url: string | null;
  html_url: string | null;
  is_selected: boolean;
  prompt_used: string | null;
  device_type?: DeviceType;
  iteration?: number;
  created_at: string;
}

export interface IterationEvent {
  step: 'editing' | 'edit_complete' | 'ready' | 'error';
  message?: string;
  screen_id?: string;
  variant_id?: string;
  screenshot_url?: string;
  html_url?: string;
  iteration?: number;
}

export interface GenerationEvent {
  step: 'generating' | 'variant_generated' | 'device_generated' | 'ready' | 'error';
  message?: string;
  screen_id?: string;
  variant_index?: number;
  variant_id?: string;
  screenshot_url?: string;
  html_url?: string;
  variants?: ScreenVariant[];
  device_type?: DeviceType;
}

export interface AppScreen {
  id: string;
  project_id: string;
  name: string;
  device_type: DeviceType;
  page_type: string;
  page_slug: string;
  order_index: number;
  approved: boolean;
  stitch_project_id: string | null;
  selected_html_url?: string;
}

export interface MultiPageEvent {
  step: 'page_started' | 'page_complete' | 'build_complete' | 'error';
  page_index?: number;
  page_slug?: string;
  total_pages?: number;
  screen_id?: string;
  html_url?: string;
  screenshot_url?: string;
  message?: string;
  screens?: Array<{
    page_index: number;
    page_slug: string;
    page_title: string;
    screen_id: string;
    html_url: string;
    screenshot_url: string;
  }>;
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

export type ShipTarget = 'react' | 'pwa' | 'capacitor' | 'video';

export interface ShipEvent {
  step: 'target_started' | 'target_complete' | 'target_failed' | 'ship_complete';
  target?: ShipTarget;
  url?: string;
  error?: string;
  downloads?: Record<ShipTarget, string>;
}
