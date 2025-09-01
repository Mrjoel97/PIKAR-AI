import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, Shield } from "lucide-react";
import { createPageUrl } from "@/utils";

export default function PrivacyPolicy() {
  const url = `${window.location.origin}${createPageUrl("PrivacyPolicy")}`;

  const copyUrl = () => {
    navigator.clipboard.writeText(url);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-emerald-700" />
          <h1 className="text-2xl font-bold">Privacy Policy</h1>
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
          <CardTitle>Our Commitment to Your Privacy</CardTitle>
          <CardDescription>How we collect, use, and protect your information.</CardDescription>
        </CardHeader>
        <CardContent className="prose max-w-none text-sm text-gray-700 space-y-4">
          <p>
            This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our
            application and services. By using the app, you agree to the practices described in this policy.
          </p>
          <h3 className="font-semibold">Information We Collect</h3>
          <ul className="list-disc ml-5">
            <li>Account and profile information (e.g., name, email).</li>
            <li>Usage data (e.g., interactions, feature usage, performance metrics).</li>
            <li>Files and content you upload (e.g., documents for analysis, media for social posts).</li>
            <li>Third-party tokens strictly for integrations you authorize (e.g., Meta Pages tokens).</li>
          </ul>

          <h3 className="font-semibold">How We Use Information</h3>
          <ul className="list-disc ml-5">
            <li>Provide and improve app features and AI-assisted services.</li>
            <li>Enable integrations you connect (e.g., posting to social media on your behalf).</li>
            <li>Security, compliance, and fraud prevention.</li>
            <li>Support and service communications.</li>
          </ul>

          <h3 className="font-semibold">Legal Basis</h3>
          <p>We process data based on legitimate interests, performance of a contract, and/or your consent where required.</p>

          <h3 className="font-semibold">Data Retention</h3>
          <p>We retain data for as long as necessary to deliver services and comply with legal obligations. You can request deletion at any time.</p>

          <h3 className="font-semibold">Data Sharing</h3>
          <p>
            We do not sell your personal data. We share data with service providers and integrations only as needed to
            deliver requested features, under appropriate safeguards.
          </p>

          <h3 className="font-semibold">Your Rights</h3>
          <ul className="list-disc ml-5">
            <li>Access, rectify, or delete your data.</li>
            <li>Object to or restrict processing in certain cases.</li>
            <li>Portability where applicable.</li>
          </ul>

          <h3 className="font-semibold">Cookies</h3>
          <p>We use cookies and similar technologies for authentication, preferences, and analytics.</p>

          <h3 className="font-semibold">Contact</h3>
          <p>
            For privacy questions or requests, contact: privacy@pikar.ai (or your organization’s contact). For data deletion, see{" "}
            <a href={createPageUrl("DataDeletion")} className="underline text-emerald-800">Data Deletion Instructions</a>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}