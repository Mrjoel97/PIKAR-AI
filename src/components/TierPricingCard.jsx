import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, Crown, Zap, Building, Rocket, Mail } from 'lucide-react';
import { motion } from 'framer-motion';

const TIER_CONFIGS = {
    solopreneur: {
        name: 'Solopreneur',
        price: '$99',
        period: '/month',
        description: 'Perfect for individual entrepreneurs starting their AI transformation journey',
        icon: Zap,
        color: 'from-blue-600 to-blue-800',
        agents: 3,
        features: [
            'Strategic Planning Agent',
            'Customer Support Agent', 
            'Data Analysis Agent',
            '1,000 API calls/month',
            '1GB storage',
            '1 user account',
            'Email support',
            'Basic analytics dashboard'
        ],
        limitations: [
            'No team collaboration',
            'No custom workflows',
            'No advanced integrations'
        ]
    },
    startup: {
        name: 'Startup',
        price: '$297',
        period: '/month',
        description: 'Ideal for growing teams ready to scale their operations',
        icon: Rocket,
        color: 'from-green-600 to-green-800',
        agents: 5,
        popular: true,
        features: [
            'All Solopreneur features',
            'Sales Intelligence Agent',
            'Content Creation Agent',
            '5,000 API calls/month',
            '5GB storage',
            '10 user accounts',
            'Team collaboration tools',
            'Priority support',
            'Advanced analytics',
            'API access'
        ]
    },
    sme: {
        name: 'SME',
        price: '$597',
        period: '/month',
        description: 'Comprehensive solution for established businesses',
        icon: Building,
        color: 'from-purple-600 to-purple-800',
        agents: 8,
        features: [
            'All Startup features',
            'Marketing Automation Agent',
            'Financial Analysis Agent',
            'Operations Optimization Agent',
            '15,000 API calls/month',
            '25GB storage',
            '100 user accounts',
            'Custom workflows',
            'Advanced reporting',
            'Dedicated support'
        ]
    },
    enterprise: {
        name: 'Enterprise',
        price: 'Custom',
        period: 'Pricing',
        description: 'Ultimate solution for large organizations with unlimited potential',
        icon: Crown,
        color: 'from-yellow-600 to-yellow-800',
        agents: 10,
        contactSales: true,
        features: [
            'All SME features',
            'HR & Recruitment Agent',
            'Compliance & Risk Agent',
            'Unlimited API calls',
            'Unlimited storage',
            'Unlimited users',
            'White-label solution',
            'Custom branding',
            'On-premise deployment',
            'Custom integrations',
            'Dedicated success manager'
        ]
    }
};

export default function TierPricingCard({ tier, currentTier, onUpgrade, className }) {
    const config = TIER_CONFIGS[tier];
    const Icon = config.icon;
    const isCurrentTier = currentTier === tier;
    const isUpgrade = ['solopreneur', 'startup', 'sme', 'enterprise'].indexOf(tier) > 
                     ['solopreneur', 'startup', 'sme', 'enterprise'].indexOf(currentTier);

    return (
        <motion.div
            whileHover={{ y: isCurrentTier ? 0 : -8, scale: isCurrentTier ? 1 : 1.02 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={className}
        >
            <Card className={`relative h-full ${isCurrentTier ? 'ring-2 ring-emerald-500 ring-offset-2' : 'hover:shadow-xl'} transition-all duration-300`}>
                {config.popular && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                        <Badge className="bg-emerald-600 text-white px-3 py-1">Most Popular</Badge>
                    </div>
                )}
                
                <CardHeader className="text-center pb-4">
                    <div className={`w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br ${config.color} flex items-center justify-center mb-4`}>
                        <Icon className="w-8 h-8 text-white" />
                    </div>
                    
                    <CardTitle className="text-2xl font-bold text-gray-900">
                        {config.name}
                    </CardTitle>
                    
                    <div className="flex items-baseline justify-center gap-1">
                        <span className="text-4xl font-bold text-gray-900">{config.price}</span>
                        <span className="text-gray-500">{config.period}</span>
                    </div>
                    
                    <CardDescription className="text-center">
                        {config.description}
                    </CardDescription>
                    
                    <div className="flex justify-center">
                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                            {config.agents} AI Agents
                        </Badge>
                    </div>
                </CardHeader>

                <CardContent className="space-y-6">
                    <div className="space-y-3">
                        {config.features.map((feature, index) => (
                            <div key={index} className="flex items-start gap-2">
                                <Check className="w-5 h-5 text-emerald-600 mt-0.5 flex-shrink-0" />
                                <span className="text-sm text-gray-700">{feature}</span>
                            </div>
                        ))}
                    </div>

                    {config.limitations && (
                        <div className="pt-4 border-t border-gray-100">
                            <p className="text-xs text-gray-500 mb-2">Limitations:</p>
                            {config.limitations.map((limitation, index) => (
                                <div key={index} className="flex items-start gap-2">
                                    <span className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0">•</span>
                                    <span className="text-xs text-gray-500">{limitation}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="pt-4">
                        {isCurrentTier ? (
                            <Button disabled className="w-full bg-gray-100 text-gray-500">
                                Current Plan
                            </Button>
                        ) : config.contactSales ? (
                            <Button 
                                className="w-full bg-gradient-to-r from-yellow-600 to-yellow-700 hover:from-yellow-700 hover:to-yellow-800"
                                onClick={() => window.open('mailto:sales@pikar.ai?subject=Enterprise Plan Inquiry', '_blank')}
                            >
                                <Mail className="w-4 h-4 mr-2" />
                                Contact Sales
                            </Button>
                        ) : isUpgrade ? (
                            <Button 
                                className={`w-full bg-gradient-to-r ${config.color} text-white hover:opacity-90`}
                                onClick={() => onUpgrade(tier)}
                            >
                                Upgrade to {config.name}
                            </Button>
                        ) : (
                            <Button variant="outline" className="w-full" disabled>
                                Downgrade Not Available
                            </Button>
                        )}
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    );
}