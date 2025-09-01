import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
    TrendingUp, AlertTriangle, Clock, DollarSign, Users, Target, 
    Zap, CheckCircle, ArrowRight, BarChart3, Calendar, FileText
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';

const businessBottlenecks = [
    {
        id: 'cash-flow',
        title: 'Cash Flow Management',
        severity: 'high',
        impact: '67% of SMEs struggle with cash flow',
        solution: 'AI Financial Forecasting',
        agent: 'Financial Analysis',
        actionUrl: 'FinancialAnalysis',
        timeToSolve: '2 hours',
        roi: '+23% cash flow optimization'
    },
    {
        id: 'lead-conversion',
        title: 'Low Lead Conversion',
        severity: 'high',
        impact: 'Only 2.35% website visitors convert',
        solution: 'Sales Intelligence Optimization',
        agent: 'Sales Intelligence',
        actionUrl: 'SalesIntelligence',
        timeToSolve: '3 hours',
        roi: '+15% conversion rate'
    },
    {
        id: 'operational-inefficiency',
        title: 'Process Inefficiencies',
        severity: 'medium',
        impact: '40% time lost on manual tasks',
        solution: 'Operations Optimization',
        agent: 'Operations Optimization',
        actionUrl: 'OperationsOptimization',
        timeToSolve: '4 hours',
        roi: '+35% efficiency gain'
    },
    {
        id: 'marketing-reach',
        title: 'Limited Marketing Reach',
        severity: 'medium',
        impact: 'Marketing ROI below industry average',
        solution: 'Marketing Automation',
        agent: 'Marketing Automation',
        actionUrl: 'MarketingAutomation',
        timeToSolve: '2.5 hours',
        roi: '+28% marketing ROI'
    },
    {
        id: 'customer-retention',
        title: 'Customer Retention Issues',
        severity: 'high',
        impact: '68% customer lifetime value loss',
        solution: 'Customer Support Intelligence',
        agent: 'Customer Support',
        actionUrl: 'CustomerSupport',
        timeToSolve: '1.5 hours',
        roi: '+45% retention rate'
    }
];

const quickWins = [
    {
        title: 'Automated Invoice Processing',
        description: 'Reduce invoice processing time by 85%',
        effort: 'Low',
        impact: 'High',
        timeframe: '1 day',
        workflow: 'CreateWorkflow'
    },
    {
        title: 'Customer Feedback Analysis',
        description: 'Turn customer feedback into actionable insights',
        effort: 'Medium',
        impact: 'High',
        timeframe: '2 days',
        workflow: 'CreateWorkflow'
    },
    {
        title: 'Competitor Price Monitoring',
        description: 'Stay competitive with automated price tracking',
        effort: 'Low',
        impact: 'Medium',
        timeframe: '3 hours',
        workflow: 'CreateWorkflow'
    }
];

const getSeverityColor = (severity) => {
    switch (severity) {
        case 'high': return 'bg-red-100 text-red-800';
        case 'medium': return 'bg-yellow-100 text-yellow-800';
        case 'low': return 'bg-green-100 text-green-800';
        default: return 'bg-gray-100 text-gray-800';
    }
};

const getEffortColor = (effort) => {
    switch (effort) {
        case 'Low': return 'bg-green-100 text-green-800';
        case 'Medium': return 'bg-yellow-100 text-yellow-800';
        case 'High': return 'bg-red-100 text-red-800';
        default: return 'bg-gray-100 text-gray-800';
    }
};

