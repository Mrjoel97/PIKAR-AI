import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { 
    Play,
    Pause,
    Settings,
    CheckCircle,
    Clock,
    AlertTriangle,
    Users,
    Bot
} from 'lucide-react';

export default function WorkflowCard({ workflow, onExecute }) {
    const getStatusColor = (status) => {
        switch (status) {
            case 'active': return 'bg-green-100 text-green-800';
            case 'completed': return 'bg-blue-100 text-blue-800';
            case 'failed': return 'bg-red-100 text-red-800';
            case 'draft': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'active': return <Play className="w-4 h-4" />;
            case 'completed': return <CheckCircle className="w-4 h-4" />;
            case 'failed': return <AlertTriangle className="w-4 h-4" />;
            case 'draft': return <Clock className="w-4 h-4" />;
            default: return <Clock className="w-4 h-4" />;
        }
    };

    const getCategoryColor = (category) => {
        switch (category) {
            case 'strategic_planning': return 'bg-purple-100 text-purple-800';
            case 'market_analysis': return 'bg-blue-100 text-blue-800';
            case 'compliance': return 'bg-red-100 text-red-800';
            case 'financial': return 'bg-green-100 text-green-800';
            case 'operations': return 'bg-yellow-100 text-yellow-800';
            case 'hr': return 'bg-cyan-100 text-cyan-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const calculateProgress = () => {
        // This would ideally come from the workflow's step completion status
        // For now, we'll simulate based on status
        switch (workflow.workflow_status) {
            case 'completed': return 100;
            case 'active': return 40; // Simulated progress
            case 'failed': return 25; // Stopped partway
            default: return 0;
        }
    };

    return (
        <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                            <CardTitle className="text-lg">{workflow.workflow_name}</CardTitle>
                            <Badge className={getStatusColor(workflow.workflow_status)}>
                                {getStatusIcon(workflow.workflow_status)}
                                <span className="ml-1">{workflow.workflow_status}</span>
                            </Badge>
                            <Badge className={getCategoryColor(workflow.workflow_category)}>
                                {workflow.workflow_category.replace(/_/g, ' ')}
                            </Badge>
                        </div>
                        <CardDescription>{workflow.workflow_description}</CardDescription>
                        <div className="flex items-center gap-4 text-sm text-gray-500 mt-2">
                            <span className="flex items-center gap-1">
                                <Bot className="w-4 h-4" />
                                {workflow.total_steps} agents
                            </span>
                            <span className="flex items-center gap-1">
                                <Clock className="w-4 h-4" />
                                {workflow.estimated_duration}
                            </span>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Link to={createPageUrl(`WorkflowDetails?id=${workflow.id}`)}>
                            <Button variant="outline" size="sm">
                                <Settings className="w-4 h-4 mr-2" />
                                Details
                            </Button>
                        </Link>
                        {workflow.workflow_status !== 'completed' && (
                            <Button size="sm" onClick={() => onExecute?.(workflow.id)} className="bg-blue-600 hover:bg-blue-700">
                                <Play className="w-4 h-4 mr-2" />
                                Execute
                            </Button>
                        )}
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {(workflow.workflow_status === 'active' || workflow.workflow_status === 'completed') && (
                    <div>
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-sm font-medium">Progress</span>
                            <span className="text-sm text-gray-500">{calculateProgress()}%</span>
                        </div>
                        <Progress value={calculateProgress()} className="h-2" />
                    </div>
                )}
            </CardContent>
        </Card>
    );
}