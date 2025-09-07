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

type Initiative = {
  _id: string;
  title: string;
  status: "draft" | "active" | "paused" | "completed";
  priority: "low" | "medium" | "high" | "urgent";
  metrics: { targetROI: number; currentROI: number; completionRate: number };
};

export default function InitiativesPage() {
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

  const initiatives = useQuery(
    api.initiatives.getByBusiness,
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
            <CardDescription>Sign in to view your initiatives.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const iList = Array.isArray(initiatives) ? initiatives : (initiatives ? [initiatives] : []);
  const filtered = iList.filter((i) => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return true;
    return [i.title, i.status, i.priority].some((f) =>
      String(f).toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Initiatives</h1>
          <p className="text-sm text-muted-foreground">Track ROI and completion.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          {userBusinesses && userBusinesses.length > 0 ? (
            <Select value={selectedBusinessId ?? ""} onValueChange={(v) => setSelectedBusinessId(v)}>
              <SelectTrigger className="min-w-56">
                <SelectValue placeholder="Select business" />
              </SelectTrigger>
              <SelectContent>
                {userBusinesses.map((b) => (
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
            <CardTitle>Initiatives</CardTitle>
            <CardDescription>List of initiatives and their KPIs.</CardDescription>
          </div>
          <div className="w-full max-w-xs">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search initiatives…"
              className="h-9"
              aria-label="Search initiatives"
            />
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead className="text-right">ROI</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((i) => (
                <TableRow key={i._id}>
                  <TableCell className="max-w-[240px] truncate">{i.title}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{i.status ?? "draft"}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={i.priority === "urgent" || i.priority === "high" ? "destructive" : "outline"}>
                      {i.priority ?? "low"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {Math.round(i.metrics?.currentROI ?? 0)}% / {Math.round(i.metrics?.targetROI ?? 0)}%
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-muted-foreground">
                    {searchQuery ? "No results match your search." : "No initiatives yet."}
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