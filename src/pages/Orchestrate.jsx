
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Workflow, WorkflowStep, WorkflowTemplate } from '@/api/entities';
import { AuditLog } from '@/api/entities'; // Added import for AuditLog
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import WorkflowExecutor from "@/components/workflow/WorkflowExecutor";
import { 
    Network, Plus, Play, Pause, RotateCcw, Loader2, CheckCircle, Clock, 
    AlertTriangle, ArrowRight, Settings, FileUp, Sparkles, Users, Bot, 
    Star, TrendingUp, Zap, Eye, Copy, Download, Filter, Search
} from 'lucide-react';
import { Toaster, toast } from 'sonner';

const agentOptions = [
    { value: 'Strategic Planning', label: 'Strategic Planning', color: 'purple' },
    { value: 'Content Creation', label: 'Content Creation', color: 'blue' },
    { value: 'Customer Support', label: 'Customer Support', color: 'green' },
    { value: 'Sales Intelligence', label: 'Sales Intelligence', color: 'orange' },
    { value: 'Data Analysis', label: 'Data Analysis', color: 'indigo' },
    { value: 'Marketing Automation', label: 'Marketing Automation', color: 'pink' },
    { value: 'Financial Analysis', label: 'Financial Analysis', color: 'emerald' },
    { value: 'HR & Recruitment', label: 'HR & Recruitment', color: 'cyan' },
    { value: 'Compliance & Risk', label: 'Compliance & Risk', color: 'red' },
    { value: 'Operations Optimization', label: 'Operations Optimization', color: 'yellow' }
];

