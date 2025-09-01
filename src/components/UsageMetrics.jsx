import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { UsageAnalytics } from '@/api/entities';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { TrendingUp, Clock, DollarSign, Zap } from 'lucide-react';
import _ from 'lodash';

export default function UsageMetrics() {
    const [metrics, setMetrics] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadMetrics();
    }, []);

    const loadMetrics = async () => {
        setIsLoading(true);
        try {
            const usageData = await UsageAnalytics.list('-created_date', 500);
            
            // Process metrics
            const agentUsage = _.groupBy(usageData, 'agent_name');
            const agentMetrics = Object.keys(agentUsage).map(agentName => ({
                agent: agentName,
                calls: agentUsage[agentName].length,
                avgDuration: _.meanBy(agentUsage[agentName], 'session_duration'),
                totalCost: _.sumBy(agentUsage[agentName], 'cost'),
                avgSatisfaction: _.meanBy(agentUsage[agentName], 'user_satisfaction')
            }));

            // Daily usage trend
            const dailyUsage = _.groupBy(usageData, d => new Date(d.created_date).toISOString().split('T')[0]);
            const trendData = Object.entries(dailyUsage)
                .sort(([a], [b]) => a.localeCompare(b))
                .slice(-14)
                .map(([date, data]) => ({
                    date: new Date(date).toLocaleDateString(),
                    calls: data.length,
                    cost: _.sumBy(data, 'cost')
                }));

            setMetrics({
                agentMetrics: _.orderBy(agentMetrics, ['calls'], ['desc']),
                trendData,
                totalCalls: usageData.length,
                totalCost: _.sumBy(usageData, 'cost'),
                avgSatisfaction: _.meanBy(usageData, 'user_satisfaction')
            });
        } catch (error) {
            console.error("Error loading usage metrics:", error);
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </CardContent>
            </Card>
        );
    }

    if (!metrics) {
        return (
            <Card>
                <CardContent className="text-center py-8 text-gray-500">
                    No usage data available
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Usage Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total API Calls</CardTitle>
                        <Zap className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{metrics.totalCalls.toLocaleString()}</div>
                        <p className="text-xs text-muted-foreground">
                            Across all agents
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
                        <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">${metrics.totalCost.toFixed(2)}</div>
                        <p className="text-xs text-muted-foreground">
                            This period
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Satisfaction</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{metrics.avgSatisfaction.toFixed(1)}/5</div>
                        <p className="text-xs text-muted-foreground">
                            User satisfaction rating
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <Card>
                    <CardHeader>
                        <CardTitle>Agent Usage Volume</CardTitle>
                        <CardDescription>API calls by agent over the selected period</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={metrics.agentMetrics}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="agent" angle={-45} textAnchor="end" height={100} />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="calls" fill="#3B82F6" />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Usage Trend</CardTitle>
                        <CardDescription>Daily usage and cost trends</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={metrics.trendData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip />
                                <Line type="monotone" dataKey="calls" stroke="#3B82F6" name="API Calls" />
                                <Line type="monotone" dataKey="cost" stroke="#10B981" name="Cost ($)" />
                            </LineChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* Agent Performance Table */}
            <Card>
                <CardHeader>
                    <CardTitle>Agent Performance Breakdown</CardTitle>
                    <CardDescription>Detailed metrics for each agent</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {metrics.agentMetrics.map(agent => (
                            <div key={agent.agent} className="p-4 border rounded-lg">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="font-semibold">{agent.agent}</h3>
                                    <Badge variant="outline">{agent.calls} calls</Badge>
                                </div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <span className="text-gray-500">Avg Duration:</span>
                                        <p className="font-medium">{Math.round(agent.avgDuration / 60)}m</p>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Total Cost:</span>
                                        <p className="font-medium">${agent.totalCost.toFixed(2)}</p>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Satisfaction:</span>
                                        <p className="font-medium">{agent.avgSatisfaction.toFixed(1)}/5</p>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Efficiency:</span>
                                        <Progress value={agent.avgSatisfaction * 20} className="h-2 mt-1" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}