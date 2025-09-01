import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AuditLog } from '@/api/entities';
import { Network, ArrowRight, Bot } from 'lucide-react';
import {
  Timeline,
  TimelineItem,
  TimelineConnector,
  TimelineHeader,
  TimelineTitle,
  TimelineIcon,
  TimelineBody,
} from "@/components/ui/timeline";
import { toast, Toaster } from 'sonner';

const AGENT_ICONS = {
    'Strategic Planning': 'Lightbulb',
    'Content Creation': 'PenSquare',
    'Customer Support': 'Users',
    'Sales Intelligence': 'BarChart',
    'Data Analysis': 'Bot',
    'Marketing Automation': 'Sparkles',
    'Financial Analysis': 'DollarSign',
    'HR & Recruitment': 'UserCheck',
    'Compliance & Risk': 'ShieldCheck',
    'Operations Optimization': 'SlidersHorizontal',
    'Default': 'Bot'
};

const getAgentIcon = (agentName) => {
    // A mapping from agent names to Lucide icon components could be used here
    // For simplicity, returning the component name as a string
    return AGENT_ICONS[agentName] || AGENT_ICONS['Default'];
};

export default function CollaborationHub() {
    const [collaborationLogs, setCollaborationLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchLogs = async () => {
            setIsLoading(true);
            try {
                // Fetch logs related to agent handoffs or workflows
                const logs = await AuditLog.filter({ 
                    $or: [
                        { action_type: 'agent_execution' },
                        { action_type: 'workflow_execution' }
                    ]
                }, '-created_date', 50);

                // Simple logic to create "collaboration" events from logs
                const collaborations = [];
                for (let i = 0; i < logs.length - 1; i++) {
                    const current = logs[i];
                    const next = logs[i+1];
                    // If two subsequent agent executions happen close in time, assume collaboration
                    if (current.agent_name && next.agent_name && current.agent_name !== next.agent_name) {
                         const timeDiff = new Date(current.created_date) - new Date(next.created_date);
                         if(Math.abs(timeDiff) < 5 * 60 * 1000) { // 5 minutes threshold
                             collaborations.push({
                                 id: current.id,
                                 fromAgent: next.agent_name,
                                 toAgent: current.agent_name,
                                 task: current.action_details?.prompt || `Task related to ${current.workflow_id || 'initiative'}` ,
                                 timestamp: current.created_date
                             });
                         }
                    }
                }
                // Add some mock data if logs are empty for demonstration
                if (collaborations.length === 0) {
                    collaborations.push(
                        { id: '1', fromAgent: 'Strategic Planning', toAgent: 'Content Creation', task: 'Generate blog post from SWOT analysis', timestamp: new Date().toISOString() },
                        { id: '2', fromAgent: 'Data Analysis', toAgent: 'Sales Intelligence', task: 'Score leads based on Q3 sales data', timestamp: new Date(Date.now() - 3600000).toISOString() }
                    );
                }

                setCollaborationLogs(collaborations);

            } catch (error) {
                console.error("Failed to fetch collaboration logs", error);
                toast.error("Could not load collaboration history.");
            } finally {
                setIsLoading(false);
            }
        };

        fetchLogs();
    }, []);

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <Toaster richColors />
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold flex items-center gap-3">
                    <Network className="w-8 h-8 text-indigo-600" />
                    Agent Collaboration Hub
                </h1>
                <p className="text-lg text-gray-600 mt-1">
                    Track and visualize how your AI agents work together to drive outcomes.
                </p>
            </div>
            
            <Card>
                <CardHeader>
                    <CardTitle>Recent Collaboration History</CardTitle>
                    <CardDescription>A timeline of automated handoffs and shared intelligence between agents.</CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="text-center p-8">Loading collaboration history...</div>
                    ) : (
                         <Timeline>
                            {collaborationLogs.map((log) => (
                                <TimelineItem key={log.id}>
                                    <TimelineConnector />
                                    <TimelineHeader>
                                        <TimelineIcon>
                                            <Bot className="w-4 h-4" />
                                        </TimelineIcon>
                                        <TimelineTitle className="flex items-center gap-4 text-md">
                                            <Badge variant="outline">{log.fromAgent}</Badge>
                                            <ArrowRight className="w-5 h-5 text-gray-400" />
                                            <Badge variant="outline">{log.toAgent}</Badge>
                                        </TimelineTitle>
                                    </TimelineHeader>
                                    <TimelineBody className="pb-8">
                                        <p className="text-sm text-gray-700">{log.task}</p>
                                        <p className="text-xs text-gray-500 mt-1">
                                            {new Date(log.timestamp).toLocaleString()}
                                        </p>
                                    </TimelineBody>
                                </TimelineItem>
                            ))}
                        </Timeline>
                    )}
                     {collaborationLogs.length === 0 && !isLoading && (
                        <div className="text-center py-12 text-gray-500">
                            No collaboration events recorded yet.
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}