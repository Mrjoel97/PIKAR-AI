import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { StrategicAnalysis } from '@/api/entities';
import { BookCopy, Lightbulb, Loader2, Save, Sparkles, Wand2, Upload, Info } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Toaster, toast } from 'sonner';
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import AgentGateway from '@/components/AgentGateway';
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

export default function StrategicPlanning() {
    const [targetCompany, setTargetCompany] = useState('');
    const [prompt, setPrompt] = useState('');
    const [analysisType, setAnalysisType] = useState('SWOT Analysis');
    const [file, setFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [analysisResult, setAnalysisResult] = useState('');
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [selectedKnowledgeDocs, setSelectedKnowledgeDocs] = useState([]);

    useEffect(() => {
        const gatewayInput = sessionStorage.getItem('agentGatewayInput');
        if (gatewayInput) {
            try {
                const parsedInput = JSON.parse(gatewayInput);
                if (typeof parsedInput === 'string') {
                    setTargetCompany(parsedInput);
                } else if (parsedInput.company_name) {
                    setTargetCompany(parsedInput.company_name);
                }
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

    const getFrameworkTooltip = (analysisType) => {
        const tooltips = {
            'SWOT Analysis': 'SWOT (Strengths, Weaknesses, Opportunities, Threats) is a classic strategic planning framework that provides a comprehensive view of internal capabilities and external market conditions. Developed at Stanford in the 1960s.',
            'PESTEL Analysis': 'PESTEL examines Political, Economic, Social, Technological, Environmental, and Legal factors that affect business strategy. Essential for understanding macro-environmental influences.',
            'Competitor Analysis': 'Systematic evaluation of competitors strategies, strengths, and market positions. Uses competitive intelligence frameworks to identify market opportunities and threats.',
            'Five Forces Analysis': 'Michael Porter framework analyzing industry structure through: competitive rivalry, supplier power, buyer power, threat of substitution, and barriers to entry.',
        };
        return tooltips[analysisType] || 'Strategic analysis framework';
    };

    const constructPrompt = (uploadedFileUrl, knowledgeFileUrls) => {
        let structuredPrompt = `You are the PIKAR AI Strategic Planning Agent. Conduct a comprehensive ${analysisType} for ${targetCompany}.\n\n`;

        if (uploadedFileUrl) {
            structuredPrompt += `**Primary Analysis Document:** ${uploadedFileUrl}\n`;
        }

        if (knowledgeFileUrls && knowledgeFileUrls.length > 0) {
            structuredPrompt += `**Additional Knowledge Base References:** ${knowledgeFileUrls.join(', ')}\n`;
        }

        structuredPrompt += `**Analysis Type:** ${analysisType}\n`;
        structuredPrompt += `**Target Company/Market:** ${targetCompany}\n\n`;
        structuredPrompt += `**Specific Requirements:**\n${prompt}\n\n`;
        structuredPrompt += `Please provide a detailed ${analysisType} with actionable insights and strategic recommendations.`;
        return structuredPrompt;
    };

    const handleAnalyze = async () => {
        if (!targetCompany || !prompt) {
            toast.error("Please provide target company and analysis requirements.");
            return;
        }

        setIsLoading(true);
        setAnalysisResult('');
        setFileUrl('');
        let uploadedFileUrl = '';

        try {
            if (file) {
                toast.info("Uploading document...");
                const { file_url } = await UploadFile({ file });
                uploadedFileUrl = file_url;
                setFileUrl(uploadedFileUrl);
                toast.success("Document uploaded successfully.");
            }

            const knowledgeFileUrls = selectedKnowledgeDocs.map(doc => doc.file_url);
            const allFileUrls = [uploadedFileUrl, ...knowledgeFileUrls].filter(Boolean);

            const fullPrompt = constructPrompt(uploadedFileUrl, knowledgeFileUrls);
            const response = await InvokeLLM({
                prompt: fullPrompt,
                file_urls: allFileUrls.length > 0 ? allFileUrls : undefined,
            });
            setAnalysisResult(response);
        } catch (error) {
            console.error("Error conducting analysis:", error);
            toast.error("Failed to conduct strategic analysis. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!analysisResult) {
            toast.error("No analysis to save.");
            return;
        }
        setIsSaving(true);
        try {
            await StrategicAnalysis.create({
                agent: "Strategic Planning",
                analysis_type: analysisType,
                target: targetCompany,
                file_url: fileUrl,
                analysis_output: analysisResult,
                knowledge_base_docs: selectedKnowledgeDocs.map(doc => ({
                    id: doc.id,
                    name: doc.document_name,
                    url: doc.file_url
                })),
            });
            toast.success("Strategic analysis saved successfully!");
        } catch (error) {
            console.error("Error saving analysis:", error);
            toast.error("Failed to save analysis. Please try again.");
        }
        setIsSaving(false);
    };

    return (
        <TooltipProvider>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start max-w-7xl mx-auto min-h-screen bg-pikar-hero p-6">
                <Toaster richColors />
                
                {/* Enhanced Header */}
                <div className="lg:col-span-3">
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ type: 'spring', stiffness: 120, damping: 18 }}
                        className="text-center mb-8"
                    >
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-700 bg-clip-text text-transparent flex items-center justify-center gap-3 mb-4">
                            <Lightbulb className="w-8 h-8 text-emerald-900" />
                            Strategic Planning Agent
                        </h1>
                        <p className="text-xl text-emerald-700">
                            Generate comprehensive strategic analyses with AI-powered insights
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
                                        <Lightbulb className="w-6 h-6 text-emerald-600" />
                                    </div>
                                    <div>
                                        <CardTitle className="text-emerald-900">Strategic Analysis</CardTitle>
                                        <CardDescription className="text-emerald-700">
                                            Configure your strategic analysis parameters
                                        </CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="space-y-2">
                                    <Label htmlFor="targetCompany" className="text-emerald-900 font-medium">Target Company / Market</Label>
                                    <Input
                                        id="targetCompany"
                                        placeholder="e.g., 'Tesla, Inc.' or 'Global EV Market'"
                                        value={targetCompany}
                                        onChange={(e) => setTargetCompany(e.target.value)}
                                        className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                    />
                                </div>
                                
                                <div className="space-y-2">
                                    <Label htmlFor="prompt" className="text-emerald-900 font-medium">Specific Requirements</Label>
                                    <Input
                                        id="prompt"
                                        placeholder="e.g., 'Focus on their sustainability initiatives and challenges.'"
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                        className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                    />
                                </div>
                                
                                <div className="space-y-2">
                                    <Label htmlFor="analysisType" className="text-emerald-900 font-medium">Analysis Type</Label>
                                    <Select value={analysisType} onValueChange={(value) => { setAnalysisType(value); setAnalysisResult(''); }}>
                                        <SelectTrigger id="analysisType" className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl">
                                            <SelectValue placeholder="Select an analysis type" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {[
                                                'SWOT Analysis',
                                                'PESTEL Analysis', 
                                                'Competitor Analysis',
                                                'Five Forces Analysis'
                                            ].map(type => (
                                                <SelectItem key={type} value={type}>
                                                    <div className="flex items-center gap-2">
                                                        {type}
                                                        <Tooltip>
                                                            <TooltipTrigger asChild>
                                                                <Info className="w-3 h-3 text-emerald-400" />
                                                            </TooltipTrigger>
                                                            <TooltipContent side="right" className="max-w-xs bg-emerald-50 border-emerald-200">
                                                                <p className="text-emerald-900">{getFrameworkTooltip(type)}</p>
                                                            </TooltipContent>
                                                        </Tooltip>
                                                    </div>
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="file-upload" className="text-emerald-900 font-medium">Context Document (Optional)</Label>
                                    <div className="flex items-center justify-center w-full">
                                        <motion.label 
                                            htmlFor="file-upload" 
                                            className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-emerald-200 rounded-xl cursor-pointer bg-emerald-50/50 hover:bg-emerald-50"
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
                                                    {file ? file.name : "Upload additional context"}
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
                                    filterCategory="strategic"
                                />

                                <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                                    <Button 
                                        onClick={handleAnalyze} 
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
                                        Generate Analysis
                                    </Button>
                                </motion.div>
                            </CardContent>
                        </Card>
                    </motion.div>

                    <motion.div variants={cardVariants}>
                        <AgentGateway agentName="Strategic Planning" lastOutput={analysisResult} />
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
                                        <CardTitle className="text-emerald-900">Analysis Report</CardTitle>
                                        <CardDescription className="text-emerald-700">
                                            Review the AI-generated strategic analysis below
                                        </CardDescription>
                                    </div>
                                </div>
                                {analysisResult && !isLoading && (
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
                                            Save Report
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
                                            className="flex flex-col items-center justify-center text-center h-80"
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
                                            <p className="mt-4 font-medium text-emerald-800">AI is analyzing...</p>
                                            <p className="text-sm text-emerald-600">Fetching data and generating your report.</p>
                                        </motion.div>
                                    )}
                                    
                                    {analysisResult && !isLoading && (
                                        <motion.div
                                            key="result"
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ type: 'spring', stiffness: 120, damping: 18 }}
                                            className="prose prose-emerald max-w-none"
                                        >
                                            <ReactMarkdown>{analysisResult}</ReactMarkdown>
                                        </motion.div>
                                    )}
                                    
                                    {!analysisResult && !isLoading && (
                                        <motion.div
                                            key="empty"
                                            initial={{ opacity: 0, scale: 0.8 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            className="flex flex-col items-center justify-center text-center h-80"
                                        >
                                            <motion.div 
                                                className="p-4 bg-emerald-50 rounded-full mb-4"
                                                whileHover={{ scale: 1.05, rotate: [0, -5, 5, 0] }}
                                                transition={{ duration: 0.3 }}
                                            >
                                                <Lightbulb className="w-10 h-10 text-emerald-500" />
                                            </motion.div>
                                            <p className="mt-4 font-medium text-emerald-800">Your strategic report will appear here</p>
                                            <p className="text-sm text-emerald-600">Define your target, requirements, and analysis type to begin.</p>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </CardContent>
                        </Card>
                    </motion.div>
                </div>
            </div>
        </TooltipProvider>
    );
}