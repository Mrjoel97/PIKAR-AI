import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { TwitterAdAccount } from "@/api/entities";
import { TwitterCampaign } from "@/api/entities";
import { TwitterStreamRule } from "@/api/entities";
import { TwitterStreamTweet } from "@/api/entities";
import { TwitterBulkOperation } from "@/api/entities";
import { Twitter, Plus, Target, Radio, Zap, BarChart3, Upload, Calendar } from 'lucide-react';
import { toast, Toaster } from 'sonner';

// Import Twitter functions
const importFunction = async (moduleName) => {
  try {
    const module = await import(`@/api/functions/${moduleName}`);
    return module[moduleName];
  } catch (error) {
    console.warn(`Function ${moduleName} not available:`, error);
    return null;
  }
};

export default function TwitterAdsManager() {
  const [adAccounts, setAdAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [campaigns, setCampaigns] = useState([]);
  const [streamRules, setStreamRules] = useState([]);
  const [streamTweets, setStreamTweets] = useState([]);
  const [bulkOperations, setBulkOperations] = useState([]);
  
  // Loading states
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [loadingCampaigns, setLoadingCampaigns] = useState(false);
  const [loadingRules, setLoadingRules] = useState(false);
  const [loadingTweets, setLoadingTweets] = useState(false);
  const [loadingOperations, setLoadingOperations] = useState(false);

  // Dialog states
  const [showCreateCampaign, setShowCreateCampaign] = useState(false);
  const [showCreateRule, setShowCreateRule] = useState(false);
  const [showBulkOperation, setShowBulkOperation] = useState(false);
  const [creatingCampaign, setCreatingCampaign] = useState(false);
  const [creatingRule, setCreatingRule] = useState(false);
  const [processingBulk, setProcessingBulk] = useState(false);

  // Form states
  const [campaignData, setCampaignData] = useState({
    campaign_name: '',
    objective: 'ENGAGEMENTS',
    daily_budget: '',
    total_budget: '',
    start_time: '',
    end_time: ''
  });

  const [ruleData, setRuleData] = useState({
    rule_value: '',
    rule_tag: '',
    rule_description: ''
  });

  const [bulkData, setBulkData] = useState({
    operation_type: 'BULK_TWEET',
    items: '',
    schedule_time: ''
  });

  const loadAdAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const twitterGetAdAccounts = await importFunction('twitterGetAdAccounts');
      if (!twitterGetAdAccounts) {
        toast.error("Twitter Ad Accounts function not available");
        return;
      }
      
      const { data } = await twitterGetAdAccounts();
      setAdAccounts(data?.ad_accounts || []);
      
      if ((data?.ad_accounts || []).length === 0) {
        toast.info("No Twitter ad accounts found. Apply for Twitter Ads access first.");
      }
    } catch (error) {
      console.error("Failed to load ad accounts:", error);
      toast.error("Failed to load Twitter ad accounts");
    } finally {
      setLoadingAccounts(false);
    }
  };

  const loadCampaigns = useCallback(async () => {
    if (!selectedAccount) return;
    
    setLoadingCampaigns(true);
    try {
      const campaignsList = await TwitterCampaign.filter({ 
        ad_account_id: selectedAccount 
      }, '-updated_at');
      setCampaigns(campaignsList || []);
    } catch (error) {
      console.error("Failed to load campaigns:", error);
      toast.error("Failed to load campaigns");
    } finally {
      setLoadingCampaigns(false);
    }
  }, [selectedAccount]);

  const loadStreamRules = async () => {
    setLoadingRules(true);
    try {
      const rules = await TwitterStreamRule.list('-created_at');
      setStreamRules(rules || []);
    } catch (error) {
      console.error("Failed to load stream rules:", error);
      toast.error("Failed to load stream rules");
    } finally {
      setLoadingRules(false);
    }
  };

  const loadStreamTweets = async () => {
    setLoadingTweets(true);
    try {
      const tweets = await TwitterStreamTweet.list('-created_at', 50);
      setStreamTweets(tweets || []);
    } catch (error) {
      console.error("Failed to load stream tweets:", error);
      toast.error("Failed to load stream tweets");
    } finally {
      setLoadingTweets(false);
    }
  };

  const loadBulkOperations = async () => {
    setLoadingOperations(true);
    try {
      const operations = await TwitterBulkOperation.list('-created_date', 20);
      setBulkOperations(operations || []);
    } catch (error) {
      console.error("Failed to load bulk operations:", error);
      toast.error("Failed to load bulk operations");
    } finally {
      setLoadingOperations(false);
    }
  };

  const handleCreateCampaign = async () => {
    if (!selectedAccount || !campaignData.campaign_name) {
      toast.error("Please select an ad account and enter a campaign name");
      return;
    }

    setCreatingCampaign(true);
    try {
      const twitterCreateCampaign = await importFunction('twitterCreateCampaign');
      if (!twitterCreateCampaign) {
        toast.error("Twitter Create Campaign function not available");
        return;
      }
      
      const { data } = await twitterCreateCampaign({
        ad_account_id: selectedAccount,
        ...campaignData
      });
      
      if (data?.success) {
        toast.success("Campaign created successfully!");
        setShowCreateCampaign(false);
        setCampaignData({
          campaign_name: '',
          objective: 'ENGAGEMENTS',
          daily_budget: '',
          total_budget: '',
          start_time: '',
          end_time: ''
        });
        loadCampaigns();
      } else {
        toast.error(data?.error || "Failed to create campaign");
      }
    } catch (error) {
      console.error("Campaign creation failed:", error);
      toast.error("Failed to create campaign");
    } finally {
      setCreatingCampaign(false);
    }
  };

  const handleCreateRule = async () => {
    if (!ruleData.rule_value || !ruleData.rule_tag) {
      toast.error("Please enter rule value and tag");
      return;
    }

    setCreatingRule(true);
    try {
      const twitterCreateStreamRule = await importFunction('twitterCreateStreamRule');
      if (!twitterCreateStreamRule) {
        toast.error("Twitter Create Stream Rule function not available");
        return;
      }
      
      const { data } = await twitterCreateStreamRule(ruleData);
      
      if (data?.success) {
        toast.success("Stream rule created successfully!");
        setShowCreateRule(false);
        setRuleData({
          rule_value: '',
          rule_tag: '',
          rule_description: ''
        });
        loadStreamRules();
      } else {
        toast.error(data?.error || "Failed to create rule");
      }
    } catch (error) {
      console.error("Rule creation failed:", error);
      toast.error("Failed to create stream rule");
    } finally {
      setCreatingRule(false);
    }
  };

  const handleBulkOperation = async () => {
    if (!bulkData.operation_type || !bulkData.items) {
      toast.error("Please select operation type and provide data");
      return;
    }

    setProcessingBulk(true);
    try {
      // Parse items based on operation type
      let parsedItems = [];
      try {
        if (bulkData.operation_type === 'BULK_TWEET') {
          parsedItems = bulkData.items.split('\n').filter(text => text.trim()).map(text => ({ text: text.trim() }));
        } else if (bulkData.operation_type === 'BULK_FOLLOW') {
          parsedItems = bulkData.items.split('\n').filter(id => id.trim()).map(id => ({ user_id: id.trim() }));
        } else {
          parsedItems = bulkData.items.split('\n').filter(id => id.trim()).map(id => ({ tweet_id: id.trim() }));
        }
      } catch (parseError) {
        toast.error("Invalid data format. Please check your input.");
        return;
      }

      const twitterBulkOperation = await importFunction('twitterBulkOperation');
      if (!twitterBulkOperation) {
        toast.error("Twitter Bulk Operation function not available");
        return;
      }
      
      const { data } = await twitterBulkOperation({
        operation_type: bulkData.operation_type,
        operation_data: { items: parsedItems },
        schedule_time: bulkData.schedule_time || null
      });
      
      if (data?.success) {
        toast.success(data.message || "Bulk operation started successfully!");
        setShowBulkOperation(false);
        setBulkData({
          operation_type: 'BULK_TWEET',
          items: '',
          schedule_time: ''
        });
        loadBulkOperations();
      } else {
        toast.error(data?.error || "Failed to start bulk operation");
      }
    } catch (error) {
      console.error("Bulk operation failed:", error);
      toast.error("Failed to start bulk operation");
    } finally {
      setProcessingBulk(false);
    }
  };

  useEffect(() => {
    loadAdAccounts();
    loadStreamRules();
    loadStreamTweets();
    loadBulkOperations();
  }, []);

  useEffect(() => {
    if (selectedAccount) {
      loadCampaigns();
    }
  }, [selectedAccount, loadCampaigns]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <Toaster richColors />
      
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-400 rounded-xl flex items-center justify-center">
            <Twitter className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Twitter/X Ads Manager</h1>
            <p className="text-gray-600">Advanced campaigns, streaming, and bulk operations</p>
          </div>
        </div>
        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
          Professional Marketing Platform
        </Badge>
      </header>

      <Tabs defaultValue="campaigns" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="campaigns" className="flex items-center gap-2">
            <Target className="w-4 h-4" />
            Campaigns
          </TabsTrigger>
          <TabsTrigger value="streaming" className="flex items-center gap-2">
            <Radio className="w-4 h-4" />
            Real-time Stream
          </TabsTrigger>
          <TabsTrigger value="bulk" className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Bulk Operations
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="campaigns" className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Select value={selectedAccount} onValueChange={setSelectedAccount}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Select Ad Account" />
                </SelectTrigger>
                <SelectContent>
                  {adAccounts.map((account) => (
                    <SelectItem key={account.account_id} value={account.account_id}>
                      {account.account_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={loadAdAccounts} disabled={loadingAccounts}>
                {loadingAccounts ? "Loading..." : "Refresh Accounts"}
              </Button>
            </div>
            <Dialog open={showCreateCampaign} onOpenChange={setShowCreateCampaign}>
              <DialogTrigger asChild>
                <Button disabled={!selectedAccount}>
                  <Plus className="w-4 h-4 mr-2" />
                  New Campaign
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create Twitter Campaign</DialogTitle>
                  <DialogDescription>
                    Set up a new advertising campaign to reach your target audience on Twitter/X.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <Label htmlFor="campaign_name">Campaign Name</Label>
                    <Input
                      id="campaign_name"
                      value={campaignData.campaign_name}
                      onChange={(e) => setCampaignData({ ...campaignData, campaign_name: e.target.value })}
                      placeholder="Spring Promotion 2024"
                    />
                  </div>
                  <div className="col-span-2">
                    <Label htmlFor="objective">Campaign Objective</Label>
                    <Select
                      value={campaignData.objective}
                      onValueChange={(value) => setCampaignData({ ...campaignData, objective: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="REACH">Reach</SelectItem>
                        <SelectItem value="VIDEO_VIEWS">Video Views</SelectItem>
                        <SelectItem value="ENGAGEMENTS">Engagements</SelectItem>
                        <SelectItem value="AWARENESS">Brand Awareness</SelectItem>
                        <SelectItem value="WEBSITE_CLICKS">Website Clicks</SelectItem>
                        <SelectItem value="APP_INSTALLS">App Installs</SelectItem>
                        <SelectItem value="FOLLOWERS">Followers</SelectItem>
                        <SelectItem value="APP_RE_ENGAGEMENTS">App Re-engagements</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="daily_budget">Daily Budget ($)</Label>
                    <Input
                      id="daily_budget"
                      type="number"
                      value={campaignData.daily_budget}
                      onChange={(e) => setCampaignData({ ...campaignData, daily_budget: e.target.value })}
                      placeholder="50"
                    />
                  </div>
                  <div>
                    <Label htmlFor="total_budget">Total Budget ($)</Label>
                    <Input
                      id="total_budget"
                      type="number"
                      value={campaignData.total_budget}
                      onChange={(e) => setCampaignData({ ...campaignData, total_budget: e.target.value })}
                      placeholder="1500"
                    />
                  </div>
                  <div>
                    <Label htmlFor="start_time">Start Time</Label>
                    <Input
                      id="start_time"
                      type="datetime-local"
                      value={campaignData.start_time}
                      onChange={(e) => setCampaignData({ ...campaignData, start_time: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="end_time">End Time</Label>
                    <Input
                      id="end_time"
                      type="datetime-local"
                      value={campaignData.end_time}
                      onChange={(e) => setCampaignData({ ...campaignData, end_time: e.target.value })}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateCampaign(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateCampaign} disabled={creatingCampaign}>
                    {creatingCampaign ? "Creating..." : "Create Campaign"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {loadingCampaigns ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-blue-400 rounded-full" />
              </CardContent>
            </Card>
          ) : campaigns.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {campaigns.map((campaign) => (
                <Card key={campaign.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{campaign.campaign_name}</CardTitle>
                      <Badge variant={campaign.status === 'ACTIVE' ? 'default' : 'secondary'}>
                        {campaign.status}
                      </Badge>
                    </div>
                    <CardDescription>
                      {campaign.objective}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {campaign.daily_budget && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Daily Budget:</span>
                        <span className="font-medium">${(campaign.daily_budget / 1000000).toFixed(2)}</span>
                      </div>
                    )}
                    {campaign.total_budget && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Total Budget:</span>
                        <span className="font-medium">${(campaign.total_budget / 1000000).toFixed(2)}</span>
                      </div>
                    )}
                    {campaign.insights && Object.keys(campaign.insights).length > 0 && (
                      <div className="pt-3 border-t">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          {campaign.insights.impressions && (
                            <div>
                              <div className="text-gray-600">Impressions</div>
                              <div className="font-medium">{campaign.insights.impressions.toLocaleString()}</div>
                            </div>
                          )}
                          {campaign.insights.engagements && (
                            <div>
                              <div className="text-gray-600">Engagements</div>
                              <div className="font-medium">{campaign.insights.engagements.toLocaleString()}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : selectedAccount ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Target className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Campaigns Yet</h3>
                <p className="text-gray-600 text-center mb-4">
                  Create your first Twitter advertising campaign to start reaching your audience.
                </p>
                <Button onClick={() => setShowCreateCampaign(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create First Campaign
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Twitter className="w-12 h-12 text-blue-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Select Ad Account</h3>
                <p className="text-gray-600 text-center">
                  Choose a Twitter ad account to view and manage campaigns.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="streaming" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Real-time Tweet Stream</h3>
            <Dialog open={showCreateRule} onOpenChange={setShowCreateRule}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  New Stream Rule
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create Stream Rule</DialogTitle>
                  <DialogDescription>
                    Set up a rule to capture tweets in real-time based on keywords, hashtags, or other criteria.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="rule_value">Rule Query</Label>
                    <Input
                      id="rule_value"
                      value={ruleData.rule_value}
                      onChange={(e) => setRuleData({ ...ruleData, rule_value: e.target.value })}
                      placeholder="#AI OR #MachineLearning -is:retweet"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Use Twitter search operators. Example: "#AI OR #MachineLearning -is:retweet"
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="rule_tag">Rule Tag</Label>
                    <Input
                      id="rule_tag"
                      value={ruleData.rule_tag}
                      onChange={(e) => setRuleData({ ...ruleData, rule_tag: e.target.value })}
                      placeholder="AI_Discussion"
                    />
                  </div>
                  <div>
                    <Label htmlFor="rule_description">Description</Label>
                    <Textarea
                      id="rule_description"
                      value={ruleData.rule_description}
                      onChange={(e) => setRuleData({ ...ruleData, rule_description: e.target.value })}
                      placeholder="Captures tweets about AI and Machine Learning discussions"
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateRule(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateRule} disabled={creatingRule}>
                    {creatingRule ? "Creating..." : "Create Rule"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Stream Rules ({streamRules.length})</CardTitle>
                <CardDescription>Active filters for real-time tweet capture</CardDescription>
              </CardHeader>
              <CardContent>
                {loadingRules ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin w-6 h-6 border-4 border-gray-200 border-t-blue-400 rounded-full" />
                  </div>
                ) : streamRules.length > 0 ? (
                  <div className="space-y-3">
                    {streamRules.map((rule) => (
                      <div key={rule.id} className="p-3 border rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium">{rule.rule_tag}</h4>
                          <Badge variant={rule.is_active ? 'default' : 'secondary'}>
                            {rule.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">{rule.rule_value}</p>
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>Tweets captured: {rule.tweet_count}</span>
                          <span>Created: {new Date(rule.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Radio className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">No stream rules configured yet.</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Stream Tweets</CardTitle>
                <CardDescription>Latest tweets captured by your rules</CardDescription>
              </CardHeader>
              <CardContent>
                {loadingTweets ? (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin w-6 h-6 border-4 border-gray-200 border-t-blue-400 rounded-full" />
                  </div>
                ) : streamTweets.length > 0 ? (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {streamTweets.slice(0, 10).map((tweet) => (
                      <div key={tweet.id} className="p-3 border rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-medium text-sm">@{tweet.author_username}</span>
                          <span className="text-xs text-gray-500">
                            {new Date(tweet.created_at).toLocaleString()}
                          </span>
                          {tweet.sentiment_score && (
                            <Badge variant="outline" className="text-xs">
                              Sentiment: {tweet.sentiment_score > 0 ? 'Positive' : tweet.sentiment_score < 0 ? 'Negative' : 'Neutral'}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 mb-2">{tweet.tweet_text}</p>
                        {tweet.public_metrics && (
                          <div className="flex gap-4 text-xs text-gray-500">
                            <span>♥ {tweet.public_metrics.like_count}</span>
                            <span>🔄 {tweet.public_metrics.retweet_count}</span>
                            <span>💬 {tweet.public_metrics.reply_count}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Twitter className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">No tweets captured yet.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="bulk" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Bulk Operations</h3>
            <Dialog open={showBulkOperation} onOpenChange={setShowBulkOperation}>
              <DialogTrigger asChild>
                <Button>
                  <Upload className="w-4 h-4 mr-2" />
                  New Bulk Operation
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create Bulk Operation</DialogTitle>
                  <DialogDescription>
                    Process multiple actions at once with intelligent rate limiting.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="operation_type">Operation Type</Label>
                    <Select
                      value={bulkData.operation_type}
                      onValueChange={(value) => setBulkData({ ...bulkData, operation_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BULK_TWEET">Bulk Tweet Posting</SelectItem>
                        <SelectItem value="BULK_FOLLOW">Bulk Follow Users</SelectItem>
                        <SelectItem value="BULK_LIKE">Bulk Like Tweets</SelectItem>
                        <SelectItem value="BULK_RETWEET">Bulk Retweet</SelectItem>
                        <SelectItem value="BULK_DELETE">Bulk Delete Tweets</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="items">Data (one per line)</Label>
                    <Textarea
                      id="items"
                      value={bulkData.items}
                      onChange={(e) => setBulkData({ ...bulkData, items: e.target.value })}
                      placeholder={
                        bulkData.operation_type === 'BULK_TWEET' 
                          ? "Tweet text 1\nTweet text 2\nTweet text 3"
                          : bulkData.operation_type === 'BULK_FOLLOW'
                          ? "user_id_1\nuser_id_2\nuser_id_3"
                          : "tweet_id_1\ntweet_id_2\ntweet_id_3"
                      }
                      rows={6}
                    />
                  </div>
                  <div>
                    <Label htmlFor="schedule_time">Schedule Time (optional)</Label>
                    <Input
                      id="schedule_time"
                      type="datetime-local"
                      value={bulkData.schedule_time}
                      onChange={(e) => setBulkData({ ...bulkData, schedule_time: e.target.value })}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Leave empty to process immediately
                    </p>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowBulkOperation(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleBulkOperation} disabled={processingBulk}>
                    {processingBulk ? "Processing..." : "Start Operation"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {loadingOperations ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-blue-400 rounded-full" />
              </CardContent>
            </Card>
          ) : bulkOperations.length > 0 ? (
            <div className="space-y-4">
              {bulkOperations.map((operation) => (
                <Card key={operation.id}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">
                        {operation.operation_type.replace('BULK_', '').replace('_', ' ')}
                      </CardTitle>
                      <Badge variant={
                        operation.status === 'COMPLETED' ? 'default' :
                        operation.status === 'PROCESSING' ? 'secondary' :
                        operation.status === 'FAILED' ? 'destructive' : 'outline'
                      }>
                        {operation.status}
                      </Badge>
                    </div>
                    <CardDescription>
                      {operation.total_items} items • Created {new Date(operation.created_date).toLocaleString()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Progress:</span>
                      <span>{operation.processed_items}/{operation.total_items}</span>
                    </div>
                    <Progress 
                      value={(operation.processed_items / operation.total_items) * 100}
                      className="w-full"
                    />
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Successful:</span>
                        <span className="font-medium ml-2 text-green-600">{operation.successful_items}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">Failed:</span>
                        <span className="font-medium ml-2 text-red-600">{operation.failed_items}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">Rate Resets:</span>
                        <span className="font-medium ml-2">{operation.rate_limit_resets}</span>
                      </div>
                    </div>
                    {operation.error_log && operation.error_log.length > 0 && (
                      <div className="mt-3 p-2 bg-red-50 rounded-lg">
                        <p className="text-xs text-red-800 font-medium">Recent Errors:</p>
                        <div className="text-xs text-red-700 mt-1">
                          {operation.error_log.slice(0, 3).map((error, index) => (
                            <div key={index}>{error}</div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Zap className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Bulk Operations</h3>
                <p className="text-gray-600 text-center mb-4">
                  Create bulk operations to process multiple actions efficiently.
                </p>
                <Button onClick={() => setShowBulkOperation(true)}>
                  <Upload className="w-4 h-4 mr-2" />
                  Start First Operation
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <BarChart3 className="w-12 h-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Advanced Analytics</h3>
              <p className="text-gray-600 text-center mb-4">
                Comprehensive Twitter marketing insights and performance metrics.
              </p>
              <Badge variant="outline">Coming Soon</Badge>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}