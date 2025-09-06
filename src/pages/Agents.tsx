import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useAction } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Bot,
  Plus,
  Star,
  Play,
  Settings,
  History,
  Share,
  Download,
  Eye,
  Trash2,
  RotateCcw,
  TrendingUp,
  Users,
  Tag,
  Filter,
  Search,
  Sparkles,
  Zap,
  Target,
  BarChart3,
} from "lucide-react";

interface AgentBuilderNode {
  id: string;
  type: "input" | "hook" | "output";
  title: string;
  config: any;
}

const AgentsPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("my-agents");
  const [selectedTier, setSelectedTier] = useState<string>("solopreneur");
  
  // Seed data on mount
  const seedAction = useAction(api.aiAgents.seedAgentFramework);
  
  useEffect(() => {
    const initSeed = async () => {
      try {
        await seedAction({});
      } catch (error) {
        // Ignore if already seeded
      }
    };
    initSeed();
  }, [seedAction]);

  // Get tier from localStorage or URL params (reuse dashboard logic)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tierFromUrl = urlParams.get("tier");
    const tierFromStorage = localStorage.getItem("tierOverride");
    
    if (tierFromUrl) {
      setSelectedTier(tierFromUrl);
    } else if (tierFromStorage) {
      setSelectedTier(tierFromStorage);
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 p-4 md:p-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-7xl mx-auto space-y-8"
      >
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-4xl font-black text-gray-900 mb-2">
              Custom Agent Framework
            </h1>
            <p className="text-gray-600">
              Build, deploy, and manage intelligent automation agents
            </p>
          </div>
          
          {/* Tier Switcher */}
          <div className="flex items-center gap-2">
            <Label>Tier:</Label>
            <Select value={selectedTier} onValueChange={setSelectedTier}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="solopreneur">Solopreneur</SelectItem>
                <SelectItem value="startup">Startup</SelectItem>
                <SelectItem value="sme">SME</SelectItem>
                <SelectItem value="enterprise">Enterprise</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="my-agents" className="flex items-center gap-2">
              <Bot className="w-4 h-4" />
              My Agents
            </TabsTrigger>
            <TabsTrigger value="templates" className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Templates
            </TabsTrigger>
            <TabsTrigger value="marketplace" className="flex items-center gap-2">
              <Share className="w-4 h-4" />
              Marketplace
            </TabsTrigger>
            <TabsTrigger value="builder" className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Builder
            </TabsTrigger>
            <TabsTrigger value="monitoring" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Monitoring
            </TabsTrigger>
          </TabsList>

          {/* My Agents Tab */}
          <TabsContent value="my-agents">
            <MyAgentsTab userId={user?._id} selectedTier={selectedTier} />
          </TabsContent>

          {/* Templates Tab */}
          <TabsContent value="templates">
            <TemplatesTab userId={user?._id} selectedTier={selectedTier} />
          </TabsContent>

          {/* Marketplace Tab */}
          <TabsContent value="marketplace">
            <MarketplaceTab userId={user?._id} />
          </TabsContent>

          {/* Builder Tab */}
          <TabsContent value="builder">
            <BuilderTab userId={user?._id} selectedTier={selectedTier} />
          </TabsContent>

          {/* Monitoring Tab */}
          <TabsContent value="monitoring">
            <MonitoringTab userId={user?._id} />
          </TabsContent>
        </Tabs>
      </motion.div>
    </div>
  );
};

