import { useNavigate } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

export default function WorkflowTemplatesPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const seedTemplates = useMutation(api.workflows.seedTemplates);

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
            <CardDescription>Sign in to manage templates.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Workflow Templates</h1>
        <p className="text-sm text-muted-foreground">Seed ready-made automations.</p>
      </div>

      <Card className="bg-white">
        <CardHeader>
          <CardTitle>Seed Templates</CardTitle>
          <CardDescription>Safe to run multiple times. No duplicates.</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button
            onClick={async () => {
              try {
                await seedTemplates({});
                toast("Templates seeded. View them under Workflows → All.");
                navigate("/workflows");
              } catch (e: any) {
                toast(e?.message || "Failed to seed templates");
              }
            }}
          >
            Seed Templates
          </Button>
          <Button variant="outline" onClick={() => navigate("/workflows")}>
            View All Workflows
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
