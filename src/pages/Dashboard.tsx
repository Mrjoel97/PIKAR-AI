import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { useQuery } from "convex/react";
import { useMutation } from "convex/react";
import { motion } from "framer-motion";
import { 
  Bot, 
  BarChart3, 
  Target, 
  Users, 
  Plus,
  Settings,
  TrendingUp,
  Activity,
  Zap,
  LogOut
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const { isLoading, isAuthenticated, user, signOut } = useAuth();
  const navigate = useNavigate();
  const [isSigningOut, setIsSigningOut] = useState(false);

  const businesses = useQuery(api.businesses.getUserBusinesses);

  const runDiagnostic = useMutation(api.diagnostics.run);
  const latestDiagnostic = useQuery(
    api.diagnostics.getLatest,
    businesses && businesses.length > 0
      ? { businessId: businesses[0]._id }
      : "skip" // Use Convex hook sentinel instead of undefined
  );
  const [runningDiag, setRunningDiag] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/auth");
    }
  }, [isLoading, isAuthenticated, navigate]);

  const handleLogout = async () => {
    setIsSigningOut(true);
    try {
      await signOut();
      toast.success("Signed out successfully");
      navigate("/");
    } catch (err) {
      console.error("Sign out failed:", err);
      toast.error("Failed to sign out. Please try again.");
      setIsSigningOut(false);
    }
  };

  const handleRunDiagnostic = async () => {
    if (!businesses || businesses.length === 0) return;
    setRunningDiag(true);
    try {
      await runDiagnostic({
        businessId: businesses[0]._id,
        inputs: { phase: "discovery", goals: [], signals: {} },
      });
      toast.success("Diagnostic completed");
    } catch (e) {
      console.error(e);
      toast.error("Failed to run diagnostic");
    } finally {
      setRunningDiag(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="neu-inset rounded-xl p-8">
          <Activity className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  // If user has no businesses, redirect to onboarding
  if (businesses && businesses.length === 0) {
    navigate("/onboarding");
    return null;
  }

  const currentBusiness = businesses?.[0]; // For now, use the first business

  // Add: tier helpers for conditional sections
  const tierOrder = ["solopreneur", "startup", "sme", "enterprise"] as const;
  const tier = (currentBusiness?.tier as (typeof tierOrder)[number]) || undefined;
  const isAtLeast = (level: (typeof tierOrder)[number]) =>
    !!tier && tierOrder.indexOf(tier) >= tierOrder.indexOf(level);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="min-h-screen bg-gradient-to-br from-background via-background to-accent/10"
    >
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-lg bg-background/80 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-14 md:h-16">
            <div className="flex items-center space-x-4">
              <motion.div 
                className="flex items-center space-x-3 cursor-pointer"
                onClick={() => navigate("/")}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <div className="neu-raised rounded-xl p-2">
                  <img src="./logo.svg" alt="Pikar AI" className="h-6 w-6" />
                </div>
                <span className="text-lg font-bold tracking-tight">Pikar AI</span>
              </motion.div>
              
              {currentBusiness && (
                <div className="hidden sm:block">
                  <span className="text-sm text-muted-foreground">•</span>
                  <span className="ml-2 text-sm font-medium">{currentBusiness.name}</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-2 sm:space-x-3">
              <Button 
                variant="ghost" 
                size="sm"
                className="neu-flat rounded-xl"
                onClick={() => navigate("/settings")}
                aria-label="Open settings"
                title="Settings"
              >
                <Settings className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="neu-flat rounded-xl"
                onClick={handleLogout}
                disabled={isSigningOut}
              >
                {isSigningOut ? (
                  <>
                    <Activity className="h-4 w-4 mr-2 animate-spin" />
                    Signing out...
                  </>
                ) : (
                  <>
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </>
                )}
              </Button>
              <div className="neu-inset rounded-xl p-2">
                <div className="h-6 w-6 bg-primary rounded-lg flex items-center justify-center">
                  <span className="text-xs font-medium text-primary-foreground">
                    {user.name?.charAt(0) || user.email?.charAt(0) || "U"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Welcome Section */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold tracking-tight mb-2">
            Welcome back, {user.name || "there"}! 👋
          </h1>
          <p className="text-muted-foreground">
            Here's what's happening with your AI-powered business operations
          </p>
        </motion.div>

        {/* Quick Stats */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active Agents</p>
                  <p className="text-2xl font-bold">12</p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Tasks Completed</p>
                  <p className="text-2xl font-bold">1,247</p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <Target className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">ROI Increase</p>
                  <p className="text-2xl font-bold">+34%</p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <TrendingUp className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Time Saved</p>
                  <p className="text-2xl font-bold">156h</p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Active Initiatives */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-xl font-semibold">Active Initiatives</CardTitle>
                  <Button 
                    size="sm" 
                    className="neu-flat rounded-xl"
                    onClick={() => navigate("/initiatives/new")}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    New Initiative
                  </Button>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="space-y-4">
                    {[
                      { name: "Q4 Marketing Campaign", progress: 75, status: "On Track" },
                      { name: "Customer Onboarding Automation", progress: 45, status: "In Progress" },
                      { name: "Sales Pipeline Optimization", progress: 90, status: "Nearly Complete" }
                    ].map((initiative, index) => (
                      <div key={initiative.name} className="neu-inset rounded-xl p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium">{initiative.name}</h4>
                          <span className="text-sm text-muted-foreground">{initiative.status}</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                          <div 
                            className="bg-primary h-2 rounded-full transition-all duration-300"
                            style={{ width: `${initiative.progress}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Performance Analytics */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader>
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <BarChart3 className="h-5 w-5 mr-2" />
                    Performance Analytics
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="h-64 neu-inset rounded-xl flex items-center justify-center">
                    <p className="text-muted-foreground">Analytics chart will be displayed here</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Add: Tiered sections for Solopreneur */}
            {tier === "solopreneur" && (
              <>
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.35 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Quick Start Templates</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {[
                          { name: "Content Calendar (30d)", desc: "Plan a month of posts fast" },
                          { name: "Lead Magnet", desc: "Build a simple lead capture funnel" },
                          { name: "Welcome Email", desc: "Automated intro to new subscribers" },
                          { name: "Offer Landing Page", desc: "Launch a single offer quickly" },
                        ].map((t) => (
                          <div key={t.name} className="neu-inset rounded-xl p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-sm">{t.name}</p>
                                <p className="text-xs text-muted-foreground">{t.desc}</p>
                              </div>
                              <Button size="sm" className="neu-flat rounded-xl">Use</Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Simple Analytics</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[
                          { label: "This Week Posts", value: "8" },
                          { label: "Leads Captured", value: "32" },
                          { label: "CTR", value: "3.4%" },
                        ].map((m) => (
                          <div key={m.label} className="neu-inset rounded-xl p-4">
                            <div className="text-xs text-muted-foreground">{m.label}</div>
                            <div className="text-xl font-semibold">{m.value}</div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.45 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Weekly Tips</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <ul className="space-y-2 text-sm">
                        {[
                          "Repurpose a top post into a short email to your list.",
                          "Batch-create 5 hooks for your next 3 posts.",
                          "Cross-post content to one new channel for discovery.",
                        ].map((tip, i) => (
                          <li key={i} className="neu-inset rounded-xl p-3">{tip}</li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </motion.div>
              </>
            )}

            {/* Add: Tiered sections for Startup */}
            {tier === "startup" && (
              <>
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.35 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Growth Levers</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[
                          { name: "Outbound Sequences", hint: "Warm + cold" },
                          { name: "Content Sprints", hint: "Topical focus" },
                          { name: "Referral Loop", hint: "Lightweight incentives" },
                        ].map((g) => (
                          <div key={g.name} className="neu-inset rounded-xl p-4">
                            <div className="font-medium text-sm">{g.name}</div>
                            <div className="text-xs text-muted-foreground">{g.hint}</div>
                            <div className="mt-3">
                              <Button variant="outline" size="sm" className="neu-flat rounded-xl">Open</Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Experiments (A/B)</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="space-y-3">
                        {[
                          { name: "Landing Page CTA", status: "Running", uplift: "+8.2%" },
                          { name: "Email Subject Line", status: "Draft", uplift: "-" },
                          { name: "Ad Creative Variant", status: "Queued", uplift: "-" },
                        ].map((e, i) => (
                          <div key={i} className="neu-inset rounded-xl p-3 flex items-center justify-between">
                            <div>
                              <p className="font-medium text-sm">{e.name}</p>
                              <p className="text-xs text-muted-foreground">{e.status}</p>
                            </div>
                            <div className="text-xs text-muted-foreground">{e.uplift}</div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.45 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Team Preview</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {[
                          { role: "Marketing", members: 3 },
                          { role: "Sales", members: 2 },
                          { role: "Ops", members: 1 },
                          { role: "Product", members: 2 },
                        ].map((r, i) => (
                          <div key={i} className="neu-inset rounded-xl p-4">
                            <div className="flex items-center justify-between">
                              <div className="font-medium text-sm">{r.role}</div>
                              <div className="text-xs text-muted-foreground">{r.members} members</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* AI Agents Status */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader>
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <Bot className="h-5 w-5 mr-2" />
                    AI Agents
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="space-y-3">
                    {[
                      { name: "Content Creator", status: "Active", tasks: 23 },
                      { name: "Sales Intelligence", status: "Active", tasks: 15 },
                      { name: "Customer Support", status: "Idle", tasks: 0 },
                      { name: "Analytics Bot", status: "Processing", tasks: 8 }
                    ].map((agent) => (
                      <div key={agent.name} className="neu-inset rounded-xl p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-sm">{agent.name}</p>
                            <p className="text-xs text-muted-foreground">{agent.tasks} tasks</p>
                          </div>
                          <div className={`h-2 w-2 rounded-full ${
                            agent.status === 'Active' ? 'bg-green-500' :
                            agent.status === 'Processing' ? 'bg-yellow-500' : 'bg-gray-400'
                          }`} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <Button 
                    variant="outline" 
                    className="w-full mt-4 neu-flat rounded-xl"
                    onClick={() => navigate("/agents")}
                  >
                    Manage Agents
                  </Button>
                </CardContent>
              </Card>
            </motion.div>

            {/* Diagnostic Recommendations */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.45 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader className="flex items-center justify-between">
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <Zap className="h-5 w-5 mr-2" />
                    Diagnostic Recommendations
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    className="neu-flat rounded-xl"
                    onClick={handleRunDiagnostic}
                    disabled={runningDiag}
                    aria-label="Run diagnostic"
                    title="Run diagnostic"
                  >
                    {runningDiag ? (
                      <>
                        <Activity className="h-4 w-4 mr-2 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Re-run
                      </>
                    )}
                  </Button>
                </CardHeader>
                <CardContent className="p-6 pt-0 space-y-4">
                  {!latestDiagnostic ? (
                    <div className="neu-inset rounded-xl p-4 text-sm text-muted-foreground">
                      No diagnostic available yet. Click "Re-run" to generate recommendations.
                    </div>
                  ) : (
                    <>
                      <div className="neu-inset rounded-xl p-4">
                        <h4 className="font-medium mb-2">KPI Targets</h4>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div className="neu-flat rounded-lg p-3">
                            <div className="text-muted-foreground">Target ROI</div>
                            <div className="font-semibold">
                              {(latestDiagnostic.outputs.kpis.targetROI * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="neu-flat rounded-lg p-3">
                            <div className="text-muted-foreground">Completion Rate</div>
                            <div className="font-semibold">
                              {(latestDiagnostic.outputs.kpis.targetCompletionRate * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {(["daily", "weekly", "monthly"] as const).map((freq) => {
                          const items = latestDiagnostic.outputs.tasks.filter((t: any) => t.frequency === freq);
                          if (items.length === 0) return null;
                          return (
                            <div key={freq} className="neu-inset rounded-xl p-4">
                              <h4 className="font-medium capitalize mb-2">{freq} Tasks</h4>
                              <ul className="space-y-2">
                                {items.map((t: any, idx: number) => (
                                  <li key={idx} className="text-sm">
                                    <span className="font-medium">{t.title}</span>
                                    <span className="text-muted-foreground"> — {t.description}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          );
                        })}
                      </div>

                      <div className="neu-inset rounded-xl p-4">
                        <h4 className="font-medium mb-2">Recommended Workflows</h4>
                        <ul className="space-y-2">
                          {latestDiagnostic.outputs.workflows.map((w: any, idx: number) => (
                            <li key={idx} className="text-sm flex items-center justify-between">
                              <div>
                                <span className="font-medium">{w.name}</span>
                                <span className="text-muted-foreground"> — {w.agentType.replaceAll("_", " ")}</span>
                              </div>
                              <span className="text-xs text-muted-foreground">Template: {w.templateId}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="text-xs text-muted-foreground">
                        Last Run: {new Date(latestDiagnostic.runAt).toLocaleString()}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Recent Activity */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader>
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <Activity className="h-5 w-5 mr-2" />
                    Recent Activity
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="space-y-3">
                    {[
                      { action: "Content created", time: "2 min ago", agent: "Content Creator" },
                      { action: "Lead qualified", time: "15 min ago", agent: "Sales Intelligence" },
                      { action: "Report generated", time: "1 hour ago", agent: "Analytics Bot" },
                      { action: "Task completed", time: "2 hours ago", agent: "Operations" }
                    ].map((activity, index) => (
                      <div key={index} className="neu-inset rounded-xl p-3">
                        <p className="text-sm font-medium">{activity.action}</p>
                        <div className="flex items-center justify-between mt-1">
                          <p className="text-xs text-muted-foreground">{activity.agent}</p>
                          <p className="text-xs text-muted-foreground">{activity.time}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </main>
    </motion.div>
  );
}