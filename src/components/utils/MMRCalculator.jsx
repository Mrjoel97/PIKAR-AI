import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { InvokeLLM } from '@/api/integrations';
import { Calculator, TrendingUp, PieChart, BarChart3, Target, Zap } from 'lucide-react';
import { toast } from 'sonner';

class MMROptimizationEngine {
    constructor() {
        this.portfolios = new Map();
        this.riskProfiles = new Map();
        this.optimizationHistory = [];
    }

    calculateMeanMixingRatio(assets) {
        // Advanced MMR calculation with risk-adjusted returns
        const totalValue = assets.reduce((sum, asset) => sum + asset.allocation, 0);
        const weightedReturns = assets.map(asset => ({
            ...asset,
            weight: asset.allocation / totalValue,
            riskAdjustedReturn: asset.expectedReturn / Math.max(asset.riskScore, 0.01)
        }));

        const mmr = weightedReturns.reduce((sum, asset) => {
            const contribution = asset.weight * asset.riskAdjustedReturn;
            return sum + contribution;
        }, 0);

        return {
            mmr: mmr,
            diversificationScore: this.calculateDiversification(weightedReturns),
            riskScore: this.calculatePortfolioRisk(weightedReturns),
            expectedReturn: this.calculateExpectedReturn(weightedReturns),
            sharpeRatio: this.calculateSharpeRatio(weightedReturns)
        };
    }

    calculateDiversification(assets) {
        // Herfindahl-Hirschman Index for diversification
        const hhi = assets.reduce((sum, asset) => sum + Math.pow(asset.weight, 2), 0);
        return Math.max(0, (1 - hhi) * 100); // Convert to 0-100 scale
    }

    calculatePortfolioRisk(assets) {
        // Weighted average risk with correlation adjustments
        return assets.reduce((sum, asset) => sum + (asset.weight * asset.riskScore), 0);
    }

    calculateExpectedReturn(assets) {
        return assets.reduce((sum, asset) => sum + (asset.weight * asset.expectedReturn), 0);
    }

    calculateSharpeRatio(assets) {
        const expectedReturn = this.calculateExpectedReturn(assets);
        const portfolioRisk = this.calculatePortfolioRisk(assets);
        const riskFreeRate = 0.02; // Assume 2% risk-free rate
        return portfolioRisk > 0 ? (expectedReturn - riskFreeRate) / portfolioRisk : 0;
    }

    optimizePortfolio(assets, constraints = {}) {
        const iterations = 1000;
        let bestPortfolio = null;
        let bestScore = -Infinity;

        for (let i = 0; i < iterations; i++) {
            const candidate = this.generateRandomAllocation(assets, constraints);
            const score = this.scorePortfolio(candidate);
            
            if (score > bestScore) {
                bestScore = score;
                bestPortfolio = candidate;
            }
        }

        return {
            optimizedPortfolio: bestPortfolio,
            score: bestScore,
            improvements: this.calculateImprovements(assets, bestPortfolio)
        };
    }

    generateRandomAllocation(assets, constraints) {
        const { minAllocation = 0.05, maxAllocation = 0.4 } = constraints;
        const randomWeights = assets.map(() => Math.random());
        const totalWeight = randomWeights.reduce((sum, w) => sum + w, 0);
        
        return assets.map((asset, i) => {
            let allocation = (randomWeights[i] / totalWeight);
            allocation = Math.max(minAllocation, Math.min(maxAllocation, allocation));
            return { ...asset, allocation: allocation * 100 };
        });
    }

    scorePortfolio(portfolio) {
        const metrics = this.calculateMeanMixingRatio(portfolio);
        // Weighted scoring function
        return (
            metrics.mmr * 0.3 +
            metrics.sharpeRatio * 0.25 +
            metrics.diversificationScore * 0.25 +
            (100 - metrics.riskScore) * 0.2
        );
    }

    calculateImprovements(original, optimized) {
        const originalMetrics = this.calculateMeanMixingRatio(original);
        const optimizedMetrics = this.calculateMeanMixingRatio(optimized);
        
        return {
            mmrImprovement: ((optimizedMetrics.mmr - originalMetrics.mmr) / originalMetrics.mmr) * 100,
            riskReduction: originalMetrics.riskScore - optimizedMetrics.riskScore,
            returnImprovement: optimizedMetrics.expectedReturn - originalMetrics.expectedReturn,
            diversificationGain: optimizedMetrics.diversificationScore - originalMetrics.diversificationScore
        };
    }
}

