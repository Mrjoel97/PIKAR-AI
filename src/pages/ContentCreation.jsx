
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { GeneratedContent } from '@/api/entities';
import { BookCopy, BrainCircuit, Loader2, Save, Sparkles, Wand2, Upload } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Toaster, toast } from 'sonner';
import AgentGateway from '../components/AgentGateway';
import KnowledgeSelector from '../components/knowledge/KnowledgeSelector';

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

export default function ContentCreation() {
    const [prompt, setPrompt] = useState('');
    const [format, setFormat] = useState('blog_post');
    const [tone, setTone] = useState('professional');
    const [selectedKnowledgeDocs, setSelectedKnowledgeDocs] = useState([]);
    const [file, setFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [generatedContent, setGeneratedContent] = useState('');
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        const gatewayInput = sessionStorage.getItem('agentGatewayInput');
        if (gatewayInput) {
            try {
                const parsedInput = JSON.parse(gatewayInput);
                const stringifiedInput = typeof parsedInput === 'string' ? parsedInput : JSON.stringify(parsedInput, null, 2);
                setPrompt(`Based on the following analysis, create content:\n\n${stringifiedInput}`);
                toast.info("Received input from another agent.");
            } catch (e) {
                console.error("Failed to parse gateway input", e);
            } finally {
                sessionStorage.removeItem('agentGatewayInput');
            }
        }
    }, []);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            toast.info(`File "${selectedFile.name}" selected.`);
        }
    };

    const constructPrompt = (uploadedFileUrl, knowledgeFileUrls) => {
        let structuredPrompt = `You are the PIKAR AI Content Creation Agent. Generate a high-quality piece of content based on the following request.\n\n`;
        
        if (uploadedFileUrl) {
            structuredPrompt += `**Primary Reference Document:** ${uploadedFileUrl}\n`;
        }
        
        if (knowledgeFileUrls && knowledgeFileUrls.length > 0) {
            structuredPrompt += `**Additional Knowledge Base References:** ${knowledgeFileUrls.join(', ')}\n`;
        }
        
        structuredPrompt += `**Content Format:** ${format.replace(/_/g, ' ')}\n`;
        structuredPrompt += `**Desired Tone:** ${tone}\n\n`;
        structuredPrompt += `**Core Subject/Prompt:**\n---\n${prompt}\n---\n\n`;
        structuredPrompt += `Please generate the content now, incorporating insights from all provided sources where relevant.`;
        return structuredPrompt;
    };

    const handleGenerate = async () => {
        if (!prompt) {
            toast.error("Please enter a prompt to generate content.");
            return;
        }
        setIsLoading(true);
        setGeneratedContent('');
        setFileUrl('');
        let uploadedFileUrl = '';

        try {
            if (file) {
                toast.info("Uploading file...");
                const { file_url } = await UploadFile({ file });
                uploadedFileUrl = file_url;
                setFileUrl(uploadedFileUrl);
                toast.success("File upload complete.");
            }

            const knowledgeFileUrls = selectedKnowledgeDocs.map(doc => doc.file_url);
            
            const allFileUrls = [uploadedFileUrl, ...knowledgeFileUrls].filter(Boolean);

            const fullPrompt = constructPrompt(uploadedFileUrl, knowledgeFileUrls);
            const response = await InvokeLLM({
                prompt: fullPrompt,
                file_urls: allFileUrls.length > 0 ? allFileUrls : undefined,
            });
            setGeneratedContent(response);
        } catch (error) {
            console.error("Error generating content:", error);
            toast.error("Failed to generate content. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!generatedContent) {
            toast.error("No content to save.");
            return;
        }
        setIsSaving(true);
        try {
            await GeneratedContent.create({
                agent: "Content Creation",
                prompt: prompt,
                output: generatedContent,
                settings: { format, tone },
                file_url: fileUrl,
                knowledge_base_docs: selectedKnowledgeDocs.map(doc => ({
                    id: doc.id,
                    name: doc.document_name,
                    url: doc.file_url
                })),
            });
            toast.success("Content saved successfully!");
        } catch (error) {
            console.error("Error saving content:", error);
            toast.error("Failed to save content. Please try again.");
        }
        setIsSaving(false);
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start max-w-7xl mx-auto min-h-screen bg-pikar-hero p-6">
            <Toaster richColors />
            
            <div className="lg:col-span-3">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: 'spring', stiffness: 120, damping: 18 }}
                    className="text-center mb-8"
                >
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-700 bg-clip-text text-transparent flex items-center justify-center gap-3 mb-4">
                        <BrainCircuit className="w-8 h-8 text-emerald-900" />
                        Content Creation Agent
                    </h1>
                    <p className="text-xl text-emerald-700">
                        Generate high-quality content with AI-powered creativity
                    </p>
                </motion.div>
            </div>

            <motion.div 
                className="lg:col-span-1 flex flex-col gap-8"
                initial="hidden"
                animate="show"
                variants={pageVariants}
            >
                <motion.div variants={cardVariants} whileHover="hover">
                    <Card className="shadow-soft border-emerald-100">
                        <CardHeader>
                            <div className="flex items-center gap-3">
                                <div className="p-3 bg-emerald-50 rounded-xl">
                                    <BrainCircuit className="w-6 h-6 text-emerald-600" />
                                </div>
                                <div>
                                    <CardTitle className="text-emerald-900">Content Creation</CardTitle>
                                    <CardDescription className="text-emerald-700">
                                        Define your content requirements and optionally upload a context document.
                                    </CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="prompt" className="text-emerald-900 font-medium">Your Prompt</Label>
                                <Textarea
                                    id="prompt"
                                    placeholder="e.g., 'Summarize the key findings from the attached report'"
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    className="h-32 border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl resize-none"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="file-upload" className="text-emerald-900 font-medium">Context Document (Optional)</Label>
                                <div className="flex items-center justify-center w-full">
                                    <motion.label 
                                        htmlFor="file-upload" 
                                        className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-emerald-200 rounded-xl cursor-pointer bg-emerald-50/50 hover:bg-emerald-50 transition-all duration-300"
                                        whileHover={{ scale: 1.01, rotateX: 1 }}
                                        whileTap={{ scale: 0.99 }}
                                    >
                                        <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                            <motion.div
                                                animate={{ y: [0, -2, 0] }}
                                                transition={{ duration: 2, repeat: Infinity }}
                                            >
                                                <Upload className="w-8 h-8 mb-2 text-emerald-500" />
                                            </motion.div>
                                            <p className="text-xs text-emerald-600 px-2 truncate">
                                                {file ? file.name : "Click to upload or drag and drop"}
                                            </p>
                                        </div>
                                        <Input id="file-upload" type="file" className="hidden" onChange={handleFileChange} />
                                    </motion.label>
                                </div>
                            </div>

                            <KnowledgeSelector
                                onSelectionChange={setSelectedKnowledgeDocs}
                                selectedDocuments={selectedKnowledgeDocs}
                                allowMultiple={true}
                            />
                            
                            <div className="grid grid-cols-1 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="format" className="text-emerald-900 font-medium">Content Format</Label>
                                    <Select value={format} onValueChange={setFormat}>
                                        <SelectTrigger id="format" className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl">
                                            <SelectValue placeholder="Select a format" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="blog_post">Blog Post</SelectItem>
                                            <SelectItem value="social_media_update">Social Media Update</SelectItem>
                                            <SelectItem value="marketing_email">Marketing Email</SelectItem>
                                            <SelectItem value="video_script">Video Script</SelectItem>
                                            <SelectItem value="ad_copy">Ad Copy</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                
                                <div className="space-y-2">
                                    <Label htmlFor="tone" className="text-emerald-900 font-medium">Tone of Voice</Label>
                                    <Select value={tone} onValueChange={setTone}>
                                        <SelectTrigger id="tone" className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl">
                                            <SelectValue placeholder="Select a tone" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="professional">Professional</SelectItem>
                                            <SelectItem value="casual">Casual</SelectItem>
                                            <SelectItem value="witty">Witty</SelectItem>
                                            <SelectItem value="persuasive">Persuasive</SelectItem>
                                            <SelectItem value="empathetic">Empathetic</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                                <Button 
                                    onClick={handleGenerate} 
                                    disabled={isLoading} 
                                    className="w-full bg-emerald-900 hover:bg-emerald-800 text-white rounded-xl h-12"
                                >
                                    {isLoading ? (
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                        >
                                            <Loader2 className="w-4 h-4 mr-2" />
                                        </motion.div>
                                    ) : (
                                        <Wand2 className="w-4 h-4 mr-2" />
                                    )}
                                    Generate Content
                                </Button>
                            </motion.div>
                        </CardContent>
                    </Card>
                </motion.div>
                
                <motion.div variants={cardVariants}>
                    <AgentGateway agentName="Content Creation" lastOutput={generatedContent} />
                </motion.div>
            </motion.div>

            <div className="lg:col-span-2">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ type: 'spring', stiffness: 120, damping: 18, delay: 0.2 }}
                >
                    <Card className="min-h-[600px] shadow-soft border-emerald-100">
                        <CardHeader className="flex flex-row items-center justify-between border-b border-emerald-100">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-emerald-50 rounded-xl">
                                    <BookCopy className="w-6 h-6 text-emerald-600" />
                                </div>
                                <div>
                                    <CardTitle className="text-emerald-900">Generated Output</CardTitle>
                                    <CardDescription className="text-emerald-700">
                                        Review the AI-generated content below.
                                    </CardDescription>
                                </div>
                            </div>
                            {generatedContent && !isLoading && (
                                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                                    <Button 
                                        onClick={handleSave} 
                                        disabled={isSaving} 
                                        variant="outline"
                                        className="border-emerald-200 text-emerald-900 hover:bg-emerald-50"
                                    >
                                        {isSaving ? (
                                            <motion.div
                                                animate={{ rotate: 360 }}
                                                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                            >
                                                <Loader2 className="w-4 h-4 mr-2" />
                                            </motion.div>
                                        ) : (
                                            <Save className="w-4 h-4 mr-2" />
                                        )}
                                        Save
                                    </Button>
                                </motion.div>
                            )}
                        </CardHeader>
                        <CardContent className="p-6">
                            <AnimatePresence mode="wait">
                                {isLoading && (
                                    <motion.div
                                        key="loading"
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.8 }}
                                        className="flex flex-col items-center justify-center text-center h-64"
                                    >
                                        <motion.div
                                            animate={{ 
                                                rotate: 360,
                                                scale: [1, 1.1, 1]
                                            }}
                                            transition={{ 
                                                rotate: { duration: 2, repeat: Infinity, ease: 'linear' },
                                                scale: { duration: 1, repeat: Infinity }
                                            }}
                                        >
                                            <Sparkles className="w-12 h-12 text-emerald-500" />
                                        </motion.div>
                                        <p className="mt-4 font-medium text-emerald-800">AI is thinking...</p>
                                        <p className="text-sm text-emerald-600">Generating your content, please wait.</p>
                                    </motion.div>
                                )}
                                
                                {generatedContent && !isLoading && (
                                    <motion.div
                                        key="content"
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ type: 'spring', stiffness: 120, damping: 18 }}
                                        className="prose prose-emerald max-w-none"
                                    >
                                        <ReactMarkdown>{generatedContent}</ReactMarkdown>
                                    </motion.div>
                                )}
                                
                                {!generatedContent && !isLoading && (
                                    <motion.div
                                        key="empty"
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        className="flex flex-col items-center justify-center text-center h-64"
                                    >
                                        <motion.div 
                                            className="p-4 bg-emerald-50 rounded-full mb-4"
                                            whileHover={{ scale: 1.05, rotate: [0, -5, 5, 0] }}
                                            transition={{ duration: 0.3 }}
                                        >
                                            <Wand2 className="w-10 h-10 text-emerald-500" />
                                        </motion.div>
                                        <p className="mt-4 font-medium text-emerald-800">Your content will appear here</p>
                                        <p className="text-sm text-emerald-600">Fill out the form and click "Generate Content".</p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </CardContent>
                    </Card>
                </motion.div>
            </div>
        </div>
    );
}
