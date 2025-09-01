import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { TrendingUp, DollarSign, Users, Target, BarChart, Clock } from 'lucide-react';
import { motion } from 'framer-motion';

const metrics = [
    {
        title: 'Business Validation Score',
        value: 67,
        target: 85,
        icon: Target,
        color: 'text-blue-500',
        bgColor: 'bg-blue-50',
        trend: '+12%',
        description: 'How well your idea fits the market'
    },
    {
        title: 'Content Consistency',
        value: 45,
        target: 70,
        icon: BarChart,
        color: 'text-green-500',
        bgColor: 'bg-green-50',
        trend: '+8%',
        description: 'Regular content creation progress'
    },
    {
        title: 'Time to Launch',
        value: 30,
        target: 100,
        icon: Clock,
        color: 'text-orange-500',
        bgColor: 'bg-orange-50',
        trend: '+15%',
        description: 'Progress towards launch readiness'
    }
];

const milestones = [
    { title: 'Business Plan Created', completed: true, date: '2024-01-15' },
    { title: 'Market Research Done', completed: true, date: '2024-01-18' },
    { title: 'Content Strategy Set', completed: false, date: 'In Progress' },
    { title: 'MVP Development', completed: false, date: 'Upcoming' },
    { title: 'First Customer', completed: false, date: 'Goal: Q2 2024' },
];

export default function SolopreneurMetrics() {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-6 h-6 text-blue-600" />
                    Your Progress Metrics
                </CardTitle>
                <CardDescription>Track your solopreneur journey milestones</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Key Metrics */}
                <div className="space-y-4">
                    {metrics.map((metric, index) => {
                        const Icon = metric.icon;
                        const progressPercentage = (metric.value / metric.target) * 100;
                        
                        return (
                            <motion.div
                                key={metric.title}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="space-y-2"
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-8 h-8 ${metric.bgColor} rounded-lg flex items-center justify-center`}>
                                            <Icon className={`w-4 h-4 ${metric.color}`} />
                                        </div>
                                        <div>
                                            <p className="font-medium text-sm">{metric.title}</p>
                                            <p className="text-xs text-gray-500">{metric.description}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-semibold">{metric.value}/{metric.target}</p>
                                        <Badge variant="outline" className="text-green-600">
                                            {metric.trend}
                                        </Badge>
                                    </div>
                                </div>
                                <Progress value={progressPercentage} className="h-2" />
                            </motion.div>
                        );
                    })}
                </div>

                {/* Milestones */}
                <div>
                    <h4 className="font-semibold mb-3">Business Milestones</h4>
                    <div className="space-y-3">
                        {milestones.map((milestone, index) => (
                            <motion.div
                                key={milestone.title}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.3 + index * 0.1 }}
                                className="flex items-center gap-3"
                            >
                                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                    milestone.completed 
                                        ? 'bg-green-500 border-green-500' 
                                        : 'border-gray-300'
                                }`}>
                                    {milestone.completed && (
                                        <div className="w-2 h-2 bg-white rounded-full" />
                                    )}
                                </div>
                                <div className="flex-1">
                                    <p className={`text-sm font-medium ${
                                        milestone.completed ? 'text-gray-900' : 'text-gray-500'
                                    }`}>
                                        {milestone.title}
                                    </p>
                                    <p className="text-xs text-gray-400">{milestone.date}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Success Tip */}
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-sm text-blue-800">
                        <strong>💡 Pro Tip:</strong> Focus on validation before building. 
                        Use the Strategic Planning Agent to test your assumptions!
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}