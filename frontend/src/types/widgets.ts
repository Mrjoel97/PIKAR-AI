/**
 * Centralized Type Definitions for Frontend Widgets
 * 
 * This module exports all data interfaces, types, and runtime validators for
 * the widget system. It serves as the single source of truth for widget data
 * structures, ensuring type safety across the application.
 */

// =============================================================================
// Widget Data Interfaces
// =============================================================================

/**
 * Data structure for the Calendar Widget
 */
export interface CalendarEvent {
    id: string;
    title: string;
    start: string;
    end: string;
    color?: string;
    location?: string;
    description?: string;
}

export interface CalendarData {
    view: 'month' | 'week' | 'day';
    events: CalendarEvent[];
}

/**
 * Data structure for the Form Widget
 */
export interface FieldDefinition {
    name: string;
    label: string;
    type: 'text' | 'number' | 'email' | 'select' | 'textarea' | 'date';
    required?: boolean;
    options?: string[]; // For select type
    defaultValue?: string;
    placeholder?: string;
}

export interface FormDataDefinition {
    fields: FieldDefinition[];
    submitLabel?: string;
}

/**
 * Data structure for the Table Widget
 */
export interface ColumnDefinition {
    key: string;
    label: string;
    sortable?: boolean;
}

export interface ActionDefinition {
    name: string;
    label: string;
    icon?: string;
}

export interface TableDataDefinition {
    columns: ColumnDefinition[];
    rows: Record<string, string | number | boolean | null>[];
    actions?: ActionDefinition[];
}

/**
 * Data structure for the Kanban Board Widget
 */
export interface Column {
    id: string;
    title: string;
    color?: string;
}

export interface Card {
    id: string;
    columnId: string;
    title: string;
    description?: string;
    tags?: string[];
}

export interface KanbanData {
    columns: Column[];
    cards: Card[];
}

/**
 * Data structure for the Revenue Chart Widget
 */
export interface RevenueData {
    periods: string[];
    values: number[];
    currency?: string;
    currentPeriod?: {
        revenue: number;
        change: number;
        changePercent: number;
    };
}

/**
 * Data structure for the Initiative Dashboard Widget
 */
export type InitiativeStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked' | 'on_hold';
export type InitiativePhase = 'ideation' | 'validation' | 'prototype' | 'build' | 'scale';

export interface Initiative {
    id: string;
    /** Display name (from DB title or name) */
    name: string;
    title?: string;
    status: InitiativeStatus;
    progress: number;
    phase?: InitiativePhase;
    phaseProgress?: Record<InitiativePhase, number>;
    owner?: string;
    dueDate?: string;
    template_id?: string;
    workflow_execution_id?: string;
    metadata?: Record<string, unknown>;
    goal?: string;
    currentPhase?: string;
    successCriteria?: string[];
    primaryWorkflow?: string;
    deliverables?: unknown[];
    evidence?: unknown[];
    blockers?: unknown[];
    nextActions?: unknown[];
    trustSummary?: Record<string, unknown>;
    verificationStatus?: string;
}

export interface InitiativeMetrics {
    total: number;
    completed: number;
    in_progress: number;
    blocked: number;
}

export interface InitiativeDashboardData {
    initiatives: Initiative[];
    metrics: InitiativeMetrics;
}

export interface InitiativeTemplate {
    id: string;
    title: string;
    description: string;
    persona: string;
    category: string;
    icon: string;
    priority: string;
    phases: Array<{ name: string; steps: string[] }>;
    suggested_workflows: string[];
    kpis: string[];
}

/**
 * Data structure for the Product Launch Widget
 */
export interface Milestone {
    name: string;
    date: string;
    status: 'completed' | 'in_progress' | 'pending' | 'delayed';
}

export interface ProductLaunchData {
    milestones: Milestone[];
    status: 'on_track' | 'at_risk' | 'delayed';
}

/**
 * Data structure for the Workflow Builder Widget
 */
export interface WorkflowNode {
    id: string;
    position: { x: number; y: number };
    data: { label: string };
    style?: Record<string, string>;
}

