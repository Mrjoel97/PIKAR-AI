import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { useQuery } from "convex/react";
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
  Zap
} from "lucide-react";
import { useNavigate } from "react-router";
import { useEffect } from "react";

export default function Dashboard() {
  const { isLoading, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  
  const businesses = useQuery(api.businesses.getUserBusinesses);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/auth");
    }
  }, [isLoading, isAuthenticated, navigate]);

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

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="min-h-screen bg-gradient-to-br from-background via-background to-accent/10"
    >
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-lg bg-background/80 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
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
            
            <div className="flex items-center space-x-3">
              <Button 
                variant="ghost" 
                size="sm"
                className="neu-flat rounded-xl"
                onClick={() => navigate("/settings")}
              >
                <Settings className="h-4 w-4" />
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
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
