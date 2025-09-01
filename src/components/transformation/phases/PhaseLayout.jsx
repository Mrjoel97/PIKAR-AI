import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle, Clock, Target, AlertTriangle } from 'lucide-react';

export default function PhaseLayout({ 
    phase, 
    deliverables = [], 
    criteria = [], 
    progress = 0,
    children,
    onDeliverableClick
}) {
    const getStatusColor = (status) => {
        switch (status) {
            case 'Completed': return 'bg-green-100 text-green-800';
            case 'In Progress': return 'bg-blue-100 text-blue-800';
            case 'Pending': return 'bg-gray-100 text-gray-800';
            case 'Approved': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getCriteriaStatus = (current, target) => {
        const percentage = (current / target) * 100;
        if (percentage >= 100) return { color: 'text-green-600', icon: CheckCircle };
        if (percentage >= 80) return { color: 'text-blue-600', icon: Clock };
        if (percentage >= 60) return { color: 'text-yellow-600', icon: AlertTriangle };
        return { color: 'text-red-600', icon: AlertTriangle };
    };

    return (
        <div className="space-y-6">
            {/* Phase Header */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-3">
                            <Target className="w-6 h-6 text-blue-600" />
                            {phase}
                        </CardTitle>
                        <Badge variant="outline" className="px-3 py-1">
                            {Math.round(progress)}% Complete
                        </Badge>
                    </div>
                    <Progress value={progress} className="mt-4" />
                </CardHeader>
            </Card>

            {/* Main Content */}
            {children}

            {/* Phase Status Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Deliverables */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Phase Deliverables</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {deliverables.map((deliverable, index) => (
                                <div 
                                    key={index} 
                                    className={`p-3 border rounded-lg transition-colors ${
                                        onDeliverableClick ? 'cursor-pointer hover:bg-gray-50' : ''
                                    }`}
                                    onClick={() => onDeliverableClick && onDeliverableClick(deliverable)}
                                >
                                    <div className="flex items-center justify-between">
                                        <h3 className="font-medium text-sm">{deliverable.deliverable_name}</h3>
                                        <Badge className={getStatusColor(deliverable.status)}>
                                            {deliverable.status}
                                        </Badge>
                                    </div>
                                    {deliverable.content && (
                                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                            {deliverable.content.substring(0, 100)}...
                                        </p>
                                    )}
                                    <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                                        <span>Type: {deliverable.deliverable_type}</span>
                                        {deliverable.created_date && (
                                            <span>{new Date(deliverable.created_date).toLocaleDateString()}</span>
                                        )}
                                    </div>
                                </div>
                            ))}
                            {deliverables.length === 0 && (
                                <div className="text-center py-8 text-gray-500">
                                    <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">No deliverables found for this phase</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Success Criteria */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Success Criteria</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {criteria.map((criterion, index) => {
                                const status = getCriteriaStatus(criterion.current, criterion.target);
                                const StatusIcon = status.icon;
                                
                                return (
                                    <div key={index} className="p-3 border rounded-lg">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium">{criterion.name}</span>
                                            <StatusIcon className={`w-4 h-4 ${status.color}`} />
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <Progress 
                                                value={(criterion.current / criterion.target) * 100} 
                                                className="flex-1 mr-3 h-2" 
                                            />
                                            <span className={`text-sm font-medium ${status.color}`}>
                                                {Math.round(criterion.current)}/{criterion.target}%
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                            {criteria.length === 0 && (
                                <div className="text-center py-8 text-gray-500">
                                    <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">No success criteria defined for this phase</p>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}