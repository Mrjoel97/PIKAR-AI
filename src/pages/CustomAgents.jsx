
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CustomAgent } from '@/api/entities';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, Brain, Settings, Play, Pause, Trash2, BarChart } from 'lucide-react';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { Toaster, toast } from 'sonner';
import AdvancedTrainingPanel from '@/components/training/AdvancedTrainingPanel';

export default function CustomAgents() {
    const [customAgents, setCustomAgents] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showTrainingPanel, setShowTrainingPanel] = useState(null);

    useEffect(() => {
        loadCustomAgents();
    }, []);

    const loadCustomAgents = async () => {
        setIsLoading(true);
        try {
            const agents = await CustomAgent.list('-created_date');
            setCustomAgents(agents);
        } catch (error) {
            console.error("Error loading custom agents:", error);
            toast.error("Failed to load custom agents.");
        } finally {
            setIsLoading(false);
        }
    };

    const toggleAgentStatus = async (agent) => {
        const newStatus = agent.agent_status === 'active' ? 'inactive' : 'active';
        try {
            await CustomAgent.update(agent.id, { agent_status: newStatus });
            loadCustomAgents();
            toast.success(`Agent ${newStatus === 'active' ? 'activated' : 'deactivated'} successfully!`);
        } catch (error) {
            console.error("Error updating agent status:", error);
            toast.error("Failed to update agent status.");
        }
    };

    const deleteAgent = async (agentId) => {
        if (!window.confirm("Are you sure you want to permanently delete this agent?")) {
            return;
        }
        try {
            await CustomAgent.delete(agentId);
            loadCustomAgents();
            toast.success("Agent deleted successfully.");
        } catch (error) {
            console.error("Error deleting agent:", error);
            toast.error("Failed to delete agent.");
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'active': return 'bg-green-100 text-green-800 border-green-200';
            case 'training': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'inactive': return 'bg-gray-100 text-gray-800 border-gray-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const renderAgentCard = (agent, isAllTab = false) => (
        <Card key={agent.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
                <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg bg-${agent.agent_color || 'blue'}-50`}>
                            <Brain className={`w-6 h-6 text-${agent.agent_color || 'blue'}-600`} />
                        </div>
                        <div>
                            <CardTitle className="text-lg">{agent.agent_name}</CardTitle>
                            <Badge className={getStatusColor(agent.agent_status)}>
                                {agent.agent_status}
                            </Badge>
                        </div>
                    </div>
                    {isAllTab && (
                        <div className="flex gap-1">
                            <Button size="icon" variant="ghost" onClick={() => setShowTrainingPanel(showTrainingPanel === agent.id ? null : agent.id)} title="View Training">
                                <BarChart className="w-4 h-4" />
                            </Button>
                             <Button size="icon" variant="ghost" onClick={() => toggleAgentStatus(agent)} title={agent.agent_status === 'active' ? 'Deactivate' : 'Activate'}>
                                {agent.agent_status === 'active' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                            </Button>
                            <Link to={createPageUrl(`EditAgent?id=${agent.id}`)}>
                                <Button size="icon" variant="ghost" title="Settings">
                                    <Settings className="w-4 h-4" />
                                </Button>
                            </Link>
                            <Button size="icon" variant="ghost" onClick={() => deleteAgent(agent.id)} title="Delete">
                                <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                        </div>
                    )}
                </div>
                <CardDescription className="mt-2">{agent.agent_description}</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Used {agent.usage_count || 0} times</span>
                    {agent.agent_status === 'active' && (
                        <Link to={createPageUrl(`CustomAgentChat?id=${agent.id}`)}>
                            <Button size="sm">Use Agent</Button>
                        </Link>
                    )}
                </div>
                
                {/* Training Panel */}
                {showTrainingPanel === agent.id && (
                    <div className="mt-4 p-4 border-t">
                        <AdvancedTrainingPanel 
                            agentId={agent.id} 
                            agentName={agent.agent_name}
                        />
                    </div>
                )}
            </CardContent>
        </Card>
    );
    
    const renderEmptyState = (title, description) => (
         <div className="text-center py-12 col-span-full">
            <Brain className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium">{title}</h3>
            <p className="text-gray-500">{description}</p>
            <Link to={createPageUrl("CreateAgent")} className="mt-4 inline-block">
                <Button>Create Agent</Button>
            </Link>
        </div>
    );

    return (
        <div className="max-w-7xl mx-auto">
            <Toaster richColors />
            <header className="mb-8">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl md:text-4xl font-bold">Custom Agents</h1>
                        <p className="text-lg text-gray-600 mt-2">Deploy and manage your specialized AI agents.</p>
                    </div>
                    <Link to={createPageUrl("CreateAgent")}>
                        <Button className="bg-blue-600 hover:bg-blue-700">
                            <Plus className="w-4 h-4 mr-2" />
                            Create Agent
                        </Button>
                    </Link>
                </div>
            </header>

            <Tabs defaultValue="all" className="w-full">
                <TabsList>
                    <TabsTrigger value="all">All Agents</TabsTrigger>
                    <TabsTrigger value="active">Active</TabsTrigger>
                    <TabsTrigger value="inactive">Inactive</TabsTrigger>
                    <TabsTrigger value="training">Training</TabsTrigger>
                </TabsList>
                
                <TabsContent value="all" className="mt-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {isLoading && <p>Loading...</p>}
                        {!isLoading && customAgents.length > 0 ? customAgents.map(agent => renderAgentCard(agent, true)) :
                         !isLoading && renderEmptyState("No custom agents yet", "Create your first agent to get started.")}
                    </div>
                </TabsContent>

                <TabsContent value="active" className="mt-6">
                     <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {isLoading && <p>Loading...</p>}
                        {!isLoading && customAgents.filter(a => a.agent_status === 'active').length > 0 ? 
                         customAgents.filter(a => a.agent_status === 'active').map(agent => renderAgentCard(agent)) : 
                         !isLoading && renderEmptyState("No active agents", "Activate an agent or create a new one.")}
                    </div>
                </TabsContent>

                 <TabsContent value="inactive" className="mt-6">
                     <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {isLoading && <p>Loading...</p>}
                        {!isLoading && customAgents.filter(a => a.agent_status === 'inactive').length > 0 ? 
                         customAgents.filter(a => a.agent_status === 'inactive').map(agent => renderAgentCard(agent)) : 
                         !isLoading && renderEmptyState("No inactive agents", "All your agents are active or in training.")}
                    </div>
                </TabsContent>

                <TabsContent value="training" className="mt-6">
                     <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {isLoading && <p>Loading...</p>}
                        {!isLoading && customAgents.filter(a => a.agent_status === 'training').length > 0 ? 
                         customAgents.filter(a => a.agent_status === 'training').map(agent => renderAgentCard(agent)) : 
                         !isLoading && renderEmptyState("No agents in training", "Agents you create will appear here while they are being trained.")}
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