export interface WorkflowEdge {
    id: string;
    source: string;
    target: string;
    animated?: boolean;
    style?: Record<string, string>;
}

export interface WorkflowBuilderData {
    nodes?: WorkflowNode[];
    edges?: WorkflowEdge[];
}

/**
 * Data structure for the Morning Briefing Widget
 */
export interface BriefingData {
    greeting: string;
    pending_approvals: {
        id: string;
        action_type: string;
        created_at: string;
        token: string;
    }[];
    online_agents: number;
    system_status: string;
}

/**
 * Data structure for the Boardroom Widget
 */
export interface TranscriptItem {
    speaker: string;
    content: string;
    sentiment: string;
    round?: number;
    stance?: string;
}

export interface BoardPacket {
    topic: string;
    recommendation: string;
    confidence: number;
    pros: string[];
    cons: string[];
    risks: string[];
    estimated_impact: string;
    next_steps: string[];
    dissenting_views: string[];
}

export interface BoardroomData {
    topic: string;
    transcript: TranscriptItem[];
    verdict: string;
    board_packet?: BoardPacket | null;
    vote_summary?: Record<string, string>;
}

/**
 * Data structure for the Suggested Workflows Widget
 */
export interface Suggestion {
    id: string;
    pattern_description: string;
    suggested_goal: string;
    suggested_context: string;
    status: string;
}

export interface SuggestedWorkflowsData {
    suggestions: Suggestion[];
}

/**
 * Data structure for the Workflow Status Widget
 */
export interface BraindumpAnalysisData {
    markdown: string;
    documentId: string;
    sessionId?: string;
    title: string;
    keyThemes: string[];
    actionItemCount: number;
}

export interface WorkflowData {
    execution_id?: string;
    execution?: Record<string, unknown>;
    template_name?: string;
    history?: Record<string, unknown>[];
    current_phase_index?: number;
    current_step_index?: number;
}

// =============================================================================
// Widget Type Unions
// =============================================================================

export type WidgetWorkspaceMode = 'embedded' | 'focus' | 'grid' | 'split' | 'compare';

export interface MediaWidgetContract {
    asset_id?: string;
    bundle_id?: string;
    deliverable_id?: string;
    workspace_item_id?: string;
    session_id?: string;
    workflow_execution_id?: string;
    editable_url?: string;
    platform_profile?: string;
}

export interface WidgetWorkspace {
    mode?: WidgetWorkspaceMode;
    bundleId?: string;
    deliverableId?: string;
    workspaceItemId?: string;
    sessionId?: string;
    workflowExecutionId?: string;
}

/**
 * Union of all supported widget types
 */
export type WidgetType =
    | 'initiative_dashboard'
    | 'revenue_chart'
    | 'product_launch'
    | 'kanban_board'
    | 'workflow_builder'
    | 'morning_briefing'
    | 'daily_briefing'
    | 'boardroom'
    | 'suggested_workflows'
    | 'form'
    | 'table'
    | 'calendar'
    | 'workflow'
    | 'image'
    | 'video'
    | 'video_spec'
    | 'braindump_analysis'
    | 'campaign_hub'
    | 'self_improvement'
    | 'workflow_observability'
    | 'workflow_timeline'
    | 'landing_pages'
    | 'api_connections'
    | 'department_activity';

/**
 * Campaign Hub widget data — surfaces campaign status, content pipeline,
 * social publishing, and marketing analytics in the workspace.
 */
