
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WorkflowStep } from '@/api/entities';
import { Workflow } from '@/api/entities';
import { InvokeLLM } from '@/api/integrations';
import { FileText, Loader2, Download, Sparkles, CheckCircle, ArrowRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { toast } from 'sonner';

export default function WorkflowResultAggregator({ workflowId, workflow, onAggregationComplete }) {
    const [steps, setSteps] = useState([]);
    const [aggregatedResult, setAggregatedResult] = useState('');
    const [isAggregating, setIsAggregating] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    const loadWorkflowSteps = useCallback(async () => {
        setIsLoading(true);
        try {
            const fetchedSteps = await WorkflowStep.filter({ workflow_id: workflowId }, 'step_order');
            setSteps(fetchedSteps || []);
        } catch (error) {
            console.error("Error loading workflow steps:", error);
            toast.error("Failed to load workflow steps");
        } finally {
            setIsLoading(false);
        }
    }, [workflowId]);

    useEffect(() => {
        loadWorkflowSteps();
    }, [loadWorkflowSteps]);

    const generateAggregatedReport = async () => {
        if (!steps || steps.length === 0) {
            toast.error("No completed steps to aggregate");
            return;
        }

        const completedSteps = steps.filter(step => 
            step.step_status === 'completed' && 
            step.step_output && 
            step.step_output.result
        );

        if (completedSteps.length === 0) {
            toast.error("No completed steps with results found");
            return;
        }

        setIsAggregating(true);
        try {
            const aggregationPrompt = `You are the PIKAR AI Workflow Aggregation System. You have received outputs from multiple specialized AI agents working on the "${workflow.workflow_name}" workflow. Your task is to create a comprehensive, executive-ready report that synthesizes all agent outputs into a cohesive strategic document.

**WORKFLOW OVERVIEW:**
- **Name:** ${workflow.workflow_name}
- **Description:** ${workflow.workflow_description}
- **Category:** ${workflow.workflow_category}
- **Total Steps Completed:** ${completedSteps.length}

**AGENT OUTPUTS TO SYNTHESIZE:**

${completedSteps.map((step, index) => `
**${index + 1}. ${step.agent_name} Agent Output:**
---
${step.step_output.result}
---
`).join('\n')}

**SYNTHESIS REQUIREMENTS:**

1. **Executive Summary** (3-4 paragraphs)
   - Provide a C-suite level overview of key findings across all agents
   - Highlight the most critical insights and strategic implications
   - Quantify business impact where possible

2. **Cross-Agent Insights Analysis**
   - Identify patterns and correlations between different agent analyses
   - Highlight where agent findings reinforce or contradict each other
   - Synthesize unique insights that emerge from the combination of analyses

3. **Strategic Recommendations**
   - Provide 5-7 prioritized strategic recommendations based on all agent inputs
   - Each recommendation should reference supporting evidence from multiple agents
   - Include implementation priorities and expected business impact

4. **Risk Assessment & Mitigation**
   - Consolidate risk factors identified across all agents
   - Provide integrated risk mitigation strategies
   - Assess overall risk profile for the initiative

5. **Implementation Roadmap**
   - Create a phased implementation plan incorporating all agent recommendations
   - Define clear milestones and success metrics
   - Identify resource requirements and dependencies

6. **Success Metrics & KPIs**
   - Define measurable success criteria based on all agent analyses
   - Create a comprehensive KPI dashboard framework
   - Establish baseline metrics and target improvements

**OUTPUT FORMAT:**
Provide a comprehensive, well-structured report in Markdown format that executives can use for strategic decision-making. The report should be professional, actionable, and clearly demonstrate the value of multi-agent collaboration.

Generate the synthesized strategic report now.`;

            const result = await InvokeLLM({
                prompt: aggregationPrompt
            });

            setAggregatedResult(result);

            // Update the workflow with the aggregated result
            await Workflow.update(workflowId, {
                workflow_output: { aggregated_report: result },
                workflow_status: 'completed'
            });

            toast.success("Workflow results successfully aggregated!");
            onAggregationComplete?.(result);

        } catch (error) {
            console.error("Error aggregating results:", error);
            toast.error("Failed to aggregate workflow results");
        } finally {
            setIsAggregating(false);
        }
    };

    const downloadReport = () => {
        if (!aggregatedResult) return;

        const blob = new Blob([aggregatedResult], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${workflow.workflow_name.replace(/\s+/g, '_')}_Aggregated_Report.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success("Report downloaded successfully!");
    };

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin" />
                </CardContent>
            </Card>
        );
    }

    const completedSteps = steps.filter(step => step.step_status === 'completed');
    const hasResults = completedSteps.some(step => step.step_output && step.step_output.result);

    return (
        <div className="space-y-6">
            {/* Step Status Overview */}
            <Card>
                <CardHeader>
                    <CardTitle>Workflow Results Overview</CardTitle>
                    <CardDescription>
                        Review individual agent outputs before generating the final aggregated report
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {steps.map((step, index) => (
                            <div key={step.id} className="flex items-center gap-3 p-3 border rounded-lg">
                                <div className="flex-shrink-0">
                                    {step.step_status === 'completed' ? (
                                        <CheckCircle className="w-5 h-5 text-green-500" />
                                    ) : (
                                        <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-sm truncate">{step.agent_name}</p>
                                    <Badge className="text-xs" variant={
                                        step.step_status === 'completed' ? 'default' : 
                                        step.step_status === 'running' ? 'secondary' : 'outline'
                                    }>
                                        {step.step_status}
                                    </Badge>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Aggregation Controls */}
            {hasResults && (
                <Card>
                    <CardHeader>
                        <CardTitle>Generate Final Report</CardTitle>
                        <CardDescription>
                            Combine all agent outputs into a comprehensive strategic report
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-3">
                            <Button 
                                onClick={generateAggregatedReport} 
                                disabled={isAggregating}
                                className="bg-blue-600 hover:bg-blue-700"
                            >
                                {isAggregating ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Sparkles className="w-4 h-4 mr-2" />
                                )}
                                {isAggregating ? 'Aggregating Results...' : 'Generate Aggregated Report'}
                            </Button>

                            {aggregatedResult && (
                                <Button 
                                    onClick={downloadReport} 
                                    variant="outline"
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    Download Report
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Aggregated Result Display */}
            {aggregatedResult && (
                <Card>
                    <CardHeader>
                        <CardTitle>Aggregated Strategic Report</CardTitle>
                        <CardDescription>
                            Comprehensive analysis combining insights from all workflow agents
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="prose dark:prose-invert max-w-none">
                            <ReactMarkdown>{aggregatedResult}</ReactMarkdown>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Individual Step Results */}
            {completedSteps.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Individual Agent Results</CardTitle>
                        <CardDescription>
                            Detailed outputs from each agent in the workflow
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {completedSteps.map((step, index) => (
                            <div key={step.id} className="border rounded-lg p-4">
                                <div className="flex items-center gap-2 mb-3">
                                    <Badge variant="secondary">{step.agent_name} Agent</Badge>
                                    <Badge variant="outline">Step {step.step_order}</Badge>
                                </div>
                                {step.step_output?.result ? (
                                    <div className="prose dark:prose-invert max-w-none text-sm">
                                        <ReactMarkdown>
                                            {step.step_output.result.length > 500 
                                                ? step.step_output.result.substring(0, 500) + "..." 
                                                : step.step_output.result}
                                        </ReactMarkdown>
                                    </div>
                                ) : (
                                    <p className="text-gray-500 text-sm">No result available</p>
                                )}
                            </div>
                        ))}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
