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
import { LinkedInAdAccount } from "@/api/entities";
import { LinkedInCampaign } from "@/api/entities";
import { LinkedInCompanyPage } from "@/api/entities";
import { LinkedInLeadGenForm } from "@/api/entities";
import { LinkedInLead } from "@/api/entities";
import { Linkedin, Plus, Users, Target, TrendingUp, FileText, Download } from 'lucide-react';
import { toast, Toaster } from 'sonner';

// Import LinkedIn functions
const importFunction = async (moduleName) => {
  try {
    const module = await import(`@/api/functions/${moduleName}`);
    return module[moduleName];
  } catch (error) {
    console.warn(`Function ${moduleName} not available:`, error);
    return null;
  }
};

export default function LinkedInAdsManager() {
  const [adAccounts, setAdAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [campaigns, setCampaigns] = useState([]);
  const [companyPages, setCompanyPages] = useState([]);
  const [leadGenForms, setLeadGenForms] = useState([]);
  const [leads, setLeads] = useState([]);
  const [selectedForm, setSelectedForm] = useState('');
  
  // Loading states
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [loadingCampaigns, setLoadingCampaigns] = useState(false);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [loadingLeads, setLoadingLeads] = useState(false);

  // Dialog states
  const [showCreateCampaign, setShowCreateCampaign] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creatingCampaign, setCreatingCampaign] = useState(false);
  const [creatingForm, setCreatingForm] = useState(false);

  // Form states
  const [campaignData, setCampaignData] = useState({
    campaign_name: '',
    campaign_type: 'SPONSORED_CONTENT',
    objective: 'AWARENESS',
    daily_budget: '',
    total_budget: '',
    bid_type: 'CPC',
    bid_amount: '',
    start_date: '',
    end_date: ''
  });

  const [formData, setFormData] = useState({
    form_name: '',
    headline: '',
    description: '',
    thank_you_message: '',
    privacy_policy_url: '',
    form_fields: [
      { field_type: 'FIRST_NAME', required: true },
      { field_type: 'LAST_NAME', required: true },
      { field_type: 'EMAIL', required: true }
    ]
  });

  const loadAdAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const linkedinGetAdAccounts = await importFunction('linkedinGetAdAccounts');
      if (!linkedinGetAdAccounts) {
        toast.error("LinkedIn Ad Accounts function not available");
        return;
      }
      
      const { data } = await linkedinGetAdAccounts();
      setAdAccounts(data?.ad_accounts || []);
      
      if ((data?.ad_accounts || []).length === 0) {
        toast.info("No LinkedIn ad accounts found. Make sure your account has advertising access.");
      }
    } catch (error) {
      console.error("Failed to load ad accounts:", error);
      toast.error("Failed to load LinkedIn ad accounts");
    } finally {
      setLoadingAccounts(false);
    }
  };

  const loadCampaigns = useCallback(async () => {
    if (!selectedAccount) return;
    
    setLoadingCampaigns(true);
    try {
      const campaignsList = await LinkedInCampaign.filter({ 
        ad_account_id: selectedAccount 
      }, '-updated_time');
      setCampaigns(campaignsList || []);
    } catch (error) {
      console.error("Failed to load campaigns:", error);
      toast.error("Failed to load campaigns");
    } finally {
      setLoadingCampaigns(false);
    }
  }, [selectedAccount]);

  const loadCompanyPages = async () => {
    setLoadingCompanies(true);
    try {
      const linkedinGetCompanyPages = await importFunction('linkedinGetCompanyPages');
      if (!linkedinGetCompanyPages) {
        toast.error("LinkedIn Company Pages function not available");
        return;
      }
      
      const { data } = await linkedinGetCompanyPages();
      setCompanyPages(data?.companies || []);
    } catch (error) {
      console.error("Failed to load company pages:", error);
      toast.error("Failed to load company pages");
    } finally {
      setLoadingCompanies(false);
    }
  };

  const loadLeadGenForms = async () => {
    try {
      const forms = await LinkedInLeadGenForm.list('-created_time');
      setLeadGenForms(forms || []);
    } catch (error) {
      console.error("Failed to load lead gen forms:", error);
    }
  };

  const loadLeads = useCallback(async () => {
    if (!selectedForm) return;
    
    setLoadingLeads(true);
    try {
      const linkedinGetLeads = await importFunction('linkedinGetLeads');
      if (!linkedinGetLeads) {
        toast.error("LinkedIn Get Leads function not available");
        return;
      }
      
      const { data } = await linkedinGetLeads({ form_id: selectedForm });
      setLeads(data?.leads || []);
    } catch (error) {
      console.error("Failed to load leads:", error);
      toast.error("Failed to load leads");
    } finally {
      setLoadingLeads(false);
    }
  }, [selectedForm]);

  const handleCreateCampaign = async () => {
    if (!selectedAccount || !campaignData.campaign_name) {
      toast.error("Please select an ad account and enter a campaign name");
      return;
    }

    setCreatingCampaign(true);
    try {
      const linkedinCreateCampaign = await importFunction('linkedinCreateCampaign');
      if (!linkedinCreateCampaign) {
        toast.error("LinkedIn Create Campaign function not available");
        return;
      }
      
      const { data } = await linkedinCreateCampaign({
        ad_account_id: selectedAccount,
        ...campaignData,
        daily_budget: campaignData.daily_budget ? parseFloat(campaignData.daily_budget) : null,
        total_budget: campaignData.total_budget ? parseFloat(campaignData.total_budget) : null,
        bid_amount: campaignData.bid_amount ? parseFloat(campaignData.bid_amount) : null
      });
      
      if (data?.success) {
        toast.success("Campaign created successfully!");
        setShowCreateCampaign(false);
        setCampaignData({
          campaign_name: '',
          campaign_type: 'SPONSORED_CONTENT',
          objective: 'AWARENESS',
          daily_budget: '',
          total_budget: '',
          bid_type: 'CPC',
          bid_amount: '',
          start_date: '',
          end_date: ''
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

  const handleCreateLeadGenForm = async () => {
    if (!formData.form_name || !formData.headline) {
      toast.error("Please enter form name and headline");
      return;
    }

    setCreatingForm(true);
    try {
      const linkedinCreateLeadGenForm = await importFunction('linkedinCreateLeadGenForm');
      if (!linkedinCreateLeadGenForm) {
        toast.error("LinkedIn Create Lead Gen Form function not available");
        return;
      }
      
      const { data } = await linkedinCreateLeadGenForm({
        campaign_id: 'standalone', // Can be linked to specific campaign later
        ...formData
      });
      
      if (data?.success) {
        toast.success("Lead generation form created successfully!");
        setShowCreateForm(false);
        setFormData({
          form_name: '',
          headline: '',
          description: '',
          thank_you_message: '',
          privacy_policy_url: '',
          form_fields: [
            { field_type: 'FIRST_NAME', required: true },
            { field_type: 'LAST_NAME', required: true },
            { field_type: 'EMAIL', required: true }
          ]
        });
        loadLeadGenForms();
      } else {
        toast.error(data?.error || "Failed to create form");
      }
    } catch (error) {
      console.error("Form creation failed:", error);
      toast.error("Failed to create lead gen form");
    } finally {
      setCreatingForm(false);
    }
  };

  useEffect(() => {
    loadAdAccounts();
    loadCompanyPages();
    loadLeadGenForms();
  }, []);

  useEffect(() => {
    if (selectedAccount) {
      loadCampaigns();
    }
  }, [selectedAccount, loadCampaigns]);

  useEffect(() => {
    if (selectedForm) {
      loadLeads();
    }
  }, [selectedForm, loadLeads]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <Toaster richColors />
      
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <Linkedin className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">LinkedIn Ads Manager</h1>
            <p className="text-gray-600">Manage campaigns, lead generation, and company pages</p>
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
          <TabsTrigger value="leads" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Lead Generation
          </TabsTrigger>
          <TabsTrigger value="companies" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Company Pages
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
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
                  <DialogTitle>Create LinkedIn Campaign</DialogTitle>
                  <DialogDescription>
                    Set up a new advertising campaign for professional audience targeting.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <Label htmlFor="campaign_name">Campaign Name</Label>
                    <Input
                      id="campaign_name"
                      value={campaignData.campaign_name}
                      onChange={(e) => setCampaignData({ ...campaignData, campaign_name: e.target.value })}
                      placeholder="Professional Services Q1 Campaign"
                    />
                  </div>
                  <div>
                    <Label htmlFor="campaign_type">Campaign Type</Label>
                    <Select
                      value={campaignData.campaign_type}
                      onValueChange={(value) => setCampaignData({ ...campaignData, campaign_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="SPONSORED_CONTENT">Sponsored Content</SelectItem>
                        <SelectItem value="SPONSORED_MESSAGING">Sponsored Messaging</SelectItem>
                        <SelectItem value="TEXT_ADS">Text Ads</SelectItem>
                        <SelectItem value="DYNAMIC_ADS">Dynamic Ads</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="objective">Objective</Label>
                    <Select
                      value={campaignData.objective}
                      onValueChange={(value) => setCampaignData({ ...campaignData, objective: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="AWARENESS">Brand Awareness</SelectItem>
                        <SelectItem value="CONSIDERATION">Consideration</SelectItem>
                        <SelectItem value="CONVERSIONS">Conversions</SelectItem>
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
                      placeholder="100"
                    />
                  </div>
                  <div>
                    <Label htmlFor="total_budget">Total Budget ($)</Label>
                    <Input
                      id="total_budget"
                      type="number"
                      value={campaignData.total_budget}
                      onChange={(e) => setCampaignData({ ...campaignData, total_budget: e.target.value })}
                      placeholder="3000"
                    />
                  </div>
                  <div>
                    <Label htmlFor="bid_type">Bid Type</Label>
                    <Select
                      value={campaignData.bid_type}
                      onValueChange={(value) => setCampaignData({ ...campaignData, bid_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="CPC">Cost Per Click (CPC)</SelectItem>
                        <SelectItem value="CPM">Cost Per Mille (CPM)</SelectItem>
                        <SelectItem value="CPA">Cost Per Action (CPA)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="bid_amount">Bid Amount ($)</Label>
                    <Input
                      id="bid_amount"
                      type="number"
                      step="0.01"
                      value={campaignData.bid_amount}
                      onChange={(e) => setCampaignData({ ...campaignData, bid_amount: e.target.value })}
                      placeholder="2.50"
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
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-blue-600 rounded-full" />
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
                      {campaign.campaign_type} • {campaign.objective}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {campaign.daily_budget && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Daily Budget:</span>
                        <span className="font-medium">${campaign.daily_budget}</span>
                      </div>
                    )}
                    {campaign.total_budget && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Total Budget:</span>
                        <span className="font-medium">${campaign.total_budget}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Bid Type:</span>
                      <span className="font-medium">{campaign.bid_type}</span>
                    </div>
                    {campaign.insights && Object.keys(campaign.insights).length > 0 && (
                      <div className="pt-3 border-t">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          {campaign.insights.impressions && (
                            <div>
                              <div className="text-gray-600">Impressions</div>
                              <div className="font-medium">{campaign.insights.impressions.toLocaleString()}</div>
                            </div>
                          )}
                          {campaign.insights.clicks && (
                            <div>
                              <div className="text-gray-600">Clicks</div>
                              <div className="font-medium">{campaign.insights.clicks.toLocaleString()}</div>
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
                  Create your first LinkedIn advertising campaign to start reaching professional audiences.
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
                <Linkedin className="w-12 h-12 text-blue-600 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Select Ad Account</h3>
                <p className="text-gray-600 text-center">
                  Choose a LinkedIn ad account to view and manage campaigns.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="leads" className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Select value={selectedForm} onValueChange={setSelectedForm}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Select Lead Gen Form" />
                </SelectTrigger>
                <SelectContent>
                  {leadGenForms.map((form) => (
                    <SelectItem key={form.id} value={form.form_id}>
                      {form.form_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={loadLeadGenForms}>
                Refresh Forms
              </Button>
            </div>
            <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  New Lead Gen Form
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create Lead Generation Form</DialogTitle>
                  <DialogDescription>
                    Design a form to capture leads from your LinkedIn campaigns.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="form_name">Form Name</Label>
                    <Input
                      id="form_name"
                      value={formData.form_name}
                      onChange={(e) => setFormData({ ...formData, form_name: e.target.value })}
                      placeholder="Professional Services Lead Form"
                    />
                  </div>
                  <div>
                    <Label htmlFor="headline">Headline</Label>
                    <Input
                      id="headline"
                      value={formData.headline}
                      onChange={(e) => setFormData({ ...formData, headline: e.target.value })}
                      placeholder="Get Expert Consultation"
                    />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Learn how our experts can help your business grow..."
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label htmlFor="thank_you_message">Thank You Message</Label>
                    <Input
                      id="thank_you_message"
                      value={formData.thank_you_message}
                      onChange={(e) => setFormData({ ...formData, thank_you_message: e.target.value })}
                      placeholder="Thank you for your interest! We'll be in touch soon."
                    />
                  </div>
                  <div>
                    <Label htmlFor="privacy_policy_url">Privacy Policy URL</Label>
                    <Input
                      id="privacy_policy_url"
                      type="url"
                      value={formData.privacy_policy_url}
                      onChange={(e) => setFormData({ ...formData, privacy_policy_url: e.target.value })}
                      placeholder="https://yourcompany.com/privacy"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateLeadGenForm} disabled={creatingForm}>
                    {creatingForm ? "Creating..." : "Create Form"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {selectedForm ? (
            <div className="space-y-6">
              {loadingLeads ? (
                <Card>
                  <CardContent className="flex justify-center py-8">
                    <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-blue-600 rounded-full" />
                  </CardContent>
                </Card>
              ) : leads.length > 0 ? (
                <>
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">Leads ({leads.length})</h3>
                    <Button variant="outline" onClick={loadLeads}>
                      <Download className="w-4 h-4 mr-2" />
                      Export CSV
                    </Button>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {leads.map((lead) => (
                      <Card key={lead.id} className="hover:shadow-lg transition-shadow">
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-lg">
                              {lead.lead_data?.first_name} {lead.lead_data?.last_name}
                            </CardTitle>
                            <Badge variant={
                              lead.lead_score >= 80 ? 'default' :
                              lead.lead_score >= 60 ? 'secondary' : 'outline'
                            }>
                              Score: {lead.lead_score}
                            </Badge>
                          </div>
                          <CardDescription>
                            Submitted {new Date(lead.submitted_at).toLocaleDateString()}
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                          {lead.lead_data?.email && (
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Email:</span>
                              <span className="font-medium">{lead.lead_data.email}</span>
                            </div>
                          )}
                          {lead.lead_data?.company && (
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Company:</span>
                              <span className="font-medium">{lead.lead_data.company}</span>
                            </div>
                          )}
                          {lead.lead_data?.job_title && (
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Title:</span>
                              <span className="font-medium">{lead.lead_data.job_title}</span>
                            </div>
                          )}
                          {lead.lead_data?.phone && (
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-600">Phone:</span>
                              <span className="font-medium">{lead.lead_data.phone}</span>
                            </div>
                          )}
                          <div className="pt-2">
                            <Badge variant={
                              lead.lead_status === 'new' ? 'default' :
                              lead.lead_status === 'contacted' ? 'secondary' :
                              lead.lead_status === 'qualified' ? 'default' :
                              lead.lead_status === 'converted' ? 'default' : 'outline'
                            }>
                              {lead.lead_status}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </>
              ) : (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Users className="w-12 h-12 text-gray-400 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No Leads Yet</h3>
                    <p className="text-gray-600 text-center">
                      Leads will appear here once your form starts receiving submissions.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Users className="w-12 h-12 text-blue-600 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Select Lead Generation Form</h3>
                <p className="text-gray-600 text-center mb-4">
                  Choose a form to view and manage leads, or create a new one.
                </p>
                <Button onClick={() => setShowCreateForm(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create First Form
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="companies" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Company Pages</h3>
            <Button variant="outline" onClick={loadCompanyPages} disabled={loadingCompanies}>
              {loadingCompanies ? "Loading..." : "Refresh Pages"}
            </Button>
          </div>

          {loadingCompanies ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-blue-600 rounded-full" />
              </CardContent>
            </Card>
          ) : companyPages.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {companyPages.map((company) => (
                <Card key={company.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3">
                      {company.logo_url ? (
                        <img
                          src={company.logo_url}
                          alt={`${company.company_name} logo`}
                          className="w-10 h-10 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                          <TrendingUp className="w-5 h-5 text-blue-600" />
                        </div>
                      )}
                      <div className="flex-1">
                        <CardTitle className="text-lg">{company.company_name}</CardTitle>
                        {company.is_verified && (
                          <Badge variant="outline" className="mt-1">
                            ✓ Verified
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {company.industry && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Industry:</span>
                        <span className="font-medium">{company.industry}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Followers:</span>
                      <span className="font-medium">{company.follower_count?.toLocaleString() || 0}</span>
                    </div>
                    {company.website && (
                      <div className="text-sm">
                        <span className="text-gray-600">Website: </span>
                        <a 
                          href={company.website} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {company.website}
                        </a>
                      </div>
                    )}
                    {company.description && (
                      <div className="text-sm">
                        <p className="text-gray-600 line-clamp-3">{company.description}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <TrendingUp className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Company Pages</h3>
                <p className="text-gray-600 text-center mb-4">
                  You need admin access to LinkedIn company pages to manage them here.
                </p>
                <Button onClick={loadCompanyPages}>
                  Refresh Pages
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FileText className="w-12 h-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Analytics Dashboard</h3>
              <p className="text-gray-600 text-center mb-4">
                Comprehensive analytics and insights will be available here.
              </p>
              <Badge variant="outline">Coming Soon</Badge>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}