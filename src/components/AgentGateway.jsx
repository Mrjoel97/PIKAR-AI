import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Network, ArrowRight, Bot, Share2, CheckCircle, Zap } from 'lucide-react';
import { toast } from 'sonner';
import RealTimeCollaboration from '@/components/collaboration/RealTimeCollaboration';

const COMPATIBLE_AGENTS = {
    "Strategic Planning": ["Data Analysis", "Financial Analysis", "Operations Optimization", "Compliance & Risk"],
    "Content Creation": ["Marketing Automation", "Strategic Planning", "HR & Recruitment"],
    "Customer Support": ["Sales Intelligence", "Data Analysis", "Operations Optimization"],
    "Sales Intelligence": ["Strategic Planning", "Data Analysis", "Marketing Automation", "Customer Support"],
    "Data Analysis": ["Strategic Planning", "Financial Analysis", "Sales Intelligence", "Marketing Automation"],
    "Marketing Automation": ["Sales Intelligence", "Content Creation", "Data Analysis"],
    "Financial Analysis": ["Strategic Planning", "Data Analysis", "Operations Optimization"],
    "HR & Recruitment": ["Strategic Planning", "Operations Optimization", "Compliance & Risk"],
    "Operations Optimization": ["Strategic Planning", "Financial Analysis", "HR & Recruitment"],
    "Compliance & Risk": ["Operations Optimization", "HR & Recruitment", "Financial Analysis"]
};

export default function AgentGateway({ agentName, lastOutput }) {
    const [selectedTarget, setSelectedTarget] = useState('');
    const [transferInProgress, setTransferInProgress] = useState(false);
    const [showCollaboration, setShowCollaboration] = useState(false);

    const compatibleAgents = COMPATIBLE_AGENTS[agentName] || [];

    const handleTransfer = () => {
        if (!selectedTarget || !lastOutput) {
            toast.error("Please select a target agent and ensure output is available");
            return;
        }

        setTransferInProgress(true);
        
        // Store the output in session storage for the target agent
        sessionStorage.setItem('agentGatewayInput', JSON.stringify(lastOutput));
        
        // Navigate to the target agent page
        const targetPages = {
            "Strategic Planning": "/StrategicPlanning",
            "Content Creation": "/ContentCreation", 
            "Customer Support": "/CustomerSupport",
            "Sales Intelligence": "/SalesIntelligence",
            "Data Analysis": "/DataAnalysis",
            "Marketing Automation": "/MarketingAutomation",
            "Financial Analysis": "/FinancialAnalysis",
            "HR & Recruitment": "/HRRecruitment",
            "Operations Optimization": "/OperationsOptimization",
            "Compliance & Risk": "/ComplianceRisk"
        };

        const targetUrl = targetPages[selectedTarget];
        if (targetUrl) {
            toast.success(`Transferring output to ${selectedTarget}...`);
            setTimeout(() => {
                window.location.href = targetUrl;
            }, 1000);
        } else {
            toast.error("Target agent page not found");
            setTransferInProgress(false);
        }
    };

    const getAgentColor = (agent) => {
        const colors = {
            'Strategic Planning': 'bg-purple-100 text-purple-800',
            'Data Analysis': 'bg-indigo-100 text-indigo-800',
            'Sales Intelligence': 'bg-orange-100 text-orange-800',
            'Marketing Automation': 'bg-pink-100 text-pink-800',
            'Financial Analysis': 'bg-emerald-100 text-emerald-800',
            'Operations Optimization': 'bg-yellow-100 text-yellow-800',
            'HR & Recruitment': 'bg-cyan-100 text-cyan-800',
            'Compliance & Risk': 'bg-red-100 text-red-800',
            'Content Creation': 'bg-blue-100 text-blue-800',
            'Customer Support': 'bg-green-100 text-green-800'
        };
        return colors[agent] || 'bg-gray-100 text-gray-800';
    };

    if (!compatibleAgents.length) {
        return null; // Don't show gateway if no compatible agents
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
                            <Network className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Agent Collaboration</CardTitle>
                            <CardDescription>
                                Transfer output to compatible agents for enhanced workflows
                            </CardDescription>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowCollaboration(!showCollaboration)}
                    >
                        <Zap className="w-4 h-4 mr-2" />
                        {showCollaboration ? 'Simple' : 'Advanced'}
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {showCollaboration ? (
                    <RealTimeCollaboration 
                        currentAgent={agentName}
                        lastOutput={lastOutput}
                    />
                ) : (
                    <div className="space-y-4">
                        {/* Output Status */}
                        <div className={`p-3 rounded-lg ${lastOutput ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
                            <div className="flex items-center gap-2 mb-2">
                                {lastOutput ? (
                                    <CheckCircle className="w-5 h-5 text-green-600" />
                                ) : (
                                    <Bot className="w-5 h-5 text-gray-400" />
                                )}
                                <span className={`font-medium ${lastOutput ? 'text-green-800' : 'text-gray-600'}`}>
                                    {lastOutput ? 'Output Ready for Transfer' : 'No Output Available'}
                                </span>
                            </div>
                            <p className={`text-sm ${lastOutput ? 'text-green-700' : 'text-gray-500'}`}>
                                {lastOutput 
                                    ? 'Generated content is ready to be transferred to compatible agents'
                                    : 'Generate content first to enable agent collaboration'
                                }
                            </p>
                        </div>

                        {/* Compatible Agents */}
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                Compatible Agents ({compatibleAgents.length})
                            </label>
                            <div className="flex flex-wrap gap-2 mb-3">
                                {compatibleAgents.map(agent => (
                                    <Badge key={agent} className={getAgentColor(agent)} variant="outline">
                                        <Bot className="w-3 h-3 mr-1" />
                                        {agent}
                                    </Badge>
                                ))}
                            </div>
                        </div>

                        {/* Transfer Interface */}
                        <div className="space-y-3">
                            <Select value={selectedTarget} onValueChange={setSelectedTarget}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select target agent..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {compatibleAgents.map(agent => (
                                        <SelectItem key={agent} value={agent}>
                                            <div className="flex items-center gap-2">
                                                <Bot className="w-4 h-4" />
                                                {agent}
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>

                            <Button 
                                onClick={handleTransfer}
                                disabled={!selectedTarget || !lastOutput || transferInProgress}
                                className="w-full"
                            >
                                {transferInProgress ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                        Transferring...
                                    </>
                                ) : (
                                    <>
                                        <Share2 className="w-4 h-4 mr-2" />
                                        Transfer & Navigate
                                    </>
                                )}
                            </Button>
                        </div>

                        {/* Collaboration Flow Visualization */}
                        {selectedTarget && (
                            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                                <div className="flex items-center justify-center gap-3 text-sm">
                                    <Badge className={getAgentColor(agentName)}>
                                        {agentName}
                                    </Badge>
                                    <ArrowRight className="w-4 h-4 text-blue-600" />
                                    <Badge className={getAgentColor(selectedTarget)}>
                                        {selectedTarget}
                                    </Badge>
                                </div>
                                <p className="text-xs text-blue-700 text-center mt-2">
                                    Output will be pre-loaded in {selectedTarget} agent
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}