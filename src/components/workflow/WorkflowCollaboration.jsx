import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { WorkflowStep } from '@/api/entities';
import { Workflow } from '@/api/entities';
import { User } from '@/api/entities';
import { 
    Users, 
    MessageSquare, 
    Clock, 
    CheckCircle, 
    AlertCircle, 
    PlayCircle,
    PauseCircle,
    User as UserIcon,
    Activity,
    Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function WorkflowCollaboration({ workflowId, workflow }) {
    const [steps, setSteps] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [currentStep, setCurrentStep] = useState(null);
    const [collaborators, setCollaborators] = useState([]);
    const [workflowStatus, setWorkflowStatus] = useState('draft');

    const loadWorkflowSteps = useCallback(async () => {
        try {
            const fetchedSteps = await WorkflowStep.filter({ workflow_id: workflowId }, 'step_order');
            setSteps(fetchedSteps || []);
            
            // Find the currently running step
            const runningStep = fetchedSteps?.find(step => step.step_status === 'running');
            setCurrentStep(runningStep);

            // Update workflow status based on step statuses
            if (fetchedSteps && fetchedSteps.length > 0) {
                const allCompleted = fetchedSteps.every(step => step.step_status === 'completed');
                const anyRunning = fetchedSteps.some(step => step.step_status === 'running');
                const anyFailed = fetchedSteps.some(step => step.step_status === 'failed');

                if (allCompleted) {
                    setWorkflowStatus('completed');
                } else if (anyFailed) {
                    setWorkflowStatus('failed');
                } else if (anyRunning) {
                    setWorkflowStatus('active');
                } else {
                    setWorkflowStatus('draft');
                }
            }

        } catch (error) {
            console.error("Error loading workflow steps:", error);
        } finally {
            setIsLoading(false);
        }
    }, [workflowId]);

    useEffect(() => {
        loadWorkflowSteps();
        const interval = setInterval(loadWorkflowSteps, 5000); // Refresh every 5 seconds
        return () => clearInterval(interval);
    }, [loadWorkflowSteps]);

    useEffect(() => {
        // Simulate real-time collaborators
        const generateCollaborators = () => {
            const mockCollaborators = [
                { id: '1', name: 'Strategic Planning Agent', status: 'active', avatar: 'SP', color: 'bg-blue-500' },
                { id: '2', name: 'Data Analysis Agent', status: 'active', avatar: 'DA', color: 'bg-green-500' },
                { id: '3', name: 'Financial Agent', status: 'idle', avatar: 'FA', color: 'bg-purple-500' },
                { id: '4', name: 'Operations Agent', status: 'working', avatar: 'OA', color: 'bg-orange-500' }
            ];
            setCollaborators(mockCollaborators.filter(c => 
                steps.some(step => step.agent_name === c.name.replace(' Agent', ''))
            ));
        };
        
        if (steps.length > 0) {
            generateCollaborators();
        }
    }, [steps]);

    const getStepStatusIcon = (status) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'running':
                return <PlayCircle className="w-5 h-5 text-blue-500 animate-pulse" />;
            case 'failed':
                return <AlertCircle className="w-5 h-5 text-red-500" />;
            case 'pending':
            default:
                return <Clock className="w-5 h-5 text-gray-400" />;
        }
    };

    const getStepStatusBadge = (status) => {
        const statusConfig = {
            completed: { color: 'bg-green-100 text-green-800', label: 'Completed' },
            running: { color: 'bg-blue-100 text-blue-800', label: 'Running' },
            failed: { color: 'bg-red-100 text-red-800', label: 'Failed' },
            pending: { color: 'bg-gray-100 text-gray-800', label: 'Pending' }
        };
        
        const config = statusConfig[status] || statusConfig.pending;
        return <Badge className={config.color}>{config.label}</Badge>;
    };

    const getCollaboratorStatus = (status) => {
        switch (status) {
            case 'active':
                return <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>;
            case 'working':
                return <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>;
            case 'idle':
            default:
                return <div className="w-3 h-3 bg-gray-300 rounded-full"></div>;
        }
    };

    const calculateProgress = () => {
        if (!steps || steps.length === 0) return 0;
        const completedSteps = steps.filter(step => step.step_status === 'completed').length;
        return Math.round((completedSteps / steps.length) * 100);
    };

    const getEstimatedTimeRemaining = () => {
        const pendingSteps = steps.filter(step => step.step_status === 'pending').length;
        const runningSteps = steps.filter(step => step.step_status === 'running').length;
        
        // Estimate 5-10 minutes per step
        const estimatedMinutes = (pendingSteps * 7) + (runningSteps * 3);
        
        if (estimatedMinutes < 60) {
            return `~${estimatedMinutes} min`;
        } else {
            const hours = Math.floor(estimatedMinutes / 60);
            const minutes = estimatedMinutes % 60;
            return `~${hours}h ${minutes}m`;
        }
    };

    return (
        <div className="space-y-6">
            {/* Workflow Status Header */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Activity className="w-6 h-6 text-blue-600" />
                            <div>
                                <CardTitle className="text-lg">Workflow Collaboration</CardTitle>
                                <CardDescription>Real-time agent coordination and progress tracking</CardDescription>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <Badge 
                                className={
                                    workflowStatus === 'completed' ? 'bg-green-100 text-green-800' :
                                    workflowStatus === 'active' ? 'bg-blue-100 text-blue-800' :
                                    workflowStatus === 'failed' ? 'bg-red-100 text-red-800' :
                                    'bg-gray-100 text-gray-800'
                                }
                            >
                                {workflowStatus.toUpperCase()}
                            </Badge>
                            <div className="text-sm text-gray-600">
                                {calculateProgress()}% Complete
                            </div>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {/* Progress Bar */}
                        <div>
                            <div className="flex justify-between text-sm mb-2">
                                <span>Overall Progress</span>
                                <span>{getEstimatedTimeRemaining()} remaining</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                                <motion.div 
                                    className="bg-blue-600 h-2 rounded-full"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${calculateProgress()}%` }}
                                    transition={{ duration: 0.5 }}
                                />
                            </div>
                        </div>

                        {/* Active Collaborators */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Users className="w-4 h-4 text-gray-500" />
                                <span className="text-sm font-medium">Active Agents:</span>
                            </div>
                            <div className="flex items-center gap-2">
                                {collaborators.map((collaborator) => (
                                    <div key={collaborator.id} className="flex items-center gap-2 px-3 py-1 bg-gray-50 rounded-full">
                                        <Avatar className="w-6 h-6">
                                            <AvatarFallback className={`text-xs text-white ${collaborator.color}`}>
                                                {collaborator.avatar}
                                            </AvatarFallback>
                                        </Avatar>
                                        <span className="text-xs font-medium">{collaborator.name.split(' ')[0]}</span>
                                        {getCollaboratorStatus(collaborator.status)}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Real-time Step Progress */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Agent Execution Timeline</CardTitle>
                    <CardDescription>Live updates from each AI agent in the workflow</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <AnimatePresence>
                            {steps.map((step, index) => (
                                <motion.div
                                    key={step.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.1 }}
                                    className={`flex items-center gap-4 p-4 border rounded-lg ${
                                        step.step_status === 'running' ? 'bg-blue-50 border-blue-200' :
                                        step.step_status === 'completed' ? 'bg-green-50 border-green-200' :
                                        step.step_status === 'failed' ? 'bg-red-50 border-red-200' :
                                        'bg-gray-50 border-gray-200'
                                    }`}
                                >
                                    {/* Step Status Icon */}
                                    <div className="flex-shrink-0">
                                        {getStepStatusIcon(step.step_status)}
                                    </div>

                                    {/* Step Details */}
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between mb-1">
                                            <h4 className="font-medium">
                                                Step {step.step_order}: {step.agent_name} Agent
                                            </h4>
                                            {getStepStatusBadge(step.step_status)}
                                        </div>
                                        
                                        {step.step_prompt && (
                                            <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                                                {step.step_prompt.substring(0, 150)}...
                                            </p>
                                        )}

                                        {/* Execution Details */}
                                        <div className="flex items-center gap-4 text-xs text-gray-500">
                                            {step.execution_time && (
                                                <div className="flex items-center gap-1">
                                                    <Clock className="w-3 h-3" />
                                                    {step.execution_time}s
                                                </div>
                                            )}
                                            
                                            {step.step_status === 'running' && (
                                                <div className="flex items-center gap-1">
                                                    <Zap className="w-3 h-3" />
                                                    Processing...
                                                </div>
                                            )}
                                            
                                            {step.step_status === 'completed' && (
                                                <div className="flex items-center gap-1">
                                                    <CheckCircle className="w-3 h-3" />
                                                    Complete
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Agent Avatar */}
                                    <div className="flex-shrink-0">
                                        <Avatar className="w-10 h-10">
                                            <AvatarFallback className="bg-gradient-to-br from-blue-500 to-purple-600 text-white text-xs">
                                                {step.agent_name.split(' ').map(word => word[0]).join('')}
                                            </AvatarFallback>
                                        </Avatar>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        
                        {steps.length === 0 && !isLoading && (
                            <div className="text-center py-8 text-gray-500">
                                <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                <p>No workflow steps found</p>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Current Step Details */}
            {currentStep && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <Card className="border-blue-200">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <PlayCircle className="w-5 h-5 text-blue-500" />
                                Currently Executing: {currentStep.agent_name} Agent
                            </CardTitle>
                            <CardDescription>Real-time execution details</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                <div>
                                    <h4 className="font-medium mb-1">Step Objective:</h4>
                                    <p className="text-sm text-gray-600">{currentStep.step_prompt}</p>
                                </div>
                                
                                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                                        <span className="text-sm font-medium">Agent is working...</span>
                                    </div>
                                    <div className="text-xs text-blue-600">
                                        Step {currentStep.step_order} of {steps.length}
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>
            )}
        </div>
    );
}