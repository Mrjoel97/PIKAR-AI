import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { 
    Lightbulb, Target, TrendingUp, ArrowRight, CheckCircle, 
    AlertTriangle, Clock, Zap, Users, BarChart 
} from 'lucide-react';
import { motion } from 'framer-motion';

const solopreneurChallenges = [
    {
        id: 'validation',
        title: 'Product/Market Fit Validation',
        severity: 'critical',
        description: 'Validate your business idea with real market feedback',
        solution: 'Strategic Planning Agent',
        actionUrl: 'StrategicPlanning',
        progress: 25,
        timeToComplete: '3-4 hours',
        impact: 'Reduces failure risk by 60%'
    },
    {
        id: 'content',
        title: 'Content Creation & Marketing',
        severity: 'high',
        description: 'Create consistent, engaging content to build your audience',
        solution: 'Content Creation Agent',
        actionUrl: 'ContentCreation',
        progress: 45,
        timeToComplete: '2-3 hours',
        impact: 'Increases visibility by 40%'
    },
    {
        id: 'analytics',
        title: 'Data-Driven Decision Making',
        severity: 'medium',
        description: 'Turn your data into actionable business insights',
        solution: 'Data Analysis Agent',
        actionUrl: 'DataAnalysis',
        progress: 60,
        timeToComplete: '1-2 hours',
        impact: 'Improves decision accuracy by 35%'
    }
];

const quickWins = [
    {
        title: 'Create Your First Business Plan',
        description: 'Use AI to generate a comprehensive business plan in minutes',
        agent: 'Strategic Planning',
        time: '30 mins',
        difficulty: 'Easy'
    },
    {
        title: 'Generate Week\'s Content Calendar',
        description: 'Create a full week of social media and blog content',
        agent: 'Content Creation',
        time: '45 mins',
        difficulty: 'Easy'
    },
    {
        title: 'Analyze Your Competitors',
        description: 'Get detailed insights about your top 3 competitors',
        agent: 'Strategic Planning',
        time: '1 hour',
        difficulty: 'Medium'
    }
];

const getSeverityColor = (severity) => {
    switch (severity) {
        case 'critical': return 'bg-red-100 text-red-800 border-red-200';
        case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
        case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
        default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
};

const getDifficultyColor = (difficulty) => {
    switch (difficulty) {
        case 'Easy': return 'bg-green-100 text-green-800';
        case 'Medium': return 'bg-yellow-100 text-yellow-800';
        case 'Hard': return 'bg-red-100 text-red-800';
        default: return 'bg-gray-100 text-gray-800';
    }
};

export default function SolopreneurEssentials() {
    const [activeTab, setActiveTab] = useState('challenges');

    return (
        <div className="space-y-6">
            {/* Challenge Tracker */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Target className="w-6 h-6 text-blue-600" />
                        Your Solopreneur Journey
                    </CardTitle>
                    <CardDescription>
                        Focus on these essential challenges to build a successful business
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {solopreneurChallenges.map((challenge, index) => (
                        <motion.div
                            key={challenge.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-2">
                                        <h4 className="font-semibold">{challenge.title}</h4>
                                        <Badge className={getSeverityColor(challenge.severity)}>
                                            {challenge.severity}
                                        </Badge>
                                    </div>
                                    <p className="text-sm text-gray-600 mb-3">{challenge.description}</p>
                                    <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                                        <span className="flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {challenge.timeToComplete}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <TrendingUp className="w-3 h-3" />
                                            {challenge.impact}
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between text-sm">
                                            <span>Progress</span>
                                            <span>{challenge.progress}%</span>
                                        </div>
                                        <Progress value={challenge.progress} />
                                    </div>
                                </div>
                                <Link to={createPageUrl(challenge.actionUrl)}>
                                    <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                                        <Zap className="w-4 h-4 mr-2" />
                                        Use {challenge.solution}
                                    </Button>
                                </Link>
                            </div>
                        </motion.div>
                    ))}
                </CardContent>
            </Card>

            {/* Quick Wins */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Lightbulb className="w-6 h-6 text-blue-600" />
                        Quick Wins for Today
                    </CardTitle>
                    <CardDescription>
                        Start with these simple tasks to make immediate progress
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {quickWins.map((win, index) => (
                            <motion.div
                                key={win.title}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 0.3 + index * 0.1 }}
                                className="border rounded-lg p-4 hover:shadow-md transition-all hover:scale-105"
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <Badge className={getDifficultyColor(win.difficulty)}>
                                        {win.difficulty}
                                    </Badge>
                                    <span className="text-xs text-gray-500">{win.time}</span>
                                </div>
                                <h4 className="font-semibold mb-2">{win.title}</h4>
                                <p className="text-sm text-gray-600 mb-3">{win.description}</p>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-blue-600">{win.agent}</span>
                                    <Button size="sm" variant="outline">
                                        Start Now
                                        <ArrowRight className="w-3 h-3 ml-2" />
                                    </Button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}