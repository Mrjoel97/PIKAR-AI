
import { createSupabaseClient } from '../_shared/supabase.ts';
import { handleError, logInfo, logError, validateRequest, corsHeaders } from '../_shared/utils.ts';
import { WorkflowExecution, WorkflowStep } from '../_shared/types.ts';

Deno.serve(async (req) => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders });
    }

    try {
        const { execution_id, step_action = 'start' } = await validateRequest(req, ['execution_id']);
        const supabase = createSupabaseClient();

        logInfo('execute-workflow', `Processing execution ${execution_id} with action ${step_action}`);

        // 1. Fetch Full Context
        const { data: execution, error: fetchError } = await supabase
            .from('workflow_executions')
            .select(`
                *,
                workflow_templates!inner (
                    phases,
                    description
                )
            `)
            .eq('id', execution_id)
            .single();

        if (fetchError || !execution) {
            throw new Error(`Execution not found: ${fetchError?.message}`);
        }

        const exec = execution as any;
        const template = exec.workflow_templates;
        const phases = template.phases as Array<{ name: string, steps: Array<{ name: string, description: string, required_approval?: boolean, action_type?: string }> }>;

        let updates: Partial<WorkflowExecution> = {};

        // 3. Action Handlers
        if (step_action === 'start') {
            if (exec.status !== 'pending') {
                // Idempotency: if already running, return ok
                return new Response(JSON.stringify({ status: exec.status, message: 'Already started' }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
            }

            // Validate pending, set status 'running'
            updates.status = 'running';
            updates.current_phase_index = 0;
            updates.current_step_index = 0;

            // Create first workflow_steps record
            const firstPhase = phases[0];
            const firstStep = firstPhase?.steps?.[0];

            if (firstStep) {
                const { data: stepData, error: stepError } = await supabase.from('workflow_steps').insert({
                    execution_id: execution_id,
                    phase_name: firstPhase.name,
                    step_name: firstStep.name,
                    status: firstStep.required_approval ? 'waiting_approval' : 'running',
                    input_data: exec.context,
                    started_at: new Date().toISOString()
                }).select().single();
                if (stepError) throw stepError;

                if (firstStep.required_approval) {
                    updates.status = 'waiting_approval';
                    // Optional: Send notification for approval
                } else {
                    // Auto-execute if no approval required
                    await executeStep(supabase, execution_id, stepData.id, exec.context, firstStep);
                }
            } else {
                // Empty workflow? Mark complete immediately
                updates.status = 'completed';
                updates.completed_at = new Date().toISOString();
            }

        } else if (step_action === 'advance') {
            // Find current unfinished step
            const { data: currentStep, error: currentStepError } = await supabase
                .from('workflow_steps')
                .select('*')
                .eq('execution_id', execution_id)
                .or('status.eq.running,status.eq.waiting_approval')
                .order('created_at', { ascending: false })
                .limit(1)
                .single();

            if (currentStep) {
                // Mark completed
                await supabase.from('workflow_steps').update({
                    status: 'completed',
                    completed_at: new Date().toISOString()
                }).eq('id', currentStep.id);
            }

            // Increment indices
            let nextPhaseIndex = exec.current_phase_index;
            let nextStepIndex = exec.current_step_index + 1;

            let currentPhase = phases[nextPhaseIndex];

            // Check if phase wrap
            if (!currentPhase || nextStepIndex >= currentPhase.steps.length) {
                nextPhaseIndex++;
                nextStepIndex = 0;
            }

            // Check if end
            if (nextPhaseIndex < phases.length) {
                const nextPhase = phases[nextPhaseIndex];
                const nextStep = nextPhase.steps[nextStepIndex];

                updates.current_phase_index = nextPhaseIndex;
                updates.current_step_index = nextStepIndex;
                updates.status = 'running'; // Default back to running if it was waiting

                // Use output from previous step + initial context
                const previousOutput = currentStep?.output_data || {};
                const newInputData = { ...exec.context, ...previousOutput };

                // Create next step record
                const { data: nextStepData, error: nextStepError } = await supabase.from('workflow_steps').insert({
                    execution_id: execution_id,
                    phase_name: nextPhase.name,
                    step_name: nextStep.name,
                    status: nextStep.required_approval ? 'waiting_approval' : 'running',
                    input_data: newInputData, // Propagate context
                    started_at: new Date().toISOString()
                }).select().single();
                if (nextStepError) throw nextStepError;

                if (nextStep.required_approval) {
                    updates.status = 'waiting_approval';
                    // Optional: Send notification for approval
                } else {
                    // Auto-execute
                    await executeStep(supabase, execution_id, nextStepData.id, newInputData, nextStep);
                }

            } else {
                // End of workflow
                updates.status = 'completed';
                updates.completed_at = new Date().toISOString();
            }

        } else if (step_action === 'retry') {
            // Find last failed step
            const { data: failedStep } = await supabase
                .from('workflow_steps')
                .select('*')
                .eq('execution_id', execution_id)
                .eq('status', 'failed')
                .order('created_at', { ascending: false })
                .limit(1)
                .single();

            if (failedStep) {
                // Reset status='running', clear error
                await supabase.from('workflow_steps').update({
                    status: 'running',
                    error_message: null,
                    output_data: null,
                    started_at: new Date().toISOString() // Restart timer
                }).eq('id', failedStep.id);

                // Find step definition to re-execute
                const currentPhase = phases[exec.current_phase_index];
                const currentStepDef = currentPhase?.steps?.[exec.current_step_index];

                if (currentStepDef) {
                    await executeStep(supabase, execution_id, failedStep.id, failedStep.input_data || exec.context, currentStepDef);
                }
            }
            updates.status = 'running';
        }

        // 6. Updates
        if (Object.keys(updates).length > 0) {
            updates.updated_at = new Date().toISOString();
            const { error: updateError } = await supabase
                .from('workflow_executions')
                .update(updates)
                .eq('id', execution_id);

            if (updateError) throw updateError;
        }

        // Notify via 'notifications' if complete/failed (Simple mock)
        if (updates.status === 'completed') {
            // await supabase.from('notifications').insert({...})
        }

        logInfo('execute-workflow', `Workflow ${execution_id} step_action=${step_action} processed. New Status: ${updates.status || exec.status}`);

        return new Response(JSON.stringify({ success: true, execution_id, status: updates.status || exec.status }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 200,
        });

    } catch (error) {
        logError('execute-workflow', error);
        return handleError(error);
    }
});

