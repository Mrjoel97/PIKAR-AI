import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Crown, Zap, Building, Rocket, ChevronDown } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { createPageUrl } from '@/utils';

const TIERS = [
    {
        id: 'solopreneur',
        name: 'Solopreneur',
        price: '$99/month',
        color: 'from-blue-600 to-blue-800',
        icon: Zap,
        dashboardPage: 'SolopreneurDashboard'
    },
    {
        id: 'startup',
        name: 'Startup',
        price: '$297/month',
        color: 'from-green-600 to-green-800',
        icon: Rocket,
        dashboardPage: 'StartupDashboard'
    },
    {
        id: 'sme',
        name: 'SME',
        price: '$597/month',
        color: 'from-purple-600 to-purple-800',
        icon: Building,
        dashboardPage: 'SmeDashboard'
    },
    {
        id: 'enterprise',
        name: 'Enterprise',
        price: 'Contact Sales',
        color: 'from-yellow-600 to-yellow-800',
        icon: Crown,
        dashboardPage: 'Dashboard'
    }
];

export default function TierSwitcher() {
    const [isOpen, setIsOpen] = useState(false);
    const location = useLocation();
    const navigate = useNavigate();
    
    // Get current tier from URL params or default to enterprise
    const searchParams = new URLSearchParams(location.search);
    const currentTierId = searchParams.get('tier') || 'enterprise';
    const currentTier = TIERS.find(tier => tier.id === currentTierId) || TIERS[3];

    const handleTierSwitch = (tier) => {
        setIsOpen(false);
        
        // Create the proper dashboard URL with tier parameter
        const dashboardUrl = createPageUrl(tier.dashboardPage);
        navigate(`${dashboardUrl}?tier=${tier.id}`);
    };

    const CurrentIcon = currentTier.icon;

    return (
        <div className="relative px-2 mb-4">
            <Card className="border border-emerald-200/50">
                <CardContent className="p-3">
                    <Button
                        variant="ghost"
                        onClick={() => setIsOpen(!isOpen)}
                        className="w-full justify-between hover:bg-emerald-50 text-left"
                    >
                        <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 bg-gradient-to-br ${currentTier.color} rounded-lg flex items-center justify-center`}>
                                <CurrentIcon className="w-4 h-4 text-white" />
                            </div>
                            <div className="flex flex-col items-start">
                                <span className="font-medium text-sm">{currentTier.name}</span>
                                <span className="text-xs text-gray-500">{currentTier.price}</span>
                            </div>
                        </div>
                        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    </Button>

                    <AnimatePresence>
                        {isOpen && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.2 }}
                                className="mt-3 border-t border-emerald-100 pt-3 space-y-2"
                            >
                                {TIERS.filter(tier => tier.id !== currentTierId).map((tier) => {
                                    const Icon = tier.icon;
                                    return (
                                        <motion.div
                                            key={tier.id}
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                        >
                                            <Button
                                                variant="ghost"
                                                onClick={() => handleTierSwitch(tier)}
                                                className="w-full justify-start hover:bg-emerald-50 p-3 h-auto"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-8 h-8 bg-gradient-to-br ${tier.color} rounded-lg flex items-center justify-center`}>
                                                        <Icon className="w-4 h-4 text-white" />
                                                    </div>
                                                    <div className="flex flex-col items-start">
                                                        <span className="font-medium text-sm">{tier.name}</span>
                                                        <span className="text-xs text-gray-500">{tier.price}</span>
                                                    </div>
                                                </div>
                                            </Button>
                                        </motion.div>
                                    );
                                })}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </CardContent>
            </Card>

            <div className="mt-2 px-1">
                <Badge variant="outline" className="w-full justify-center text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                    🧪 Tier Testing Mode
                </Badge>
            </div>
        </div>
    );
}