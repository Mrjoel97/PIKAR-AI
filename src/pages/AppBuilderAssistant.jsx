
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { agentSDK } from '@/agents';
import { DevelopmentTask } from '@/api/entities';
import MessageBubble from '@/components/chat/MessageBubble';
import { Send, Loader2, Code, ClipboardList, Bot } from 'lucide-react';
import { Toaster, toast } from 'sonner';

export default function AppBuilderAssistantPage() {
    const [conversation, setConversation] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [tasks, setTasks] = useState([]);
    const messagesEndRef = useRef(null);

    const loadTasks = useCallback(async () => {
        try {
            const developmentTasks = await DevelopmentTask.list('-created_date');
            setTasks(developmentTasks);
        } catch (e) {
            console.error("Failed to load tasks:", e);
        }
    }, []);

    useEffect(() => {
        // Start a new conversation when the component mounts
        const initConversation = async () => {
            try {
                const newConversation = await agentSDK.createConversation({
                    agent_name: "AppBuilderAgent",
                    metadata: {
                        name: `App Builder Session - ${new Date().toISOString()}`,
                    }
                });
                setConversation(newConversation);
                setMessages(newConversation.messages || []);
            } catch (e) {
                toast.error("Failed to initialize App Builder Agent.");
                console.error(e);
            }
        };
        initConversation();
        loadTasks();
    }, [loadTasks]);
    
    useEffect(() => {
        if (!conversation) return;

        const unsubscribe = agentSDK.subscribeToConversation(conversation.id, (data) => {
            setMessages(prevMessages => {
                // If the number of messages has increased, reload the tasks.
                if (data.messages && data.messages.length > prevMessages.length) {
                    loadTasks();
                }
                return data.messages || [];
            });
        });

        return () => unsubscribe();
    }, [conversation, loadTasks]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim() || !conversation) return;

        setIsLoading(true);
        try {
            await agentSDK.addMessage(conversation, {
                role: 'user',
                content: input,
            });
            setInput('');
        } catch (error) {
            console.error("Error sending message:", error);
            toast.error("Failed to send message to agent.");
        } finally {
            setIsLoading(false);
        }
    };
    
    const TaskList = () => (
        <Card className="h-full">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <ClipboardList className="w-5 h-5" />
                    Development Backlog
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto">
                {tasks.map(task => (
                    <div key={task.id} className="p-3 border rounded-lg">
                        <p className="font-semibold">{task.task_name}</p>
                        <p className="text-sm text-gray-500">{task.file_path}</p>
                        <p className="text-xs text-gray-400 mt-1">{task.description.substring(0, 50)}...</p>
                    </div>
                ))}
                {tasks.length === 0 && <p className="text-sm text-center text-gray-500 py-8">No tasks yet.</p>}
            </CardContent>
        </Card>
    );

    return (
        <div className="max-w-7xl mx-auto h-[calc(100vh-100px)]">
            <Toaster richColors />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
                <div className="lg:col-span-2 flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg border">
                    <div className="p-4 border-b flex items-center gap-3">
                        <Bot className="w-6 h-6 text-blue-600" />
                        <div>
                            <h1 className="text-lg font-bold">App Builder Assistant</h1>
                            <p className="text-sm text-gray-500">Your AI pair-programmer for building this app.</p>
                        </div>
                    </div>
                    <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                        {messages.map((msg, index) => (
                            <MessageBubble key={index} message={msg} />
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                    <form onSubmit={handleSendMessage} className="p-4 border-t flex gap-2">
                        <Textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="e.g., 'Create a new page to display sales analytics...'"
                            className="flex-1"
                            rows={1}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSendMessage(e);
                                }
                            }}
                        />
                        <Button type="submit" disabled={isLoading || !input.trim()}>
                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        </Button>
                    </form>
                </div>
                <div className="hidden lg:block h-full">
                    <TaskList />
                </div>
            </div>
        </div>
    );
}
