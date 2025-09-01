import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { CandidateScreening } from '@/api/entities';
import { UserCheck, Loader2, Save, Sparkles, Upload, FileText, CheckCircle, XCircle, Award } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Toaster, toast } from 'sonner';

export default function HRRecruitment() {
    const [jobDescription, setJobDescription] = useState('');
    const [jobTitle, setJobTitle] = useState('');
    const [resumeFile, setResumeFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [screeningResult, setScreeningResult] = useState(null);
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [recentCandidates, setRecentCandidates] = useState([]);

    useEffect(() => {
        loadRecentCandidates();
    }, []);

    const loadRecentCandidates = async () => {
        try {
            const candidates = await CandidateScreening.list('-created_date', 5);
            setRecentCandidates(candidates);
        } catch (error) {
            console.error("Error loading recent candidates:", error);
        }
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setResumeFile(selectedFile);
            toast.info(`Resume "${selectedFile.name}" selected.`);
        }
    };
    
    const constructPrompt = (uploadedFileUrl) => {
        let prompt = `You are the PIKAR AI HR & Recruitment Agent, an expert in enterprise-level talent acquisition and candidate screening. Your analysis must be thorough, unbiased, and aligned with strategic hiring goals for a large organization.

**ENTERPRISE HIRING CONTEXT:**
- **Scale:** You are screening for roles within a large enterprise, where cultural fit, scalability, and long-term potential are as important as technical skills.
- **Complexity:** The roles often have complex requirements, involving cross-functional collaboration and stakeholder management.
- **Compliance:** Your analysis must be compliant with HR best practices and avoid discriminatory language or biased assessments.

**HIRING PROFILE:**
- **Job Title:** ${jobTitle}
- **Job Description:** ${jobDescription}

**CANDIDATE RESUME:**
A candidate's resume has been uploaded for analysis. Use this as the sole source of information about the candidate.
URL: ${uploadedFileUrl}

**ENTERPRISE SCREENING DELIVERABLES:**

1.  **CANDIDATE NAME:** Extract the candidate's full name from the resume.
2.  **MATCH SCORE:** Provide a percentage score (0-100) indicating the candidate's match to the job description. The score should be based on:
    -   Experience Alignment (40%)
    -   Skills Match (40%)
    -   Education & Certifications (10%)
    -   Keywords & Phrasing (10%)
3.  **SCREENING SUMMARY:** Write a concise, 3-5 sentence summary of the candidate's profile and their suitability for the role.
4.  **STRENGTHS:** Identify and list 3-5 key strengths of the candidate that align directly with the job description.
5.  **WEAKNESSES / GAPS:** Identify and list 2-4 potential weaknesses, skill gaps, or areas for clarification. Frame these constructively as "Areas to Explore".
6.  **RECOMMENDATION:** Provide a clear hiring recommendation from the following options: "strong_hire", "hire", "maybe", "no_hire".

**OUTPUT FORMAT:**
Provide your response as a JSON object with this exact structure:
{
  "candidate_name": "<Candidate's Full Name>",
  "match_score": <number between 0-100>,
  "screening_summary": "<A concise summary of the candidate's profile>",
  "strengths": ["<Strength 1>", "<Strength 2>", "<Strength 3>"],
  "weaknesses": ["<Weakness/Gap 1>", "<Weakness/Gap 2>"],
  "recommendation": "<strong_hire/hire/maybe/no_hire>"
}

Generate a comprehensive and unbiased screening report for this candidate.`;
        return prompt;
    };

    const handleScreen = async () => {
        if (!jobTitle || !jobDescription || !resumeFile) {
            toast.error("Please provide a job title, description, and a resume file.");
            return;
        }
        
        setIsLoading(true);
        setScreeningResult(null);
        setFileUrl('');
        
        try {
            toast.info("Uploading resume...");
            const { file_url } = await UploadFile({ file: resumeFile });
            setFileUrl(file_url);
            toast.success("Resume uploaded. Screening in progress...");
            
            const fullPrompt = constructPrompt(file_url);
            const response = await InvokeLLM({ 
                prompt: fullPrompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        candidate_name: { type: "string" },
                        match_score: { type: "number" },
                        screening_summary: { type: "string" },
                        strengths: { type: "array", items: { type: "string" } },
                        weaknesses: { type: "array", items: { type: "string" } },
                        recommendation: { type: "string", enum: ["strong_hire", "hire", "maybe", "no_hire"] },
                    },
                    required: ["candidate_name", "match_score", "screening_summary", "strengths", "weaknesses", "recommendation"]
                },
                file_urls: [file_url],
            });
            setScreeningResult(response);
            toast.success("Screening complete!");
        } catch (error) {
            console.error("Error screening candidate:", error);
            toast.error("Failed to screen candidate. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!screeningResult) return;
        setIsSaving(true);
        try {
            await CandidateScreening.create({
                job_title: jobTitle,
                job_description: jobDescription,
                candidate_name: screeningResult.candidate_name,
                resume_file_url: fileUrl,
                match_score: screeningResult.match_score,
                screening_summary: screeningResult.screening_summary,
                strengths: screeningResult.strengths,
                weaknesses: screeningResult.weaknesses,
                recommendation: screeningResult.recommendation,
            });
            toast.success("Screening report saved successfully!");
            loadRecentCandidates();
        } catch (error) {
            console.error("Error saving report:", error);
            toast.error("Failed to save report.");
        }
        setIsSaving(false);
    };

    const getRecommendationBadge = (rec) => {
        switch (rec) {
            case 'strong_hire': return 'bg-green-100 text-green-800 border-green-200';
            case 'hire': return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'maybe': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'no_hire': return 'bg-red-100 text-red-800 border-red-200';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
            <Toaster richColors />
            <div className="lg:col-span-1 space-y-8">
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-cyan-50 dark:bg-cyan-900/30 rounded-lg">
                                <UserCheck className="w-6 h-6 text-cyan-600 dark:text-cyan-400" />
                            </div>
                            <CardTitle>HR & Recruitment Agent</CardTitle>
                        </div>
                        <CardDescription>Screen candidates against a job description.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="job-title">Job Title</Label>
                            <Input id="job-title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} placeholder="e.g., Senior Software Engineer" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="job-desc">Job Description</Label>
                            <Textarea id="job-desc" value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Paste the full job description here..." className="h-32" />
                        </div>
                         <div className="space-y-2">
                            <Label htmlFor="resume-upload">Candidate Resume</Label>
                             <div className="flex items-center justify-center w-full">
                                <label htmlFor="resume-upload" className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                        <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                        <p className="text-xs text-gray-500 dark:text-gray-400 px-2 truncate">
                                            {resumeFile ? resumeFile.name : "Upload PDF or DOCX file"}
                                        </p>
                                    </div>
                                    <Input id="resume-upload" type="file" className="hidden" onChange={handleFileChange} accept=".pdf,.doc,.docx" />
                                </label>
                            </div>
                        </div>
                        <Button onClick={handleScreen} disabled={isLoading} className="w-full bg-cyan-600 hover:bg-cyan-700 dark:text-white">
                            {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                            Screen Candidate
                        </Button>
                    </CardContent>
                </Card>
                {recentCandidates.length > 0 && (
                     <Card>
                        <CardHeader>
                            <CardTitle>Recently Screened</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {recentCandidates.map(c => (
                                <div key={c.id} className="text-sm p-3 border rounded-md">
                                    <div className="flex justify-between items-start">
                                        <p className="font-medium truncate">{c.candidate_name}</p>
                                        <Badge className={getRecommendationBadge(c.recommendation)}>{c.recommendation.replace('_', ' ')}</Badge>
                                    </div>
                                    <p className="text-xs text-gray-500">for {c.job_title}</p>
                                    <Progress value={c.match_score} className="h-1 mt-2" />
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
                                <CardTitle>Screening Report</CardTitle>
                                <CardDescription>AI-generated candidate analysis.</CardDescription>
                            </div>
                        </div>
                        {screeningResult && !isLoading && (
                            <Button onClick={handleSave} disabled={isSaving} variant="outline">
                                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                Save Report
                            </Button>
                        )}
                    </CardHeader>
                    <CardContent>
                       {isLoading && (
                            <div className="flex flex-col items-center justify-center text-center h-80">
                                <Sparkles className="w-12 h-12 text-cyan-500 animate-pulse" />
                                <p className="mt-4 font-medium">Screening resume...</p>
                            </div>
                        )}
                        {screeningResult && !isLoading && (
                            <div className="space-y-6">
                                <div className="text-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                    <h2 className="text-2xl font-bold">{screeningResult.candidate_name}</h2>
                                    <p className="text-gray-500">for {jobTitle}</p>
                                    <div className="mt-4">
                                        <p className="text-sm text-gray-500">Match Score</p>
                                        <div className="text-5xl font-bold text-cyan-600 my-1">{screeningResult.match_score}%</div>
                                        <Progress value={screeningResult.match_score} className="w-1/2 mx-auto" />
                                    </div>
                                    <Badge className={`${getRecommendationBadge(screeningResult.recommendation)} mt-4 text-base`}>
                                        {screeningResult.recommendation.replace('_', ' ')}
                                    </Badge>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg mb-2">Screening Summary</h3>
                                    <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 p-3 rounded-md">{screeningResult.screening_summary}</p>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <h3 className="font-semibold text-lg mb-2 flex items-center gap-2"><CheckCircle className="w-5 h-5 text-green-500" />Strengths</h3>
                                        <ul className="space-y-2 list-inside list-disc text-sm">
                                            {screeningResult.strengths.map((s, i) => <li key={i}>{s}</li>)}
                                        </ul>
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-lg mb-2 flex items-center gap-2"><XCircle className="w-5 h-5 text-red-500" />Areas to Explore</h3>
                                        <ul className="space-y-2 list-inside list-disc text-sm">
                                            {screeningResult.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        )}
                         {!screeningResult && !isLoading && (
                             <div className="flex flex-col items-center justify-center text-center h-80">
                                <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full">
                                    <UserCheck className="w-10 h-10 text-gray-500" />
                                </div>
                                <p className="mt-4 font-medium">Candidate report will appear here</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}