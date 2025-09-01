
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { InvokeLLM, UploadFile, ExtractDataFromUploadedFile } from '@/api/integrations';
import { SalesLead } from '@/api/entities';
import { BarChart, TrendingUp, Loader2, Save, Sparkles, Target, AlertCircle, Upload, CheckCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import ReactMarkdown from 'react-markdown';
import { Toaster, toast } from 'sonner';
import AgentGateway from '@/components/AgentGateway';

const pageVariants = {
  hidden: { opacity: 0, y: 24 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 100, damping: 20, staggerChildren: 0.1 }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 120, damping: 18 }
  },
  hover: {
    y: -6,
    rotateX: -2,
    rotateY: 2,
    scale: 1.02,
    boxShadow: '0 12px 40px rgba(6,95,70,0.15)',
    transition: { type: 'spring', stiffness: 150, damping: 15 }
  }
};

export default function SalesIntelligence() {
    const [leadData, setLeadData] = useState({
        company_name: '',
        contact_person: '',
        industry: '',
        company_size: '',
        budget_range: '',
        pain_points: '',
    });
    const [file, setFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [recentLeads, setRecentLeads] = useState([]);

    // Bulk import state
    const [bulkFiles, setBulkFiles] = useState([]);
    const [isImporting, setIsImporting] = useState(false);

    useEffect(() => {
        loadRecentLeads();
    }, []);

    const loadRecentLeads = async () => {
        try {
            const leads = await SalesLead.list('-created_date', 5);
            setRecentLeads(leads);
        } catch (error) {
            console.error("Error loading recent leads:", error);
        }
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            toast.info(`File "${selectedFile.name}" selected.`);
        }
    };

    const constructPrompt = (uploadedFileUrl) => {
        let prompt = `You are the PIKAR AI Sales Intelligence Agent specialized in ENTERPRISE B2B SALES STRATEGY and large-scale deal optimization. You provide VP of Sales and CRO-level insights for complex, high-value enterprise sales cycles.

**ENTERPRISE SALES CONTEXT:**
You are analyzing prospects for enterprise-level B2B sales with:
- Complex decision-making units (6-20 stakeholders)
- Long sales cycles (6-18 months)
- High deal values ($100K-$10M+ annually)
- Multi-departmental procurement processes
- Technical evaluation and proof-of-concept requirements
- Legal, security, and compliance scrutiny
- C-suite and board-level approval processes`;
        
        if(uploadedFileUrl) {
            prompt += `\n\n**ENTERPRISE PROSPECT INTELLIGENCE:** Comprehensive prospect documentation provided for deep analysis. Use this to enrich your enterprise sales strategy. URL: ${uploadedFileUrl}`;
        }

        prompt += `\n\n**PROSPECT PROFILE:**
- **Company:** ${leadData.company_name}
- **Primary Contact:** ${leadData.contact_person}
- **Industry Vertical:** ${leadData.industry}
- **Organization Scale:** ${leadData.company_size}
- **Budget Authority:** ${leadData.budget_range}
- **Business Challenges:** ${leadData.pain_points}

**ENTERPRISE SALES INTELLIGENCE DELIVERABLES:**

1. **LEAD SCORING METHODOLOGY:**
   - Strategic fit alignment (0-25 points)
   - Financial qualification (0-25 points)
   - Decision-making authority (0-20 points)
   - Implementation readiness (0-15 points)
   - Competitive positioning (0-15 points)

2. **STAKEHOLDER MAPPING:**
   - Economic buyer identification and influence assessment
   - Technical evaluators and their criteria
   - End user champions and adoption risks
   - Procurement and legal gatekeepers
   - Executive sponsors and political dynamics

3. **ENTERPRISE SALES STRATEGY:**
   - Value proposition customization for this specific prospect
   - ROI and business case development framework
   - Competitive differentiation and positioning strategy
   - Risk mitigation and objection handling approach
   - Implementation and change management considerations

4. **DEAL PROGRESSION ROADMAP:**
   - Discovery and qualification milestones
   - Technical evaluation and proof-of-concept strategy
   - Proposal and negotiation approach
   - Contract terms and pricing strategy
   - Implementation and customer success planning

**ENTERPRISE SUCCESS CRITERIA:**
Your analysis must provide:
- Quantified lead score with detailed scoring rationale
- Specific next steps with clear timelines and owners
- ROI projections and business impact quantification
- Risk assessment with mitigation strategies
- Competitive intelligence and positioning guidance

**OUTPUT FORMAT:**
Provide your response as a JSON object with this exact structure:
{
  "lead_score": <number between 0-100>,
  "priority_level": "<low/medium/high/critical>",
  "stakeholder_analysis": "<detailed analysis of decision-making unit and key influencers>",
  "value_proposition": "<customized value proposition for this specific prospect>",
  "competitive_intelligence": "<analysis of competitive landscape and positioning strategy>",
  "deal_strategy": "<specific approach for progressing this enterprise deal>",
  "roi_projection": "<quantified business impact and ROI for the prospect>",
  "next_steps": ["<specific action 1 with timeline>", "<action 2 with owner>", "<action 3 with success criteria>"],
  "risk_factors": ["<risk 1 with mitigation>", "<risk 2 with contingency>", "<risk 3 with monitoring approach>"],
  "recommendation": "<comprehensive markdown-formatted sales strategy and execution plan>"
}

Base your enterprise scoring on:
- Strategic alignment with prospect's transformation initiatives (25%)
- Financial capacity and budget authority confirmation (25%)  
- Decision-making process clarity and timeline (20%)
- Technical fit and implementation complexity (15%)
- Competitive landscape and differentiation opportunity (15%)

Generate enterprise-grade sales intelligence with specific, actionable strategies for winning this complex B2B deal.`;
        return prompt;
    };

    const handleAnalyze = async () => {
        if (!leadData.company_name || !leadData.contact_person || !leadData.industry) {
            toast.error("Please fill in the required fields (Company, Contact, Industry).");
            return;
        }
        
        setIsLoading(true);
        setAnalysisResult(null);
        setFileUrl('');
        let uploadedFileUrl = '';
        
        try {
            if (file) {
                toast.info("Uploading file...");
                const { file_url } = await UploadFile({ file });
                uploadedFileUrl = file_url;
                setFileUrl(uploadedFileUrl);
                toast.success("File upload complete.");
            }

            const fullPrompt = constructPrompt(uploadedFileUrl);
            const response = await InvokeLLM({ 
                prompt: fullPrompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        lead_score: { type: "number" },
                        priority_level: { type: "string" },
                        stakeholder_analysis: { type: "string" },
                        value_proposition: { type: "string" },
                        competitive_intelligence: { type: "string" },
                        deal_strategy: { type: "string" },
                        roi_projection: { type: "string" },
                        next_steps: { type: "array", items: { type: "string" } },
                        risk_factors: { type: "array", items: { type: "string" } },
                        recommendation: { type: "string" }
                    },
                    required: [
                        "lead_score", "priority_level", "stakeholder_analysis",
                        "value_proposition", "competitive_intelligence", "deal_strategy",
                        "roi_projection", "next_steps", "risk_factors", "recommendation"
                    ]
                },
                file_urls: uploadedFileUrl ? [uploadedFileUrl] : undefined,
            });
            setAnalysisResult(response);
        } catch (error) {
            console.error("Error analyzing lead:", error);
            toast.error("Failed to analyze lead. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!analysisResult) {
            toast.error("No analysis to save.");
            return;
        }
        setIsSaving(true);
        try {
            await SalesLead.create({
                ...leadData,
                lead_score: analysisResult.lead_score,
                priority_level: analysisResult.priority_level,
                file_url: fileUrl,
                stakeholder_analysis: analysisResult.stakeholder_analysis,
                value_proposition: analysisResult.value_proposition,
                competitive_intelligence: analysisResult.competitive_intelligence,
                deal_strategy: analysisResult.deal_strategy,
                roi_projection: analysisResult.roi_projection,
                next_steps: analysisResult.next_steps, // Save as array
                risk_factors: analysisResult.risk_factors, // Save as array
                recommendation: analysisResult.recommendation,
            });
            toast.success("Lead analysis saved successfully!");
            loadRecentLeads();
            setLeadData({
                company_name: '',
                contact_person: '',
                industry: '',
                company_size: '',
                budget_range: '',
                pain_points: '',
            });
            setFile(null);
            setFileUrl('');
            setAnalysisResult(null);
        } catch (error) {
            console.error("Error saving lead:", error);
            toast.error("Failed to save lead. Please try again.");
        }
        setIsSaving(false);
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'critical': return 'bg-red-100 text-red-800 border-red-200';
            case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'low': return 'bg-gray-100 text-gray-800 border-gray-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    // Bulk import handlers
    const handleBulkFileChange = (e) => {
        const files = Array.from(e.target.files || []);
        setBulkFiles(files);
        if (files.length > 0) {
            toast.info(`${files.length} file${files.length > 1 ? 's' : ''} selected for import`);
        }
    };

    const normalizeLeadRecord = (rec) => {
        // Basic normalization for common header variants
        const val = (obj, keys) => {
            for (const k of keys) {
                if (obj[k] != null && obj[k] !== '') return obj[k];
                const found = Object.keys(obj).find(kk => kk.toLowerCase() === String(k).toLowerCase());
                if (found && obj[found] != null && obj[found] !== '') return obj[found];
            }
            return undefined;
        };
        return {
            company_name: val(rec, ['company_name', 'company', 'companyName', 'Company']),
            contact_person: val(rec, ['contact_person', 'contact', 'contactName', 'Contact', 'contact_person_name']),
            industry: val(rec, ['industry', 'Industry', 'sector']),
            company_size: val(rec, ['company_size', 'size']),
            budget_range: val(rec, ['budget_range', 'budget']),
            pain_points: val(rec, ['pain_points', 'notes', 'Pain Points']),
        };
    };

    const handleBulkImport = async () => {
        if (!bulkFiles || bulkFiles.length === 0) {
            toast.error('Please select at least one file to import.');
            return;
        }

        setIsImporting(true);
        try {
            const salesLeadSchema = await SalesLead.schema();
            const allowedKeys = Object.keys(salesLeadSchema.properties || {});
            const requiredKeys = salesLeadSchema.required || ['company_name', 'contact_person', 'industry'];

            let aggregated = [];

            for (const file of bulkFiles) {
                // Upload file
                const { file_url } = await UploadFile({ file });

                // Extract using schema-aware extractor (supports csv/pdf/txt/images)
                const extraction = await ExtractDataFromUploadedFile({
                    file_url,
                    json_schema: salesLeadSchema
                });

                if (extraction.status !== 'success' || !extraction.output) {
                    toast.warning(`No leads extracted from ${file.name}`);
                    continue;
                }

                const outputArray = Array.isArray(extraction.output) ? extraction.output : [extraction.output];

                // Normalize and filter records
                const cleaned = outputArray.map(normalizeLeadRecord)
                    .filter(rec => requiredKeys.every(k => rec[k] && String(rec[k]).trim().length > 0))
                    .map(rec => {
                        // Keep only schema-allowed keys
                        const obj = {};
                        for (const k of allowedKeys) {
                            if (rec[k] !== undefined) obj[k] = rec[k];
                        }
                        return obj;
                    });

                aggregated = aggregated.concat(cleaned);
            }

            if (aggregated.length === 0) {
                toast.error('No valid leads found to import.');
                setIsImporting(false);
                return;
            }

            // Insert in chunks to be safe
            const chunkSize = 50;
            for (let i = 0; i < aggregated.length; i += chunkSize) {
                const chunk = aggregated.slice(i, i + chunkSize);
                await SalesLead.bulkCreate(chunk);
            }

            toast.success(`Imported ${aggregated.length} leads successfully.`);
            setBulkFiles([]);
            loadRecentLeads();
        } catch (error) {
            console.error('Bulk import failed:', error);
            toast.error('Bulk import failed. Please check your files and try again.');
        }
        setIsImporting(false);
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-7xl mx-auto min-h-screen bg-pikar-hero p-6">
            <Toaster richColors />
            
            {/* Enhanced Header */}
            <div className="lg:col-span-3">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: 'spring', stiffness: 120, damping: 18 }}
                    className="text-center mb-8"
                >
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-900 via-emerald-800 to-emerald-700 bg-clip-text text-transparent flex items-center justify-center gap-3 mb-4">
                        <Target className="w-8 h-8 text-emerald-900" />
                        Sales Intelligence Agent
                    </h1>
                    <p className="text-xl text-emerald-700">
                        Advanced B2B lead analysis and strategic sales intelligence
                    </p>
                </motion.div>
            </div>

            <motion.div 
                className="lg:col-span-2 space-y-8"
                initial="hidden"
                animate="show"
                variants={pageVariants}
            >
                <motion.div variants={cardVariants} whileHover="hover">
                    <Card className="shadow-soft border-emerald-100">
                        <CardHeader>
                            <div className="flex items-center gap-3">
                                <div className="p-3 bg-emerald-50 rounded-xl">
                                    <Target className="w-6 h-6 text-emerald-600" />
                                </div>
                                <div>
                                    <CardTitle className="text-emerald-900">Lead Information</CardTitle>
                                    <CardDescription className="text-emerald-700">
                                        Enter prospect details and optionally upload a file for context.
                                    </CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="company" className="text-emerald-900 font-medium">Company Name *</Label>
                                    <Input
                                        id="company"
                                        value={leadData.company_name}
                                        onChange={(e) => setLeadData({...leadData, company_name: e.target.value})}
                                        placeholder="e.g., Acme Corp"
                                        className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="contact" className="text-emerald-900 font-medium">Contact Person *</Label>
                                    <Input
                                        id="contact"
                                        value={leadData.contact_person}
                                        onChange={(e) => setLeadData({...leadData, contact_person: e.target.value})}
                                        placeholder="e.g., John Smith"
                                        className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="industry" className="text-emerald-900 font-medium">Industry *</Label>
                                    <Input
                                        id="industry"
                                        value={leadData.industry}
                                        onChange={(e) => setLeadData({...leadData, industry: e.target.value})}
                                        placeholder="e.g., Technology, Healthcare"
                                        className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="size" className="text-emerald-900 font-medium">Company Size</Label>
                                    <Select value={leadData.company_size} onValueChange={(value) => setLeadData({...leadData, company_size: value})}>
                                        <SelectTrigger className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl">
                                            <SelectValue placeholder="Select company size" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="startup">Startup (1-10)</SelectItem>
                                            <SelectItem value="small">Small (11-50)</SelectItem>
                                            <SelectItem value="medium">Medium (51-250)</SelectItem>
                                            <SelectItem value="large">Large (251-1000)</SelectItem>
                                            <SelectItem value="enterprise">Enterprise (1000+)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2 md:col-span-2">
                                    <Label htmlFor="budget" className="text-emerald-900 font-medium">Budget Range</Label>
                                    <Input
                                        id="budget"
                                        value={leadData.budget_range}
                                        onChange={(e) => setLeadData({...leadData, budget_range: e.target.value})}
                                        placeholder="e.g., $10K-$50K annually"
                                        className="border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="pain_points" className="text-emerald-900 font-medium">Pain Points & Requirements</Label>
                                <Textarea
                                    id="pain_points"
                                    value={leadData.pain_points}
                                    onChange={(e) => setLeadData({...leadData, pain_points: e.target.value})}
                                    placeholder="Describe their challenges, needs, and requirements..."
                                    className="h-24 border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900 rounded-xl"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="file-upload" className="text-emerald-900 font-medium">Lead Document (Optional)</Label>
                                <div className="flex items-center justify-center w-full">
                                    <motion.label 
                                        htmlFor="file-upload" 
                                        className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-emerald-200 rounded-xl cursor-pointer bg-emerald-50/50 hover:bg-emerald-50"
                                        whileHover={{ scale: 1.01, rotateX: 1 }}
                                        whileTap={{ scale: 0.99 }}
                                    >
                                        <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                            <motion.div
                                                animate={{ y: [0, -2, 0] }}
                                                transition={{ duration: 2, repeat: Infinity }}
                                            >
                                                <Upload className="w-8 h-8 mb-2 text-emerald-500" />
                                            </motion.div>
                                            <p className="text-xs text-emerald-600 px-2 truncate">
                                                {file ? file.name : "Upload call transcript, profile, etc."}
                                            </p>
                                        </div>
                                        <Input id="file-upload" type="file" className="hidden" onChange={handleFileChange} />
                                    </motion.label>
                                </div>
                            </div>

                            <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                                <Button 
                                    onClick={handleAnalyze} 
                                    disabled={isLoading} 
                                    className="w-full bg-emerald-900 hover:bg-emerald-800 text-white rounded-xl h-12"
                                >
                                    {isLoading ? (
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                        >
                                            <Loader2 className="w-4 h-4 mr-2" />
                                        </motion.div>
                                    ) : (
                                        <BarChart className="w-4 h-4 mr-2" />
                                    )}
                                    Analyze Lead
                                </Button>
                            </motion.div>
                        </CardContent>
                    </Card>
                </motion.div>

                {/* Enhanced analysis results */}
                <AnimatePresence>
                    {analysisResult && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ type: 'spring', stiffness: 120, damping: 18 }}
                        >
                            <Card className="shadow-soft border-emerald-100">
                                <CardHeader className="flex flex-row items-center justify-between border-b border-emerald-100">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-emerald-50 rounded-xl">
                                            <TrendingUp className="w-6 h-6 text-emerald-600" />
                                        </div>
                                        <div>
                                            <CardTitle className="text-emerald-900">Sales Intelligence Report</CardTitle>
                                            <CardDescription className="text-emerald-700">
                                                AI-generated lead analysis and recommendations.
                                            </CardDescription>
                                        </div>
                                    </div>
                                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                                        <Button 
                                            onClick={handleSave} 
                                            disabled={isSaving} 
                                            variant="outline"
                                            className="border-emerald-200 text-emerald-900 hover:bg-emerald-50"
                                        >
                                            {isSaving ? (
                                                <motion.div
                                                    animate={{ rotate: 360 }}
                                                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                                >
                                                    <Loader2 className="w-4 h-4 mr-2" />
                                                </motion.div>
                                            ) : (
                                                <Save className="w-4 h-4 mr-2" />
                                            )}
                                            Save Lead
                                        </Button>
                                    </motion.div>
                                </CardHeader>
                                
                                <CardContent className="space-y-6 p-6">
                                    <div className="grid grid-cols-2 gap-4 p-4 bg-gradient-to-r from-emerald-50 to-emerald-100/50 rounded-2xl">
                                        <div className="text-center">
                                            <div className="text-sm text-emerald-700 mb-2">Lead Score</div>
                                            <motion.div 
                                                className="text-4xl font-bold text-emerald-900"
                                                initial={{ scale: 0.8 }}
                                                animate={{ scale: 1 }}
                                                transition={{ type: 'spring', stiffness: 200 }}
                                            >
                                                {analysisResult.lead_score}
                                            </motion.div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-sm text-emerald-700 mb-2">Priority Level</div>
                                            <Badge className={`${getPriorityColor(analysisResult.priority_level)} mt-2 text-base`}>
                                                {analysisResult.priority_level.toUpperCase()}
                                            </Badge>
                                        </div>
                                    </div>
                                    <div className="space-y-4">
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">Stakeholder Analysis</h3>
                                            <div className="prose dark:prose-invert max-w-none text-sm p-3 bg-emerald-50 dark:bg-emerald-800 rounded-xl">
                                                <ReactMarkdown>{analysisResult.stakeholder_analysis}</ReactMarkdown>
                                            </div>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">Customized Value Proposition</h3>
                                            <div className="prose dark:prose-invert max-w-none text-sm p-3 bg-emerald-50 dark:bg-emerald-800 rounded-xl">
                                                <ReactMarkdown>{analysisResult.value_proposition}</ReactMarkdown>
                                            </div>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">Competitive Intelligence</h3>
                                            <div className="prose dark:prose-invert max-w-none text-sm p-3 bg-emerald-50 dark:bg-emerald-800 rounded-xl">
                                                <ReactMarkdown>{analysisResult.competitive_intelligence}</ReactMarkdown>
                                            </div>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">Deal Progression Strategy</h3>
                                            <div className="prose dark:prose-invert max-w-none text-sm p-3 bg-emerald-50 dark:bg-emerald-800 rounded-xl">
                                                <ReactMarkdown>{analysisResult.deal_strategy}</ReactMarkdown>
                                            </div>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">ROI Projection</h3>
                                            <div className="prose dark:prose-invert max-w-none text-sm p-3 bg-emerald-50 dark:bg-emerald-800 rounded-xl">
                                                <ReactMarkdown>{analysisResult.roi_projection}</ReactMarkdown>
                                            </div>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">Next Steps</h3>
                                            <ul className="list-disc list-inside space-y-2 text-sm">
                                                {analysisResult.next_steps.map((step, index) => (
                                                    <li key={index} className="p-2 bg-emerald-50 dark:bg-emerald-800 rounded-xl">{step}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">Risk Factors & Mitigation</h3>
                                            <ul className="list-disc list-inside space-y-2 text-sm">
                                                {analysisResult.risk_factors.map((risk, index) => (
                                                    <li key={index} className="p-2 bg-emerald-50 dark:bg-emerald-800 rounded-xl">{risk}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-lg mb-2 text-emerald-900">Overall Recommendation</h3>
                                            <div className="prose dark:prose-invert max-w-none border border-emerald-200 rounded-xl p-4">
                                                <ReactMarkdown>{analysisResult.recommendation}</ReactMarkdown>
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>

            <motion.div 
                className="lg:col-span-1 space-y-6"
                initial="hidden"
                animate="show"
                variants={pageVariants}
            >
                <motion.div variants={cardVariants} whileHover="hover">
                    <Card className="shadow-soft border-emerald-100">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-emerald-900">
                                <AlertCircle className="w-5 h-5" />
                                Recent Leads
                            </CardTitle>
                            <CardDescription className="text-emerald-700">
                                Recently analyzed prospects
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {recentLeads.length > 0 ? (
                                <div className="space-y-3">
                                    {recentLeads.map((lead, index) => (
                                        <motion.div 
                                            key={lead.id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: index * 0.1 }}
                                            className="p-3 border border-emerald-100 rounded-xl hover:bg-emerald-50/50 transition-colors"
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <h4 className="font-medium text-sm text-emerald-900">{lead.company_name}</h4>
                                                <Badge className={getPriorityColor(lead.priority_level)} variant="outline">
                                                    {lead.priority_level}
                                                </Badge>
                                            </div>
                                            <p className="text-xs text-emerald-700">{lead.contact_person} • {lead.industry}</p>
                                            <div className="flex justify-between items-center mt-2">
                                                <span className="text-xs text-emerald-600">Score: {lead.lead_score}/100</span>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            ) : (
                                <motion.div 
                                    className="text-center text-emerald-600 py-8"
                                    whileHover={{ scale: 1.05 }}
                                >
                                    <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">No leads analyzed yet</p>
                                </motion.div>
                            )}
                        </CardContent>
                    </Card>
                </motion.div>
                
                {/* Bulk Import Leads */}
                <motion.div variants={cardVariants} whileHover="hover">
                    <Card className="shadow-soft border-emerald-100">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-emerald-900">
                                <Upload className="w-5 h-5" />
                                Bulk Import Leads
                            </CardTitle>
                            <CardDescription className="text-emerald-700">
                                Upload CSV, JSON, PDF, or TXT files to import multiple leads at once.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <label htmlFor="bulk-file-upload" className="text-sm font-medium text-emerald-900">
                                    Files (you can select multiple)
                                </label>
                                <Input
                                    id="bulk-file-upload"
                                    type="file"
                                    multiple
                                    accept=".csv,.json,.pdf,.txt,text/plain,application/pdf,application/json,text/csv"
                                    onChange={handleBulkFileChange}
                                    className="rounded-xl border-emerald-200 focus:border-emerald-900 focus:ring-emerald-900"
                                />
                                {bulkFiles.length > 0 && (
                                    <div className="text-xs text-emerald-700">
                                        {bulkFiles.length} file{bulkFiles.length > 1 ? 's' : ''} selected
                                    </div>
                                )}
                            </div>

                            <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                                <Button
                                    onClick={handleBulkImport}
                                    disabled={isImporting || bulkFiles.length === 0}
                                    className="w-full bg-emerald-900 hover:bg-emerald-800 text-white rounded-xl"
                                >
                                    {isImporting ? (
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                        >
                                            <Loader2 className="w-4 h-4 mr-2" />
                                        </motion.div>
                                    ) : (
                                        <CheckCircle className="w-4 h-4 mr-2" />
                                    )}
                                    {isImporting ? 'Importing...' : 'Import Leads'}
                                </Button>
                            </motion.div>

                            <div className="text-xs text-emerald-700">
                                Tip: Make sure your files include at least company_name, contact_person, and industry columns.
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>

                <motion.div variants={cardVariants}>
                    <AgentGateway agentName="Sales Intelligence Agent" />
                </motion.div>
            </motion.div>
        </div>
    );
}
