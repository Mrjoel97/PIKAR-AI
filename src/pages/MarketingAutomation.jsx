import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { MarketingCampaign } from '@/api/entities';
import { Wand2, Loader2, Save, Sparkles, Target, Upload, Mail, MessageSquare, Megaphone } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Toaster, toast } from 'sonner';

export default function MarketingAutomation() {
    const [campaignData, setCampaignData] = useState({
        product_description: '',
        target_audience: '',
        campaign_goal: '',
    });
    const [file, setFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [campaignPlan, setCampaignPlan] = useState(null);
    const [fileUrl, setFileUrl] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [recentCampaigns, setRecentCampaigns] = useState([]);

    useEffect(() => {
        loadRecentCampaigns();
    }, []);

    const loadRecentCampaigns = async () => {
        try {
            const campaigns = await MarketingCampaign.list('-created_date', 3);
            setRecentCampaigns(campaigns);
        } catch (error) {
            console.error("Error loading recent campaigns:", error);
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
        let prompt = `You are the PIKAR AI Marketing Automation Agent, an expert in creating comprehensive, multi-channel marketing strategies for enterprise-level campaigns. Your plans must be detailed, actionable, and aligned with complex business objectives.

**ENTERPRISE MARKETING CONTEXT:**
You are developing a strategy for a large enterprise with:
- Multiple product lines and business units.
- A global presence requiring regional adaptation.
- Complex customer journeys and long sales cycles.
- Significant brand equity to protect and enhance.
- The need for measurable ROI and attribution across all channels.`;
        
        if (uploadedFileUrl) {
            prompt += `\n\n**REFERENCE DOCUMENT:** A detailed marketing brief or product document has been uploaded for context. Use this as your primary source of information. URL: ${uploadedFileUrl}`;
        }
        
        prompt += `\n\n**CAMPAIGN BRIEF:**
- **Product/Service Description:** ${campaignData.product_description}
- **Target Audience Profile:** ${campaignData.target_audience}
- **Primary Campaign Goal:** ${campaignData.campaign_goal}

**ENTERPRISE CAMPAIGN PLAN DELIVERABLES:**

1.  **CAMPAIGN NAME & KEY MESSAGING:**
    -   Propose 3-5 compelling campaign names.
    -   Define a core campaign message and 3-5 supporting pillars.
    -   Outline the primary value proposition.

2.  **MULTI-CHANNEL STRATEGY:**
    -   **Email Marketing:** Design a 3-5 step email nurture sequence (for leads, prospects, customers). For each email, provide the subject line and a detailed body outline.
    -   **Social Media:** Propose a content strategy for LinkedIn, Twitter, and one other relevant platform. Provide 3 sample posts for each platform, including text and visual suggestions (e.g., 'Infographic showing...', 'Short video of...').
    -   **Paid Advertising (Ad Copy):** Write 3 ad variations for a primary channel like Google Ads or LinkedIn Ads. Include a headline, body copy, and call-to-action for each.
    -   **Content Marketing:** Suggest 2-3 cornerstone content pieces (e.g., whitepaper, webinar, case study) that support the campaign goal. Provide a brief outline for each.

3.  **EXECUTION & MEASUREMENT:**
    -   Suggest key performance indicators (KPIs) for each channel.
    -   Recommend a high-level budget allocation percentage across channels.
    -   Outline a 4-week campaign timeline with key milestones.

**OUTPUT FORMAT:**
Provide your response as a JSON object with this exact structure:
{
  "campaign_name": "<The best campaign name>",
  "key_messaging": "<The core campaign message and value proposition>",
  "email_sequence": [
    { "subject": "<Email 1 Subject>", "body": "<Email 1 Body Outline>" },
    { "subject": "<Email 2 Subject>", "body": "<Email 2 Body Outline>" }
  ],
  "social_media_posts": [
    { "platform": "LinkedIn", "content": "<Post content for LinkedIn>" },
    { "platform": "Twitter", "content": "<Post content for Twitter>" }
  ],
  "ad_copy": [
    { "headline": "<Ad 1 Headline>", "body": "<Ad 1 Body>" },
    { "headline": "<Ad 2 Headline>", "body": "<Ad 2 Body>" }
  ],
  "content_marketing_ideas": ["<Idea 1 with outline>", "<Idea 2 with outline>"],
  "kpis": ["<KPI 1>", "<KPI 2>"],
  "timeline_summary": "<A brief summary of the 4-week plan>"
}

Generate a detailed, strategic, and ready-to-execute enterprise marketing campaign plan.`;
        return prompt;
    };

    const handleGenerate = async () => {
        if (!campaignData.product_description || !campaignData.target_audience || !campaignData.campaign_goal) {
            toast.error("Please fill in all campaign brief fields.");
            return;
        }
        
        setIsLoading(true);
        setCampaignPlan(null);
        setFileUrl('');
        let uploadedFileUrl = '';
        
        try {
            if (file) {
                toast.info("Uploading context file...");
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
                        campaign_name: { type: "string" },
                        key_messaging: { type: "string" },
                        email_sequence: { type: "array", items: { type: "object", properties: { subject: { type: "string" }, body: { type: "string" } }, required: ["subject", "body"] } },
                        social_media_posts: { type: "array", items: { type: "object", properties: { platform: { type: "string" }, content: { type: "string" } }, required: ["platform", "content"] } },
                        ad_copy: { type: "array", items: { type: "object", properties: { headline: { type: "string" }, body: { type: "string" } }, required: ["headline", "body"] } },
                        content_marketing_ideas: { type: "array", items: { type: "string" } },
                        kpis: { type: "array", items: { type: "string" } },
                        timeline_summary: { type: "string" },
                    },
                    required: ["campaign_name", "key_messaging", "email_sequence", "social_media_posts", "ad_copy", "content_marketing_ideas", "kpis", "timeline_summary"]
                },
                file_urls: uploadedFileUrl ? [uploadedFileUrl] : undefined,
            });
            setCampaignPlan(response);
            toast.success("Campaign plan generated!");
        } catch (error) {
            console.error("Error generating campaign:", error);
            toast.error("Failed to generate campaign plan. Please try again.");
        }
        setIsLoading(false);
    };

    const handleSave = async () => {
        if (!campaignPlan) return;
        setIsSaving(true);
        try {
            await MarketingCampaign.create({
                ...campaignData,
                file_url: fileUrl,
                campaign_plan: campaignPlan,
            });
            toast.success("Campaign saved successfully!");
            loadRecentCampaigns();
        } catch (error) {
            console.error("Error saving campaign:", error);
            toast.error("Failed to save campaign.");
        }
        setIsSaving(false);
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
            <Toaster richColors />
            <div className="lg:col-span-1 space-y-8">
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-pink-50 dark:bg-pink-900/30 rounded-lg">
                                <Wand2 className="w-6 h-6 text-pink-600 dark:text-pink-400" />
                            </div>
                            <CardTitle>Marketing Automation Agent</CardTitle>
                        </div>
                        <CardDescription>Define your campaign and get a multi-channel plan.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="product">Product/Service Description</Label>
                            <Textarea id="product" value={campaignData.product_description} onChange={(e) => setCampaignData({...campaignData, product_description: e.target.value})} placeholder="Describe the product or service you're promoting." />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="audience">Target Audience</Label>
                            <Textarea id="audience" value={campaignData.target_audience} onChange={(e) => setCampaignData({...campaignData, target_audience: e.target.value})} placeholder="Describe your ideal customer profile." />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="goal">Campaign Goal</Label>
                            <Input id="goal" value={campaignData.campaign_goal} onChange={(e) => setCampaignData({...campaignData, campaign_goal: e.target.value})} placeholder="e.g., 'Generate 500 enterprise leads in Q3'" />
                        </div>
                         <div className="space-y-2">
                            <Label htmlFor="file-upload">Campaign Brief (Optional)</Label>
                             <div className="flex items-center justify-center w-full">
                                <label htmlFor="file-upload" className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                        <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                        <p className="text-xs text-gray-500 dark:text-gray-400 px-2 truncate">
                                            {file ? file.name : "Upload brief, persona, etc."}
                                        </p>
                                    </div>
                                    <Input id="file-upload" type="file" className="hidden" onChange={handleFileChange} />
                                </label>
                            </div>
                        </div>
                        <Button onClick={handleGenerate} disabled={isLoading} className="w-full bg-pink-600 hover:bg-pink-700 dark:text-white">
                            {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                            Generate Campaign
                        </Button>
                    </CardContent>
                </Card>

                {recentCampaigns.length > 0 && (
                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Campaigns</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {recentCampaigns.map(c => (
                                <div key={c.id} className="text-sm p-2 border rounded-md">
                                    <p className="font-medium truncate">{c.campaign_plan?.campaign_name}</p>
                                    <p className="text-xs text-gray-500">{c.campaign_goal}</p>
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
                                <Target className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                            </div>
                            <div>
                                <CardTitle>Generated Campaign Plan</CardTitle>
                                <CardDescription>Review the AI-generated multi-channel plan.</CardDescription>
                            </div>
                        </div>
                        {campaignPlan && !isLoading && (
                            <Button onClick={handleSave} disabled={isSaving} variant="outline">
                                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                                Save Campaign
                            </Button>
                        )}
                    </CardHeader>
                    <CardContent>
                        {isLoading && (
                            <div className="flex flex-col items-center justify-center text-center h-80">
                                <Sparkles className="w-12 h-12 text-pink-500 animate-pulse" />
                                <p className="mt-4 font-medium">Building your campaign strategy...</p>
                            </div>
                        )}
                        {campaignPlan && !isLoading && (
                            <div className="space-y-6">
                                <div>
                                    <h2 className="text-2xl font-bold">{campaignPlan.campaign_name}</h2>
                                    <p className="text-gray-500 mt-1">{campaignPlan.key_messaging}</p>
                                </div>
                                <div className="space-y-4">
                                    <div>
                                        <h3 className="font-semibold text-lg mb-2 flex items-center gap-2"><Mail className="w-5 h-5 text-blue-500"/>Email Sequence</h3>
                                        <div className="space-y-3">
                                        {campaignPlan.email_sequence.map((email, i) => (
                                            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <p className="font-medium text-sm">Subject: {email.subject}</p>
                                                <div className="prose prose-sm dark:prose-invert max-w-none text-gray-600 dark:text-gray-300 mt-1">
                                                    <ReactMarkdown>{email.body}</ReactMarkdown>
                                                </div>
                                            </div>
                                        ))}
                                        </div>
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-lg mb-2 flex items-center gap-2"><MessageSquare className="w-5 h-5 text-green-500"/>Social Media Posts</h3>
                                        <div className="space-y-3">
                                        {campaignPlan.social_media_posts.map((post, i) => (
                                            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <p className="font-medium text-sm">Platform: {post.platform}</p>
                                                <div className="prose prose-sm dark:prose-invert max-w-none text-gray-600 dark:text-gray-300 mt-1">
                                                     <ReactMarkdown>{post.content}</ReactMarkdown>
                                                </div>
                                            </div>
                                        ))}
                                        </div>
                                    </div>
                                     <div>
                                        <h3 className="font-semibold text-lg mb-2 flex items-center gap-2"><Megaphone className="w-5 h-5 text-orange-500"/>Ad Copy</h3>
                                        <div className="space-y-3">
                                        {campaignPlan.ad_copy.map((ad, i) => (
                                            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                                                <p className="font-medium text-sm">Headline: {ad.headline}</p>
                                                <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{ad.body}</p>
                                            </div>
                                        ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                        {!campaignPlan && !isLoading && (
                             <div className="flex flex-col items-center justify-center text-center h-80">
                                <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-full">
                                    <Target className="w-10 h-10 text-gray-500" />
                                </div>
                                <p className="mt-4 font-medium">Your campaign plan will appear here</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}