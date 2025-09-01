import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BarChart3, TrendingUp, TrendingDown, Filter, Users, DollarSign, Target, Zap } from 'lucide-react';
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, CartesianGrid, Line, LineChart, Area, AreaChart } from 'recharts';
import { motion } from 'framer-motion';

const weeklyData = [
    { name: 'Week 1', leads: 32, conversion: 2.1, revenue: 1200, cac: 45 },
    { name: 'Week 2', leads: 45, conversion: 2.5, revenue: 1850, cac: 42 },
    { name: 'Week 3', leads: 58, conversion: 3.1, revenue: 2400, cac: 38 },
    { name: 'Week 4', leads: 72, conversion: 3.5, revenue: 3200, cac: 35 },
];

const keyMetrics = [
    {
        title: 'Lead Velocity',
        value: '18%',
        change: '+12%',
        trend: 'up',
        icon: TrendingUp,
        color: 'text-green-600',
        bgColor: 'bg-green-50',
        description: 'Weekly lead generation growth'
    },
    {
        title: 'Conversion Rate',
        value: '3.5%',
        change: '+0.4%',
        trend: 'up',
        icon: Target,
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
        description: 'Visitor to customer conversion'
    },
    {
        title: 'Customer CAC',
        value: '$35',
        change: '-$10',
        trend: 'up',
        icon: DollarSign,
        color: 'text-purple-600',
        bgColor: 'bg-purple-50',
        description: 'Customer acquisition cost'
    },
    {
        title: 'Monthly ARR',
        value: '$12.4K',
        change: '+$2.1K',
        trend: 'up',
        icon: Zap,
        color: 'text-orange-600',
        bgColor: 'bg-orange-50',
        description: 'Annual recurring revenue (monthly)'
    }
];

const chartTypes = [
    { id: 'bar', name: 'Bar Chart', icon: BarChart3 },
    { id: 'line', name: 'Line Chart', icon: TrendingUp },
    { id: 'area', name: 'Area Chart', icon: Filter }
];

export default function KeyMetricsTracker() {
    const [selectedChart, setSelectedChart] = useState('bar');
    const [selectedMetric, setSelectedMetric] = useState('leads');

    const renderChart = () => {
        const commonProps = {
            width: "100%",
            height: 200,
            data: weeklyData,
            margin: { top: 5, right: 30, left: 20, bottom: 5 }
        };

        switch (selectedChart) {
            case 'line':
                return (
                    <ResponsiveContainer {...commonProps}>
                        <LineChart data={weeklyData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" fontSize={12} />
                            <YAxis yAxisId="left" orientation="left" stroke="#10b981" fontSize={12} />
                            <YAxis yAxisId="right" orientation="right" stroke="#3b82f6" fontSize={12} />
                            <Tooltip />
                            <Legend wrapperStyle={{fontSize: "12px"}}/>
                            <Line yAxisId="left" type="monotone" dataKey="leads" stroke="#10b981" strokeWidth={2} name="New Leads" />
                            <Line yAxisId="right" type="monotone" dataKey="conversion" stroke="#3b82f6" strokeWidth={2} name="Conversion %" />
                        </LineChart>
                    </ResponsiveContainer>
                );
            case 'area':
                return (
                    <ResponsiveContainer {...commonProps}>
                        <AreaChart data={weeklyData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" fontSize={12} />
                            <YAxis fontSize={12} />
                            <Tooltip />
                            <Legend wrapperStyle={{fontSize: "12px"}}/>
                            <Area type="monotone" dataKey="revenue" stackId="1" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} name="Revenue ($)" />
                            <Area type="monotone" dataKey="leads" stackId="2" stroke="#10b981" fill="#10b981" fillOpacity={0.6} name="New Leads" />
                        </AreaChart>
                    </ResponsiveContainer>
                );
            default:
                return (
                    <ResponsiveContainer {...commonProps}>
                        <BarChart data={weeklyData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" fontSize={12} />
                            <YAxis yAxisId="left" orientation="left" stroke="#10b981" fontSize={12} />
                            <YAxis yAxisId="right" orientation="right" stroke="#3b82f6" fontSize={12} />
                            <Tooltip />
                            <Legend wrapperStyle={{fontSize: "12px"}}/>
                            <Bar yAxisId="left" dataKey="leads" fill="#10b981" name="New Leads" />
                            <Bar yAxisId="right" dataKey="conversion" fill="#3b82f6" name="Conversion %" />
                        </BarChart>
                    </ResponsiveContainer>
                );
        }
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-green-600" />
                            Key Metrics Tracker
                        </CardTitle>
                        <CardDescription>Monitor the metrics that matter most for startup growth.</CardDescription>
                    </div>
                    <div className="flex gap-1">
                        {chartTypes.map(chart => {
                            const Icon = chart.icon;
                            return (
                                <Button
                                    key={chart.id}
                                    variant={selectedChart === chart.id ? "default" : "outline"}
                                    size="sm"
                                    onClick={() => setSelectedChart(chart.id)}
                                    className="h-8"
                                >
                                    <Icon className="w-3 h-3" />
                                </Button>
                            );
                        })}
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {keyMetrics.map((metric, index) => {
                        const Icon = metric.icon;
                        return (
                            <motion.div
                                key={metric.title}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: index * 0.1 }}
                                className="p-3 rounded-lg border hover:shadow-md transition-shadow cursor-pointer"
                                onClick={() => setSelectedMetric(metric.title.toLowerCase().replace(' ', '_'))}
                            >
                                <div className="flex items-start justify-between mb-2">
                                    <div className={`w-8 h-8 ${metric.bgColor} rounded-lg flex items-center justify-center`}>
                                        <Icon className={`w-4 h-4 ${metric.color}`} />
                                    </div>
                                    <Badge 
                                        className={`${metric.trend === 'up' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'} text-xs`}
                                        variant="outline"
                                    >
                                        {metric.change}
                                    </Badge>
                                </div>
                                <div>
                                    <div className="text-lg font-bold text-gray-900">{metric.value}</div>
                                    <div className="text-xs text-gray-600">{metric.title}</div>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {/* Chart */}
                <div>
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-sm">Growth Trends</h4>
                        <Badge variant="outline" className="text-xs">
                            Last 4 weeks
                        </Badge>
                    </div>
                    {renderChart()}
                </div>

                {/* Insights */}
                <div className="bg-green-50 p-4 rounded-lg">
                    <h4 className="font-medium text-sm text-green-800 mb-2">🎯 Growth Insights</h4>
                    <ul className="space-y-1 text-sm text-green-700">
                        <li>• Lead velocity increased 18% week-over-week</li>
                        <li>• Customer acquisition cost improved by $10</li>
                        <li>• Conversion rate trending upward (+0.4%)</li>
                        <li>• On track for $15K ARR by month end</li>
                    </ul>
                </div>
            </CardContent>
        </Card>
    );
}