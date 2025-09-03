

import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { createPageUrl } from "@/utils";
import { Brain, LayoutDashboard, PenSquare, Settings, User, Lightbulb, Users, BarChart, Sparkles, DollarSign, UserCheck, ShieldCheck, SlidersHorizontal, Cpu, Network, Shield, Route, ChevronDown, Award, ListChecks, FileDown, Plug, CheckSquare, Search, Command, Wrench, Target, GraduationCap, Database, Megaphone, FileText, Trash2, TestTube, LogOut } from "lucide-react";
import ErrorBoundary from "@/components/ui/error-boundary";
import { ToastProvider } from "@/components/ui/toast-manager";
import SkipToContent, { MainContent, NavigationLandmark } from "@/components/accessibility/SkipToContent";
import { TrialStatusIndicator } from "@/components/trial/TrialManager";
import { PWAInstaller, ServiceWorkerRegistration } from "@/components/ui/progressive-web-app";
import GlobalSearch from "@/components/ui/global-search";
import { MotionSection, staggerContainer, listItemVariants } from "@/components/ui/motion-primitives";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import TierSwitcher from "@/components/dashboard/TierSwitcher";
import { useAuth } from "@/contexts/AuthContext";
import { PermissionGuard, TierGuard } from "@/components/auth/ProtectedRoute";

// Main navigation items
const navigationItems = [
  { title: "Dashboard", icon: LayoutDashboard, url: createPageUrl("SmeDashboard") }, // Updated to SME Dashboard, will be dynamically changed
  { title: "Transformation Hub", icon: Target, url: createPageUrl("TransformationHub") },
  { title: "Agent Orchestration", icon: Cpu, url: createPageUrl("Orchestrate") },
  { title: "Performance Analytics", icon: BarChart, url: createPageUrl("PerformanceAnalytics") },
  { title: "Resource Management", icon: DollarSign, url: createPageUrl("ResourceManagement") },
  { title: "API Tester", icon: TestTube, url: createPageUrl("SocialPlatformTester") }, // Added new navigation item
];

// AI Agents
const agentItems = [
  { title: "Strategic Planning", icon: Target, url: createPageUrl("StrategicPlanning") },
  { title: "Customer Support", icon: Users, url: createPageUrl("CustomerSupport") },
  { title: "Sales Intelligence", icon: DollarSign, url: createPageUrl("SalesIntelligence") },
  { title: "Content Creation", icon: PenSquare, url: createPageUrl("ContentCreation") },
  { title: "Data Analysis", icon: BarChart, url: createPageUrl("DataAnalysis") },
  { title: "Marketing Automation", icon: Sparkles, url: createPageUrl("MarketingAutomation") },
  { title: "Financial Analysis", icon: DollarSign, url: createPageUrl("FinancialAnalysis") },
  { title: "HR & Recruitment", icon: UserCheck, url: createPageUrl("HRRecruitment") },
  { title: "Operations Optimization", icon: SlidersHorizontal, url: createPageUrl("OperationsOptimization") },
  { title: "Compliance & Risk", icon: ShieldCheck, url: createPageUrl("ComplianceRisk") },
  { title: "Custom Agents", icon: Brain, url: createPageUrl("CustomAgents") },
];

// Platform & Tools
const platformItems = [
  { title: "Agent Directory", icon: Network, url: createPageUrl("AgentDirectory") },
  { title: "Learning Hub", icon: GraduationCap, url: createPageUrl("LearningHub") },
  { title: "Knowledge Hub", icon: Database, url: createPageUrl("KnowledgeHub") },
  { title: "Collaboration Hub", icon: Users, url: createPageUrl("CollaborationHub") },
  { title: "Workflow Templates", icon: Route, url: createPageUrl("CreateWorkflow") },
  { title: "Integrations", icon: Plug, url: createPageUrl("Integrations") },
  { title: "Quality Management", icon: CheckSquare, url: createPageUrl("QualityManagement") },
  { title: "Audit Trail", icon: ListChecks, url: createPageUrl("AuditTrail") },
  { title: "Reporting", icon: FileDown, url: createPageUrl("Reporting") },
  { title: "Marketing Suite", icon: Megaphone, url: createPageUrl("MarketingSuite") },
  { title: "Social Media Marketing", icon: Megaphone, url: createPageUrl("SocialMediaMarketing") },
  { title: "Social Campaigns", icon: Megaphone, url: createPageUrl("SocialCampaigns") },
  { title: "Social API Readiness", icon: Plug, url: createPageUrl("SocialAPIReadiness") },
  { title: "Marketing Suite Tests", icon: Target, url: createPageUrl("MarketingSuiteTests") }
];

