import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, FileText } from "lucide-react";
import { createPageUrl } from "@/utils";

export default function Terms() {
  const url = `${window.location.origin}${createPageUrl("Terms")}`;

  const copyUrl = () => {
    navigator.clipboard.writeText(url);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-6 h-6 text-emerald-700" />
          <h1 className="text-2xl font-bold">Terms of Service</h1>
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
          <CardTitle>Agreement to Terms</CardTitle>
          <CardDescription>By accessing or using the app, you agree to these terms.</CardDescription>
        </CardHeader>
        <CardContent className="prose max-w-none text-sm text-gray-700 space-y-4">
          <h3 className="font-semibold">Use of the Service</h3>
          <ul className="list-disc ml-5">
            <li>You will comply with applicable laws and this Agreement.</li>
            <li>No misuse, reverse engineering, or abuse of rate limits or integrations.</li>
            <li>AI outputs are provided “as-is”; verify critical decisions independently.</li>
          </ul>

          <h3 className="font-semibold">Accounts & Security</h3>
          <p>You are responsible for safeguarding your account and for all activities under it.</p>

          <h3 className="font-semibold">Intellectual Property</h3>
          <p>
            The service and its original content are our property. You retain rights to your data and uploaded content,
            and grant us a limited license to process it to deliver features you request.
          </p>

          <h3 className="font-semibold">Third-Party Services</h3>
          <p>Integrations (e.g., Meta) are governed by their own terms; you must comply with those as well.</p>

          <h3 className="font-semibold">Disclaimers & Limitation of Liability</h3>
          <p>
            The service is provided “as-is” without warranties. To the maximum extent permitted by law, our liability is
            limited to amounts paid in the 12 months preceding the claim.
          </p>

          <h3 className="font-semibold">Termination</h3>
          <p>We may suspend or terminate access for violations. You may stop using the service at any time.</p>

          <h3 className="font-semibold">Changes</h3>
          <p>We may update these terms; continued use constitutes acceptance of the updated terms.</p>

          <h3 className="font-semibold">Contact</h3>
          <p>For any questions about these Terms, contact: legal@pikar.ai.</p>
        </CardContent>
      </Card>
    </div>
  );
}