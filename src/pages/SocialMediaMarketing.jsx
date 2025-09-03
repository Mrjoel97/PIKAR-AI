import React, { useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';
// import { SocialCampaign, SocialAdVariant, SocialPost, ABTest } from "@/api/entities";
import { api } from '@/lib/api';
import { auth } from '@/lib/auth';
import KnowledgeSelector from "@/components/knowledge/KnowledgeSelector";
import ReactMarkdown from "react-markdown";
import { toast, Toaster } from "sonner";
import { Wand2, FlaskConical, SplitSquareHorizontal, Calendar, Save, Loader2, BarChart2, Megaphone } from "lucide-react";

const ALL_PLATFORMS = ["LinkedIn", "Facebook", "Instagram", "X/Twitter", "YouTube", "TikTok"];

export default function SocialMediaMarketing() {
  const [brief, setBrief] = useState({
    campaign_name: "",
    brand: "",
    objective: "awareness",
    audience: "",
    budget: "",
    timeframe: "",
    platforms: ["LinkedIn", "Facebook"],
    tone: "professional",
    brand_values: ""
  });
  const [knowledgeDocs, setKnowledgeDocs] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [plan, setPlan] = useState(null);
  const [adMetrics, setAdMetrics] = useState({}); // variantId -> metrics inputs
  const [iterating, setIterating] = useState(false);
  const [iterationProposal, setIterationProposal] = useState(null);
  const [saving, setSaving] = useState(false);

  const togglePlatform = (p) => {
    setBrief((b) => ({
      ...b,
      platforms: b.platforms.includes(p) ? b.platforms.filter((x) => x !== p) : [...b.platforms, p]
    }));
  };

  const constructPrompt = () => {
    const docRefs = knowledgeDocs.map((d) => `${d.document_name}: ${d.file_url}`).join("\n");
    return `You are the PIKAR AI Social Media Marketing Orchestrator.

GOAL: Create a complete multi-platform social media plan with:
- Paid ads (2-3 A/B variants per selected platform),
- Organic content calendar (2 weeks),
- Branding guidance (voice, pillars, do/don't),
- Iteration plan for A/B results.

BRIEF:
- Campaign Name: ${brief.campaign_name}
- Brand: ${brief.brand}
- Objective: ${brief.objective}
- Audience: ${brief.audience}
- Budget: ${brief.budget}
- Timeframe: ${brief.timeframe}
- Platforms: ${brief.platforms.join(", ")}
- Tone: ${brief.tone}
- Brand Values: ${brief.brand_values}

KNOWLEDGE DOCS:
${docRefs || "None"}

OUTPUT JSON SCHEMA (strict):
{
  "branding_guidelines": {
    "voice": "string",
    "pillars": ["string"],
    "do": ["string"],
    "dont": ["string"]
  },
  "paid_ads": [
    {
      "platform": "string",
      "variants": [
        {"variant_name": "A", "headline": "string", "body": "string", "cta": "string", "creative_idea": "string", "hypothesis": "string"},
        {"variant_name": "B", "headline": "string", "body": "string", "cta": "string", "creative_idea": "string", "hypothesis": "string"}
      ]
    }
  ],
  "organic_calendar": [
    {"platform":"string","date":"YYYY-MM-DD","content":"string","media_idea":"string"}
  ],
  "iteration_playbook": {
    "primary_metric": "CTR or CVR or CPA",
    "if_variant_underperforms": ["string"],
    "lift_hypotheses": ["string"]
  }
}

Return ONLY JSON.`;
  };

  const handleGenerate = async () => {
    if (!brief.campaign_name || !brief.brand) {
      toast.error("Please fill Campaign Name and Brand.");
      return;
    }
    setIsGenerating(true);
    setPlan(null);
    try {
      const { text } = await generateText({ model: openai('gpt-4o-mini'), prompt: constructPrompt(), temperature: 0.7, maxTokens: 1400 });
      let response;
      try {
        const jsonStart = text.indexOf('{');
        const jsonEnd = text.lastIndexOf('}') + 1;
        response = JSON.parse(text.slice(jsonStart, jsonEnd));
      } catch {
        response = { branding_guidelines: {}, paid_ads: [], organic_calendar: [], iteration_playbook: {} };
      }
      setPlan(response);
      toast.success("Social plan generated.");
    } catch (e) {
      toast.error("Failed to generate plan.");
      console.error(e);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!plan) return;
    setSaving(true);
    try {
      const { data: userRes } = await auth.getCurrentUser();
      const userId = userRes?.user?.id || null;
      const campaign = await api.createSocialCampaign({
        user_id: userId,
        campaign_name: brief.campaign_name,
        brand: brief.brand,
        objective: brief.objective,
        platforms: brief.platforms,
        generated_plan: plan,
        status: 'draft'
      });

      const adVariants = [];
      (plan.paid_ads || []).forEach((block) => {
        (block.variants || []).forEach((v) => {
          adVariants.push({
            campaign_id: campaign.id,
            platform: block.platform,
            variant_name: v.variant_name,
            headline: v.headline,
            body: v.body,
            cta: v.cta,
            creative_idea: v.creative_idea,
            hypothesis: v.hypothesis,
            status: "draft"
          });
        });
      });
      if (adVariants.length) {
        await api.createAdVariants(adVariants);
      }

      const posts = (plan.organic_calendar || []).map((p) => ({
        campaign_id: campaign.id,
        platform: p.platform,
        content: p.content,
        media_idea: p.media_idea,
        scheduled_time: p.date ? new Date(p.date).toISOString() : undefined,
        status: "planned"
      }));
      if (posts.length) {
        await api.createSocialPosts(posts);
      }

      toast.success("Campaign saved.");
    } catch (e) {
      toast.error("Save failed.");
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleIterate = async () => {
    // Collect current metrics inputs to inform iteration suggestions
    setIterating(true);
    try {
      const metricsSummary = Object.values(adMetrics).map((m) => ({
        platform: m.platform,
        variant_name: m.variant_name,
        ctr: Number(m.ctr || 0),
        cvr: Number(m.cvr || 0),
        cpa: Number(m.cpa || 0)
      }));

      const prompt = `You are optimizing paid social A/B tests.
Here are current results:
${JSON.stringify(metricsSummary, null, 2)}

Branding guardrails:
${JSON.stringify(plan?.branding_guidelines || {}, null, 2)}

Propose improved variants with specific edits (headline/body/cta/creative_idea), per platform.
Return JSON:
{"improvements":[{"platform":"string","from_variant":"A","new_variant_name":"A2","headline":"...","body":"...","cta":"...","creative_idea":"...","rationale":"..."}]}`;
      const { text } = await generateText({ model: openai('gpt-4o-mini'), prompt, temperature: 0.7, maxTokens: 1000 });
      let parsed;
      try {
        const jsonStart = text.indexOf('{');
        const jsonEnd = text.lastIndexOf('}') + 1;
        parsed = JSON.parse(text.slice(jsonStart, jsonEnd));
      } catch {
        parsed = { improvements: [] };
      }
      setIterationProposal(parsed);
      toast.success("Improvement proposals ready.");
    } catch (e) {
      toast.error("Iteration failed.");
      console.error(e);
    } finally {
      setIterating(false);
    }
  };

  const canGenerate = useMemo(() => !!brief.campaign_name && !!brief.brand, [brief]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <Toaster richColors />
      <header className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
          <Megaphone className="w-4 h-4" />
          Social Media Marketing Suite
        </div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-900 to-emerald-700 bg-clip-text text-transparent">
          Plan, A/B test, and iterate high-performing social campaigns
        </h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Campaign Brief</CardTitle>
            <CardDescription>Define your goals and guardrails</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label>Campaign Name</Label>
            <Input value={brief.campaign_name} onChange={(e) => setBrief({ ...brief, campaign_name: e.target.value })} />
            <Label>Brand/Product</Label>
            <Input value={brief.brand} onChange={(e) => setBrief({ ...brief, brand: e.target.value })} />
            <Label>Objective</Label>
            <Select value={brief.objective} onValueChange={(v) => setBrief({ ...brief, objective: v })}>
              <SelectTrigger><SelectValue placeholder="Objective" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="awareness">Awareness</SelectItem>
                <SelectItem value="leads">Leads</SelectItem>
                <SelectItem value="sales">Sales</SelectItem>
                <SelectItem value="engagement">Engagement</SelectItem>
              </SelectContent>
            </Select>
            <Label>Audience</Label>
            <Textarea value={brief.audience} onChange={(e) => setBrief({ ...brief, audience: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Budget</Label>
                <Input value={brief.budget} onChange={(e) => setBrief({ ...brief, budget: e.target.value })} />
              </div>
              <div>
                <Label>Timeframe</Label>
                <Input value={brief.timeframe} onChange={(e) => setBrief({ ...brief, timeframe: e.target.value })} />
              </div>
            </div>
            <Label>Platforms</Label>
            <div className="flex flex-wrap gap-2">
              {ALL_PLATFORMS.map((p) => (
                <Button key={p} type="button" variant={brief.platforms.includes(p) ? "default" : "outline"} size="sm" onClick={() => togglePlatform(p)}>
                  {p}
                </Button>
              ))}
            </div>
            <Label>Tone</Label>
            <Select value={brief.tone} onValueChange={(v) => setBrief({ ...brief, tone: v })}>
              <SelectTrigger><SelectValue placeholder="Tone" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="professional">Professional</SelectItem>
                <SelectItem value="friendly">Friendly</SelectItem>
                <SelectItem value="witty">Witty</SelectItem>
                <SelectItem value="bold">Bold</SelectItem>
              </SelectContent>
            </Select>
            <Label>Brand Values</Label>
            <Textarea value={brief.brand_values} onChange={(e) => setBrief({ ...brief, brand_values: e.target.value })} />
            <KnowledgeSelector onSelectionChange={setKnowledgeDocs} selectedDocuments={knowledgeDocs} allowMultiple />
            <Button className="w-full" onClick={handleGenerate} disabled={!canGenerate || isGenerating}>
              {isGenerating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
              Generate Plan
            </Button>
          </CardContent>
        </Card>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div>
                <CardTitle>Branding & Guidelines</CardTitle>
                <CardDescription>Guardrails for ads and posts</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {!plan ? (
                <div className="text-gray-500 text-sm">Generate a plan to see guidelines.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-medium mb-1">Voice</div>
                    <p className="text-gray-700">{plan.branding_guidelines?.voice}</p>
                    <div className="font-medium mt-3 mb-1">Pillars</div>
                    <div className="flex flex-wrap gap-2">
                      {(plan.branding_guidelines?.pillars || []).map((p, i) => <Badge key={i} variant="outline">{p}</Badge>)}
                    </div>
                  </div>
                  <div>
                    <div className="font-medium mb-1">Do</div>
                    <ul className="list-disc ml-5 text-gray-700">
                      {(plan.branding_guidelines?.do || []).map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                    <div className="font-medium mt-3 mb-1">Don't</div>
                    <ul className="list-disc ml-5 text-gray-700">
                      {(plan.branding_guidelines?.dont || []).map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <SplitSquareHorizontal className="w-5 h-5 text-emerald-700" />
                <CardTitle>A/B Test Lab (Paid Ads)</CardTitle>
              </div>
              <Button variant="outline" onClick={handleIterate} disabled={!plan || iterating}>
                {iterating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FlaskConical className="w-4 h-4 mr-2" />}
                Propose Improvements
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {!plan ? (
                <div className="text-gray-500 text-sm">Generate a plan to see variants.</div>
              ) : (
                <>
                  {(plan.paid_ads || []).map((blk, idx) => (
                    <div key={idx} className="border rounded-xl p-3">
                      <div className="font-medium mb-2">{blk.platform}</div>
                      <div className="grid md:grid-cols-2 gap-3">
                        {(blk.variants || []).map((v, i) => {
                          const id = `${blk.platform}-${v.variant_name}`;
                          return (
                            <div key={i} className="border rounded-lg p-3">
                              <div className="flex items-center justify-between mb-2">
                                <Badge variant="outline">Variant {v.variant_name}</Badge>
                                <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200">Hypothesis</Badge>
                              </div>
                              <div className="text-sm">
                                <div className="font-medium">Headline</div>
                                <div className="text-gray-700">{v.headline}</div>
                                <div className="font-medium mt-2">Body</div>
                                <ReactMarkdown className="prose prose-sm max-w-none">{v.body}</ReactMarkdown>
                                <div className="mt-2 text-xs text-gray-600">CTA: {v.cta}</div>
                                {v.creative_idea && <div className="mt-2 text-xs text-gray-600">Creative: {v.creative_idea}</div>}
                                {v.hypothesis && <div className="mt-1 text-xs text-gray-600">Hypothesis: {v.hypothesis}</div>}
                              </div>
                              <div className="grid grid-cols-3 gap-2 mt-3">
                                <Input placeholder="CTR %" onChange={(e) => setAdMetrics((m) => ({ ...m, [id]: { ...(m[id] || {}), platform: blk.platform, variant_name: v.variant_name, ctr: e.target.value } }))} />
                                <Input placeholder="CVR %" onChange={(e) => setAdMetrics((m) => ({ ...m, [id]: { ...(m[id] || {}), platform: blk.platform, variant_name: v.variant_name, cvr: e.target.value } }))} />
                                <Input placeholder="CPA" onChange={(e) => setAdMetrics((m) => ({ ...m, [id]: { ...(m[id] || {}), platform: blk.platform, variant_name: v.variant_name, cpa: e.target.value } }))} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                  {iterationProposal && (
                    <div className="border rounded-xl p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <BarChart2 className="w-4 h-4 text-emerald-700" />
                        <div className="font-medium">Proposed Improvements</div>
                      </div>
                      <ul className="list-disc ml-5 text-sm">
                        {(iterationProposal.improvements || []).map((imp, i) => (
                          <li key={i}>
                            <span className="font-medium">{imp.platform} • {imp.new_variant_name}:</span> {imp.headline} — {imp.cta}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-emerald-700" />
                <CardTitle>Organic Posting Calendar</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {!plan ? (
                <div className="text-gray-500 text-sm">Generate a plan to see the calendar.</div>
              ) : (
                <div className="grid md:grid-cols-2 gap-3">
                  {(plan.organic_calendar || []).map((p, i) => (
                    <div key={i} className="border rounded-lg p-3">
                      <div className="text-xs text-gray-500">{p.platform} • {p.date}</div>
                      <div className="text-sm mt-1 font-medium">Content</div>
                      <ReactMarkdown className="prose prose-sm max-w-none">{p.content}</ReactMarkdown>
                      {p.media_idea && <div className="text-xs text-gray-600 mt-1">Media: {p.media_idea}</div>}
                    </div>
                  ))}
                </div>
              )}
              <div className="flex justify-end">
                <Button onClick={handleSave} disabled={!plan || saving}>
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Campaign
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}