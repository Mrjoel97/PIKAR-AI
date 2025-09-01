import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { SupportTicket } from '@/api/entities';
import { Bot, BookOpen, Loader2, Send, Sparkles, User, Users, Upload } from 'lucide-react';
import { Toaster, toast } from 'sonner';

const pageVariants = {
  hidden: { opacity: 0, y: 24 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 100, damping: 20, staggerChildren: 0.1 }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 120, damping: 18 }
  },
  hover: {
    y: -6,
    rotateX: -2,
    rotateY: 2,
    scale: 1.02,
    boxShadow: '0 12px 40px rgba(6,95,70,0.15)',
    transition: { type: 'spring', stiffness: 150, damping: 15 }
  }
};

export default function CustomerSupport() {
    const [knowledgeBaseFile, setKnowledgeBaseFile] = useState(null);
    const [knowledgeBaseUrl, setKnowledgeBaseUrl] = useState('');
    const [isKbSet, setIsKbSet] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setKnowledgeBaseFile(selectedFile);
        }
    };

    const constructPrompt = (userQuery) => {
        return `You are the PIKAR AI Customer Support Agent. Your primary function is to provide accurate answers based *only* on the information contained within the provided Knowledge Base document. The document is available at the URL below.

        If the answer to the user's question cannot be found in the Knowledge Base, you must clearly state: "I'm sorry, but I don't have enough information in the knowledge base to answer that question." Do not make up information or use external knowledge.

        **Knowledge Base Document URL:**
        ---
        ${knowledgeBaseUrl}
        ---

        **Customer's Question:**
        ---
        ${userQuery}
        ---

        Please provide a helpful and accurate answer based on the knowledge base document.`;
    };

    const handleSendMessage = async () => {
        if (!input.trim()) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const fullPrompt = constructPrompt(input);
            const response = await InvokeLLM({
                prompt: fullPrompt,
                file_urls: [knowledgeBaseUrl]
            });
            const aiMessage = { role: 'assistant', content: response };
            setMessages(prev => [...prev, aiMessage]);

            await SupportTicket.create({
                customer_query: input,
                ai_response: response,
                knowledge_base_summary: `KB File: ${knowledgeBaseFile?.name || 'Uploaded Document'}`,
                status: 'open',
            });
        } catch (error) {
            console.error("Error with support agent:", error);
            const errorMessage = { role: 'assistant', content: "Sorry, I encountered an error. Please try again." };
            setMessages(prev => [...prev, errorMessage]);
            toast.error("Failed to get response from AI agent.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleSetKb = async () => {
        if (!knowledgeBaseFile) {
            toast.error("Please select a knowledge base file to upload.");
            return;
        }
        setIsLoading(true);
        try {
            toast.info("Uploading knowledge base...");
            const { file_url } = await UploadFile({ file: knowledgeBaseFile });
            setKnowledgeBaseUrl(file_url);
            setIsKbSet(true);
            toast.success("Knowledge base is ready. You can now start the chat.");
        } catch(e) {
            toast.error("Failed to upload knowledge base. Please try again.");
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isKbSet) {
        return (
            <div className="max-w-4xl mx-auto min-h-screen bg-pikar-hero p-6">
                <Toaster richColors />
                <motion.div
                    initial="hidden"
                    animate="show"
                    variants={pageVariants}
                >
                    {/* Premium Header */}
                    <motion.div 
                        className="text-center mb-8"
                        variants={cardVariants}
                    >
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-700 bg-clip-text text-transparent flex items-center justify-center gap-3 mb-4">
                            <Users className="w-8 h-8 text-emerald-900" />
                            Customer Support Agent
                        </h1>
                        <p className="text-xl text-emerald-700">
                            Set up your knowledge base to provide intelligent customer support
                        </p>
                    </motion.div>

                    <motion.div variants={cardVariants} whileHover="hover">
                        <Card className="shadow-soft border-emerald-100">
                            <CardHeader>
                                <div className="flex items-center gap-3">
                                    <div className="p-3 bg-emerald-50 rounded-xl">
                                        <BookOpen className="w-6 h-6 text-emerald-600" />
                                    </div>
                                    <div>
                                        <CardTitle className="text-emerald-900">Set Up Knowledge Base</CardTitle>
                                        <CardDescription className="text-emerald-700">
                                            Upload your product documentation, FAQs, or any relevant text file. The AI will use this as its sole source of information.
                                        </CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center justify-center w-full">
                                    <motion.label 
                                        htmlFor="file-upload" 
                                        className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-emerald-200 rounded-2xl cursor-pointer bg-emerald-50/50 hover:bg-emerald-50 transition-all duration-300"
                                        whileHover={{ scale: 1.01, rotateX: 1 }}
                                        whileTap={{ scale: 0.99 }}
                                    >
                                        <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                            <motion.div
                                                animate={{ y: [0, -4, 0] }}
                                                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                                            >
                                                <Upload className="w-10 h-10 mb-3 text-emerald-500" />
                                            </motion.div>
                                            <p className="mb-2 text-sm text-emerald-700">
                                                <span className="font-semibold">Click to upload</span> or drag and drop
                                            </p>
                                            <p className="text-xs text-emerald-600">TXT, MD, PDF, or DOCX files</p>
                                            {knowledgeBaseFile && (
                                                <motion.p 
                                                    className="text-sm text-emerald-800 mt-2 font-medium"
                                                    initial={{ opacity: 0, scale: 0.8 }}
                                                    animate={{ opacity: 1, scale: 1 }}
                                                >
                                                    {knowledgeBaseFile.name}
                                                </motion.p>
                                            )}
                                        </div>
                                        <Input id="file-upload" type="file" className="hidden" onChange={handleFileChange} />
                                    </motion.label>
                                </div>
                                <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                                    <Button 
                                        onClick={handleSetKb} 
                                        className="w-full bg-emerald-900 hover:bg-emerald-800 text-white rounded-2xl h-12" 
                                        disabled={isLoading}
                                    >
                                        {isLoading ? (
                                            <motion.div
                                                animate={{ rotate: 360 }}
                                                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                            >
                                                <Loader2 className="w-4 h-4 mr-2" />
                                            </motion.div>
                                        ) : (
                                            <Sparkles className="w-4 h-4 mr-2" />
                                        )}
                                        Set Knowledge Base & Start Chat
                                    </Button>
                                </motion.div>
                            </CardContent>
                        </Card>
                    </motion.div>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto h-[calc(100vh-10rem)] flex flex-col min-h-screen bg-pikar-hero p-6">
            <Toaster richColors />
            
            {/* Enhanced Header */}
            <motion.div 
                className="text-center mb-6"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 120, damping: 18 }}
            >
                <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-900 to-emerald-700 bg-clip-text text-transparent flex items-center justify-center gap-3">
                    <Users className="w-7 h-7 text-emerald-900" />
                    Customer Support Chat
                </h1>
            </motion.div>

            <motion.div 
                className="flex-1 flex flex-col"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', stiffness: 120, damping: 18 }}
            >
                <Card className="flex-1 flex flex-col shadow-soft border-emerald-100">
                    <CardHeader className="flex flex-row items-center justify-between border-b border-emerald-100">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-emerald-50 rounded-xl">
                                <Users className="w-6 h-6 text-emerald-600" />
                            </div>
                            <div>
                                <CardTitle className="text-emerald-900">Live Support Chat</CardTitle>
                                <CardDescription className="text-emerald-700">
                                    Using KB: {knowledgeBaseFile?.name || 'Uploaded Document'}
                                </CardDescription>
                            </div>
                        </div>
                        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                            <Button 
                                variant="outline" 
                                onClick={() => { 
                                    setIsKbSet(false); 
                                    setMessages([]); 
                                    setKnowledgeBaseFile(null); 
                                    setKnowledgeBaseUrl(''); 
                                }}
                                className="border-emerald-200 text-emerald-900 hover:bg-emerald-50"
                            >
                                Change Knowledge Base
                            </Button>
                        </motion.div>
                    </CardHeader>
                    
                    <CardContent className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
                        <AnimatePresence>
                            {messages.map((message, index) => (
                                <motion.div
                                    key={index}
                                    initial={{ opacity: 0, y: 20, scale: 0.9 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: -20, scale: 0.9 }}
                                    transition={{ type: 'spring', stiffness: 200, damping: 20 }}
                                    className={`flex items-start gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
                                >
                                    {message.role === 'assistant' && (
                                        <motion.div 
                                            className="p-2 bg-emerald-100 rounded-xl"
                                            whileHover={{ rotate: [0, -5, 5, 0] }}
                                            transition={{ duration: 0.5 }}
                                        >
                                            <Bot className="w-6 h-6 text-emerald-600" />
                                        </motion.div>
                                    )}
                                    <motion.div 
                                        className={`px-4 py-3 rounded-2xl max-w-lg ${
                                            message.role === 'user' 
                                                ? 'bg-emerald-900 text-white' 
                                                : 'bg-white border border-emerald-100 shadow-soft'
                                        }`}
                                        whileHover={{ scale: 1.01 }}
                                        transition={{ type: 'spring', stiffness: 300 }}
                                    >
                                        {message.content}
                                    </motion.div>
                                    {message.role === 'user' && (
                                        <motion.div 
                                            className="p-2 bg-gray-100 rounded-xl"
                                            whileHover={{ rotate: [0, 5, -5, 0] }}
                                            transition={{ duration: 0.5 }}
                                        >
                                            <User className="w-6 h-6 text-gray-600" />
                                        </motion.div>
                                    )}
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        
                        {isLoading && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex items-start gap-3"
                            >
                                <div className="p-2 bg-emerald-100 rounded-xl">
                                    <Bot className="w-6 h-6 text-emerald-600" />
                                </div>
                                <div className="px-4 py-3 rounded-2xl bg-white border border-emerald-100 shadow-soft flex items-center">
                                    <motion.div
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                    >
                                        <Loader2 className="w-4 h-4 mr-2 text-emerald-600"/>
                                    </motion.div>
                                    <span className="text-emerald-700">Thinking...</span>
                                </div>
                            </motion.div>
                        )}
                        <div ref={messagesEndRef} />
                    </CardContent>
                    
                    <div className="p-4 border-t border-emerald-100 bg-emerald-50/30">
                        <motion.div 
                            className="relative"
                            whileFocus={{ scale: 1.01 }}
                        >
                            <Input
                                placeholder="Ask a question..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                                disabled={isLoading}
                                className="pr-12 border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-2xl"
                            />
                            <motion.div
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                            >
                                <Button 
                                    size="icon" 
                                    className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 bg-emerald-900 hover:bg-emerald-800 rounded-xl" 
                                    onClick={handleSendMessage} 
                                    disabled={isLoading}
                                >
                                    <Send className="w-4 h-4" />
                                </Button>
                            </motion.div>
                        </motion.div>
                    </div>
                </Card>
            </motion.div>
        </div>
    );
}