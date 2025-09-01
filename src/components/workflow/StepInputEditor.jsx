import React, { useEffect, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import KnowledgeSelector from "@/components/knowledge/KnowledgeSelector";
import { Plus, Trash2, FileText } from "lucide-react";

export default function StepInputEditor({ value = {}, onChange }) {
  const [pairs, setPairs] = useState(() => {
    const entries = Object.entries(value || {}).filter(([k]) => !["file_urls", "files", "context_files"].includes(k));
    return entries.length ? entries.map(([key, val]) => ({ key, val })) : [{ key: "", val: "" }];
  });
  const [selectedDocs, setSelectedDocs] = useState([]);

  const fileUrls = useMemo(() => {
    return selectedDocs
      .map((d) => (typeof d === "string" ? d : d.file_url))
      .filter(Boolean);
  }, [selectedDocs]);

  useEffect(() => {
    const obj = {};
    pairs.forEach(({ key, val }) => {
      if (String(key).trim().length > 0) obj[key] = val;
    });
    if (fileUrls.length > 0) obj.file_urls = fileUrls;
    onChange?.(obj);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairs, fileUrls]);

  const updatePair = (idx, field, v) => {
    const next = pairs.slice();
    next[idx] = { ...next[idx], [field]: v };
    setPairs(next);
  };

  const addPair = () => setPairs([...pairs, { key: "", val: "" }]);
  const removePair = (idx) => setPairs(pairs.filter((_, i) => i !== idx));

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <div className="text-sm font-medium text-gray-700">Input parameters</div>
        {pairs.map((row, idx) => (
          <div key={idx} className="flex gap-2">
            <Input
              placeholder="key"
              value={row.key}
              onChange={(e) => updatePair(idx, "key", e.target.value)}
              className="w-44"
            />
            <Input
              placeholder="value"
              value={row.val}
              onChange={(e) => updatePair(idx, "val", e.target.value)}
            />
            <Button variant="ghost" size="icon" onClick={() => removePair(idx)}>
              <Trash2 className="w-4 h-4 text-red-500" />
            </Button>
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={addPair}>
          <Plus className="w-4 h-4 mr-2" />
          Add parameter
        </Button>
      </div>

      <div className="space-y-2">
        <div className="text-sm font-medium text-gray-700">Attach knowledge (optional)</div>
        <KnowledgeSelector
          selectedDocuments={selectedDocs}
          onSelectionChange={setSelectedDocs}
          allowMultiple
          placeholder="Select documents to attach as context"
        />
        {fileUrls.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {fileUrls.map((u, i) => (
              <Badge key={i} variant="outline" className="text-xs">
                <FileText className="w-3 h-3 mr-1" />
                {u.split("/").slice(-1)[0]}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}