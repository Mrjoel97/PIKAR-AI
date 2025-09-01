import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { InvokeLLM } from '@/api/integrations';
import { Target, Zap, TrendingDown, CheckCircle, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const SNAP_PRINCIPLES = {
    Simplification: {
        description: "Remove unnecessary complexity and streamline processes",
        metrics: ["process_steps", "decision_points", "stakeholders_involved"],
        target_reduction: 30
    },
    Normalization: {
        description: "Standardize processes and eliminate variations",
        metrics: ["process_variations", "exception_handling", "custom_workflows"],
        target_reduction: 50
    },
    Automation: {
        description: "Automate repetitive tasks and decision points",
        metrics: ["manual_steps", "approval_cycles", "data_entry_points"],
        target_reduction: 60
    },
    Parallelization: {
        description: "Execute tasks concurrently to reduce cycle time",
        metrics: ["sequential_dependencies", "bottlenecks", "waiting_time"],
        target_reduction: 40
    }
};

export default function SNAPFramework({ processData, onOptimizationComplete }) {
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [snapAssessment, setSnapAssessment] = useState(null);
    const [optimizationResults, setOptimizationResults] = useState(null);

    const analyzeComplexity = async () => {
        setIsAnalyzing(true);
        try {
            const prompt = `You are the PIKAR AI Operations Optimization Agent implementing SNAP Framework analysis for complexity reduction.

**SNAP FRAMEWORK ANALYSIS REQUEST**

Process Data: ${JSON.stringify(processData, null, 2)}

Analyze this process using the SNAP Framework principles:

**1. SIMPLIFICATION ANALYSIS:**
- Identify unnecessary steps, redundant approvals, and excessive documentation
- Calculate current complexity score (1-100, higher = more complex)
- Recommend specific simplification actions
- Project complexity reduction percentage

**2. NORMALIZATION ANALYSIS:**
- Identify process variations and inconsistencies
- Map exception handling complexity
- Recommend standardization opportunities
- Calculate normalization impact

**3. AUTOMATION ANALYSIS:**
- Identify manual, repetitive tasks suitable for automation
- Assess decision points that can be automated
- Calculate automation potential and ROI
- Recommend automation technologies

**4. PARALLELIZATION ANALYSIS:**
- Identify sequential dependencies that can be made parallel
- Find bottlenecks and waiting time opportunities
- Design parallel execution workflows
- Calculate time reduction potential

Return analysis as JSON with this structure:
{
  "overall_complexity_score": <number 1-100>,
  "snap_assessment": {
    "simplification": {
      "current_score": <number>,
      "reduction_potential": <percentage>,
      "recommendations": [<strings>]
    },
    "normalization": {
      "current_score": <number>,
      "reduction_potential": <percentage>,
      "recommendations": [<strings>]
    },
    "automation": {
      "current_score": <number>,
      "reduction_potential": <percentage>,
      "recommendations": [<strings>]
    },
    "parallelization": {
      "current_score": <number>,
      "reduction_potential": <percentage>,
      "recommendations": [<strings>]
    }
  },
  "optimization_roadmap": [
    {
      "principle": "<snap_principle>",
      "priority": "<high|medium|low>",
      "effort": "<low|medium|high>",
      "impact": "<low|medium|high>",
      "timeline": "<weeks>",
      "description": "<string>"
    }
  ],
  "projected_benefits": {
    "complexity_reduction": <percentage>,
    "time_savings": <percentage>,
    "cost_reduction": <percentage>,
    "quality_improvement": <percentage>
  }
}`;

            const analysis = await InvokeLLM({
                prompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        overall_complexity_score: { type: "number" },
                        snap_assessment: { type: "object" },
                        optimization_roadmap: { type: "array" },
                        projected_benefits: { type: "object" }
                    }
                }
            });

            setSnapAssessment(analysis);
            generateOptimizationPlan(analysis);
            
        } catch (error) {
            console.error("Error analyzing complexity:", error);
            toast.error("Failed to analyze process complexity");
        } finally {
            setIsAnalyzing(false);
        }
    };

    const generateOptimizationPlan = async (assessment) => {
        try {
            const prompt = `Generate detailed implementation plan for SNAP Framework optimization based on analysis:

${JSON.stringify(assessment, null, 2)}

Create specific, actionable optimization steps with:
- Technical implementation details
- Resource requirements
- Success metrics and KPIs
- Risk mitigation strategies
- Change management approach

Focus on enterprise-scale implementation with measurable business impact.`;

            const optimizationPlan = await InvokeLLM({ prompt });
            setOptimizationResults(optimizationPlan);
            
            if (onOptimizationComplete) {
                onOptimizationComplete({
                    assessment,
                    optimizationPlan,
                    framework: 'SNAP'
                });
            }

            toast.success("SNAP Framework analysis completed");
        } catch (error) {
            console.error("Error generating optimization plan:", error);
            toast.error("Failed to generate optimization plan");
        }
    };

    const getComplexityColor = (score) => {
        if (score >= 80) return 'text-red-600 bg-red-50';
        if (score >= 60) return 'text-orange-600 bg-orange-50';
        if (score >= 40) return 'text-yellow-600 bg-yellow-50';
        return 'text-green-600 bg-green-50';
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'high': return 'bg-red-100 text-red-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-3">
                        <Target className="w-6 h-6 text-blue-600" />
                        SNAP Framework Complexity Analysis
                    </CardTitle>
                    <p className="text-gray-600">
                        Systematic complexity reduction through Simplification, Normalization, Automation, and Parallelization
                    </p>
                </CardHeader>
                <CardContent>
                    {!snapAssessment && (
                        <div className="text-center py-8">
                            <Button 
                                onClick={analyzeComplexity} 
                                disabled={isAnalyzing}
                                className="bg-blue-600 hover:bg-blue-700"
                            >
                                {isAnalyzing ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                        Analyzing Complexity...
                                    </>
                                ) : (
                                    <>
                                        <Target className="w-4 h-4 mr-2" />
                                        Start SNAP Analysis
                                    </>
                                )}
                            </Button>
                        </div>
                    )}

                    {snapAssessment && (
                        <div className="space-y-6">
                            {/* Overall Complexity Score */}
                            <div className="text-center">
                                <div className={`inline-flex items-center px-4 py-2 rounded-lg ${getComplexityColor(snapAssessment.overall_complexity_score)}`}>
                                    <span className="text-2xl font-bold mr-2">
                                        {snapAssessment.overall_complexity_score}/100
                                    </span>
                                    <span className="text-sm">Complexity Score</span>
                                </div>
                            </div>

                            {/* SNAP Principles Assessment */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {Object.entries(SNAP_PRINCIPLES).map(([principle, config]) => {
                                    const assessment = snapAssessment.snap_assessment[principle.toLowerCase()];
                                    return (
                                        <Card key={principle} className="border-2">
                                            <CardContent className="p-4">
                                                <div className="flex items-center justify-between mb-2">
                                                    <h3 className="font-semibold text-sm">{principle}</h3>
                                                    <Badge variant="outline">
                                                        {assessment?.reduction_potential}% reduction
                                                    </Badge>
                                                </div>
                                                <Progress 
                                                    value={100 - assessment?.current_score} 
                                                    className="h-2 mb-2"
                                                />
                                                <p className="text-xs text-gray-600">
                                                    {config.description}
                                                </p>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </div>

                            {/* Optimization Roadmap */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Zap className="w-5 h-5 text-yellow-600" />
                                        Optimization Roadmap
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        {snapAssessment.optimization_roadmap?.map((item, index) => (
                                            <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <Badge className={getPriorityColor(item.priority)}>
                                                            {item.priority}
                                                        </Badge>
                                                        <Badge variant="outline">{item.timeline} weeks</Badge>
                                                        <Badge variant="outline">
                                                            {item.effort} effort • {item.impact} impact
                                                        </Badge>
                                                    </div>
                                                    <p className="text-sm font-medium">{item.description}</p>
                                                    <p className="text-xs text-gray-600">
                                                        Principle: {item.principle}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Projected Benefits */}
                            {snapAssessment.projected_benefits && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <TrendingDown className="w-5 h-5 text-green-600" />
                                            Projected Benefits
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="text-center">
                                                <div className="text-2xl font-bold text-blue-600">
                                                    {snapAssessment.projected_benefits.complexity_reduction}%
                                                </div>
                                                <div className="text-sm text-gray-600">Complexity Reduction</div>
                                            </div>
                                            <div className="text-center">
                                                <div className="text-2xl font-bold text-green-600">
                                                    {snapAssessment.projected_benefits.time_savings}%
                                                </div>
                                                <div className="text-sm text-gray-600">Time Savings</div>
                                            </div>
                                            <div className="text-center">
                                                <div className="text-2xl font-bold text-purple-600">
                                                    {snapAssessment.projected_benefits.cost_reduction}%
                                                </div>
                                                <div className="text-sm text-gray-600">Cost Reduction</div>
                                            </div>
                                            <div className="text-center">
                                                <div className="text-2xl font-bold text-orange-600">
                                                    {snapAssessment.projected_benefits.quality_improvement}%
                                                </div>
                                                <div className="text-sm text-gray-600">Quality Improvement</div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Implementation Plan */}
            {optimizationResults && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-green-600" />
                            Implementation Plan
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="prose max-w-none">
                            <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-lg">
                                {optimizationResults}
                            </pre>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}