export default function Orchestrate() {
    const [workflows, setWorkflows] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [selectedTab, setSelectedTab] = useState('gallery');
    const [searchQuery, setSearchQuery] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('all');
    const [newWorkflow, setNewWorkflow] = useState({
        workflow_name: '',
        workflow_description: '',
        workflow_category: '',
        context_file: null
    });
    const [workflowSteps, setWorkflowSteps] = useState([]);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [workflowsData, templatesData] = await Promise.all([
                Workflow.list('-created_date'),
                WorkflowTemplate.list('-usage_count')
            ]);
            setWorkflows(workflowsData);
            setTemplates(templatesData);
        } catch (error) {
            console.error("Failed to load orchestration data:", error);
            toast.error("Failed to load data");
        } finally {
            setIsLoading(false);
        }
    };

    const deployTemplate = async (template) => {
        try {
            await AuditLog.create({
                action_type: "workflow_creation",
                success: true,
                action_details: { event: "template_deploy_start", template_id: template.id, template_name: template.template_name },
                risk_level: "low"
            });

            // Create workflow from template
            const workflow = await Workflow.create({
                workflow_name: `${template.template_name} - Copy`,
                workflow_description: template.template_description,
                workflow_category: template.category,
                total_steps: template.template_config.steps.length,
                estimated_duration: template.estimated_duration,
                workflow_status: 'active'
            });

            // Create workflow steps from template
            for (const step of template.template_config.steps) {
                await WorkflowStep.create({
                    workflow_id: workflow.id,
                    step_order: step.step_order,
                    agent_name: step.agent_name,
                    step_prompt: step.step_prompt,
                    step_input: step.step_input_schema || {},
                    step_status: 'pending'
                });
            }

            // Update template usage count
            await WorkflowTemplate.update(template.id, {
                usage_count: (template.usage_count || 0) + 1
            });

            await AuditLog.create({
                action_type: "workflow_creation",
                success: true,
                workflow_id: String(workflow.id),
                action_details: { event: "template_deploy_finish", template_id: template.id, steps: template.template_config.steps.length },
                risk_level: "low"
            });

            toast.success(`Template "${template.template_name}" deployed successfully!`);
            loadData();
        } catch (error) {
            console.error("Error deploying template:", error);
            await AuditLog.create({
                action_type: "workflow_creation",
                success: false,
                action_details: { event: "template_deploy_error", error: String(error) },
                risk_level: "medium"
            });
            toast.error("Failed to deploy template");
        }
    };

    async function handleExecuteWorkflow(workflowId) {
      await WorkflowExecutor.run(workflowId, { mode: "remaining", maxRetries: 2 });
    }

    const getStatusColor = (status) => {
        switch (status) {
            case 'active': return 'bg-green-100 text-green-800';
            case 'completed': return 'bg-blue-100 text-blue-800';
            case 'failed': return 'bg-red-100 text-red-800';
            case 'draft': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'active': return <Play className="w-4 h-4" />;
            case 'completed': return <CheckCircle className="w-4 h-4" />;
            case 'failed': return <AlertTriangle className="w-4 h-4" />;
            case 'draft': return <Clock className="w-4 h-4" />;
            default: return <Clock className="w-4 h-4" />;
        }
    };

    const getCategoryColor = (category) => {
        switch (category) {
            case 'data_management': return 'bg-blue-100 text-blue-800';
            case 'notifications': return 'bg-yellow-100 text-yellow-800';
            case 'analysis': return 'bg-purple-100 text-purple-800';
            case 'automation': return 'bg-green-100 text-green-800';
            case 'compliance': return 'bg-red-100 text-red-800';
            case 'reporting': return 'bg-indigo-100 text-indigo-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getDifficultyColor = (difficulty) => {
        switch (difficulty) {
            case 'beginner': return 'bg-green-100 text-green-800';
            case 'intermediate': return 'bg-yellow-100 text-yellow-800';
            case 'advanced': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const filteredTemplates = templates.filter(template => {
        const matchesSearch = !searchQuery || 
            template.template_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            template.template_description.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesCategory = categoryFilter === 'all' || template.category === categoryFilter;
        return matchesSearch && matchesCategory;
    });

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <Toaster richColors />
            
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                        <Network className="w-8 h-8 text-blue-600" />
                        Agent Orchestration
                    </h1>
                    <p className="text-lg text-gray-600 dark:text-gray-400 mt-1">
                        Coordinate multiple AI agents with pre-built templates and custom workflows
                    </p>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" onClick={() => setSelectedTab('create')}>
                        <Plus className="w-4 h-4 mr-2" />
                        Create Custom
                    </Button>
                </div>
            </header>

            <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="gallery">Template Gallery</TabsTrigger>
                    <TabsTrigger value="workflows">My Workflows</TabsTrigger>
                    <TabsTrigger value="create">Create Custom</TabsTrigger>
                </TabsList>

                <TabsContent value="gallery" className="space-y-6">
                    {/* Search and Filter */}
                    <Card>
                        <CardContent className="p-4">
                            <div className="flex flex-wrap gap-4">
                                <div className="relative flex-1 min-w-64">
                                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                                    <Input
                                        placeholder="Search templates..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-10"
                                    />
                                </div>
                                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                                    <SelectTrigger className="w-48">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">All Categories</SelectItem>
                                        <SelectItem value="data_management">Data Management</SelectItem>
                                        <SelectItem value="notifications">Notifications</SelectItem>
                                        <SelectItem value="analysis">Analysis</SelectItem>
                                        <SelectItem value="automation">Automation</SelectItem>
                                        <SelectItem value="compliance">Compliance</SelectItem>
                                        <SelectItem value="reporting">Reporting</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Featured Templates */}
                    <div>
                        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                            <Star className="w-6 h-6 text-yellow-500" />
                            Featured Templates
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {filteredTemplates.filter(t => t.is_featured).map(template => (
                                <Card key={template.id} className="hover:shadow-lg transition-all duration-200 border-2 border-yellow-200">
                                    <CardHeader>
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <Star className="w-4 h-4 text-yellow-500 fill-current" />
                                                    <Badge className={getCategoryColor(template.category)}>
                                                        {template.category.replace(/_/g, ' ')}
                                                    </Badge>
                                                    <Badge className={getDifficultyColor(template.difficulty)}>
                                                        {template.difficulty}
                                                    </Badge>
                                                </div>
                                                <CardTitle className="text-lg">{template.template_name}</CardTitle>
                                                <CardDescription className="mt-1">
                                                    {template.template_description}
                                                </CardDescription>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            {/* Template Stats */}
                                            <div className="grid grid-cols-3 gap-4 text-center">
                                                <div>
                                                    <div className="text-lg font-bold text-blue-600">{template.usage_count || 0}</div>
                                                    <div className="text-xs text-gray-500">Uses</div>
                                                </div>
                                                <div>
                                                    <div className="text-lg font-bold text-green-600">{template.success_rate || 100}%</div>
                                                    <div className="text-xs text-gray-500">Success</div>
                                                </div>
                                                <div>
                                                    <div className="text-lg font-bold text-purple-600">
                                                        {template.template_config?.steps?.length || 0}
                                                    </div>
                                                    <div className="text-xs text-gray-500">Steps</div>
                                                </div>
                                            </div>

                                            {/* Template Tags */}
                                            {template.tags && (
                                                <div className="flex flex-wrap gap-1">
                                                    {template.tags.slice(0, 3).map((tag, idx) => (
                                                        <Badge key={idx} variant="outline" className="text-xs">
                                                            {tag}
                                                        </Badge>
                                                    ))}
                                                    {template.tags.length > 3 && (
                                                        <Badge variant="outline" className="text-xs">
                                                            +{template.tags.length - 3}
                                                        </Badge>
                                                    )}
                                                </div>
                                            )}

                                            {/* Actions */}
                                            <div className="flex gap-2">
                                                <Button 
                                                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                                                    onClick={() => deployTemplate(template)}
                                                >
                                                    <Play className="w-4 h-4 mr-2" />
                                                    Deploy
                                                </Button>
                                                <Button variant="outline" size="sm">
                                                    <Eye className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </CardContent>
                                    </Card>
                            ))}
                        </div>
                    </div>

                    {/* All Templates */}
                    {filteredTemplates.filter(t => !t.is_featured).length > 0 && (
                        <div>
                            <h2 className="text-2xl font-bold mb-4">All Templates</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {filteredTemplates.filter(t => !t.is_featured).map(template => (
                                    <Card key={template.id} className="hover:shadow-md transition-shadow">
                                        <CardHeader>
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <Badge className={getCategoryColor(template.category)}>
                                                            {template.category.replace(/_/g, ' ')}
                                                        </Badge>
                                                        <Badge className={getDifficultyColor(template.difficulty)}>
                                                            {template.difficulty}
                                                        </Badge>
                                                    </div>
                                                    <CardTitle className="text-lg">{template.template_name}</CardTitle>
                                                    <CardDescription className="mt-1">
                                                        {template.template_description}
                                                    </CardDescription>
                                                </div>
                                            </div>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-4">
                                                {/* Template Stats */}
                                                <div className="flex justify-between text-sm">
                                                    <span className="text-gray-600">Duration:</span>
                                                    <span className="font-medium">{template.estimated_duration}</span>
                                                </div>
                                                
                                                <div className="flex justify-between text-sm">
                                                    <span className="text-gray-600">Success Rate:</span>
                                                    <span className="font-medium text-green-600">
                                                        {template.success_rate || 100}%
                                                    </span>
                                                </div>

                                                {/* Actions */}
                                                <div className="flex gap-2">
                                                    <Button 
                                                        className="flex-1"
                                                        onClick={() => deployTemplate(template)}
                                                    >
                                                        <Play className="w-4 h-4 mr-2" />
                                                        Deploy
                                                    </Button>
                                                    <Button variant="outline" size="sm">
                                                        <Eye className="w-4 h-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="workflows" className="space-y-6">
                    {/* Active Workflows */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Network className="w-5 h-5 text-blue-500" />
                                Active Workflows
                            </CardTitle>
                            <CardDescription>
                                Monitor and manage your deployed multi-agent workflows
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <div className="flex justify-center items-center h-32">
                                    <Loader2 className="w-8 h-8 animate-spin" />
                                </div>
                            ) : workflows.length > 0 ? (
                                <div className="space-y-4">
                                    {workflows.map(workflow => (
                                        <div key={workflow.id} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-3 mb-2">
                                                        <h3 className="font-semibold text-lg">{workflow.workflow_name}</h3>
                                                        <Badge className={getStatusColor(workflow.workflow_status)}>
                                                            {getStatusIcon(workflow.workflow_status)}
                                                            <span className="ml-1">{workflow.workflow_status}</span>
                                                        </Badge>
                                                        <Badge className={getCategoryColor(workflow.workflow_category)}>
                                                            {workflow.workflow_category?.replace(/_/g, ' ')}
                                                        </Badge>
                                                    </div>
                                                    <p className="text-gray-600 dark:text-gray-400 mb-3">
                                                        {workflow.workflow_description}
                                                    </p>
                                                    <div className="flex items-center gap-4 text-sm text-gray-500">
                                                        <span className="flex items-center gap-1">
                                                            <Bot className="w-4 h-4" />
                                                            {workflow.total_steps} agents
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Clock className="w-4 h-4" />
                                                            {workflow.estimated_duration}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="flex gap-2">
                                                    <Link to={createPageUrl(`WorkflowDetails?id=${workflow.id}`)}>
                                                        <Button variant="outline" size="sm">
                                                            <Settings className="w-4 h-4 mr-2" />
                                                            Details
                                                        </Button>
                                                    </Link>
                                                    <Button 
                                                        size="sm" 
                                                        className="bg-blue-600 hover:bg-blue-700"
                                                        onClick={() => handleExecuteWorkflow(workflow.id)}
                                                    >
                                                        <Play className="w-4 h-4 mr-2" />
                                                        Execute
                                                    </Button>
                                                </div>
                                            </div>
                                            {workflow.workflow_status === 'active' && (
                                                <div className="mt-4">
                                                    <div className="flex justify-between items-center mb-1">
                                                        <span className="text-sm font-medium">Progress</span>
                                                        <span className="text-sm text-gray-500">Step 1 of {workflow.total_steps}</span>
                                                    </div>
                                                    <Progress value={20} className="h-2" />
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-12">
                                    <Network className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                                    <p className="text-gray-500 mb-2">No workflows deployed yet</p>
                                    <p className="text-sm text-gray-400 mb-4">
                                        Deploy a template or create a custom workflow to get started
                                    </p>
                                    <Button onClick={() => setSelectedTab('gallery')}>
                                        <Sparkles className="w-4 h-4 mr-2" />
                                        Browse Templates
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="create" className="space-y-6">
                    <Link to={createPageUrl("CreateWorkflow")}>
                        <Card className="hover:shadow-md transition-shadow cursor-pointer">
                            <CardContent className="flex items-center justify-center p-8">
                                <div className="text-center">
                                    <Plus className="w-12 h-12 mx-auto text-blue-600 mb-4" />
                                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                        Create Custom Workflow
                                    </h3>
                                    <p className="text-gray-600">
                                        Build a custom multi-agent workflow from scratch
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                </TabsContent>
            </Tabs>
        </div>
    );
}
