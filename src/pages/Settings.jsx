import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User as UserIcon, Bell, Palette, Building, Shield, LogOut, Users, KeyRound } from 'lucide-react';
import { toast, Toaster } from 'sonner';
import { User } from '@/api/entities';
import TierGate from '@/components/TierGate';

export default function Settings() {
    const [brandName, setBrandName] = useState('PIKAR AI');
    const [brandColor, setBrandColor] = useState('#3b82f6');
    const [currentUser, setCurrentUser] = useState({ tier: 'enterprise' }); // Mock current user

    const handleSaveBranding = () => {
        toast.success("Branding settings saved successfully!");
        document.documentElement.style.setProperty('--primary-color', brandColor);
    };

    const handleLogout = async () => {
        try {
            await User.logout();
            toast.success("You have been logged out successfully.");
            // The platform will handle the redirection after logout.
            window.location.reload();
        } catch (error) {
            toast.error("Logout failed. Please try again.");
            console.error("Logout error:", error);
        }
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <Toaster richColors />
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold">Settings</h1>
                <Button variant="outline" onClick={handleLogout}>
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                </Button>
            </div>
            
            {/* Profile Settings */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <UserIcon className="w-5 h-5" /> Profile
                    </CardTitle>
                    <CardDescription>Manage your personal information.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* ... Profile content from previous version ... */}
                </CardContent>
            </Card>

            {/* Tenant Configuration - Gated for Enterprise */}
            <TierGate
                currentTier={currentUser.tier}
                requiredTier="enterprise"
                feature="Tenant Configuration"
                description="Custom branding is an exclusive Enterprise feature."
                onUpgrade={() => {}}
            >
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Building className="w-5 h-5" /> Tenant Configuration
                        </CardTitle>
                        <CardDescription>
                            Customize the platform's appearance for your organization.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="brand-name">Brand Name</Label>
                            <Input id="brand-name" value={brandName} onChange={(e) => setBrandName(e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="brand-logo">Brand Logo</Label>
                            <Input id="brand-logo" type="file" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="brand-color">Primary Color</Label>
                            <div className="flex items-center gap-2">
                                <Input id="brand-color" type="color" value={brandColor} onChange={(e) => setBrandColor(e.target.value)} className="w-16 p-1" />
                                <span>{brandColor}</span>
                            </div>
                        </div>
                        <Button onClick={handleSaveBranding}>Save Branding</Button>
                    </CardContent>
                </Card>
            </TierGate>

            {/* Security Settings - Gated for Enterprise */}
            <TierGate
                currentTier={currentUser.tier}
                requiredTier="enterprise"
                feature="Advanced Security"
                description="Advanced security settings like SSO and RBAC are exclusive to the Enterprise plan."
                onUpgrade={() => {}}
            >
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Shield className="w-5 h-5" /> Advanced Security
                        </CardTitle>
                        <CardDescription>
                            Manage Single Sign-On (SSO), Role-Based Access Control (RBAC), and audit logs.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div>
                            <h4 className="font-semibold text-lg">Single Sign-On (SSO)</h4>
                            <p className="text-sm text-gray-500 mb-2">Configure SSO with your identity provider.</p>
                            <Button>Configure SSO</Button>
                        </div>
                        <div>
                            <h4 className="font-semibold text-lg">Role-Based Access Control (RBAC)</h4>
                            <p className="text-sm text-gray-500 mb-2">Define custom roles and permissions for your team.</p>
                            <Button>Manage Roles</Button>
                        </div>
                        <div>
                            <h4 className="font-semibold text-lg">API Key Management</h4>
                            <p className="text-sm text-gray-500 mb-2">Manage API keys for your integrations.</p>
                            <Button>Manage API Keys</Button>
                        </div>
                    </CardContent>
                </Card>
            </TierGate>
        </div>
    );
}