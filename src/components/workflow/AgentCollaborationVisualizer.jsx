
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WorkflowStep } from '@/api/entities';
import { 
    Network, 
    ArrowRight, 
    CheckCircle, 
    Clock, 
    AlertCircle, 
    Lightbulb,
    Target,
    Users,
    BarChart3,
    Bot,
    Sparkles,
    DollarSign,
    UserCheck,
    ShieldCheck,
    SlidersHorizontal
} from 'lucide-react';

const AGENT_ICONS = {
    'Strategic Planning': Lightbulb,
    'Content Creation': Sparkles,
    'Customer Support': Users,
    'Sales Intelligence': Target,
    'Data Analysis': Bot,
    'Marketing Automation': BarChart3,
    'Financial Analysis': DollarSign,
    'HR & Recruitment': UserCheck,
    'Compliance & Risk': ShieldCheck,
    'Operations Optimization': SlidersHorizontal
};

const AGENT_COLORS = {
    'Strategic Planning': 'bg-purple-100 text-purple-800 border-purple-200',
    'Content Creation': 'bg-blue-100 text-blue-800 border-blue-200',
    'Customer Support': 'bg-green-100 text-green-800 border-green-200',
    'Sales Intelligence': 'bg-orange-100 text-orange-800 border-orange-200',
    'Data Analysis': 'bg-indigo-100 text-indigo-800 border-indigo-200',
    'Marketing Automation': 'bg-pink-100 text-pink-800 border-pink-200',
    'Financial Analysis': 'bg-emerald-100 text-emerald-800 border-emerald-200',
    'HR & Recruitment': 'bg-cyan-100 text-cyan-800 border-cyan-200',
    'Compliance & Risk': 'bg-red-100 text-red-800 border-red-200',
    'Operations Optimization': 'bg-yellow-100 text-yellow-800 border-yellow-200'
};

