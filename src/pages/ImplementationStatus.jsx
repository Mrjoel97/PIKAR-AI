
import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Clock, AlertTriangle, Play, Route, Network, FilePlus2 } from "lucide-react";
import { Link } from "react-router-dom";
import { createPageUrl } from "@/utils";

const completed = [
  { name: "WorkflowExecutor (run, cancel, rerunFailed, runStep, retries, timeouts)", id: "exec" },
  { name: "Template Gallery (search, preview, one-click deploy)", id: "gallery" },
  { name: "Create Workflow (drag & drop builder, dry run, save/publish)", id: "create" },
  { name: "Seeded 9 Curated Workflow Templates", id: "seed" },
  { name: "Workflow Details (controls, progress, live polling, history)", id: "details" },
  { name: "Knowledge Selector (attach KB docs to steps)", id: "knowledge" },
  { name: "Automated tests and CI validation pipeline (linting, security, contracts)", id: "tests" }
];

const pending = [
  { name: "Manual cleanup of duplicate WorkflowTemplate records (Dashboard → Data)", id: "cleanup" },
  { name: "Advanced logs viewer (streaming and filtering)", id: "logs" }
];

export default function ImplementationStatus() {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-bold">Implementation Status</h1>
        <p className="text-gray-600">
          Summary of completed tasks and remaining items for the workflow engine and templates.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
            Completed
          </CardTitle>
          <CardDescription>Shipped features available for testing</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {completed.map((item) => (
            <div key={item.id} className="flex items-center justify-between p-3 border rounded-xl">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                <span>{item.name}</span>
              </div>
              <Badge variant="outline" className="border-green-300 text-green-800 bg-green-50">done</Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-yellow-600" />
            Pending / Not Implemented
          </CardTitle>
          <CardDescription>Items still to be addressed</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {pending.map((item) => (
            <div key={item.id} className="flex items-center justify-between p-3 border rounded-xl">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-600" />
                <span>{item.name}</span>
              </div>
              <Badge variant="secondary">todo</Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quick Testing Links</CardTitle>
          <CardDescription>Open key pages from the sidebar or use these shortcuts</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Link to={createPageUrl("Orchestrate")}>
            <Button variant="outline"><Network className="w-4 h-4 mr-2" />Orchestrate</Button>
          </Link>
          <Link to={createPageUrl("CreateWorkflow")}>
            <Button variant="outline"><Route className="w-4 h-4 mr-2" />Create Workflow</Button>
          </Link>
          <Link to={createPageUrl("CreateWorkflow")}>
            <Button><FilePlus2 className="w-4 h-4 mr-2" />Build New Workflow</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
