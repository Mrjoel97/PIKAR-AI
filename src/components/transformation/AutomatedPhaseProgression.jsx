
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { BusinessInitiative, InitiativeDeliverable } from '@/api/entities';
import { InvokeLLM } from '@/api/integrations';
import { CheckCircle, Clock, ArrowRight, Zap, Target, AlertCircle, Play, Pause } from 'lucide-react';
import { toast } from 'sonner';

const PHASE_REQUIREMENTS = {
  "Discovery & Assessment": {
    deliverables: [
      "Initiative Charter Document", 
      "Stakeholder Analysis", 
      "Current State Assessment",
      "Gap Analysis Matrix",
      "Feasibility Study Results"
    ],
    criteria: [
      { name: "Stakeholder alignment", target: 85, current: 0 },
      { name: "Initiative clarity", target: 90, current: 0 },
      { name: "Resource availability", target: 100, current: 0 },
      { name: "Risk assessment completion", target: 100, current: 0 }
    ],
    next_phase: "Planning & Design"
  },
  "Planning & Design": {
    deliverables: [
      "Strategic Plan Document", 
      "Target State Architecture", 
      "Implementation Roadmap",
      "Resource Allocation Plan",
      "Risk Management Framework"
    ],
    criteria: [
      { name: "Plan completeness", target: 95, current: 0 },
      { name: "Design validation", target: 90, current: 0 },
      { name: "Resource commitment", target: 100, current: 0 },
      { name: "Timeline feasibility", target: 85, current: 0 }
    ],
    next_phase: "Foundation & Infrastructure"
  },
  "Foundation & Infrastructure": {
    deliverables: [
      "Core Infrastructure Platform", 
      "Team Structure", 
      "Governance Framework",
      "Process Library",
      "Training Program"
    ],
    criteria: [
      { name: "Infrastructure availability", target: 99, current: 0 },
      { name: "System implementation", target: 100, current: 0 },
      { name: "Team readiness", target: 85, current: 0 },
      { name: "Training completion", target: 100, current: 0 }
    ],
    next_phase: "Execution & Optimization"
  },
  "Execution & Optimization": {
    deliverables: [
      "Project Execution Results", 
      "Performance Metrics Dashboard", 
      "Optimization Reports",
      "Value Delivery Evidence",
      "Stakeholder Communication Records"
    ],
    criteria: [
      { name: "Project delivery rate", target: 95, current: 0 },
      { name: "Performance targets", target: 90, current: 0 },
      { name: "Process efficiency gains", target: 20, current: 0 },
      { name: "Stakeholder satisfaction", target: 85, current: 0 }
    ],
    next_phase: "Scale & Expansion"
  },
  "Scale & Expansion": {
    deliverables: [
      "Scaling Strategy Document", 
      "Replication Playbooks", 
      "Change Management Results",
      "Expansion Implementation Plans",
      "Organizational Impact Reports"
    ],
    criteria: [
      { name: "Scaling success rate", target: 80, current: 0 },
      { name: "Replication effectiveness", target: 85, current: 0 },
      { name: "Change adoption rate", target: 75, current: 0 },
      { name: "Knowledge transfer completion", target: 100, current: 0 }
    ],
    next_phase: "Sustainability"
  },
  "Sustainability": {
    deliverables: [
      "Sustainability Framework", 
      "Performance Optimization Results", 
      "Future State Vision",
      "Continuous Evolution Plan",
      "Final Success Metrics Report"
    ],
    criteria: [
      { name: "Optimal performance achievement", target: 95, current: 0 },
      { name: "Sustainability score", target: 90, current: 0 },
      { name: "Culture embedding index", target: 85, current: 0 },
      { name: "Future readiness score", target: 80, current: 0 }
    ],
    next_phase: "Complete"
  }
};

class PhaseProgressionEngine {
    constructor(initiativeId) {
        this.initiativeId = initiativeId;
        this.automationEnabled = true;
        this.validationRules = new Map();
        this.progressionHistory = [];
    }