export default function SMEBusinessSolutions() {
    const [activeTab, setActiveTab] = useState('bottlenecks');

    return (
        <Card className="col-span-full">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Target className="w-6 h-6 text-purple-600" />
                    SME Business Solutions Center
                </CardTitle>
            </CardHeader>
            <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="bottlenecks">Critical Bottlenecks</TabsTrigger>
                        <TabsTrigger value="quick-wins">Quick Wins</TabsTrigger>
                        <TabsTrigger value="recommendations">AI Recommendations</TabsTrigger>
                    </TabsList>

                    <TabsContent value="bottlenecks" className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {businessBottlenecks.map((bottleneck, index) => (
                                <motion.div
                                    key={bottleneck.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.1 }}
                                >
                                    <Card className="hover:shadow-md transition-shadow">
                                        <CardContent className="p-4">
                                            <div className="flex justify-between items-start mb-3">
                                                <h4 className="font-semibold text-lg">{bottleneck.title}</h4>
                                                <Badge className={getSeverityColor(bottleneck.severity)}>
                                                    {bottleneck.severity}
                                                </Badge>
                                            </div>
                                            <p className="text-sm text-gray-600 mb-2">{bottleneck.impact}</p>
                                            <div className="space-y-2 mb-4">
                                                <div className="flex justify-between text-sm">
                                                    <span>Solution: {bottleneck.solution}</span>
                                                    <span className="text-green-600">{bottleneck.roi}</span>
                                                </div>
                                                <div className="flex justify-between text-xs text-gray-500">
                                                    <span>Time to solve: {bottleneck.timeToSolve}</span>
                                                    <span>Agent: {bottleneck.agent}</span>
                                                </div>
                                            </div>
                                            <Link to={createPageUrl(bottleneck.actionUrl)}>
                                                <Button className="w-full bg-purple-600 hover:bg-purple-700">
                                                    <Zap className="w-4 h-4 mr-2" />
                                                    Solve Now
                                                </Button>
                                            </Link>
                                        </CardContent>
                                    </Card>
                                </motion.div>
                            ))}
                        </div>
                    </TabsContent>

                    <TabsContent value="quick-wins" className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {quickWins.map((win, index) => (
                                <Card key={index} className="hover:shadow-md transition-shadow">
                                    <CardContent className="p-4">
                                        <h4 className="font-semibold mb-2">{win.title}</h4>
                                        <p className="text-sm text-gray-600 mb-3">{win.description}</p>
                                        <div className="flex gap-2 mb-4">
                                            <Badge className={getEffortColor(win.effort)}>
                                                {win.effort} Effort
                                            </Badge>
                                            <Badge className="bg-blue-100 text-blue-800">
                                                {win.impact} Impact
                                            </Badge>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm text-gray-500">
                                                <Clock className="w-3 h-3 inline mr-1" />
                                                {win.timeframe}
                                            </span>
                                            <Link to={createPageUrl(win.workflow)}>
                                                <Button size="sm">
                                                    Create Workflow
                                                </Button>
                                            </Link>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </TabsContent>

                    <TabsContent value="recommendations" className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
                                <CardContent className="p-6">
                                    <h4 className="font-semibold text-lg mb-2 flex items-center gap-2">
                                        <BarChart3 className="w-5 h-5 text-blue-600" />
                                        Revenue Optimization
                                    </h4>
                                    <p className="text-sm text-gray-700 mb-4">
                                        Based on your data, you could increase revenue by 23% in the next quarter.
                                    </p>
                                    <div className="space-y-2 mb-4">
                                        <div className="flex justify-between text-sm">
                                            <span>Current Revenue Growth</span>
                                            <span className="font-semibold">12%</span>
                                        </div>
                                        <Progress value={12} className="h-2" />
                                    </div>
                                    <Button className="w-full bg-blue-600 hover:bg-blue-700">
                                        View Revenue Strategy
                                    </Button>
                                </CardContent>
                            </Card>

                            <Card className="bg-gradient-to-br from-green-50 to-green-100">
                                <CardContent className="p-6">
                                    <h4 className="font-semibold text-lg mb-2 flex items-center gap-2">
                                        <Users className="w-5 h-5 text-green-600" />
                                        Team Productivity
                                    </h4>
                                    <p className="text-sm text-gray-700 mb-4">
                                        Optimize team workflows and reduce task completion time by 35%.
                                    </p>
                                    <div className="space-y-2 mb-4">
                                        <div className="flex justify-between text-sm">
                                            <span>Current Efficiency</span>
                                            <span className="font-semibold">68%</span>
                                        </div>
                                        <Progress value={68} className="h-2" />
                                    </div>
                                    <Button className="w-full bg-green-600 hover:bg-green-700">
                                        Optimize Workflows
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
}