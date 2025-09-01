import React from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkles, Rocket, Eye } from "lucide-react";

export default function TemplateCard({ template, onPreview, onDeploy }) {
  const { template_name, template_description, category, difficulty, estimated_duration, tags = [], success_rate = 100, usage_count = 0 } = template;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">{template_name}</CardTitle>
            <CardDescription>{template_description}</CardDescription>
          </div>
          <Badge variant="outline" className="capitalize">{category.replace(/_/g, " ")}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary" className="capitalize">{difficulty}</Badge>
            {estimated_duration && <Badge variant="secondary">{estimated_duration}</Badge>}
            <Badge variant="secondary">{success_rate}% success</Badge>
            <Badge variant="secondary">{usage_count} uses</Badge>
          </div>
          {tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {tags.slice(0, 4).map((t, i) => (
                <Badge key={i} variant="outline" className="text-xs">#{t}</Badge>
              ))}
              {tags.length > 4 && <Badge variant="outline" className="text-xs">+{tags.length - 4}</Badge>}
            </div>
          )}
        </div>

        <div className="mt-4 flex gap-2">
          <Button variant="outline" size="sm" onClick={() => onPreview?.(template)}>
            <Eye className="w-4 h-4 mr-2" />
            Preview
          </Button>
          <Button size="sm" onClick={() => onDeploy?.(template)} className="bg-emerald-900 hover:bg-emerald-800">
            <Rocket className="w-4 h-4 mr-2" />
            Deploy
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}