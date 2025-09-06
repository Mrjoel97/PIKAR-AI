import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Business = {
  _id: string;
  name: string;
  tier: "solopreneur" | "startup" | "sme" | "enterprise";
  industry: string;
};

type Agent = {
  _id: string;
  name: string;
  type: string;
  isActive: boolean;
};

export default function AgentsPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated } = useAuth();

  const userBusinesses = useQuery(api.businesses.getUserBusinesses, {});
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!selectedBusinessId && (userBusinesses?.length || 0) > 0) {
      setSelectedBusinessId(userBusinesses![0]._id);
    }
  }, [selectedBusinessId, userBusinesses]);

  const agents = useQuery(
    api.aiAgents.getByBusiness,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  );

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
            <CardDescription>Sign in to view your agents.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const filtered = (agents || []).filter((a: Agent) => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return true;
    return [a.name, a.type, a.isActive ? "active" : "inactive"].some((f) => String(f).toLowerCase().includes(q));
  });

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">AI Agents</h1>
          <p className="text-sm text-muted-foreground">Operational assistants for your workflows.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          {userBusinesses && userBusinesses.length > 0 ? (
            <Select value={selectedBusinessId ?? ""} onValueChange={(v) => setSelectedBusinessId(v)}>
              <SelectTrigger className="min-w-56">
                <SelectValue placeholder="Select business" />
              </SelectTrigger>
              <SelectContent>
                {userBusinesses.map((b: Business) => (
                  <SelectItem key={b._id} value={b._id}>
                    {b.name} <span className="text-muted-foreground">• {b.tier}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
          <Button variant="outline" onClick={() => navigate("/onboarding")}>Onboarding</Button>
        </div>
      </div>

      <Card className="bg-white">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Agents</CardTitle>
            <CardDescription>List of AI agents.</CardDescription>
          </div>
          <div className="w-full max-w-xs">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search agents…"
              className="h-9"
              aria-label="Search agents"
            />
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((a: Agent) => (
                <TableRow key={a._id}>
                  <TableCell className="max-w-[200px] truncate">{a.name}</TableCell>
                  <TableCell><Badge variant="outline">{a.type}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={a.isActive ? "secondary" : "outline"}>
                      {a.isActive ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="text-muted-foreground">
                    {searchQuery ? "No results match your search." : "No agents yet."}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
