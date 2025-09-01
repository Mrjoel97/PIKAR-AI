import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Shield, FileCheck2 } from "lucide-react";

export default function TestResultCard({ result }) {
  const { name, category, success, details } = result || {};
  const color = success ? "bg-green-100 text-green-800 border-green-200" : "bg-red-100 text-red-800 border-red-200";
  const Icon = success ? CheckCircle2 : XCircle;

  const catBadge = {
    contract: "bg-blue-100 text-blue-800 border-blue-200",
    data: "bg-purple-100 text-purple-800 border-purple-200",
    security: "bg-yellow-100 text-yellow-800 border-yellow-200",
    lint: "bg-gray-100 text-gray-800 border-gray-200",
    crud: "bg-emerald-100 text-emerald-800 border-emerald-200"
  }[category] || "bg-gray-100 text-gray-800 border-gray-200";

  return (
    <Card className="border rounded-xl">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 ${success ? "text-green-600" : "text-red-600"}`} />
            <div className="font-medium">{name}</div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={catBadge}>{category}</Badge>
            <Badge className={color}>{success ? "pass" : "fail"}</Badge>
          </div>
        </div>
        {details && (
          <div className="text-xs text-gray-600 mt-2 whitespace-pre-wrap">
            {details}
          </div>
        )}
      </CardContent>
    </Card>
  );
}