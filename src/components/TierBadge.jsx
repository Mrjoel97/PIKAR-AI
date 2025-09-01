import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Crown, Zap, Building, Rocket } from 'lucide-react';

export default function TierBadge({ tier, className, showPrice = false }) {
    const tierConfig = {
        solopreneur: {
            label: 'Solopreneur',
            price: '$99/month',
            color: 'bg-blue-100 text-blue-800 border-blue-200',
            icon: Zap
        },
        startup: {
            label: 'Startup',
            price: '$297/month',
            color: 'bg-green-100 text-green-800 border-green-200',
            icon: Rocket
        },
        sme: {
            label: 'SME',
            price: '$597/month',
            color: 'bg-purple-100 text-purple-800 border-purple-200',
            icon: Building
        },
        enterprise: {
            label: 'Enterprise',
            price: 'Contact Sales',
            color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
            icon: Crown
        }
    };

    const config = tierConfig[tier] || tierConfig.solopreneur;
    const Icon = config.icon;

    return (
        <Badge className={`${config.color} ${className} flex items-center gap-1`}>
            <Icon className="w-3 h-3" />
            {config.label}
            {showPrice && <span className="ml-1 text-xs opacity-75">• {config.price}</span>}
        </Badge>
    );
}