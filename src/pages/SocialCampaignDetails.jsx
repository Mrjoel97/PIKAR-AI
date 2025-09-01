
import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { SocialCampaign } from "@/api/entities";
import { SocialAdVariant } from "@/api/entities";
import { SocialPost } from "@/api/entities";
import { ABTest } from "@/api/entities";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import AdMetricsEditor from "@/components/social/AdMetricsEditor";
import CSVImport from "@/components/social/CSVImport";
import ReactMarkdown from "react-markdown";
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend } from "recharts";
import { toast } from "sonner";
import { Wand2, Trophy, FileDown, Loader2 } from "lucide-react";
import { InvokeLLM } from "@/api/integrations";

function useQuery() {
  const { search } = useLocation();
  return new URLSearchParams(search);
}

export default function SocialCampaignDetails() {
  const query = useQuery();
  const id = query.get("id");
  const [campaign, setCampaign] = useState(null);
  const [variants, setVariants] = useState([]);
  const [posts, setPosts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [proposal, setProposal] = useState(null);

  const load = useCallback(async () => {
    const [c] = await SocialCampaign.filter({ id });
    setCampaign(c || null);
    const v = await SocialAdVariant.filter({ campaign_id: id });
    setVariants(v || []);
    const p = await SocialPost.filter({ campaign_id: id });
    setPosts(p || []);
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const chartData = useMemo(() => {
    return (variants || []).map(v => ({
      name: `${v.platform} ${v.variant_name}`,
      CTR: v.metrics?.ctr || 0,
      CVR: v.metrics?.cvr || 0,
      CPA: v.metrics?.cpa || 0,
    }));
  }, [variants]);

  const exportPostsCSV = () => {
    const header = ["platform,date,content,media_idea"];
    const rows = (posts || []).map(p => [
      JSON.stringify(p.platform || ""),
      JSON.stringify(p.scheduled_time ? String(p.scheduled_time).slice(0,10) : ""),
      JSON.stringify(p.content || ""),
      JSON.stringify(p.media_idea || "")
    ].join(","));
    const csv = [header.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${campaign?.campaign_name || "campaign"}_posts.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const markWinner = async (variant) => {
    setBusy(true);
    try {
      // Set winner and archive others on same platform
      await SocialAdVariant.update(variant.id, { status: "winner" });
      const siblings = variants.filter(v => v.platform === variant.platform && v.id !== variant.id);
      for (const s of siblings) {
        await SocialAdVariant.update(s.id, { status: "archived" });
      }
      toast.success("Winner marked and others archived");
      load();
    } catch (e) {
      console.error(e);
      toast.error("Failed to mark winner");
    } finally {
      setBusy(false);
    }
  };

  const proposeImprovements = async () => {
    if (!variants.length) return;
    setBusy(true);
    try {
      const metricsSummary = variants.map(v => ({
        platform: v.platform,
        variant_name: v.variant_name,
        ctr: Number(v.metrics?.ctr || 0),
        cvr: Number(v.metrics?.cvr || 0),
        cpa: Number(v.metrics?.cpa || 0)
      }));
      const prompt = `Given these performance metrics, propose improved ad variants with concrete edits:
${JSON.stringify(metricsSummary, null, 2)}
Return JSON: {"improvements":[{"platform":"string","from_variant":"A","new_variant_name":"A2","headline":"...","body":"...","cta":"...","creative_idea":"...","rationale":"..."}]}`;
      const res = await InvokeLLM({
        prompt,
        response_json_schema: {
          type: "object",
          properties: {
            improvements: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  platform: { type: "string" },
                  from_variant: { type: "string" },
                  new_variant_name: { type: "string" },
                  headline: { type: "string" },
                  body: { type: "string" },
                  cta: { type: "string" },
                  creative_idea: { type: "string" },
                  rationale: { type: "string" }
                },
                required: ["platform", "new_variant_name", "headline", "body", "cta"]
              }
            }
          },
          required: ["improvements"]
        }
      });
      setProposal(res);
      toast.success("Improvement proposals ready");
    } catch (e) {
      console.error(e);
      toast.error("Failed to generate proposals");
    } finally {
      setBusy(false);
    }
  };

  const applyImprovement = async (imp) => {
    setBusy(true);
    try {
      await SocialAdVariant.create({
        campaign_id: id,
        platform: imp.platform,
        variant_name: imp.new_variant_name,
        headline: imp.headline,
        body: imp.body,
        cta: imp.cta,
        creative_idea: imp.creative_idea,
        hypothesis: `Iterated from ${imp.from_variant || "N/A"}: ${imp.rationale || ""}`,
        status: "draft"
      });
      toast.success(`Created ${imp.new_variant_name}`);
      load();
    } catch (e) {
      console.error(e);
      toast.error("Failed to create variant");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {!campaign ? (
        <div>Loading...</div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">{campaign.campaign_name}</h1>
              <div className="text-gray-600">{campaign.brand} • {(campaign.platforms || []).join(", ")}</div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={exportPostsCSV}>
                <FileDown className="w-4 h-4 mr-2" /> Export Posts CSV
              </Button>
              <Button onClick={proposeImprovements} disabled={busy}>
                {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
                Propose Improvements
              </Button>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Ad Variants</CardTitle>
              <CardDescription>Edit metrics, mark winner, and iterate</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {(variants || []).map(v => (
                  <div key={v.id} className="border rounded-xl p-3">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{v.platform} • Variant {v.variant_name}</div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{v.status || "draft"}</Badge>
                        <Button size="sm" variant="outline" onClick={() => markWinner(v)} disabled={busy}>
                          <Trophy className="w-4 h-4 mr-1" /> Winner
                        </Button>
                      </div>
                    </div>
                    <div className="mt-2 text-sm">
                      <div className="font-medium">Headline</div>
                      <div className="text-gray-700">{v.headline}</div>
                      <div className="font-medium mt-2">Body</div>
                      <ReactMarkdown className="prose prose-sm max-w-none">{v.body}</ReactMarkdown>
                      {v.cta && <div className="text-xs text-gray-600 mt-1">CTA: {v.cta}</div>}
                    </div>
                    <div className="mt-3">
                      <AdMetricsEditor variant={v} onUpdated={load} />
                    </div>
                  </div>
                ))}
              </div>

              {proposal?.improvements?.length ? (
                <div className="border rounded-xl p-3">
                  <div className="font-medium mb-2">Proposed Improvements</div>
                  <div className="space-y-2">
                    {proposal.improvements.map((imp, i) => (
                      <div key={i} className="p-2 border rounded-lg">
                        <div className="text-sm font-medium">{imp.platform} • {imp.new_variant_name}</div>
                        <div className="text-xs text-gray-600 mb-1">{imp.rationale}</div>
                        <div className="text-xs"><span className="font-semibold">Headline:</span> {imp.headline}</div>
                        <div className="text-xs"><span className="font-semibold">CTA:</span> {imp.cta}</div>
                        <Button size="sm" className="mt-2" onClick={() => applyImprovement(imp)} disabled={busy}>Create Variant</Button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Performance Overview</CardTitle>
              <CardDescription>CTR/CVR/CPA across variants</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="CTR" fill="#10b981" />
                    <Bar dataKey="CVR" fill="#6366f1" />
                    <Bar dataKey="CPA" fill="#f59e0b" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Bulk Import Metrics</CardTitle>
              <CardDescription>Upload CSV to update variant metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <CSVImport campaignId={id} onApplied={load} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Organic Posting</CardTitle>
              <CardDescription>{posts.length} items</CardDescription>
            </CardHeader>
            <CardContent className="grid md:grid-cols-2 gap-3">
              {(posts || []).map(p => (
                <div key={p.id} className="border rounded-lg p-3">
                  <div className="text-xs text-gray-500">{p.platform} • {p.scheduled_time ? String(p.scheduled_time).slice(0,10) : ""}</div>
                  <div className="text-sm mt-1 font-medium">Content</div>
                  <ReactMarkdown className="prose prose-sm max-w-none">{p.content}</ReactMarkdown>
                  {p.media_idea && <div className="text-xs text-gray-600 mt-1">Media: {p.media_idea}</div>}
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
