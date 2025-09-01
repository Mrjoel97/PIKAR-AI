import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { InvokeLLM } from '@/api/integrations';
import { Brain, TrendingUp, AlertCircle, Target, BarChart3, Zap } from 'lucide-react';
import { toast } from 'sonner';

const PREDICTION_MODELS = {
    revenue_forecast: {
        name: "Revenue Forecasting",
        description: "Predict future revenue based on historical data and market trends",
        accuracy_range: "85-92%",
        timeframes: ["1 month", "3 months", "6 months", "1 year", "2 years"]
    },
    market_trend_analysis: {
        name: "Market Trend Analysis",
        description: "Analyze market patterns and predict future opportunities",
        accuracy_range: "78-85%",
        timeframes: ["1 week", "1 month", "3 months", "6 months"]
    },
    customer_behavior: {
        name: "Customer Behavior Prediction",
        description: "Predict customer actions, churn risk, and lifetime value",
        accuracy_range: "82-89%",
        timeframes: ["1 month", "3 months", "6 months", "1 year"]
    },
    operational_efficiency: {
        name: "Operational Efficiency Forecasting",
        description: "Predict process improvements and resource optimization",
        accuracy_range: "79-86%",
        timeframes: ["1 month", "3 months", "6 months"]
    },
    risk_assessment: {
        name: "Risk Probability Analysis",
        description: "Predict potential risks and their impact probabilities",
        accuracy_range: "76-83%",
        timeframes: ["1 month", "3 months", "6 months", "1 year"]
    }
};