    async evaluatePhaseCompletion(currentPhase, deliverables) {
        const requirements = PHASE_REQUIREMENTS[currentPhase];
        if (!requirements) return { canProgress: false, score: 0, gaps: [] };

        // Check deliverable completion
        const completedDeliverables = deliverables.filter(d => d.status === 'Completed').length;
        const totalDeliverables = requirements.deliverables.length;
        const deliverableScore = (completedDeliverables / totalDeliverables) * 100;

        // Evaluate criteria (simulated - in real implementation would use actual metrics)
        const criteriaScores = requirements.criteria.map(criterion => {
            // Simulate current progress based on deliverable completion
            const simulatedCurrent = Math.min(criterion.target, deliverableScore * (criterion.target / 100));
            return {
                ...criterion,
                current: simulatedCurrent,
                met: simulatedCurrent >= criterion.target
            };
        });

        const overallScore = criteriaScores.reduce((sum, c) => sum + c.current, 0) / criteriaScores.length;
        const canProgress = overallScore >= 80 && deliverableScore >= 80;

        const gaps = criteriaScores.filter(c => !c.met).map(c => ({
            criterion: c.name,
            current: c.current,
            target: c.target,
            gap: c.target - c.current
        }));

        return {
            canProgress,
            score: overallScore,
            deliverableScore,
            criteriaScores,
            gaps,
            nextPhase: requirements.next_phase
        };
    }

    async generateMissingDeliverables(currentPhase, existingDeliverables) {
        const requirements = PHASE_REQUIREMENTS[currentPhase];
        const existingNames = existingDeliverables.map(d => d.deliverable_name);
        const missingDeliverables = requirements.deliverables.filter(
            name => !existingNames.includes(name)
        );

        const generatedDeliverables = [];

        for (const deliverableName of missingDeliverables) {
            try {
                const content = await this.generateDeliverableContent(currentPhase, deliverableName);
                
                const deliverable = await InitiativeDeliverable.create({
                    initiative_id: this.initiativeId,
                    phase: currentPhase,
                    deliverable_name: deliverableName,
                    deliverable_type: deliverableName.replace(/\s+/g, '_').toLowerCase(),
                    content: content,
                    status: 'Completed'
                });

                generatedDeliverables.push(deliverable);
            } catch (error) {
                console.error(`Failed to generate ${deliverableName}:`, error);
            }
        }

        return generatedDeliverables;
    }

    async generateDeliverableContent(phase, deliverableName) {
        const prompt = `You are the PIKAR AI Transformation Agent generating a comprehensive ${deliverableName} for the ${phase} phase of an enterprise business transformation initiative.

**DELIVERABLE GENERATION REQUEST**

Phase: ${phase}
Deliverable: ${deliverableName}

**GENERATION REQUIREMENTS:**

Generate a professional, enterprise-grade document that includes:

1. **Executive Summary** (3-4 key points)
2. **Detailed Content** (comprehensive analysis/plan)
3. **Key Findings/Recommendations** (5-7 actionable items)
4. **Success Metrics** (3-5 measurable KPIs)
5. **Next Steps** (specific actions with timelines)

**ENTERPRISE STANDARDS:**
- C-suite quality content
- Quantified business impact where possible
- Risk assessment and mitigation strategies
- Implementation timelines and resource requirements
- Success measurement frameworks

Format as structured markdown with clear sections, bullet points, and actionable content suitable for board-level presentation.

Generate the comprehensive ${deliverableName} now.`;

        const content = await InvokeLLM({ prompt });
        return content;
    }

    async executeAutomatedProgression(currentPhase, targetPhase) {
        this.progressionHistory.push({
            from: currentPhase,
            to: targetPhase,
            timestamp: new Date(),
            automated: true
        });

        // Update initiative phase
        await BusinessInitiative.update(this.initiativeId, {
            current_phase: targetPhase,
            status: "In Progress"
        });

        return {
            success: true,
            newPhase: targetPhase,
            timestamp: new Date()
        };
    }
}

