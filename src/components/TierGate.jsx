import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lock, ArrowUp } from 'lucide-react';
import TierBadge from './TierBadge';

export default function TierGate({ 
    currentTier, 
    requiredTier, 
    feature, 
    description, 
    onUpgrade,
    children 
}) {
    const tierHierarchy = ['solopreneur', 'startup', 'sme', 'enterprise'];
    const currentIndex = tierHierarchy.indexOf(currentTier);
    const requiredIndex = tierHierarchy.indexOf(requiredTier);
    
    const hasAccess = currentIndex >= requiredIndex;
    
    if (hasAccess) {
        return children;
    }
    
    return (
        <Card className="border-2 border-dashed border-gray-300 bg-gray-50">
            <CardHeader className="text-center">
                <div className="w-16 h-16 mx-auto rounded-full bg-gray-200 flex items-center justify-center mb-4">
                    <Lock className="w-8 h-8 text-gray-400" />
                </div>
                <CardTitle className="text-xl text-gray-700">
                    {feature} Locked
                </CardTitle>
                <CardDescription>
                    {description}
                </CardDescription>
                <div className="flex items-center justify-center gap-2 mt-4">
                    <span className="text-sm text-gray-500">Requires:</span>
                    <TierBadge tier={requiredTier} />
                </div>
            </CardHeader>
            <CardContent className="text-center">
                <Button 
                    onClick={() => onUpgrade(requiredTier)}
                    className="bg-emerald-600 hover:bg-emerald-700"
                >
                    <ArrowUp className="w-4 h-4 mr-2" />
                    Upgrade to {requiredTier.charAt(0).toUpperCase() + requiredTier.slice(1)}
                </Button>
            </CardContent>
        </Card>
    );
}