
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { User } from '@/api/entities';
import { 
    MessageCircle, 
    Send, 
    Users, 
    Clock, 
    Eye,
    UserPlus,
    CheckCircle,
    AlertCircle,
    Edit3,
    Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

// Mock real-time collaboration system
class MockCollaborationService {
    constructor() {
        this.subscribers = new Set();
        this.comments = new Map();
        this.activeUsers = new Map();
        this.cursors = new Map();
    }

    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback);
    }

    broadcast(event) {
        this.subscribers.forEach(callback => callback(event));
    }

    addComment(initiativeId, comment) {
        const id = Date.now().toString();
        const commentData = {
            id,
            ...comment,
            timestamp: new Date().toISOString(),
            replies: []
        };
        
        if (!this.comments.has(initiativeId)) {
            this.comments.set(initiativeId, []);
        }
        
        this.comments.get(initiativeId).push(commentData);
        
        this.broadcast({
            type: 'comment_added',
            initiativeId,
            comment: commentData
        });
        
        return commentData;
    }

    getComments(initiativeId) {
        return this.comments.get(initiativeId) || [];
    }

    joinInitiative(initiativeId, user) {
        if (!this.activeUsers.has(initiativeId)) {
            this.activeUsers.set(initiativeId, new Set());
        }
        
        this.activeUsers.get(initiativeId).add(user);
        
        this.broadcast({
            type: 'user_joined',
            initiativeId,
            user
        });
    }

    leaveInitiative(initiativeId, userId) {
        const users = this.activeUsers.get(initiativeId);
        if (users) {
            const userToRemove = Array.from(users).find(u => u.id === userId);
            if (userToRemove) {
                users.delete(userToRemove);
                
                this.broadcast({
                    type: 'user_left',
                    initiativeId,
                    userId
                });
            }
        }
    }

    getActiveUsers(initiativeId) {
        const users = this.activeUsers.get(initiativeId);
        return users ? Array.from(users) : [];
    }

    updateCursor(initiativeId, userId, position) {
        if (!this.cursors.has(initiativeId)) {
            this.cursors.set(initiativeId, new Map());
        }
        
        this.cursors.get(initiativeId).set(userId, position);
        
        this.broadcast({
            type: 'cursor_updated',
            initiativeId,
            userId,
            position
        });
    }
}

const collaborationService = new MockCollaborationService();