export default function AutomatedPhaseProgression({ initiativeId, currentPhase, onPhaseChange }) {
    const [phaseProgress, setPhaseProgress] = useState(0);
    const [deliverables, setDeliverables] = useState([]);
    const [isEvaluating, setIsEvaluating] = useState(false);
    const [evaluation, setEvaluation] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [automationEnabled, setAutomationEnabled] = useState(true);
    const [progressionEngine] = useState(new PhaseProgressionEngine(initiativeId));

    const phases = [
        "Discovery & Assessment",
        "Planning & Design", 
        "Foundation & Infrastructure",
        "Execution & Optimization",
        "Scale & Expansion",
        "Sustainability"
    ];

    const loadPhaseDeliverables = useCallback(async () => {
        try {
            const phaseDeliverables = await InitiativeDeliverable.filter({
                initiative_id: initiativeId,
                phase: currentPhase
            });
            setDeliverables(phaseDeliverables);
        } catch (error) {
            console.error("Error loading deliverables:", error);
        }
    }, [initiativeId, currentPhase]);

    const generateMissingDeliverables = useCallback(async () => {
        setIsGenerating(true);
        try {
            const generated = await progressionEngine.generateMissingDeliverables(currentPhase, deliverables);
            if (generated.length > 0) {
                toast.success(`Generated ${generated.length} missing deliverable(s)`);
                await loadPhaseDeliverables();
            }
        } catch (error) {
            console.error("Error generating deliverables:", error);
            toast.error("Failed to generate missing deliverables");
        } finally {
            setIsGenerating(false);
        }
    }, [currentPhase, deliverables, progressionEngine, loadPhaseDeliverables]);

    const executePhaseProgression = useCallback(async (targetPhase) => {
        try {
            const result = await progressionEngine.executeAutomatedProgression(currentPhase, targetPhase);
            if (result.success) {
                toast.success(`Automatically progressed to ${targetPhase} phase`);
                if (onPhaseChange) {
                    onPhaseChange(targetPhase);
                }
            }
        } catch (error) {
            console.error("Error executing phase progression:", error);
            toast.error("Failed to progress to next phase");
        }
    }, [currentPhase, progressionEngine, onPhaseChange]);

    const evaluatePhaseCompletion = useCallback(async () => {
        setIsEvaluating(true);
        try {
            const evaluation = await progressionEngine.evaluatePhaseCompletion(currentPhase, deliverables);
            setEvaluation(evaluation);
            setPhaseProgress(evaluation.score);

            // Auto-generate missing deliverables if enabled
            if (automationEnabled && evaluation.deliverableScore < 100) {
                await generateMissingDeliverables();
            }

            // Auto-progress if conditions are met
            if (automationEnabled && evaluation.canProgress && evaluation.nextPhase !== 'Complete') {
                setTimeout(() => {
                    executePhaseProgression(evaluation.nextPhase);
                }, 2000);
            }
        } catch (error) {
            console.error("Error evaluating phase:", error);
        } finally {
            setIsEvaluating(false);
        }
    }, [currentPhase, deliverables, automationEnabled, progressionEngine, generateMissingDeliverables, executePhaseProgression]);

    useEffect(() => {
        loadPhaseDeliverables();
    }, [loadPhaseDeliverables]);

    useEffect(() => {
        if (deliverables.length > 0) {
            evaluatePhaseCompletion();
        }
    }, [deliverables, evaluatePhaseCompletion]);

    const getPhaseStatus = (phaseName) => {
        const currentIndex = phases.indexOf(currentPhase);
        const phaseIndex = phases.indexOf(phaseName);
        
        if (phaseIndex < currentIndex) return 'completed';
        if (phaseIndex === currentIndex) return 'current';
        return 'upcoming';
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800';
            case 'current': return 'bg-blue-100 text-blue-800';
            case 'upcoming': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getCriteriaColor = (criterion) => {
        const percentage = (criterion.current / criterion.target) * 100;
        if (percentage >= 100) return 'text-green-600';
        if (percentage >= 80) return 'text-blue-600';
        if (percentage >= 60) return 'text-yellow-600';
        return 'text-red-600';
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-3">
                            <Zap className="w-6 h-6 text-blue-600" />
                            Automated Phase Progression Engine
                        </CardTitle>
                        <p className="text-gray-600">
                            AI-powered phase transition with automated deliverable generation and validation
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge variant={automationEnabled ? "default" : "outline"}>
                            {automationEnabled ? "Auto-Enabled" : "Manual Mode"}
                        </Badge>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setAutomationEnabled(!automationEnabled)}
                        >
                            {automationEnabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Phase Timeline */}
                    <div className="mb-8">
                        <h3 className="font-semibold mb-4">Transformation Journey Progress</h3>
                        <div className="flex items-center space-x-4 overflow-x-auto pb-4">
                            {phases.map((phase, index) => {
                                const status = getPhaseStatus(phase);
                                return (
                                    <div key={phase} className="flex items-center">
                                        <div className="flex flex-col items-center min-w-[120px]">
                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                                status === 'completed' ? 'bg-green-600 text-white' :
                                                status === 'current' ? 'bg-blue-600 text-white' :
                                                'bg-gray-300 text-gray-600'
                                            }`}>
                                                {status === 'completed' ? <CheckCircle className="w-4 h-4" /> : index + 1}
                                            </div>
                                            <Badge className={`${getStatusColor(status)} mt-2 text-xs`} variant="outline">
                                                {phase.split(' ')[0]}
                                            </Badge>
                                        </div>
                                        {index < phases.length - 1 && (
                                            <ArrowRight className="w-4 h-4 text-gray-400 mx-2" />
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Current Phase Analysis */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Phase Progress */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Current Phase: {currentPhase}</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    <div>
                                        <div className="flex justify-between mb-2">
                                            <span className="text-sm font-medium">Overall Progress</span>
                                            <span className="text-sm text-gray-600">{Math.round(phaseProgress)}%</span>
                                        </div>
                                        <Progress value={phaseProgress} className="h-3" />
                                    </div>

                                    {evaluation && (
                                        <div>
                                            <div className="flex justify-between mb-2">
                                                <span className="text-sm font-medium">Deliverables</span>
                                                <span className="text-sm text-gray-600">
                                                    {Math.round(evaluation.deliverableScore)}%
                                                </span>
                                            </div>
                                            <Progress value={evaluation.deliverableScore} className="h-2" />
                                        </div>
                                    )}

                                    <div className="flex gap-2">
                                        <Button
                                            onClick={evaluatePhaseCompletion}
                                            disabled={isEvaluating}
                                            size="sm"
                                            variant="outline"
                                        >
                                            {isEvaluating ? (
                                                <>
                                                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-600 mr-2"></div>
                                                    Evaluating...
                                                </>
                                            ) : (
                                                <>
                                                    <Target className="w-3 h-3 mr-2" />
                                                    Evaluate Progress
                                                </>
                                            )}
                                        </Button>

                                        <Button
                                            onClick={generateMissingDeliverables}
                                            disabled={isGenerating}
                                            size="sm"
                                            variant="outline"
                                        >
                                            {isGenerating ? (
                                                <>
                                                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-600 mr-2"></div>
                                                    Generating...
                                                </>
                                            ) : (
                                                <>
                                                    <Zap className="w-3 h-3 mr-2" />
                                                    Generate Missing
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Completion Criteria */}
                        {evaluation && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <CheckCircle className="w-5 h-5" />
                                        Completion Criteria
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        {evaluation.criteriaScores.map((criterion, index) => (
                                            <div key={index} className="flex items-center justify-between">
                                                <span className="text-sm">{criterion.name}</span>
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-sm font-medium ${getCriteriaColor(criterion)}`}>
                                                        {Math.round(criterion.current)}/{criterion.target}%
                                                    </span>
                                                    {criterion.met && <CheckCircle className="w-4 h-4 text-green-600" />}
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {evaluation.canProgress && evaluation.nextPhase !== 'Complete' && (
                                        <div className="mt-4 p-3 bg-green-50 rounded-lg">
                                            <div className="flex items-center gap-2 text-green-800">
                                                <CheckCircle className="w-4 h-4" />
                                                <span className="font-medium">Ready for {evaluation.nextPhase}</span>
                                            </div>
                                            <p className="text-sm text-green-600 mt-1">
                                                All criteria met. {automationEnabled ? 'Auto-progressing...' : 'Manual progression required.'}
                                            </p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}
                    </div>

                    {/* Gaps and Recommendations */}
                    {evaluation && evaluation.gaps.length > 0 && (
                        <Card className="mt-6">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <AlertCircle className="w-5 h-5 text-orange-600" />
                                    Completion Gaps
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-2">
                                    {evaluation.gaps.map((gap, index) => (
                                        <div key={index} className="flex items-center justify-between p-2 bg-orange-50 rounded">
                                            <span className="text-sm">{gap.criterion}</span>
                                            <Badge variant="outline" className="bg-white">
                                                {Math.round(gap.gap)}% gap
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Deliverables Status */}
                    <Card className="mt-6">
                        <CardHeader>
                            <CardTitle>Phase Deliverables</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                {PHASE_REQUIREMENTS[currentPhase]?.deliverables.map((deliverableName) => {
                                    const existing = deliverables.find(d => d.deliverable_name === deliverableName);
                                    return (
                                        <div key={deliverableName} className="flex items-center justify-between p-2 border rounded">
                                            <span className="text-sm">{deliverableName}</span>
                                            <Badge className={existing?.status === 'Completed' ? 
                                                'bg-green-100 text-green-800' : 
                                                'bg-gray-100 text-gray-800'
                                            }>
                                                {existing?.status || 'Pending'}
                                            </Badge>
                                        </div>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>
                </CardContent>
            </Card>
        </div>
    );
}
