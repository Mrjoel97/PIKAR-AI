
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Settings, Zap, CheckCircle, Clock, BarChart3, Cog, RefreshCw, Plus } from 'lucide-react';

const automationRules = [
    {
        id: 1,
        name: 'Document Review Alerts',
        description: 'Automatically notify owners when documents need review',
        status: 'active',
        trigger: 'Review due date approaching',
        action: 'Send email notification',
        lastRun: '2 hours ago',
        successRate: 98
    },
    {
        id: 2,
        name: 'Compliance Score Monitoring',
        description: 'Monitor compliance scores and trigger alerts for low scores',
        status: 'active',
        trigger: 'Compliance score < 80%',
        action: 'Create corrective action',
        lastRun: '6 hours ago',
        successRate: 95
    },
    {
        id: 3,
        name: 'Overdue Action Escalation',
        description: 'Escalate overdue corrective actions to management',
        status: 'active',
        trigger: 'Action overdue by 3+ days',
        action: 'Escalate to manager',
        lastRun: '1 day ago',
        successRate: 92
    },
    {
        id: 4,
        name: 'Training Reminder System',
        description: 'Remind employees of upcoming training requirements',
        status: 'inactive',
        trigger: 'Training due in 7 days',
        action: 'Send training reminder',
        lastRun: 'Never',
        successRate: 0
    }
];

export default function ProcessAutomation() {
    const [rules, setRules] = useState(automationRules);

    const toggleRule = (ruleId) => {
        setRules(rules.map(rule => 
            rule.id === ruleId 
                ? { ...rule, status: rule.status === 'active' ? 'inactive' : 'active' }
                : rule
        ));
    };

    const getStatusColor = (status) => {
        return status === 'active' 
            ? 'bg-green-100 text-green-800' 
            : 'bg-gray-100 text-gray-800';
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <Settings className="w-6 h-6 text-blue-600" />
                        <div>
                            <CardTitle>Process Automation Rules</CardTitle>
                            <CardDescription>
                                Automated workflows for quality management processes
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {rules.map(rule => (
                            <div key={rule.id} className="p-4 border rounded-lg">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-3 mb-2">
                                            <h3 className="font-semibold">{rule.name}</h3>
                                            <Badge className={getStatusColor(rule.status)}>
                                                {rule.status === 'active' ? (
                                                    <CheckCircle className="w-3 h-3 mr-1" />
                                                ) : (
                                                    <Clock className="w-3 h-3 mr-1" />
                                                )}
                                                {rule.status}
                                            </Badge>
                                        </div>
                                        <p className="text-gray-600 mb-3">{rule.description}</p>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                                            <div>
                                                <span className="font-medium">Trigger:</span> {rule.trigger}
                                            </div>
                                            <div>
                                                <span className="font-medium">Action:</span> {rule.action}
                                            </div>
                                            <div>
                                                <span className="font-medium">Last Run:</span> {rule.lastRun}
                                            </div>
                                        </div>
                                        {rule.status === 'active' && (
                                            <div className="mt-3 flex items-center gap-2">
                                                <span className="text-sm text-gray-500">Success Rate:</span>
                                                <Progress value={rule.successRate} className="w-24 h-2" />
                                                <span className="text-sm font-medium">{rule.successRate}%</span>
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex gap-2">
                                        <Button 
                                            variant="outline" 
                                            size="sm"
                                            onClick={() => toggleRule(rule.id)}
                                        >
                                            {rule.status === 'active' ? 'Disable' : 'Enable'}
                                        </Button>
                                        <Button variant="ghost" size="sm">
                                            <Cog className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Zap className="w-5 h-5 text-yellow-500" />
                            Automation Stats
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex justify-between">
                            <span>Active Rules</span>
                            <span className="font-bold">{rules.filter(r => r.status === 'active').length}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Avg Success Rate</span>
                            <span className="font-bold">95.2%</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Time Saved</span>
                            <span className="font-bold">12.5 hrs/week</span>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-blue-500" />
                            Performance
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex justify-between">
                            <span>Executions Today</span>
                            <span className="font-bold">47</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Errors</span>
                            <span className="font-bold text-red-600">2</span>
                        </div>
                        <div className="flex justify-between">
                            <span>System Health</span>
                            <Badge className="bg-green-100 text-green-800">Healthy</Badge>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <RefreshCw className="w-5 h-5 text-purple-500" />
                            Quick Actions
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <Button variant="outline" className="w-full justify-start">
                            <Plus className="w-4 h-4 mr-2" />
                            Create New Rule
                        </Button>
                        <Button variant="outline" className="w-full justify-start">
                            <BarChart3 className="w-4 h-4 mr-2" />
                            View Analytics
                        </Button>
                        <Button variant="outline" className="w-full justify-start">
                            <Settings className="w-4 h-4 mr-2" />
                            System Settings
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
