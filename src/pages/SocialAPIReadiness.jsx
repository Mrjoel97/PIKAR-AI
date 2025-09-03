
import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Plug, Shield, CheckCircle2, AlertTriangle, Download, Eye, Link as LinkIcon, Twitter, Copy, Linkedin, Youtube } from "lucide-react";
import { Link } from "react-router-dom";
import { createPageUrl } from "@/utils";

// Import entities
import { SocialCampaign } from "@/api/entities";
import { SocialAdVariant } from "@/api/entities";
import { SocialPost } from "@/api/entities";

// Import functions with error handling
const importFunction = async (moduleName) => {
  try {
    // Use the functions barrel file exported from src/api/functions.js
    const functions = await import('@/api/functions');
    return functions[moduleName];
  } catch (error) {
    console.warn(`Function ${moduleName} not available:`, error);
    return null;
  }
};

export default function SocialAPIReadiness() {
  const [campaignId, setCampaignId] = useState("");
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [pages, setPages] = useState([]);
  const [posting, setPosting] = useState(false);
  const [selectedPage, setSelectedPage] = useState("");
  const [postMessage, setPostMessage] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [validation, setValidation] = useState(null);
  const [validating, setValidating] = useState(false);

  // Twitter state
  const [twValidating, setTwValidating] = useState(false);
  const [twValidation, setTwValidation] = useState(null);
  const [twConnecting, setTwConnecting] = useState(false);
  const [twAccount, setTwAccount] = useState(null);
  const [twTweet, setTwTweet] = useState("");
  const [twPosting, setTwPosting] = useState(false);

  // LinkedIn state
  const [liValidating, setLiValidating] = useState(false);
  const [liValidation, setLiValidation] = useState(null);
  const [liConnecting, setLiConnecting] = useState(false);
  const [liProfile, setLiProfile] = useState(null);
  const [liPost, setLiPost] = useState("");
  const [liPosting, setLiPosting] = useState(false);

  // YouTube state
  const [ytValidating, setYtValidating] = useState(false);
  const [ytValidation, setYtValidation] = useState(null);
  const [ytConnecting, setYtConnecting] = useState(false);
  const [ytChannel, setYtChannel] = useState(null);

  // Safe notification system
  const notify = {
    success: (msg) => console.log("SUCCESS:", msg),
    error: (msg) => console.error("ERROR:", msg),
    info: (msg) => console.info("INFO:", msg)
  };

  // Platform data
  const platforms = [
    { name: "Meta (Facebook/Instagram) Marketing API", status: "Not connected", notes: "Requires backend functions, OAuth (ads_management, pages_manage_posts), app review, and rate-limit handling." },
    { name: "LinkedIn Ads API", status: "Not connected", notes: "Requires backend functions, OAuth (rw_organization_admin, ads), app approval." },
    { name: "X (Twitter) Ads API", status: "Not connected", notes: "Requires elevated access, OAuth, async job orchestration." },
    { name: "TikTok Ads API", status: "Not connected", notes: "Requires developer app, OAuth, creative upload flows." },
    { name: "YouTube (organic via Data API)", status: "Not connected", notes: "Requires OAuth scopes and upload quotas." }
  ];

  // Expected redirect URLs
  const expectedMetaRedirect = `${window.location.origin}/functions/metaOauthCallback`;
  const expectedTwitterRedirect = `${window.location.origin}/functions/twitterOauthCallback`;
  const expectedLinkedInRedirect = `${window.location.origin}/functions/linkedinOauthCallback`;
  const expectedYoutubeRedirect = `${window.location.origin}/functions/youtubeOauthCallback`;

  const handlePreview = async () => {
    if (!campaignId) {
      notify.error("Enter a Campaign ID to preview payloads.");
      return;
    }
    setLoading(true);
    try {
      const [campaign] = await SocialCampaign.filter({ id: campaignId });
      if (!campaign) {
        notify.error("Campaign not found.");
        return;
      }
      
      const variants = await SocialAdVariant.filter({ campaign_id: campaignId });
      const posts = await SocialPost.filter({ campaign_id: campaignId });

      const byPlatform = {};
      (variants || []).forEach((v) => {
        const key = v.platform || "Unknown";
        byPlatform[key] = byPlatform[key] || { ads: [], posts: [] };
        byPlatform[key].ads.push({
          variant_name: v.variant_name,
          headline: v.headline,
          body: v.body,
          cta: v.cta,
          creative_idea: v.creative_idea,
          hypothesis: v.hypothesis,
          metrics: v.metrics || {}
        });
      });
      
      (posts || []).forEach((p) => {
        const key = p.platform || "Unknown";
        byPlatform[key] = byPlatform[key] || { ads: [], posts: [] };
        byPlatform[key].posts.push({
          content_markdown: p.content,
          media_idea: p.media_idea,
          scheduled_time: p.scheduled_time || null,
          metrics: p.metrics || {}
        });
      });

      const exportPayload = {
        campaign: {
          id: campaign.id,
          name: campaign.campaign_name,
          brand: campaign.brand,
          objective: campaign.objective,
          timeframe: campaign.timeframe,
          platforms: campaign.platforms || []
        },
        platforms: byPlatform
      };

      setPreview(exportPayload);
      notify.success("Preview ready.");
    } catch (e) {
      console.error(e);
      notify.error("Failed to build preview.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!preview) return;
    const blob = new Blob([JSON.stringify(preview, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `social_api_payload_${preview?.campaign?.id || "campaign"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Function handlers with safe imports
  const connectMeta = async () => {
    setConnecting(true);
    try {
      const metaOauthStart = await importFunction('metaOauthStart');
      if (!metaOauthStart) {
        notify.error("Meta OAuth function not available");
        return;
      }
      
      const { data, status } = await metaOauthStart();
      const url = data?.auth_url;
      if (status !== 200 || !url) {
        notify.error(data?.error || "Failed to get Meta OAuth URL. Check META_* env vars.");
        return;
      }
      
      const popup = window.open(url, "meta_connect", "width=800,height=800");
      if (!popup) {
        window.location.href = url;
      }
    } catch (e) {
      console.error("Meta connect failed:", e);
      notify.error("Could not start Meta OAuth. Verify secrets and try again.");
    } finally {
      setConnecting(false);
    }
  };

  const loadPages = useCallback(async () => {
    try {
      const metaListPages = await importFunction('metaListPages');
      if (!metaListPages) return;
      
      const { data } = await metaListPages();
      setPages(data?.pages || []);
      if ((data?.pages || []).length === 0) {
        notify.info("No pages found. Connect Meta and grant permissions, then Refresh.");
      }
    } catch (e) {
      console.error("Failed to load pages:", e);
      notify.error("Failed to load pages. Please connect Meta first.");
    }
  }, [notify]);

  const handlePost = async () => {
    if (!selectedPage || !postMessage) {
      notify.error("Please select a page and enter a message.");
      return;
    }
    setPosting(true);
    try {
      const metaPostPage = await importFunction('metaPostPage');
      if (!metaPostPage) {
        notify.error("Meta post function not available");
        return;
      }
      
      const { data, status } = await metaPostPage({ page_id: selectedPage, message: postMessage });
      if (status === 200 && data?.ok) {
        setPostMessage("");
        notify.success("Posted to Facebook Page successfully!");
      } else {
        notify.error(`Post failed: ${data?.error || data?.message || "Unknown error"}`);
      }
    } catch (e) {
      console.error("Post failed:", e);
      notify.error("Failed to post to Facebook Page.");
    } finally {
      setPosting(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const metaValidateSecrets = await importFunction('metaValidateSecrets');
      if (!metaValidateSecrets) {
        setValidation({ status: 404, data: { ok: false, error: "Meta validation function not available" } });
        return;
      }
      
      const { data, status } = await metaValidateSecrets();
      setValidation({ status, data });
      if (status === 200 && data?.ok) {
        notify.success("Meta credentials validated successfully.");
      } else {
        notify.error(data?.error || "Validation failed. See details below.");
      }
    } catch (e) {
      setValidation({ status: 500, data: { ok: false, error: e.message } });
      notify.error("Validation failed with error: " + e.message);
    } finally {
      setValidating(false);
    }
  };

  // Twitter functions
  const handleTwitterValidate = async () => {
    setTwValidating(true);
    try {
      const twitterValidateSecrets = await importFunction('twitterValidateSecrets');
      if (!twitterValidateSecrets) {
        setTwValidation({ ok: false, error: "Twitter validation function not available" });
        return;
      }
      
      const { data, status } = await twitterValidateSecrets();
      setTwValidation(data);
      if (status === 200 && data?.ok) {
        notify.success("Twitter credentials look good.");
      } else {
        notify.error(data?.missing?.length ? `Missing: ${data.missing.join(", ")}` : "Twitter validation issues. See details.");
      }
    } catch (e) {
      console.error("Twitter validation failed:", e);
      notify.error("Failed to validate Twitter credentials.");
      setTwValidation({ ok: false, error: e.message });
    } finally {
      setTwValidating(false);
    }
  };

  const connectTwitter = async () => {
    setTwConnecting(true);
    try {
      const twitterOauthStart = await importFunction('twitterOauthStart');
      if (!twitterOauthStart) {
        notify.error("Twitter OAuth function not available");
        return;
      }
      
      const { data, status } = await twitterOauthStart();
      const url = data?.auth_url;
      if (status !== 200 || !url) {
        notify.error(data?.error || "Failed to get Twitter OAuth URL.");
        return;
      }
      
      const popup = window.open(url, "twitter_connect", "width=800,height=800");
      if (!popup) {
        window.location.href = url;
      }
    } catch (e) {
      console.error("Twitter connect failed:", e);
      notify.error("Could not start Twitter OAuth. Verify secrets and try again.");
    } finally {
      setTwConnecting(false);
    }
  };

  const loadTwitterAccount = useCallback(async () => {
    try {
      const twitterListAccount = await importFunction('twitterListAccount');
      if (!twitterListAccount) return;
      
      const { data } = await twitterListAccount();
      if (data?.account) {
        setTwAccount(data.account);
        notify.success(`Loaded @${data.account.username}`);
      } else {
        setTwAccount(null);
        if (!data?.error) notify.info("No Twitter account connected.");
      }
    } catch (e) {
      console.error("Failed to load Twitter account:", e);
      notify.error("Failed to load Twitter account. Please connect Twitter first.");
    }
  }, [notify]);

  const handleTweet = async () => {
    if (!twTweet.trim()) {
      notify.error("Enter a tweet message.");
      return;
    }
    setTwPosting(true);
    try {
      const twitterPostTweet = await importFunction('twitterPostTweet');
      if (!twitterPostTweet) {
        notify.error("Twitter post function not available");
        return;
      }
      
      const { data, status } = await twitterPostTweet({ text: twTweet.trim() });
      if (status === 200 && data?.ok) {
        notify.success("Tweet posted!");
        setTwTweet("");
      } else {
        notify.error(data?.error || "Tweet failed");
      }
    } catch (e) {
      console.error("Tweet failed:", e);
      notify.error("Tweet failed.");
    } finally {
      setTwPosting(false);
    }
  };

  // LinkedIn functions
  const handleLinkedInValidate = async () => {
    setLiValidating(true);
    try {
      const linkedinValidateSecrets = await importFunction('linkedinValidateSecrets');
      if (!linkedinValidateSecrets) {
        setLiValidation({ ok: false, error: "LinkedIn validation function not available" });
        return;
      }
      
      const { data, status } = await linkedinValidateSecrets();
      setLiValidation(data);
      if (status === 200 && data?.ok) {
        notify.success("LinkedIn credentials look good.");
      } else {
        notify.error(data?.missing?.length ? `Missing: ${data.missing.join(", ")}` : "Validation issues. See details.");
      }
    } catch (e) {
      console.error("LinkedIn validation failed:", e);
      notify.error("Failed to validate LinkedIn credentials.");
      setLiValidation({ ok: false, error: e.message });
    } finally {
      setLiValidating(false);
    }
  };

  const connectLinkedIn = async () => {
    setLiConnecting(true);
    try {
      const linkedinOauthStart = await importFunction('linkedinOauthStart');
      if (!linkedinOauthStart) {
        notify.error("LinkedIn OAuth function not available");
        return;
      }
      
      const { data, status } = await linkedinOauthStart();
      const url = data?.auth_url;
      if (status !== 200 || !url) {
        notify.error(data?.error || "Failed to get LinkedIn OAuth URL.");
        return;
      }
      
      const popup = window.open(url, "linkedin_connect", "width=800,height=800");
      if (!popup) window.location.href = url;
    } catch (e) {
      console.error("LinkedIn connect failed:", e);
      notify.error("Could not start LinkedIn OAuth. Verify secrets and try again.");
    } finally {
      setLiConnecting(false);
    }
  };

  const loadLinkedInProfile = useCallback(async () => {
    try {
      const linkedinGetProfile = await importFunction('linkedinGetProfile');
      if (!linkedinGetProfile) return;
      
      const { data } = await linkedinGetProfile();
      if (data?.profile) {
        setLiProfile(data.profile);
        notify.success(`Loaded ${data.profile.name || "profile"}`);
      } else {
        setLiProfile(null);
        if (!data?.error) notify.info("No LinkedIn account connected.");
      }
    } catch (e) {
      console.error("Failed to load LinkedIn profile:", e);
      notify.error("Failed to load LinkedIn profile. Please connect first.");
    }
  }, [notify]);

  const handleLinkedInPost = async () => {
    if (!liPost.trim()) {
      notify.error("Enter a post message.");
      return;
    }
    setLiPosting(true);
    try {
      const linkedinPostShare = await importFunction('linkedinPostShare');
      if (!linkedinPostShare) {
        notify.error("LinkedIn post function not available");
        return;
      }
      
      const { data, status } = await linkedinPostShare({ text: liPost.trim() });
      if (status === 200 && data?.ok) {
        notify.success("Share posted!");
        setLiPost("");
      } else {
        notify.error(data?.error || "Share failed");
      }
    } catch (e) {
      console.error("Share failed:", e);
      notify.error("Share failed.");
    } finally {
      setLiPosting(false);
    }
  };

  // YouTube functions
  const handleYouTubeValidate = async () => {
    setYtValidating(true);
    try {
      const youtubeValidateSecrets = await importFunction('youtubeValidateSecrets');
      if (!youtubeValidateSecrets) {
        setYtValidation({ ok: false, error: "YouTube validation function not available" });
        return;
      }
      
      const { data, status } = await youtubeValidateSecrets();
      setYtValidation(data);
      if (status === 200 && data?.ok) {
        notify.success("YouTube credentials look good.");
      } else {
        notify.error(data?.missing?.length ? `Missing: ${data.missing.join(", ")}` : "Validation issues. See details.");
      }
    } catch (e) {
      console.error("YouTube validation failed:", e);
      notify.error("Failed to validate YouTube credentials.");
      setYtValidation({ ok: false, error: e.message });
    } finally {
      setYtValidating(false);
    }
  };

  const connectYouTube = async () => {
    setYtConnecting(true);
    try {
      const youtubeOauthStart = await importFunction('youtubeOauthStart');
      if (!youtubeOauthStart) {
        notify.error("YouTube OAuth function not available");
        return;
      }
      
      const { data, status } = await youtubeOauthStart();
      const url = data?.auth_url;
      if (status !== 200 || !url) {
        notify.error(data?.error || "Failed to get YouTube OAuth URL.");
        return;
      }
      
      const popup = window.open(url, "youtube_connect", "width=800,height=800");
      if (!popup) window.location.href = url;
    } catch (e) {
      console.error("YouTube connect failed:", e);
      notify.error("Could not start YouTube OAuth. Verify secrets and try again.");
    } finally {
      setYtConnecting(false);
    }
  };

  const loadYouTubeChannel = useCallback(async () => {
    try {
      const youtubeGetChannel = await importFunction('youtubeGetChannel');
      if (!youtubeGetChannel) return;
      
      const { data } = await youtubeGetChannel();
      if (data?.channel) {
        setYtChannel(data.channel);
        notify.success(`Loaded channel ${data.channel.title}`);
      } else {
        setYtChannel(null);
        if (!data?.error) notify.info("No YouTube account connected.");
      }
    } catch (e) {
      console.error("Failed to load YouTube channel:", e);
      notify.error("Failed to load YouTube channel. Please connect first.");
    }
  }, [notify]);

  useEffect(() => {
    const handler = (ev) => {
      if (typeof ev.data !== 'string') return;
      
      try {
        if (ev.data === "meta_connected") {
          loadPages();
        } else if (ev.data === "twitter_connected") {
          loadTwitterAccount();
        } else if (ev.data === "linkedin_connected") {
          loadLinkedInProfile();
        } else if (ev.data === "youtube_connected") {
          loadYouTubeChannel();
        }
      } catch (error) {
        console.error('Message handler error:', error);
      }
    };
    
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [loadPages, loadTwitterAccount, loadLinkedInProfile, loadYouTubeChannel]);

  return (
    <div className="max-w-7xl mx-auto space-y-8 p-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Plug className="w-6 h-6 text-emerald-700" />
          <h1 className="text-2xl font-bold">Social API Readiness</h1>
        </div>
        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
          Guidance + Payload Preview
        </Badge>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Current Capability</CardTitle>
          <CardDescription>
            Live publishing via social network APIs isn't enabled in this app yet. It requires backend functions to securely handle OAuth, tokens, rate limits, retries, and platform-specific payloads.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-gray-700">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
            <p>
              To enable live campaigns, go to Dashboard → Settings and enable backend functions. We'll then add secure server-side connectors for each platform.
            </p>
          </div>
          <ul className="list-disc ml-5 space-y-1">
            <li>OAuth flows per platform with encrypted token storage.</li>
            <li>Ad/creative endpoints for paid (ad accounts, campaigns, ad sets/groups, creatives).</li>
            <li>Organic post endpoints (page/profile posting, scheduling, media upload).</li>
            <li>Job queue with retries, backoff, and idempotency keys.</li>
            <li>Budget pacing, daily caps, and error telemetry.</li>
          </ul>
          <div className="flex gap-2 pt-2">
            <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200"><Shield className="w-3 h-3 mr-1" /> SOC2-ready patterns</Badge>
            <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200"><CheckCircle2 className="w-3 h-3 mr-1" /> OAuth + token rotation</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Validate Meta Credentials</CardTitle>
          <CardDescription>Checks secrets and verifies your App ID/Secret with Meta</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleValidate} disabled={validating}>
              {validating ? "Validating..." : "Validate Credentials"}
            </Button>
            {validation?.data && (
              <Badge variant={validation.data.ok ? "success" : "destructive"}>
                {validation.data.ok ? "All checks passed" : "Issues found"}
              </Badge>
            )}
          </div>
          <div className="border rounded-xl p-3 bg-gray-50 flex items-center justify-between gap-2">
            <div className="text-xs text-gray-700 break-all">
              Meta Redirect URI: {expectedMetaRedirect}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(expectedMetaRedirect);
                notify.success("Copied to clipboard!");
              }}
            >
              <Copy className="w-3.5 h-3.5 mr-1.5" /> Copy
            </Button>
          </div>
          {validation?.data && (
            <div className="border rounded-xl p-3 bg-gray-50 overflow-auto max-h-72">
              <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                {JSON.stringify(validation.data, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Twitter className="w-5 h-5 text-emerald-700" />
            Connect to X (Twitter)
          </CardTitle>
          <CardDescription>Authenticate and post a test Tweet</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={handleTwitterValidate} disabled={twValidating}>
              {twValidating ? "Validating..." : "Validate Credentials"}
            </Button>
            <Button onClick={connectTwitter} disabled={twConnecting}>
              {twConnecting ? "Opening..." : "Connect Twitter"}
            </Button>
            <Button variant="outline" onClick={loadTwitterAccount}>Refresh Account</Button>
          </div>

          <div className="border rounded-xl p-3 bg-gray-50 flex items-center justify-between gap-2">
            <div className="text-xs text-gray-700 break-all">
              Twitter Redirect URI: {expectedTwitterRedirect}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(expectedTwitterRedirect);
                notify.success("Copied to clipboard!");
              }}
            >
              <Copy className="w-3.5 h-3.5 mr-1.5" /> Copy
            </Button>
          </div>

          {twValidation && (
            <div className="border rounded-xl p-3 bg-gray-50 overflow-auto max-h-72">
              <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                {JSON.stringify(twValidation, null, 2)}
              </pre>
            </div>
          )}

          {twAccount ? (
            <div className="space-y-2">
              <div className="text-sm text-gray-700">
                Connected as <span className="font-medium">@{twAccount.username}</span> • {twAccount.name}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <Input
                  placeholder="Write a test tweet..."
                  value={twTweet}
                  onChange={(e) => setTwTweet(e.target.value)}
                  className="md:col-span-2"
                />
                <Button onClick={handleTweet} disabled={twPosting || !twTweet.trim()}>
                  {twPosting ? "Posting..." : "Post Tweet"}
                </Button>
              </div>
              <div className="text-xs text-gray-500">Posts a simple text tweet using your connected account.</div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">No Twitter account yet. Click Connect Twitter, approve access, then Refresh Account.</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Linkedin className="w-5 h-5 text-emerald-700" />
            Connect to LinkedIn
          </CardTitle>
          <CardDescription>Authenticate and post a test share</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={handleLinkedInValidate} disabled={liValidating}>
              {liValidating ? "Validating..." : "Validate Credentials"}
            </Button>
            <Button onClick={connectLinkedIn} disabled={liConnecting}>
              {liConnecting ? "Opening..." : "Connect LinkedIn"}
            </Button>
            <Button variant="outline" onClick={loadLinkedInProfile}>Refresh Profile</Button>
          </div>

          <div className="border rounded-xl p-3 bg-gray-50 flex items-center justify-between gap-2">
            <div className="text-xs text-gray-700 break-all">
              LinkedIn Redirect URI: {expectedLinkedInRedirect}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(expectedLinkedInRedirect);
                notify.success("Copied to clipboard!");
              }}
            >
              <Copy className="w-3.5 h-3.5 mr-1.5" /> Copy
            </Button>
          </div>

          {liValidation && (
            <div className="border rounded-xl p-3 bg-gray-50 overflow-auto max-h-72">
              <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                {JSON.stringify(liValidation, null, 2)}
              </pre>
            </div>
          )}

          {liProfile ? (
            <div className="space-y-2">
              <div className="text-sm text-gray-700">
                Connected as <span className="font-medium">{liProfile.name}</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <Input
                  placeholder="Write a test share..."
                  value={liPost}
                  onChange={(e) => setLiPost(e.target.value)}
                  className="md:col-span-2"
                />
                <Button onClick={handleLinkedInPost} disabled={liPosting || !liPost.trim()}>
                  {liPosting ? "Posting..." : "Post Share"}
                </Button>
              </div>
              <div className="text-xs text-gray-500">Posts a simple text share to your personal profile.</div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">No LinkedIn account yet. Click Connect LinkedIn, approve access, then Refresh Profile.</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Youtube className="w-5 h-5 text-emerald-700" />
            Connect to YouTube
          </CardTitle>
          <CardDescription>Authenticate and fetch your channel</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={handleYouTubeValidate} disabled={ytValidating}>
              {ytValidating ? "Validating..." : "Validate Credentials"}
            </Button>
            <Button onClick={connectYouTube} disabled={ytConnecting}>
              {ytConnecting ? "Opening..." : "Connect YouTube"}
            </Button>
            <Button variant="outline" onClick={loadYouTubeChannel}>Refresh Channel</Button>
          </div>

          <div className="border rounded-xl p-3 bg-gray-50 flex items-center justify-between gap-2">
            <div className="text-xs text-gray-700 break-all">
              YouTube Redirect URI: {expectedYoutubeRedirect}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(expectedYoutubeRedirect);
                notify.success("Copied to clipboard!");
              }}
            >
              <Copy className="w-3.5 h-3.5 mr-1.5" /> Copy
            </Button>
          </div>

          {ytValidation && (
            <div className="border rounded-xl p-3 bg-gray-50 overflow-auto max-h-72">
              <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                {JSON.stringify(ytValidation, null, 2)}
              </pre>
            </div>
          )}

          {ytChannel ? (
            <div className="space-y-2">
              <div className="text-sm text-gray-700">
                Connected channel: <span className="font-medium">{ytChannel.title}</span>
              </div>
              <div className="text-xs text-gray-500">Channel ID: {ytChannel.id}</div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">No YouTube channel yet. Click Connect YouTube, approve access, then Refresh Channel.</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Platform Matrix</CardTitle>
          <CardDescription>What's needed to go live for each platform</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {platforms.map((p, i) => (
            <div key={i} className="border rounded-xl p-3">
              <div className="flex items-center justify-between">
                <div className="font-medium">{p.name}</div>
                <Badge variant="outline">{p.status}</Badge>
              </div>
              <div className="text-xs text-gray-600 mt-2">{p.notes}</div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Connect to Meta (Facebook/Instagram)</CardTitle>
          <CardDescription>Authenticate and fetch your Pages for posting</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Button onClick={connectMeta} disabled={connecting}>
              {connecting ? "Opening..." : "Connect Meta"}
            </Button>
            <Button variant="outline" onClick={loadPages} disabled={connecting}>Refresh Pages</Button>
          </div>
          {pages.length > 0 ? (
            <div className="space-y-2">
              <div className="text-sm text-gray-700">Connected Pages</div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
                {pages.map((p) => (
                  <div key={p.id} className="border rounded-xl p-3">
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-gray-500">{p.id}{p.category ? ` • ${p.category}` : ""}</div>
                  </div>
                ))}
              </div>

              <div className="border rounded-xl p-3 space-y-2">
                <div className="text-sm font-medium">Test Organic Post</div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <select className="border rounded-xl p-2" value={selectedPage} onChange={(e) => setSelectedPage(e.target.value)}>
                    <option value="">Select Page</option>
                    {pages.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <Input placeholder="Write message..." value={postMessage} onChange={(e) => setPostMessage(e.target.value)} />
                  <Button onClick={handlePost} disabled={posting || !selectedPage || !postMessage}>
                    {posting ? "Posting..." : "Post"}
                  </Button>
                </div>
                <div className="text-xs text-gray-500">This posts a simple text message to the selected Page using the saved page token.</div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">No pages yet. Click Connect Meta, approve permissions, then Refresh Pages.</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Build and Inspect Payloads</CardTitle>
          <CardDescription>Preview the JSON we'd send to APIs (per platform) from your campaign</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <Input
                placeholder="Enter Social Campaign ID (from Social Campaigns list)"
                value={campaignId}
                onChange={(e) => setCampaignId(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handlePreview} disabled={loading || !campaignId}>
                {loading ? <Eye className="w-4 h-4 mr-2 animate-pulse" /> : <Eye className="w-4 h-4 mr-2" />}
                Preview JSON
              </Button>
              <Button variant="outline" onClick={handleDownload} disabled={!preview}>
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
            </div>
          </div>

          {!preview ? (
            <div className="text-sm text-gray-500">
              No preview yet. Pick a campaign ID from{" "}
              <Link to={createPageUrl("SocialCampaigns")} className="underline inline-flex items-center gap-1">
                Social Campaigns <LinkIcon className="w-3 h-3" />
              </Link>.
            </div>
          ) : (
            <div className="border rounded-xl p-3 bg-gray-50 overflow-auto max-h-96">
              <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                {JSON.stringify(preview, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Next Steps Checklist</CardTitle>
          <CardDescription>When you're ready to wire up live APIs</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-gray-700 space-y-2">
          <ol className="list-decimal ml-5 space-y-1">
            <li>Enable backend functions in Dashboard → Settings (staging first).</li>
            <li>Register apps on platforms and set redirect URIs (https://yourapp/callback/provider).</li>
            <li>Store client IDs/secrets in a secure secret manager (never in repo).</li>
            <li>Implement OAuth handlers and token refresh; persist tokens per user/account.</li>
            <li>Map our entities to each platform's payload and validate (lint + contract tests).</li>
            <li>Add job queue for scheduling posts/ads with retries and backoff.</li>
            <li>Ship a limited beta with one platform (Meta Ads) before expanding coverage.</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
