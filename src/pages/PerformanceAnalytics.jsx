
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button'; // Added this import
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { UsageAnalytics } from '@/api/entities';
import { BarChart, LineChart, PieChart, Bar, Line, Pie, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import _ from 'lodash';
import { apiIntegrationService } from '@/services/apiIntegrationService';
import { errorHandlingService } from '@/services/errorHandlingService';
import AsyncErrorBoundary from '@/components/error/AsyncErrorBoundary';
import {
    BarChart3,
    Zap,
    Users,
    TrendingUp,
    Lightbulb,
    AlertTriangle,
    FileSearch,
    BrainCircuit
} from 'lucide-react';

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export default function PerformanceAnalytics() {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [timeframe, setTimeframe] = useState('30d');

    useEffect(() => {
        fetchAnalytics();
        // ... (URL param handling)
    }, [timeframe]);

    const fetchAnalytics = async () => {
        setIsLoading(true);
        try {
            // Fetch real usage analytics data
            const usageData = await UsageAnalytics.list('-created_date', 200);

            // Fetch real analytics data from multiple sources
            const [kpisData, agentUsageData, trendsData, predictiveData, bottlenecksData] = await Promise.all([
                fetchKPIData(),
                fetchAgentUsageData(),
                fetchTrendsData(),
                fetchPredictiveData(),
                fetchBottlenecksData()
            ]);

            const realData = {
                kpis: kpisData,
                agentUsage: agentUsageData,
                usageOverTime: trendsData.usage,
                satisfactionTrends: trendsData.satisfaction,
                predictive: predictiveData,
                bottlenecks: bottlenecksData
            };
            setAnalyticsData(realData);
        } catch (error) {
            console.error("Failed to fetch analytics:", error);
            errorHandlingService.handleApiError(error, {
                component: 'PerformanceAnalytics',
                operation: 'fetchAnalytics'
            });

            // Fallback to basic data structure
            setAnalyticsData({
                kpis: { avgSuccessRate: 0, avgSatisfaction: 0, totalInteractions: 0, avgSessionDuration: 0 },
                agentUsage: [],
                usageOverTime: [],
                satisfactionTrends: [],
                predictive: [],
                bottlenecks: []
            });
        } finally {
            setIsLoading(false);
        }
    };

    // Real API fetch functions
    const fetchKPIData = async () => {
        try {
            const response = await UsageAnalytics.filter({
                date_range: getDateRange(timeframe),
                aggregate: ['success_rate', 'satisfaction', 'interactions', 'session_duration']
            });

            return {
                avgSuccessRate: response.data?.avg_success_rate || 0,
                avgSatisfaction: response.data?.avg_satisfaction || 0,
                totalInteractions: response.data?.total_interactions || 0,
                avgSessionDuration: response.data?.avg_session_duration || 0
            };
        } catch (error) {
            console.error('Error fetching KPI data:', error);
            return { avgSuccessRate: 0, avgSatisfaction: 0, totalInteractions: 0, avgSessionDuration: 0 };
        }
    };

    const fetchAgentUsageData = async () => {
        try {
            const response = await UsageAnalytics.filter({
                date_range: getDateRange(timeframe),
                group_by: 'agent_type',
                metrics: ['interactions', 'success_rate', 'satisfaction']
            });

            return response.data?.map(item => ({
                name: item.agent_type,
                interactions: item.interactions || 0,
                success_rate: item.success_rate || 0,
                satisfaction: item.satisfaction || 0
            })) || [];
        } catch (error) {
            console.error('Error fetching agent usage data:', error);
            return [];
        }
    };

    const fetchTrendsData = async () => {
        try {
            const [usageResponse, satisfactionResponse] = await Promise.all([
                UsageAnalytics.filter({
                    date_range: getDateRange(timeframe),
                    group_by: 'date',
                    metrics: ['interactions']
                }),
                UsageAnalytics.filter({
                    date_range: getDateRange(timeframe),
                    group_by: 'date',
                    metrics: ['satisfaction']
                })
            ]);

            return {
                usage: usageResponse.data?.map(item => ({
                    date: formatDate(item.date),
                    interactions: item.interactions || 0
                })) || [],
                satisfaction: satisfactionResponse.data?.map(item => ({
                    date: formatDate(item.date),
                    rating: item.satisfaction || 0
                })) || []
            };
        } catch (error) {
            console.error('Error fetching trends data:', error);
            return { usage: [], satisfaction: [] };
        }
    };

    const fetchPredictiveData = async () => {
        try {
            const response = await UsageAnalytics.filter({
                type: 'predictive',
                months: 4,
                metrics: ['actual', 'predicted']
            });

            return response.data?.map(item => ({
                month: item.month,
                actual: item.actual,
                predicted: item.predicted
            })) || [];
        } catch (error) {
            console.error('Error fetching predictive data:', error);
            return [];
        }
    };

    const fetchBottlenecksData = async () => {
        try {
            const response = await UsageAnalytics.filter({
                type: 'bottlenecks',
                severity: ['high', 'medium'],
                limit: 10
            });

            return response.data?.map(item => ({
                area: item.area,
                issue: item.issue,
                impact: item.impact,
                recommendation: item.recommendation
            })) || [];
        } catch (error) {
            console.error('Error fetching bottlenecks data:', error);
            return [];
        }
    };

    // Helper functions
    const getDateRange = (timeframe) => {
        const now = new Date();
        const ranges = {
            '7d': new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
            '30d': new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000),
            '90d': new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
        };

        return {
            start: ranges[timeframe] || ranges['30d'],
            end: now
        };
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };
    
    if (isLoading) return <div>Loading...</div>;

    const { kpis, agentUsage, usageOverTime, satisfactionTrends, predictive, bottlenecks } = analyticsData;

    return (
        <AsyncErrorBoundary
            componentName="PerformanceAnalytics"
            operation="render"
            onRetry={fetchAnalytics}
            fallbackUrl="/dashboard"
        >
            <div className="max-w-7xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <BarChart3 className="w-8 h-8 text-blue-600" />
                        Performance Analytics
                    </h1>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* KPI cards ... */}
            </div>

            {/* Agent Usage and Success Metrics */}
            <Card id="agent-usage">
                {/* Agent usage chart ... */}
            </Card>

            {/* Predictive Analytics & Bottleneck Detection */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-green-500" />
                            Predictive Analytics & Forecasting
                        </CardTitle>
                        <CardDescription>Forecasted usage based on historical trends.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={predictive}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="month" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="actual" stroke="#8884d8" strokeWidth={2} name="Actual Interactions" />
                                <Line type="monotone" dataKey="predicted" stroke="#82ca9d" strokeDasharray="5 5" name="Predicted Interactions" />
                            </LineChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5 text-red-500" />
                            Bottleneck Detection
                        </CardTitle>
                        <CardDescription>AI-identified areas for performance improvement.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {bottlenecks.map((item, index) => (
                            <div key={index} className="p-3 border rounded-lg">
                                <h4 className="font-semibold text-sm">{item.area}</h4>
                                <p className="text-sm text-gray-600">{item.issue}</p>
                                <div className="flex justify-between items-center mt-2">
                                    <Badge variant={item.impact === 'High' ? 'destructive' : 'secondary'}>{item.impact} Impact</Badge>
                                    <Button variant="ghost" size="sm">Details</Button>
                                </div>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            </div>
        </div>
        </AsyncErrorBoundary>
    );
}
