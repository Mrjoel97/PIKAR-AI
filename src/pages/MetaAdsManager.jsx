
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { 
  Facebook, 
  Instagram, 
  TrendingUp, 
  DollarSign, 
  Eye, 
  MousePointer, 
  Users,
  Plus,
  Settings,
  BarChart3,
  Camera,
  Video,
  RefreshCw,
  Loader2
} from "lucide-react";
import { MetaAdAccount } from "@/api/entities";
import { MetaCampaign } from "@/api/entities";
import { Toaster, toast } from 'sonner';

// Import functions with error handling
const importFunction = async (moduleName) => {
  try {
    const module = await import(`@/api/functions/${moduleName}`);
    return module[moduleName];
  } catch (error) {
    console.warn(`Function ${moduleName} not available:`, error);
    return null;
  }
};

export default function MetaAdsManager() {
  const [adAccounts, setAdAccounts] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [syncing, setSyncing] = useState(false);

  // Campaign creation form
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    objective: '',
    daily_budget: '',
    status: 'PAUSED'
  });

  // Instagram publishing form
  const [instagramPost, setInstagramPost] = useState({
    page_id: '',
    caption: '',
    image_url: '',
    video_url: ''
  });
  const [publishing, setPublishing] = useState(false);

  const loadAdAccounts = async () => {
    setLoading(true);
    try {
      const metaGetAdAccounts = await importFunction('metaGetAdAccounts');
      if (!metaGetAdAccounts) {
        toast.error("Meta ad accounts function not available");
        return;
      }

      const { data } = await metaGetAdAccounts();
      setAdAccounts(data?.ad_accounts || []);
      
      if (data?.ad_accounts?.length > 0) {
        setSelectedAccount(data.ad_accounts[0].account_id);
      }
      
      toast.success(`Loaded ${data?.ad_accounts?.length || 0} ad accounts`);
    } catch (error) {
      console.error("Failed to load ad accounts:", error);
      toast.error("Failed to load ad accounts");
    } finally {
      setLoading(false);
    }
  };

  const loadCampaigns = useCallback(async () => {
    if (!selectedAccount) return;
    
    try {
      const campaignsList = await MetaCampaign.filter({ 
        ad_account_id: selectedAccount 
      }, '-updated_time');
      setCampaigns(campaignsList || []);
    } catch (error) {
      console.error("Failed to load campaigns:", error);
      toast.error("Failed to load campaigns");
    }
  }, [selectedAccount, setCampaigns]); // setCampaigns is a stable reference from useState, but good practice to include if directly used inside useCallback.

  useEffect(() => {
    loadAdAccounts();
  }, []);

  useEffect(() => {
    if (selectedAccount) {
      loadCampaigns();
    }
  }, [selectedAccount, loadCampaigns]);

  const handleCreateCampaign = async () => {
    if (!newCampaign.name || !newCampaign.objective || !selectedAccount) {
      toast.error("Please fill in all required fields");
      return;
    }

    setCreating(true);
    try {
      const metaCreateCampaign = await importFunction('metaCreateCampaign');
      if (!metaCreateCampaign) {
        toast.error("Meta campaign creation function not available");
        return;
      }

      const { data } = await metaCreateCampaign({
        ad_account_id: selectedAccount,
        name: newCampaign.name,
        objective: newCampaign.objective,
        daily_budget: newCampaign.daily_budget,
        status: newCampaign.status
      });

      if (data?.campaign) {
        toast.success("Campaign created successfully!");
        setNewCampaign({ name: '', objective: '', daily_budget: '', status: 'PAUSED' });
        loadCampaigns();
      }
    } catch (error) {
      console.error("Failed to create campaign:", error);
      toast.error("Failed to create campaign");
    } finally {
      setCreating(false);
    }
  };

  const handleSyncInsights = async (campaignId) => {
    setSyncing(true);
    try {
      const metaGetInsights = await importFunction('metaGetInsights');
      if (!metaGetInsights) {
        toast.error("Meta insights function not available");
        return;
      }

      const response = await fetch(`/functions/metaGetInsights?level=campaign&object_id=${campaignId}&date_preset=last_7_days`);
      const data = await response.json();

      if (response.ok) {
        toast.success("Insights synced successfully!");
        loadCampaigns(); // Reload to get updated insights
      } else {
        throw new Error(data.error || 'Failed to sync insights');
      }
    } catch (error) {
      console.error("Failed to sync insights:", error);
      toast.error("Failed to sync insights");
    } finally {
      setSyncing(false);
    }
  };

  const handlePublishInstagram = async () => {
    if (!instagramPost.page_id || (!instagramPost.image_url && !instagramPost.video_url)) {
      toast.error("Please select a page and provide media URL");
      return;
    }

    setPublishing(true);
    try {
      const metaPublishInstagram = await importFunction('metaPublishInstagram');
      if (!metaPublishInstagram) {
        toast.error("Instagram publishing function not available");
        return;
      }

      const { data } = await metaPublishInstagram(instagramPost);
      
      if (data?.success) {
        toast.success("Published to Instagram successfully!");
        setInstagramPost({ page_id: '', caption: '', image_url: '', video_url: '' });
      } else {
        throw new Error(data?.error || 'Publishing failed');
      }
    } catch (error) {
      console.error("Failed to publish to Instagram:", error);
      toast.error("Failed to publish to Instagram");
    } finally {
      setPublishing(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ACTIVE': return 'bg-green-100 text-green-800 border-green-200';
      case 'PAUSED': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'DELETED': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 p-6">
      <Toaster richColors />
      
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <Facebook className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Meta Ads Manager</h1>
            <p className="text-gray-600">Manage Facebook and Instagram campaigns</p>
          </div>
        </div>
        <Button onClick={loadAdAccounts} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
          Refresh Accounts
        </Button>
      </header>

      {/* Ad Account Selection */}
      {adAccounts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Select Ad Account</CardTitle>
            <CardDescription>Choose which ad account to manage</CardDescription>
          </CardHeader>
          <CardContent>
            <Select value={selectedAccount} onValueChange={setSelectedAccount}>
              <SelectTrigger>
                <SelectValue placeholder="Select an ad account" />
              </SelectTrigger>
              <SelectContent>
                {adAccounts.map(account => (
                  <SelectItem key={account.account_id} value={account.account_id}>
                    {account.account_name} ({account.currency}) - {account.account_status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="campaigns" className="space-y-6">
        <TabsList className="grid grid-cols-3 w-full max-w-md">
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
          <TabsTrigger value="create">Create</TabsTrigger>
          <TabsTrigger value="instagram">Instagram</TabsTrigger>
        </TabsList>

        {/* Campaigns Tab */}
        <TabsContent value="campaigns" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Active Campaigns</CardTitle>
              <CardDescription>Manage your Facebook and Instagram ad campaigns</CardDescription>
            </CardHeader>
            <CardContent>
              {campaigns.length === 0 ? (
                <div className="text-center py-8">
                  <Settings className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-600">No campaigns found for this account</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {campaigns.map(campaign => (
                    <div key={campaign.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h3 className="font-semibold">{campaign.campaign_name}</h3>
                          <p className="text-sm text-gray-600">{campaign.objective}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={getStatusColor(campaign.status)}>
                            {campaign.status}
                          </Badge>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleSyncInsights(campaign.campaign_id)}
                            disabled={syncing}
                          >
                            {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                          </Button>
                        </div>
                      </div>
                      
                      {campaign.insights && (
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div className="flex items-center gap-2">
                            <Eye className="w-4 h-4 text-blue-500" />
                            <span>{campaign.insights.impressions?.toLocaleString() || 0} impressions</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <MousePointer className="w-4 h-4 text-green-500" />
                            <span>{campaign.insights.clicks?.toLocaleString() || 0} clicks</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <DollarSign className="w-4 h-4 text-red-500" />
                            <span>${campaign.insights.spend?.toFixed(2) || '0.00'} spent</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-purple-500" />
                            <span>{campaign.insights.ctr?.toFixed(2) || '0.00'}% CTR</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Create Campaign Tab */}
        <TabsContent value="create" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Create New Campaign</CardTitle>
              <CardDescription>Set up a new Facebook or Instagram ad campaign</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="campaign-name">Campaign Name</Label>
                <Input
                  id="campaign-name"
                  value={newCampaign.name}
                  onChange={(e) => setNewCampaign({...newCampaign, name: e.target.value})}
                  placeholder="Enter campaign name"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="objective">Campaign Objective</Label>
                <Select 
                  value={newCampaign.objective} 
                  onValueChange={(value) => setNewCampaign({...newCampaign, objective: value})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select objective" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="AWARENESS">Brand Awareness</SelectItem>
                    <SelectItem value="TRAFFIC">Traffic</SelectItem>
                    <SelectItem value="ENGAGEMENT">Engagement</SelectItem>
                    <SelectItem value="LEADS">Lead Generation</SelectItem>
                    <SelectItem value="SALES">Conversions</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="budget">Daily Budget ($)</Label>
                <Input
                  id="budget"
                  type="number"
                  value={newCampaign.daily_budget}
                  onChange={(e) => setNewCampaign({...newCampaign, daily_budget: e.target.value})}
                  placeholder="10.00"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="status">Initial Status</Label>
                <Select 
                  value={newCampaign.status} 
                  onValueChange={(value) => setNewCampaign({...newCampaign, status: value})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PAUSED">Paused (Recommended)</SelectItem>
                    <SelectItem value="ACTIVE">Active</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button onClick={handleCreateCampaign} disabled={creating || !selectedAccount}>
                {creating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating Campaign...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Campaign
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Instagram Publishing Tab */}
        <TabsContent value="instagram" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Instagram className="w-5 h-5 text-pink-500" />
                <CardTitle>Instagram Publishing</CardTitle>
              </div>
              <CardDescription>Publish content directly to Instagram Business accounts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="page-select">Facebook Page (linked to Instagram)</Label>
                <Input
                  id="page-select"
                  value={instagramPost.page_id}
                  onChange={(e) => setInstagramPost({...instagramPost, page_id: e.target.value})}
                  placeholder="Enter Facebook Page ID"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="caption">Caption</Label>
                <Textarea
                  id="caption"
                  value={instagramPost.caption}
                  onChange={(e) => setInstagramPost({...instagramPost, caption: e.target.value})}
                  placeholder="Write your Instagram caption..."
                  className="h-24"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="image-url">Image URL</Label>
                  <Input
                    id="image-url"
                    value={instagramPost.image_url}
                    onChange={(e) => setInstagramPost({...instagramPost, image_url: e.target.value, video_url: ''})}
                    placeholder="https://example.com/image.jpg"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="video-url">Video URL (alternative)</Label>
                  <Input
                    id="video-url"
                    value={instagramPost.video_url}
                    onChange={(e) => setInstagramPost({...instagramPost, video_url: e.target.value, image_url: ''})}
                    placeholder="https://example.com/video.mp4"
                  />
                </div>
              </div>

              <Button onClick={handlePublishInstagram} disabled={publishing}>
                {publishing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Publishing...
                  </>
                ) : (
                  <>
                    <Camera className="w-4 h-4 mr-2" />
                    Publish to Instagram
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
