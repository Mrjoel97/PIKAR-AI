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
import { TikTokAccount } from "@/api/entities";
import { TikTokVideo } from "@/api/entities";
import { UploadFile } from "@/api/integrations";
import { Play, Upload, Users, Eye, Heart, MessageCircle, Share2, Verified, Hash, Calendar } from 'lucide-react';
import { toast, Toaster } from 'sonner';

// Import TikTok functions
const importFunction = async (moduleName) => {
  try {
    const functions = await import('@/api/functions');
    return functions[moduleName];
  } catch (error) {
    console.warn(`Function ${moduleName} not available:`, error);
    return null;
  }
};

export default function TikTokManager() {
  const [account, setAccount] = useState(null);
  const [videos, setVideos] = useState([]);
  
  // Loading states
  const [loadingAccount, setLoadingAccount] = useState(false);
  const [loadingVideos, setLoadingVideos] = useState(false);

  // Dialog states
  const [showUploadVideo, setShowUploadVideo] = useState(false);
  const [uploadingVideo, setUploadingVideo] = useState(false);

  // Form states
  const [videoData, setVideoData] = useState({
    title: '',
    description: '',
    hashtags: '',
    video_file: null,
    cover_image_file: null,
    privacy_level: 'PUBLIC',
    is_commercial: false,
    schedule_time: ''
  });

  const loadAccount = useCallback(async () => {
    setLoadingAccount(true);
    try {
      const tiktokGetAccount = await importFunction('tiktokGetAccount');
      if (!tiktokGetAccount) {
        toast.error("TikTok Get Account function not available");
        return;
      }
      
      const { data } = await tiktokGetAccount();
      if (data?.success && data?.account) {
        setAccount(data.account);
      } else {
        toast.info("No TikTok account connected. Please connect your account first.");
      }
    } catch (error) {
      console.error("Failed to load account:", error);
      toast.error("Failed to load TikTok account");
    } finally {
      setLoadingAccount(false);
    }
  }, []);

  const loadVideos = useCallback(async () => {
    if (!account) return;
    
    setLoadingVideos(true);
    try {
      const tiktokGetVideos = await importFunction('tiktokGetVideos');
      if (tiktokGetVideos) {
        const { data } = await tiktokGetVideos({ max_count: 50 });
        if (data?.success) {
          setVideos(data.videos || []);
        }
      } else {
        // Fallback to database records
        const videosList = await TikTokVideo.filter({ 
          account_id: account.account_id 
        }, '-published_at');
        setVideos(videosList || []);
      }
    } catch (error) {
      console.error("Failed to load videos:", error);
      // Fallback to database records
      try {
        const videosList = await TikTokVideo.filter({ 
          account_id: account.account_id 
        }, '-published_at');
        setVideos(videosList || []);
      } catch (dbError) {
        toast.error("Failed to load videos");
      }
    } finally {
      setLoadingVideos(false);
    }
  }, [account]);

  const handleVideoUpload = async () => {
    if (!videoData.title || !videoData.video_file) {
      toast.error("Please provide title and select a video file");
      return;
    }

    setUploadingVideo(true);
    try {
      // First upload the video file
      const videoUploadResult = await UploadFile({ file: videoData.video_file });
      if (!videoUploadResult?.file_url) {
        toast.error("Failed to upload video file");
        return;
      }

      let coverImageUrl = null;
      if (videoData.cover_image_file) {
        const coverUploadResult = await UploadFile({ file: videoData.cover_image_file });
        coverImageUrl = coverUploadResult?.file_url;
      }

      const tiktokUploadVideo = await importFunction('tiktokUploadVideo');
      if (!tiktokUploadVideo) {
        toast.error("TikTok Upload function not available");
        return;
      }
      
      const hashtags = videoData.hashtags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag)
        .map(tag => tag.startsWith('#') ? tag : `#${tag}`);
      
      const { data } = await tiktokUploadVideo({
        title: videoData.title,
        description: videoData.description,
        hashtags: hashtags,
        video_file_url: videoUploadResult.file_url,
        cover_image_url: coverImageUrl,
        privacy_level: videoData.privacy_level,
        is_commercial: videoData.is_commercial,
        schedule_time: videoData.schedule_time || null
      });
      
      if (data?.success) {
        toast.success("Video uploaded successfully!");
        setShowUploadVideo(false);
        setVideoData({
          title: '',
          description: '',
          hashtags: '',
          video_file: null,
          cover_image_file: null,
          privacy_level: 'PUBLIC',
          is_commercial: false,
          schedule_time: ''
        });
        loadVideos();
      } else {
        toast.error(data?.error || "Failed to upload video");
      }
    } catch (error) {
      console.error("Video upload failed:", error);
      toast.error("Failed to upload video");
    } finally {
      setUploadingVideo(false);
    }
  };

  useEffect(() => {
    loadAccount();
  }, [loadAccount]);

  useEffect(() => {
    if (account) {
      loadVideos();
    }
  }, [account, loadVideos]);

  const formatNumber = (num) => {
    if (!num) return '0';
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <Toaster richColors />
      
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center">
            <Play className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">TikTok Manager</h1>
            <p className="text-gray-600">Short-form video content management and analytics</p>
          </div>
        </div>
        <Badge variant="outline" className="bg-black/5 text-black border-black/20">
          Short Video Platform
        </Badge>
      </header>

      {/* Account Overview */}
      {account && (
        <Card className="bg-gradient-to-r from-black/5 to-black/10 border-black/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {account.profile_image_url && (
                  <img 
                    src={account.profile_image_url} 
                    alt={account.account_name}
                    className="w-16 h-16 rounded-full object-cover"
                  />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-xl text-black">{account.account_name}</CardTitle>
                    {account.is_verified && (
                      <Verified className="w-5 h-5 text-blue-500" />
                    )}
                  </div>
                  <CardDescription className="text-black/70">
                    {formatNumber(account.follower_count)} followers • {formatNumber(account.video_count)} videos
                  </CardDescription>
                </div>
              </div>
              <Button variant="outline" onClick={loadAccount} disabled={loadingAccount}>
                {loadingAccount ? "Syncing..." : "Refresh Account"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-black">{formatNumber(account.follower_count)}</div>
                <div className="text-sm text-black/60">Followers</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-black">{formatNumber(account.following_count)}</div>
                <div className="text-sm text-black/60">Following</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-black">{formatNumber(account.video_count)}</div>
                <div className="text-sm text-black/60">Videos</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-black">{formatNumber(account.total_likes)}</div>
                <div className="text-sm text-black/60">Total Likes</div>
              </div>
            </div>
            {account.bio && (
              <div className="mt-4 pt-4 border-t border-black/20">
                <p className="text-black/80">{account.bio}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="videos" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="videos" className="flex items-center gap-2">
            <Play className="w-4 h-4" />
            Videos
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <Eye className="w-4 h-4" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="videos" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Video Management</h3>
            <Dialog open={showUploadVideo} onOpenChange={setShowUploadVideo}>
              <DialogTrigger asChild>
                <Button>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Video
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Upload New TikTok Video</DialogTitle>
                  <DialogDescription>
                    Upload and publish a new short-form video to your TikTok account.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="video_title">Title/Caption</Label>
                    <Textarea
                      id="video_title"
                      value={videoData.title}
                      onChange={(e) => setVideoData({ ...videoData, title: e.target.value })}
                      placeholder="What's your video about?"
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label htmlFor="video_description">Additional Description (optional)</Label>
                    <Textarea
                      id="video_description"
                      value={videoData.description}
                      onChange={(e) => setVideoData({ ...videoData, description: e.target.value })}
                      placeholder="Add more details about your video..."
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label htmlFor="video_hashtags">Hashtags (comma-separated)</Label>
                    <Input
                      id="video_hashtags"
                      value={videoData.hashtags}
                      onChange={(e) => setVideoData({ ...videoData, hashtags: e.target.value })}
                      placeholder="fyp, viral, trending, dance"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter hashtags without # - they'll be added automatically
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="video_privacy">Privacy</Label>
                      <Select
                        value={videoData.privacy_level}
                        onValueChange={(value) => setVideoData({ ...videoData, privacy_level: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="PUBLIC">Public</SelectItem>
                          <SelectItem value="FRIENDS_ONLY">Friends Only</SelectItem>
                          <SelectItem value="PRIVATE">Private</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-center space-x-2 pt-6">
                      <input
                        type="checkbox"
                        id="is_commercial"
                        checked={videoData.is_commercial}
                        onChange={(e) => setVideoData({ ...videoData, is_commercial: e.target.checked })}
                        className="rounded"
                      />
                      <Label htmlFor="is_commercial" className="text-sm">
                        Commercial Content
                      </Label>
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="video_file">Video File (required)</Label>
                    <Input
                      id="video_file"
                      type="file"
                      accept="video/mp4,video/mov,video/avi"
                      onChange={(e) => setVideoData({ ...videoData, video_file: e.target.files[0] })}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Recommended: MP4 format, 9:16 aspect ratio, under 3 minutes
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="cover_image_file">Custom Cover Image (optional)</Label>
                    <Input
                      id="cover_image_file"
                      type="file"
                      accept="image/*"
                      onChange={(e) => setVideoData({ ...videoData, cover_image_file: e.target.files[0] })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="scheduled_time">Schedule Publication (optional)</Label>
                    <Input
                      id="scheduled_time"
                      type="datetime-local"
                      value={videoData.schedule_time}
                      onChange={(e) => setVideoData({ ...videoData, schedule_time: e.target.value })}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowUploadVideo(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleVideoUpload} disabled={uploadingVideo}>
                    {uploadingVideo ? "Uploading..." : "Upload Video"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {loadingVideos ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-black rounded-full" />
              </CardContent>
            </Card>
          ) : videos.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {videos.map((video) => (
                <Card key={video.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    {video.cover_image_url && (
                      <div className="relative">
                        <img 
                          src={video.cover_image_url} 
                          alt={video.title}
                          className="w-full h-48 object-cover rounded-lg mb-3"
                        />
                        <div className="absolute bottom-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
                          {Math.floor(video.duration / 60)}:{(video.duration % 60).toString().padStart(2, '0')}
                        </div>
                      </div>
                    )}
                    <CardTitle className="text-sm line-clamp-2">{video.title}</CardTitle>
                    <div className="flex items-center justify-between">
                      <Badge variant={video.privacy_level === 'PUBLIC' ? 'default' : 'secondary'}>
                        {video.privacy_level}
                      </Badge>
                      <Badge variant={video.upload_status === 'PUBLISHED' ? 'default' : 'outline'}>
                        {video.upload_status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex items-center gap-1 text-sm">
                        <Eye className="w-3 h-3" />
                        <span>{formatNumber(video.view_count)}</span>
                      </div>
                      <div className="flex items-center gap-1 text-sm">
                        <Heart className="w-3 h-3 text-red-500" />
                        <span>{formatNumber(video.like_count)}</span>
                      </div>
                      <div className="flex items-center gap-1 text-sm">
                        <MessageCircle className="w-3 h-3" />
                        <span>{formatNumber(video.comment_count)}</span>
                      </div>
                      <div className="flex items-center gap-1 text-sm">
                        <Share2 className="w-3 h-3" />
                        <span>{formatNumber(video.share_count)}</span>
                      </div>
                    </div>
                    
                    {video.hashtags && video.hashtags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {video.hashtags.slice(0, 3).map((hashtag, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">
                            <Hash className="w-2 h-2 mr-1" />
                            {hashtag.replace('#', '')}
                          </Badge>
                        ))}
                        {video.hashtags.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{video.hashtags.length - 3}
                          </Badge>
                        )}
                      </div>
                    )}

                    {video.analytics && video.analytics.engagement_rate > 0 && (
                      <div className="pt-2 border-t">
                        <div className="text-xs text-gray-600">
                          Engagement: {video.analytics.engagement_rate.toFixed(1)}%
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Calendar className="w-3 h-3" />
                      <span>{new Date(video.published_at).toLocaleDateString()}</span>
                    </div>
                    
                    {video.video_url && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="w-full"
                        onClick={() => window.open(video.video_url, '_blank')}
                      >
                        View on TikTok
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Play className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Videos Yet</h3>
                <p className="text-gray-600 text-center mb-4">
                  Upload your first TikTok video to start building your presence.
                </p>
                <Button onClick={() => setShowUploadVideo(true)}>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload First Video
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>TikTok Analytics</CardTitle>
              <CardDescription>
                Detailed analytics will be available once you have published videos.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {account && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-black">{formatNumber(account.follower_count)}</div>
                    <div className="text-sm text-gray-600">Followers</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-black">{formatNumber(account.total_likes)}</div>
                    <div className="text-sm text-gray-600">Total Likes</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-black">{formatNumber(account.video_count)}</div>
                    <div className="text-sm text-gray-600">Videos</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-black">
                      {videos.length > 0 ? 
                        (videos.reduce((sum, v) => sum + (v.view_count || 0), 0) / videos.length).toFixed(0) : '0'
                      }
                    </div>
                    <div className="text-sm text-gray-600">Avg Views</div>
                  </div>
                </div>
              )}
              
              {videos.length > 0 && (
                <div className="mt-8">
                  <h4 className="font-semibold mb-4">Top Performing Videos</h4>
                  <div className="space-y-3">
                    {videos
                      .sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
                      .slice(0, 5)
                      .map((video) => (
                        <div key={video.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex-1">
                            <p className="font-medium truncate">{video.title}</p>
                            <div className="flex items-center gap-4 text-sm text-gray-500">
                              <span>{formatNumber(video.view_count)} views</span>
                              <span>{formatNumber(video.like_count)} likes</span>
                              <span>{video.analytics?.engagement_rate?.toFixed(1)}% engagement</span>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}