import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Key, Copy, Eye, EyeOff, Plus, ExternalLink } from 'lucide-react';

const apiKeys = [
    {
        id: 'prod-key-1',
        name: 'Production API Key',
        key: 'pk_live_51H7x...',
        created: '2024-01-15',
        lastUsed: '2 hours ago',
        permissions: ['read', 'write'],
        status: 'active'
    },
    {
        id: 'dev-key-1',
        name: 'Development Key',
        key: 'pk_test_51H7x...',
        created: '2024-01-10',
        lastUsed: '1 day ago',
        permissions: ['read'],
        status: 'active'
    }
];

const apiEndpoints = [
    {
        method: 'POST',
        path: '/api/v1/agents/strategic-planning/analyze',
        description: 'Generate strategic analysis'
    },
    {
        method: 'POST',
        path: '/api/v1/agents/content-creation/generate',
        description: 'Create content with AI'
    },
    {
        method: 'GET',
        path: '/api/v1/analytics/usage',
        description: 'Get usage statistics'
    }
];

export default function ApiAccess() {
    const [showKeys, setShowKeys] = useState({});
    const [activeTab, setActiveTab] = useState('keys');

    const toggleKeyVisibility = (keyId) => {
        setShowKeys(prev => ({
            ...prev,
            [keyId]: !prev[keyId]
        }));
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        // You could add a toast notification here
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Key className="w-6 h-6 text-emerald-600" />
                    API Access
                </CardTitle>
                <CardDescription>Manage your API keys and integration endpoints</CardDescription>
            </CardHeader>
            <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="grid w-full grid-cols-2 mb-4">
                        <TabsTrigger value="keys">API Keys</TabsTrigger>
                        <TabsTrigger value="docs">Documentation</TabsTrigger>
                    </TabsList>

                    <TabsContent value="keys" className="space-y-4">
                        <div className="flex justify-between items-center">
                            <p className="text-sm text-gray-600">Manage your API authentication keys</p>
                            <Button size="sm">
                                <Plus className="w-4 h-4 mr-2" />
                                Generate Key
                            </Button>
                        </div>

                        <div className="space-y-3">
                            {apiKeys.map((key) => (
                                <div key={key.id} className="border rounded-lg p-4 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h4 className="font-medium">{key.name}</h4>
                                            <p className="text-xs text-gray-500">Created {key.created}</p>
                                        </div>
                                        <Badge variant={key.status === 'active' ? 'default' : 'secondary'}>
                                            {key.status}
                                        </Badge>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <Input 
                                            type={showKeys[key.id] ? 'text' : 'password'}
                                            value={showKeys[key.id] ? `pikar_${key.key}9f8a7b6c5d` : '••••••••••••••••'}
                                            readOnly
                                            className="font-mono text-sm"
                                        />
                                        <Button 
                                            size="icon" 
                                            variant="outline"
                                            onClick={() => toggleKeyVisibility(key.id)}
                                        >
                                            {showKeys[key.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                        </Button>
                                        <Button 
                                            size="icon" 
                                            variant="outline"
                                            onClick={() => copyToClipboard(`pikar_${key.key}9f8a7b6c5d`)}
                                        >
                                            <Copy className="w-4 h-4" />
                                        </Button>
                                    </div>

                                    <div className="flex items-center justify-between text-xs text-gray-500">
                                        <span>Last used: {key.lastUsed}</span>
                                        <div className="flex gap-1">
                                            {key.permissions.map(permission => (
                                                <Badge key={permission} variant="outline" className="text-xs">
                                                    {permission}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </TabsContent>

                    <TabsContent value="docs" className="space-y-4">
                        <div className="flex justify-between items-center">
                            <p className="text-sm text-gray-600">API endpoints and documentation</p>
                            <Button size="sm" variant="outline">
                                <ExternalLink className="w-4 h-4 mr-2" />
                                Full Docs
                            </Button>
                        </div>

                        <div className="space-y-2">
                            {apiEndpoints.map((endpoint, index) => (
                                <div key={index} className="border rounded p-3">
                                    <div className="flex items-center gap-3 mb-2">
                                        <Badge variant={endpoint.method === 'GET' ? 'secondary' : 'default'}>
                                            {endpoint.method}
                                        </Badge>
                                        <code className="text-sm font-mono">{endpoint.path}</code>
                                    </div>
                                    <p className="text-sm text-gray-600">{endpoint.description}</p>
                                </div>
                            ))}
                        </div>

                        <div className="p-3 bg-gray-50 rounded-lg">
                            <p className="text-sm">
                                <strong>Base URL:</strong> <code>https://api.pikar.ai</code>
                            </p>
                            <p className="text-sm mt-1">
                                <strong>Authentication:</strong> Include your API key in the <code>Authorization</code> header
                            </p>
                        </div>
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
}