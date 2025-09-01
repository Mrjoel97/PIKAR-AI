
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { ComplianceReport } from '@/api/entities';
import { ShieldCheck, Loader2, Save, Sparkles, Upload, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Toaster, toast } from 'sonner';
import ReactMarkdown from 'react-markdown'; // Assuming ReactMarkdown is available for detailed report rendering

export default function ComplianceRisk() {
    const [reportData, setReportData] = useState({
        report_title: '',
        compliance_area: 'GDPR',
        organization_name: '',
        assessment_scope: ''
    });
    const [documentFile, setDocumentFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [reportResult, setReportResult] = useState(null);
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [recentReports, setRecentReports] = useState([]);

    useEffect(() => {
        loadRecentReports();
    }, []);

    const loadRecentReports = async () => {
        try {
            const reports = await ComplianceReport.list('-created_date', 3);
            setRecentReports(reports);
        } catch (error) {
            console.error("Error loading recent reports:", error);
        }
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setDocumentFile(selectedFile);
            toast.info(`Document "${selectedFile.name}" selected.`);
        }
    };
    
    const constructPrompt = (uploadedFileUrl) => {
        let prompt = `You are the PIKAR AI Compliance & Risk Agent, an expert in enterprise-level regulatory compliance and risk management. You conduct thorough assessments based on provided documentation and standards.

**ENTERPRISE COMPLIANCE CONTEXT:**
- **Scale:** You are assessing a large enterprise with global operations, requiring an understanding of complex regulatory landscapes.
- **Criticality:** The assessment impacts legal standing, financial health, and brand reputation. Accuracy and thoroughness are paramount.
- **Scope:** The analysis covers policies, procedures, and controls across multiple departments.

**ASSESSMENT PROFILE:**
- **Organization:** ${reportData.organization_name}
- **Compliance Area:** ${reportData.compliance_area}
- **Assessment Scope:** ${reportData.assessment_scope}

**ASSESSMENT DOCUMENTATION:**
Relevant documentation (policies, procedures, reports) has been uploaded for analysis.
URL: ${uploadedFileUrl}

**ENTERPRISE COMPLIANCE ASSESSMENT DELIVERABLES:**

1.  **COMPLIANCE SCORE:** Provide a percentage score (0-100) representing the overall level of compliance based on the provided documents.
2.  **RISK LEVEL:** Assign a risk level ("low", "medium", "high", "critical") based on the findings.
3.  **EXECUTIVE SUMMARY:** Write a concise, 3-5 sentence summary for C-level executives, highlighting the overall compliance posture and critical risks.
4.  **COMPLIANCE GAPS:** Identify and list 3-7 specific, actionable compliance gaps or violations discovered in the documentation. For each gap, cite the relevant policy or procedure area.
5.  **RECOMMENDATIONS:** For each identified gap, provide a clear, actionable recommendation for remediation.
6.  **DETAILED REPORT:** Write a comprehensive assessment report in Markdown format, detailing the findings for each major area of the selected compliance standard.

**OUTPUT FORMAT:**
Provide your response as a JSON object with this exact structure:
{
  "compliance_score": <number between 0-100>,
  "risk_level": "<low/medium/high/critical>",
  "executive_summary": "<A concise summary for executives>",
  "compliance_gaps": ["<Gap 1: Description and citation>", "<Gap 2: Description and citation>"],
  "recommendations": ["<Recommendation for Gap 1>", "<Recommendation for Gap 2>"],
  "detailed_report": "<A full, Markdown-formatted compliance assessment report>"
}

Generate a comprehensive and actionable compliance and risk assessment report.`;
        return prompt;
    };

    const handleAssess = async () => {
        if (!reportData.report_title || !reportData.organization_name || !documentFile) {
            toast.error("Please provide a report title, organization name, and a document to assess.");
            return;
        }
        
        setIsLoading(true);
        setReportResult(null);
        setFileUrl('');
        
        try {
            toast.info("Uploading documentation...");
            const { file_url } = await UploadFile({ file: documentFile });
            setFileUrl(file_url);
            toast.success("Documentation uploaded. Assessment in progress...");
            
            const fullPrompt = constructPrompt(file_url);
            const response = await InvokeLLM({ 
                prompt: fullPrompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        compliance_score: { type: "number" },
                        risk_level: { type: "string", enum: ["low", "medium", "high", "critical"] },
                        executive_summary: { type: "string" },
                        compliance_gaps: { type: "array", items: { type: "string" } },
                        recommendations: { type: "array", items: { type: "string" } },
                        detailed_report: { type: "string" },
                    },
                    required: ["compliance_score", "risk_level", "executive_summary", "compliance_gaps", "recommendations", "detailed_report"]
                },
                file_urls: [file_url],
            });
            setReportResult(response);
            toast.success("Assessment complete!");
        } catch (error) {
            console.error("Error assessing compliance:", error);
            toast.error("Failed to assess compliance. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!reportResult) return;
        setIsSaving(true);
        try {
            await ComplianceReport.create({
                report_title: reportData.report_title,
                compliance_area: reportData.compliance_area,
                organization_name: reportData.organization_name,
                assessment_scope: reportData.assessment_scope,
                document_file_url: fileUrl,
                compliance_score: reportResult.compliance_score,
                risk_level: reportResult.risk_level,
                compliance_gaps: reportResult.compliance_gaps,
                recommendations: reportResult.recommendations,
                detailed_report: reportResult.detailed_report,
            });
            toast.success("Compliance report saved successfully!");
            loadRecentReports();
        } catch (error) {
            console.error("Error saving report:", error);
            toast.error("Failed to save report.");
        }
        setIsSaving(false);
    };
    
    const getRiskColor = (level) => {
         switch (level) {
            case 'critical': return 'bg-red-100 text-red-800 border-red-200';
            case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'low': return 'bg-green-100 text-green-800 border-green-200';
            default: return 'bg-gray-100';
        }
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
            <Toaster richColors />
            <div className="lg:col-span-1 space-y-8">
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-red-50 dark:bg-red-900/30 rounded-lg">
                                <ShieldCheck className="w-6 h-6 text-red-600 dark:text-red-400" />
                            </div>
                            <CardTitle>Compliance & Risk Agent</CardTitle>
                        </div>
                        <CardDescription>Assess documents against compliance standards.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="report-title">Report Title</Label>
                            <Input id="report-title" value={reportData.report_title} onChange={(e) => setReportData({...reportData, report_title: e.target.value})} placeholder="e.g., Q3 GDPR Audit" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="org-name">Organization Name</Label>
                            <Input id="org-name" value={reportData.organization_name} onChange={(e) => setReportData({...reportData, organization_name: e.target.value})} placeholder="e.g., PIKAR AI Inc." />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="compliance-area">Compliance Area</Label>
                            <Select value={reportData.compliance_area} onValueChange={(value) => setReportData({...reportData, compliance_area: value})}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="GDPR">GDPR</SelectItem>
                                    <SelectItem value="SOX">SOX</SelectItem>
                                    <SelectItem value="HIPAA">HIPAA</SelectItem>
                                    <SelectItem value="ISO_27001">ISO 27001</SelectItem>
                                    <SelectItem value="PCI_DSS">PCI DSS</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                         <div className="space-y-2">
                            <Label htmlFor="scope">Assessment Scope</Label>
                            <Textarea id="scope" value={reportData.assessment_scope} onChange={(e) => setReportData({...reportData, assessment_scope: e.target.value})} placeholder="Describe what is being assessed..." />
                        </div>
                         <div className="space-y-2">
                            <Label htmlFor="doc-upload">Compliance Documentation</Label>
                             <div className="flex items-center justify-center w-full">
                                <label htmlFor="doc-upload" className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                        <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                        <p className="text-xs text-gray-500 dark:text-gray-400 px-2 truncate">
                                            {documentFile ? documentFile.name : "Upload policies, reports, etc."}
                                        </p>
                                    </div>
                                    <Input id="doc-upload" type="file" className="hidden" onChange={handleFileChange} />
                                </label>
                            </div>
                        </div>
                        <Button onClick={handleAssess} disabled={isLoading} className="w-full bg-red-600 hover:bg-red-700 dark:text-white">
                            {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                            Assess Compliance
                        </Button>
                    </CardContent>
                </Card>
                 {recentReports.length > 0 && (
                     <Card>
                        <CardHeader>
                            <CardTitle>Recent Reports</CardTitle>
                        </CardHeader> {/* Corrected closing tag */}
                        <CardContent className="space-y-2">
                            {recentReports.map(r => (
                                <div key={r.id} className="text-sm p-3 border rounded-md">
                                    <div className="flex justify-between items-start">
                                        <p className="font-medium truncate">{r.report_title}</p>
                                        <Badge className={getRiskColor(r.risk_level)}>{r.risk_level}</Badge>
                                    </div>
                                    <p className="text-xs text-gray-500">{r.compliance_area}</p>
                                    <Progress value={r.compliance_score} className="h-1 mt-2" />
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                )}
            </div>
            <div className="lg:col-span-2">
                <Card className="min-h-[600px]">
                     <CardHeader className="flex flex-row items-center justify-between">
                        <div className="flex items-center gap-3">
                             <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                <FileText className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                            </div>
                            <div>
                                <CardTitle>Compliance Report</CardTitle>
                                <CardDescription>AI-generated compliance assessment.</CardDescription>
                            </div>
                        </div>
                        {reportResult && !isLoading && (
                            <Button onClick={handleSave} disabled={isSaving} variant="outline">
                                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                Save Report
                            </Button>
                        )}
                    </CardHeader>
                     <CardContent>
                       {isLoading && (
                            <div className="flex flex-col items-center justify-center text-center h-80">
                                <Sparkles className="w-12 h-12 text-red-500 animate-pulse" />
                                <p className="mt-4 font-medium">Assessing documents...</p>
                            </div>
                        )}
                        {reportResult && !isLoading && (
                            <div className="space-y-6">
                               <div className="text-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                    <p className="text-sm text-gray-500">Overall Compliance Score</p>
                                    <div className="text-5xl font-bold text-red-600 my-1">{reportResult.compliance_score}%</div>
                                    <Progress value={reportResult.compliance_score} className="w-1/2 mx-auto" />
                                    <Badge className={`${getRiskColor(reportResult.risk_level)} mt-4 text-base`}>
                                        Risk Level: {reportResult.risk_level.toUpperCase()}
                                    </Badge>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Executive Summary</h3>
                                    <p className="text-sm text-gray-700 dark:text-gray-300">{reportResult.executive_summary}</p>
                                </div>
                                 <div>
                                    <h3 className="font-semibold text-lg mb-2">Identified Gaps</h3>
                                    <ul className="space-y-2 list-disc list-inside text-sm">
                                        {reportResult.compliance_gaps.map((g, i) => <li key={i}>{g}</li>)}
                                    </ul>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Recommendations</h3>
                                    <ul className="space-y-2 list-disc list-inside text-sm">
                                        {reportResult.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                                    </ul>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Detailed Report</h3>
                                    <div className="prose prose-sm dark:prose-invert max-w-none border p-4 rounded-md">
                                        <ReactMarkdown>{reportResult.detailed_report}</ReactMarkdown>
                                    </div>
                                </div>
                            </div>
                        )}
                        {!reportResult && !isLoading && (
                             <div className="flex flex-col items-center justify-center text-center h-80">
                                <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full">
                                    <ShieldCheck className="w-10 h-10 text-gray-500" />
                                </div>
                                <p className="mt-4 font-medium">Compliance report will appear here</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
