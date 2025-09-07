import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery, useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Separator } from "@/components/ui/separator";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
type Business = {
  _id: string;
  name: string;
  tier: "solopreneur" | "startup" | "sme" | "enterprise";
  industry: string;
};

export default function BusinessPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated } = useAuth();

  const userBusinesses = useQuery(api.businesses.getUserBusinesses, {});
  const createBusiness = useMutation(api.businesses.create);
  const reportIncident = useMutation(api.workflows.reportIncident);
  const logNonconformity = useMutation(api.workflows.logNonconformity);
  const approveRunStep = useMutation(api.workflows.approveRunStep);

  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedBusinessId && (userBusinesses?.length || 0) > 0) {
      setSelectedBusinessId(userBusinesses![0]._id);
    }
  }, [selectedBusinessId, userBusinesses]);

  if (authLoading) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="animate-pulse h-8 w-40 rounded bg-muted mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-28 rounded-lg bg-muted" />
          <div className="h-28 rounded-lg bg-muted" />
          <div className="h-28 rounded-lg bg-muted" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-6">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle>Welcome</CardTitle>
            <CardDescription>Sign in to manage your business.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasBusinesses = (userBusinesses?.length || 0) > 0;
  // Use inferred types from Convex and avoid strict local typing here
  const selectedBusiness = userBusinesses?.find((b) => b._id === selectedBusinessId);

  const complianceChecks = useQuery(
    api.workflows.listComplianceChecks,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : "skip"
  );
  const auditLogs = useQuery(
    api.workflows.listAuditLogs,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : "skip"
  );
  const initiatives = useQuery(
    api.initiatives.getByBusiness,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : "skip"
  );
  const incidents = useQuery(
    api.workflows.listIncidents,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : "skip"
  );
  const nonconformities = useQuery(
    api.workflows.listNonconformities,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : "skip"
  );
  const approvals = useQuery(
    api.workflows.listPendingApprovals,
    selectedBusinessId ? ({ businessId: selectedBusinessId, limit: 20 } as any) : "skip"
  );

  const handleQuickCreateBusiness = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const name = String(fd.get("name") || "").trim();
    const industry = String(fd.get("industry") || "").trim();
    const tier = (String(fd.get("tier") || "startup") as Business["tier"]);
    if (!name || !industry) {
      toast("Please provide a name and industry.");
      return;
    }
    try {
      const id = await createBusiness({
        name,
        tier,
        industry,
        description: undefined,
        website: undefined,
      } as any);
      toast("Business created");
      setSelectedBusinessId(id as any);
    } catch (err: any) {
      toast(err?.message || "Failed to create business");
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Business</h1>
        <p className="text-sm text-muted-foreground">Manage your business profile.</p>
      </div>

      {!userBusinesses ? (
        <Card className="bg-white">
          <CardContent className="p-6">
            <div className="animate-pulse h-6 w-44 rounded bg-muted" />
          </CardContent>
        </Card>
      ) : !hasBusinesses ? (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle>Create your first business</CardTitle>
            <CardDescription>Get started by creating a business profile.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleQuickCreateBusiness} className="grid grid-cols-1 md:grid-cols-5 gap-3">
              <Input name="name" placeholder="Business name" className="md:col-span-2" />
              <Input name="industry" placeholder="Industry" className="md:col-span-2" />
              <Select name="tier" defaultValue="startup" onValueChange={() => {}}>
                <SelectTrigger><SelectValue placeholder="Tier" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="solopreneur">Solopreneur</SelectItem>
                  <SelectItem value="startup">Startup</SelectItem>
                  <SelectItem value="sme">SME</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                </SelectContent>
              </Select>
              <div className="md:col-span-5 flex gap-2">
                <Button type="submit">Create</Button>
                <Button type="button" variant="outline" onClick={() => navigate("/onboarding")}>
                  Use guided onboarding
                </Button>
              </div>
            </form>
          </CardContent>

        </Card>
      ) : (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle>Business</CardTitle>
            <CardDescription>{selectedBusiness?.name}</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-1">
            <div>Tier: <span className="text-foreground font-medium">{selectedBusiness?.tier}</span></div>
            <div>Industry: <span className="text-foreground font-medium">{selectedBusiness?.industry}</span></div>
          </CardContent>
        </Card>
      )}

      {hasBusinesses && selectedBusiness && (
        <div className="mt-6">
          <Tabs defaultValue="crm" className="space-y-4">
            <TabsList>
              <TabsTrigger value="crm">CRM/Sales</TabsTrigger>
              <TabsTrigger value="compliance">Compliance/QMS</TabsTrigger>
            </TabsList>

            <TabsContent value="crm" className="space-y-3">
              {Array.isArray(initiatives) && initiatives.length > 0 ? (
                initiatives.map((i: any) => (
                  <Card key={i._id}>
                    <CardHeader>
                      <CardTitle className="text-base">{i.name || i.title || "Initiative"}</CardTitle>
                      <CardDescription>Status: {i.status || "active"}</CardDescription>
                    </CardHeader>
                  </Card>
                ))
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>No pipeline items</CardTitle>
                    <CardDescription>Create an initiative to get started.</CardDescription>
                  </CardHeader>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="compliance" className="space-y-3">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Approval Queue</CardTitle>
                  <CardDescription>Steps awaiting your approval</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Array.isArray(approvals) && approvals.length > 0 ? (
                      approvals.map((p: any) => (
                        <div key={p.runStepId} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <div className="font-medium">{p.workflowName} • {p.stepTitle}</div>
                            <div className="text-xs text-muted-foreground">Started {new Date(p.startedAt).toLocaleString()}</div>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={async () => {
                              try {
                                await approveRunStep({ runStepId: p.runStepId, approved: false, note: "Rejected" } as any);
                                toast("Step rejected");
                              } catch (e: any) { toast(e?.message || "Failed"); }
                            }}>Reject</Button>
                            <Button size="sm" onClick={async () => {
                              try {
                                await approveRunStep({ runStepId: p.runStepId, approved: true, note: "Approved" } as any);
                                toast("Step approved");
                              } catch (e: any) { toast(e?.message || "Failed"); }
                            }}>Approve</Button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-muted-foreground">No items awaiting approval.</div>
                    )}
                  </div>
                </CardContent>
              </Card>


              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Quick QMS Actions</CardTitle>
                  <CardDescription>Log incidents and nonconformities</CardDescription>
                </CardHeader>
                <CardContent>
                  <form className="grid grid-cols-1 md:grid-cols-6 gap-2" onSubmit={async (e) => {
                    e.preventDefault();
                    if (!selectedBusinessId) return;
                    const fd = new FormData(e.currentTarget);
                    const type = String(fd.get("inc_type") || "").trim() || "process";
                    const desc = String(fd.get("inc_desc") || "").trim();
                    const sev = String(fd.get("inc_sev") || "medium") as any;
                    if (!desc) { toast("Provide incident description"); return; }
                    try {
                      await reportIncident({ businessId: selectedBusinessId as any, reportedBy: (selectedBusiness as any)?.ownerId, type, description: desc, severity: sev });
                      toast("Incident reported (CAPA will be created)");
                      (e.currentTarget as any).reset();
                    } catch (err: any) {
                      toast(err?.message || "Failed to report incident");
                    }
                  }}>
                    <Input name="inc_type" placeholder="Incident type" className="md:col-span-1" />
                    <Input name="inc_desc" placeholder="Incident description" className="md:col-span-4" />
                    <Select name="inc_sev" defaultValue="medium" onValueChange={() => {}}>
                      <SelectTrigger className="md:col-span-1"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                    <div className="md:col-span-6"><Button type="submit" size="sm">Log Incident</Button></div>
                  </form>
                  <Separator className="my-3" />
                  <form className="grid grid-cols-1 md:grid-cols-6 gap-2" onSubmit={async (e) => {
                    e.preventDefault();
                    if (!selectedBusinessId) return;
                    const fd = new FormData(e.currentTarget);
                    const desc = String(fd.get("nc_desc") || "").trim();
                    const sev = String(fd.get("nc_sev") || "medium") as any;
                    if (!desc) { toast("Provide nonconformity description"); return; }
                    try {
                      await logNonconformity({ businessId: selectedBusinessId as any, createdBy: (selectedBusiness as any)?.ownerId, description: desc, severity: sev, autoCapa: true } as any);
                      toast("Nonconformity logged (CAPA will be created)");
                      (e.currentTarget as any).reset();
                    } catch (err: any) {
                      toast(err?.message || "Failed to log nonconformity");
                    }
                  }}>
                    <Input name="nc_desc" placeholder="Nonconformity description" className="md:col-span-5" />
                    <Select name="nc_sev" defaultValue="medium" onValueChange={() => {}}>
                      <SelectTrigger className="md:col-span-1"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                    <div className="md:col-span-6"><Button type="submit" size="sm">Log Nonconformity</Button></div>
                  </form>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Incidents</CardTitle>
                  <CardDescription>Most recent incidents</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Array.isArray(incidents) && incidents.length > 0 ? (
                      incidents.slice(0, 10).map((i: any) => (
                        <div key={i._id} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <div className="font-medium">{i.type} • {i.severity}</div>
                            <div className="text-xs text-muted-foreground">{new Date(i._creationTime).toLocaleString()}</div>
                            <div className="text-xs line-clamp-1">{i.description}</div>
                          </div>
                          {i.correctiveWorkflowId && (
                            <div className="text-xs text-muted-foreground">CAPA linked</div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-muted-foreground">No incidents logged.</div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Compliance Scans</CardTitle>
                  <CardDescription>Recent automated compliance checks</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Array.isArray(complianceChecks) && complianceChecks.length > 0 ? (
                      complianceChecks.map((c: any) => (
                        <div key={c._id} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <div className="font-medium">{c.subjectType} • {c.status}</div>
                            <div className="text-xs text-muted-foreground">{new Date(c._creationTime).toLocaleString()} • Score: {c.score ?? "-"}</div>
                          </div>
                          <div className="text-xs">{(c.flags || []).length} flags</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-muted-foreground">No scans yet.</div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Audit Logs</CardTitle>
                  <CardDescription>Key governance events</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Array.isArray(auditLogs) && auditLogs.length > 0 ? (
                      auditLogs.slice(0, 10).map((a: any) => (
                        <div key={a._id} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <div className="font-medium">{a.action}</div>
                            <div className="text-xs text-muted-foreground">{new Date(a._creationTime).toLocaleString()}</div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-muted-foreground">No audit entries.</div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      )}

    </div>
  );
}
