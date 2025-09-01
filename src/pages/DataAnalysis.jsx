
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { DataAnalysisReport } from '@/api/entities';
import { Bot, FileUp, Loader2, Save, Sparkles, Upload } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Toaster, toast } from 'sonner';
import KnowledgeSelector from '../components/knowledge/KnowledgeSelector'; // New import
import AgentGateway from '../components/AgentGateway'; // New import - assuming this path

export default function DataAnalysis() {
    // State variables updated
    const [analysisTitle, setAnalysisTitle] = useState('');
    const [userRequest, setUserRequest] = useState('');
    const [selectedKnowledgeDocs, setSelectedKnowledgeDocs] = useState([]); // New state
    const [dataFile, setDataFile] = useState(null); // Renamed from 'file'
    const [isLoading, setIsLoading] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(''); // Renamed from 'reportOutput'
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // There was no useEffect in the original code, so no need to keep/add one.

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            if (selectedFile.size > 5 * 1024 * 1024) { // 5MB limit
                toast.error("File size cannot exceed 5MB.");
                return;
            }
            // Added common Excel MIME types and extensions for better user guidance
            if (!['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'].includes(selectedFile.type)) {
                toast.warning("For best results, please use a CSV or Excel file.");
            }
            setDataFile(selectedFile); // Updated from setFile
        }
    };

    const constructPrompt = (uploadedFileUrl, knowledgeFileUrls) => {
        let prompt = `You are the PIKAR AI Data Analysis Agent. Conduct a comprehensive data analysis based on the following requirements:\n\n`;

        prompt += `**Primary Data File:** ${uploadedFileUrl}\n`;

        if (knowledgeFileUrls && knowledgeFileUrls.length > 0) {
            prompt += `**Additional Context from Knowledge Base:** ${knowledgeFileUrls.join(', ')}\n\n`;
        }

        prompt += `**Analysis Title:** ${analysisTitle}\n`;
        prompt += `**Specific Analysis Request:** ${userRequest}\n\n`;
        prompt += `Please provide a detailed analysis including:\n`;
        prompt += `1. Data Overview and Quality Assessment\n`;
        prompt += `2. Key Statistical Insights\n`;
        prompt += `3. Trends and Patterns\n`;
        prompt += `4. Business Implications\n`;
        prompt += `5. Actionable Recommendations\n\n`;
        prompt += `Format your response in clear, business-friendly language with specific metrics and insights.`;
        return prompt;
    };

    const handleAnalyze = async () => {
        // Updated conditions to check for dataFile instead of file
        if (!analysisTitle || !userRequest || !dataFile) {
            toast.error("Please provide analysis title, request, and upload a data file.");
            return;
        }

        setIsLoading(true);
        setAnalysisResult(''); // Updated state variable
        setFileUrl('');

        try {
            toast.info("Uploading data file...");
            // Updated file state variable
            const { file_url } = await UploadFile({ file: dataFile });
            setFileUrl(file_url);
            toast.success("Data file uploaded. Analysis in progress...");

            // Collect knowledge base file URLs
            const knowledgeFileUrls = selectedKnowledgeDocs.map(doc => doc.file_url);

            // Combine all file URLs for InvokeLLM, filtering out any empty strings/nulls
            const allFileUrls = [file_url, ...knowledgeFileUrls].filter(Boolean);

            const fullPrompt = constructPrompt(file_url, knowledgeFileUrls); // Pass knowledgeFileUrls
            const response = await InvokeLLM({
                prompt: fullPrompt,
                file_urls: allFileUrls, // Pass combined URLs
            });
            setAnalysisResult(response); // Updated state variable
            toast.success("Analysis complete!");
        } catch (error) {
            console.error("Error analyzing data:", error);
            toast.error("An error occurred during analysis. Please try again."); // Kept original error message
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        // Updated state variable
        if (!analysisResult) return;
        setIsSaving(true);
        try {
            await DataAnalysisReport.create({
                analysis_title: analysisTitle,
                user_request: userRequest,
                file_url: fileUrl,
                report_output: analysisResult, // Updated state variable
                knowledge_base_docs: selectedKnowledgeDocs.map(doc => ({
                    id: doc.id,
                    name: doc.document_name,
                    url: doc.file_url
                })),
            });
            toast.success("Analysis report saved successfully!");
        } catch (error) {
            console.error("Error saving report:", error);
            toast.error("Failed to save the report."); // Kept original error message
        }
        setIsSaving(false);
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start max-w-7xl mx-auto">
            <Toaster richColors />
            <div className="lg:col-span-1 flex flex-col gap-8">
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-indigo-50 dark:bg-indigo-900/30 rounded-lg">
                                <Bot className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                            </div>
                            <CardTitle>Data Analysis Agent</CardTitle>
                        </div>
                        <CardDescription>Upload your data and specify your analysis request.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="file-upload">Upload Data File (CSV/Excel recommended)</Label> {/* Updated label text */}
                            <div className="flex items-center justify-center w-full">
                                <label htmlFor="file-upload" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                                        <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            {dataFile ? dataFile.name : <><span className="font-semibold">Click to upload</span> or drag and drop</>} {/* Updated from file to dataFile */}
                                        </p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400">Max 5MB</p>
                                    </div>
                                    {/* Updated accept types to include common Excel extensions */}
                                    <Input id="file-upload" type="file" className="hidden" onChange={handleFileChange} accept=".csv, application/vnd.ms-excel, .xls, .xlsx" />
                                </label>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="title">Analysis Title</Label>
                            <Input id="title" placeholder="e.g., 'Q4 Sales Trend Analysis'" value={analysisTitle} onChange={(e) => setAnalysisTitle(e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="request">Analysis Request</Label>
                            <Textarea id="request" placeholder="e.g., 'Identify the top 5 performing products and forecast next quarter's sales.'" value={userRequest} onChange={(e) => setUserRequest(e.target.value)} className="h-28" />
                        </div>

                        {/* New Knowledge Base Selector */}
                        <KnowledgeSelector
                            onSelectionChange={setSelectedKnowledgeDocs}
                            selectedDocuments={selectedKnowledgeDocs}
                            allowMultiple={true}
                            filterCategory="financial" // As specified in the outline
                        />

                        <Button onClick={handleAnalyze} disabled={isLoading} className="w-full bg-green-600 hover:bg-green-700 dark:text-white"> {/* Updated button color */}
                            {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                            Run Analysis
                        </Button>
                    </CardContent>
                </Card>
                {/* AgentGateway component added as per outline */}
                <AgentGateway agentName="Data Analysis" lastOutput={analysisResult} />
            </div>

            <div className="lg:col-span-2">
                <Card className="min-h-[600px]">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                <FileUp className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                            </div>
                            <div>
                                <CardTitle>Analysis Report</CardTitle>
                                <CardDescription>Review the AI-generated data analysis below.</CardDescription>
                            </div>
                        </div>
                        {/* Updated state variable */}
                        {analysisResult && !isLoading && (
                            <Button onClick={handleSave} disabled={isSaving} variant="outline">
                                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                Save Report
                            </Button>
                        )}
                    </CardHeader>
                    <CardContent>
                        {isLoading && (
                            <div className="flex flex-col items-center justify-center text-center h-80">
                                <Sparkles className="w-12 h-12 text-indigo-500 animate-pulse" />
                                <p className="mt-4 font-medium text-gray-700 dark:text-gray-300">AI is processing your data...</p>
                                <p className="text-sm text-gray-500 dark:text-gray-400">This may take a moment for larger files.</p>
                            </div>
                        )}
                        {/* Updated state variable */}
                        {analysisResult && !isLoading && (
                             <div className="prose dark:prose-invert max-w-none">
                                <ReactMarkdown>{analysisResult}</ReactMarkdown>
                            </div>
                        )}
                        {/* Updated state variable */}
                        {!analysisResult && !isLoading && (
                            <div className="flex flex-col items-center justify-center text-center h-80">
                                <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full">
                                    <Bot className="w-10 h-10 text-gray-500 dark:text-gray-400" />
                                </div>
                                <p className="mt-4 font-medium text-gray-700 dark:text-gray-300">Your report will be generated here</p>
                                <p className="text-sm text-gray-500 dark:text-gray-400">Upload a data file and describe your request.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
