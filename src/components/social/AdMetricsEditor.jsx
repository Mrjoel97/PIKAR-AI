import React, { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
// import { SocialAdVariant } from "@/api/entities";
import { api } from '@/lib/api';
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

export default function AdMetricsEditor({ variant, onUpdated }) {
  const [form, setForm] = useState({
    spend: variant?.metrics?.spend || "",
    impressions: variant?.metrics?.impressions || "",
    clicks: variant?.metrics?.clicks || "",
    conversions: variant?.metrics?.conversions || "",
  });
  const [saving, setSaving] = useState(false);

  const computed = useMemo(() => {
    const impressions = Number(form.impressions) || 0;
    const clicks = Number(form.clicks) || 0;
    const conversions = Number(form.conversions) || 0;
    const spend = Number(form.spend) || 0;

    const ctr = impressions > 0 ? +(100 * (clicks / impressions)).toFixed(2) : 0;
    const cvr = clicks > 0 ? +(100 * (conversions / clicks)).toFixed(2) : 0;
    const cpa = conversions > 0 ? +(spend / conversions).toFixed(2) : 0;

    return { ctr, cvr, cpa };
  }, [form]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        metrics: {
          spend: Number(form.spend) || 0,
          impressions: Number(form.impressions) || 0,
          clicks: Number(form.clicks) || 0,
          conversions: Number(form.conversions) || 0,
          ctr: computed.ctr,
          cvr: computed.cvr,
          cpa: computed.cpa,
        }
      };
      await api.updateAdVariant(variant.id, payload);
      toast.success("Metrics updated");
      onUpdated?.();
    } catch (e) {
      console.error(e);
      toast.error("Failed updating metrics");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Input placeholder="Spend" value={form.spend} onChange={(e) => setForm(f => ({...f, spend: e.target.value}))} />
        <Input placeholder="Impressions" value={form.impressions} onChange={(e) => setForm(f => ({...f, impressions: e.target.value}))} />
        <Input placeholder="Clicks" value={form.clicks} onChange={(e) => setForm(f => ({...f, clicks: e.target.value}))} />
        <Input placeholder="Conversions" value={form.conversions} onChange={(e) => setForm(f => ({...f, conversions: e.target.value}))} />
      </div>
      <div className="flex items-center gap-2 text-xs">
        <Badge variant="outline">CTR: {computed.ctr}%</Badge>
        <Badge variant="outline">CVR: {computed.cvr}%</Badge>
        <Badge variant="outline">CPA: ${computed.cpa}</Badge>
      </div>
      <Button size="sm" onClick={handleSave} disabled={saving}>
        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
        Save Metrics
      </Button>
    </div>
  );
}