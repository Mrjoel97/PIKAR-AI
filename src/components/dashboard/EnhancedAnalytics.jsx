import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { DollarSign, Zap, Users, BarChart3, TrendingUp, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

const revenueData = [
  { name: 'Jan', revenue: 4000, profit: 2400 },
  { name: 'Feb', revenue: 3000, profit: 1398 },
  { name: 'Mar', revenue: 2000, profit: 9800 },
  { name: 'Apr', revenue: 2780, profit: 3908 },
  { name: 'May', revenue: 1890, profit: 4800 },
  { name: 'Jun', revenue: 2390, profit: 3800 },
  { name: 'Jul', revenue: 3490, profit: 4300 },
];

const customerData = [
  { name: 'Q1', new: 120, retained: 450 },
  { name: 'Q2', new: 150, retained: 480 },
  { name: 'Q3', new: 180, retained: 520 },
  { name: 'Q4', new: 210, retained: 550 },
];

const efficiencyData = [
    { name: 'Marketing', score: 85 },
    { name: 'Sales', score: 72 },
    { name: 'Support', score: 91 },
    { name: 'Operations', score: 68 },
    { name: 'Finance', score: 78 },
];

const agentUsageData = [
    { name: 'Sales Intelligence', value: 400 },
    { name: 'Marketing Automation', value: 300 },
    { name: 'Financial Analysis', value: 300 },
    { name: 'Operations Optimization', value: 200 },
    { name: 'Others', value: 278 },
];

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#00C49F'];

export default function EnhancedAnalytics() {
    const [activeTab, setActiveTab] = useState('financials');

    return (
        <Card className="col-span-full">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-6 h-6 text-purple-600" />
                    Enhanced Analytics Dashboard
                </CardTitle>
                <CardDescription>Deep dive into your business performance metrics</CardDescription>
            </CardHeader>
            <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="grid w-full grid-cols-3 mb-4">
                        <TabsTrigger value="financials">Financials</TabsTrigger>
                        <TabsTrigger value="customers">Customers</TabsTrigger>
                        <TabsTrigger value="efficiency">Efficiency</TabsTrigger>
                    </TabsList>
                    <motion.div
                        key={activeTab}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                    >
                        <TabsContent value="financials">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <h4 className="font-semibold mb-2">Revenue & Profit</h4>
                                    <ResponsiveContainer width="100%" height={300}>
                                        <LineChart data={revenueData}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis dataKey="name" />
                                            <YAxis />
                                            <Tooltip />
                                            <Legend />
                                            <Line type="monotone" dataKey="revenue" stroke="#8884d8" activeDot={{ r: 8 }} />
                                            <Line type="monotone" dataKey="profit" stroke="#82ca9d" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                                <div>
                                    <h4 className="font-semibold mb-2">Agent Usage by Department</h4>
                                     <ResponsiveContainer width="100%" height={300}>
                                        <PieChart>
                                            <Pie data={agentUsageData} cx="50%" cy="50%" labelLine={false} outerRadius={80} fill="#8884d8" dataKey="value" label>
                                                {agentUsageData.map((entry, index) => (
                                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip />
                                            <Legend />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </TabsContent>
                        <TabsContent value="customers">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <h4 className="font-semibold mb-2">Customer Growth</h4>
                                    <ResponsiveContainer width="100%" height={300}>
                                        <BarChart data={customerData}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis dataKey="name" />
                                            <YAxis />
                                            <Tooltip />
                                            <Legend />
                                            <Bar dataKey="new" stackId="a" fill="#8884d8" />
                                            <Bar dataKey="retained" stackId="a" fill="#82ca9d" />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="space-y-4">
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-lg">Lifetime Value</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <p className="text-3xl font-bold">$1,280 <Badge className="bg-green-100 text-green-800">+12%</Badge></p>
                                        </CardContent>
                                    </Card>
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-lg">Acquisition Cost</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <p className="text-3xl font-bold">$150 <Badge className="bg-red-100 text-red-800">-5%</Badge></p>
                                        </CardContent>
                                    </Card>
                                </div>
                            </div>
                        </TabsContent>
                        <TabsContent value="efficiency">
                            <h4 className="font-semibold mb-2">Departmental Efficiency Score</h4>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={efficiencyData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="name" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Bar dataKey="score" fill="#8884d8" />
                                </BarChart>
                            </ResponsiveContainer>
                        </TabsContent>
                    </motion.div>
                </Tabs>
            </CardContent>
        </Card>
    );
}