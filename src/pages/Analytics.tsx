import { useNavigate } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated } = useAuth();

  const businesses = useQuery(api.businesses.getUserBusinesses, {});
  const firstBizId = businesses?.[0]?._id;
  const initiatives = useQuery(api.initiatives.getByBusiness, firstBizId ? ({ businessId: firstBizId } as any) : ("skip" as any));
  const agents = useQuery(api.aiAgents.getByBusiness, firstBizId ? ({ businessId: firstBizId } as any) : ("skip" as any));
  const workflows = useQuery(api.workflows.listWorkflows, firstBizId ? ({ businessId: firstBizId } as any) : ("skip" as any));

  // Normalize initiatives to an array for counting
  const initiativesList = Array.isArray(initiatives) ? initiatives : (initiatives ? [initiatives] : []);

  const workflowExecutions = useQuery(api.workflows.getExecutions, 
    firstBizId && workflows?.[0] ? { 
      workflowId: workflows[0]._id,
      paginationOpts: { numItems: 5, cursor: null }
    } : "skip");

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
            <CardDescription>Sign in to view analytics.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats = [
    { label: "Initiatives", value: initiativesList.length },
    { label: "AI Agents", value: agents?.length ?? 0 },
    { label: "Workflows", value: workflows?.length ?? 0 },
    { label: "Executions", value: workflowExecutions?.page?.length ?? 0 },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="text-sm text-muted-foreground">Overview metrics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stats.map((s) => (
          <Card key={s.label} className="bg-white">
            <CardHeader className="pb-2">
              <CardDescription>{s.label}</CardDescription>
              <CardTitle className="text-2xl">{s.value}</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="text-xs text-muted-foreground">Updated in real time</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}