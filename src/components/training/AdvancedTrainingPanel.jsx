
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AgentTrainingSession } from '@/api/entities';
import { 
    Brain, 
    BarChart3, 
    Clock, 
    CheckCircle, 
    AlertCircle, 
    TrendingUp,
    Zap,
    FileText,
    Loader2,
    Play,
    Pause,
    RotateCcw,
    Eye
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { format, parseISO } from 'date-fns';
import { toast } from 'sonner';

export default function AdvancedTrainingPanel({ agentId, agentName }) {
    const [trainingSessions, setTrainingSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedSession, setSelectedSession] = useState(null);
    const [isTraining, setIsTraining] = useState(false);

    const loadTrainingSessions = useCallback(async () => {
        setIsLoading(true);
        try {
            const sessions = await AgentTrainingSession.list('-created_date');
            const agentSessions = sessions.filter(s => s.agent_id === agentId);
            
            // Add mock performance metrics for demo
            const sessionsWithMetrics = agentSessions.map(session => ({
                ...session,
                performance_metrics: session.performance_metrics || {
                    accuracy_score: Math.random() * 0.3 + 0.7, // 70-100%
                    response_quality: Math.random() * 2 + 3, // 3-5 rating
                    training_loss: Math.random() * 0.5 + 0.1, // 0.1-0.6
                    validation_score: Math.random() * 0.2 + 0.8 // 80-100%
                },
                training_duration: session.training_duration || Math.floor(Math.random() * 300) + 60
            }));
            
            setTrainingSessions(sessionsWithMetrics);
        } catch (error) {
            console.error('Failed to load training sessions:', error);
            toast.error('Failed to load training data');
        } finally {
            setIsLoading(false);
        }
    }, [agentId]); // agentId is a dependency for filtering sessions

    const updateTrainingProgress = async () => {
        // Simulate progress updates for active training sessions
        setTrainingSessions(prev => prev.map(session => {
            if (session.training_status === 'processing') {
                const currentProgress = session.progress || 0;
                const newProgress = Math.min(currentProgress + Math.random() * 15, 100);
                
                // Complete session when progress reaches 100%
                if (newProgress >= 100) {
                    return {
                        ...session,
                        training_status: 'completed',
                        progress: 100,
                        performance_metrics: {
                            ...session.performance_metrics,
                            accuracy_score: Math.random() * 0.2 + 0.8,
                            response_quality: Math.random() * 1 + 4,
                            training_loss: Math.random() * 0.3 + 0.1,
                            validation_score: Math.random() * 0.15 + 0.85
                        }
                    };
                }
                
                return { ...session, progress: newProgress };
            }
            return session;
        }));
    };

    useEffect(() => {
        loadTrainingSessions();
        
        // Simulate real-time updates for training sessions
        const interval = setInterval(() => {
            updateTrainingProgress();
        }, 3000);

        return () => clearInterval(interval);
    }, [loadTrainingSessions]); // loadTrainingSessions is a dependency

    const startTrainingSession = async () => {
        setIsTraining(true);
        try {
            const newSession = await AgentTrainingSession.create({
                agent_id: agentId,
                training_type: 'continuous_learning',
                training_source: 'User feedback and interaction logs',
                training_content: 'Automated training based on recent interactions',
                training_parameters: {
                    learning_rate: 0.001,
                    batch_size: 32,
                    epochs: 10,
                    optimization_method: 'adaptive'
                },
                training_status: 'processing'
            });

            setTrainingSessions(prev => [{ ...newSession, progress: 0 }, ...prev]);
            toast.success('Training session started!');
        } catch (error) {
            console.error('Failed to start training:', error);
            toast.error('Failed to start training session');
        } finally {
            setIsTraining(false);
        }
    };

    const getStatusColor = (status) => {
        const colors = {
            'queued': 'bg-yellow-100 text-yellow-800',
            'processing': 'bg-blue-100 text-blue-800',
            'completed': 'bg-green-100 text-green-800',
            'failed': 'bg-red-100 text-red-800'
        };
        return colors[status] || 'bg-gray-100 text-gray-800';
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'completed': return <CheckCircle className="w-4 h-4" />;
            case 'processing': return <Loader2 className="w-4 h-4 animate-spin" />;
            case 'failed': return <AlertCircle className="w-4 h-4" />;
            default: return <Clock className="w-4 h-4" />;
        }
    };

    const calculateOverallMetrics = () => {
        const completedSessions = trainingSessions.filter(s => s.training_status === 'completed');
        if (completedSessions.length === 0) return null;

        return {
            avgAccuracy: (completedSessions.reduce((sum, s) => sum + s.performance_metrics.accuracy_score, 0) / completedSessions.length * 100).toFixed(1),
            avgQuality: (completedSessions.reduce((sum, s) => sum + s.performance_metrics.response_quality, 0) / completedSessions.length).toFixed(1),
            totalSessions: trainingSessions.length,
            successRate: ((completedSessions.length / trainingSessions.length) * 100).toFixed(1)
        };
    };

    const performanceData = trainingSessions
        .filter(s => s.training_status === 'completed')
        .slice(0, 10)
        .reverse()
        .map((session, index) => ({
            session: `S${index + 1}`,
            accuracy: (session.performance_metrics.accuracy_score * 100).toFixed(1),
            quality: session.performance_metrics.response_quality,
            loss: session.performance_metrics.training_loss
        }));

    const overallMetrics = calculateOverallMetrics();

    return (
        <div className="space-y-6">
            
            {/* Header with Start Training */}
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Brain className="w-5 h-5 text-purple-600" />
                        Training Monitor: {agentName}
                    </h3>
                    <p className="text-sm text-gray-600">Monitor and manage agent training progress</p>
                </div>
                <Button 
                    onClick={startTrainingSession}
                    disabled={isTraining || trainingSessions.some(s => s.training_status === 'processing')}
                    className="bg-purple-600 hover:bg-purple-700"
                >
                    {isTraining ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                        <Play className="w-4 h-4 mr-2" />
                    )}
                    Start Training
                </Button>
            </div>

            {/* Overall Performance Metrics */}
            {overallMetrics && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Card>
                        <CardContent className="p-4 text-center">
                            <div className="text-2xl font-bold text-green-600">{overallMetrics.avgAccuracy}%</div>
                            <div className="text-sm text-gray-600">Avg Accuracy</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-4 text-center">
                            <div className="text-2xl font-bold text-blue-600">{overallMetrics.avgQuality}/5</div>
                            <div className="text-sm text-gray-600">Avg Quality</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-4 text-center">
                            <div className="text-2xl font-bold text-purple-600">{overallMetrics.totalSessions}</div>
                            <div className="text-sm text-gray-600">Total Sessions</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-4 text-center">
                            <div className="text-2xl font-bold text-indigo-600">{overallMetrics.successRate}%</div>
                            <div className="text-sm text-gray-600">Success Rate</div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Training Analytics */}
            <Tabs defaultValue="sessions" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="sessions">Training Sessions</TabsTrigger>
                    <TabsTrigger value="performance">Performance Trends</TabsTrigger>
                    <TabsTrigger value="details">Session Details</TabsTrigger>
                </TabsList>

                <TabsContent value="sessions" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Training Sessions</CardTitle>
                            <CardDescription>Monitor active and completed training sessions</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <div className="flex items-center justify-center h-32">
                                    <Loader2 className="w-6 h-6 animate-spin" />
                                </div>
                            ) : trainingSessions.length === 0 ? (
                                <div className="text-center py-8 text-gray-500">
                                    <Brain className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p>No training sessions yet</p>
                                    <p className="text-sm">Start a training session to see progress here</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {trainingSessions.slice(0, 5).map(session => (
                                        <div 
                                            key={session.id} 
                                            className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                                                selectedSession?.id === session.id ? 'border-purple-500 bg-purple-50' : 'hover:bg-gray-50'
                                            }`}
                                            onClick={() => setSelectedSession(session)}
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-3">
                                                    {getStatusIcon(session.training_status)}
                                                    <div>
                                                        <div className="font-medium">{session.training_type.replace(/_/g, ' ')}</div>
                                                        <div className="text-sm text-gray-500">
                                                            {format(parseISO(session.created_date), 'MMM d, HH:mm')}
                                                        </div>
                                                    </div>
                                                </div>
                                                <Badge className={getStatusColor(session.training_status)}>
                                                    {session.training_status}
                                                </Badge>
                                            </div>

                                            {session.training_status === 'processing' && (
                                                <div className="space-y-2">
                                                    <div className="flex justify-between text-sm">
                                                        <span>Progress</span>
                                                        <span>{Math.round(session.progress || 0)}%</span>
                                                    </div>
                                                    <Progress value={session.progress || 0} />
                                                </div>
                                            )}

                                            {session.training_status === 'completed' && session.performance_metrics && (
                                                <div className="grid grid-cols-3 gap-4 text-sm">
                                                    <div>
                                                        <div className="text-gray-500">Accuracy</div>
                                                        <div className="font-medium">{(session.performance_metrics.accuracy_score * 100).toFixed(1)}%</div>
                                                    </div>
                                                    <div>
                                                        <div className="text-gray-500">Quality</div>
                                                        <div className="font-medium">{session.performance_metrics.response_quality.toFixed(1)}/5</div>
                                                    </div>
                                                    <div>
                                                        <div className="text-gray-500">Duration</div>
                                                        <div className="font-medium">{session.training_duration}s</div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="performance">
                    <Card>
                        <CardHeader>
                            <CardTitle>Performance Trends</CardTitle>
                            <CardDescription>Track agent improvement over time</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {performanceData.length > 0 ? (
                                <div className="space-y-6">
                                    <div className="h-64">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={performanceData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="session" />
                                                <YAxis />
                                                <Tooltip />
                                                <Line 
                                                    type="monotone" 
                                                    dataKey="accuracy" 
                                                    stroke="#10B981" 
                                                    strokeWidth={2}
                                                    name="Accuracy %" 
                                                />
                                                <Line 
                                                    type="monotone" 
                                                    dataKey="quality" 
                                                    stroke="#3B82F6" 
                                                    strokeWidth={2}
                                                    name="Quality Score" 
                                                />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>

                                    <div className="h-64">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart data={performanceData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="session" />
                                                <YAxis />
                                                <Tooltip />
                                                <Bar dataKey="loss" fill="#EF4444" name="Training Loss" />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-8 text-gray-500">
                                    <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p>No performance data available</p>
                                    <p className="text-sm">Complete some training sessions to see trends</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="details">
                    {selectedSession ? (
                        <Card>
                            <CardHeader>
                                <CardTitle>Session Details</CardTitle>
                                <CardDescription>
                                    Detailed information for training session {selectedSession.id}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <h4 className="font-medium mb-2">Training Configuration</h4>
                                        <div className="space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Type:</span>
                                                <span>{selectedSession.training_type}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Learning Rate:</span>
                                                <span>{selectedSession.training_parameters?.learning_rate}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Batch Size:</span>
                                                <span>{selectedSession.training_parameters?.batch_size}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                    <span className="text-gray-600">Epochs:</span>
                                                    <span>{selectedSession.training_parameters?.epochs}</span>
                                            </div>
                                        </div>
                                    </div>

                                    {selectedSession.performance_metrics && (
                                        <div>
                                            <h4 className="font-medium mb-2">Performance Metrics</h4>
                                            <div className="space-y-2 text-sm">
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Accuracy Score:</span>
                                                    <Badge className="bg-green-100 text-green-800">
                                                        {(selectedSession.performance_metrics.accuracy_score * 100).toFixed(1)}%
                                                    </Badge>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Response Quality:</span>
                                                    <Badge className="bg-blue-100 text-blue-800">
                                                        {selectedSession.performance_metrics.response_quality.toFixed(1)}/5
                                                    </Badge>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Training Loss:</span>
                                                    <Badge className="bg-yellow-100 text-yellow-800">
                                                        {selectedSession.performance_metrics.training_loss.toFixed(3)}
                                                    </Badge>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Validation Score:</span>
                                                    <Badge className="bg-purple-100 text-purple-800">
                                                        {(selectedSession.performance_metrics.validation_score * 100).toFixed(1)}%
                                                    </Badge>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div>
                                    <h4 className="font-medium mb-2">Training Source</h4>
                                    <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                                        {selectedSession.training_source}
                                    </p>
                                </div>

                                {selectedSession.training_content && (
                                    <div>
                                        <h4 className="font-medium mb-2">Training Content</h4>
                                        <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded max-h-32 overflow-y-auto">
                                            {selectedSession.training_content}
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    ) : (
                        <Card>
                            <CardContent className="text-center py-12">
                                <Eye className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                                <p className="text-gray-500">Select a training session to view details</p>
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
