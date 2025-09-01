
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { OperationsAnalysis } from '@/api/entities';
import { SlidersHorizontal, Loader2, Save, Sparkles, Upload, FileText, CheckCircle, AlertTriangle } from 'lucide-react';
import { Toaster, toast } from 'sonner';
import { Badge } from '@/components/ui/badge'; // Added Badge import for KPI recommendations
import SNAPFramework from '@/components/utils/SNAPFramework';

export default function OperationsOptimization() {
    const [processData, setProcessData] = useState({
        process_name: '',
        process_description: ''
    });
    const [analysisFile, setAnalysisFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [report, setReport] = useState(null);
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [recentAnalyses, setRecentAnalyses] = useState([]);

    useEffect(() => {
        loadRecentAnalyses();
    }, []);

    const loadRecentAnalyses = async () => {
        try {
            const analyses = await OperationsAnalysis.list('-created_date', 3);
            setRecentAnalyses(analyses);
        } catch (error) {
            console.error("Error loading recent analyses:", error);
        }
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setAnalysisFile(selectedFile);
            toast.info(`File "${selectedFile.name}" selected.`);
        }
    };
    
    const constructPrompt = (uploadedFileUrl) => {
        let prompt = `You are the PIKAR AI Operations Optimization Agent, a specialist in analyzing and improving complex business processes for large enterprises. Your goal is to identify inefficiencies and provide actionable, high-impact recommendations.

**ENTERPRISE OPERATIONS CONTEXT:**
- **Scale & Complexity:** You are analyzing processes within a large, multi-departmental organization. Solutions must be scalable and consider cross-functional impacts.
- **Data-Driven:** Your analysis should be based on the provided process description and any uploaded documentation.
- **Impact-Oriented:** Focus on recommendations that deliver measurable improvements in cost, time, quality, or resource utilization.

**PROCESS FOR ANALYSIS:**
- **Process Name:** ${processData.process_name}
- **Process Description:** ${processData.process_description}

**CONTEXTUAL DOCUMENTATION:**
A document detailing the process (e.g., flowchart, standard operating procedure) has been uploaded.
URL: ${uploadedFileUrl}

**ENTERPRISE OPTIMIZATION REPORT DELIVERABLES:**

1.  **PROCESS SUMMARY:** Briefly summarize the process to confirm your understanding.
2.  **IDENTIFIED BOTTLENECKS & INEFFICIENCIES:** Identify and list 3-5 major bottlenecks, redundancies, or areas of inefficiency in the current process.
3.  **IMPROVEMENT SUGGESTIONS:** For each identified issue, provide a specific, actionable improvement suggestion. Suggestions could include automation, process re-engineering, technology adoption, or role clarification.
4.  **EXPECTED IMPACT:** For each suggestion, describe the expected positive impact (e.g., "Reduce cycle time by an estimated 20%", "Decrease manual errors by 50%").
5.  **KPI RECOMMENDATIONS:** Recommend 3-5 Key Performance Indicators (KPIs) to measure the performance of the optimized process.
6.  **IMPLEMENTATION PLAN:** Provide a high-level, 3-step implementation plan (e.g., "1. Pilot program with X team. 2. Refine based on feedback. 3. Enterprise-wide rollout.").

**OUTPUT FORMAT:**
Provide your response as a JSON object with this exact structure:
{
  "process_summary": "<A brief summary of the process>",
  "identified_bottlenecks": ["<Bottleneck 1>", "<Bottleneck 2>"],
  "improvement_suggestions": [
    { "suggestion": "<Suggestion for Bottleneck 1>", "expected_impact": "<Impact of Suggestion 1>" },
    { "suggestion": "<Suggestion for Bottleneck 2>", "expected_impact": "<Impact of Suggestion 2>" }
  ],
  "kpi_recommendations": ["<KPI 1>", "<KPI 2>", "<KPI 3>"],
  "implementation_plan": "<A high-level 3-step plan>"
}

Generate a comprehensive and actionable operations optimization report.`;
        return prompt;
    };

    const handleAnalyze = async () => {
        if (!processData.process_name || !processData.process_description || !analysisFile) {
            toast.error("Please provide a process name, description, and an analysis file.");
            return;
        }
        
        setIsLoading(true);
        setReport(null);
        setFileUrl('');
        
        try {
            toast.info("Uploading process document...");
            const { file_url } = await UploadFile({ file: analysisFile });
            setFileUrl(file_url);
            toast.success("Document uploaded. Analyzing process...");
            
            const fullPrompt = constructPrompt(file_url);
            const response = await InvokeLLM({ 
                prompt: fullPrompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        process_summary: { type: "string" },
                        identified_bottlenecks: { type: "array", items: { type: "string" } },
                        improvement_suggestions: { 
                            type: "array", 
                            items: { 
                                type: "object",
                                properties: {
                                    suggestion: { type: "string" },
                                    expected_impact: { type: "string" }
                                },
                                required: ["suggestion", "expected_impact"]
                            } 
                        },
                        kpi_recommendations: { type: "array", items: { type: "string" } },
                        implementation_plan: { type: "string" },
                    },
                    required: ["process_summary", "identified_bottlenecks", "improvement_suggestions", "kpi_recommendations", "implementation_plan"]
                },
                file_urls: [file_url],
            });
            setReport(response);
            toast.success("Analysis complete!");
        } catch (error) {
            console.error("Error analyzing process:", error);
            toast.error("Failed to analyze process. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!report) return;
        setIsSaving(true);
        try {
            await OperationsAnalysis.create({
                process_name: processData.process_name,
                process_description: processData.process_description,
                analysis_file_url: fileUrl,
                optimization_report: report,
            });
            toast.success("Analysis report saved successfully!");
            loadRecentAnalyses();
        } catch (error) {
            console.error("Error saving report:", error);
            toast.error("Failed to save report.");
        }
        setIsSaving(false);
    };

    const handleSNAPAnalysis = (snapResults) => {
        toast.success("SNAP Framework analysis completed!");
        // Could integrate SNAP results with optimization report
    };
    
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
            <Toaster richColors />
            <div className="lg:col-span-1 space-y-8">
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-yellow-50 dark:bg-yellow-900/30 rounded-lg">
                                <SlidersHorizontal className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                            </div>
                            <CardTitle>Operations Optimization Agent</CardTitle>
                        </div>
                        <CardDescription>Analyze business processes for inefficiencies.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="process-name">Process Name</Label>
                            <Input id="process-name" value={processData.process_name} onChange={(e) => setProcessData({...processData, process_name: e.target.value})} placeholder="e.g., Customer Onboarding" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="process-desc">Process Description</Label>
                            <Textarea id="process-desc" value={processData.process_description} onChange={(e) => setProcessData({...processData, process_description: e.target.value})} placeholder="Describe the current process from start to finish..." className="h-32" />
                        </div>
                         <div className="space-y-2">
                            <Label htmlFor="analysis-file">Process Document</Label>
                             <div className="flex items-center justify-center w-full">
                                <label htmlFor="analysis-file" className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                        <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                        <p className="text-xs text-gray-500 dark:text-gray-400 px-2 truncate">
                                            {analysisFile ? analysisFile.name : "Upload flowchart, SOP, etc."}
                                        </p>
                                    </div>
                                    <Input id="analysis-file" type="file" className="hidden" onChange={handleFileChange} />
                                </label>
                            </div>
                        </div>
                        <Button onClick={handleAnalyze} disabled={isLoading} className="w-full bg-yellow-500 hover:bg-yellow-600 text-black">
                            {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                            Analyze Process
                        </Button>
                    </CardContent>
                </Card>
                {recentAnalyses.length > 0 && (
                     <Card>
                        <CardHeader>
                            <CardTitle>Recent Analyses</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {recentAnalyses.map(a => (
                                <div key={a.id} className="text-sm p-3 border rounded-md">
                                    <p className="font-medium truncate">{a.process_name}</p>
                                    <p className="text-xs text-gray-500">
                                        {a.optimization_report?.identified_bottlenecks?.length || 0} bottlenecks identified
                                    </p>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                )}
            </div>
            <div className="lg:col-span-2 space-y-8">
                <Card className="min-h-[600px]">
                     <CardHeader className="flex flex-row items-center justify-between">
                        <div className="flex items-center gap-3">
                             <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                <FileText className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                            </div>
                            <div>
                                <CardTitle>Optimization Report</CardTitle>
                                <CardDescription>AI-generated process improvement plan.</CardDescription>
                            </div>
                        </div>
                        {report && !isLoading && (
                            <Button onClick={handleSave} disabled={isSaving} variant="outline">
                                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                Save Report
                            </Button>
                        )}
                    </CardHeader>
                     <CardContent>
                       {isLoading && (
                            <div className="flex flex-col items-center justify-center text-center h-80">
                                <Sparkles className="w-12 h-12 text-yellow-500 animate-pulse" />
                                <p className="mt-4 font-medium">Analyzing business process...</p>
                            </div>
                        )}
                        {report && !isLoading && (
                            <div className="space-y-6">
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Process Summary</h3>
                                    <p className="text-sm text-gray-700 dark:text-gray-300 p-3 bg-gray-50 dark:bg-gray-800 rounded-md">{report.process_summary}</p>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2 flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-red-500"/>Bottlenecks & Inefficiencies</h3>
                                    <ul className="space-y-2 list-disc list-inside text-sm">
                                        {report.identified_bottlenecks.map((b, i) => <li key={i}>{b}</li>)}
                                    </ul>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2 flex items-center gap-2"><CheckCircle className="w-5 h-5 text-green-500"/>Improvement Suggestions</h3>
                                    <div className="space-y-3">
                                        {report.improvement_suggestions.map((s, i) => (
                                            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <p className="font-medium text-sm">{s.suggestion}</p>
                                                <p className="text-xs text-green-600 dark:text-green-400 mt-1">Impact: {s.expected_impact}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Recommended KPIs</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {report.kpi_recommendations.map((k, i) => <Badge key={i} variant="secondary">{k}</Badge>)}
                                    </div>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Implementation Plan</h3>
                                    <p className="text-sm text-gray-700 dark:text-gray-300">{report.implementation_plan}</p>
                                </div>
                            </div>
                        )}
                        {!report && !isLoading && (
                             <div className="flex flex-col items-center justify-center text-center h-80">
                                <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full">
                                    <SlidersHorizontal className="w-10 h-10 text-gray-500" />
                                </div>
                                <p className="mt-4 font-medium">Optimization report will appear here</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
                
                {/* Add SNAP Framework */}
                <SNAPFramework 
                    processData={processData}
                    onAnalysisComplete={handleSNAPAnalysis}
                />
            </div>
        </div>
    );
}

