import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { KeyRound, RefreshCw, Copy, Plug } from 'lucide-react';
import { toast, Toaster } from 'sonner';

const integrations = [
    { name: "Salesforce", category: "CRM", description: "Sync leads and opportunities." },
    { name: "Slack", category: "Communication", description: "Get real-time notifications." },
    { name: "Jira", category: "Project Management", description: "Create issues from insights." },
    { name: "Google Analytics", category: "Analytics", description: "Import website data." },
];

export default function Integrations() {
    const handleConnect = (name) => toast.info(`Connecting to ${name}...`);
    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <Toaster richColors />
            <h1 className="text-3xl font-bold flex items-center gap-3">
                <Plug className="w-8 h-8" />
                Integrations
            </h1>
            <Card>
                <CardHeader><CardTitle>Integration Marketplace</CardTitle></CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {integrations.map(int => (
                        <div key={int.name} className="p-4 border rounded-lg flex justify-between items-center">
                            <div>
                                <h3 className="font-semibold">{int.name}</h3>
                                <p className="text-sm text-gray-500">{int.description}</p>
                            </div>
                            <Button onClick={() => handleConnect(int.name)}>Connect</Button>
                        </div>
                    ))}
                </CardContent>
            </Card>
            <Card>
                <CardHeader><CardTitle>API Key Management</CardTitle></CardHeader>
                <CardContent>
                    <p className="mb-4 text-sm">Use these keys to access the PIKAR AI API.</p>
                    <div className="flex gap-2 items-center">
                        <Input readOnly value="pikar_sk_live_******************1234" />
                        <Button variant="outline" size="icon"><Copy className="w-4 h-4" /></Button>
                    </div>
                    <Button className="mt-4"><RefreshCw className="w-4 h-4 mr-2" /> Generate New Key</Button>
                </CardContent>
            </Card>
        </div>
    );
}