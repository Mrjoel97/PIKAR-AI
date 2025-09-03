
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CheckCircle2, XCircle, AlertTriangle, Loader2, TestTube, Zap, Link as LinkIcon } from 'lucide-react';
import { toast, Toaster } from 'sonner';

// Import functions safely
const importFunction = async (moduleName) => {
  try {
    const functions = await import('@/api/functions');
    return functions[moduleName];
  } catch (error) {
    console.warn(`Function ${moduleName} not available:`, error);
    return null;
  }
};

const PLATFORMS = {
  meta: {
    name: 'Meta (Facebook/Instagram)',
    color: 'bg-blue-500',
    functions: [
      'metaValidateSecrets',
      'metaOauthStart', 
      'metaOauthCallback',
      'metaListPages',
      'metaPostPage',
      'metaGetAdAccounts',
      'metaCreateCampaign',
      'metaPublishInstagram',
      'metaGetInsights'
    ]
  },
  twitter: {
    name: 'X (Twitter)',
    color: 'bg-black',
    functions: [
      'twitterValidateSecrets',
      'twitterOauthStart',
      'twitterOauthCallback', 
      'twitterListAccount',
      'twitterPostTweet',
      'twitterGetAdAccounts',
      'twitterCreateCampaign',
      'twitterCreateStreamRule',
      'twitterBulkOperation'
    ]
  },
  linkedin: {
    name: 'LinkedIn',
    color: 'bg-blue-600',
    functions: [
      'linkedinValidateSecrets',
      'linkedinOauthStart',
      'linkedinOauthCallback',
      'linkedinGetProfile',
      'linkedinPostShare',
      'linkedinGetAdAccounts',
      'linkedinGetCompanyPages',
      'linkedinCreateCampaign',
      'linkedinCreateLeadGenForm',
      'linkedinGetLeads'
    ]
  },
  youtube: {
    name: 'YouTube',
    color: 'bg-red-500',
    functions: [
      'youtubeValidateSecrets',
      'youtubeOauthStart',
      'youtubeOauthCallback',
      'youtubeGetChannel',
      'youtubeUploadVideo',
      'youtubeGetAnalytics',
      'youtubeCreatePlaylist',
      'youtubeManageSubscriptions'
    ]
  },
  tiktok: {
    name: 'TikTok',
    color: 'bg-black',
    functions: [
      'tiktokValidateSecrets',
      'tiktokOauthStart', 
      'tiktokOauthCallback',
      'tiktokGetAccount',
      'tiktokUploadVideo',
      'tiktokGetVideos'
    ]
  }
};

