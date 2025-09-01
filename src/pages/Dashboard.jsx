
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { createPageUrl } from '@/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { BusinessInitiative } from '@/api/entities';
import { Toaster } from 'sonner';
import { MotionSection, MotionCard, staggerContainer, listItemVariants, heroParallaxVariants } from '@/components/ui/motion-primitives';
import SuggestedInitiatives from '../components/dashboard/SuggestedInitiatives';
import RecentActivity from '../components/dashboard/RecentActivity';
import UserJourneyTester from '../components/dashboard/UserJourneyTester';
import {
    TrendingUp,
    Users,
    DollarSign,
    Activity,
    Plus,
    ArrowRight,
    Clock,
    CheckCircle,
    AlertCircle,
    BarChart3,
    Lightbulb,
    Target,
    Zap,
    Sparkles,
    Brain
} from 'lucide-react';

export default function Dashboard() {
    const [initiatives, setInitiatives] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadInitiatives();
    }, []);

    const loadInitiatives = async () => {
        setIsLoading(true);
        try {
            const fetchedInitiatives = await BusinessInitiative.list('-created_date', 10);
            setInitiatives(fetchedInitiatives);
        } catch (error) {
            console.error("Error loading initiatives:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'active': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
            case 'completed': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
            case 'on_hold': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'active': return <Clock className="w-4 h-4 text-emerald-600" />;
            case 'completed': return <CheckCircle className="w-4 h-4 text-emerald-600" />;
            case 'on_hold': return <AlertCircle className="w-4 h-4 text-yellow-600" />;
            default: return <Clock className="w-4 h-4 text-gray-600" />;
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8 bg-pikar-hero min-h-screen">
            <Toaster richColors />

            {/* Enhanced Header Section with premium branding */}
            <motion.div 
                className="flex items-center justify-between"
                variants={heroParallaxVariants}
                initial="rest"
                animate="scroll"
            >
                <MotionSection>
                    <div className="relative">
                        <motion.div
                            initial={{ opacity: 0, y: 24 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, type: 'spring', stiffness: 100 }}
                        >
                            {/* Swap gradient headline to neutral black for stronger contrast */}
                            <h1 className="text-4xl font-bold text-gray-900">
                                Welcome to PIKAR AI
                            </h1>
                            <p className="text-lg sm:text-xl text-gray-600 mt-2">
                                Your AI-powered business intelligence command center
                            </p>
                        </motion.div>
                        {/* soften the header glow to a subtle emerald tint */}
                        <motion.div
                            className="absolute -inset-4 bg-gradient-to-r from-emerald-50 to-white rounded-3xl -z-10 opacity-40"
                            animate={{ rotateX: [0, 1, 0], rotateY: [0, -1, 0] }}
                            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
                        />
                    </div>
                </MotionSection>
                
                <motion.div
                    whileHover={{ scale: 1.05, rotateY: 5 }}
                    whileTap={{ scale: 0.95 }}
                    transition={{ type: 'spring', stiffness: 200, damping: 15 }}
                >
                    <Link to={createPageUrl("CreateInitiative")}>
                        {/* Keep CTA strong emerald */}
                        <Button size="lg" className="bg-emerald-900 hover:bg-emerald-800 text-white border-0">
                            <Plus className="w-5 h-5 mr-2" />
                            New Initiative
                        </Button>
                    </Link>
                </motion.div>
            </motion.div>

            {/* Enhanced Key Metrics with emerald branding */}
            <motion.div 
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
                variants={staggerContainer}
                initial="hidden"
                animate="show"
            >
                {[
                    {
                        title: "Active Initiatives",
                        value: initiatives.filter(i => i.status === 'active').length,
                        change: "+2 from last week",
                        icon: Target
                    },
                    {
                        title: "Completion Rate", 
                        value: "87%",
                        change: "+5% improvement this month",
                        icon: CheckCircle
                    },
                    {
                        title: "AI Interactions",
                        value: "1,247", 
                        change: "This week across all agents",
                        icon: Brain
                    },
                    {
                        title: "Time Saved",
                        value: "156h",
                        change: "Through AI automation", 
                        icon: TrendingUp
                    }
                ].map((metric) => (
                    <motion.div
                        key={metric.title}
                        variants={listItemVariants}
                        whileHover={{ 
                          y: -6,
                          rotateX: -2,
                          rotateY: 2,
                          scale: 1.02
                        }}
                        transition={{ type: 'spring', stiffness: 150, damping: 15 }}
                    >
                        <Card hover3d={true} className="relative overflow-hidden bg-white border border-gray-200">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium text-gray-700">
                                    {metric.title}
                                </CardTitle>
                                <div className="p-2 rounded-xl bg-emerald-900">
                                    <metric.icon className="h-4 w-4 text-white" />
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold text-gray-900">
                                    {metric.value}
                                </div>
                                <p className="text-xs text-gray-500 mt-1">
                                    {metric.change}
                                </p>
                            </CardContent>
                        </Card>
                    </motion.div>
                ))}
            </motion.div>

            {/* Main Dashboard Content with consistent emerald branding */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column */}
                <motion.div 
                    className="lg:col-span-2 space-y-6"
                    variants={staggerContainer}
                    initial="hidden"
                    animate="show"
                >
                    {isLoading ? (
                        <Card className="border border-gray-200">
                            <CardContent className="flex justify-center py-8">
                                <motion.div 
                                    className="w-8 h-8 border-4 border-gray-200 border-t-emerald-900 rounded-full"
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                />
                            </CardContent>
                        </Card>
                    ) : initiatives.length === 0 ? (
                        <motion.div variants={listItemVariants} className="space-y-6">
                            {/* Callout stays but use white/emerald balance */}
                            <Card className="border-2 border-dashed border-gray-200 bg-white">
                                <CardHeader className="text-center">
                                    <motion.div
                                        animate={{ 
                                          rotateY: [0, 360],
                                          scale: [1, 1.1, 1]
                                        }}
                                        transition={{ 
                                          duration: 3,
                                          repeat: Infinity,
                                          ease: 'easeInOut'
                                        }}
                                    >
                                        <Lightbulb className="w-12 h-12 mx-auto text-emerald-900 mb-4" />
                                    </motion.div>
                                    <CardTitle className="text-gray-900">
                                        Ready to Transform Your Business?
                                    </CardTitle>
                                    <CardDescription className="text-gray-600">
                                        Start your first AI-powered business transformation initiative with our guided 6-phase journey.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="text-center">
                                    <motion.div
                                        whileHover={{ scale: 1.05, rotateX: 5 }}
                                        whileTap={{ scale: 0.95 }}
                                    >
                                        <Link to={createPageUrl("CreateInitiative")}>
                                            <Button size="lg" className="bg-emerald-900 hover:bg-emerald-800">
                                                <Target className="w-5 h-5 mr-2" />
                                                Start Your First Initiative
                                            </Button>
                                        </Link>
                                    </motion.div>
                                </CardContent>
                            </Card>

                            <SuggestedInitiatives />

                            {/* Quick Access with emerald theme */}
                            <Card className="border border-gray-200">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-gray-900">
                                        <Sparkles className="w-5 h-5 text-emerald-900" />
                                        Explore AI Agents
                                    </CardTitle>
                                    <CardDescription className="text-gray-600">
                                        Get familiar with our 10 specialized AI agents before starting your initiative.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <motion.div 
                                        className="grid grid-cols-2 gap-3"
                                        variants={staggerContainer}
                                        initial="hidden"
                                        animate="show"
                                    >
                                        {[
                                            { title: "Strategic Planning", icon: BarChart3, url: "StrategicPlanning" },
                                            { title: "Data Analysis", icon: BarChart3, url: "DataAnalysis" },
                                            { title: "Content Creation", icon: Zap, url: "ContentCreation" },
                                            { title: "View All Agents", icon: ArrowRight, url: "AgentDirectory" }
                                        ].map((agent) => (
                                            <motion.div key={agent.title} variants={listItemVariants}>
                                                <Link to={createPageUrl(agent.url)}>
                                                    <motion.div
                                                        whileHover={{ scale: 1.02, y: -2 }}
                                                        whileTap={{ scale: 0.98 }}
                                                    >
                                                        <Button variant="outline" className="w-full justify-start border-gray-300 hover:bg-gray-50 text-gray-900">
                                                            <agent.icon className="w-4 h-4 mr-2 text-emerald-900" />
                                                            {agent.title}
                                                        </Button>
                                                    </motion.div>
                                                </Link>
                                            </motion.div>
                                        ))}
                                    </motion.div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    ) : (
                        <motion.div variants={listItemVariants}>
                            <Card className="border border-gray-200">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-gray-900">
                                        <Target className="w-5 h-5 text-emerald-900" />
                                        Your Active Initiatives
                                    </CardTitle>
                                    <CardDescription className="text-gray-600">
                                        Track progress on your ongoing business transformation projects.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <motion.div 
                                        className="space-y-4"
                                        variants={staggerContainer}
                                        initial="hidden"
                                        animate="show"
                                    >
                                        <AnimatePresence>
                                            {initiatives.slice(0, 5).map((initiative) => (
                                                <motion.div 
                                                    key={initiative.id} 
                                                    variants={listItemVariants}
                                                    whileHover={{ 
                                                      scale: 1.01, 
                                                      x: 4,
                                                      boxShadow: '0 8px 24px rgba(0,0,0,0.08)'
                                                    }}
                                                    className="flex items-center justify-between p-4 border border-gray-200 rounded-2xl hover:bg-gray-50 transition-all duration-200"
                                                >
                                                    <div className="flex items-center gap-4">
                                                        <motion.div
                                                            whileHover={{ rotate: 360 }}
                                                            transition={{ duration: 0.3 }}
                                                        >
                                                            {getStatusIcon(initiative.status)}
                                                        </motion.div>
                                                        <div>
                                                            <h4 className="font-medium text-gray-900">{initiative.initiative_name}</h4>
                                                            <p className="text-sm text-gray-500">
                                                                Phase: {initiative.current_phase} • {initiative.category}
                                                            </p>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-3">
                                                        <Badge className={getStatusColor(initiative.status)}>
                                                            {initiative.status.replace(/_/g, ' ')}
                                                        </Badge>
                                                        <Link to={createPageUrl(`InitiativeDetails?id=${initiative.id}`)}>
                                                            <motion.div
                                                                whileHover={{ x: 4 }}
                                                                whileTap={{ scale: 0.9 }}
                                                            >
                                                                <Button variant="ghost" size="sm" className="hover:bg-gray-100 text-gray-900">
                                                                    <ArrowRight className="w-4 h-4" />
                                                                </Button>
                                                            </motion.div>
                                                        </Link>
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </AnimatePresence>

                                        {initiatives.length > 5 && (
                                            <motion.div 
                                                className="text-center pt-4"
                                                whileHover={{ scale: 1.05 }}
                                            >
                                                <Link to={createPageUrl("TransformationHub")}>
                                                    <Button variant="outline" className="border-gray-300 hover:bg-gray-50 text-gray-900">
                                                        View All Initiatives
                                                        <ArrowRight className="w-4 h-4 ml-2" />
                                                    </Button>
                                                </Link>
                                            </motion.div>
                                        )}
                                    </motion.div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    )}
                </motion.div>

                {/* Right Column with consistent branding */}
                <motion.div 
                    className="space-y-6"
                    variants={staggerContainer}
                    initial="hidden"
                    animate="show"
                >
                    <motion.div variants={listItemVariants}>
                        <RecentActivity />
                    </motion.div>
                    
                    <motion.div variants={listItemVariants}>
                        <UserJourneyTester />
                    </motion.div>

                    {/* Quick Links with emerald theme */}
                    <motion.div variants={listItemVariants}>
                        <Card className="border border-gray-200">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-gray-900">
                                    <Zap className="w-5 h-5 text-emerald-900" />
                                    Quick Actions
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {[
                                    { title: "Agent Orchestration", icon: Activity, url: "Orchestrate" },
                                    { title: "Performance Analytics", icon: BarChart3, url: "PerformanceAnalytics" },
                                    { title: "Resource Management", icon: DollarSign, url: "ResourceManagement" }
                                ].map((action) => (
                                    <motion.div
                                        key={action.title}
                                        whileHover={{ scale: 1.02, x: 4 }}
                                        whileTap={{ scale: 0.98 }}
                                    >
                                        <Link to={createPageUrl(action.url)}>
                                            <Button variant="outline" className="w-full justify-start border-gray-300 hover:bg-gray-50 text-gray-900">
                                                <action.icon className="w-4 h-4 mr-2 text-emerald-900" />
                                                {action.title}
                                            </Button>
                                        </Link>
                                    </motion.div>
                                ))}
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Platform Insights with emerald gradient */}
                    <motion.div variants={listItemVariants}>
                        <Card className="border border-gray-200 bg-white">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-gray-900">
                                    <TrendingUp className="w-5 h-5 text-emerald-900" />
                                    Platform Insights
                                </CardTitle>
                                <CardDescription className="text-gray-600">
                                    Real-time insights into agent performance and platform usage
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Most Used Agent</span>
                                    <Badge variant="outline" className="border-emerald-300 text-emerald-900 bg-emerald-50">Strategic Planning</Badge>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Average Session</span>
                                    <span className="text-sm font-medium text-gray-900">47 minutes</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Success Rate</span>
                                    <span className="text-sm font-medium text-emerald-800">94.2%</span>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                </motion.div>
            </div>
        </div>
    );
}
