import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { UsageAnalytics } from '@/api/entities';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { 
    Lightbulb,
    PenSquare,
    Users,
    BarChart,
    Sparkles,
    DollarSign,
    UserCheck,
    ShieldCheck,
    SlidersHorizontal,
    Search,
    TrendingUp,
    ArrowRight,
    Target
} from 'lucide-react';
import { motion } from 'framer-motion';
import TierBadge from '@/components/TierBadge';

const agentData = [
    {
        id: 'strategic-planning',
        name: 'Strategic Planning Agent',
        description: 'Market analysis, competitive intelligence, and strategic framework development',
        icon: Lightbulb,
        capabilities: [
            'SWOT & PESTEL Analysis',
            'Competitor Intelligence',
            'Market Research',
            'Strategic Frameworks',
            'Business Model Design'
        ],
        pageUrl: createPageUrl('StrategicPlanning'),
        tier: 'solopreneur',
        avgResponseTime: '2.3s',
        successRate: 92,
        popularityScore: 95
    },
    {
        id: 'content-creation',
        name: 'Content Creation Agent',
        description: 'Multi-format content generation with SEO optimization and brand consistency',
        icon: PenSquare,
        capabilities: [
            'Blog Posts & Articles',
            'Social Media Content',
            'Marketing Copy',
            'Video Scripts',
            'SEO Optimization'
        ],
        pageUrl: createPageUrl('ContentCreation'),
        tier: 'startup',
        avgResponseTime: '1.8s',
        successRate: 89,
        popularityScore: 88
    },
    {
        id: 'customer-support',
        name: 'Customer Support Agent',
        description: '24/7 automated support with intelligent routing and sentiment analysis',
        icon: Users,
        capabilities: [
            'Instant Query Resolution',
            'Knowledge Base Integration',
            'Sentiment Analysis',
            'Escalation Management',
            'Multi-language Support'
        ],
        pageUrl: createPageUrl('CustomerSupport'),
        tier: 'solopreneur',
        avgResponseTime: '1.2s',
        successRate: 94,
        popularityScore: 91
    },
    {
        id: 'sales-intelligence',
        name: 'Sales Intelligence Agent',
        description: 'Lead scoring, pipeline optimization, and sales strategy development',
        icon: Target,
        capabilities: [
            'Lead Scoring & Qualification',
            'Pipeline Analysis',
            'Sales Forecasting',
            'Competitive Intelligence',
            'Deal Strategy'
        ],
        pageUrl: createPageUrl('SalesIntelligence'),
        tier: 'startup',
        avgResponseTime: '2.1s',
        successRate: 87,
        popularityScore: 85
    },
    {
        id: 'data-analysis',
        name: 'Data Analysis Agent',
        description: 'Predictive analytics, pattern recognition, and data-driven insights',
        icon: BarChart,
        capabilities: [
            'Predictive Modeling',
            'Pattern Recognition',
            'Statistical Analysis',
            'Data Visualization',
            'Trend Forecasting'
        ],
        pageUrl: createPageUrl('DataAnalysis'),
        tier: 'solopreneur',
        avgResponseTime: '3.2s',
        successRate: 91,
        popularityScore: 93
    },
    {
        id: 'marketing-automation',
        name: 'Marketing Automation Agent',
        description: 'Campaign orchestration, audience segmentation, and performance optimization',
        icon: Sparkles,
        capabilities: [
            'Campaign Planning',
            'Audience Segmentation',
            'A/B Testing',
            'Performance Tracking',
            'Multi-channel Orchestration'
        ],
        pageUrl: createPageUrl('MarketingAutomation'),
        tier: 'sme',
        avgResponseTime: '2.5s',
        successRate: 88,
        popularityScore: 82
    },
    {
        id: 'financial-analysis',
        name: 'Financial Analysis Agent',
        description: 'Financial forecasting, risk assessment, and investment analysis',
        icon: DollarSign,
        capabilities: [
            'Financial Forecasting',
            'Risk Assessment',
            'ROI Analysis',
            'Cash Flow Modeling',
            'Investment Evaluation'
        ],
        pageUrl: createPageUrl('FinancialAnalysis'),
        tier: 'sme',
        avgResponseTime: '2.8s',
        successRate: 93,
        popularityScore: 89
    },
    {
        id: 'hr-recruitment',
        name: 'HR & Recruitment Agent',
        description: 'Resume screening, candidate matching, and talent management',
        icon: UserCheck,
        capabilities: [
            'Resume Screening',
            'Candidate Matching',
            'Interview Scheduling',
            'Skills Assessment',
            'Performance Tracking'
        ],
        pageUrl: createPageUrl('HRRecruitment'),
        tier: 'enterprise',
        avgResponseTime: '2.0s',
        successRate: 90,
        popularityScore: 78
    },
    {
        id: 'compliance-risk',
        name: 'Compliance & Risk Agent',
        description: 'Regulatory monitoring, risk assessment, and compliance management',
        icon: ShieldCheck,
        capabilities: [
            'Regulatory Monitoring',
            'Risk Assessment',
            'Compliance Auditing',
            'Policy Development',
            'Incident Management'
        ],
        pageUrl: createPageUrl('ComplianceRisk'),
        tier: 'enterprise',
        avgResponseTime: '2.7s',
        successRate: 95,
        popularityScore: 86
    },
    {
        id: 'operations-optimization',
        name: 'Operations Optimization Agent',
        description: 'Process analysis, efficiency optimization, and workflow automation',
        icon: SlidersHorizontal,
        capabilities: [
            'Process Mapping',
            'Efficiency Analysis',
            'Workflow Automation',
            'Bottleneck Identification',
            'Performance Optimization'
        ],
        pageUrl: createPageUrl('OperationsOptimization'),
        tier: 'sme',
        avgResponseTime: '2.4s',
        successRate: 92,
        popularityScore: 84
    }
];

