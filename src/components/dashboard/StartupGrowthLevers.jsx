import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { DollarSign, PenSquare, TestTube, ArrowRight, TrendingUp, Users, Target } from 'lucide-react';
import { motion } from 'framer-motion';

const growthLevers = [
    {
        title: 'Lead Generation Engine',
        description: 'Analyze leads, score opportunities, and generate sales strategies to build your pipeline.',
        icon: DollarSign,
        color: 'text-emerald-500',
        bgColor: 'bg-emerald-50',
        url: 'SalesIntelligence',
        action: 'Analyze Leads',
        impact: 'High',
        effort: 'Medium',
        timeframe: '2-3 hours',
        expectedROI: '+25% conversion rate',
        challenges: [
            'Low lead quality',
            'Poor lead scoring',
            'Manual qualification process'
        ]
    },
    {
        title: 'Content Creation Hub',
        description: 'Generate blog posts, social media updates, and ad copy to build brand awareness.',
        icon: PenSquare,
        color: 'text-orange-500',
        bgColor: 'bg-orange-50',
        url: 'ContentCreation',
        action: 'Create Content',
        impact: 'High',
        effort: 'Low',
        timeframe: '1-2 hours',
        expectedROI: '+40% content output',
        challenges: [
            'Inconsistent content quality',
            'Limited content volume',
            'Brand voice inconsistency'
        ]
    },
    {
        title: 'Product-Market Fit Lab',
        description: 'Use data and support insights to analyze user feedback and iterate on your product.',
        icon: TestTube,
        color: 'text-blue-500',
        bgColor: 'bg-blue-50',
        url: 'DataAnalysis',
        action: 'Analyze Feedback',
        impact: 'Critical',
        effort: 'High',
        timeframe: '4-6 hours',
        expectedROI: '+60% user satisfaction',
        challenges: [
            'Unclear product-market fit',
            'User feedback analysis',
            'Feature prioritization'
        ]
    }
];

const getImpactColor = (impact) => {
    switch (impact) {
        case 'Critical': return 'bg-red-100 text-red-800';
        case 'High': return 'bg-orange-100 text-orange-800';
        case 'Medium': return 'bg-yellow-100 text-yellow-800';
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

export default function StartupGrowthLevers() {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Target className="w-6 h-6 text-green-600" />
                    Growth Levers
                </CardTitle>
                <CardDescription>Focus on the most critical challenges for your startup growth.</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {growthLevers.map((lever, index) => {
                    const Icon = lever.icon;
                    return (
                        <motion.div
                            key={lever.title}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.15 }}
                            whileHover={{ y: -5, scale: 1.02 }}
                            className="group"
                        >
                            <Card className="h-full flex flex-col justify-between hover:shadow-lg transition-shadow duration-300 border-l-4 border-l-green-200 hover:border-l-green-500">
                                <CardHeader className="pb-4">
                                    <div className="flex items-start justify-between mb-3">
                                        <div className={`w-12 h-12 ${lever.bgColor} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform`}>
                                            <Icon className={`w-6 h-6 ${lever.color}`} />
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <Badge className={getImpactColor(lever.impact)} variant="outline">
                                                {lever.impact} Impact
                                            </Badge>
                                            <Badge className={getEffortColor(lever.effort)} variant="outline">
                                                {lever.effort} Effort
                                            </Badge>
                                        </div>
                                    </div>
                                    <CardTitle className="text-lg group-hover:text-green-700 transition-colors">
                                        {lever.title}
                                    </CardTitle>
                                    <CardDescription>{lever.description}</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Time to Impact:</span>
                                            <span className="font-medium">{lever.timeframe}</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Expected ROI:</span>
                                            <span className="font-medium text-green-600">{lever.expectedROI}</span>
                                        </div>
                                    </div>
                                    
                                    <div className="space-y-2">
                                        <h4 className="text-sm font-medium text-gray-700">Addresses:</h4>
                                        <ul className="space-y-1">
                                            {lever.challenges.map((challenge, idx) => (
                                                <li key={idx} className="text-xs text-gray-600 flex items-center gap-2">
                                                    <div className="w-1 h-1 bg-green-500 rounded-full"></div>
                                                    {challenge}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    
                                    <Link to={createPageUrl(lever.url)}>
                                        <Button className="w-full bg-green-600 hover:bg-green-700 group-hover:shadow-md transition-all">
                                            {lever.action}
                                            <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                                        </Button>
                                    </Link>
                                </CardContent>
                            </Card>
                        </motion.div>
                    );
                })}
            </CardContent>
        </Card>
    );
}