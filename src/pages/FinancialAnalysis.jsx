
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { FinancialAnalysis } from '@/api/entities';
import { DollarSign, TrendingUp, AlertTriangle, Loader2, Save, Sparkles, PieChart, Upload, Shield, Target } from 'lucide-react'; // Added Shield and Target icons
import ReactMarkdown from 'react-markdown';
import { Toaster, toast } from 'sonner';

export default function FinancialAnalysisPage() {
    const [analysisData, setAnalysisData] = useState({
        analysis_title: '',
        company_name: '',
        analysis_type: 'Financial Forecast',
        time_period: ''
    });
    const [file, setFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [recentAnalyses, setRecentAnalyses] = useState([]);

    useEffect(() => {
        loadRecentAnalyses();
    }, []);

    const loadRecentAnalyses = async () => {
        try {
            const analyses = await FinancialAnalysis.list('-created_date', 5);
            setRecentAnalyses(analyses);
        } catch (error) {
            console.error("Error loading recent analyses:", error);
        }
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
        }
    };

    const constructPrompt = (uploadedFileUrl) => {
        return `You are the PIKAR AI Financial Analysis Agent specialized in ENTERPRISE-LEVEL financial analysis, risk assessment, and strategic financial planning. You provide CFO-grade insights that drive critical business decisions.

**ENTERPRISE FINANCIAL ANALYSIS CONTEXT:**
You are analyzing for a large enterprise with:
- Complex multi-entity corporate structures
- International operations with currency exposures  
- Regulatory compliance requirements (SOX, IFRS, local regulations)
- Institutional investor scrutiny and reporting obligations
- Board-level fiduciary responsibilities and governance requirements

**ANALYSIS PARAMETERS:**
- **Company:** ${analysisData.company_name}
- **Analysis Type:** ${analysisData.analysis_type}
- **Time Period:** ${analysisData.time_period || 'Multi-year strategic horizon'}
- **Financial Data Source:** ${uploadedFileUrl}

**ENTERPRISE ANALYSIS REQUIREMENTS:**

${analysisData.analysis_type === 'Financial Forecast' ? `
**FINANCIAL FORECASTING DELIVERABLES:**
1. **REVENUE PROJECTIONS:** Multi-scenario revenue forecasts (conservative, base, optimistic) with:
   - Market-driven top-line growth assumptions
   - New product/service revenue streams
   - Geographic expansion impact
   - Market share evolution and competitive dynamics

2. **EXPENSE MODELING:** Comprehensive cost structure analysis:
   - Fixed vs. variable cost breakdown
   - Operational leverage analysis
   - Inflation and cost escalation factors
   - Efficiency improvement opportunities

3. **PROFITABILITY ANALYSIS:** 
   - Gross, operating, and net margin evolution
   - EBITDA and cash flow generation capacity
   - Return on invested capital (ROIC) projections
   - Economic value added (EVA) analysis

4. **CASH FLOW PROJECTIONS:**
   - Free cash flow generation capacity
   - Working capital requirements and optimization
   - Capital expenditure planning and ROI
   - Dividend policy and shareholder return capacity

5. **BALANCE SHEET MODELING:**
   - Asset efficiency and utilization rates
   - Debt capacity and optimal capital structure
   - Liquidity requirements and credit facilities
   - Off-balance sheet obligations and commitments` : ''}

${analysisData.analysis_type === 'Risk Assessment' ? `
**ENTERPRISE RISK ASSESSMENT DELIVERABLES:**
1. **FINANCIAL RISKS:** Credit risk, liquidity risk, market risk, operational risk quantification
2. **STRATEGIC RISKS:** Competitive positioning, technology disruption, regulatory changes
3. **OPERATIONAL RISKS:** Supply chain, cybersecurity, business continuity, key person dependencies
4. **REGULATORY RISKS:** Compliance failures, regulatory changes, tax law modifications
5. **MARKET RISKS:** Economic cycles, currency fluctuations, commodity price volatility
6. **RISK MITIGATION:** Specific hedging strategies, insurance coverage, operational controls` : ''}

${analysisData.analysis_type === 'Cash Flow Analysis' ? `
**ENTERPRISE CASH FLOW ANALYSIS DELIVERABLES:**
1. **OPERATING CASH FLOW:** Revenue collection efficiency, expense timing, working capital optimization
2. **INVESTING CASH FLOW:** Capital allocation priorities, M&A impact, asset disposal strategies  
3. **FINANCING CASH FLOW:** Debt service capacity, equity funding requirements, dividend sustainability
4. **LIQUIDITY ANALYSIS:** Minimum cash requirements, credit facility utilization, cash conversion cycles
5. **CASH OPTIMIZATION:** Treasury management, cash pooling opportunities, investment yield optimization` : ''}

**OUTPUT FORMAT REQUIREMENTS:**
Provide your response as a JSON object with this exact structure:
{
  "executive_summary": "<3-4 sentence C-suite summary of key findings>",
  "analysis_report": "<comprehensive markdown-formatted financial analysis with specific metrics, charts descriptions, and quantified insights>",
  "risk_level": "<low/medium/high/critical>",
  "key_insights": ["<insight 1 with specific metrics>", "<insight 2 with financial impact>", "<insight 3 with strategic implications>"],
  "recommendations": ["<actionable recommendation 1 with timeline>", "<strategic recommendation 2 with ROI>", "<operational recommendation 3 with implementation steps>"],
  "success_metrics": ["<KPI 1 with target>", "<KPI 2 with benchmark>", "<KPI 3 with measurement frequency>"],
  "risk_mitigation": ["<risk 1 mitigation strategy>", "<risk 2 hedging approach>", "<risk 3 operational control>"]
}

**ENTERPRISE SUCCESS CRITERIA:**
- Provide quantified business impact and ROI projections
- Include specific implementation timelines and resource requirements
- Address regulatory compliance and governance considerations
- Offer benchmark comparisons and industry context
- Ensure audit-trail quality documentation and assumptions

Generate detailed, enterprise-grade financial analysis with specific metrics, actionable insights, and strategic recommendations.`;
    };

    const handleAnalyze = async () => {
        if (!analysisData.analysis_title || !analysisData.company_name || !file) {
            toast.error("Please provide a title, company name, and upload a financial data file.");
            return;
        }

        setIsLoading(true);
        setAnalysisResult(null);
        setFileUrl('');

        try {
            toast.info("Uploading financial data...");
            const { file_url } = await UploadFile({ file });
            setFileUrl(file_url);
            toast.success("Upload complete. Starting enterprise analysis...");

            const fullPrompt = constructPrompt(file_url);
            const response = await InvokeLLM({
                prompt: fullPrompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        executive_summary: { type: "string" },
                        analysis_report: { type: "string" },
                        risk_level: { type: "string" },
                        key_insights: { type: "array", items: { type: "string" } },
                        recommendations: { type: "array", items: { type: "string" } },
                        success_metrics: { type: "array", items: { type: "string" } },
                        risk_mitigation: { type: "array", items: { type: "string" } }
                    },
                    required: ["executive_summary", "analysis_report", "risk_level"]
                },
                file_urls: [file_url]
            });
            setAnalysisResult(response);
            toast.success("Enterprise financial analysis completed successfully!");
        } catch (error) {
            console.error("Error analyzing financial data:", error);
            toast.error("Failed to analyze financial data. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!analysisResult) return;
        setIsSaving(true);
        try {
            await FinancialAnalysis.create({
                ...analysisData,
                file_url: fileUrl,
                analysis_report: analysisResult.analysis_report,
                risk_level: analysisResult.risk_level,
                executive_summary: analysisResult.executive_summary,
                key_insights: analysisResult.key_insights,
                recommendations: analysisResult.recommendations,
                success_metrics: analysisResult.success_metrics,
                risk_mitigation: analysisResult.risk_mitigation,
            });
            toast.success("Financial analysis saved successfully!");
            loadRecentAnalyses();
            setAnalysisData({
                analysis_title: '',
                company_name: '',
                analysis_type: 'Financial Forecast',
                time_period: ''
            });
            setFile(null);
            setFileUrl('');
            setAnalysisResult(null);
        } catch (error) {
            console.error("Error saving analysis:", error);
            toast.error("Failed to save analysis. Please try again.");
        }
        setIsSaving(false);
    };

    const getRiskColor = (risk) => {
        switch (risk) {
            case 'critical': return 'bg-red-100 text-red-800 border-red-200';
            case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'low': return 'bg-green-100 text-green-800 border-green-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
            <Toaster richColors />

            <div className="lg:col-span-2 space-y-8">
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-teal-50 dark:bg-teal-900/30 rounded-lg">
                                <DollarSign className="w-6 h-6 text-teal-600 dark:text-teal-400" />
                            </div>
                            <CardTitle>Financial Analysis Agent</CardTitle>
                        </div>
                        <CardDescription>Upload your financial data for comprehensive analysis and forecasting.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="title">Analysis Title *</Label>
                                <Input
                                    id="title"
                                    value={analysisData.analysis_title}
                                    onChange={(e) => setAnalysisData({...analysisData, analysis_title: e.target.value})}
                                    placeholder="e.g., Q4 2024 Financial Forecast"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="company">Company Name *</Label>
                                <Input
                                    id="company"
                                    value={analysisData.company_name}
                                    onChange={(e) => setAnalysisData({...analysisData, company_name: e.target.value})}
                                    placeholder="e.g., Acme Corporation"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="type">Analysis Type *</Label>
                                <Select value={analysisData.analysis_type} onValueChange={(value) => setAnalysisData({...analysisData, analysis_type: value})}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select analysis type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="Financial Forecast">Financial Forecast</SelectItem>
                                        <SelectItem value="Risk Assessment">Risk Assessment</SelectItem>
                                        <SelectItem value="Cash Flow Analysis">Cash Flow Analysis</SelectItem>
                                        <SelectItem value="Profitability Analysis">Profitability Analysis</SelectItem>
                                        <SelectItem value="Investment Analysis">Investment Analysis</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="period">Time Period</Label>
                                <Input
                                    id="period"
                                    value={analysisData.time_period}
                                    onChange={(e) => setAnalysisData({...analysisData, time_period: e.target.value})}
                                    placeholder="e.g., Next 12 months"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="file-upload">Financial Data File *</Label>
                            <div className="flex items-center justify-center w-full">
                                <label htmlFor="file-upload" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                        <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                        <p className="text-sm text-gray-500 dark:text-gray-400 px-2 truncate">
                                            {file ? file.name : "Upload financial statements (CSV, TXT)"}
                                        </p>
                                    </div>
                                    <Input
                                        id="file-upload"
                                        type="file"
                                        className="hidden"
                                        onChange={handleFileChange}
                                        accept=".csv,.txt,text/plain,text/csv"
                                    />
                                </label>
                            </div>
                        </div>
                        <Button onClick={handleAnalyze} disabled={isLoading} className="w-full bg-teal-600 hover:bg-teal-700 dark:text-white">
                            {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <PieChart className="w-4 h-4 mr-2" />}
                            Run Analysis
                        </Button>
                    </CardContent>
                </Card>

                {analysisResult && (
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                    <TrendingUp className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                                </div>
                                <div>
                                    <CardTitle>Financial Analysis Report</CardTitle>
                                    <CardDescription>AI-generated financial insights and recommendations.</CardDescription>
                                </div>
                            </div>
                            <Button onClick={handleSave} disabled={isSaving} variant="outline">
                                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                Save Report
                            </Button>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center justify-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                <div className="text-center">
                                    <div className="text-sm text-gray-500">Risk Level</div>
                                    <Badge className={`${getRiskColor(analysisResult.risk_level)} mt-2`}>
                                        {analysisResult.risk_level?.toUpperCase()}
                                    </Badge>
                                </div>
                            </div>

                            {analysisResult.executive_summary && (
                                <div>
                                    <h3 className="font-semibold mb-3 flex items-center gap-2 text-lg">
                                        <Sparkles className="w-5 h-5 text-purple-500" />
                                        Executive Summary
                                    </h3>
                                    <p className="text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 p-3 rounded-md">{analysisResult.executive_summary}</p>
                                </div>
                            )}

                            {analysisResult.key_insights && analysisResult.key_insights.length > 0 && (
                                <div>
                                    <h3 className="font-semibold mb-3 flex items-center gap-2 text-lg">
                                        <Sparkles className="w-5 h-5 text-teal-500" />
                                        Key Insights
                                    </h3>
                                    <ul className="space-y-2">
                                        {analysisResult.key_insights.map((insight, i) => (
                                            <li key={i} className="flex items-start gap-3 text-sm p-2 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <div className="w-2 h-2 bg-teal-500 rounded-full mt-1.5 flex-shrink-0" />
                                                <span>{insight}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
                                <div>
                                    <h3 className="font-semibold mb-3 flex items-center gap-2 text-lg">
                                        <AlertTriangle className="w-5 h-5 text-orange-500" />
                                        Recommendations
                                    </h3>
                                    <ul className="space-y-2">
                                        {analysisResult.recommendations.map((rec, i) => (
                                            <li key={i} className="flex items-start gap-3 text-sm p-2 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 flex-shrink-0" />
                                                <span>{rec}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {analysisResult.success_metrics && analysisResult.success_metrics.length > 0 && (
                                <div>
                                    <h3 className="font-semibold mb-3 flex items-center gap-2 text-lg">
                                        <Target className="w-5 h-5 text-blue-500" />
                                        Success Metrics (KPIs)
                                    </h3>
                                    <ul className="space-y-2">
                                        {analysisResult.success_metrics.map((metric, i) => (
                                            <li key={i} className="flex items-start gap-3 text-sm p-2 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5 flex-shrink-0" />
                                                <span>{metric}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {analysisResult.risk_mitigation && analysisResult.risk_mitigation.length > 0 && (
                                <div>
                                    <h3 className="font-semibold mb-3 flex items-center gap-2 text-lg">
                                        <Shield className="w-5 h-5 text-red-500" />
                                        Risk Mitigation Plan
                                    </h3>
                                    <ul className="space-y-2">
                                        {analysisResult.risk_mitigation.map((mitigation, i) => (
                                            <li key={i} className="flex items-start gap-3 text-sm p-2 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <div className="w-2 h-2 bg-red-500 rounded-full mt-1.5 flex-shrink-0" />
                                                <span>{mitigation}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <div>
                                <h3 className="font-semibold mb-3 flex items-center gap-2 text-lg">
                                    <TrendingUp className="w-5 h-5" />
                                    Detailed Analysis Report
                                </h3>
                                <div className="prose dark:prose-invert max-w-none p-4 border rounded-md">
                                    <ReactMarkdown>{analysisResult.analysis_report}</ReactMarkdown>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>

            <div className="lg:col-span-1">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <PieChart className="w-5 h-5" />
                            Recent Analyses
                        </CardTitle>
                        <CardDescription>Previously completed financial reports</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {recentAnalyses.length > 0 ? (
                            <div className="space-y-3">
                                {recentAnalyses.map((analysis) => (
                                    <div key={analysis.id} className="p-3 border rounded-lg">
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className="font-medium text-sm">{analysis.analysis_title}</h4>
                                            <Badge className={getRiskColor(analysis.risk_level)} variant="outline">
                                                {analysis.risk_level}
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-gray-500">{analysis.company_name}</p>
                                        <p className="text-xs text-gray-500 mt-1">{analysis.analysis_type}</p>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center text-gray-500 py-8">
                                <DollarSign className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                <p className="text-sm">No analyses completed yet</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
