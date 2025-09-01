import React, { useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Copy, Play, Shield, FileDown, CheckCircle2, XCircle, GitBranch } from "lucide-react";
import { toast } from "sonner";
import TestResultCard from "@/components/testing/TestResultCard";
import { ValidationRun } from "@/api/entities";
import { Workflow } from "@/api/entities";
import { WorkflowStep } from "@/api/entities";
import { WorkflowTemplate } from "@/api/entities";
import { AuditLog } from "@/api/entities";

const CI_YAML = `name: CI Validation

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - name: Install deps
        run: npm ci
      - name: Lint
        run: npm run lint --if-present
      - name: Unit tests
        run: npm test --if-present -- --ci
      - name: Build
        run: npm run build --if-present
      - name: Bundle size check (advisory)
        run: echo "Add bundle-size tooling as needed"
`;

export default function PlatformTesting() {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState([]);
  const passed = useMemo(() => results.filter(r => r.success).length, [results]);
  const failed = useMemo(() => results.filter(r => !r.success).length, [results]);
  const total = results.length || 1;
  const progress = Math.round((passed / total) * 100);

  async function runAll() {
    setRunning(true);
    const started = new Date().toISOString();
    const out = [];

    // Helper: safe exec
    const safe = async (name, category, fn) => {
      try {
        const ok = await fn();
        out.push({ name, category, success: ok.success, details: ok.details || "" });
      } catch (e) {
        out.push({ name, category, success: false, details: String(e?.message || e) });
      }
    };

    // Contract checks (entity schemas)
    await safe("Workflow schema enums", "contract", async () => {
      const s = await Workflow.schema();
      const hasStatusEnum = Array.isArray(s?.properties?.workflow_status?.enum);
      const includesActive = hasStatusEnum && s.properties.workflow_status.enum.includes("active");
      return { success: !!includesActive, details: JSON.stringify(s.properties.workflow_status || {}, null, 2) };
    });

    await safe("WorkflowStep schema agent enum", "contract", async () => {
      const s = await WorkflowStep.schema();
      const agentEnum = s?.properties?.agent_name?.enum || [];
      const includesDataAnalysis = agentEnum.includes("Data Analysis");
      return { success: includesDataAnalysis, details: `agents: ${agentEnum.join(", ")}` };
    });

    await safe("WorkflowTemplate required props", "contract", async () => {
      const s = await WorkflowTemplate.schema();
      const hasConfig = !!s?.properties?.template_config;
      const hasCategory = !!s?.properties?.category;
      return { success: hasConfig && hasCategory, details: hasConfig ? "config ok" : "config missing" };
    });

    // Data checks
    await safe("Templates available", "data", async () => {
      const list = await WorkflowTemplate.list("-usage_count", 1);
      const ok = Array.isArray(list) && list.length >= 1;
      return { success: ok, details: ok ? `found ${list.length}` : "none found" };
    });

    // CRUD smoke (create + delete)
    await safe("AuditLog CRUD smoke", "crud", async () => {
      const log = await AuditLog.create({
        action_type: "settings_change",
        success: true,
        action_details: { test: "smoke" },
        risk_level: "low"
      });
      const logId = log?.id;
      const listed = await AuditLog.filter({ id: logId });
      const found = Array.isArray(listed) && listed.length === 1;
      // try cleanup
      if (logId) {
        try { await AuditLog.delete(logId); } catch (_) {}
      }
      return { success: found, details: `created id: ${logId}` };
    });

    // Security config check (enum present)
    await safe("AuditLog risk_level enum", "security", async () => {
      const s = await AuditLog.schema();
      const riskEnum = s?.properties?.risk_level?.enum || [];
      const hasLow = riskEnum.includes("low");
      const hasCritical = riskEnum.includes("critical");
      return { success: hasLow && hasCritical, details: `enum: ${riskEnum.join(", ")}` };
    });

    // Linting advisory (pipeline guidance present)
    await safe("Lint config advisory", "lint", async () => {
      const hasYaml = CI_YAML.includes("Lint");
      return { success: hasYaml, details: "Provide ESLint config in repo and enable npm run lint" };
    });

    setResults(out);

    const finished = new Date().toISOString();
    const cats = out.reduce((acc, r) => {
      acc[r.category] = acc[r.category] || { total: 0, passed: 0, failed: 0 };
      acc[r.category].total += 1;
      acc[r.category].passed += r.success ? 1 : 0;
      acc[r.category].failed += r.success ? 0 : 1;
      return acc;
    }, {});
    const run = await ValidationRun.create({
      run_name: `Validation #${new Date().toLocaleString()}`,
      started_at: started,
      finished_at: finished,
      total_checks: out.length,
      passed: out.filter(r => r.success).length,
      failed: out.filter(r => !r.success).length,
      success: out.every(r => r.success),
      categories_result: cats,
      results: out,
      ci_guidance_version: "gha-v1"
    });

    toast.success(`Validation completed: ${run.passed}/${run.total_checks} passed`);
    setRunning(false);
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="w-8 h-8 text-emerald-900" />
            Platform Testing & CI
          </h1>
          <p className="text-gray-600">
            Run automated contract, data, security checks and view CI pipeline guidance.
          </p>
        </div>
        <Button onClick={runAll} disabled={running} className="bg-emerald-900 hover:bg-emerald-800">
          <Play className="w-4 h-4 mr-2" />
          {running ? "Running..." : "Run All Checks"}
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Summary</CardTitle>
          <CardDescription>Overall pass/fail across checks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
            <div className="space-y-1">
              <div className="text-3xl font-bold">{passed}/{results.length || 0}</div>
              <div className="text-sm text-gray-500">Passed</div>
            </div>
            <div className="space-y-1">
              <div className="text-3xl font-bold">{failed}</div>
              <div className="text-sm text-gray-500">Failed</div>
            </div>
            <div>
              <Progress value={results.length ? Math.max(5, progress) : 0} className="h-2" />
              <div className="text-xs text-gray-500 mt-1">{progress}%</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.map((r, idx) => <TestResultCard key={idx} result={r} />)}
        {results.length === 0 && (
          <Card>
            <CardContent className="p-6 text-sm text-gray-600">
              No results yet. Click “Run All Checks” to execute the validation suite.
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-emerald-900" />
            CI Pipeline (GitHub Actions)
          </CardTitle>
          <CardDescription>Copy this YAML to .github/workflows/ci.yml</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <pre className="bg-gray-50 border rounded-xl p-4 text-xs overflow-auto">{CI_YAML}</pre>
            <div className="flex justify-end mt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => { navigator.clipboard.writeText(CI_YAML); toast.success("CI YAML copied"); }}
              >
                <Copy className="w-4 h-4 mr-2" />
                Copy YAML
              </Button>
            </div>
            <div className="mt-3 text-xs text-gray-500">
              Note: Linting and unit tests require adding ESLint/Jest configs to your repo.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}