export interface CampaignHubData {
    /** Active campaign summary */
    campaign?: {
        id: string;
        name: string;
        status: string;
        campaign_type?: string;
        target_audience?: string;
        channels?: string[];
        metrics?: {
            impressions?: number;
            clicks?: number;
            conversions?: number;
            ctr?: number;
        };
    };
    /** Content pipeline status */
    content_pipeline?: {
        phase: string;
        items: Array<{
            type: string;
            title: string;
            status: 'draft' | 'in_review' | 'approved' | 'published';
            platform?: string;
            media_url?: string;
        }>;
    };
    /** Connected social accounts status */
    social_accounts?: Array<{
        platform: string;
        connected: boolean;
        last_post?: string;
    }>;
    /** Research summary (from deep research) */
    research_summary?: string;
    /** Quick stats */
    stats?: Array<{
        label: string;
        value: string;
        change?: string;
        trend?: 'up' | 'down' | 'flat';
    }>;
    /** Competitor tracking entries */
    competitors?: Array<{
        handle: string;
        platform: string;
        name?: string;
        followers?: number;
        engagement_rate?: number;
        posting_frequency?: string;
        growth_trend?: 'up' | 'down' | 'flat';
        recent_posts?: number;
        avatar_url?: string;
    }>;
    /** Industry news feed */
    news_feed?: Array<{
        id: string;
        headline: string;
        source: string;
        published_at: string;
        summary: string;
        topic?: string;
        url?: string;
    }>;
    /** Analytics date range label */
    analytics_period?: string;
    /** Top performing content */
    top_posts?: Array<{
        title: string;
        platform?: string;
        impressions?: number;
        engagement_rate?: number;
        published_at?: string;
    }>;
}

/**
 * Data structure for the Landing Pages Widget
 */
export interface LandingPagesData {
    pages: Array<{
        id: string;
        title: string;
        slug: string;
        published: boolean;
        submission_count: number;
        updated_at: string;
    }>;
    total_published: number;
    total_drafts: number;
    total_leads: number;
}

/**
 * Data structure for the API Connections Widget
 */
export interface APIConnectionData {
    api_name: string;
    spec_url: string;
    connected_at: string;
    endpoint_count: number;
    status: 'healthy' | 'stale' | 'error';
    tools: string[];
}

export interface APIConnectionsWidgetData {
    connections: APIConnectionData[];
    connection_count: number;
}

/**
 * Discriminated union for widget data, mapping types to their data interfaces
 */
export type WidgetData =
    | { type: 'calendar'; data: CalendarData }
    | { type: 'form'; data: FormDataDefinition }
    | { type: 'table'; data: TableDataDefinition }
    | { type: 'kanban_board'; data: KanbanData }
    | { type: 'revenue_chart'; data: RevenueData }
    | { type: 'initiative_dashboard'; data: InitiativeDashboardData }
    | { type: 'product_launch'; data: ProductLaunchData }
    | { type: 'workflow_builder'; data: WorkflowBuilderData }
    | { type: 'morning_briefing'; data: BriefingData }
    | { type: 'boardroom'; data: BoardroomData }
    | { type: 'suggested_workflows'; data: SuggestedWorkflowsData }
    | { type: 'workflow'; data: WorkflowData }
    | { type: 'image'; data: { imageUrl: string; prompt?: string; caption?: string } & MediaWidgetContract }
    | { type: 'video'; data: { videoUrl: string; title?: string; caption?: string; progress?: unknown[]; storyboard_captions?: string[] } & MediaWidgetContract }
    | { type: 'video_spec'; data: { title?: string; prompt?: string; scenes?: Array<{ text: string; duration: number }>; fps?: number; durationInFrames?: number; remotion_code?: string; instructions?: string[]; caption?: string } & MediaWidgetContract }
    | { type: 'braindump_analysis'; data: BraindumpAnalysisData }
    | { type: 'campaign_hub'; data: CampaignHubData }
    | { type: 'self_improvement'; data: Record<string, unknown> }
    | { type: 'workflow_observability'; data: Record<string, unknown> }
    | { type: 'workflow_timeline'; data: { execution_id: string } }
    | { type: 'api_connections'; data: APIConnectionsWidgetData }
    | { type: 'department_activity'; data: Record<string, unknown> }
    | { type: 'landing_pages'; data: LandingPagesData };

/**
 * Generic definition of a widget as received from the backend
 */
export type WidgetDefinition = {
    type: WidgetType;
    title?: string;
    data: Record<string, unknown>; // Keep flexible for now, will be typed in future phases
    workspace?: WidgetWorkspace;
    dismissible?: boolean;
    expandable?: boolean;
};

// =============================================================================
// Runtime Type Guards
// =============================================================================

/**
 * Type guard to check if a string is a valid WidgetType
 * @param type The type string to check
 * @returns True if the string is a valid WidgetType
 */