// My Agents Tab Component
const MyAgentsTab: React.FC<{ userId?: Id<"users">; selectedTier: string }> = ({ 
  userId, 
  selectedTier 
}) => {
  const [selectedAgent, setSelectedAgent] = useState<any>(null);
  const [showVersions, setShowVersions] = useState(false);
  
  const agents = useQuery(api.aiAgents.listCustomAgents, 
    userId ? { userId } : {}
  );
  
  const createAgent = useMutation(api.aiAgents.createCustomAgent);

  const handleCreateAgent = async () => {
    if (!userId) return;
    
    try {
      await createAgent({
        name: "New Agent",
        description: "A custom agent",
        tags: [],
        config: { inputs: [], hooks: [], outputs: [] },
        businessId: "sample-business" as Id<"businesses">, // Mock business ID
        userId,
      });
      toast.success("Agent created successfully");
    } catch (error) {
      toast.error("Failed to create agent");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">My Custom Agents</h2>
        <Button onClick={handleCreateAgent} className="flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Create Agent
        </Button>
      </div>

      <div className="grid gap-4">
        {agents?.map((agent) => (
          <Card key={agent._id} className="border-2 border-gray-200 hover:border-purple-300 transition-colors">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Bot className="w-5 h-5" />
                    {agent.name}
                  </CardTitle>
                  <CardDescription>{agent.description}</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Badge variant={agent.visibility === "private" ? "secondary" : "default"}>
                    {agent.visibility}
                  </Badge>
                  <Badge variant={agent.riskLevel === "high" ? "destructive" : "outline"}>
                    {agent.riskLevel} risk
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-4">
                {agent.tags.map((tag: string) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
              
              <div className="flex justify-between items-center text-sm text-gray-600 mb-4">
                <span>Version: {agent.currentVersion?.version || "1.0.0"}</span>
                <span>
                  Runs: {agent.stats.runs} | Success: {
                    agent.stats.runs > 0 
                      ? Math.round((agent.stats.successes / agent.stats.runs) * 100)
                      : 0
                  }%
                </span>
              </div>
              
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Settings className="w-4 h-4 mr-1" />
                  Edit
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => {
                    setSelectedAgent(agent);
                    setShowVersions(true);
                  }}
                >
                  <History className="w-4 h-4 mr-1" />
                  Versions
                </Button>
                <Button variant="outline" size="sm">
                  <Share className="w-4 h-4 mr-1" />
                  Submit to Marketplace
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Versions Sheet */}
      <Sheet open={showVersions} onOpenChange={setShowVersions}>
        <SheetContent className="w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle>Agent Versions</SheetTitle>
            <SheetDescription>
              Manage versions for {selectedAgent?.name}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            <VersionsList agentId={selectedAgent?._id} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
};

// Templates Tab Component
const TemplatesTab: React.FC<{ userId?: Id<"users">; selectedTier: string }> = ({ 
  userId, 
  selectedTier 
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newAgentName, setNewAgentName] = useState("");
  const [newAgentTags, setNewAgentTags] = useState("");
  
  const templates = useQuery(api.aiAgents.listTemplates, { tier: selectedTier });
  const createFromTemplate = useMutation(api.aiAgents.createFromTemplate);

  const handleUseTemplate = async () => {
    if (!userId || !selectedTemplate) return;
    
    try {
      await createFromTemplate({
        templateId: selectedTemplate._id,
        name: newAgentName || selectedTemplate.name,
        tags: newAgentTags ? newAgentTags.split(",").map((t: string) => t.trim()) : selectedTemplate.tags,
        businessId: "sample-business" as Id<"businesses">,
        userId,
      });
      toast.success("Agent created from template");
      setShowCreateForm(false);
      setSelectedTemplate(null);
      setNewAgentName("");
      setNewAgentTags("");
    } catch (error) {
      toast.error("Failed to create agent from template");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Agent Templates</h2>
        <Badge variant="outline">{selectedTier} tier</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates?.map((template: any) => (
          <Card key={template._id} className="border-2 border-gray-200 hover:border-blue-300 transition-colors">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="w-5 h-5" />
                {template.name}
              </CardTitle>
              <CardDescription>{template.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-4">
                {template.tags.map((tag: string) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
              
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setSelectedTemplate(template)}
                >
                  <Eye className="w-4 h-4 mr-1" />
                  Preview
                </Button>
                <Button 
                  size="sm"
                  onClick={() => {
                    setSelectedTemplate(template);
                    setShowCreateForm(true);
                  }}
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Use Template
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Template Preview Dialog */}
      <Dialog open={!!selectedTemplate && !showCreateForm} onOpenChange={() => setSelectedTemplate(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedTemplate?.name}</DialogTitle>
            <DialogDescription>{selectedTemplate?.description}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Configuration Preview:</Label>
              <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto">
                {JSON.stringify(selectedTemplate?.configPreview, null, 2)}
              </pre>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create from Template Dialog */}
      <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Agent from Template</DialogTitle>
            <DialogDescription>
              Customize your agent based on {selectedTemplate?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="agent-name">Agent Name</Label>
              <Input
                id="agent-name"
                value={newAgentName}
                onChange={(e) => setNewAgentName(e.target.value)}
                placeholder={selectedTemplate?.name}
              />
            </div>
            <div>
              <Label htmlFor="agent-tags">Tags (comma-separated)</Label>
              <Input
                id="agent-tags"
                value={newAgentTags}
                onChange={(e) => setNewAgentTags(e.target.value)}
                placeholder={selectedTemplate?.tags.join(", ")}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateForm(false)}>
              Cancel
            </Button>
            <Button onClick={handleUseTemplate}>
              Create Agent
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Marketplace Tab Component
const MarketplaceTab: React.FC<{ userId?: Id<"users"> }> = ({ userId }) => {
  const [filterStatus, setFilterStatus] = useState("approved");
  const [searchTags, setSearchTags] = useState("");
  
  const marketplaceAgents = useQuery(api.aiAgents.listMarketplaceAgents, { 
    status: filterStatus 
  });
  const addToWorkspace = useMutation(api.aiAgents.addToWorkspace);

  const handleAddToWorkspace = async (agentId: Id<"custom_agents">) => {
    if (!userId) return;
    
    try {
      await addToWorkspace({
        marketplaceAgentId: agentId,
        businessId: "sample-business" as Id<"businesses">,
        userId,
      });
      toast.success("Agent added to your workspace");
    } catch (error) {
      toast.error("Failed to add agent to workspace");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h2 className="text-2xl font-bold">Agent Marketplace</h2>
        
        <div className="flex gap-2">
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
          
          <Input
            placeholder="Search tags..."
            value={searchTags}
            onChange={(e) => setSearchTags(e.target.value)}
            className="w-40"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {marketplaceAgents?.map((item: any) => (
          <Card key={item._id} className="border-2 border-gray-200 hover:border-green-300 transition-colors">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                {item.agent?.name}
              </CardTitle>
              <CardDescription>{item.agent?.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-4">
                {item.industryTags.map((tag: string) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
                {item.usageTags.map((tag: string) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
              
              <div className="flex justify-between items-center text-sm text-gray-600 mb-4">
                <div className="flex items-center gap-1">
                  <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  <span>{item.avgRating.toFixed(1)} ({item.ratingsCount})</span>
                </div>
                <span>
                  {item.stats.runs} runs | {
                    item.stats.runs > 0 
                      ? Math.round((item.stats.successes / item.stats.runs) * 100)
                      : 0
                  }% success
                </span>
              </div>
              
              <Button 
                className="w-full"
                onClick={() => handleAddToWorkspace(item.agentId)}
              >
                <Download className="w-4 h-4 mr-1" />
                Add to Workspace
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// Builder Tab Component
const BuilderTab: React.FC<{ userId?: Id<"users">; selectedTier: string }> = ({ 
  userId, 
  selectedTier 
}) => {
  const [builderNodes, setBuilderNodes] = useState<AgentBuilderNode[]>([
    { id: "1", type: "input", title: "Input", config: {} }
  ]);
  const [agentName, setAgentName] = useState("");
  const [agentDescription, setAgentDescription] = useState("");
  const [configJson, setConfigJson] = useState("{}");
  
  const createAgent = useMutation(api.aiAgents.createCustomAgent);

  const addNode = (type: "input" | "hook" | "output") => {
    const newNode: AgentBuilderNode = {
      id: Date.now().toString(),
      type,
      title: type.charAt(0).toUpperCase() + type.slice(1),
      config: {}
    };
    setBuilderNodes([...builderNodes, newNode]);
  };

  const removeNode = (id: string) => {
    setBuilderNodes(builderNodes.filter(node => node.id !== id));
  };

  const handleSave = async () => {
    if (!userId || !agentName) return;
    
    try {
      const config = {
        nodes: builderNodes,
        rawConfig: JSON.parse(configJson || "{}")
      };
      
      await createAgent({
        name: agentName,
        description: agentDescription,
        tags: ["custom-built"],
        config,
        businessId: "sample-business" as Id<"businesses">,
        userId,
      });
      
      toast.success("Agent created successfully");
      setAgentName("");
      setAgentDescription("");
      setBuilderNodes([{ id: "1", type: "input", title: "Input", config: {} }]);
      setConfigJson("{}");
    } catch (error) {
      toast.error("Failed to create agent");
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Graphical Agent Builder</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Palette */}
        <Card>
          <CardHeader>
            <CardTitle>Component Palette</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button 
              variant="outline" 
              className="w-full justify-start"
              onClick={() => addNode("input")}
            >
              <Target className="w-4 h-4 mr-2" />
              Add Input
            </Button>
            <Button 
              variant="outline" 
              className="w-full justify-start"
              onClick={() => addNode("hook")}
            >
              <Zap className="w-4 h-4 mr-2" />
              Add Hook
            </Button>
            <Button 
              variant="outline" 
              className="w-full justify-start"
              onClick={() => addNode("output")}
            >
              <TrendingUp className="w-4 h-4 mr-2" />
              Add Output
            </Button>
          </CardContent>
        </Card>

        {/* Canvas */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Flow</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 min-h-[300px]">
              {builderNodes.map((node, index) => (
                <div 
                  key={node.id}
                  className="flex items-center justify-between p-3 border rounded-lg bg-gray-50"
                >
                  <div className="flex items-center gap-2">
                    {node.type === "input" && <Target className="w-4 h-4" />}
                    {node.type === "hook" && <Zap className="w-4 h-4" />}
                    {node.type === "output" && <TrendingUp className="w-4 h-4" />}
                    <span>{node.title}</span>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => removeNode(node.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Properties */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Properties</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="agent-name">Name</Label>
              <Input
                id="agent-name"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="My Custom Agent"
              />
            </div>
            
            <div>
              <Label htmlFor="agent-description">Description</Label>
              <Textarea
                id="agent-description"
                value={agentDescription}
                onChange={(e) => setAgentDescription(e.target.value)}
                placeholder="What does this agent do?"
                rows={3}
              />
            </div>
            
            <div>
              <Label htmlFor="config-json">Configuration (JSON)</Label>
              <Textarea
                id="config-json"
                value={configJson}
                onChange={(e) => setConfigJson(e.target.value)}
                placeholder="{}"
                rows={6}
                className="font-mono text-sm"
              />
            </div>
            
            <Button onClick={handleSave} className="w-full">
              <Plus className="w-4 h-4 mr-2" />
              Create Agent
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Monitoring Tab Component
const MonitoringTab: React.FC<{ userId?: Id<"users"> }> = ({ userId }) => {
  const [selectedAgentId, setSelectedAgentId] = useState<Id<"custom_agents"> | null>(null);
  const [showRatingForm, setShowRatingForm] = useState(false);
  const [newRating, setNewRating] = useState(5);
  const [newComment, setNewComment] = useState("");
  
  const agents = useQuery(api.aiAgents.listCustomAgents, 
    userId ? { userId } : {}
  );
  const selectedAgent = selectedAgentId ? useQuery(api.aiAgents.getCustomAgent, { id: selectedAgentId }) : null;
  const ratings = selectedAgentId ? useQuery(api.aiAgents.listRatings, { agentId: selectedAgentId }) : null;
  
  const addRating = useMutation(api.aiAgents.addRating);

  const handleAddRating = async () => {
    if (!userId || !selectedAgentId) return;
    
    try {
      await addRating({
        agentId: selectedAgentId,
        userId,
        rating: newRating,
        comment: newComment || undefined,
      });
      toast.success("Rating added successfully");
      setShowRatingForm(false);
      setNewComment("");
    } catch (error) {
      toast.error("Failed to add rating");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Agent Monitoring</h2>
        
        <Select 
          value={selectedAgentId || ""} 
          onValueChange={(value) => setSelectedAgentId(value as Id<"custom_agents">)}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Select an agent to monitor" />
          </SelectTrigger>
          <SelectContent>
            {agents?.map((agent) => (
              <SelectItem key={agent._id} value={agent._id}>
                {agent.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedAgent && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Total Runs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">
                {selectedAgent.stats.runs}
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">
                {selectedAgent.stats.runs > 0 
                  ? Math.round((selectedAgent.stats.successes / selectedAgent.stats.runs) * 100)
                  : 0}%
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Last Run</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-gray-600">
                {selectedAgent.stats.lastRunAt 
                  ? new Date(selectedAgent.stats.lastRunAt).toLocaleDateString()
                  : "Never"
                }
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Version</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">
                {selectedAgent.currentVersion?.version || "1.0.0"}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {selectedAgentId && ratings && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>User Feedback</CardTitle>
              <Button onClick={() => setShowRatingForm(true)}>
                <Star className="w-4 h-4 mr-2" />
                Add Rating
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {ratings.map((rating) => (
                <div key={rating._id} className="border-b pb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star
                          key={star}
                          className={`w-4 h-4 ${
                            star <= rating.rating 
                              ? "fill-yellow-400 text-yellow-400" 
                              : "text-gray-300"
                          }`}
                        />
                      ))}
                    </div>
                    <span className="text-sm text-gray-600">
                      by {rating.user?.name || "Anonymous"}
                    </span>
                  </div>
                  {rating.comment && (
                    <p className="text-sm text-gray-700">{rating.comment}</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rating Form Dialog */}
      <Dialog open={showRatingForm} onOpenChange={setShowRatingForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Rating</DialogTitle>
            <DialogDescription>
              Rate this agent and provide feedback
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Rating</Label>
              <div className="flex gap-1 mt-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => setNewRating(star)}
                    className="p-1"
                  >
                    <Star
                      className={`w-6 h-6 ${
                        star <= newRating 
                          ? "fill-yellow-400 text-yellow-400" 
                          : "text-gray-300"
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>
            
            <div>
              <Label htmlFor="comment">Comment (optional)</Label>
              <Textarea
                id="comment"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Share your experience with this agent..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRatingForm(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddRating}>
              Submit Rating
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Versions List Component
const VersionsList: React.FC<{ agentId?: Id<"custom_agents"> }> = ({ agentId }) => {
  const versions = agentId ? useQuery(api.aiAgents.getVersions, { agentId }) : null;
  const rollback = useMutation(api.aiAgents.rollbackToVersion);

  const handleRollback = async (versionId: Id<"custom_agent_versions">) => {
    if (!agentId) return;
    
    try {
      await rollback({ agentId, versionId });
      toast.success("Rolled back to selected version");
    } catch (error) {
      toast.error("Failed to rollback");
    }
  };

  if (!versions) return <div>Loading versions...</div>;

  return (
    <div className="space-y-4">
      {versions.map((version: any) => (
        <Card key={version._id}>
          <CardContent className="pt-4">
            <div className="flex justify-between items-start mb-2">
              <div>
                <div className="font-semibold">Version {version.version}</div>
                <div className="text-sm text-gray-600">{version.changelog}</div>
              </div>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleRollback(version._id)}
              >
                <RotateCcw className="w-4 h-4 mr-1" />
                Rollback
              </Button>
            </div>
            <div className="text-xs text-gray-500">
              Created {new Date(version._creationTime).toLocaleDateString()}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default AgentsPage;