// System & Settings
const systemItems = [
  { title: "Settings", icon: Settings, url: createPageUrl("Settings") },
  { title: "Implementation Status", icon: CheckSquare, url: createPageUrl("ImplementationStatus") },
  { title: "Platform Testing", icon: Wrench, url: createPageUrl("PlatformTesting") },
  { title: "Privacy Policy", icon: ShieldCheck, url: createPageUrl("PrivacyPolicy") },
  { title: "Terms of Service", icon: FileText, url: createPageUrl("Terms") },
  { title: "Data Deletion", icon: Trash2, url: createPageUrl("DataDeletion") }
];

// Sidebar variants for animations
const sidebarVariants = {
  closed: { 
    x: -280,
    opacity: 0
  },
  open: { 
    x: 0,
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 120,
      damping: 18
    }
  }
};

export default function Layout({ children, currentPageName }) {
  const location = useLocation();
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const searchParams = new URLSearchParams(location.search);
  const currentTier = searchParams.get('tier') || 'enterprise';

  let dashboardUrl;
  switch (currentTier) {
      case 'sme':
          dashboardUrl = createPageUrl("SmeDashboard");
          break;
      case 'startup':
          dashboardUrl = createPageUrl("StartupDashboard");
          break;
      case 'solopreneur':
          dashboardUrl = createPageUrl("SolopreneurDashboard");
          break;
      default: // 'enterprise' or any other value
          dashboardUrl = createPageUrl("Dashboard");
          break;
  }
  
  // Update dashboard URL in navigation
  const updatedNavigationItems = navigationItems.map(item => 
      item.title === 'Dashboard' ? { ...item, url: dashboardUrl } : item
  );

  // Keyboard shortcut for search
  React.useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        setIsSearchOpen(true);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
        await logout();
        // Redirect to login page
        window.location.href = '/login';
    } catch (error) {
        toast.error("Logout failed. Please try again.");
        console.error("Logout error:", error);
    }
  };

  return (
    <ErrorBoundary>
      <ToastProvider>
        <SkipToContent />
        <PWAInstaller />
        <ServiceWorkerRegistration />
        <SidebarProvider>
          <div className="min-h-screen flex w-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
            <NavigationLandmark ariaLabel="Main navigation">
              <motion.div
                variants={sidebarVariants}
                initial="closed"
                animate="open"
              >
                <Sidebar className="border-r border-gray-200/50 dark:border-gray-800 bg-white/95 dark:bg-gray-950/95 backdrop-blur-sm">
                <SidebarHeader className="border-b border-gray-200/50 dark:border-gray-800 p-4">
                  <motion.div 
                    className="flex items-center gap-3"
                    whileHover={{ scale: 1.02 }}
                    transition={{ duration: 0.18 }}
                  >
                    <div className="w-9 h-9 bg-gradient-to-br from-emerald-600 to-emerald-900 rounded-xl flex items-center justify-center">
                      <Brain className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h2 className="font-bold text-lg text-gray-900 dark:text-white">PIKAR AI</h2>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Business Intelligence</p>
                    </div>
                  </motion.div>
                </SidebarHeader>
                
                <SidebarContent className="p-2 flex-1">
                  {/* Search Button with enhanced animation */}
                  <div className="px-2 mb-4">
                    <motion.button
                      onClick={() => setIsSearchOpen(true)}
                      className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-600 bg-gray-100/80 hover:bg-gray-200/80 rounded-xl transition-colors backdrop-blur-sm"
                      whileHover={{ scale: 1.01, boxShadow: '0 4px 12px rgba(6,95,70,0.08)' }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ duration: 0.18 }}
                    >
                      <Search className="w-4 h-4" />
                      <span>Search...</span>
                      <div className="ml-auto flex gap-1">
                        <kbd className="px-1.5 py-0.5 text-xs bg-white rounded border shadow-sm">⌘</kbd>
                        <kbd className="px-1.5 py-0.5 text-xs bg-white rounded border shadow-sm">K</kbd>
                      </div>
                    </motion.button>
                  </div>

                  {/* Enhanced navigation groups with stagger animations */}
                  <motion.div
                    variants={staggerContainer}
                    initial="hidden"
                    animate="show"
                  >
                    <SidebarGroup>
                      <SidebarGroupLabel className="text-xs font-medium text-gray-500 uppercase tracking-wider px-2 py-2">
                        Overview
                      </SidebarGroupLabel>
                      <SidebarGroupContent>
                        <SidebarMenu>
                          {updatedNavigationItems.map((item) => {
                            // Define permission requirements for navigation items
                            const getItemPermissions = (title) => {
                              switch (title) {
                                case 'Performance Analytics':
                                  return ['advanced_analytics'];
                                case 'API Tester':
                                  return ['api_access'];
                                case 'Resource Management':
                                  return ['advanced_analytics'];
                                default:
                                  return ['basic_agents']; // Basic permission for most items
                              }
                            };

                            return (
                              <PermissionGuard
                                key={item.title}
                                permissions={getItemPermissions(item.title)}
                                fallback={null}
                              >
                                <motion.div variants={listItemVariants}>
                                  <SidebarMenuItem>
                                    <SidebarMenuButton
                                      asChild
                                      className={`hover:bg-emerald-50 dark:hover:bg-emerald-900/20 hover:text-emerald-900 dark:hover:text-emerald-100 transition-all duration-200 rounded-xl mb-1 ${
                                        location.pathname.startsWith(item.url)
                                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-900 dark:text-emerald-100' : 'text-gray-600 dark:text-gray-400'
                                      }`}
                                    >
                                      <Link to={`${item.url}?tier=${currentTier}`} className="flex items-center gap-3 px-3 py-2">
                                        <item.icon className="w-4 h-4" />
                                        <span className="font-medium text-sm">{item.title}</span>
                                      </Link>
                                    </SidebarMenuButton>
                                  </SidebarMenuItem>
                                </motion.div>
                              </PermissionGuard>
                            );
                          })}
                        </SidebarMenu>
                      </SidebarGroupContent>
                    </SidebarGroup>

                    {/* Enhanced AI Agents section */}
                    <SidebarGroup>
                      <Collapsible defaultOpen={true}>
                        <SidebarGroupLabel asChild>
                          <CollapsibleTrigger className="flex w-full items-center gap-2 text-xs font-medium text-gray-500 uppercase tracking-wider px-2 py-2 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-xl transition-colors duration-200">
                            <Brain className="w-4 h-4" />
                            AI Agents
                            <ChevronDown className="ml-auto h-4 w-4 shrink-0 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-180" />
                          </CollapsibleTrigger>
                        </SidebarGroupLabel>
                        <CollapsibleContent>
                          <SidebarGroupContent>
                            <SidebarMenu>
                              {agentItems.map((item) => {
                                // Define permission requirements for AI agents
                                const getAgentPermissions = (title) => {
                                  switch (title) {
                                    case 'Strategic Planning':
                                    case 'Customer Support':
                                    case 'Content Creation':
                                      return ['basic_agents'];
                                    case 'Sales Intelligence':
                                    case 'Data Analysis':
                                    case 'Marketing Automation':
                                      return ['advanced_agents'];
                                    case 'Financial Analysis':
                                    case 'HR & Recruitment':
                                    case 'Operations Optimization':
                                    case 'Compliance & Risk':
                                      return ['all_agents'];
                                    case 'Custom Agents':
                                      return ['custom_integrations'];
                                    default:
                                      return ['basic_agents'];
                                  }
                                };

                                return (
                                  <PermissionGuard
                                    key={item.title}
                                    permissions={getAgentPermissions(item.title)}
                                    fallback={
                                      <motion.div
                                        variants={listItemVariants}
                                        whileHover={{ x: 4 }}
                                        transition={{ duration: 0.18 }}
                                      >
                                        <SidebarMenuItem>
                                          <div className="flex items-center gap-3 px-3 py-2 text-gray-400 cursor-not-allowed opacity-50">
                                            <item.icon className="w-4 h-4" />
                                            <span className="font-medium text-sm">{item.title}</span>
                                            <TierGuard minTier="startup" fallback={<span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full ml-auto">Upgrade</span>}>
                                              <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-1 rounded-full ml-auto">Available</span>
                                            </TierGuard>
                                          </div>
                                        </SidebarMenuItem>
                                      </motion.div>
                                    }
                                  >
                                    <motion.div
                                      variants={listItemVariants}
                                      whileHover={{ x: 4 }}
                                      transition={{ duration: 0.18 }}
                                    >
                                      <SidebarMenuItem>
                                        <SidebarMenuButton
                                          asChild
                                          className={`hover:bg-emerald-50 dark:hover:bg-emerald-900/20 hover:text-emerald-900 dark:hover:text-emerald-100 transition-all duration-200 rounded-xl mb-1 ${
                                            location.pathname.startsWith(item.url) ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-900 dark:text-emerald-100' : 'text-gray-600 dark:text-gray-400'
                                          }`}
                                        >
                                          <Link to={`${item.url}?tier=${currentTier}`} className="flex items-center gap-3 px-3 py-2">
                                            <item.icon className="w-4 h-4" />
                                            <span className="font-medium text-sm">{item.title}</span>
                                          </Link>
                                        </SidebarMenuButton>
                                      </SidebarMenuItem>
                                    </motion.div>
                                  </PermissionGuard>
                                );
                              })}
                            </SidebarMenu>
                          </SidebarGroupContent>
                        </CollapsibleContent>
                      </Collapsible>
                    </SidebarGroup>

                    {/* Platform & Tools Section */}
                    <SidebarGroup>
                      <Collapsible defaultOpen={false}>
                        <SidebarGroupLabel asChild>
                          <CollapsibleTrigger className="flex w-full items-center gap-2 text-xs font-medium text-gray-500 uppercase tracking-wider px-2 py-2 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-xl transition-colors duration-200">
                            <Wrench className="w-4 h-4" />
                            Platform & Tools
                            <ChevronDown className="ml-auto h-4 w-4 shrink-0 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-180" />
                          </CollapsibleTrigger>
                        </SidebarGroupLabel>
                        <CollapsibleContent>
                          <SidebarGroupContent>
                            <SidebarMenu>
                              {platformItems.map((item) => (
                                <motion.div key={item.title} variants={listItemVariants}>
                                  <SidebarMenuItem>
                                    <SidebarMenuButton 
                                      asChild 
                                      className={`hover:bg-emerald-50 dark:hover:bg-emerald-900/20 hover:text-emerald-900 dark:hover:text-emerald-100 transition-all duration-200 rounded-xl mb-1 ${
                                        location.pathname.startsWith(item.url) ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-900 dark:text-emerald-100' : 'text-gray-600 dark:text-gray-400'
                                      }`}
                                    >
                                      <Link to={`${item.url}?tier=${currentTier}`} className="flex items-center gap-3 px-3 py-2">
                                        <item.icon className="w-4 h-4" />
                                        <span className="font-medium text-sm">{item.title}</span>
                                      </Link>
                                    </SidebarMenuButton>
                                  </SidebarMenuItem>
                                </motion.div>
                              ))}
                            </SidebarMenu>
                          </SidebarGroupContent>
                        </CollapsibleContent>
                      </Collapsible>
                    </SidebarGroup>

                    {/* System & Settings */}
                    <SidebarGroup>
                      <SidebarGroupLabel className="text-xs font-medium text-gray-500 uppercase tracking-wider px-2 py-2">
                        System
                      </SidebarGroupLabel>
                      <SidebarGroupContent>
                        <SidebarMenu>
                          {systemItems.map((item) => (
                            <motion.div key={item.title} variants={listItemVariants}>
                              <SidebarMenuItem>
                                <SidebarMenuButton 
                                  asChild 
                                  className={`hover:bg-emerald-50 dark:hover:bg-emerald-900/20 hover:text-emerald-900 dark:hover:text-emerald-100 transition-all duration-200 rounded-xl mb-1 ${
                                    location.pathname.startsWith(item.url) ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-900 dark:text-emerald-100' : 'text-gray-600 dark:text-gray-400'
                                  }`}
                                >
                                  <Link to={`${item.url}?tier=${currentTier}`} className="flex items-center gap-3 px-3 py-2">
                                    <item.icon className="w-4 h-4" />
                                    <span className="font-medium text-sm">{item.title}</span>
                                  </Link>
                                </SidebarMenuButton>
                              </SidebarMenuItem>
                            </motion.div>
                          ))}
                        </SidebarMenu>
                      </SidebarGroupContent>
                    </SidebarGroup>
                  </motion.div>

                  {/* TierSwitcher Component */}
                  <TierSwitcher />

                  {/* Platform Status Badge with animation */}
                  <motion.div 
                    className="px-2 mt-auto mb-2"
                    whileHover={{ scale: 1.02 }}
                    transition={{ duration: 0.18 }}
                  >
                    <div className="bg-gradient-to-r from-emerald-50 to-emerald-100 border border-emerald-200 rounded-xl p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckSquare className="w-4 h-4 text-emerald-600" />
                        <span className="text-sm font-medium text-emerald-800">Platform Complete</span>
                      </div>
                      <div className="text-xs text-emerald-600">
                        🎉 All 14 critical tasks implemented
                      </div>
                    </div>
                  </motion.div>
                </SidebarContent>

                <SidebarFooter className="border-t border-gray-200/50 dark:border-gray-800 p-4 space-y-2">
                  <motion.div 
                    className="flex items-center gap-3 pt-2 border-t border-gray-200/50 dark:border-gray-800"
                    whileHover={{ scale: 1.01 }}
                    transition={{ duration: 0.18 }}
                  >
                    <div className="w-9 h-9 bg-gradient-to-br from-gray-200 to-gray-300 dark:bg-gray-700 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-white text-sm truncate">SME User</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">sme.user@pikar.ai</p>
                    </div>
                    <Button variant="ghost" size="icon" onClick={handleLogout} className="text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800">
                        <LogOut className="w-4 h-4"/>
                    </Button>
                  </motion.div>
                </SidebarFooter>
              </Sidebar>
            </motion.div>
            </NavigationLandmark>

            <main className="flex-1 flex flex-col">
              {/* Enhanced mobile header */}
              <header className="bg-white/95 dark:bg-gray-950/95 backdrop-blur-sm border-b border-gray-200/50 dark:border-gray-800 px-6 py-3 md:hidden">
                <div className="flex items-center justify-between">
                    <motion.div 
                      className="flex items-center gap-2"
                      whileHover={{ scale: 1.02 }}
                      transition={{ duration: 0.18 }}
                    >
                        <div className="w-8 h-8 bg-gradient-to-br from-emerald-600 to-emerald-900 rounded-lg flex items-center justify-center">
                            <Brain className="w-5 h-5 text-white" />
                        </div>
                        <h1 className="text-lg font-bold text-gray-900 dark:text-white">PIKAR AI</h1>
                    </motion.div>
                    <div className="flex items-center gap-2">
                      <TrialStatusIndicator />
                      <SidebarTrigger className="hover:bg-gray-100 dark:hover:bg-gray-800 p-2 rounded-lg transition-colors duration-200" />
                    </div>
                </div>
              </header>

              {/* Enhanced main content with reveal animations */}
              <MainContent className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={location.pathname}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -12 }}
                    transition={{
                      duration: 0.32,
                      type: 'spring',
                      stiffness: 120,
                      damping: 18
                    }}
                  >
                    {children}
                  </motion.div>
                </AnimatePresence>
              </MainContent>
            </main>
          </div>

          {/* Enhanced Global Search Modal */}
          <AnimatePresence>
            {isSearchOpen && (
              <GlobalSearch 
                isOpen={isSearchOpen} 
                onClose={() => setIsSearchOpen(false)} 
              />
            )}
          </AnimatePresence>
        </SidebarProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