export default function AgentCollaborationVisualizer({ workflowId, workflowSteps = [], onStepClick }) {
    const [activeConnections, setActiveConnections] = useState([]);
    const [collaborationInsights, setCollaborationInsights] = useState([]);

    const analyzeCollaborationPatterns = useCallback(() => {
        const insights = [];
        
        // Analyze sequential agent handoffs
        for (let i = 0; i < workflowSteps.length - 1; i++) {
            const currentStep = workflowSteps[i];
            const nextStep = workflowSteps[i + 1];
            
            if (currentStep.step_status === 'completed' && nextStep.step_status === 'running') {
                insights.push({
                    type: 'handoff',
                    message: `${currentStep.agent_name} → ${nextStep.agent_name}: Active data transfer`,
                    confidence: 95
                });
            }
        }

        // Identify parallel processing opportunities
        const parallelSteps = workflowSteps.filter(step => 
            step.step_status === 'running' || step.step_status === 'pending'
        );
        
        if (parallelSteps.length > 1) {
            insights.push({
                type: 'optimization',
                message: `${parallelSteps.length} agents can work in parallel to reduce execution time`,
                confidence: 88
            });
        }

        // Detect high-value collaborations
        const completedSteps = workflowSteps.filter(step => step.step_status === 'completed');
        if (completedSteps.length >= 2) {
            const agentPairs = [];
            for (let i = 0; i < completedSteps.length - 1; i++) {
                agentPairs.push([completedSteps[i].agent_name, completedSteps[i + 1].agent_name]);
            }
            
            if (agentPairs.some(pair => pair.includes('Strategic Planning') && pair.includes('Data Analysis'))) {
                insights.push({
                    type: 'synergy',
                    message: 'Strategic Planning + Data Analysis: High-impact collaboration detected',
                    confidence: 92
                });
            }
        }

        setCollaborationInsights(insights);
    }, [workflowSteps]); // workflowSteps is a dependency because it's used inside

    const identifyActiveConnections = useCallback(() => {
        const connections = [];
        
        for (let i = 0; i < workflowSteps.length - 1; i++) {
            const currentStep = workflowSteps[i];
            const nextStep = workflowSteps[i + 1];
            
            connections.push({
                from: currentStep.agent_name,
                to: nextStep.agent_name,
                status: currentStep.step_status === 'completed' ? 'active' : 'pending',
                dataType: 'analysis_output'
            });
        }
        
        setActiveConnections(connections);
    }, [workflowSteps]); // workflowSteps is a dependency because it's used inside

    useEffect(() => {
        if (workflowSteps.length > 0) {
            analyzeCollaborationPatterns();
            identifyActiveConnections();
        }
    }, [workflowSteps, analyzeCollaborationPatterns, identifyActiveConnections]); // Added functions to dependencies

    const getStepStatus = (status) => {
        switch (status) {
            case 'completed': return { icon: CheckCircle, color: 'text-green-600' };
            case 'running': return { icon: Clock, color: 'text-blue-600 animate-pulse' };
            case 'failed': return { icon: AlertCircle, color: 'text-red-600' };
            default: return { icon: Clock, color: 'text-gray-400' };
        }
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Network className="w-5 h-5" />
                        Agent Collaboration Flow
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="relative">
                        {/* Agent Steps Visualization */}
                        <div className="flex flex-wrap gap-4 mb-6">
                            {workflowSteps.map((step, index) => {
                                const AgentIcon = AGENT_ICONS[step.agent_name] || Bot;
                                const statusInfo = getStepStatus(step.step_status);
                                const StatusIcon = statusInfo.icon;
                                
                                return (
                                    <div key={step.id} className="relative group">
                                        <Card 
                                            className={`p-4 cursor-pointer transition-all hover:shadow-lg ${
                                                step.step_status === 'running' ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
                                            }`}
                                            onClick={() => onStepClick && onStepClick(step)}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className="relative">
                                                    <AgentIcon className="w-8 h-8 text-gray-600" />
                                                    <StatusIcon className={`absolute -bottom-1 -right-1 w-4 h-4 ${statusInfo.color}`} />
                                                </div>
                                                <div>
                                                    <h4 className="font-medium text-sm">{step.agent_name}</h4>
                                                    <Badge 
                                                        variant="outline" 
                                                        className={`text-xs ${AGENT_COLORS[step.agent_name] || 'bg-gray-100'}`}
                                                    >
                                                        Step {step.step_order}
                                                    </Badge>
                                                </div>
                                            </div>
                                            
                                            {step.execution_time && (
                                                <div className="mt-2 text-xs text-gray-500">
                                                    ⏱ {step.execution_time}s
                                                </div>
                                            )}
                                        </Card>
                                        
                                        {/* Connection Arrow */}
                                        {index < workflowSteps.length - 1 && (
                                            <div className="absolute top-1/2 -right-6 transform -translate-y-1/2 z-10">
                                                <ArrowRight className={`w-4 h-4 ${
                                                    step.step_status === 'completed' ? 'text-green-500' : 'text-gray-300'
                                                }`} />
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        {/* Data Flow Connections */}
                        <div className="border-t pt-4">
                            <h4 className="font-medium mb-3">Active Data Connections</h4>
                            <div className="grid gap-2">
                                {activeConnections.map((conn, index) => (
                                    <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                                        <Badge variant="outline" className={AGENT_COLORS[conn.from]}>
                                            {conn.from}
                                        </Badge>
                                        <ArrowRight className={`w-4 h-4 ${
                                            conn.status === 'active' ? 'text-green-500' : 'text-gray-400'
                                        }`} />
                                        <Badge variant="outline" className={AGENT_COLORS[conn.to]}>
                                            {conn.to}
                                        </Badge>
                                        <span className="text-xs text-gray-500 ml-auto">
                                            {conn.dataType}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Collaboration Insights */}
            {collaborationInsights.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">AI Collaboration Insights</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {collaborationInsights.map((insight, index) => (
                                <div key={index} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                                    <Bot className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <p className="text-sm font-medium text-blue-900">{insight.message}</p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <Badge variant="outline" className="text-xs">
                                                {insight.type}
                                            </Badge>
                                            <span className="text-xs text-blue-700">
                                                {insight.confidence}% confidence
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
