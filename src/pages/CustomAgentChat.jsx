
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { CustomAgent } from '@/api/entities';
import { CustomAgentInteraction } from '@/api/entities';
import { UploadFile } from '@/api/integrations';
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';
import { Bot, Send, User, Upload, Star, FileText, Sparkles, ArrowLeft, Clock, CheckCircle } from 'lucide-react';
import { Toaster, toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';
import { createPageUrl } from '@/utils';
import { Link } from 'react-router-dom';

export default function CustomAgentChat() {
    const [agentId, setAgentId] = useState('');
    const [agent, setAgent] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [contextFile, setContextFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isAgentLoading, setIsAgentLoading] = useState(true);
    const [rating, setRating] = useState(0);
    const [showRating, setShowRating] = useState(false);
    const [lastInteractionId, setLastInteractionId] = useState(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const id = urlParams.get('id');
        setAgentId(id);
    }, []);

    const loadPreviousInteractions = useCallback(async (agentData) => {
        try {
            const interactions = await CustomAgentInteraction.filter({ agent_id: agentData.id }, '-created_date', 10);
            const chatHistory = [];
            
            interactions.reverse().forEach(interaction => {
                chatHistory.push({ role: 'user', content: interaction.user_input });
                chatHistory.push({ role: 'assistant', content: interaction.agent_response });
            });
            
            setMessages(chatHistory);
        } catch (error) {
            console.error("Error loading previous interactions:", error);
        }
    }, []); // No dependencies from component scope needed here, setMessages is stable.

    const loadAgent = useCallback(async () => {
        setIsAgentLoading(true);
        try {
            const agents = await CustomAgent.filter({ id: agentId });
            if (agents && agents.length > 0) {
                setAgent(agents[0]);
                // Load previous interactions for context
                await loadPreviousInteractions(agents[0]);
            } else {
                toast.error("Custom agent not found");
            }
        } catch (error) {
            console.error("Error loading custom agent:", error);
            toast.error("Failed to load custom agent");
        } finally {
            setIsAgentLoading(false);
        }
    }, [agentId, loadPreviousInteractions]); // Depends on agentId state and loadPreviousInteractions callback

    useEffect(() => {
        if (agentId) {
            loadAgent();
        }
    }, [agentId, loadAgent]); // Effect depends on agentId and the memoized loadAgent function

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setContextFile(selectedFile);
            toast.info(`Context file "${selectedFile.name}" selected`);
        }
    };

    const constructCustomPrompt = async (userInput, uploadedFileUrl = null) => {
        let prompt = `${agent.prompt_template}\n\n`;
        
        if (agent.training_data_url) {
            prompt += `**Training Knowledge Base:** You have been trained on specific knowledge available at: ${agent.training_data_url}\n\n`;
        }
        
        if (uploadedFileUrl) {
            prompt += `**Context Document:** Additional context has been provided at: ${uploadedFileUrl}\n\n`;
        }
        
        // Add conversation history for context
        if (messages.length > 0) {
            prompt += `**Previous Conversation Context:**\n`;
            const recentMessages = messages.slice(-6); // Last 6 messages for context
            recentMessages.forEach(msg => {
                prompt += `${msg.role === 'user' ? 'User' : agent.agent_name}: ${msg.content}\n`;
            });
            prompt += `\n`;
        }
        
        prompt += `**Current User Request:** ${userInput}\n\n`;
        prompt += `Please respond as ${agent.agent_name}, using your specialized knowledge and training to provide helpful, accurate, and relevant assistance.`;
        
        return prompt;
    };

    const handleSendMessage = async () => {
        if (!input.trim()) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            let contextFileUrl = null;
            
            // Upload context file if provided
            if (contextFile) {
                toast.info("Uploading context file...");
                const { file_url } = await UploadFile({ file: contextFile });
                contextFileUrl = file_url;
                setContextFile(null);
                toast.success("Context file uploaded");
            }

            // Construct the custom prompt
            const fullPrompt = await constructCustomPrompt(input, contextFileUrl);
            
            // Include both training data and context file in the LLM call
            const fileUrls = [];
            if (agent.training_data_url) fileUrls.push(agent.training_data_url);
            if (contextFileUrl) fileUrls.push(contextFileUrl);

            const filesNote = fileUrls.length ? `\n\nContext files (URLs):\n${fileUrls.join('\n')}` : ''
            const { text: response } = await generateText({ model: openai('gpt-4o-mini'), prompt: fullPrompt + filesNote, temperature: 0.6, maxTokens: 900 });

            const aiMessage = { role: 'assistant', content: response };
            setMessages(prev => [...prev, aiMessage]);

            // Save the interaction
            const interaction = await CustomAgentInteraction.create({
                agent_id: agent.id,
                agent_name: agent.agent_name,
                user_input: input,
                context_file_url: contextFileUrl,
                agent_response: response
            });

            setLastInteractionId(interaction.id);
            setShowRating(true);

            // Update agent usage count
            await CustomAgent.update(agent.id, {
                usage_count: (agent.usage_count || 0) + 1
            });

        } catch (error) {
            console.error("Error with custom agent:", error);
            const errorMessage = { role: 'assistant', content: "I apologize, but I encountered an error processing your request. Please try again." };
            setMessages(prev => [...prev, errorMessage]);
            toast.error("Failed to get response from custom agent");
        } finally {
            setIsLoading(false);
        }
    };

    const handleRating = async (selectedRating) => {
        if (!lastInteractionId) return;
        
        try {
            await CustomAgentInteraction.update(lastInteractionId, {
                interaction_rating: selectedRating
            });
            setRating(selectedRating);
            setShowRating(false);
            toast.success("Thank you for your feedback!");
        } catch (error) {
            console.error("Error saving rating:", error);
            toast.error("Failed to save rating");
        }
    };

    if (isAgentLoading) {
        return (
            <div className="flex justify-center items-center h-screen">
                <div className="text-center">
                    <Bot className="w-12 h-12 animate-pulse mx-auto mb-4 text-blue-500" />
                    <p className="text-lg">Loading your custom agent...</p>
                </div>
            </div>
        );
    }

    if (!agent) {
        return (
            <div className="flex justify-center items-center h-screen">
                <Card>
                    <CardHeader>
                        <CardTitle>Agent Not Found</CardTitle>
                        <CardDescription>The requested custom agent could not be loaded.</CardDescription>
                    </CardHeader>
                    <CardContent className="text-center">
                        <Link to={createPageUrl("CustomAgents")}>
                            <Button variant="outline">
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back to Custom Agents
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
            <Toaster richColors />
            
            {/* Agent Header */}
            <Card className="mb-6">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-lg ${agent.agent_color || 'bg-blue-50'}`}>
                                <Bot className={`w-8 h-8 ${agent.agent_color ? 'text-white' : 'text-blue-600'}`} />
                            </div>
                            <div>
                                <CardTitle className="text-2xl">{agent.agent_name}</CardTitle>
                                <CardDescription className="text-lg mt-1">{agent.agent_description}</CardDescription>
                                <div className="flex items-center gap-4 mt-2">
                                    <Badge className={`${agent.agent_status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                                        {agent.agent_status === 'active' ? <CheckCircle className="w-3 h-3 mr-1" /> : <Clock className="w-3 h-3 mr-1" />}
                                        {agent.agent_status}
                                    </Badge>
                                    <span className="text-sm text-gray-500">
                                        Used {agent.usage_count || 0} times
                                    </span>
                                </div>
                            </div>
                        </div>
                        <Link to={createPageUrl("CustomAgents")}>
                            <Button variant="outline">
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back to Agents
                            </Button>
                        </Link>
                    </div>
                </CardHeader>
            </Card>

            {/* Chat Interface */}
            <Card className="flex-1 flex flex-col">
                <CardHeader className="border-b">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-blue-500" />
                            <CardTitle>Chat with {agent.agent_name}</CardTitle>
                        </div>
                        <Badge variant="outline" className="text-xs">
                            Specialized AI Assistant
                        </Badge>
                    </div>
                </CardHeader>
                
                <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
                    {messages.length === 0 && (
                        <div className="text-center py-12">
                            <div className={`w-16 h-16 rounded-full ${agent.agent_color || 'bg-blue-50'} flex items-center justify-center mx-auto mb-4`}>
                                <Bot className={`w-8 h-8 ${agent.agent_color ? 'text-white' : 'text-blue-600'}`} />
                            </div>
                            <h3 className="text-lg font-semibold mb-2">Welcome to {agent.agent_name}!</h3>
                            <p className="text-gray-600 mb-4">{agent.agent_purpose}</p>
                            <p className="text-sm text-gray-500">Start a conversation by typing a message below.</p>
                        </div>
                    )}
                    
                    <AnimatePresence>
                        {messages.map((message, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex items-start gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
                            >
                                {message.role === 'assistant' && (
                                    <div className={`w-8 h-8 rounded-full ${agent.agent_color || 'bg-blue-50'} flex items-center justify-center flex-shrink-0 mt-1`}>
                                        <Bot className={`w-4 h-4 ${agent.agent_color ? 'text-white' : 'text-blue-600'}`} />
                                    </div>
                                )}
                                
                                <div className={`px-4 py-3 rounded-lg max-w-2xl ${
                                    message.role === 'user' 
                                        ? 'bg-blue-600 text-white' 
                                        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                                }`}>
                                    <div className="whitespace-pre-wrap break-words">
                                        {message.content}
                                    </div>
                                </div>
                                
                                {message.role === 'user' && (
                                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                                        <User className="w-4 h-4 text-white" />
                                    </div>
                                )}
                            </motion.div>
                        ))}
                    </AnimatePresence>
                    
                    {isLoading && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex items-start gap-3"
                        >
                            <div className={`w-8 h-8 rounded-full ${agent.agent_color || 'bg-blue-50'} flex items-center justify-center flex-shrink-0 mt-1`}>
                                <Bot className={`w-4 h-4 ${agent.agent_color ? 'text-white' : 'text-blue-600'}`} />
                            </div>
                            <div className="px-4 py-3 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center">
                                <Sparkles className="w-4 h-4 mr-2 animate-pulse text-blue-500" />
                                <span className="text-gray-600 dark:text-gray-300">
                                    {agent.agent_name} is thinking...
                                </span>
                            </div>
                        </motion.div>
                    )}
                    
                    {/* Rating Prompt */}
                    {showRating && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg"
                        >
                            <Star className="w-5 h-5 text-blue-600" />
                            <span className="text-sm font-medium">How was this response?</span>
                            <div className="flex gap-1">
                                {[1, 2, 3, 4, 5].map((star) => (
                                    <button
                                        key={star}
                                        onClick={() => handleRating(star)}
                                        className="p-1 hover:bg-blue-100 rounded"
                                    >
                                        <Star 
                                            className={`w-4 h-4 ${star <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} 
                                        />
                                    </button>
                                ))}
                            </div>
                        </motion.div>
                    )}
                    
                    <div ref={messagesEndRef} />
                </CardContent>

                {/* Input Area */}
                <div className="p-4 border-t bg-gray-50 dark:bg-gray-800">
                    {contextFile && (
                        <div className="mb-3 flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
                            <FileText className="w-4 h-4 text-blue-600" />
                            <span className="text-sm text-blue-800">{contextFile.name}</span>
                            <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => setContextFile(null)}
                                className="ml-auto h-6 w-6 p-0"
                            >
                                ×
                            </Button>
                        </div>
                    )}
                    
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Input
                                placeholder={`Ask ${agent.agent_name} anything...`}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                                disabled={isLoading}
                                className="pr-12"
                            />
                            <label htmlFor="context-file" className="absolute right-10 top-1/2 -translate-y-1/2 cursor-pointer p-1 hover:bg-gray-100 rounded">
                                <Upload className="w-4 h-4 text-gray-400" />
                                <input
                                    id="context-file"
                                    type="file"
                                    className="hidden"
                                    onChange={handleFileChange}
                                    disabled={isLoading}
                                />
                            </label>
                        </div>
                        <Button 
                            onClick={handleSendMessage} 
                            disabled={isLoading || !input.trim()}
                            className="px-4"
                        >
                            <Send className="w-4 h-4" />
                        </Button>
                    </div>
                    
                    <p className="text-xs text-gray-500 mt-2 text-center">
                        This agent uses specialized knowledge and training. Upload files for additional context.
                    </p>
                </div>
            </Card>
        </div>
    );
}
