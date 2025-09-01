import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { TrendingUp, Target, Users, DollarSign, CheckCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';

const kpiData = [
  { name: 'Customer Acquisition Cost', value: 120, target: 100, progress: 83 },
  { name: 'Customer Lifetime Value', value: 2500, target: 3000, progress: 83 },
  { name: 'Lead Conversion Rate', value: 15, target: 20, progress: 75 },
  { name: 'Operational Efficiency', value: 82, target: 90, progress: 91 },
  { name: 'Marketing ROI', value: 4.2, target: 5, progress: 84 },
];

const quarterlyRevenueData = [
  { quarter: 'Q1', revenue: 45000 },
  { quarter: 'Q2', revenue: 62000 },
  { quarter: 'Q3', revenue: 78000 },
  { quarter: 'Q4', revenue: 95000 },
];

export default function SMEPerformanceMetrics() {
    return (
        <Card className="col-span-full">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-6 h-6 text-purple-600" />
                    Business Performance Metrics
                </CardTitle>
                <CardDescription>Track your key performance indicators (KPIs) against targets.</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                    <h4 className="font-semibold mb-4">KPI Overview</h4>
                    <div className="space-y-6">
                        {kpiData.map((kpi, index) => (
                            <motion.div 
                                key={kpi.name}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.1 }}
                            >
                                <div className="flex items-center justify-between">
                                    <p className="font-medium text-sm">{kpi.name}</p>
                                    <Badge variant="outline" className={kpi.value >= kpi.target ? 'text-green-600 border-green-200' : 'text-orange-600 border-orange-200'}>
                                        {kpi.progress}% to target
                                    </Badge>
                                </div>
                                <Progress value={kpi.progress} className="mt-2" />
                                <div className="flex justify-between text-xs text-gray-500 mt-1">
                                    <span>Current: {kpi.value}</span>
                                    <span>Target: {kpi.target}</span>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
                <div>
                    <h4 className="font-semibold mb-4">Quarterly Revenue Growth</h4>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={quarterlyRevenueData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="quarter" />
                            <YAxis />
                            <Tooltip formatter={(value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)} />
                            <Bar dataKey="revenue" fill="#8884d8" />
                        </BarChart>
                    </ResponsiveContainer>

                    <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                        <h5 className="font-semibold flex items-center gap-2 mb-2">
                            <CheckCircle className="w-5 h-5 text-green-500"/>
                            Performance Summary
                        </h5>
                        <ul className="text-sm space-y-1 text-gray-700">
                            <li>- <strong>Customer Lifetime Value</strong> is trending positively towards the goal.</li>
                            <li>- <strong>Lead Conversion Rate</strong> needs focus, consider Sales Agent optimization.</li>
                            <li>- <strong>Operational Efficiency</strong> is exceeding expectations, great work!</li>
                        </ul>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}