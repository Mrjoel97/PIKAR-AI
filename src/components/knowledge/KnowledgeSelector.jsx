import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { KnowledgeBaseDocument } from "@/api/entities";
import { Search, X } from "lucide-react";

export default function KnowledgeSelector({
  onSelectionChange,
  selectedDocuments = [],
  allowMultiple = true,
  filterCategory = "all"
}) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState(filterCategory || "all");

  useEffect(() => {
    (async () => {
      setLoading(true);
      const list = await KnowledgeBaseDocument.list("-updated_date", 100);
      setDocs(list || []);
      setLoading(false);
    })();
  }, []);

  useEffect(() => {
    if (filterCategory && filterCategory !== "all") {
      setCategory(filterCategory);
    }
  }, [filterCategory]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return (docs || []).filter((d) => {
      const matchQ =
        !q ||
        (d.document_name || "").toLowerCase().includes(q) ||
        (d.description || "").toLowerCase().includes(q) ||
        (Array.isArray(d.tags) && d.tags.some((t) => (t || "").toLowerCase().includes(q)));
      const matchC = category === "all" || d.document_category === category;
      return matchQ && matchC;
    });
  }, [docs, query, category]);

  const isSelected = (doc) => selectedDocuments.some((s) => s.id === doc.id);

  const toggleSelect = (doc) => {
    let next = [];
    if (allowMultiple) {
      if (isSelected(doc)) {
        next = selectedDocuments.filter((s) => s.id !== doc.id);
      } else {
        next = [...selectedDocuments, doc];
      }
    } else {
      next = isSelected(doc) ? [] : [doc];
    }
    onSelectionChange?.(next);
  };

  const removeSelected = (docId) => {
    onSelectionChange?.(selectedDocuments.filter((s) => s.id !== docId));
  };

  return (
    <Card className="border-emerald-100">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-emerald-900 text-base">Attach Knowledge</CardTitle>
            <CardDescription className="text-emerald-700">
              Select documents to pass as context to the agent
            </CardDescription>
          </div>
          {loading && <span className="text-xs text-gray-500">Loading...</span>}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              placeholder="Search documents..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-8"
            />
          </div>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="all">All categories</option>
            <option value="strategic">Strategic</option>
            <option value="financial">Financial</option>
            <option value="marketing">Marketing</option>
            <option value="operations">Operations</option>
            <option value="compliance">Compliance</option>
            <option value="hr">HR</option>
            <option value="technical">Technical</option>
            <option value="general">General</option>
          </select>
        </div>

        {selectedDocuments.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedDocuments.map((doc) => (
              <Badge key={doc.id} variant="outline" className="flex items-center gap-1">
                {doc.document_name}
                <button onClick={() => removeSelected(doc.id)} className="ml-1 hover:opacity-80">
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}

        <div className="max-h-56 overflow-auto rounded-lg border">
          {filtered.length === 0 ? (
            <div className="text-sm text-gray-500 p-3">No documents found.</div>
          ) : (
            <ul className="divide-y">
              {filtered.map((doc) => (
                <li key={doc.id} className="flex items-center justify-between p-3 hover:bg-gray-50">
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{doc.document_name}</div>
                    <div className="text-xs text-gray-500 truncate">
                      {(doc.description || "").slice(0, 100)}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {Array.isArray(doc.tags) &&
                        doc.tags.slice(0, 4).map((t, i) => (
                          <Badge key={i} variant="secondary" className="text-[10px]">
                            #{t}
                          </Badge>
                        ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {doc.document_category && (
                      <Badge variant="outline" className="capitalize">
                        {String(doc.document_category).replace(/_/g, " ")}
                      </Badge>
                    )}
                    <Button
                      variant={isSelected(doc) ? "outline" : "default"}
                      size="sm"
                      onClick={() => toggleSelect(doc)}
                    >
                      {isSelected(doc) ? "Remove" : "Add"}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}