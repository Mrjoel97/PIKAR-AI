import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Users, Clock, TrendingUp, MessageCircle, FileText, Target } from 'lucide-react';
import { motion } from 'framer-motion';

const activities = [
    { 
        user: 'Alice Johnson', 
        action: 'generated a sales report for Q4 prospects', 
        time: '5m ago', 
        avatar: '/api/placeholder/32/32',
        type: 'analysis',
        agent: 'Sales Intelligence',
        impact: 'high'
    },
    { 
        user: 'Bob Chen', 
        action: 'drafted 3 new blog posts about product features', 
        time: '12m ago', 
        avatar: '/api/placeholder/32/32',
        type: 'content',
        agent: 'Content Creation',
        impact: 'medium'
    },
    { 
        user: 'Alice Johnson', 
        action: 'analyzed competitor pricing strategies', 
        time: '28m ago', 
        avatar: '/api/placeholder/32/32',
        type: 'strategy',
        agent: 'Strategic Planning',
        impact: 'high'
    },
    { 
        user: 'Charlie Wilson', 
        action: 'resolved 5 customer support tickets', 
        time: '45m ago', 
        avatar: '/api/placeholder/32/32',
        type: 'support',
        agent: 'Customer Support',
        impact: 'medium'
    },
    { 
        user: 'Bob Chen', 
        action: 'optimized social media content calendar', 
        time: '1h ago', 
        avatar: '/api/placeholder/32/32',
        type: 'content',
        agent: 'Content Creation',
        impact: 'low'
    },
    { 
        user: 'Diana Martinez', 
        action: 'analyzed user feedback from 127 responses', 
        time: '1.5h ago', 
        avatar: '/api/placeholder/32/32',
        type: 'analysis',
        agent: 'Data Analysis',
        impact: 'high'
    }
];

const getActivityIcon = (type) => {
    switch (type) {
        case 'analysis': return TrendingUp;
        case 'content': return FileText;
        case 'strategy': return Target;
        case 'support': return MessageCircle;
        default: return Clock;
    }
};

const getImpactColor = (impact) => {
    switch (impact) {
        case 'high': return 'bg-red-100 text-red-800';
        case 'medium': return 'bg-yellow-100 text-yellow-800';
        case 'low': return 'bg-green-100 text-green-800';
        default: return 'bg-gray-100 text-gray-800';
    }
};

const getTypeColor = (type) => {
    switch (type) {
        case 'analysis': return 'text-purple-600';
        case 'content': return 'text-blue-600';
        case 'strategy': return 'text-orange-600';
        case 'support': return 'text-green-600';
        default: return 'text-gray-600';
    }
};

export default function TeamActivityFeed() {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-green-600" />
                    Team Activity Feed
                </CardTitle>
                <CardDescription>Stay aligned with your team's latest AI-powered actions.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {/* Team Stats */}
                    <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-green-50 rounded-lg">
                        <div className="text-center">
                            <div className="text-lg font-bold text-green-700">24</div>
                            <div className="text-xs text-green-600">Actions Today</div>
                        </div>
                        <div className="text-center">
                            <div className="text-lg font-bold text-green-700">5</div>
                            <div className="text-xs text-green-600">Active Members</div>
                        </div>
                        <div className="text-center">
                            <div className="text-lg font-bold text-green-700">87%</div>
                            <div className="text-xs text-green-600">Efficiency Gain</div>
                        </div>
                    </div>

                    {/* Activity List */}
                    <ul className="space-y-3 max-h-64 overflow-y-auto">
                        {activities.map((activity, index) => {
                            const Icon = getActivityIcon(activity.type);
                            return (
                                <motion.li
                                    key={index}
                                    className="flex items-start gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors"
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.1 }}
                                >
                                    <Avatar className="w-8 h-8 flex-shrink-0">
                                        <AvatarImage src={activity.avatar} />
                                        <AvatarFallback className="bg-green-100 text-green-600 text-xs">
                                            {activity.user.split(' ').map(n => n[0]).join('')}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1">
                                                <p className="text-sm">
                                                    <span className="font-semibold text-gray-900">{activity.user}</span>
                                                    {' '}{activity.action}
                                                </p>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <div className="flex items-center gap-1 text-xs text-gray-500">
                                                        <Icon className={`w-3 h-3 ${getTypeColor(activity.type)}`} />
                                                        <span>{activity.agent}</span>
                                                    </div>
                                                    <Badge 
                                                        className={`${getImpactColor(activity.impact)} text-xs px-2 py-0`}
                                                        variant="outline"
                                                    >
                                                        {activity.impact} impact
                                                    </Badge>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1 text-xs text-gray-500 flex-shrink-0">
                                                <Clock className="w-3 h-3" />
                                                <span>{activity.time}</span>
                                            </div>
                                        </div>
                                    </div>
                                </motion.li>
                            );
                        })}
                    </ul>
                </div>
            </CardContent>
        </Card>
    );
}