export interface Notification {
    id: string;
    user_id: string;
    title: string;
    message: string;
    type: 'email' | 'push' | 'in_app' | 'sms';
    link?: string;
    is_read: boolean;
    created_at: string;
    metadata?: Record<string, any>;
    delivered_at?: string;
    status?: string;
}

export interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    phases: {
        name: string;
        steps: WorkflowStepDetail[];
    }[];
    created_at: string;
}

export interface WorkflowStepDetail {
    name: string;
    description: string;
    action_type: string; // e.g., 'send_email', 'ai_analysis', 'manual_approval'
    required_approval: boolean;
    config?: Record<string, any>;
}

export interface WorkflowExecution {
    id: string;
    user_id: string;
    template_id: string;
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'waiting_approval';
    current_phase_index: number;
    current_step_index: number;
    context: Record<string, any>;
    created_at: string;
    updated_at: string;
    completed_at?: string;
}

export interface WorkflowStep {
    id: string;
    execution_id: string;
    phase_name: string;
    step_name: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting_approval';
    input_data?: Record<string, any>;
    output_data?: Record<string, any>;
    error_message?: string;
    started_at?: string;
    completed_at?: string;
}

export interface Session {
    app_name: string;
    user_id: string;
    session_id: string;
    state: Record<string, any>;
    created_at: string;
    updated_at: string;
    current_version?: number;
}

export interface WidgetDefinition {
    type: string;
    title: string;
    data: Record<string, any>;
    dismissible?: boolean;
    expandable?: boolean;
}
