import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CustomAgent } from '@/api/entities';
import { Save, Loader2, Settings, Brain } from 'lucide-react';
import { Toaster, toast } from 'sonner';
import { createPageUrl } from '@/utils';
import AdvancedTrainingPanel from '@/components/training/AdvancedTrainingPanel';

export default function EditAgent() {
    const [agentId, setAgentId] = useState('');
    const [agent, setAgent] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [formData, setFormData] = useState({
        agent_name: '',
        agent_description: '',
        agent_purpose: '',
        prompt_template: '',
        agent_status: 'active',
        agent_icon: 'Bot',
        agent_color: 'blue'
    });

    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const id = urlParams.get('id');
        setAgentId(id);
    }, []);

    const loadAgent = useCallback(async () => {
        if (!agentId) return;
        setIsLoading(true);
        try {
            const agents = await CustomAgent.filter({ id: agentId });
            if (agents && agents.length > 0) {
                const agentData = agents[0];
                setAgent(agentData);
                setFormData({
                    agent_name: agentData.agent_name || '',
                    agent_description: agentData.agent_description || '',
                    agent_purpose: agentData.agent_purpose || '',
                    prompt_template: agentData.prompt_template || '',
                    agent_status: agentData.agent_status || 'active',
                    agent_icon: agentData.agent_icon || 'Bot',
                    agent_color: agentData.agent_color || 'blue'
                });
            } else {
                toast.error("Agent not found");
                window.location.href = createPageUrl("CustomAgents");
            }
        } catch (error) {
            console.error("Error loading agent:", error);
            toast.error("Failed to load agent");
        } finally {
            setIsLoading(false);
        }
    }, [agentId]);

    useEffect(() => {
        loadAgent();
    }, [loadAgent]);

    const handleSave = async () => {
        if (!formData.agent_name || !formData.agent_description || !formData.prompt_template) {
            toast.error("Please fill in all required fields.");
            return;
        }

        setIsSaving(true);
        try {
            await CustomAgent.update(agentId, formData);
            toast.success("Agent updated successfully!");
        } catch (error) {
            console.error("Error updating agent:", error);
            toast.error("Failed to update agent.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleTrainingComplete = () => {
        loadAgent(); // Reload agent data after training
        toast.success("Agent capabilities updated through training!");
    };

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-96">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
                    <p>Loading agent...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <Toaster richColors />
            <div className="flex items-center gap-3">
                <Settings className="w-8 h-8 text-blue-600" />
                <div>
                    <h1 className="text-3xl font-bold">Edit Agent</h1>
                    <p className="text-gray-600">Configure and train your custom AI agent</p>
                </div>
            </div>

            <Tabs defaultValue="configuration" className="w-full">
                <TabsList>
                    <TabsTrigger value="configuration">Configuration</TabsTrigger>
                    <TabsTrigger value="training">Advanced Training</TabsTrigger>
                </TabsList>

                <TabsContent value="configuration">
                    <Card>
                        <CardHeader>
                            <CardTitle>Agent Configuration</CardTitle>
                            <CardDescription>Basic agent settings and prompt template</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="name">Agent Name</Label>
                                    <Input
                                        id="name"
                                        value={formData.agent_name}
                                        onChange={(e) => setFormData({...formData, agent_name: e.target.value})}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="status">Status</Label>
                                    <Select 
                                        value={formData.agent_status} 
                                        onValueChange={(value) => setFormData({...formData, agent_status: value})}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="active">Active</SelectItem>
                                            <SelectItem value="inactive">Inactive</SelectItem>
                                            <SelectItem value="training">Training</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            
                            <div className="space-y-2">
                                <Label htmlFor="description">Description</Label>
                                <Textarea
                                    id="description"
                                    value={formData.agent_description}
                                    onChange={(e) => setFormData({...formData, agent_description: e.target.value})}
                                    className="h-24"
                                />
                            </div>
                            
                            <div className="space-y-2">
                                <Label htmlFor="purpose">Business Purpose</Label>
                                <Textarea
                                    id="purpose"
                                    value={formData.agent_purpose}
                                    onChange={(e) => setFormData({...formData, agent_purpose: e.target.value})}
                                    className="h-24"
                                />
                            </div>
                            
                            <div className="space-y-2">
                                <Label htmlFor="template">Prompt Template</Label>
                                <Textarea
                                    id="template"
                                    value={formData.prompt_template}
                                    onChange={(e) => setFormData({...formData, prompt_template: e.target.value})}
                                    className="h-32"
                                    placeholder="You are a specialized AI agent that..."
                                />
                            </div>

                            <Button onClick={handleSave} disabled={isSaving} className="w-full">
                                {isSaving ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Save className="w-4 h-4 mr-2" />
                                )}
                                Save Changes
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="training">
                    <AdvancedTrainingPanel 
                        agentId={agentId} 
                        onTrainingComplete={handleTrainingComplete}
                    />
                </TabsContent>
            </Tabs>
        </div>
    );
}