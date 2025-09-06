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
import { useLocation } from "react-router";

interface AgentBuilderNode {
  id: string;
  type: "input" | "hook" | "output";
  title: string;
  config: any;
}

const AgentsPage: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();
  const isDirectory = location.pathname === "/ai-agents";
  // Default to Templates tab in directory view
  const [activeTab, setActiveTab] = useState(isDirectory ? "templates" : "my-agents");
  // Default to enterprise in the directory view so enterprise templates show immediately
  const [selectedTier, setSelectedTier] = useState<string>(isDirectory ? "enterprise" : "solopreneur");
  
  // Seed data on mount
  const seedAction = useAction(api.aiAgents.seedAgentFramework);
  const seedEnterprise = useAction(api.aiAgents.seedEnterpriseTemplates);
  
  useEffect(() => {
    const initSeed = async () => {
      try {
        await seedAction({});
      } catch (error) {
        // Ignore if already seeded
      }
      try {
        await seedEnterprise({});
      } catch (error) {
        // Ignore if already seeded
      }
    };
    initSeed();
  }, [seedAction, seedEnterprise]);

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
              {isDirectory ? "Agent Directory" : "Custom Agent Framework"}
            </h1>
            <p className="text-gray-600">
              {isDirectory
                ? "Browse, use, and manage AI agents across templates and marketplace"
                : "Build, deploy, and manage intelligent automation agents"}
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