const pageVariants = {
    hidden: { opacity: 0, y: 24 },
    show: { 
        opacity: 1, 
        y: 0,
        transition: { type: 'spring', stiffness: 100, damping: 20, staggerChildren: 0.1 }
    }
};

const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { 
        opacity: 1, 
        y: 0,
        transition: { type: 'spring', stiffness: 120, damping: 18 }
    }
};

export default function AgentDirectory() {
    const [searchTerm, setSearchTerm] = useState('');
    const [filterTier, setFilterTier] = useState('all');
    const [sortBy, setSortBy] = useState('popularity');
    const [usageData, setUsageData] = useState({});
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            try {
                // Defensive check: Ensure the entity module has loaded correctly.
                if (typeof UsageAnalytics?.list !== 'function') {
                    console.warn("UsageAnalytics entity not available. Falling back to mock data.");
                    throw new Error("Entity not found");
                }
                
                const analytics = await UsageAnalytics.list('-created_date', 100);
                const usageMap = {};
                analytics.forEach(record => {
                    if (!usageMap[record.agent_name]) {
                        usageMap[record.agent_name] = { totalUsage: 0, avgSatisfaction: 0, count: 0 };
                    }
                    usageMap[record.agent_name].totalUsage += 1;
                    if (record.user_satisfaction) {
                        usageMap[record.agent_name].avgSatisfaction += record.user_satisfaction;
                        usageMap[record.agent_name].count += 1;
                    }
                });
                
                Object.keys(usageMap).forEach(agent => {
                    if (usageMap[agent].count > 0) {
                        usageMap[agent].avgSatisfaction = usageMap[agent].avgSatisfaction / usageMap[agent].count;
                    }
                });
                
                setUsageData(usageMap);
            } catch (error) {
                console.error("Could not load usage data, using mock data:", error);
                // Fallback to mock data on any error
                setUsageData({
                    'Strategic Planning Agent': { totalUsage: 42, avgSatisfaction: 4.2 },
                    'Content Creation Agent': { totalUsage: 38, avgSatisfaction: 4.5 },
                    'Data Analysis Agent': { totalUsage: 35, avgSatisfaction: 4.1 }
                });
            } finally {
                setIsLoading(false);
            }
        };

        loadData();
    }, []);

    const filteredAgents = agentData
        .filter(agent => {
            const matchesSearch = agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                                agent.description.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesTier = filterTier === 'all' || agent.tier === filterTier;
            return matchesSearch && matchesTier;
        })
        .sort((a, b) => {
            switch (sortBy) {
                case 'popularity':
                    return b.popularityScore - a.popularityScore;
                case 'performance':
                    return b.successRate - a.successRate;
                case 'speed':
                    return parseFloat(a.avgResponseTime) - parseFloat(b.avgResponseTime);
                case 'alphabetical':
                    return a.name.localeCompare(b.name);
                default:
                    return 0;
            }
        });

    return (
        <div className="max-w-7xl mx-auto space-y-8 bg-pikar-hero min-h-screen p-6">
            {/* Header */}
            <motion.div 
                className="text-center space-y-4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
            >
                <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-900 to-emerald-700 bg-clip-text text-transparent">
                    AI Agent Directory
                </h1>
                <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                    Discover our 10 specialized AI agents designed to transform every aspect of your business operations.
                </p>
            </motion.div>

            {/* Filters and Search */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.5 }}
            >
                <Card className="border-emerald-100 bg-white shadow-soft">
                    <CardContent className="p-6">
                        <div className="flex flex-col sm:flex-row gap-4 items-center">
                            <div className="relative flex-1 w-full">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-emerald-400 w-4 h-4" />
                                <Input
                                    placeholder="Search agents by name or capability..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10 border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                />
                            </div>
                            <div className="flex gap-2 w-full sm:w-auto">
                                <select 
                                    value={filterTier}
                                    onChange={(e) => setFilterTier(e.target.value)}
                                    className="px-3 py-2 border border-emerald-200 rounded-xl bg-white text-emerald-900 focus:border-emerald-900 focus:outline-none w-full sm:w-auto"
                                >
                                    <option value="all">All Tiers</option>
                                    <option value="solopreneur">Solopreneur</option>
                                    <option value="startup">Startup</option>
                                    <option value="sme">SME</option>
                                    <option value="enterprise">Enterprise</option>
                                </select>
                                <select 
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value)}
                                    className="px-3 py-2 border border-emerald-200 rounded-xl bg-white text-emerald-900 focus:border-emerald-900 focus:outline-none w-full sm:w-auto"
                                >
                                    <option value="popularity">Most Popular</option>
                                    <option value="performance">Best Performance</option>
                                    <option value="speed">Fastest Response</option>
                                    <option value="alphabetical">A-Z</option>
                                </select>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            {/* Agent Grid */}
            <motion.div 
                className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
                initial="hidden"
                animate="show"
                variants={pageVariants}
            >
                {filteredAgents.map((agent, index) => {
                    const Icon = agent.icon;
                    const agentUsage = usageData[agent.name] || {};
                    
                    return (
                        <motion.div
                            key={agent.id}
                            variants={cardVariants}
                            whileHover={{ 
                                y: -6, 
                                rotateX: -2, 
                                rotateY: 2,
                                scale: 1.02,
                                boxShadow: '0 12px 40px rgba(6,95,70,0.15)',
                                transition: { type: 'spring', stiffness: 150, damping: 15 }
                            }}
                        >
                            <Card className="shadow-soft border-l-4 border-l-emerald-200 hover:border-l-emerald-500 bg-white transition-all duration-300">
                                <CardHeader className="pb-4">
                                    <div className="flex items-start justify-between">
                                        <div className="p-3 bg-emerald-50 rounded-xl">
                                            <Icon className="w-6 h-6 text-emerald-600" />
                                        </div>
                                        <TierBadge tier={agent.tier} />
                                    </div>
                                    <CardTitle className="text-lg text-emerald-900">{agent.name}</CardTitle>
                                    <CardDescription className="text-sm">
                                        {agent.description}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-3 gap-2 text-center">
                                        <div>
                                            <div className="text-sm font-medium text-gray-500">Success Rate</div>
                                            <div className="text-lg font-bold text-emerald-900">{agent.successRate}%</div>
                                        </div>
                                        <div>
                                            <div className="text-sm font-medium text-gray-500">Response</div>
                                            <div className="text-lg font-bold text-emerald-900">{agent.avgResponseTime}</div>
                                        </div>
                                        <div>
                                            <div className="text-sm font-medium text-gray-500">Usage</div>
                                            {isLoading ? (
                                                <div className="h-7 w-10 mx-auto bg-gray-200 rounded-md animate-pulse mt-1"></div>
                                            ) : (
                                                <div className="text-lg font-bold text-emerald-900">{agentUsage.totalUsage || 0}</div>
                                            )}
                                        </div>
                                    </div>

                                    <div>
                                        <h4 className="font-medium text-sm mb-2 text-emerald-900">Key Capabilities</h4>
                                        <div className="flex flex-wrap gap-1">
                                            {agent.capabilities.slice(0, 3).map((capability, idx) => (
                                                <Badge key={idx} variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                                                    {capability}
                                                </Badge>
                                            ))}
                                            {agent.capabilities.length > 3 && (
                                                <Badge variant="outline" className="text-xs text-emerald-600 border-emerald-200">
                                                    +{agent.capabilities.length - 3} more
                                                </Badge>
                                            )}
                                        </div>
                                    </div>

                                    <Link to={`${agent.pageUrl}?tier=${filterTier !== 'all' ? filterTier : agent.tier}`} className="block">
                                        <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                                            <Button className="w-full bg-gradient-to-r from-emerald-800 to-emerald-900 hover:from-emerald-900 hover:to-emerald-800 text-white rounded-xl">
                                                Launch Agent
                                                <ArrowRight className="w-4 h-4 ml-2" />
                                            </Button>
                                        </motion.div>
                                    </Link>
                                </CardContent>
                            </Card>
                        </motion.div>
                    );
                })}
            </motion.div>

            {/* Platform Statistics */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.5 }}
            >
                <Card className="border-emerald-100 bg-white shadow-soft">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-emerald-900">
                            <TrendingUp className="w-5 h-5 text-emerald-600" />
                            Platform Performance Overview
                        </CardTitle>
                        <CardDescription>
                            Real-time insights into agent performance and platform usage
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                            <div className="text-center">
                                <div className="text-3xl font-bold text-emerald-600">10</div>
                                <div className="text-sm text-gray-500">Specialized Agents</div>
                            </div>
                            <div className="text-center">
                                <div className="text-3xl font-bold text-emerald-600">99.97%</div>
                                <div className="text-sm text-gray-500">System Uptime</div>
                            </div>
                            <div className="text-center">
                                <div className="text-3xl font-bold text-emerald-600">2.3s</div>
                                <div className="text-sm text-gray-500">Avg Response Time</div>
                            </div>
                            <div className="text-center">
                                <div className="text-3xl font-bold text-emerald-600">91%</div>
                                <div className="text-sm text-gray-500">Average Success Rate</div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            {/* Getting Started */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.5 }}
            >
                <Card className="border-2 border-dashed border-emerald-200 bg-gradient-to-br from-emerald-50/50 to-emerald-100/30 shadow-soft">
                    <CardHeader className="text-center">
                        <Sparkles className="w-8 h-8 mx-auto text-emerald-600 mb-2" />
                        <CardTitle className="text-emerald-900">
                            Ready to Transform Your Business?
                        </CardTitle>
                        <CardDescription className="text-emerald-700">
                            Start with our guided 6-phase transformation journey or explore individual agents.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center space-y-4">
                        <div className="flex flex-col sm:flex-row gap-3 justify-center">
                            <Link to={createPageUrl('CreateInitiative')}>
                                <Button size="lg" className="bg-emerald-900 hover:bg-emerald-800">
                                    <Target className="w-5 h-5 mr-2" />
                                    Start Transformation Journey
                                </Button>
                            </Link>
                            <Link to={createPageUrl('StrategicPlanning')}>
                                <Button size="lg" variant="outline" className="border-emerald-600 text-emerald-600 hover:bg-emerald-50">
                                    <Lightbulb className="w-5 h-5 mr-2" />
                                    Try Strategic Planning
                                </Button>
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </motion.div>
        </div>
    );
}