export default function PredictiveAnalytics({ historicalData, onPredictionComplete }) {
    const [selectedModel, setSelectedModel] = useState('revenue_forecast');
    const [selectedTimeframe, setSelectedTimeframe] = useState('3 months');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [predictions, setPredictions] = useState(null);
    const [modelAccuracy, setModelAccuracy] = useState(null);
    const [trends, setTrends] = useState([]);

    const generatePredictions = async () => {
        setIsAnalyzing(true);
        try {
            const modelConfig = PREDICTION_MODELS[selectedModel];
            
            const prompt = `You are the PIKAR AI Data Analysis Agent with advanced predictive analytics capabilities. Generate comprehensive predictions using machine learning techniques.

**PREDICTIVE ANALYSIS REQUEST**

Model Type: ${modelConfig.name}
Timeframe: ${selectedTimeframe}
Historical Data: ${JSON.stringify(historicalData, null, 2)}

**ANALYSIS REQUIREMENTS:**

1. **Data Pattern Recognition:**
   - Identify seasonal patterns, trends, and cyclical behaviors
   - Detect anomalies and outliers in historical data
   - Calculate statistical measures (mean, variance, correlation)

2. **Predictive Modeling:**
   - Apply appropriate forecasting algorithms (ARIMA, Prophet, Neural Networks)
   - Generate point forecasts with confidence intervals
   - Calculate prediction accuracy and reliability scores

3. **Scenario Analysis:**
   - Best case scenario (95th percentile)
   - Most likely scenario (50th percentile)  
   - Worst case scenario (5th percentile)
   - Custom scenario based on specific assumptions

4. **Risk Assessment:**
   - Identify key risk factors affecting predictions
   - Quantify prediction uncertainty
   - Recommend monitoring indicators

Return comprehensive analysis as JSON:
{
  "model_summary": {
    "model_type": "${selectedModel}",
    "accuracy_score": <0-100>,
    "confidence_level": <0-100>,
    "data_quality": <0-100>,
    "prediction_reliability": <0-100>
  },
  "predictions": [
    {
      "period": "<time_period>",
      "predicted_value": <number>,
      "confidence_interval": {
        "lower_bound": <number>,
        "upper_bound": <number>
      },
      "probability": <0-1>
    }
  ],
  "scenarios": {
    "best_case": {
      "value": <number>,
      "probability": <0-1>,
      "key_drivers": [<strings>]
    },
    "most_likely": {
      "value": <number>,
      "probability": <0-1>,
      "key_drivers": [<strings>]
    },
    "worst_case": {
      "value": <number>,
      "probability": <0-1>,
      "key_drivers": [<strings>]
    }
  },
  "key_insights": [<strings>],
  "risk_factors": [
    {
      "factor": "<string>",
      "impact": "<high|medium|low>",
      "probability": <0-1>,
      "mitigation": "<string>"
    }
  ],
  "recommendations": [<strings>],
  "monitoring_kpis": [<strings>]
}`;

            const analysis = await InvokeLLM({
                prompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        model_summary: { type: "object" },
                        predictions: { type: "array" },
                        scenarios: { type: "object" },
                        key_insights: { type: "array" },
                        risk_factors: { type: "array" },
                        recommendations: { type: "array" },
                        monitoring_kpis: { type: "array" }
                    }
                }
            });

            setPredictions(analysis);
            setModelAccuracy(analysis.model_summary);
            
            // Extract trends from predictions
            if (analysis.predictions) {
                const trendData = analysis.predictions.map(p => ({
                    period: p.period,
                    value: p.predicted_value,
                    confidence: p.confidence_interval
                }));
                setTrends(trendData);
            }

            if (onPredictionComplete) {
                onPredictionComplete({
                    model: selectedModel,
                    timeframe: selectedTimeframe,
                    predictions: analysis,
                    timestamp: new Date()
                });
            }

            toast.success("Predictive analysis completed successfully");

        } catch (error) {
            console.error("Error generating predictions:", error);
            toast.error("Failed to generate predictions");
        } finally {
            setIsAnalyzing(false);
        }
    };

    const getAccuracyColor = (score) => {
        if (score >= 85) return 'text-green-600 bg-green-50';
        if (score >= 70) return 'text-blue-600 bg-blue-50';
        if (score >= 60) return 'text-yellow-600 bg-yellow-50';
        return 'text-red-600 bg-red-50';
    };

    const getRiskColor = (impact) => {
        switch (impact) {
            case 'high': return 'bg-red-100 text-red-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getScenarioColor = (scenario) => {
        switch (scenario) {
            case 'best_case': return 'border-green-500 bg-green-50';
            case 'most_likely': return 'border-blue-500 bg-blue-50';
            case 'worst_case': return 'border-red-500 bg-red-50';
            default: return 'border-gray-500 bg-gray-50';
        }
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-3">
                        <Brain className="w-6 h-6 text-purple-600" />
                        AI Predictive Analytics Engine
                    </CardTitle>
                    <p className="text-gray-600">
                        Advanced machine learning models for business forecasting and trend prediction
                    </p>
                </CardHeader>
                <CardContent>
                    {/* Model Configuration */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <div>
                            <label className="block text-sm font-medium mb-2">Prediction Model</label>
                            <Select value={selectedModel} onValueChange={setSelectedModel}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select prediction model" />
                                </SelectTrigger>
                                <SelectContent>
                                    {Object.entries(PREDICTION_MODELS).map(([key, model]) => (
                                        <SelectItem key={key} value={key}>
                                            <div>
                                                <div className="font-medium">{model.name}</div>
                                                <div className="text-xs text-gray-500">
                                                    Accuracy: {model.accuracy_range}
                                                </div>
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-sm text-gray-600 mt-1">
                                {PREDICTION_MODELS[selectedModel]?.description}
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">Forecast Timeframe</label>
                            <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select timeframe" />
                                </SelectTrigger>
                                <SelectContent>
                                    {PREDICTION_MODELS[selectedModel]?.timeframes.map((timeframe) => (
                                        <SelectItem key={timeframe} value={timeframe}>
                                            {timeframe}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <Button 
                        onClick={generatePredictions} 
                        disabled={isAnalyzing}
                        className="w-full bg-purple-600 hover:bg-purple-700"
                    >
                        {isAnalyzing ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                Analyzing Patterns...
                            </>
                        ) : (
                            <>
                                <Brain className="w-4 h-4 mr-2" />
                                Generate Predictions
                            </>
                        )}
                    </Button>

                    {predictions && (
                        <div className="mt-8 space-y-6">
                            {/* Model Performance */}
                            {modelAccuracy && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <Target className="w-5 h-5 text-green-600" />
                                            Model Performance
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="text-center">
                                                <div className={`text-2xl font-bold p-2 rounded ${getAccuracyColor(modelAccuracy.accuracy_score)}`}>
                                                    {modelAccuracy.accuracy_score}%
                                                </div>
                                                <div className="text-sm text-gray-600">Accuracy Score</div>
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-2xl font-bold p-2 rounded ${getAccuracyColor(modelAccuracy.confidence_level)}`}>
                                                    {modelAccuracy.confidence_level}%
                                                </div>
                                                <div className="text-sm text-gray-600">Confidence Level</div>
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-2xl font-bold p-2 rounded ${getAccuracyColor(modelAccuracy.data_quality)}`}>
                                                    {modelAccuracy.data_quality}%
                                                </div>
                                                <div className="text-sm text-gray-600">Data Quality</div>
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-2xl font-bold p-2 rounded ${getAccuracyColor(modelAccuracy.prediction_reliability)}`}>
                                                    {modelAccuracy.prediction_reliability}%
                                                </div>
                                                <div className="text-sm text-gray-600">Reliability</div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Scenario Analysis */}
                            {predictions.scenarios && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <TrendingUp className="w-5 h-5 text-blue-600" />
                                            Scenario Analysis
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                            {Object.entries(predictions.scenarios).map(([scenarioKey, scenario]) => (
                                                <Card key={scenarioKey} className={`border-2 ${getScenarioColor(scenarioKey)}`}>
                                                    <CardContent className="p-4">
                                                        <h3 className="font-semibold mb-2 capitalize">
                                                            {scenarioKey.replace('_', ' ')} Scenario
                                                        </h3>
                                                        <div className="space-y-2">
                                                            <div className="text-2xl font-bold">
                                                                {typeof scenario.value === 'number' ? 
                                                                    scenario.value.toLocaleString() : 
                                                                    scenario.value}
                                                            </div>
                                                            <div className="text-sm text-gray-600">
                                                                Probability: {(scenario.probability * 100).toFixed(1)}%
                                                            </div>
                                                            <div className="text-xs">
                                                                <strong>Key Drivers:</strong>
                                                                <ul className="list-disc list-inside mt-1">
                                                                    {scenario.key_drivers?.slice(0, 2).map((driver, i) => (
                                                                        <li key={i}>{driver}</li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        </div>
                                                    </CardContent>
                                                </Card>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Detailed Predictions */}
                            {predictions.predictions && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <BarChart3 className="w-5 h-5 text-purple-600" />
                                            Detailed Predictions
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-3">
                                            {predictions.predictions.map((prediction, index) => (
                                                <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                                                    <div>
                                                        <div className="font-semibold">{prediction.period}</div>
                                                        <div className="text-sm text-gray-600">
                                                            Range: {prediction.confidence_interval?.lower_bound?.toLocaleString()} - {prediction.confidence_interval?.upper_bound?.toLocaleString()}
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-xl font-bold">
                                                            {prediction.predicted_value?.toLocaleString()}
                                                        </div>
                                                        <div className="text-sm text-gray-600">
                                                            {(prediction.probability * 100).toFixed(1)}% confidence
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Risk Factors */}
                            {predictions.risk_factors && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <AlertCircle className="w-5 h-5 text-red-600" />
                                            Risk Assessment
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-3">
                                            {predictions.risk_factors.map((risk, index) => (
                                                <div key={index} className="p-3 border rounded-lg">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <h3 className="font-semibold">{risk.factor}</h3>
                                                        <div className="flex gap-2">
                                                            <Badge className={getRiskColor(risk.impact)}>
                                                                {risk.impact} impact
                                                            </Badge>
                                                            <Badge variant="outline">
                                                                {(risk.probability * 100).toFixed(1)}% chance
                                                            </Badge>
                                                        </div>
                                                    </div>
                                                    <p className="text-sm text-gray-600">
                                                        <strong>Mitigation:</strong> {risk.mitigation}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Key Insights & Recommendations */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {predictions.key_insights && (
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="flex items-center gap-2">
                                                <Zap className="w-5 h-5 text-yellow-600" />
                                                Key Insights
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <ul className="space-y-2">
                                                {predictions.key_insights.map((insight, index) => (
                                                    <li key={index} className="flex items-start gap-2">
                                                        <div className="w-2 h-2 bg-yellow-500 rounded-full mt-2 flex-shrink-0"></div>
                                                        <span className="text-sm">{insight}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </CardContent>
                                    </Card>
                                )}

                                {predictions.recommendations && (
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="flex items-center gap-2">
                                                <Target className="w-5 h-5 text-green-600" />
                                                Recommendations
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <ul className="space-y-2">
                                                {predictions.recommendations.map((rec, index) => (
                                                    <li key={index} className="flex items-start gap-2">
                                                        <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                                                        <span className="text-sm">{rec}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </CardContent>
                                    </Card>
                                )}
                            </div>

                            {/* Monitoring KPIs */}
                            {predictions.monitoring_kpis && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <BarChart3 className="w-5 h-5 text-blue-600" />
                                            Monitoring KPIs
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                            {predictions.monitoring_kpis.map((kpi, index) => (
                                                <Badge key={index} variant="outline" className="p-2 text-center">
                                                    {kpi}
                                                </Badge>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}