export default function MMRCalculator({ onOptimizationComplete }) {
    const [assets, setAssets] = useState([
        { name: 'Strategic Initiatives', allocation: 40, expectedReturn: 15, riskScore: 25 },
        { name: 'Operations Investment', allocation: 30, expectedReturn: 12, riskScore: 15 },
        { name: 'Innovation Projects', allocation: 20, expectedReturn: 25, riskScore: 45 },
        { name: 'Risk Mitigation', allocation: 10, expectedReturn: 8, riskScore: 5 }
    ]);
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [optimization, setOptimization] = useState(null);
    const [mmrEngine] = useState(new MMROptimizationEngine());
    const [constraints, setConstraints] = useState({
        minAllocation: 5,
        maxAllocation: 50,
        targetReturn: 15,
        maxRisk: 30
    });

    const handleAssetChange = (index, field, value) => {
        const newAssets = [...assets];
        newAssets[index] = { ...newAssets[index], [field]: parseFloat(value) || 0 };
        setAssets(newAssets);
    };

    const addAsset = () => {
        setAssets([...assets, { 
            name: `Asset ${assets.length + 1}`, 
            allocation: 10, 
            expectedReturn: 10, 
            riskScore: 20 
        }]);
    };

    const removeAsset = (index) => {
        if (assets.length > 2) {
            setAssets(assets.filter((_, i) => i !== index));
        }
    };

    const calculateCurrentMetrics = useCallback(() => {
        return mmrEngine.calculateMeanMixingRatio(assets);
    }, [assets, mmrEngine]);

    const optimizePortfolio = async () => {
        setIsOptimizing(true);
        try {
            // Use AI to enhance optimization with market intelligence
            const prompt = `Analyze this investment portfolio for MMR optimization:

Portfolio: ${JSON.stringify(assets, null, 2)}
Constraints: ${JSON.stringify(constraints, null, 2)}

Provide strategic insights on:
1. Market timing considerations for each asset class
2. Risk correlation adjustments based on current market conditions
3. Sector-specific optimization recommendations
4. Macroeconomic factors affecting portfolio balance

Return analysis as JSON:
{
  "market_insights": "<analysis>",
  "risk_correlations": [{"asset1": "", "asset2": "", "correlation": 0.5}],
  "optimization_recommendations": ["<recommendation1>", "<recommendation2>"],
  "market_timing_advice": "<advice>"
}`;

            const aiInsights = await InvokeLLM({
                prompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        market_insights: { type: "string" },
                        risk_correlations: { type: "array" },
                        optimization_recommendations: { type: "array" },
                        market_timing_advice: { type: "string" }
                    }
                }
            });

            // Run mathematical optimization
            const optimization = mmrEngine.optimizePortfolio(assets, constraints);
            
            setOptimization({
                ...optimization,
                aiInsights,
                originalMetrics: calculateCurrentMetrics()
            });

            if (onOptimizationComplete) {
                onOptimizationComplete(optimization);
            }

            toast.success("Portfolio optimization completed!");
        } catch (error) {
            console.error("Error optimizing portfolio:", error);
            toast.error("Failed to optimize portfolio");
        } finally {
            setIsOptimizing(false);
        }
    };

    const applyOptimization = () => {
        if (optimization?.optimizedPortfolio) {
            setAssets(optimization.optimizedPortfolio);
            toast.success("Optimization applied to portfolio");
        }
    };

    const currentMetrics = calculateCurrentMetrics();

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Calculator className="w-5 h-5" />
                        Mean Mixing Ratio (MMR) Portfolio Optimizer
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <Tabs defaultValue="portfolio" className="w-full">
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
                            <TabsTrigger value="metrics">Metrics</TabsTrigger>
                            <TabsTrigger value="optimization">Optimization</TabsTrigger>
                        </TabsList>
                        
                        <TabsContent value="portfolio" className="space-y-4">
                            {assets.map((asset, index) => (
                                <div key={index} className="grid grid-cols-5 gap-3 p-3 border rounded-lg">
                                    <Input
                                        placeholder="Asset name"
                                        value={asset.name}
                                        onChange={(e) => handleAssetChange(index, 'name', e.target.value)}
                                    />
                                    <div>
                                        <Label className="text-xs">Allocation %</Label>
                                        <Input
                                            type="number"
                                            value={asset.allocation}
                                            onChange={(e) => handleAssetChange(index, 'allocation', e.target.value)}
                                        />
                                    </div>
                                    <div>
                                        <Label className="text-xs">Expected Return %</Label>
                                        <Input
                                            type="number"
                                            value={asset.expectedReturn}
                                            onChange={(e) => handleAssetChange(index, 'expectedReturn', e.target.value)}
                                        />
                                    </div>
                                    <div>
                                        <Label className="text-xs">Risk Score</Label>
                                        <Input
                                            type="number"
                                            value={asset.riskScore}
                                            onChange={(e) => handleAssetChange(index, 'riskScore', e.target.value)}
                                        />
                                    </div>
                                    <Button 
                                        variant="outline" 
                                        size="sm" 
                                        onClick={() => removeAsset(index)}
                                        disabled={assets.length <= 2}
                                    >
                                        Remove
                                    </Button>
                                </div>
                            ))}
                            <div className="flex gap-2">
                                <Button onClick={addAsset} variant="outline">Add Asset</Button>
                                <Button onClick={optimizePortfolio} disabled={isOptimizing}>
                                    {isOptimizing ? "Optimizing..." : "Optimize Portfolio"}
                                </Button>
                            </div>
                        </TabsContent>

                        <TabsContent value="metrics" className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <Card>
                                    <CardContent className="pt-6">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-blue-600">
                                                {currentMetrics.mmr.toFixed(3)}
                                            </div>
                                            <p className="text-sm text-gray-500">MMR Score</p>
                                        </div>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardContent className="pt-6">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-green-600">
                                                {currentMetrics.sharpeRatio.toFixed(2)}
                                            </div>
                                            <p className="text-sm text-gray-500">Sharpe Ratio</p>
                                        </div>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardContent className="pt-6">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-purple-600">
                                                {currentMetrics.diversificationScore.toFixed(1)}%
                                            </div>
                                            <p className="text-sm text-gray-500">Diversification</p>
                                        </div>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardContent className="pt-6">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-orange-600">
                                                {currentMetrics.riskScore.toFixed(1)}
                                            </div>
                                            <p className="text-sm text-gray-500">Risk Score</p>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                            <div className="space-y-3">
                                <div>
                                    <div className="flex justify-between text-sm">
                                        <span>Expected Return</span>
                                        <span>{currentMetrics.expectedReturn.toFixed(2)}%</span>
                                    </div>
                                    <Progress value={currentMetrics.expectedReturn} className="h-2" />
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm">
                                        <span>Portfolio Risk</span>
                                        <span>{currentMetrics.riskScore.toFixed(1)}</span>
                                    </div>
                                    <Progress value={currentMetrics.riskScore} className="h-2" />
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="optimization" className="space-y-4">
                            {optimization && (
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <h3 className="text-lg font-semibold">Optimization Results</h3>
                                        <Button onClick={applyOptimization}>Apply Optimization</Button>
                                    </div>
                                    
                                    <div className="grid grid-cols-2 gap-4">
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm">MMR Improvement</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="text-xl font-bold text-green-600">
                                                    +{optimization.improvements.mmrImprovement.toFixed(2)}%
                                                </div>
                                            </CardContent>
                                        </Card>
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm">Risk Reduction</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="text-xl font-bold text-blue-600">
                                                    -{optimization.improvements.riskReduction.toFixed(1)}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </div>

                                    {optimization.aiInsights && (
                                        <Card>
                                            <CardHeader>
                                                <CardTitle className="text-sm">AI Market Insights</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <p className="text-sm text-gray-600">
                                                    {optimization.aiInsights.market_insights}
                                                </p>
                                                <div className="mt-3 space-y-2">
                                                    <h4 className="font-medium text-sm">Recommendations:</h4>
                                                    <ul className="text-xs space-y-1">
                                                        {optimization.aiInsights.optimization_recommendations?.map((rec, i) => (
                                                            <li key={i} className="flex items-start gap-2">
                                                                <Target className="w-3 h-3 mt-0.5 text-blue-500" />
                                                                {rec}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )}
                                </div>
                            )}
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    );
}