export default function RealTimeCollaboration({ initiativeId, deliverableId = null }) {
    const [comments, setComments] = useState([]);
    const [activeUsers, setActiveUsers] = useState([]);
    const [newComment, setNewComment] = useState('');
    const [isConnected, setIsConnected] = useState(false);
    const [currentUser, setCurrentUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const messagesEndRef = useRef(null);

    const handleRealtimeEvent = useCallback((event) => {
        if (event.initiativeId !== initiativeId) return;

        switch (event.type) {
            case 'comment_added':
                setComments(prev => [...prev, event.comment]);
                scrollToBottom();
                // Check if currentUser is defined before accessing its properties
                if (currentUser && event.comment.author.id !== currentUser.id) {
                    toast.info(`New comment from ${event.comment.author.name}`);
                }
                break;

            case 'user_joined':
                setActiveUsers(prev => {
                    const exists = prev.find(u => u.id === event.user.id);
                    return exists ? prev : [...prev, event.user];
                });
                // Check if currentUser is defined before accessing its properties
                if (currentUser && event.user.id !== currentUser.id) {
                    toast.info(`${event.user.name} joined the collaboration`);
                }
                break;

            case 'user_left':
                setActiveUsers(prev => prev.filter(u => u.id !== event.userId));
                break;

            default:
                break;
        }
    }, [initiativeId, currentUser]); // Added currentUser to dependencies

    const initializeCollaboration = useCallback(async () => {
        setIsLoading(true);
        try {
            // Get current user
            const user = await User.me();
            setCurrentUser(user);

            // Join initiative
            collaborationService.joinInitiative(initiativeId, {
                id: user.id || 'demo-user',
                name: user.full_name || 'Demo User',
                email: user.email || 'demo@pikar.ai',
                avatar: user.avatar_url || null,
                joinedAt: new Date().toISOString()
            });

            // Load existing comments
            const existingComments = collaborationService.getComments(initiativeId);
            setComments(existingComments);

            // Subscribe to real-time events
            // The handleRealtimeEvent function is now wrapped in useCallback,
            // so it's stable and can be used here without causing re-subscriptions
            // unless its own dependencies change.
            const unsubscribe = collaborationService.subscribe(handleRealtimeEvent);

            // Set initial state
            setActiveUsers(collaborationService.getActiveUsers(initiativeId));
            setIsConnected(true);

            return unsubscribe;

        } catch (error) {
            console.error('Failed to initialize collaboration:', error);
            toast.error('Failed to connect to collaboration service');
        } finally {
            setIsLoading(false);
        }
    }, [initiativeId, handleRealtimeEvent]); // Added handleRealtimeEvent to dependencies

    useEffect(() => {
        const unsubscribe = initializeCollaboration();
        return () => {
            if (currentUser && initiativeId) {
                // This cleanup will run when initiativeId or initializeCollaboration changes
                // or when the component unmounts.
                collaborationService.leaveInitiative(initiativeId, currentUser.id);
            }
            if (typeof unsubscribe === 'function') {
                unsubscribe(); // Call the unsubscribe returned from the service
            }
        };
    }, [initiativeId, initializeCollaboration, currentUser]); // Added currentUser to dependencies for cleanup logic

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleSubmitComment = async (e) => {
        e.preventDefault();
        if (!newComment.trim() || !currentUser) return;

        const comment = {
            content: newComment.trim(),
            author: {
                id: currentUser.id || 'demo-user',
                name: currentUser.full_name || 'Demo User',
                email: currentUser.email || 'demo@pikar.ai'
            },
            deliverableId,
            type: 'comment'
        };

        collaborationService.addComment(initiativeId, comment);
        setNewComment('');
    };

    const getUserInitials = (name) => {
        return name.split(' ').map(n => n[0]).join('').toUpperCase();
    };

    const getTimeAgo = (timestamp) => {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInMinutes = Math.floor((now - time) / (1000 * 60));
        
        if (diffInMinutes < 1) return 'Just now';
        if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
        if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
        return format(time, 'MMM d, HH:mm');
    };

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center p-8">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    <span>Connecting to collaboration service...</span>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <MessageCircle className="w-5 h-5" />
                            Real-Time Collaboration
                        </CardTitle>
                        <CardDescription>
                            Live comments and discussion on this initiative
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge className={isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                            {isConnected ? (
                                <>
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Connected
                                </>
                            ) : (
                                <>
                                    <AlertCircle className="w-3 h-3 mr-1" />
                                    Disconnected
                                </>
                            )}
                        </Badge>
                    </div>
                </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
                
                {/* Active Users */}
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <Users className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-700">
                        Active Collaborators ({activeUsers.length})
                    </span>
                    <div className="flex items-center gap-2">
                        {activeUsers.slice(0, 5).map(user => (
                            <div key={user.id} className="relative">
                                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-medium">
                                    {getUserInitials(user.name)}
                                </div>
                                {user.id === currentUser?.id && (
                                    <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                                )}
                            </div>
                        ))}
                        {activeUsers.length > 5 && (
                            <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-gray-600 text-xs font-medium">
                                +{activeUsers.length - 5}
                            </div>
                        )}
                    </div>
                </div>

                {/* Comments Feed */}
                <div className="space-y-4 max-h-96 overflow-y-auto">
                    {comments.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No comments yet. Start the discussion!</p>
                        </div>
                    ) : (
                        comments.map(comment => (
                            <div key={comment.id} className="flex gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                                <div className="w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                                    {getUserInitials(comment.author.name)}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="font-medium text-sm">{comment.author.name}</span>
                                        <span className="text-xs text-gray-500">
                                            {getTimeAgo(comment.timestamp)}
                                        </span>
                                        {comment.deliverableId && (
                                            <Badge variant="outline" className="text-xs">
                                                Deliverable Comment
                                            </Badge>
                                        )}
                                    </div>
                                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                                        {comment.content}
                                    </p>
                                </div>
                            </div>
                        ))
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Comment Input */}
                <form onSubmit={handleSubmitComment} className="flex gap-2">
                    <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                        {currentUser ? getUserInitials(currentUser.full_name || 'Demo User') : 'U'}
                    </div>
                    <div className="flex-1">
                        <Textarea
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            placeholder={deliverableId ? "Comment on this deliverable..." : "Add a comment to this initiative..."}
                            className="resize-none"
                            rows={2}
                            disabled={!isConnected}
                        />
                    </div>
                    <Button 
                        type="submit" 
                        size="sm" 
                        disabled={!newComment.trim() || !isConnected}
                        className="self-end"
                    >
                        <Send className="w-4 h-4" />
                    </Button>
                </form>

                {/* Connection Status */}
                {!isConnected && (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <div className="flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 text-yellow-600" />
                            <span className="text-sm text-yellow-800">
                                Connection lost. Attempting to reconnect...
                            </span>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
