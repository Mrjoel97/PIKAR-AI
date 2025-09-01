import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { UploadFile, ExtractDataFromUploadedFile } from "@/api/integrations";
import { SocialAdVariant } from "@/api/entities";
import { Loader2, Upload } from "lucide-react";
import { toast } from "sonner";

const MetricsSchema = {
  type: "array",
  items: {
    type: "object",
    properties: {
      platform: { type: "string" },
      variant_name: { type: "string" },
      spend: { type: "number" },
      impressions: { type: "number" },
      clicks: { type: "number" },
      conversions: { type: "number" }
    },
    required: ["platform", "variant_name"]
  }
};

export default function CSVImport({ campaignId, onApplied }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState([]);

  const handleUpload = async () => {
    if (!file) {
      toast.error("Please choose a CSV file.");
      return;
    }
    setBusy(true);
    try {
      const { file_url } = await UploadFile({ file });
      const res = await ExtractDataFromUploadedFile({ file_url, json_schema: MetricsSchema });
      if (res.status !== "success") {
        toast.error("Failed to parse CSV");
        setBusy(false);
        return;
      }
      const data = Array.isArray(res.output) ? res.output : [];
      setRows(data);
      toast.success(`Parsed ${data.length} rows`);
    } catch (e) {
      console.error(e);
      toast.error("Upload/parse failed");
    } finally {
      setBusy(false);
    }
  };

  const applyRows = async () => {
    if (!rows.length) return;
    setBusy(true);
    try {
      const variants = await SocialAdVariant.filter({ campaign_id: campaignId });
      const key = (v) => `${(v.platform || "").toLowerCase()}::${(v.variant_name || "").toLowerCase()}`;
      const byKey = new Map((variants || []).map(v => [key(v), v]));
      let updated = 0;

      for (const r of rows) {
        const k = `${String(r.platform || "").toLowerCase()}::${String(r.variant_name || "").toLowerCase()}`;
        const v = byKey.get(k);
        if (!v) continue;

        const impressions = Number(r.impressions) || 0;
        const clicks = Number(r.clicks) || 0;
        const conversions = Number(r.conversions) || 0;
        const spend = Number(r.spend) || 0;
        const ctr = impressions > 0 ? +(100 * (clicks / impressions)).toFixed(2) : 0;
        const cvr = clicks > 0 ? +(100 * (conversions / clicks)).toFixed(2) : 0;
        const cpa = conversions > 0 ? +(spend / conversions).toFixed(2) : 0;

        await SocialAdVariant.update(v.id, {
          metrics: { impressions, clicks, conversions, spend, ctr, cvr, cpa }
        });
        updated += 1;
      }

      toast.success(`Applied metrics to ${updated} variants`);
      onApplied?.();
    } catch (e) {
      console.error(e);
      toast.error("Failed applying metrics");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-2">
        <div className="text-sm text-gray-700">
          Import performance metrics via CSV. Required columns: platform, variant_name, spend, impressions, clicks, conversions.
        </div>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0])}
          className="block text-sm"
        />
        <div className="flex gap-2">
          <Button onClick={handleUpload} disabled={busy || !file}>
            {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
            Upload & Parse
          </Button>
          <Button variant="outline" onClick={applyRows} disabled={busy || !rows.length}>
            Apply to Variants
          </Button>
        </div>
        {!!rows.length && (
          <div className="text-xs text-gray-500">Ready rows: {rows.length}</div>
        )}
      </CardContent>
    </Card>
  );
}