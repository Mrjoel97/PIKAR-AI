import Layout from "./Layout.jsx";
import Landing from "./Landing";
import AdminLayout from './admin/AdminLayout';
import AdminProtectedRoute from '@/components/admin/AdminProtectedRoute';
import AdminDashboard from './admin/AdminDashboard';
import AdminUsers from './admin/AdminUsers';
import AdminAudit from './admin/AdminAudit';
import AdminFlags from './admin/AdminFlags';
import AdminSettings from './admin/AdminSettings';
import AdminBilling from './admin/AdminBilling';
import Agents from './admin/Agents';
import Pricing from './Pricing';
import Billing from './Billing';
import LoginForm from "@/components/auth/LoginForm";
import RegisterForm from "@/components/auth/RegisterForm";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

import Dashboard from "./Dashboard";

import ContentCreation from "./ContentCreation";

import StrategicPlanning from "./StrategicPlanning";

import CustomerSupport from "./CustomerSupport";

import SalesIntelligence from "./SalesIntelligence";

import DataAnalysis from "./DataAnalysis";

import MarketingAutomation from "./MarketingAutomation";

import FinancialAnalysis from "./FinancialAnalysis";

import OperationsOptimization from "./OperationsOptimization";

import CustomAgents from "./CustomAgents";

import CreateAgent from "./CreateAgent";

import CustomAgentChat from "./CustomAgentChat";

import HRRecruitment from "./HRRecruitment";

import ComplianceRisk from "./ComplianceRisk";

import EditAgent from "./EditAgent";

import Settings from "./Settings";

import Orchestrate from "./Orchestrate";

import AuditTrail from "./AuditTrail";

import TransformationHub from "./TransformationHub";

import CreateInitiative from "./CreateInitiative";

import InitiativeDetails from "./InitiativeDetails";

import PerformanceAnalytics from "./PerformanceAnalytics";

import ResourceManagement from "./ResourceManagement";

import WorkflowDetails from "./WorkflowDetails";

import ComplianceAudit from "./ComplianceAudit";

import QualityManagement from "./QualityManagement";

import CollaborationHub from "./CollaborationHub";

import ImplementationStatus from "./ImplementationStatus";

import Integrations from "./Integrations";

import Reporting from "./Reporting";

import PlatformCompletionStatus from "./PlatformCompletionStatus";

import PlatformTesting from "./PlatformTesting";

import AppBuilderAssistant from "./AppBuilderAssistant";

import ComplianceAnalysisReport from "./ComplianceAnalysisReport";

import DatabaseMigrations from "./DatabaseMigrations";

import LearningHub from "./LearningHub";

import LearningPath from "./LearningPath";

import KnowledgeHub from "./KnowledgeHub";

import AgentDirectory from "./AgentDirectory";

import CreateWorkflow from "./CreateWorkflow";

import MarketingSuite from "./MarketingSuite";

import SocialMediaMarketing from "./SocialMediaMarketing";

import SocialCampaigns from "./SocialCampaigns";

import SocialCampaignDetails from "./SocialCampaignDetails";

import SocialAPIReadiness from "./SocialAPIReadiness";

import PrivacyPolicy from "./PrivacyPolicy";

import Terms from "./Terms";

import DataDeletion from "./DataDeletion";

import MarketingSuiteTests from "./MarketingSuiteTests";
import MarketingAnalytics from "./MarketingAnalytics";

import MetaAdsManager from "./MetaAdsManager";

import LinkedInAdsManager from "./LinkedInAdsManager";

import TwitterAdsManager from "./TwitterAdsManager";

import YouTubeManager from "./YouTubeManager";

import TikTokManager from "./TikTokManager";

import SocialPlatformTester from "./SocialPlatformTester";

import SolopreneurDashboard from "./SolopreneurDashboard";

import SmeDashboard from "./SmeDashboard";

import StartupDashboard from "./StartupDashboard";

import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';

