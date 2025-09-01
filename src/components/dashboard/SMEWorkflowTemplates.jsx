import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { 
    Workflow, Users, DollarSign, BarChart, FileText, 
    Clock, ArrowRight, CheckCircle 
} from 'lucide-react';
import { motion } from 'framer-motion';

const workflowTemplates = [
    {
        id: 'customer-onboarding',
        title: 'Customer Onboarding Automation',
        description: 'Streamline new customer setup with automated workflows',
        category: 'Customer Success',
        agents: ['Customer Support', 'Operations Optimization'],
        timeToSetup: '30 mins',
        complexity: 'Medium',
        roi: '+40% efficiency',
        usageCount: 127,
        rating: 4.8,
        steps: [
            'Welcome email sequence',
            'Account setup automation',
            'Training resource delivery',
            'First-week check-in'
        ]
    },
    {
        id: 'lead-qualification',
        title: 'Intelligent Lead Scoring',
        description: 'Automatically score and prioritize incoming leads',
        category: 'Sales',
        agents: ['Sales Intelligence', 'Data Analysis'],
        timeToSetup: '45 mins',
        complexity: 'High',
        roi: '+60% conversion',
        usageCount: 89,
        rating: 4.9,
        steps: [
            'Lead data collection',
            'AI-powered scoring',
            'CRM integration',
            'Sales team notification'
        ]
    },
    {
        id: 'content-pipeline',
        title: 'Content Creation Pipeline',
        description: 'Consistent content creation and publishing workflow',
        category: 'Marketing',
        agents: ['Content Creation', 'Marketing Automation'],
        timeToSetup: '20 mins',
        complexity: 'Low',
        roi: '+35% output',
        usageCount: 156,
        rating: 4.7,
        steps: [
            'Topic research',
            'Content generation',
            'Review and approval',
            'Multi-platform publishing'
        ]
    },
    {
        id: 'financial-reporting',
        title: 'Monthly Financial Reports',
        description: 'Automated financial analysis and reporting',
        category: 'Finance',
        agents: ['Financial Analysis', 'Data Analysis'],
        timeToSetup: '60 mins',
        complexity: 'High',
        roi: '+50% accuracy',
        usageCount: 73,
        rating: 4.6,
        steps: [
            'Data collection',
            'Financial analysis',
            'Report generation',
            'Stakeholder distribution'
        ]
    }
];

const getComplexityColor = (complexity) => {
    switch (complexity) {
        case 'Low': return 'bg-green-100 text-green-800';
        case 'Medium': return 'bg-yellow-100 text-yellow-800';
        case 'High': return 'bg-red-100 text-red-800';
        default: return 'bg-gray-100 text-gray-800';
    }
};

const getCategoryColor = (category) => {
    switch (category) {
        case 'Sales': return 'bg-blue-100 text-blue-800';
        case 'Marketing': return 'bg-purple-100 text-purple-800';
        case 'Finance': return 'bg-green-100 text-green-800';
        case 'Customer Success': return 'bg-orange-100 text-orange-800';
        default: return 'bg-gray-100 text-gray-800';
    }
};

export default function SMEWorkflowTemplates() {
    return (
        <Card className="col-span-full">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Workflow className="w-6 h-6 text-purple-600" />
                            Workflow Templates Gallery
                        </CardTitle>
                        <CardDescription>
                            Pre-built workflows to solve common SME business challenges
                        </CardDescription>
                    </div>
                    <Link to={createPageUrl('CreateWorkflow')}>
                        <Button>
                            Create Custom Workflow
                            <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                    </Link>
                </div>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {workflowTemplates.map((template, index) => (
                        <motion.div
                            key={template.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="group"
                        >
                            <Card className="h-full hover:shadow-lg transition-all duration-300 group-hover:scale-105">
                                <CardHeader className="pb-4">
                                    <div className="flex items-start justify-between mb-2">
                                        <Badge className={getCategoryColor(template.category)}>
                                            {template.category}
                                        </Badge>
                                        <div className="flex items-center gap-1 text-xs text-gray-500">
                                            ⭐ {template.rating} • {template.usageCount} uses
                                        </div>
                                    </div>
                                    <CardTitle className="text-lg">{template.title}</CardTitle>
                                    <CardDescription>{template.description}</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex items-center justify-between text-sm">
                                        <div className="flex items-center gap-4">
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {template.timeToSetup}
                                            </span>
                                            <Badge className={getComplexityColor(template.complexity)} variant="outline">
                                                {template.complexity}
                                            </Badge>
                                        </div>
                                        <span className="text-green-600 font-medium">{template.roi}</span>
                                    </div>
                                    
                                    <div>
                                        <p className="text-sm font-medium mb-2">Workflow Steps:</p>
                                        <div className="space-y-1">
                                            {template.steps.map((step, stepIndex) => (
                                                <div key={stepIndex} className="flex items-center gap-2 text-xs text-gray-600">
                                                    <CheckCircle className="w-3 h-3 text-green-500" />
                                                    {step}
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    <div>
                                        <p className="text-sm font-medium mb-2">AI Agents Used:</p>
                                        <div className="flex flex-wrap gap-1">
                                            {template.agents.map((agent) => (
                                                <Badge key={agent} variant="outline" className="text-xs">
                                                    {agent}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="pt-2 border-t">
                                        <Button className="w-full" size="sm">
                                            Use This Template
                                            <ArrowRight className="w-3 h-3 ml-2" />
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}