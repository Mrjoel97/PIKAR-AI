import React from "react";
import { Link } from "react-router-dom";
import { createPageUrl } from "@/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Target, BarChart, Users, PenSquare, Wand2, Megaphone } from "lucide-react";

export default function MarketingSuite() {
  const modules = [
    {
      title: "Campaign Orchestration",
      desc: "Plan, execute, and monitor multi-channel campaigns with AI assistance.",
      link: createPageUrl("MarketingAutomation"),
      cta: "Open Campaign Planner",
      icon: Target,
      status: "available"
    },
    {
      title: "Content Creation",
      desc: "Generate multi-format assets (email, social, landing copy) aligned to brand voice.",
      link: createPageUrl("ContentCreation"),
      cta: "Create Content",
      icon: PenSquare,
      status: "available"
    },
    {
      title: "Sales Intelligence Bridge",
      desc: "Align campaigns with enterprise accounts and deals for tighter GTM.",
      link: createPageUrl("SalesIntelligence"),
      cta: "Analyze Leads",
      icon: Users,
      status: "available"
    },
    {
      title: "Performance & Attribution",
      desc: "Dashboards, KPI tracking, and ROI narratives for each campaign.",
      link: createPageUrl("Reporting"),
      cta: "Open Reporting",
      icon: BarChart,
      status: "available"
    },
    {
      title: "Social Media Marketing",
      desc: "Automate paid + organic social campaigns with A/B testing and iteration.",
      link: createPageUrl("SocialMediaMarketing"),
      cta: "Open Social Suite",
      icon: Megaphone,
      status: "available"
    },
    {
      title: "Social Campaigns",
      desc: "Manage campaigns, edit metrics, import CSVs, and review results.",
      link: createPageUrl("SocialCampaigns"),
      cta: "Manage Campaigns",
      icon: Megaphone,
      status: "available"
    }
  ];

  const planned = [
    { title: "Personas", desc: "Centralized ICP/persona profiles that guide copy, channels, and offers." },
    { title: "Audience Segmentation", desc: "Smart cohorts by behavior, firmographics, and intent signals." },
    { title: "Customer Journeys", desc: "Drag-and-drop journey builder with channel touchpoints and SLAs." },
    { title: "Experiments (A/B/n)", desc: "Hypothesis-driven tests with automated analysis and guardrails." },
    { title: "Content Calendar", desc: "Editorial planning with asset reuse, approvals, and dependencies." }
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <header className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
          <Sparkles className="w-4 h-4" />
          AI-Powered Marketing Suite
        </div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-900 to-emerald-700 bg-clip-text text-transparent">
          Orchestrate high-impact marketing with specialized agents
        </h1>
        <p className="text-gray-600 max-w-3xl mx-auto">
          A cohesive suite that turns briefs into multi-channel execution, content assets, experiments, and measurable ROI.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-emerald-100">
          <CardHeader>
            <CardTitle className="text-emerald-900">What this suite provides</CardTitle>
            <CardDescription className="text-emerald-700">
              Understanding from docs and current capabilities
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-gray-700">
            <ul className="list-disc ml-5 space-y-2">
              <li>Specialized agents collaborate: Marketing Automation, Content Creation, Sales Intelligence, and Analytics.</li>
              <li>Enterprise-grade planning: goals, audience, channels, and timelines with AI scaffolding.</li>
              <li>Asset generation aligned to brand tone with knowledge-base grounding.</li>
              <li>Closed-loop measurement: KPIs, ROI narratives, and executive-ready summaries.</li>
            </ul>
          </CardContent>
        </Card>

        <Card className="border-emerald-100">
          <CardHeader>
            <CardTitle className="text-emerald-900">Strategic implementation plan</CardTitle>
            <CardDescription className="text-emerald-700">Phased rollout for maximum UX</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-gray-700">
            <ol className="list-decimal ml-5 space-y-2">
              <li>Unify campaign planning and content creation with a shared brief and knowledge attachments.</li>
              <li>Add Personas and Segments to personalize prompts, copy, and channel mix.</li>
              <li>Introduce Journey Builder to map touchpoints and SLAs; connect to experiments.</li>
              <li>Ship Experiments (A/B/n) with guardrails and automatic result reads.</li>
              <li>Enhance Reporting with attribution views and budget pacing alerts.</li>
            </ol>
          </CardContent>
        </Card>
      </div>

      <Card className="border-emerald-100">
        <CardHeader>
          <CardTitle className="text-emerald-900">Launch modules</CardTitle>
          <CardDescription className="text-emerald-700">Jump into production-ready features</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {modules.map((m, idx) => {
            const Icon = m.icon;
            return (
              <Card key={idx} className="hover:shadow-pop transition-all">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="p-2 bg-emerald-50 rounded-xl">
                      <Icon className="w-5 h-5 text-emerald-700" />
                    </div>
                    <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">Available</Badge>
                  </div>
                  <CardTitle className="text-base mt-2">{m.title}</CardTitle>
                  <CardDescription>{m.desc}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Link to={m.link}>
                    <Button className="w-full bg-emerald-900 hover:bg-emerald-800">
                      <Wand2 className="w-4 h-4 mr-2" />
                      {m.cta}
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            );
          })}
        </CardContent>
      </Card>

      <Card className="border-emerald-100">
        <CardHeader>
          <CardTitle className="text-emerald-900">Upcoming modules</CardTitle>
          <CardDescription className="text-emerald-700">Planned for the next iterations</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {planned.map((p, idx) => (
            <Card key={idx} className="border-dashed">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{p.title}</CardTitle>
                  <Badge className="bg-gray-100 text-gray-800 border-gray-200">Planned</Badge>
                </div>
                <CardDescription>{p.desc}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}