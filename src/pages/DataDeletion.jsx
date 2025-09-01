import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, Trash2 } from "lucide-react";
import { createPageUrl } from "@/utils";

export default function DataDeletion() {
  const url = `${window.location.origin}${createPageUrl("DataDeletion")}`;

  const copyUrl = () => {
    navigator.clipboard.writeText(url);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Trash2 className="w-6 h-6 text-emerald-700" />
          <h1 className="text-2xl font-bold">Data Deletion Instructions</h1>
        </div>
        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
          Public URL
        </Badge>
      </header>

      <Card>
        <CardContent className="p-4 flex items-center justify-between gap-3">
          <div className="text-sm text-gray-700 break-all">{url}</div>
          <Button variant="outline" size="sm" onClick={copyUrl}><Copy className="w-4 h-4 mr-2" />Copy</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>How to Request Deletion</CardTitle>
          <CardDescription>Follow these steps to request deletion of your data from our systems.</CardDescription>
        </CardHeader>
        <CardContent className="prose max-w-none text-sm text-gray-700 space-y-4">
          <ol className="list-decimal ml-5 space-y-2">
            <li>Send a deletion request email to privacy@pikar.ai from your registered email address.</li>
            <li>Include: your full name, the email associated with your account, and “Data Deletion Request” in the subject.</li>
            <li>If you connected integrations (e.g., Meta), specify whether to revoke and purge related tokens as well.</li>
            <li>We will verify your identity and confirm deletion within 30 days (usually much sooner).</li>
          </ol>

          <h3 className="font-semibold">What Will Be Deleted</h3>
          <ul className="list-disc ml-5">
            <li>Your account profile and associated content/entities.</li>
            <li>Stored integration tokens (e.g., Meta long-lived tokens, Page tokens).</li>
            <li>Backups will be purged on their normal rotation schedule.</li>
          </ul>

          <h3 className="font-semibold">What May Be Retained</h3>
          <p>
            Certain records may be retained as required by law, to prevent fraud/abuse, or for audit purposes (e.g., aggregated logs).
          </p>

          <h3 className="font-semibold">Contact</h3>
          <p>
            For any questions, contact: privacy@pikar.ai. For our general policy, see{" "}
            <a href={createPageUrl("PrivacyPolicy")} className="underline text-emerald-800">Privacy Policy</a>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}