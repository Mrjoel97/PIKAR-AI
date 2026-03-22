
import { createSupabaseClient } from '../_shared/supabase.ts';
import { handleError, logInfo, logError, validateRequest, corsHeaders, requireAuth, assertUuid } from '../_shared/utils.ts';
import { WorkflowExecution, WorkflowStep } from '../_shared/types.ts';

Deno.serve(async (req) => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders });
    }

    try {
        const auth = await requireAuth(req);
        const userAuthToken = req.headers.get('Authorization') || '';
        const { execution_id, step_action = 'start' } = await validateRequest(req, ['execution_id']);
        assertUuid(execution_id, 'execution_id');
        const validActions = new Set(['start', 'advance', 'retry']);
        if (!validActions.has(step_action)) {
            throw new Error('Invalid step_action');
        }
        const supabase = createSupabaseClient();

        logInfo('execute-workflow', `Processing execution ${execution_id} with action ${step_action}`);

        // 1. Fetch Full Context
        const { data: execution, error: fetchError } = await supabase
            .from('workflow_executions')
            .select(`
                *,
                workflow_templates!inner (
                    name,
                    phases,
                    description,
                    on_complete
                )
            `)
            .eq('id', execution_id)
            .single();

        if (fetchError || !execution) {
            throw new Error(`Execution not found: ${fetchError?.message}`);
        }

        const exec = execution as any;
        if (!auth.isServiceRole && exec.user_id !== auth.user?.id) {
            throw new Error('Unauthorized');
        }
        const template = exec.workflow_templates;
        const phases = template.phases as Array<{ name: string, steps: Array<{ name: string, description: string, tool?: string, required_approval?: boolean, action_type?: string }> }>;

        let updates: Partial<WorkflowExecution> = {};

        // 3. Action Handlers
        if (step_action === 'start') {
            if (exec.status !== 'pending') {
                // Idempotency: repeated starts return current execution state.
                return new Response(
                    JSON.stringify({ success: true, execution_id, status: exec.status, message: 'Execution already started' }),
                    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
                );
            }

            // Validate pending, set status 'running'
            updates.status = 'running';
            updates.current_phase_index = 0;
            updates.current_step_index = 0;

            // Create first workflow step only once.
            const firstPhase = phases[0];
            const firstStep = firstPhase?.steps?.[0];

            if (firstStep) {
                const { data: existingFirstStep } = await supabase
                    .from('workflow_steps')
                    .select('*')
                    .eq('execution_id', execution_id)
                    .eq('phase_index', 0)
                    .eq('step_index', 0)
                    .order('created_at', { ascending: false })
                    .limit(1)
                    .maybeSingle();

                let stepData = existingFirstStep;
                if (!stepData) {
                    const { data: insertedFirstStep, error: stepError } = await supabase.from('workflow_steps').insert({
                        execution_id: execution_id,
                        phase_name: firstPhase.name,
                        phase_index: 0,
                        phase_key: firstPhase.name?.toLowerCase().replace(/\s+/g, '_'),
                        step_name: firstStep.name,
                        step_index: 0,
                        status: firstStep.required_approval ? 'waiting_approval' : 'running',
                        input_data: exec.context,
                        started_at: new Date().toISOString()
                    }).select().single();
                    if (stepError) throw stepError;
                    stepData = insertedFirstStep;
                }

                if (firstStep.required_approval) {
                    updates.status = 'waiting_approval';
                    // Optional: Send notification for approval
                } else {
                    // Auto-execute if no approval required (inject user_id for backend request context)
                    const contextWithUser = { ...(exec.context || {}), user_id: exec.user_id, run_source: exec.run_source };
                    await executeStep(supabase, execution_id, stepData.id, contextWithUser, firstStep, exec.user_id);
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
                    phase_index: nextPhaseIndex,
                    phase_key: nextPhase.name?.toLowerCase().replace(/\s+/g, '_'),
                    step_name: nextStep.name,
                    step_index: nextStepIndex,
                    status: nextStep.required_approval ? 'waiting_approval' : 'running',
                    input_data: newInputData, // Propagate context
                    started_at: new Date().toISOString()
                }).select().single();
                if (nextStepError) throw nextStepError;

                if (nextStep.required_approval) {
                    updates.status = 'waiting_approval';
                    // Optional: Send notification for approval
                } else {
                    // Auto-execute (inject user_id for backend request context)
                    const contextWithUser = { ...(newInputData || {}), user_id: exec.user_id, run_source: exec.run_source };
                    await executeStep(supabase, execution_id, nextStepData.id, contextWithUser, nextStep, exec.user_id);
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
                    const contextWithUser = { ...(failedStep.input_data || exec.context || {}), user_id: exec.user_id, run_source: exec.run_source };
                    await executeStep(supabase, execution_id, failedStep.id, contextWithUser, currentStepDef, exec.user_id);
                }
            }
            updates.status = 'running';
        }

        // When execution completes, build outcome summary from steps for user visibility
        if (updates.status === 'completed') {
            const { data: steps } = await supabase
                .from('workflow_steps')
                .select('step_name, phase_name, status, output_data')
                .eq('execution_id', execution_id)
                .order('created_at', { ascending: true });
            const completed = (steps || []).filter((s: any) => s.status === 'completed');
            const toolsUsed = completed
                .map((s: any) => (s.output_data && (s.output_data as any).tool) || (s.output_data && (s.output_data as any).tool_name) || 'step')
                .filter((t: string) => t && t !== 'step');
            const lastOutput = completed.length > 0 ? completed[completed.length - 1].output_data : null;
            const summaryText = (lastOutput && typeof (lastOutput as any).message === 'string')
                ? (lastOutput as any).message
                : (lastOutput && typeof (lastOutput as any).summary === 'string')
                ? (lastOutput as any).summary
                : `${completed.length} step(s) completed.`;

            const artifactCandidates = completed.flatMap((step: any) => {
                const output = (step.output_data || {}) as Record<string, unknown>;
                const meta = (output._execution_meta || {}) as { evidence_refs?: Array<Record<string, unknown>> };
                const evidenceRefs = Array.isArray(meta.evidence_refs) ? meta.evidence_refs : [];
                const explicitArtifacts = [
                    output.report_id ? { type: 'report', value: String(output.report_id) } : null,
                    output.task_id ? { type: 'task', value: String(output.task_id) } : null,
                    output.initiative_id ? { type: 'initiative', value: String(output.initiative_id) } : null,
                    output.ticket_id ? { type: 'ticket', value: String(output.ticket_id) } : null,
                    output.page_url ? { type: 'url', value: String(output.page_url) } : null,
                    output.live_url ? { type: 'url', value: String(output.live_url) } : null,
                ].filter(Boolean) as Array<{ type: string; value: string }>;
                return [...explicitArtifacts, ...evidenceRefs.map((ref) => ({
                    type: String(ref.type || ref.key || 'artifact'),
                    value: String(ref.value || ref.url || ''),
                }))];
            });

            const artifacts = artifactCandidates
                .filter((artifact) => artifact.value)
                .map((artifact) => {
                    const normalizedType = artifact.type.replace(/\s+/g, '_');
                    let href: string | undefined;
                    if (normalizedType === 'initiative') {
                        href = `/dashboard/initiatives/${artifact.value}`;
                    } else if (normalizedType === 'report') {
                        href = '/dashboard/reports';
                    } else if (normalizedType === 'workflow_execution') {
                        href = '/dashboard/workflows/completed';
                    } else if (normalizedType === 'url' && /^https?:\/\//.test(artifact.value)) {
                        href = artifact.value;
                    }
                    return {
                        type: normalizedType,
                        value: artifact.value,
                        href,
                        label: normalizedType === 'url'
                            ? 'Reference link'
                            : `${normalizedType.replace(/_/g, ' ')} created`,
                    };
                })
                .filter((artifact, index, arr) => arr.findIndex((candidate) => candidate.type === artifact.type && candidate.value === artifact.value) === index)
                .slice(0, 6);

            const nextActions = [
                exec.context?.initiative_id ? 'Open the linked initiative and confirm the next owner.' : null,
                artifacts.some((artifact) => artifact.type === 'report') ? 'Review the generated report and share the key takeaway.' : null,
                artifacts.some((artifact) => artifact.type === 'task') ? 'Check the tasks that were created and assign an owner if needed.' : null,
                toolsUsed.length > 0 ? `Review outputs from ${[...new Set(toolsUsed)].slice(0, 2).join(' and ')}.` : null,
            ].filter((value, index, arr): value is string => Boolean(value) && arr.indexOf(value) === index).slice(0, 3);

            updates.outcome_summary = {
                steps_completed: completed.length,
                tools_used: [...new Set(toolsUsed)],
                summary: summaryText,
                artifacts,
                next_actions: nextActions,
            };

            // Auto-save to Reports page for easy navigation and search
            const templateName = (exec.workflow_templates as any)?.name || exec.name;
            const ctx = exec.context || {};
            const reportTitle = (ctx.topic as string) || exec.name || templateName || 'Workflow completed';
            const reportCategory = (exec.workflow_templates as any)?.category || 'Workflow';
            const artifactLines = artifacts.length
                ? `\n\nArtifacts: ${artifacts.map((artifact) => artifact.label + (artifact.value ? ` (${artifact.value})` : '')).join(', ')}.`
                : '';
            const actionLines = nextActions.length
                ? `\n\nNext actions: ${nextActions.join(' ')}`
                : '';
            const contentBody = summaryText
                + (toolsUsed.length ? `\n\nTools used: ${[...new Set(toolsUsed)].join(', ')}.` : '')
                + artifactLines
                + actionLines;
            const { error: reportErr } = await supabase.from('user_reports').insert({
                user_id: exec.user_id,
                title: reportTitle,
                category: reportCategory,
                status: 'Completed',
                summary: summaryText,
                content: contentBody,
                source_type: 'workflow',
                source_id: execution_id,
                metadata: { template_name: templateName, initiative_id: ctx.initiative_id || null },
            });
            if (reportErr) logError('execute-workflow', `Failed to save report: ${reportErr.message}`);
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

        // Sync linked initiative state from workflow progression.
        const initiativeId = exec?.context?.initiative_id;
        if (initiativeId) {
            const phaseOrder = ['ideation', 'validation', 'prototype', 'build', 'scale'];
            const phaseIndex = updates.current_phase_index ?? exec.current_phase_index ?? 0;
            const stepIndex = updates.current_step_index ?? exec.current_step_index ?? 0;
            const totalSteps = (phases || []).reduce((sum, phase) => sum + (phase.steps?.length || 0), 0);
            const completedBeforePhase = (phases || [])
                .slice(0, phaseIndex)
                .reduce((sum, phase) => sum + (phase.steps?.length || 0), 0);
            const progress = totalSteps > 0 ? Math.min(100, Math.round(((completedBeforePhase + stepIndex) / totalSteps) * 100)) : 0;
            const phaseName = (phases?.[phaseIndex]?.name || '').toLowerCase();
            const normalizedPhase = phaseOrder.includes(phaseName) ? phaseName : phaseOrder[Math.min(phaseIndex, phaseOrder.length - 1)];
            const workflowStatus = updates.status || exec.status;
            const initiativeStatus =
                workflowStatus === 'completed' ? 'completed' :
                workflowStatus === 'failed' ? 'blocked' :
                'in_progress';

            const metadataPatch = {
                workflow_template_name: (exec.workflow_templates as any)?.name || null,
                workflow_last_phase_index: phaseIndex,
                workflow_last_step_index: stepIndex,
                workflow_last_status: workflowStatus,
                workflow_last_step_synced_at: new Date().toISOString(),
            };

            const { data: currentInitiative } = await supabase
                .from('initiatives')
                .select('metadata, phase_progress')
                .eq('id', initiativeId)
                .limit(1)
                .maybeSingle();

            const mergedMetadata = {
                ...((currentInitiative?.metadata as Record<string, unknown>) || {}),
                ...metadataPatch,
            };

            const existingPhaseProgress = (currentInitiative?.phase_progress as Record<string, number> | null) || {};
            const nextPhaseProgress: Record<string, number> = {
                ideation: existingPhaseProgress.ideation ?? 0,
                validation: existingPhaseProgress.validation ?? 0,
                prototype: existingPhaseProgress.prototype ?? 0,
                build: existingPhaseProgress.build ?? 0,
                scale: existingPhaseProgress.scale ?? 0,
            };
            phaseOrder.forEach((p, idx) => {
                if (idx < phaseIndex) nextPhaseProgress[p] = 100;
            });

            const { error: initiativeSyncError } = await supabase
                .from('initiatives')
                .update({
                    phase: normalizedPhase,
                    progress,
                    status: initiativeStatus,
                    phase_progress: nextPhaseProgress,
                    metadata: mergedMetadata,
                    workflow_execution_id: execution_id,
                })
                .eq('id', initiativeId);
            if (initiativeSyncError) {
                logError('execute-workflow', `Failed to sync initiative ${initiativeId}: ${initiativeSyncError.message}`);
            }
        }

        // Notify via 'notifications' if complete/failed (Simple mock)
        if (updates.status === 'completed') {
            // await supabase.from('notifications').insert({...})
        }

        // Workflow chaining: trigger a follow-up workflow on completion
        if (updates.status === 'completed') {
            await handleWorkflowChaining(supabase, exec, execution_id, userAuthToken);
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

function parseBooleanEnv(name: string, defaultValue: boolean): boolean {
    const raw = Deno.env.get(name);
    if (raw == null || raw.trim() === '') {
        return defaultValue;
    }
    return raw.trim().toLowerCase() === 'true';
}

function isProductionExecutionEnvironment(): boolean {
    const env = (Deno.env.get('ENVIRONMENT') || Deno.env.get('ENV') || 'development').trim().toLowerCase();
    return env === 'production' || env === 'prod';
}

function getValidatedBackendApiUrl(required: boolean): string | null {
    const raw = (Deno.env.get('BACKEND_API_URL') || '').trim();
    if (!raw) {
        if (required) {
            throw new Error('BACKEND_API_URL is required when strict workflow execution is enabled.');
        }
        return null;
    }

    let parsed: URL;
    try {
        parsed = new URL(raw);
    } catch {
        throw new Error(`BACKEND_API_URL must be a valid absolute URL. Received: "${raw}"`);
    }

    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        throw new Error(`BACKEND_API_URL must use http or https. Received: "${parsed.protocol}"`);
    }

    return raw.replace(/\/+$/, '');
}

// Helper to execute a single step
// Uses the 'tool' field from template definitions to call the Python backend worker
async function executeStep(supabase: any, execution_id: string, step_id: string, context: any, stepDef: any, _userId?: string) {
    try {
        const toolName = stepDef.tool || stepDef.action_type || 'unknown';
        logInfo('execute-workflow', `Executing step "${stepDef.name}" with tool "${toolName}"`);

        let outputData: Record<string, unknown> = {};
        const allowFallbackSimulation = shouldAllowFallbackSimulation();
        const strictToolResolution = parseBooleanEnv('WORKFLOW_STRICT_TOOL_RESOLUTION', false);
        const isUserVisibleRun = ['user_ui', 'agent_ui'].includes(String(context?.run_source || '').trim().toLowerCase());
        const strictExecutionMode = isUserVisibleRun || strictToolResolution || !allowFallbackSimulation;
        const backendUrl = getValidatedBackendApiUrl(strictExecutionMode);
        const serviceSecret = (Deno.env.get('WORKFLOW_SERVICE_SECRET') || '').trim();

        if (toolName === 'unknown' && strictExecutionMode) {
            throw new Error(`Unknown workflow tool for step "${stepDef.name}" with strict execution enabled.`);
        }
        if (!serviceSecret && strictExecutionMode) {
            throw new Error("WORKFLOW_SERVICE_SECRET is required for authenticated backend calls");
        }

        // Try calling the Python backend worker API to execute the tool
        if (backendUrl && toolName !== 'unknown') {
            try {
                const headers: Record<string, string> = {
                    'Content-Type': 'application/json',
                };
                if (serviceSecret) {
                    headers['X-Service-Secret'] = serviceSecret;
                }
                const response = await fetch(`${backendUrl}/workflows/execute-step`, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({
                        execution_id,
                        step_id,
                        tool_name: toolName,
                        context,
                        step_name: stepDef.name,
                        step_description: stepDef.description || '',
                        step_definition: stepDef,
                        run_source: context?.run_source || 'user_ui',
                    }),
                });

                const result = await response.json().catch(() => ({}));

                if (response.ok && result.success !== false) {
                    outputData = result.data ?? result;
                    logInfo('execute-workflow', `Tool "${toolName}" executed via backend worker`);
                } else if (response.ok && result.success === false) {
                    // Backend ran but reported failure (e.g. tool TypeError) — mark step failed
                    const errMsg = result.error_message ?? result.message ?? (typeof result.data === 'string' ? result.data : 'Step failed');
                    logError('execute-workflow', `Backend reported step failure: ${errMsg}`);
                    await supabase.from('workflow_steps').update({
                        status: 'failed',
                        error_message: errMsg,
                        output_data: result.data ?? {}
                    }).eq('id', step_id);
                    return;
                } else {
                    if (response.status === 401) {
                        logError('execute-workflow', 'Backend rejected service authentication - check WORKFLOW_SERVICE_SECRET configuration');
                    }
                    if (strictExecutionMode) {
                        throw new Error(`Backend worker returned ${response.status}. Strict execution mode blocks fallback simulation.`);
                    }
                    // Backend HTTP error, fall back to edge execution when allowed.
                    logInfo('execute-workflow', `Backend worker returned ${response.status}, using edge execution`);
                    outputData = await executeStepLocally(
                        toolName,
                        context,
                        stepDef,
                        strictToolResolution,
                        allowFallbackSimulation
                    );
                }
            } catch (fetchErr: any) {
                if (strictExecutionMode) {
                    throw new Error(`Backend worker unreachable: ${fetchErr.message}. Strict execution mode blocks fallback simulation.`);
                }
                // Backend unreachable, fall through to local execution when allowed.
                logInfo('execute-workflow', `Backend worker unreachable: ${fetchErr.message}, using edge execution`);
                outputData = await executeStepLocally(
                    toolName,
                    context,
                    stepDef,
                    strictToolResolution,
                    allowFallbackSimulation
                );
            }
        } else {
            if (!backendUrl && strictExecutionMode) {
                throw new Error('BACKEND_API_URL is required and must be valid when strict workflow execution is enabled.');
            }
            if (!allowFallbackSimulation) {
                throw new Error('Edge fallback execution is disabled by WORKFLOW_ALLOW_FALLBACK_SIMULATION=false.');
            }
            // No backend URL configured, execute locally when allowed.
            outputData = await executeStepLocally(
                toolName,
                context,
                stepDef,
                strictToolResolution,
                allowFallbackSimulation
            );
        }

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

// Fallback local execution for when the backend worker is unavailable.
// When BACKEND_API_URL is set, the backend /workflows/execute-step endpoint is called first
// and uses the Python tool registry for real execution. This fallback runs only if the
// backend is unreachable or BACKEND_API_URL is not set.
async function executeStepLocally(
    toolName: string,
    context: any,
    stepDef: any,
    strictToolResolution = false,
    allowFallbackSimulation = true
): Promise<Record<string, unknown>> {
    if (isProductionExecutionEnvironment()) {
        throw new Error('executeStepLocally is disabled in production. Configure BACKEND_API_URL and WORKFLOW_SERVICE_SECRET for real execution.');
    }
    if (strictToolResolution || !allowFallbackSimulation) {
        throw new Error('executeStepLocally is disabled when strict tool resolution is enabled or fallback simulation is disabled.');
    }
    logInfo('execute-workflow', `Executing "${toolName}" locally (edge fallback)`);

    const stepMsg = stepDef?.name || stepDef?.description || 'step';
    const genericTool = [
        'mcp_web_search',
        'mcp_web_scrape',
        'add_business_knowledge',
        'search_business_knowledge',
        'create_initiative',
        'get_initiative',
        'update_initiative',
        'update_initiative_status',
        'list_initiatives',
        'start_initiative_from_idea',
        'advance_initiative_phase',
        'list_initiative_templates',
        'create_initiative_from_template',
        'create_task',
        'get_task',
        'update_task',
        'list_tasks',
        'create_campaign',
        'get_campaign',
        'update_campaign',
        'list_campaigns',
        'record_campaign_metrics',
        'create_ticket',
        'get_ticket',
        'update_ticket',
        'list_tickets',
        'create_audit',
        'get_audit',
        'update_audit',
        'list_audits',
        'create_risk',
        'get_risk',
        'update_risk',
        'list_risks',
        'create_job',
        'get_job',
        'update_job',
        'list_jobs',
        'track_event',
        'query_events',
        'create_report',
        'list_reports',
        'get_revenue_stats',
        'analyze_financial_health',
        'save_content',
        'get_content',
        'update_content',
        'list_content',
        'deep_research',
        'quick_research',
        'market_research',
        'competitor_research',
        'generate_image',
        'generate_short_video',
        'generate_content',
        'generate_ideas',
        'publish_content',
        'generate_social_content',
        'analyze_process_bottlenecks',
        'get_seo_checklist',
        'get_sop_template',
        'analyze_results',
        'filter_users',
        'record_metrics',
        'query_metrics',
        'generate_report',
        'assign_task',
        'update_crm',
        'send_email_campaign',
    ].includes(toolName);

    if (genericTool) {
        return {
            executed: true,
            tool: toolName,
            message: `Step "${stepMsg}" completed (edge fallback). Configure BACKEND_API_URL for full execution.`,
            timestamp: new Date().toISOString(),
        };
    }

    if (strictToolResolution) {
        throw new Error(`Unknown workflow tool "${toolName}" with strict tool resolution enabled.`);
    }

    return {
        executed: true,
        tool: toolName,
        message: `Step "${stepMsg}" auto-completed`,
        description: stepDef?.description,
        timestamp: new Date().toISOString(),
    };
}

/**
 * Handle workflow chaining: when a template defines `on_complete.trigger_workflow`,
 * automatically start the chained workflow with the completed execution's context
 * and output data merged as input.
 */
async function handleWorkflowChaining(supabase: any, exec: any, completedExecutionId: string, userAuthToken: string) {
    const template = exec.workflow_templates;
    const onComplete = template?.on_complete;

    if (!onComplete?.trigger_workflow) return;

    const chainConfig = onComplete.trigger_workflow;
    const targetTemplateId: string | undefined = chainConfig.template_id;
    const targetTemplateName: string | undefined = chainConfig.template_name;

    if (!targetTemplateId && !targetTemplateName) {
        logError('execute-workflow', 'on_complete.trigger_workflow defined but missing template_id or template_name');
        return;
    }

    // Prevent infinite chain loops — limit chain depth
    const maxChainDepth = parseInt(Deno.env.get('WORKFLOW_MAX_CHAIN_DEPTH') || '5', 10);
    const currentDepth = (exec.context?._chain_depth as number) || 0;
    if (currentDepth >= maxChainDepth) {
        logError('execute-workflow', `Chain depth ${currentDepth} reached max ${maxChainDepth}. Stopping chain.`);
        return;
    }

    try {
        // Resolve the target template
        let templateQuery = supabase.from('workflow_templates').select('*');
        if (targetTemplateId) {
            templateQuery = templateQuery.eq('id', targetTemplateId);
        } else {
            templateQuery = templateQuery.eq('name', targetTemplateName);
        }
        const { data: targetTemplate, error: templateError } = await templateQuery.limit(1).maybeSingle();

        if (templateError || !targetTemplate) {
            logError('execute-workflow', `Chained template not found: ${targetTemplateId || targetTemplateName}`);
            return;
        }

        // Build chained context: merge original context + completed output + chain metadata
        const lastStepQuery = await supabase
            .from('workflow_steps')
            .select('output_data')
            .eq('execution_id', completedExecutionId)
            .eq('status', 'completed')
            .order('completed_at', { ascending: false })
            .limit(1)
            .maybeSingle();
        const lastStepOutput = lastStepQuery.data?.output_data || {};

        const chainedContext = {
            ...(exec.context || {}),
            ...(chainConfig.context_overrides || {}),
            _parent_execution_id: completedExecutionId,
            _parent_template_name: template?.name || null,
            _chain_depth: currentDepth + 1,
            _parent_output: lastStepOutput,
        };

        // Create the chained execution
        const { data: chainedExec, error: chainError } = await supabase
            .from('workflow_executions')
            .insert({
                template_id: targetTemplate.id,
                user_id: exec.user_id,
                status: 'pending',
                context: chainedContext,
                run_source: 'workflow_chain',
                name: chainConfig.execution_name || `Chain: ${targetTemplate.name}`,
            })
            .select()
            .single();

        if (chainError || !chainedExec) {
            logError('execute-workflow', `Failed to create chained execution: ${chainError?.message}`);
            return;
        }

        logInfo('execute-workflow', `Chained workflow started: ${chainedExec.id} (template: ${targetTemplate.name}, depth: ${currentDepth + 1})`);

        // Trigger the chained workflow via the same edge function pattern
        const backendUrl = getValidatedBackendApiUrl(false);
        const serviceSecret = (Deno.env.get('WORKFLOW_SERVICE_SECRET') || '').trim();

        if (backendUrl && serviceSecret) {
            // Trigger via backend for proper orchestration
            try {
                await fetch(`${backendUrl}/workflows/start-execution`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Service-Secret': serviceSecret,
                    },
                    body: JSON.stringify({ execution_id: chainedExec.id }),
                });
            } catch (triggerErr: any) {
                logError('execute-workflow', `Failed to trigger chained execution via backend: ${triggerErr.message}`);
                // Fallback: invoke self recursively with start action
                const selfUrl = `${Deno.env.get('SUPABASE_URL')}/functions/v1/execute-workflow`;
                const selfHeaders: Record<string, string> = {
                    'Content-Type': 'application/json',
                    'Authorization': userAuthToken,
                };
                await fetch(selfUrl, {
                    method: 'POST',
                    headers: selfHeaders,
                    body: JSON.stringify({ execution_id: chainedExec.id, step_action: 'start' }),
                }).catch((e: any) => logError('execute-workflow', `Self-invoke for chain also failed: ${e.message}`));
            }
        } else {
            // Direct self-invocation when no backend URL
            const selfUrl = `${Deno.env.get('SUPABASE_URL')}/functions/v1/execute-workflow`;
            const selfHeaders: Record<string, string> = {
                'Content-Type': 'application/json',
                'Authorization': userAuthToken,
            };
            await fetch(selfUrl, {
                method: 'POST',
                headers: selfHeaders,
                body: JSON.stringify({ execution_id: chainedExec.id, step_action: 'start' }),
            }).catch((e: any) => logError('execute-workflow', `Self-invoke for chain failed: ${e.message}`));
        }
    } catch (err: any) {
        logError('execute-workflow', `Workflow chaining failed: ${err.message}`);
    }
}

function shouldAllowFallbackSimulation(): boolean {
    if (isProductionExecutionEnvironment()) {
        return false;
    }
    const explicit = Deno.env.get('WORKFLOW_ALLOW_FALLBACK_SIMULATION');
    if (explicit != null && explicit !== '') {
        return explicit.toLowerCase() === 'true';
    }
    // Safe default: disabled unless explicitly enabled.
    return false;
}