function MyAgentsTab({
  userId,
}: {
  userId?: Id<"users">;
  selectedTier: string;
}) {
  // Fetch current user to derive businessId
  const currentUser = useQuery(api.users.currentUser, {});
  const businessId = currentUser?.businessId as Id<"businesses"> | undefined;

  const agents = useQuery(
    api.aiAgents.listCustomAgents,
    userId ? { userId } : ({} as any),
  );

  // Fetch Pikar AI App Agents for the user's business
  const pikarAgents = useQuery(
    api.aiAgents.getByBusiness,
    businessId ? ({ businessId } as any) : undefined
  );

  const seedEnhanced = useMutation(api.aiAgents.seedEnhancedForBusiness);

  const createCustomAgent = useMutation(api.aiAgents.createCustomAgent);

  // Local state for "Create Custom Agent" dialog
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string>("");
  const [visibility, setVisibility] = useState<"private" | "team" | "market">("private");
  const [riskLevel, setRiskLevel] = useState<"low" | "medium" | "high">("low");

  const handleSeed = async () => {
    if (!businessId) {
      toast("No business linked to your account yet.");
      return;
    }
    try {
      await seedEnhanced({ businessId });
      toast("Pikar AI App Agents added to your workspace.");
    } catch (e: any) {
      toast(`Failed to add agents: ${e?.message ?? "Unknown error"}`);
    }
  };

  const handleCreateCustom = async () => {
    if (!userId || !businessId) {
      toast("You must be signed in with a business to create agents.");
      return;
    }
    if (!name.trim()) {
      toast("Please provide a name.");
      return;
    }
    try {
      await createCustomAgent({
        name: name.trim(),
        description: description.trim() || "Custom agent",
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        config: {}, // blank slate
        businessId,
        userId,
        visibility,
        riskLevel,
      } as any);
      toast("Custom agent created.");
      setOpen(false);
      setName("");
      setDescription("");
      setTags("");
      setVisibility("private");
      setRiskLevel("low");
    } catch (e: any) {
      toast(`Failed to create agent: ${e?.message ?? "Unknown error"}`);
    }
  };

  if (agents === undefined || (businessId && pikarAgents === undefined)) {
    return <div className="text-gray-600">Loading your agents...</div>;
  }

  return (
    <div className="space-y-8">
      {/* Header actions */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="space-y-1">
          <h3 className="text-xl font-semibold">My Agents</h3>
          <p className="text-sm text-gray-600">Your custom agents and built-in Pikar AI app agents.</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={handleSeed} disabled={!businessId}>
            Add Pikar AI App Agents
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Create Custom Agent
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Custom Agent</DialogTitle>
                <DialogDescription>Start from a blank slate without using a template.</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., Outreach Assistant" />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this agent do?" />
                </div>
                <div className="space-y-2">
                  <Label>Tags (comma separated)</Label>
                  <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="sales, outreach, email" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Visibility</Label>
                    <Select value={visibility} onValueChange={(v) => setVisibility(v as any)}>
                      <SelectTrigger><SelectValue placeholder="Select visibility" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="private">Private</SelectItem>
                        <SelectItem value="team">Team</SelectItem>
                        <SelectItem value="market">Market</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Risk Level</Label>
                    <Select value={riskLevel} onValueChange={(v) => setRiskLevel(v as any)}>
                      <SelectTrigger><SelectValue placeholder="Select risk level" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleCreateCustom} disabled={!userId || !businessId}>
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Pikar AI App Agents */}
      <div className="space-y-3">
        <h4 className="text-lg font-semibold">Pikar AI App Agents</h4>
        {!businessId ? (
          <Card>
            <CardHeader>
              <CardTitle>Connect to a Business</CardTitle>
              <CardDescription>Link your account to a business to view built-in app agents.</CardDescription>
            </CardHeader>
          </Card>
        ) : pikarAgents && pikarAgents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {pikarAgents.map((a: any) => (
              <Card key={a._id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{a.name}</span>
                    <Badge variant="secondary">{a.isActive ? "Active" : "Inactive"}</Badge>
                  </CardTitle>
                  <CardDescription>{a.description || "Built-in agent"}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {!!(a.capabilities?.length) && (
                    <div className="flex flex-wrap gap-2">
                      {a.capabilities.map((t: string) => (
                        <Badge key={t} variant="outline">{t}</Badge>
                      ))}
                    </div>
                  )}
                  <div className="text-sm text-gray-500">
                    Tasks: {a.performance?.tasksCompleted ?? 0} • Success Rate: {(a.performance?.successRate ?? 0)}%
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>No built-in agents found</CardTitle>
              <CardDescription>Click "Add Pikar AI App Agents" to populate your workspace.</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>

      {/* Custom Agents */}
      <div className="space-y-3">
        <h4 className="text-lg font-semibold">Your Custom Agents</h4>
        {agents && agents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {agents.map((a: any) => (
              <Card key={a._id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{a.name}</span>
                    <Badge variant="secondary">{a.visibility}</Badge>
                  </CardTitle>
                  <CardDescription>{a.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    {(a.tags || []).map((t: string) => (
                      <Badge key={t} variant="outline">{t}</Badge>
                    ))}
                  </div>
                  <div className="text-sm text-gray-500">
                    Runs: {a.stats?.runs ?? 0} • Successes: {a.stats?.successes ?? 0}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>No custom agents yet</CardTitle>
              <CardDescription>Create agents from scratch with the button above, or from templates.</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </div>
  );
}

function TemplatesTab({
  userId,
  selectedTier,
}: {
  userId?: Id<"users">;
  selectedTier: string;
}) {
  const seedEnterprise = useAction(api.aiAgents.seedEnterpriseTemplates);
  const [attemptedSeed, setAttemptedSeed] = useState(false);

  const templates = useQuery(api.aiAgents.listTemplates, { tier: selectedTier });

  useEffect(() => {
    if (
      selectedTier === "enterprise" &&
      templates !== undefined &&
      templates.length === 0 &&
      !attemptedSeed
    ) {
      (async () => {
        try {
          await seedEnterprise({});
        } catch {
          // ignore errors (e.g., already seeded)
        } finally {
          setAttemptedSeed(true);
        }
      })();
    }
  }, [selectedTier, templates, attemptedSeed, seedEnterprise]);

  if (templates === undefined) {
    return <div className="text-gray-600">Loading templates...</div>;
  }

  if (!templates.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No templates found</CardTitle>
          <CardDescription>
            Try a different tier or refresh to load the latest templates.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {templates.map((t: any) => (
        <Card key={t._id}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{t.name}</span>
              <Badge variant="secondary">{t.tier ?? selectedTier}</Badge>
            </CardTitle>
            <CardDescription>{t.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {(t.tags || []).map((tag: string) => (
                <Badge key={tag} variant="outline">
                  {tag}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function MarketplaceTab({ userId }: { userId?: Id<"users"> }) {
  const items = useQuery(api.aiAgents.listMarketplaceAgents, {
    status: "approved",
  });

  if (items === undefined) {
    return <div className="text-gray-600">Loading marketplace...</div>;
  }

  if (!items.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No approved marketplace agents yet</CardTitle>
          <CardDescription>
            Check back soon for curated agents from the community.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {items.map((m: any) => (
        <Card key={m._id}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{m.agent?.name ?? "Untitled Agent"}</span>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Star className="w-4 h-4 text-yellow-500" />
                <span>{(m.avgRating ?? 0).toFixed(1)}</span>
                <span>({m.ratingsCount ?? 0})</span>
              </div>
            </CardTitle>
            <CardDescription>{m.agent?.description}</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-gray-600">
            Runs: {m.stats?.runs ?? 0} • Successes: {m.stats?.successes ?? 0}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function BuilderTab({}: { userId?: Id<"users">; selectedTier: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Builder</CardTitle>
        <CardDescription>
          Use templates as a starting point and customize configurations for
          your workflows.
        </CardDescription>
      </CardHeader>
      <CardContent className="text-gray-600">
        Select a template from the Templates tab to begin.
      </CardContent>
    </Card>
  );
}

function MonitoringTab({}: { userId?: Id<"users"> }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Monitoring</CardTitle>
        <CardDescription>
          Track performance, usage, and success rates of your agents.
        </CardDescription>
      </CardHeader>
      <CardContent className="text-gray-600">
        Connect agents to workflows to see real-time insights here.
      </CardContent>
    </Card>
  );
}

export default AgentsPage;