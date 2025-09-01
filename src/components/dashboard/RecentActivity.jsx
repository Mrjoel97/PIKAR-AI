import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AuditLog } from '@/api/entities';
import { 
    Bot, 
    FileUp, 
    Settings, 
    Shield, 
    Network, 
    BarChart, 
    Clock,
    CheckCircle,
    AlertTriangle
} from 'lucide-react';

const getActionIcon = (actionType) => {
    switch (actionType) {
        case 'agent_execution': return Bot;
        case 'workflow_execution': return Network;
        case 'file_upload': return FileUp;
        case 'compliance_check': return Shield;
        case 'data_access': return BarChart;
        case 'settings_change': return Settings;
        default: return Clock;
    }
};

const getActivityColor = (actionType, success) => {
    if (!success) return 'text-red-600 bg-red-50';
    
    switch (actionType) {
        case 'agent_execution': return 'text-blue-600 bg-blue-50';
        case 'workflow_execution': return 'text-purple-600 bg-purple-50';
        case 'file_upload': return 'text-green-600 bg-green-50';
        case 'compliance_check': return 'text-orange-600 bg-orange-50';
        case 'data_access': return 'text-indigo-600 bg-indigo-50';
        case 'settings_change': return 'text-gray-600 bg-gray-50';
        default: return 'text-gray-600 bg-gray-50';
    }
};

export default function RecentActivity() {
    const [activities, setActivities] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadRecentActivity();
    }, []);

    const loadRecentActivity = async () => {
        try {
            const auditLogs = await AuditLog.list('-created_date', 8);
            setActivities(auditLogs);
        } catch (error) {
            console.error("Failed to load recent activity:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const formatActivityDescription = (log) => {
        const { action_type, agent_name, action_details } = log;
        
        switch (action_type) {
            case 'agent_execution':
                return `${agent_name} completed ${action_details?.analysis_type || 'analysis'}`;
            case 'workflow_execution':
                return `Workflow "${action_details?.workflow_name}" executed`;
            case 'file_upload':
                return `Uploaded ${action_details?.file_name}`;
            case 'compliance_check':
                return `${action_details?.compliance_area} compliance check completed`;
            case 'data_access':
                return `Processed ${action_details?.records_processed?.toLocaleString()} records`;
            case 'settings_change':
                return `Modified ${action_details?.setting} setting`;
            default:
                return `${action_type.replace(/_/g, ' ')} completed`;
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Latest AI agent interactions and system events</CardDescription>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="space-y-3">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <div key={i} className="animate-pulse">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 bg-gray-200 rounded-full" />
                                    <div className="flex-1">
                                        <div className="h-4 bg-gray-200 rounded w-3/4" />
                                        <div className="h-3 bg-gray-200 rounded w-1/2 mt-1" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="space-y-4">
                        {activities.map((activity, index) => {
                            const Icon = getActionIcon(activity.action_type);
                            const colorClass = getActivityColor(activity.action_type, activity.success);
                            
                            return (
                                <div key={index} className="flex items-start gap-3">
                                    <div className={`p-2 rounded-full ${colorClass}`}>
                                        <Icon className="w-4 h-4" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                                            {formatActivityDescription(activity)}
                                        </p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                                {new Date(activity.created_date).toLocaleTimeString()}
                                            </p>
                                            {activity.success ? (
                                                <CheckCircle className="w-3 h-3 text-green-500" />
                                            ) : (
                                                <AlertTriangle className="w-3 h-3 text-red-500" />
                                            )}
                                            <Badge variant="outline" className="text-xs">
                                                {activity.risk_level}
                                            </Badge>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}