export function isValidWidgetType(type: string): type is WidgetType {
    const validTypes: WidgetType[] = [
        'initiative_dashboard', 'revenue_chart', 'product_launch',
        'kanban_board', 'workflow_builder', 'morning_briefing', 'daily_briefing',
        'boardroom', 'suggested_workflows', 'form', 'table', 'calendar',
        'workflow', 'image', 'video', 'video_spec', 'braindump_analysis',
        'campaign_hub', 'self_improvement', 'workflow_observability', 'workflow_timeline',
        'landing_pages', 'api_connections', 'department_activity'
    ];
    return validTypes.includes(type as WidgetType);
}

export function isValidWorkspaceMode(mode: unknown): mode is WidgetWorkspaceMode {
    return typeof mode === 'string' && ['embedded', 'focus', 'grid', 'split', 'compare'].includes(mode);
}

/**
 * Type guard for CalendarData
 * @param data The data object to check
 * @returns True if data matches the CalendarData interface
 */
export function isCalendarData(data: unknown): data is CalendarData {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;

    // Require view to be one of 'month' | 'week' | 'day'
    if (!d.view || !['month', 'week', 'day'].includes(d.view as string)) return false;

    // Ensure events is an array
    if (!Array.isArray(d.events)) return false;

    // Ensure each event has required string fields
    return d.events.every((e: unknown) =>
        typeof e === 'object' &&
        e !== null &&
        typeof (e as Record<string, unknown>).id === 'string' &&
        typeof (e as Record<string, unknown>).title === 'string' &&
        typeof (e as Record<string, unknown>).start === 'string' &&
        typeof (e as Record<string, unknown>).end === 'string'
    );
}

/**
 * Type guard for FormDataDefinition
 * @param data The data object to check
 * @returns True if data matches the FormDataDefinition interface
 */
export function isFormData(data: unknown): data is FormDataDefinition {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    return Array.isArray(d.fields) && d.fields.every((f: unknown) =>
        typeof f === 'object' &&
        f !== null &&
        typeof (f as Record<string, unknown>).name === 'string' &&
        typeof (f as Record<string, unknown>).label === 'string'
    );
}

/**
 * Type guard for TableDataDefinition
 * @param data The data object to check
 * @returns True if data matches the TableDataDefinition interface
 */
export function isTableData(data: unknown): data is TableDataDefinition {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    return Array.isArray(d.columns) && Array.isArray(d.rows);
}

/**
 * Type guard for KanbanData
 * @param data The data object to check
 * @returns True if data matches the KanbanData interface
 */
export function isKanbanData(data: unknown): data is KanbanData {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    return Array.isArray(d.columns) && Array.isArray(d.cards);
}



/**
 * Type guard for RevenueData
 * @param data The data object to check
 * @returns True if data matches the RevenueData interface
 */
export function isRevenueData(data: unknown): data is RevenueData {
    if (!data || typeof data !== 'object') return false;
    const d = data as any;
    return Array.isArray(d.periods) && Array.isArray(d.values);
}

/**
 * Type guard for InitiativeDashboardData
 * @param data The data object to check
 * @returns True if data matches the InitiativeDashboardData interface
 */
export function isInitiativeDashboardData(data: unknown): data is InitiativeDashboardData {
    if (!data || typeof data !== 'object') return false;
    const d = data as any;
    return Array.isArray(d.initiatives);
}

/**
 * Type guard for ProductLaunchData
 * @param data The data object to check
 * @returns True if data matches the ProductLaunchData interface
 */
export function isProductLaunchData(data: unknown): data is ProductLaunchData {
    if (!data || typeof data !== 'object') return false;
    const d = data as any;
    return Array.isArray(d.milestones);
}

/**
 * Type guard for WorkflowBuilderData
 * @param data The data object to check
 * @returns True if data matches the WorkflowBuilderData interface
 */
export function isWorkflowBuilderData(data: unknown): data is WorkflowBuilderData {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    // nodes and edges are optional in interface
    if (d.nodes && !Array.isArray(d.nodes)) return false;
    if (d.edges && !Array.isArray(d.edges)) return false;
    return true;
}