// Helper to execute a single step
async function executeStep(supabase: any, execution_id: string, step_id: string, context: any, stepDef: any) {
    try {
        logInfo('execute-workflow', `Executing step ${stepDef.name} (${stepDef.action_type})`);

        let outputData = {};

        switch (stepDef.action_type) {
            case 'send_email':
                // Mock execution for now (or real fetch if keys present)
                // const res = await fetch('https://api.resend.com/emails', ...);
                logInfo('execute-workflow', `[Mock] Sending email to ${context.email || 'user'}`);
                outputData = { sent: true, timestamp: new Date().toISOString() };
                break;

            case 'ai_analysis':
                // Mock AI analysis
                logInfo('execute-workflow', `[Mock] AI analyzing context...`);
                outputData = { analysis: "Everything looks good", score: 0.95 };
                break;

            case 'update_database':
                // Mock DB update
                logInfo('execute-workflow', `[Mock] Updating database records...`);
                outputData = { success: true, updated_rows: 1 };
                break;

            default:
                logInfo('execute-workflow', `Unknown action type ${stepDef.action_type}, executing generic step`);
                outputData = { executed: true };
        }

        // Simulate processing time
        // await new Promise(resolve => setTimeout(resolve, 1000));

        // Update step as completed
        await supabase.from('workflow_steps').update({
            status: 'completed',
            output_data: outputData,
            completed_at: new Date().toISOString()
        }).eq('id', step_id);

    } catch (err: any) {
        logError('execute-workflow', `Step execution failed: ${err.message}`);
        await supabase.from('workflow_steps').update({
            status: 'failed',
            error_message: err.message
        }).eq('id', step_id);
    }
}