const PAGES = {
    
    Dashboard: Dashboard,
    
    ContentCreation: ContentCreation,
    
    StrategicPlanning: StrategicPlanning,
    
    CustomerSupport: CustomerSupport,
    
    SalesIntelligence: SalesIntelligence,
    
    DataAnalysis: DataAnalysis,
    
    MarketingAutomation: MarketingAutomation,
    
    FinancialAnalysis: FinancialAnalysis,
    
    OperationsOptimization: OperationsOptimization,
    
    CustomAgents: CustomAgents,
    
    CreateAgent: CreateAgent,
    
    CustomAgentChat: CustomAgentChat,
    
    HRRecruitment: HRRecruitment,
    
    ComplianceRisk: ComplianceRisk,
    
    EditAgent: EditAgent,
    
    Settings: Settings,
    
    Orchestrate: Orchestrate,
    
    AuditTrail: AuditTrail,
    
    TransformationHub: TransformationHub,
    
    CreateInitiative: CreateInitiative,
    
    InitiativeDetails: InitiativeDetails,
    
    PerformanceAnalytics: PerformanceAnalytics,
    
    ResourceManagement: ResourceManagement,
    
    WorkflowDetails: WorkflowDetails,
    
    ComplianceAudit: ComplianceAudit,
    
    QualityManagement: QualityManagement,
    
    CollaborationHub: CollaborationHub,
    
    ImplementationStatus: ImplementationStatus,
    
    Integrations: Integrations,
    
    Reporting: Reporting,
    
    PlatformCompletionStatus: PlatformCompletionStatus,
    
    PlatformTesting: PlatformTesting,
    
    AppBuilderAssistant: AppBuilderAssistant,
    
    ComplianceAnalysisReport: ComplianceAnalysisReport,
    
    DatabaseMigrations: DatabaseMigrations,
    
    LearningHub: LearningHub,
    
    LearningPath: LearningPath,
    
    KnowledgeHub: KnowledgeHub,
    
    AgentDirectory: AgentDirectory,
    
    CreateWorkflow: CreateWorkflow,
    
    MarketingSuite: MarketingSuite,
    
    SocialMediaMarketing: SocialMediaMarketing,
    
    SocialCampaigns: SocialCampaigns,
    
    SocialCampaignDetails: SocialCampaignDetails,
    
    SocialAPIReadiness: SocialAPIReadiness,
    
    PrivacyPolicy: PrivacyPolicy,
    
    Terms: Terms,
    
    DataDeletion: DataDeletion,
    
    MarketingSuiteTests: MarketingSuiteTests,
    
    MetaAdsManager: MetaAdsManager,
    
    LinkedInAdsManager: LinkedInAdsManager,
    
    TwitterAdsManager: TwitterAdsManager,
    
    YouTubeManager: YouTubeManager,
    
    TikTokManager: TikTokManager,
    
    SocialPlatformTester: SocialPlatformTester,
    
    SolopreneurDashboard: SolopreneurDashboard,
    
    SmeDashboard: SmeDashboard,
    
    StartupDashboard: StartupDashboard,
    
}

function _getCurrentPage(url) {
    if (url.endsWith('/')) {
        url = url.slice(0, -1);
    }
    let urlLastPart = url.split('/').pop();
    if (urlLastPart.includes('?')) {
        urlLastPart = urlLastPart.split('?')[0];
    }

    const pageName = Object.keys(PAGES).find(page => page.toLowerCase() === urlLastPart.toLowerCase());
    return pageName || Object.keys(PAGES)[0];
}

