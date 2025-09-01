
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { InvokeLLM } from '@/api/integrations';
import { 
    Brain, 
    TrendingUp, 
    Users, 
    Zap, 
    Network,
    Sparkles,
    ArrowRight,
    Eye,
    BarChart3,
    Target,
    Lightbulb
} from 'lucide-react';
import { toast } from 'sonner';

export default function CrossAgentInsights({ agentResults = {}, currentContext = '' }) {
    const [insights, setInsights] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [correlations, setCorrelations] = useState([]);
    const [recommendations, setRecommendations] = useState([]);

    const generateCrossAgentInsights = useCallback(async () => {
        if (Object.keys(agentResults).length < 2) return;

        setIsAnalyzing(true);
        try {
            const prompt = `You are the PIKAR AI Cross-Agent Intelligence Coordinator. Analyze the outputs from multiple specialized agents and generate comprehensive insights that reveal patterns, correlations, and opportunities that wouldn't be visible from individual agent analysis.

**CURRENT CONTEXT:**
${currentContext}

**AGENT OUTPUTS:**
${Object.entries(agentResults).map(([agent, result]) => `
**${agent} Analysis:**
${typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
`).join('\n')}

**CROSS-AGENT ANALYSIS REQUIREMENTS:**

1. **CORRELATION ANALYSIS:**
   - Identify patterns and connections between different agent findings
   - Highlight complementary insights and conflicting perspectives
   - Quantify correlation strength where possible

2. **SYNTHESIS INSIGHTS:**
   - Generate insights that only emerge from combining multiple agent perspectives
   - Identify blind spots that individual agents might have missed
   - Create unified recommendations based on collective intelligence

3. **STRATEGIC IMPLICATIONS:**
   - Assess business impact of combined insights
   - Prioritize actions based on cross-agent consensus
   - Identify areas requiring additional agent analysis

4. **PERFORMANCE OPTIMIZATION:**
   - Suggest how agents could better collaborate in future
   - Identify the most valuable agent combinations for this type of analysis
   - Recommend workflow optimizations

**OUTPUT FORMAT:**
Provide a JSON response with this structure:
{
  "correlation_score": <number 0-100>,
  "key_insights": [
    {
      "insight": "<insight description>",
      "supporting_agents": ["agent1", "agent2"],
      "confidence_level": <number 0-100>,
      "business_impact": "<high/medium/low>"
    }
  ],
  "agent_synergies": [
    {
      "agents": ["agent1", "agent2"],
      "synergy_type": "<complementary/reinforcing/contrasting>",
      "value_created": "<description>"
    }
  ],
  "unified_recommendations": [
    {
      "recommendation": "<action item>",
      "priority": "<high/medium/low>",
      "required_agents": ["agent1", "agent2"],
      "expected_outcome": "<description>"
    }
  ],
  "gaps_identified": [
    {
      "gap": "<description>",
      "suggested_agent": "<agent name>",
      "analysis_type": "<type of analysis needed>"
    }
  ],
  "executive_summary": "<2-3 sentence summary of key cross-agent insights>"
}

Generate the comprehensive cross-agent intelligence analysis now.`;

            const response = await InvokeLLM({
                prompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        correlation_score: { type: "number" },
                        key_insights: { 
                            type: "array", 
                            items: { 
                                type: "object",
                                properties: {
                                    insight: { type: "string" },
                                    supporting_agents: { type: "array", items: { type: "string" } },
                                    confidence_level: { type: "number" },
                                    business_impact: { type: "string" }
                                }
                            } 
                        },
                        agent_synergies: {
                            type: "array",
                            items: {
                                type: "object", 
                                properties: {
                                    agents: { type: "array", items: { type: "string" } },
                                    synergy_type: { type: "string" },
                                    value_created: { type: "string" }
                                }
                            }
                        },
                        unified_recommendations: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    recommendation: { type: "string" },
                                    priority: { type: "string" },
                                    required_agents: { type: "array", items: { type: "string" } },
                                    expected_outcome: { type: "string" }
                                }
                            }
                        },
                        gaps_identified: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    gap: { type: "string" },
                                    suggested_agent: { type: "string" },
                                    analysis_type: { type: "string" }
                                }
                            }
                        },
                        executive_summary: { type: "string" }
                    },
                    required: ["correlation_score", "key_insights", "unified_recommendations", "executive_summary"]
                }
            });

            setInsights(response);
            
            // Extract correlations and recommendations for quick access
            setCorrelations(response.agent_synergies || []);
            setRecommendations(response.unified_recommendations || []);

        } catch (error) {
            console.error("Error generating cross-agent insights:", error);
            toast.error("Failed to generate cross-agent insights");
        }
        setIsAnalyzing(false);
    }, [agentResults, currentContext]); // Add agentResults and currentContext to useCallback dependencies

    useEffect(() => {
        if (Object.keys(agentResults).length >= 2) {
            generateCrossAgentInsights();
        }
    }, [agentResults, generateCrossAgentInsights]); // Add generateCrossAgentInsights to useEffect dependencies

    const getConfidenceColor = (confidence) => {
        if (confidence >= 80) return 'bg-green-100 text-green-800';
        if (confidence >= 60) return 'bg-yellow-100 text-yellow-800';
        return 'bg-red-100 text-red-800';
    };

    const getImpactColor = (impact) => {
        switch (impact) {
            case 'high': return 'bg-red-100 text-red-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'high': return 'bg-red-100 text-red-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-blue-100 text-blue-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    if (Object.keys(agentResults).length < 2) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Brain className="w-5 h-5 text-purple-600" />
                        Cross-Agent Intelligence
                    </CardTitle>
                    <CardDescription>Insights from multi-agent collaboration</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="text-center text-gray-500 py-8">
                        <Network className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Run at least 2 different agents to generate cross-agent insights</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Overview Card */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Brain className="w-5 h-5 text-purple-600" />
                        Cross-Agent Intelligence Dashboard
                    </CardTitle>
                    <CardDescription>
                        {Object.keys(agentResults).length} agents analyzed • 
                        {insights ? ` ${insights.correlation_score}% correlation detected` : ' Analyzing...'}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isAnalyzing ? (
                        <div className="flex items-center justify-center py-8">
                            <Sparkles className="w-6 h-6 animate-spin text-purple-500 mr-2" />
                            <span>Analyzing cross-agent patterns...</span>
                        </div>
                    ) : insights ? (
                        <div className="space-y-4">
                            {/* Executive Summary */}
                            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                                <h3 className="font-medium text-purple-900 mb-2 flex items-center gap-2">
                                    <Eye className="w-4 h-4" />
                                    Executive Summary
                                </h3>
                                <p className="text-purple-800 text-sm">{insights.executive_summary}</p>
                            </div>

                            {/* Quick Stats */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="text-center p-4 bg-gray-50 rounded-lg">
                                    <div className="text-2xl font-bold text-purple-600">{insights.correlation_score}%</div>
                                    <div className="text-xs text-gray-600">Correlation Score</div>
                                </div>
                                <div className="text-center p-4 bg-gray-50 rounded-lg">
                                    <div className="text-2xl font-bold text-blue-600">{insights.key_insights?.length || 0}</div>
                                    <div className="text-xs text-gray-600">Key Insights</div>
                                </div>
                                <div className="text-center p-4 bg-gray-50 rounded-lg">
                                    <div className="text-2xl font-bold text-green-600">{insights.unified_recommendations?.length || 0}</div>
                                    <div className="text-xs text-gray-600">Recommendations</div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <Button onClick={generateCrossAgentInsights} className="w-full">
                            <Brain className="w-4 h-4 mr-2" />
                            Generate Cross-Agent Analysis
                        </Button>
                    )}
                </CardContent>
            </Card>

            {/* Detailed Analysis Tabs */}
            {insights && (
                <Card>
                    <CardContent className="p-0">
                        <Tabs defaultValue="insights" className="w-full">
                            <TabsList className="grid w-full grid-cols-4">
                                <TabsTrigger value="insights">Key Insights</TabsTrigger>
                                <TabsTrigger value="synergies">Agent Synergies</TabsTrigger>
                                <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
                                <TabsTrigger value="gaps">Analysis Gaps</TabsTrigger>
                            </TabsList>

                            <TabsContent value="insights" className="p-6">
                                <div className="space-y-4">
                                    <h3 className="font-medium flex items-center gap-2">
                                        <Lightbulb className="w-4 h-4" />
                                        Cross-Agent Key Insights
                                    </h3>
                                    {insights.key_insights?.map((insight, index) => (
                                        <div key={index} className="border rounded-lg p-4">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex-1">
                                                    <p className="font-medium text-sm">{insight.insight}</p>
                                                    <div className="flex items-center gap-2 mt-2">
                                                        <Badge variant="outline" className="text-xs">
                                                            {insight.supporting_agents?.join(' + ')}
                                                        </Badge>
                                                        <Badge className={getConfidenceColor(insight.confidence_level)}>
                                                            {insight.confidence_level}% Confidence
                                                        </Badge>
                                                        <Badge className={getImpactColor(insight.business_impact)}>
                                                            {insight.business_impact} Impact
                                                        </Badge>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </TabsContent>

                            <TabsContent value="synergies" className="p-6">
                                <div className="space-y-4">
                                    <h3 className="font-medium flex items-center gap-2">
                                        <Network className="w-4 h-4" />
                                        Agent Collaboration Synergies
                                    </h3>
                                    {insights.agent_synergies?.map((synergy, index) => (
                                        <div key={index} className="border rounded-lg p-4">
                                            <div className="flex items-center gap-2 mb-2">
                                                <Badge variant="outline">
                                                    {synergy.agents?.join(' ↔ ')}
                                                </Badge>
                                                <Badge className={
                                                    synergy.synergy_type === 'reinforcing' ? 'bg-green-100 text-green-800' :
                                                    synergy.synergy_type === 'complementary' ? 'bg-blue-100 text-blue-800' :
                                                    'bg-orange-100 text-orange-800'
                                                }>
                                                    {synergy.synergy_type}
                                                </Badge>
                                            </div>
                                            <p className="text-sm text-gray-700">{synergy.value_created}</p>
                                        </div>
                                    ))}
                                </div>
                            </TabsContent>

                            <TabsContent value="recommendations" className="p-6">
                                <div className="space-y-4">
                                    <h3 className="font-medium flex items-center gap-2">
                                        <Target className="w-4 h-4" />
                                        Unified Recommendations
                                    </h3>
                                    {insights.unified_recommendations?.map((rec, index) => (
                                        <div key={index} className="border rounded-lg p-4">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex-1">
                                                    <p className="font-medium text-sm">{rec.recommendation}</p>
                                                    <p className="text-xs text-gray-600 mt-1">{rec.expected_outcome}</p>
                                                </div>
                                                <Badge className={getPriorityColor(rec.priority)}>
                                                    {rec.priority} Priority
                                                </Badge>
                                            </div>
                                            <div className="flex items-center gap-2 mt-2">
                                                <Badge variant="outline" className="text-xs">
                                                    Requires: {rec.required_agents?.join(', ')}
                                                </Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </TabsContent>

                            <TabsContent value="gaps" className="p-6">
                                <div className="space-y-4">
                                    <h3 className="font-medium flex items-center gap-2">
                                        <TrendingUp className="w-4 h-4" />
                                        Identified Analysis Gaps
                                    </h3>
                                    {insights.gaps_identified?.length > 0 ? (
                                        insights.gaps_identified.map((gap, index) => (
                                            <div key={index} className="border rounded-lg p-4">
                                                <div className="flex items-start justify-between mb-2">
                                                    <div className="flex-1">
                                                        <p className="font-medium text-sm">{gap.gap}</p>
                                                        <p className="text-xs text-gray-600 mt-1">Analysis Type: {gap.analysis_type}</p>
                                                    </div>
                                                </div>
                                                <Badge variant="outline" className="text-xs">
                                                    Suggested Agent: {gap.suggested_agent}
                                                </Badge>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center text-gray-500 py-8">
                                            <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                            <p className="text-sm">No analysis gaps identified - comprehensive coverage achieved!</p>
                                        </div>
                                    )}
                                </div>
                            </TabsContent>
                        </Tabs>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
