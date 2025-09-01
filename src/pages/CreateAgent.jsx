
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { UploadFile } from '@/api/integrations';
import { CustomAgent } from '@/api/entities';
import { Bot, Upload, Loader2, ArrowLeft, FileText, Link as LinkIcon, Pilcrow } from 'lucide-react';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { Toaster, toast } from 'sonner';

export default function CreateAgent() {
    const [agentData, setAgentData] = useState({
        agent_name: '',
        agent_description: '',
        agent_purpose: '',
        prompt_template: '',
        agent_icon: 'Bot',
        agent_color: 'blue'
    });
    const [trainingSources, setTrainingSources] = useState([]);
    const [textInput, setTextInput] = useState('');
    const [urlInput, setUrlInput] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    const handleAddFile = (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            const newSources = files.map(file => ({ type: 'file', source: file, name: file.name }));
            setTrainingSources(prev => [...prev, ...newSources]);
            toast.info(`${files.length} file(s) added.`);
        }
    };

    const handleAddUrl = () => {
        if (!urlInput.startsWith('http')) {
            toast.error("Please enter a valid URL.");
            return;
        }
        setTrainingSources(prev => [...prev, { type: 'url', source: urlInput, name: urlInput }]);
        setUrlInput('');
        toast.info("URL source added.");
    };

    const handleAddText = () => {
        if (textInput.trim().length < 50) {
            toast.error("Text input must be at least 50 characters.");
            return;
        }
        const textSnippet = textInput.substring(0, 40) + '...';
        setTrainingSources(prev => [...prev, { type: 'text', source: textInput, name: `Text: "${textSnippet}"` }]);
        setTextInput('');
        toast.info("Text source added.");
    };


    const handleCreateAgent = async () => {
        if (!agentData.agent_name || !agentData.agent_description || !agentData.agent_purpose) {
            toast.error("Please fill in all agent detail fields.");
            return;
        }
        if (trainingSources.length === 0) {
            toast.error("Please add at least one training data source.");
            return;
        }

        setIsCreating(true);
        toast.info("Processing training sources...");

        try {
            const processedSources = await Promise.all(
                trainingSources.map(async (source) => {
                    if (source.type === 'file') {
                        const { file_url } = await UploadFile({ file: source.source });
                        return { type: 'file', source: file_url };
                    }
                    if (source.type === 'text') {
                        const file = new Blob([source.source], { type: 'text/plain' });
                        const { file_url } = await UploadFile({ file: new File([file], "text-source.txt") });
                        return { type: 'text', source: file_url };
                    }
                    return source; // URL sources are already processed
                })
            );

            toast.info("Deploying agent...");
            await CustomAgent.create({
                ...agentData,
                training_sources: processedSources,
                agent_status: 'active'
            });
            
            toast.success("Custom agent created successfully!");
            // Reset form
            setAgentData({ agent_name: '', agent_description: '', agent_purpose: '', prompt_template: '', agent_icon: 'Bot', agent_color: 'blue' });
            setTrainingSources([]);
        } catch (error) {
            console.error("Error creating agent:", error);
            toast.error("Failed to create agent. Please try again.");
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto">
            <Toaster richColors />
            
            <header className="mb-8">
                <div className="flex items-center gap-4 mb-4">
                    <Link to={createPageUrl("CustomAgents")}>
                        <Button variant="outline" size="icon">
                            <ArrowLeft className="w-4 h-4" />
                        </Button>
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold">Create Custom Agent</h1>
                        <p className="text-gray-600">Deploy a specialized AI agent with advanced training data.</p>
                    </div>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>1. Agent Details</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Agent Name *</Label>
                                <Input id="name" value={agentData.agent_name} onChange={(e) => setAgentData({...agentData, agent_name: e.target.value})} placeholder="e.g., Legal Document Reviewer" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="color">Agent Color</Label>
                                <Select value={agentData.agent_color} onValueChange={(value) => setAgentData({...agentData, agent_color: value})}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="blue">Blue</SelectItem>
                                        <SelectItem value="green">Green</SelectItem>
                                        <SelectItem value="purple">Purple</SelectItem>
                                        <SelectItem value="orange">Orange</SelectItem>
                                        <SelectItem value="red">Red</SelectItem>
                                        <SelectItem value="teal">Teal</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="description">Agent Description *</Label>
                            <Input id="description" value={agentData.agent_description} onChange={(e) => setAgentData({...agentData, agent_description: e.target.value})} placeholder="Brief description of what this agent does" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="purpose">Business Purpose *</Label>
                            <Textarea id="purpose" value={agentData.agent_purpose} onChange={(e) => setAgentData({...agentData, agent_purpose: e.target.value})} placeholder="Explain the specific business problem this agent solves..." className="h-24" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="template">Custom Prompt Template *</Label>
                            <Textarea id="template" value={agentData.prompt_template} onChange={(e) => setAgentData({...agentData, prompt_template: e.target.value})} placeholder="You are a specialized [AGENT_NAME] agent. Your role is to [AGENT_PURPOSE]. Use your training data to answer user queries..." className="h-32" />
                        </div>
                    </CardContent>
                </Card>

                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>2. Agent Training</CardTitle>
                        <CardDescription>Provide knowledge sources. You can add multiple sources of different types.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Tabs defaultValue="file">
                            <TabsList className="grid w-full grid-cols-3">
                                <TabsTrigger value="file"><FileText className="w-4 h-4 mr-2" />Files</TabsTrigger>
                                <TabsTrigger value="url"><LinkIcon className="w-4 h-4 mr-2" />Website</TabsTrigger>
                                <TabsTrigger value="text"><Pilcrow className="w-4 h-4 mr-2" />Text</TabsTrigger>
                            </TabsList>
                            <TabsContent value="file" className="pt-4">
                                <Label htmlFor="training-upload" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <Upload className="w-8 h-8 mb-2 text-gray-500" />
                                    <p className="text-sm text-center text-gray-500">Click to upload files</p>
                                    <Input id="training-upload" type="file" multiple className="hidden" onChange={handleAddFile} />
                                </Label>
                            </TabsContent>
                            <TabsContent value="url" className="pt-4 space-y-2">
                                <Input value={urlInput} onChange={e => setUrlInput(e.target.value)} placeholder="https://example.com/knowledge-base" />
                                <Button onClick={handleAddUrl} className="w-full">Add Website Source</Button>
                            </TabsContent>
                            <TabsContent value="text" className="pt-4 space-y-2">
                                <Textarea value={textInput} onChange={e => setTextInput(e.target.value)} placeholder="Paste raw text here..." className="h-40" />
                                <Button onClick={handleAddText} className="w-full">Add Text Source</Button>
                            </TabsContent>
                        </Tabs>
                        
                        {trainingSources.length > 0 && (
                            <div className="mt-6">
                                <h4 className="font-medium mb-2">Added Sources:</h4>
                                <div className="space-y-2">
                                    {trainingSources.map((s, i) => (
                                        <div key={i} className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-800 rounded-md text-sm">
                                            <span className="truncate">{s.name}</span>
                                            <Badge variant="secondary" className="capitalize">{s.type}</Badge>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <div className="md:col-span-2">
                     <Button onClick={handleCreateAgent} disabled={isCreating} className="w-full text-lg py-6 bg-blue-600 hover:bg-blue-700 dark:text-white">
                        {isCreating ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <Bot className="w-5 h-5 mr-2" />}
                        Deploy Agent
                    </Button>
                </div>
            </div>
        </div>
    );
}
