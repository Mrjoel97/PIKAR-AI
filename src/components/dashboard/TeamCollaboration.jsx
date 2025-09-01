import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Users, Plus, Send } from 'lucide-react';
import { motion } from 'framer-motion';

const teamMembers = [
    { name: 'Alice Johnson', role: 'Marketing Lead', avatar: 'https://i.pravatar.cc/150?u=a042581f4e29026704d' },
    { name: 'Bob Williams', role: 'Sales Director', avatar: 'https://i.pravatar.cc/150?u=a042581f4e29026705d' },
    { name: 'Charlie Brown', role: 'Operations Manager', avatar: 'https://i.pravatar.cc/150?u=a042581f4e29026706d' },
    { name: 'Diana Miller', role: 'Financial Analyst', avatar: 'https://i.pravatar.cc/150?u=a042581f4e29026707d' },
];

const recentActivity = [
    { user: 'Alice Johnson', action: 'launched a new marketing campaign', time: '2 hours ago' },
    { user: 'Bob Williams', action: 'updated the sales forecast', time: '4 hours ago' },
    { user: 'Charlie Brown', action: 'optimized the inventory workflow', time: '1 day ago' },
];

export default function TeamCollaboration() {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Users className="w-6 h-6 text-purple-600" />
                    Team Collaboration Hub
                </CardTitle>
                <CardDescription>Manage your team and track their activities.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div>
                    <div className="flex justify-between items-center mb-2">
                        <h4 className="font-semibold">Team Members (4/100)</h4>
                        <Button variant="outline" size="sm">
                            <Plus className="w-4 h-4 mr-2" /> Invite Member
                        </Button>
                    </div>
                    <div className="space-y-3">
                        {teamMembers.map((member, index) => (
                            <motion.div
                                key={member.name}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50"
                            >
                                <div className="flex items-center gap-3">
                                    <Avatar>
                                        <AvatarImage src={member.avatar} />
                                        <AvatarFallback>{member.name.charAt(0)}</AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <p className="font-medium text-sm">{member.name}</p>
                                        <p className="text-xs text-gray-500">{member.role}</p>
                                    </div>
                                </div>
                                <Badge variant="secondary">Active</Badge>
                            </motion.div>
                        ))}
                    </div>
                </div>

                <div>
                    <h4 className="font-semibold mb-2">Recent Team Activity</h4>
                    <div className="space-y-3">
                        {recentActivity.map((activity, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.4 + index * 0.1 }}
                                className="flex items-start gap-3"
                            >
                                <Avatar className="w-8 h-8">
                                    <AvatarImage src={teamMembers.find(m => m.name === activity.user)?.avatar} />
                                    <AvatarFallback>{activity.user.charAt(0)}</AvatarFallback>
                                </Avatar>
                                <div className="text-sm">
                                    <p>
                                        <span className="font-semibold">{activity.user}</span> {activity.action}.
                                    </p>
                                    <p className="text-xs text-gray-500">{activity.time}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>

                <div>
                    <h4 className="font-semibold mb-2">Quick Message</h4>
                    <div className="flex gap-2">
                        <Input placeholder="Message your team..." />
                        <Button>
                            <Send className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}