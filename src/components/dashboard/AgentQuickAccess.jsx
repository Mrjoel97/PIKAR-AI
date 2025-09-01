import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
    Brain, Target, Users, BarChart, PenSquare, Sparkles, 
    DollarSign, UserCheck, SlidersHorizontal, Activity, ArrowRight 
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';

const tierAgents = {
    solopreneur: [
        { name: 'Strategic Planning', icon: Target, url: 'StrategicPlanning', color: 'bg-blue-500' },
        { name: 'Customer Support', icon: Users, url: 'CustomerSupport', color: 'bg-green-500' },
        { name: 'Data Analysis', icon: BarChart, url: 'DataAnalysis', color: 'bg-purple-500' }
    ],
    startup: [
        { name: 'Strategic Planning', icon: Target, url: 'StrategicPlanning', color: 'bg-blue-500' },
        { name: 'Customer Support', icon: Users, url: 'CustomerSupport', color: 'bg-green-500' },
        { name: 'Data Analysis', icon: BarChart, url: 'DataAnalysis', color: 'bg-purple-500' },
        { name: 'Sales Intelligence', icon: DollarSign, url: 'SalesIntelligence', color: 'bg-emerald-500' },
        { name: 'Content Creation', icon: PenSquare, url: 'ContentCreation', color: 'bg-orange-500' }
    ],
    sme: [
        { name: 'Strategic Planning', icon: Target, url: 'StrategicPlanning', color: 'bg-blue-500' },
        { name: 'Customer Support', icon: Users, url: 'CustomerSupport', color: 'bg-green-500' },
        { name: 'Data Analysis', icon: BarChart, url: 'DataAnalysis', color: 'bg-purple-500' },
        { name: 'Sales Intelligence', icon: DollarSign, url: 'SalesIntelligence', color: 'bg-emerald-500' },
        { name: 'Content Creation', icon: PenSquare, url: 'ContentCreation', color: 'bg-orange-500' },
        { name: 'Marketing Automation', icon: Sparkles, url: 'MarketingAutomation', color: 'bg-pink-500' },
        { name: 'Financial Analysis', icon: DollarSign, url: 'FinancialAnalysis', color: 'bg-indigo-500' },
        { name: 'Operations Optimization', icon: SlidersHorizontal, url: 'OperationsOptimization', color: 'bg-teal-500' }
    ],
    enterprise: [
        { name: 'Strategic Planning', icon: Target, url: 'StrategicPlanning', color: 'bg-blue-500' },
        { name: 'Customer Support', icon: Users, url: 'CustomerSupport', color: 'bg-green-500' },
        { name: 'Data Analysis', icon: BarChart, url: 'DataAnalysis', color: 'bg-purple-500' },
        { name: 'Sales Intelligence', icon: DollarSign, url: 'SalesIntelligence', color: 'bg-emerald-500' },
        { name: 'Content Creation', icon: PenSquare, url: 'ContentCreation', color: 'bg-orange-500' },
        { name: 'Marketing Automation', icon: Sparkles, url: 'MarketingAutomation', color: 'bg-pink-500' },
        { name: 'Financial Analysis', icon: DollarSign, url: 'FinancialAnalysis', color: 'bg-indigo-500' },
        { name: 'HR & Recruitment', icon: UserCheck, url: 'HRRecruitment', color: 'bg-cyan-500' },
        { name: 'Operations Optimization', icon: SlidersHorizontal, url: 'OperationsOptimization', color: 'bg-teal-500' },
        { name: 'Custom Agents', icon: Brain, url: 'CustomAgents', color: 'bg-gray-500' }
    ]
};

const agentUsageStats = {
    'Strategic Planning': { usage: 89, trend: '+12%' },
    'Customer Support': { usage: 76, trend: '+8%' },
    'Data Analysis': { usage: 94, trend: '+15%' },
    'Sales Intelligence': { usage: 82, trend: '+6%' },
    'Content Creation': { usage: 71, trend: '+22%' },
    'Marketing Automation': { usage: 67, trend: '+18%' },
    'Financial Analysis': { usage: 78, trend: '+5%' },
    'HR & Recruitment': { usage: 45, trend: '+3%' },
    'Operations Optimization': { usage: 68, trend: '+14%' },
    'Custom Agents': { usage: 34, trend: '+7%' }
};

export default function AgentQuickAccess({ tier = 'enterprise' }) {
    const agents = tierAgents[tier] || tierAgents.enterprise;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Brain className="w-6 h-6 text-emerald-600" />
                    AI Agent Quick Access
                    <Badge className="ml-2 bg-emerald-100 text-emerald-800">
                        {agents.length} Agents Available
                    </Badge>
                </CardTitle>
                <CardDescription>
                    Access your specialized AI agents for instant business intelligence
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {agents.map((agent, index) => {
                        const Icon = agent.icon;
                        const stats = agentUsageStats[agent.name] || { usage: 0, trend: '0%' };
                        
                        return (
                            <motion.div
                                key={agent.name}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.1 }}
                                whileHover={{ y: -2, scale: 1.02 }}
                                className="group"
                            >
                                <Card className="hover:shadow-md transition-all duration-200 border-2 border-transparent hover:border-emerald-200">
                                    <CardContent className="p-4">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className={`w-12 h-12 ${agent.color} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform`}>
                                                <Icon className="w-6 h-6 text-white" />
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm font-semibold text-gray-900">{stats.usage}%</div>
                                                <div className="text-xs text-green-600">{stats.trend}</div>
                                            </div>
                                        </div>
                                        
                                        <h3 className="font-semibold text-gray-900 mb-2 group-hover:text-emerald-700 transition-colors">
                                            {agent.name}
                                        </h3>
                                        
                                        <div className="mb-4">
                                            <div className="w-full bg-gray-200 rounded-full h-1.5">
                                                <motion.div 
                                                    className="bg-emerald-500 h-1.5 rounded-full"
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${stats.usage}%` }}
                                                    transition={{ duration: 1, delay: index * 0.1 }}
                                                />
                                            </div>
                                        </div>
                                        
                                        <Link to={createPageUrl(agent.url)}>
                                            <Button 
                                                variant="outline" 
                                                className="w-full group-hover:bg-emerald-50 group-hover:border-emerald-300 group-hover:text-emerald-700 transition-all"
                                            >
                                                Launch Agent
                                                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                                            </Button>
                                        </Link>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        );
                    })}
                </div>

                {tier !== 'enterprise' && (
                    <div className="mt-6 p-4 bg-gradient-to-r from-purple-50 to-purple-100 border border-purple-200 rounded-xl">
                        <div className="flex items-center justify-between">
                            <div>
                                <h4 className="font-semibold text-purple-900 mb-1">
                                    Unlock {10 - agents.length} More AI Agents
                                </h4>
                                <p className="text-sm text-purple-700">
                                    Upgrade to access the complete AI agent ecosystem
                                </p>
                            </div>
                            <Button className="bg-purple-600 hover:bg-purple-700 text-white">
                                Upgrade Now
                            </Button>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}