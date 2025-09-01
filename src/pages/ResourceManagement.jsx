import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { UserSubscription } from '@/api/entities';
import { UsageAnalytics } from '@/api/entities';
import { SlidersHorizontal, Users, Zap, DollarSign, BrainCircuit, TrendingUp, BarChart3, Activity } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { toast, Toaster } from 'sonner';

export default function ResourceManagement() {
    const [subscription, setSubscription] = useState(null);
    const [usage, setUsage] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                // In a real app, you'd fetch the current user's subscription
                const subs = await UserSubscription.list();
                setSubscription(subs[0] || { 
                    tier: 'enterprise', 
                    api_calls_used: 72500, 
                    api_calls_limit: 100000,
                    status: 'active'
                });

                // Fetch usage analytics data
                const usageData = await UsageAnalytics.list('-created_date', 100);
                if (usageData.length === 0) {
                    // Mock data for demonstration
                    usageData.push(
                        { agent_name: 'Strategic Planning', cost: 120, usage_type: 'api_call' },
                        { agent_name: 'Data Analysis', cost: 250, usage_type: 'analysis' },
                        { agent_name: 'Content Creation', cost: 80, usage_type: 'content_generation' }
                    );
                }
                setUsage(usageData);

            } catch (error) {
                console.error("Failed to fetch resource data:", error);
                toast.error("Failed to load resource data.");
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    const agentUsageCost = usage.reduce((acc, item) => {
        acc[item.agent_name] = (acc[item.agent_name] || 0) + item.cost;
        return acc;
    }, {});
    
    const chartData = Object.keys(agentUsageCost).map(key => ({
        name: key,
        cost: agentUsageCost[key]
    }));

    if (isLoading) {
        return (
            <div className="max-w-7xl mx-auto min-h-screen bg-pikar-hero">
                <div className="flex justify-center items-center h-64">
                    <motion.div 
                        className="w-8 h-8 border-4 border-emerald-200 border-t-emerald-900 rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    <span className="ml-3 text-emerald-900 font-medium">Loading resource data...</span>
                </div>
            </div>
        );
    }

    const apiUsagePercentage = subscription ? (subscription.api_calls_used / subscription.api_calls_limit) * 100 : 0;

    return (
        <div className="max-w-7xl mx-auto space-y-8 min-h-screen bg-pikar-hero p-6">
            <Toaster richColors />
            
            {/* Enhanced Header with Premium Styling */}
            <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, type: 'spring', stiffness: 100 }}
                className="relative"
            >
                <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-700 bg-clip-text text-transparent flex items-center gap-3">
                    <SlidersHorizontal className="w-8 h-8 text-emerald-900" />
                    Resource Management
                </h1>
                <p className="text-xl text-gray-600 mt-2">
                    Monitor and optimize your platform usage and costs with premium insights.
                </p>
                <motion.div
                    className="absolute -inset-4 bg-gradient-to-r from-emerald-50 to-emerald-100 rounded-3xl -z-10 opacity-30"
                    animate={{ 
                        rotateX: [0, 1, 0],
                        rotateY: [0, -1, 0] 
                    }}
                    transition={{ 
                        duration: 6,
                        repeat: Infinity,
                        ease: 'easeInOut'
                    }}
                />
            </motion.div>

            {/* Key Metrics Cards with Enhanced Styling */}
            <motion.div 
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                initial="hidden"
                animate="show"
                variants={{
                    hidden: { opacity: 0 },
                    show: {
                        opacity: 1,
                        transition: { staggerChildren: 0.1 }
                    }
                }}
            >
                {[
                    {
                        title: "Current Plan",
                        value: subscription?.tier || 'Enterprise',
                        subtitle: subscription?.status || 'Active',
                        icon: Users,
                        gradient: "from-emerald-600 to-emerald-800"
                    },
                    {
                        title: "API Usage",
                        value: `${subscription?.api_calls_used?.toLocaleString()} / ${subscription?.api_calls_limit?.toLocaleString()}`,
                        subtitle: `${apiUsagePercentage.toFixed(1)}% of monthly limit used`,
                        icon: Zap,
                        gradient: "from-emerald-700 to-emerald-900",
                        showProgress: true,
                        progressValue: apiUsagePercentage
                    },
                    {
                        title: "Estimated Monthly Cost",
                        value: `$${usage.reduce((sum, item) => sum + item.cost, 0).toFixed(2)}`,
                        subtitle: "Based on current usage patterns",
                        icon: DollarSign,
                        gradient: "from-emerald-800 to-emerald-900"
                    }
                ].map((metric, index) => (
                    <motion.div
                        key={metric.title}
                        variants={{
                            hidden: { opacity: 0, y: 20 },
                            show: { opacity: 1, y: 0 }
                        }}
                        whileHover={{ 
                            y: -6,
                            rotateX: -2,
                            rotateY: 2,
                            scale: 1.02,
                            boxShadow: '0 12px 40px rgba(6,95,70,0.15)'
                        }}
                        transition={{ type: 'spring', stiffness: 150, damping: 15 }}
                        className="relative overflow-hidden"
                    >
                        <Card className="border-emerald-100 bg-white shadow-soft">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium text-gray-600">
                                    {metric.title}
                                </CardTitle>
                                <div className={`p-2 rounded-xl bg-gradient-to-br ${metric.gradient}`}>
                                    <metric.icon className="h-5 w-5 text-white" />
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-emerald-900 mb-1">
                                    {metric.value}
                                </div>
                                {metric.showProgress && (
                                    <div className="mt-2 mb-1">
                                        <Progress 
                                            value={metric.progressValue} 
                                            className="h-2 bg-emerald-50" 
                                        />
                                    </div>
                                )}
                                <p className="text-xs text-emerald-700">
                                    {metric.subtitle}
                                </p>
                                {metric.title === "Current Plan" && (
                                    <Badge className="mt-2 bg-emerald-100 text-emerald-800 border-emerald-200">
                                        {subscription?.status || 'Active'}
                                    </Badge>
                                )}
                            </CardContent>
                            <div className="absolute inset-0 bg-gradient-to-br from-emerald-50/30 to-transparent pointer-events-none" />
                        </Card>
                    </motion.div>
                ))}
            </motion.div>

            {/* Cost Breakdown Chart with Premium Styling */}
            <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.6, type: 'spring', stiffness: 100 }}
            >
                <Card className="border-emerald-100 bg-white shadow-soft">
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-emerald-50 rounded-xl">
                                <BrainCircuit className="w-6 h-6 text-emerald-700" />
                            </div>
                            <div>
                                <CardTitle className="text-emerald-900">Cost Breakdown by AI Agent</CardTitle>
                                <CardDescription className="text-emerald-700">
                                    Visualize which agents are driving platform costs with detailed insights.
                                </CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="h-80">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 30, top: 20, bottom: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                    <XAxis type="number" tick={{ fill: '#065f46', fontSize: 12 }} />
                                    <YAxis 
                                        dataKey="name" 
                                        type="category" 
                                        width={120} 
                                        tick={{ fill: '#065f46', fontSize: 12 }} 
                                    />
                                    <Tooltip 
                                        formatter={(value) => [`$${value.toFixed(2)}`, 'Cost']}
                                        labelStyle={{ color: '#065f46' }}
                                        contentStyle={{ 
                                            backgroundColor: '#f0fdf4', 
                                            border: '1px solid #bbf7d0',
                                            borderRadius: '8px'
                                        }}
                                    />
                                    <Bar 
                                        dataKey="cost" 
                                        fill="url(#emeraldGradient)"
                                        radius={[0, 4, 4, 0]}
                                    />
                                    <defs>
                                        <linearGradient id="emeraldGradient" x1="0" y1="0" x2="1" y2="0">
                                            <stop offset="0%" stopColor="#065f46" />
                                            <stop offset="100%" stopColor="#10b981" />
                                        </linearGradient>
                                    </defs>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            {/* Additional Insights Section */}
            <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.6, type: 'spring', stiffness: 100 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-6"
            >
                <Card className="border-emerald-100 bg-gradient-to-br from-emerald-50 to-emerald-100/50">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-emerald-900">
                            <TrendingUp className="w-5 h-5" />
                            Usage Insights
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-emerald-700">Most Used Agent</span>
                            <Badge className="bg-emerald-200 text-emerald-800 border-emerald-300">
                                Strategic Planning
                            </Badge>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-emerald-700">Peak Usage Time</span>
                            <span className="text-sm font-medium text-emerald-900">2:00 PM - 4:00 PM</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-emerald-700">Efficiency Score</span>
                            <span className="text-sm font-medium text-emerald-600">94.2%</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-emerald-100 bg-white">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-emerald-900">
                            <Activity className="w-5 h-5" />
                            Quick Actions
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {[
                            { title: "Usage Analytics", icon: BarChart3 },
                            { title: "Cost Optimization", icon: TrendingUp },
                            { title: "Usage Alerts", icon: BrainCircuit }
                        ].map((action, index) => (
                            <motion.div
                                key={action.title}
                                whileHover={{ scale: 1.02, x: 4 }}
                                whileTap={{ scale: 0.98 }}
                            >
                                <Button 
                                    variant="outline" 
                                    className="w-full justify-start border-emerald-200 hover:bg-emerald-50 hover:border-emerald-300 text-emerald-900"
                                >
                                    <action.icon className="w-4 h-4 mr-2 text-emerald-600" />
                                    {action.title}
                                </Button>
                            </motion.div>
                        ))}
                    </CardContent>
                </Card>
            </motion.div>
        </div>
    );
}