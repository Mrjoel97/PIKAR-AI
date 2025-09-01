import React, { useEffect, useMemo, useState } from "react";
import { SocialCampaign } from "@/api/entities";
import { SocialAdVariant } from "@/api/entities";
import { SocialPost } from "@/api/entities";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { createPageUrl } from "@/utils";
import { Megaphone, Plus, Search } from "lucide-react";

export default function SocialCampaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [counts, setCounts] = useState({});
  const [q, setQ] = useState("");

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    const list = await SocialCampaign.list("-updated_date", 100);
    setCampaigns(list || []);
    // counts
    const map = {};
    for (const c of list || []) {
      const variants = await SocialAdVariant.filter({ campaign_id: c.id });
      const posts = await SocialPost.filter({ campaign_id: c.id });
      map[c.id] = { variants: (variants || []).length, posts: (posts || []).length };
    }
    setCounts(map);
  };

  const filtered = useMemo(() => {
    const text = q.toLowerCase();
    return (campaigns || []).filter(c =>
      (c.campaign_name || "").toLowerCase().includes(text) ||
      (c.brand || "").toLowerCase().includes(text) ||
      (c.objective || "").toLowerCase().includes(text)
    );
  }, [campaigns, q]);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Megaphone className="w-6 h-6 text-emerald-700" />
          <h1 className="text-2xl font-bold">Social Campaigns</h1>
        </div>
        <Link to={createPageUrl("SocialMediaMarketing")}>
          <Button><Plus className="w-4 h-4 mr-2" />New Campaign</Button>
        </Link>
      </div>

      <div className="flex items-center gap-2">
        <Search className="w-4 h-4 text-gray-400" />
        <Input placeholder="Search campaigns..." value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(c => (
          <Card key={c.id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{c.campaign_name}</CardTitle>
              <CardDescription>{c.brand} • {c.objective}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-sm text-gray-600">
                Platforms: {(c.platforms || []).join(", ") || "—"}
              </div>
              <div className="flex gap-2">
                <Badge variant="outline">{counts[c.id]?.variants || 0} variants</Badge>
                <Badge variant="outline">{counts[c.id]?.posts || 0} posts</Badge>
                <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200">{c.status || "draft"}</Badge>
              </div>
              <Link to={createPageUrl(`SocialCampaignDetails?id=${c.id}`)}>
                <Button variant="outline" className="mt-2 w-full">Open</Button>
              </Link>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <Card><CardContent className="p-6 text-sm text-gray-600">No campaigns yet.</CardContent></Card>
        )}
      </div>
    </div>
  );
}