/**
 * Type guard for BriefingData
 * @param data The data object to check
 * @returns True if data matches the BriefingData interface
 */
export function isBriefingData(data: unknown): data is BriefingData {
    if (!data || typeof data !== 'object') return false;
    const d = data as any;
    return typeof d.greeting === 'string' && Array.isArray(d.pending_approvals);
}

/**
 * Type guard for BoardroomData
 * @param data The data object to check
 * @returns True if data matches the BoardroomData interface
 */
export function isBoardroomData(data: unknown): data is BoardroomData {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    return typeof d.topic === 'string' && Array.isArray(d.transcript);
}



/**
 * Type guard for SuggestedWorkflowsData
 * @param data The data object to check
 * @returns True if data matches the SuggestedWorkflowsData interface
 */
export function isBraindumpAnalysisData(data: unknown): data is BraindumpAnalysisData {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    return typeof d.markdown === 'string' && typeof d.documentId === 'string';
}

export function isSuggestedWorkflowsData(data: unknown): data is SuggestedWorkflowsData {
    if (!data || typeof data !== 'object') return false;
    const d = data as any;
    return Array.isArray(d.suggestions);
}

/**
 * Type guard for the top-level WidgetDefinition
 * Checks if the object has a valid type and a data object
 * @param widget The object to check
 * @returns True if the object is a valid WidgetDefinition
 */
export function validateWidgetDefinition(widget: unknown): widget is WidgetDefinition {
    if (!widget || typeof widget !== 'object') return false;
    const w = widget as Record<string, unknown>;

    if (
        typeof w.type !== 'string' ||
        !isValidWidgetType(w.type) ||
        typeof w.data !== 'object' ||
        w.data === null
    ) {
        return false;
    }

    if (w.workspace !== undefined) {
        if (!w.workspace || typeof w.workspace !== 'object') return false;
        const workspace = w.workspace as Record<string, unknown>;
        if (workspace.mode !== undefined && !isValidWorkspaceMode(workspace.mode)) {
            return false;
        }
    }

    switch (w.type) {
        case 'calendar': return isCalendarData(w.data);
        case 'form': return isFormData(w.data);
        case 'table': return isTableData(w.data);
        case 'kanban_board': return isKanbanData(w.data);
        case 'revenue_chart': return isRevenueData(w.data);
        case 'initiative_dashboard': return isInitiativeDashboardData(w.data);
        case 'product_launch': return isProductLaunchData(w.data);
        case 'workflow_builder': return isWorkflowBuilderData(w.data);
        case 'morning_briefing': return isBriefingData(w.data);
        case 'daily_briefing': return isBriefingData(w.data);
        case 'boardroom': return isBoardroomData(w.data);
        case 'suggested_workflows': return isSuggestedWorkflowsData(w.data);
        case 'workflow': return true; // Simple validation for now
        case 'image': return typeof (w.data as any)?.imageUrl === 'string';
        case 'video': return typeof (w.data as any)?.videoUrl === 'string';
        case 'video_spec': return typeof (w.data as any)?.title === 'string' || typeof (w.data as any)?.remotion_code === 'string';
        case 'braindump_analysis': return isBraindumpAnalysisData(w.data);
        case 'self_improvement': return true;
        case 'workflow_observability': return true;
        case 'workflow_timeline': return typeof (w.data as any)?.execution_id === 'string';
        case 'api_connections': return Array.isArray((w.data as any)?.connections);
        case 'landing_pages': return Array.isArray((w.data as any)?.pages);
        case 'department_activity': return true;
        default: return false;
    }
}

// =============================================================================
// Widget Persistence & Display Interfaces
// =============================================================================

export interface SavedWidget {
    id: string;
    definition: WidgetDefinition;
    isMinimized: boolean;
    isPinned: boolean;
    createdAt: string;
    sessionId: string;
    userId: string;
}

export interface RenderOptions {
    className?: string;
    onAction?: (action: string, payload?: unknown) => void;
    onDismiss?: () => void;
    showControls?: boolean;
}