// Create a wrapper component that uses useLocation inside the Router context
function PagesContent() {
    const location = useLocation();
    const currentPage = _getCurrentPage(location.pathname);

    return (
        <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginForm />} />

            {/* Protected routes */}
            <Route path="/*" element={
                <ProtectedRoute>
                    <Layout currentPageName={currentPage}>
                        <Routes>
                            <Route path="/dashboard" element={<Dashboard />} />
                            <Route path="/Dashboard" element={<Dashboard />} />
                
                <Route path="/ContentCreation" element={<ContentCreation />} />
                
                <Route path="/StrategicPlanning" element={<StrategicPlanning />} />
                
                <Route path="/CustomerSupport" element={<CustomerSupport />} />
                
                <Route path="/SalesIntelligence" element={<SalesIntelligence />} />
                
                <Route path="/DataAnalysis" element={<DataAnalysis />} />
                
                <Route path="/MarketingAutomation" element={<MarketingAutomation />} />
                
                <Route path="/FinancialAnalysis" element={<FinancialAnalysis />} />
                
                <Route path="/OperationsOptimization" element={<OperationsOptimization />} />
                
                <Route path="/CustomAgents" element={<CustomAgents />} />
                
                <Route path="/CreateAgent" element={<CreateAgent />} />
                
                <Route path="/CustomAgentChat" element={<CustomAgentChat />} />
                
                <Route path="/HRRecruitment" element={<HRRecruitment />} />
                
                <Route path="/ComplianceRisk" element={<ComplianceRisk />} />
                
                <Route path="/EditAgent" element={<EditAgent />} />
                
                <Route path="/Settings" element={<Settings />} />
                
                <Route path="/Orchestrate" element={<Orchestrate />} />
                
                <Route path="/AuditTrail" element={<AuditTrail />} />
                
                <Route path="/TransformationHub" element={<TransformationHub />} />
                
                <Route path="/CreateInitiative" element={<CreateInitiative />} />
                
                <Route path="/InitiativeDetails" element={<InitiativeDetails />} />
                
                <Route path="/PerformanceAnalytics" element={<PerformanceAnalytics />} />
                
                <Route path="/ResourceManagement" element={<ResourceManagement />} />
                
                <Route path="/WorkflowDetails" element={<WorkflowDetails />} />
                
                <Route path="/ComplianceAudit" element={<ComplianceAudit />} />
                
                <Route path="/QualityManagement" element={<QualityManagement />} />
                
                <Route path="/CollaborationHub" element={<CollaborationHub />} />
                
                <Route path="/ImplementationStatus" element={<ImplementationStatus />} />
                
                <Route path="/Integrations" element={<Integrations />} />
                
                <Route path="/Reporting" element={<Reporting />} />
                
                <Route path="/PlatformCompletionStatus" element={<PlatformCompletionStatus />} />
                
                <Route path="/PlatformTesting" element={<PlatformTesting />} />
                
                <Route path="/AppBuilderAssistant" element={<AppBuilderAssistant />} />
                
                <Route path="/ComplianceAnalysisReport" element={<ComplianceAnalysisReport />} />
                
                <Route path="/DatabaseMigrations" element={<DatabaseMigrations />} />
                
                <Route path="/LearningHub" element={<LearningHub />} />
                
                <Route path="/LearningPath" element={<LearningPath />} />
                
                <Route path="/KnowledgeHub" element={<KnowledgeHub />} />
                
                <Route path="/AgentDirectory" element={<AgentDirectory />} />
                
                <Route path="/CreateWorkflow" element={<CreateWorkflow />} />
                
                <Route path="/MarketingSuite" element={<MarketingSuite />} />
                
                <Route path="/SocialMediaMarketing" element={<SocialMediaMarketing />} />
                
                <Route path="/SocialCampaigns" element={<SocialCampaigns />} />
                
                <Route path="/SocialCampaignDetails" element={<SocialCampaignDetails />} />
                
                <Route path="/SocialAPIReadiness" element={<SocialAPIReadiness />} />
                
                <Route path="/PrivacyPolicy" element={<PrivacyPolicy />} />
                
                <Route path="/Terms" element={<Terms />} />
                
                <Route path="/DataDeletion" element={<DataDeletion />} />
                
                <Route path="/MarketingSuiteTests" element={<MarketingSuiteTests />} />
                <Route path="/MarketingAnalytics" element={<MarketingAnalytics />} />
                
                <Route path="/MetaAdsManager" element={<MetaAdsManager />} />
                
                <Route path="/LinkedInAdsManager" element={<LinkedInAdsManager />} />
                
                <Route path="/TwitterAdsManager" element={<TwitterAdsManager />} />
                
                <Route path="/YouTubeManager" element={<YouTubeManager />} />
                
                <Route path="/TikTokManager" element={<TikTokManager />} />
                
                <Route path="/SocialPlatformTester" element={<SocialPlatformTester />} />
                
                <Route path="/SolopreneurDashboard" element={<SolopreneurDashboard />} />
                
                <Route path="/SmeDashboard" element={<SmeDashboard />} />
                
                            <Route path="/StartupDashboard" element={<StartupDashboard />} />
                        </Routes>
                    </Layout>
                </ProtectedRoute>
            } />
        </Routes>
    );
}

export default function Pages() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<LoginForm />} />
                <Route path="/auth" element={<LoginForm />} />
                <Route path="/register" element={<RegisterForm />} />
                <Route path="/pricing" element={<Pricing />} />
                <Route path="/billing" element={<Billing />} />
                <Route path="/admin" element={<AdminProtectedRoute><AdminLayout /></AdminProtectedRoute>}>
                  <Route index element={<AdminDashboard />} />
                  <Route path="users" element={<AdminUsers />} />
                  <Route path="audit" element={<AdminAudit />} />
                  <Route path="flags" element={<AdminFlags />} />
                  <Route path="billing" element={<AdminBilling />} />
                  <Route path="agents" element={<Agents />} />
                  <Route path="settings" element={<AdminSettings />} />
                </Route>
                <Route path="/*" element={<PagesContent />} />
            </Routes>
        </Router>
    );
}