export default function SocialPlatformTester() {
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState('meta');
  const [testMessage, setTestMessage] = useState('Testing PIKAR AI social media integration! 🚀');

  const updateTestResult = (platform, functionName, status, details = null) => {
    setTestResults(prev => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        [functionName]: { status, details, timestamp: new Date().toISOString() }
      }
    }));
  };

  const getExpectedErrorType = (error, functionName) => {
    const errorStr = String(error).toLowerCase(); // Ensure error is a string for comparison
    
    // Configuration errors (missing environment variables)
    if (errorStr.includes('missing') && (errorStr.includes('app_id') || errorStr.includes('redirect_uri') || errorStr.includes('encryption_key') || errorStr.includes('client_id') || errorStr.includes('client_secret'))) {
      return 'config';
    }
    
    // Authentication errors (no account connected or invalid token)
    if (errorStr.includes('not connected') || errorStr.includes('no meta account') || errorStr.includes('unauthorized') || errorStr.includes('invalid token') || errorStr.includes('access token')) {
      return 'auth';
    }
    
    // Missing required parameters for the specific function call (logic error in test setup)
    if (errorStr.includes('missing required field') || errorStr.includes('missing required fields')) {
      return 'params';
    }
    
    return 'error';
  };

  const testFunction = async (platform, functionName) => {
    updateTestResult(platform, functionName, 'testing');
    
    try {
      const func = await importFunction(functionName);
      if (!func) {
        updateTestResult(platform, functionName, 'missing', 'Function not implemented');
        return;
      }

      let testParams = {};
      
      // Add comprehensive test parameters based on function type
      if (functionName.includes('Post') && !functionName.includes('Create')) {
        if (platform === 'meta') {
          testParams = { page_id: 'test_page_123', message: testMessage };
        } else if (platform === 'twitter') {
          testParams = { text: testMessage };
        } else if (platform === 'linkedin') {
          testParams = { text: testMessage };
        }
      } else if (functionName.includes('Upload') || functionName.includes('Publish')) {
        if (platform === 'meta' && functionName === 'metaPublishInstagram') {
          testParams = { 
            instagram_account_id: 'test_ig_account_123',
            image_url: 'https://via.placeholder.com/1080x1080.jpg',
            caption: testMessage
          };
        } else {
          testParams = { 
            title: 'Test Video',
            description: testMessage,
            video_file_url: 'https://example.com/test.mp4'
          };
        }
      } else if (functionName.includes('Create') && functionName.includes('Campaign')) {
        if (platform === 'meta') {
          testParams = {
            ad_account_id: 'act_test_123456',
            campaign_name: 'Test Campaign',
            objective: 'AWARENESS',
            daily_budget: 1000
          };
        } else {
          testParams = {
            campaign_name: 'Test Campaign',
            objective: 'AWARENESS',
            daily_budget: 1000
          };
        }
      } else if (functionName.includes('Insights') || functionName.includes('Analytics')) {
        testParams = {
          object_id: 'test_object_123',
          object_type: 'campaign',
          metrics: ['impressions', 'clicks', 'spend']
        };
      } else if (functionName.includes('ValidateSecrets')) {
        // ValidateSecrets might not need specific params, it often checks env vars
        testParams = {}; 
      }
      // For functions like OauthStart/Callback, List/Get, no specific params might be needed for a test call
      // The actual functions are expected to handle their own internal logic based on environment/auth

      const response = await func(testParams);
      const { data, status } = response;
      
      if (status >= 200 && status < 300) {
        updateTestResult(platform, functionName, 'success', data);
      } else {
        // Handle expected errors gracefully
        const errorDetails = data?.error || data?.message || `HTTP ${status}`;
        const errorType = getExpectedErrorType(errorDetails, functionName);
        updateTestResult(platform, functionName, errorType, errorDetails);
      }
    } catch (error) {
      // Handle caught errors gracefully
      const errorType = getExpectedErrorType(error.message, functionName);
      updateTestResult(platform, functionName, errorType, error.message);
    }
  };

  const testPlatform = async (platform) => {
    setTesting(true);
    const functions = PLATFORMS[platform].functions;
    
    for (const functionName of functions) {
      await testFunction(platform, functionName);
      // Small delay to prevent overwhelming
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setTesting(false);
  };

  const testAllPlatforms = async () => {
    setTesting(true);
    
    for (const platform of Object.keys(PLATFORMS)) {
      await testPlatform(platform);
    }
    
    setTesting(false);
    toast.success('All platforms tested!');
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'config':
        return <AlertTriangle className="w-4 h-4 text-orange-500" />;
      case 'auth':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'params':
        return <AlertTriangle className="w-4 h-4 text-purple-500" />; {/* Changed to purple for better distinction */}
      case 'missing':
        return <AlertTriangle className="w-4 h-4 text-gray-500" />; {/* Changed to gray for missing function */}
      case 'testing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <div className="w-4 h-4 bg-gray-300 rounded-full" />;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'success':
        return <Badge className="bg-green-100 text-green-800">Working</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-800">Error</Badge>;
      case 'config':
        return <Badge className="bg-orange-100 text-orange-800">Config Needed</Badge>;
      case 'auth':
        return <Badge className="bg-yellow-100 text-yellow-800">Auth Needed</Badge>;
      case 'params':
        return <Badge className="bg-purple-100 text-purple-800">Param Error</Badge>; {/* Changed to purple for better distinction */}
      case 'missing':
        return <Badge className="bg-gray-100 text-gray-800">Missing</Badge>; {/* Changed to gray for missing function */}
      case 'testing':
        return <Badge className="bg-blue-100 text-blue-800">Testing...</Badge>;
      default:
        return <Badge variant="outline">Untested</Badge>;
    }
  };

  const getPlatformSummary = (platform) => {
    const results = testResults[platform] || {};
    const functions = PLATFORMS[platform].functions;
    const tested = Object.keys(results).length;
    const successful = Object.values(results).filter(r => r.status === 'success').length;
    const errors = Object.values(results).filter(r => r.status === 'error').length;
    const configNeeded = Object.values(results).filter(r => r.status === 'config').length;
    const authNeeded = Object.values(results).filter(r => r.status === 'auth').length;
    const paramsError = Object.values(results).filter(r => r.status === 'params').length;
    const missing = Object.values(results).filter(r => r.status === 'missing').length;
    
    return { tested, successful, errors, configNeeded, authNeeded, paramsError, missing, total: functions.length };
  };

  const connectToPlatform = async (platform) => {
    try {
      const oauthStartFunc = await importFunction(`${platform}OauthStart`);
      if (!oauthStartFunc) {
        toast.error(`OAuth start function not available for ${platform}`);
        return;
      }
      
      const { data } = await oauthStartFunc();
      if (data?.auth_url) {
        window.open(data.auth_url, `${platform}_connect`, 'width=800,height=800');
      } else {
        toast.error('Failed to get authorization URL');
      }
    } catch (error) {
      toast.error(`Failed to connect to ${platform}: ${error.message}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <Toaster richColors />
      
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TestTube className="w-8 h-8 text-emerald-600" />
          <div>
            <h1 className="text-3xl font-bold">Social Platform API Tester</h1>
            <p className="text-gray-600">Comprehensive testing suite for all social media integrations</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button onClick={testAllPlatforms} disabled={testing} size="lg">
            {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
            Test All Platforms
          </Button>
        </div>
      </header>

      {/* Platform Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {Object.entries(PLATFORMS).map(([key, platform]) => {
          const summary = getPlatformSummary(key);
          const workingRate = summary.total > 0 ? Math.round((summary.successful / summary.total) * 100) : 0;
          
          return (
            <Card key={key} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => setSelectedPlatform(key)}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className={`w-4 h-4 rounded-full ${platform.color}`} />
                  <Badge variant="outline">{summary.tested}/{summary.total}</Badge>
                </div>
                <CardTitle className="text-base">{platform.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Working</span>
                    <span className="font-medium">{workingRate}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-emerald-600 h-2 rounded-full transition-all" 
                      style={{ width: `${workingRate}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>✓ {summary.successful}</span>
                    <span>⚙️ {summary.configNeeded}</span>
                    <span>🔐 {summary.authNeeded}</span>
                    <span>✗ {summary.errors}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Detailed Testing Interface */}
      <Tabs value={selectedPlatform} onValueChange={setSelectedPlatform}>
        <TabsList className="grid w-full grid-cols-5">
          {Object.entries(PLATFORMS).map(([key, platform]) => (
            <TabsTrigger key={key} value={key} className="text-xs">
              {platform.name.split(' ')[0]}
            </TabsTrigger>
          ))}
        </TabsList>

        {Object.entries(PLATFORMS).map(([key, platform]) => (
          <TabsContent key={key} value={key} className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold">{platform.name} Integration</h3>
                <p className="text-gray-600">Test and verify all API functions</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => connectToPlatform(key)}>
                  <LinkIcon className="w-4 h-4 mr-2" />
                  Connect Account
                </Button>
                <Button onClick={() => testPlatform(key)} disabled={testing}>
                  {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <TestTube className="w-4 h-4 mr-2" />}
                  Test Platform
                </Button>
              </div>
            </div>

            {/* Function Testing Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {platform.functions.map((functionName) => {
                const result = testResults[key]?.[functionName];
                
                return (
                  <Card key={functionName} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">{functionName}</CardTitle>
                        {getStatusIcon(result?.status)}
                      </div>
                      <div className="flex justify-between items-center">
                        {getStatusBadge(result?.status)}
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => testFunction(key, functionName)}
                          disabled={testing}
                        >
                          Test
                        </Button>
                      </div>
                    </CardHeader>
                    {result && (
                      <CardContent className="pt-0">
                        {result.status === 'success' && (
                          <div className="text-xs text-green-600 bg-green-50 p-2 rounded">
                            ✓ Function working correctly
                          </div>
                        )}
                        {result.status === 'error' && (
                          <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                            ✗ {result.details}
                          </div>
                        )}
                        {result.status === 'missing' && (
                          <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                            ⚠ {result.details}
                          </div>
                        )}
                        {result.status === 'config' && (
                          <div className="text-xs text-orange-600 bg-orange-50 p-2 rounded">
                            ⚙️ Configuration needed: {result.details}
                          </div>
                        )}
                        {result.status === 'auth' && (
                          <div className="text-xs text-yellow-600 bg-yellow-50 p-2 rounded">
                            🔐 Authentication needed: {result.details}
                          </div>
                        )}
                        {result.status === 'params' && (
                          <div className="text-xs text-purple-600 bg-purple-50 p-2 rounded">
                            ❓ Parameter issue: {result.details}
                          </div>
                        )}
                        {result.timestamp && (
                          <div className="text-xs text-gray-500 mt-2">
                            Last tested: {new Date(result.timestamp).toLocaleTimeString()}
                          </div>
                        )}
                      </CardContent>
                    )}
                  </Card>
                );
              })}
            </div>

            {/* Test Message Configuration */}
            <Card>
              <CardHeader>
                <CardTitle>Test Configuration</CardTitle>
                <CardDescription>
                  Customize the test message used for posting functions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Test Message</label>
                    <Textarea
                      value={testMessage}
                      onChange={(e) => setTestMessage(e.target.value)}
                      placeholder="Enter test message for posting functions..."
                      rows={3}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>

      {/* Overall Status Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Integration Status Summary</CardTitle>
          <CardDescription>
            Overall health of social media platform integrations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Object.entries(PLATFORMS).map(([key, platform]) => {
              const summary = getPlatformSummary(key);
              const workingRate = summary.total > 0 ? Math.round((summary.successful / summary.total) * 100) : 0;
              
              return (
                <div key={key} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{platform.name}</span>
                    <span className="text-sm text-gray-500">{workingRate}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all ${
                        workingRate >= 80 ? 'bg-green-500' :
                        workingRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${workingRate}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Working: {summary.successful}</span>
                    <span>Errors: {summary.errors}</span>
                    <span>Config: {summary.configNeeded}</span>
                    <span>Auth: {summary.authNeeded}</span>
                    <span>Params: {summary.paramsError}</span>
                    <span>Missing: {summary.missing}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
