
import { createSupabaseClient } from '../_shared/supabase.ts';
import { handleError, logInfo, logError, validateRequest, corsHeaders, requireAuth, assertUuid } from '../_shared/utils.ts';
import { WidgetDefinition } from '../_shared/types.ts';
import { z } from 'zod';

// Schema for request validation
const RequestSchema = z.object({
    user_id: z.string(),
    widget_type: z.enum(['initiative_dashboard', 'revenue_chart', 'workflow_builder', 'kanban_board', 'calendar']),
    parameters: z.record(z.any()).optional(),
});

Deno.serve(async (req) => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders });
    }

    try {
        const auth = await requireAuth(req);
        const body = await validateRequest(req);
        const validation = RequestSchema.safeParse(body);

        if (!validation.success) {
            throw new Error(`Validation error: ${JSON.stringify(validation.error.issues)}`);
        }

        const { user_id, widget_type, parameters } = validation.data;
        assertUuid(user_id, 'user_id');
        if (!auth.isServiceRole && auth.user?.id !== user_id) {
            throw new Error('Unauthorized');
        }
        const supabase = createSupabaseClient();

        logInfo('generate-widget', `Generating ${widget_type} for user ${user_id}`);

        let widgetData: Record<string, any> = {};
        let title = '';

        // Mock generation logic based on type
        switch (widget_type) {
            case 'initiative_dashboard':
                title = 'Initiative Overview';
                // Fetch initiatives from DB would go here
                widgetData = {
                    total: 5,
                    active: 3,
                    completed: 2,
                    recent_updates: []
                };
                break;

            case 'revenue_chart':
                title = 'Revenue Trends';
                widgetData = {
                    labels: ['Jan', 'Feb', 'Mar'],
                    datasets: [{ label: 'Revenue', data: [1000, 1500, 1200] }]
                };
                break;

            case 'workflow_builder':
                title = 'Workflow Editor';
                widgetData = {
                    nodes: [],
                    edges: []
                };
                break;

            case 'kanban_board':
                title = 'Tasks';
                widgetData = {
                    columns: [
                        { id: 'todo', title: 'To Do', tasks: [] },
                        { id: 'done', title: 'Done', tasks: [] }
                    ]
                };
                break;

            case 'calendar':
                title = 'Schedule';
                widgetData = {
                    events: []
                };
                break;
        }

        const widget: WidgetDefinition = {
            type: widget_type,
            title,
            data: widgetData,
            dismissible: true,
            expandable: true
        };

        // Optionally store the generated widget or notify user
        // For now we just return it

        logInfo('generate-widget', `Widget ${widget_type} generated successfully`);

        return new Response(JSON.stringify({ success: true, widget }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 200,
        });

    } catch (error) {
        logError('generate-widget', error);
        return handleError(error);
    }
});
