import React from 'react';
import { motion } from 'framer-motion';
import TierBadge from '../components/TierBadge';
import AgentQuickAccess from '../components/dashboard/AgentQuickAccess';
import TeamCollaboration from '../components/dashboard/TeamCollaboration';
import EnhancedAnalytics from '../components/dashboard/EnhancedAnalytics';
import ApiAccess from '../components/dashboard/ApiAccess';
import SMEBusinessSolutions from '../components/dashboard/SMEBusinessSolutions';
import SMEWorkflowTemplates from '../components/dashboard/SMEWorkflowTemplates';
import SMEPerformanceMetrics from '../components/dashboard/SMEPerformanceMetrics';
import { 
    BarChart3, Building, Users, Zap, Target, TrendingUp, 
    Award, Clock, DollarSign, Brain 
} from 'lucide-react';

const staggerContainer = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.1 }
    }
};

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
};

export default function SmeDashboard() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
            <div className="max-w-7xl mx-auto space-y-8">
                {/* SME Header */}
                <motion.header
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="relative overflow-hidden"
                >
                    <div className="bg-gradient-to-r from-purple-600 via-purple-700 to-purple-800 rounded-3xl p-8 text-white">
                        <div className="absolute inset-0 bg-black opacity-10 rounded-3xl"></div>
                        <div className="relative z-10">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-3">
                                    <div className="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm">
                                        <Building className="w-7 h-7 text-white" />
                                    </div>
                                    <div>
                                        <h1 className="text-3xl font-bold">SME Business Command Center</h1>
                                        <p className="text-purple-100 text-lg">Streamline operations with 8 specialized AI agents</p>
                                    </div>
                                </div>
                                <TierBadge tier="sme" showPrice={true} className="bg-white/20 text-white border-white/30" />
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                                    <div className="flex items-center gap-3">
                                        <Brain className="w-8 h-8 text-purple-200" />
                                        <div>
                                            <div className="text-2xl font-bold">8</div>
                                            <div className="text-sm text-purple-200">AI Agents Active</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                                    <div className="flex items-center gap-3">
                                        <Users className="w-8 h-8 text-purple-200" />
                                        <div>
                                            <div className="text-2xl font-bold">100</div>
                                            <div className="text-sm text-purple-200">Team Members</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                                    <div className="flex items-center gap-3">
                                        <Zap className="w-8 h-8 text-purple-200" />
                                        <div>
                                            <div className="text-2xl font-bold">15K</div>
                                            <div className="text-sm text-purple-200">API Calls/Month</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                                    <div className="flex items-center gap-3">
                                        <Award className="w-8 h-8 text-purple-200" />
                                        <div>
                                            <div className="text-2xl font-bold">25GB</div>
                                            <div className="text-sm text-purple-200">Storage Available</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.header>

                {/* Main Grid Layout */}
                <motion.div 
                    className="grid grid-cols-1 lg:grid-cols-3 gap-6"
                    variants={staggerContainer}
                    initial="hidden"
                    animate="show"
                >
                    {/* Left Column */}
                    <div className="lg:col-span-2 space-y-6">
                        <motion.div variants={itemVariants}>
                            <SMEBusinessSolutions />
                        </motion.div>
                        <motion.div variants={itemVariants}>
                            <EnhancedAnalytics />
                        </motion.div>
                    </div>

                    {/* Right Column */}
                    <div className="space-y-6">
                        <motion.div variants={itemVariants}>
                            <AgentQuickAccess tier="sme" />
                        </motion.div>
                        <motion.div variants={itemVariants}>
                            <TeamCollaboration />
                        </motion.div>
                        <motion.div variants={itemVariants}>
                            <ApiAccess />
                        </motion.div>
                    </div>
                </motion.div>

                {/* Full Width Sections */}
                <motion.div 
                    className="space-y-8"
                    variants={staggerContainer}
                    initial="hidden"
                    animate="show"
                >
                    <motion.div variants={itemVariants}>
                        <SMEPerformanceMetrics />
                    </motion.div>
                    <motion.div variants={itemVariants}>
                        <SMEWorkflowTemplates />
                    </motion.div>
                </motion.div>
            </div>
        </div>
    );
}