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
import { YouTubeChannel } from "@/api/entities";
import { YouTubeVideo } from "@/api/entities";
import { YouTubePlaylist } from "@/api/entities";
import { YouTubeAnalytics } from "@/api/entities";
import { UploadFile } from "@/api/integrations";
import { Youtube, Upload, Play, ListVideo, BarChart3, Users, Eye, Calendar, Plus } from 'lucide-react';
import { toast, Toaster } from 'sonner';

// Import YouTube functions
const importFunction = async (moduleName) => {
  try {
    const module = await import(`@/api/functions/${moduleName}`);
    return module[moduleName];
  } catch (error) {
    console.warn(`Function ${moduleName} not available:`, error);
    return null;
  }
};

// YouTube categories for video uploads
const YOUTUBE_CATEGORIES = [
  { id: "1", name: "Film & Animation" },
  { id: "2", name: "Autos & Vehicles" },
  { id: "10", name: "Music" },
  { id: "15", name: "Pets & Animals" },
  { id: "17", name: "Sports" },
  { id: "19", name: "Travel & Events" },
  { id: "20", name: "Gaming" },
  { id: "22", name: "People & Blogs" },
  { id: "23", name: "Comedy" },
  { id: "24", name: "Entertainment" },
  { id: "25", name: "News & Politics" },
  { id: "26", name: "Howto & Style" },
  { id: "27", name: "Education" },
  { id: "28", name: "Science & Technology" }
];

export default function YouTubeManager() {
  const [channel, setChannel] = useState(null);
  const [videos, setVideos] = useState([]);
  const [playlists, setPlaylists] = useState([]);
  const [analytics, setAnalytics] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  
  // Loading states
  const [loadingChannel, setLoadingChannel] = useState(false);
  const [loadingVideos, setLoadingVideos] = useState(false);
  const [loadingPlaylists, setLoadingPlaylists] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [loadingSubscriptions, setLoadingSubscriptions] = useState(false);

  // Dialog states
  const [showUploadVideo, setShowUploadVideo] = useState(false);
  const [showCreatePlaylist, setShowCreatePlaylist] = useState(false);
  const [showAnalyticsDialog, setShowAnalyticsDialog] = useState(false);
  const [uploadingVideo, setUploadingVideo] = useState(false);
  const [creatingPlaylist, setCreatingPlaylist] = useState(false);
  const [fetchingAnalytics, setFetchingAnalytics] = useState(false);

  // Form states
  const [videoData, setVideoData] = useState({
    title: '',
    description: '',
    tags: '',
    category_id: '22',
    privacy_status: 'PUBLIC',
    video_file: null,
    thumbnail_file: null,
    scheduled_publish_time: ''
  });

  const [playlistData, setPlaylistData] = useState({
    title: '',
    description: '',
    privacy_status: 'PUBLIC',
    video_ids: ''
  });

  const [analyticsFilter, setAnalyticsFilter] = useState({
    video_id: '',
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0]
  });

  const loadChannel = useCallback(async () => {
    setLoadingChannel(true);
    try {
      const youtubeGetChannel = await importFunction('youtubeGetChannel');
      if (!youtubeGetChannel) {
        toast.error("YouTube Get Channel function not available");
        return;
      }
      
      const { data } = await youtubeGetChannel();
      if (data?.channel) {
        setChannel(data.channel);
        
        // Store/update channel in database
        const channelRecord = {
          channel_id: data.channel.id,
          owner_user_id: 'current_user', // This would be populated by the function
          channel_title: data.channel.title,
          channel_description: data.channel.description || '',
          subscriber_count: data.channel.subscriber_count || 0,
          video_count: data.channel.video_count || 0,
          view_count: data.channel.view_count || 0,
          thumbnail_url: data.channel.thumbnail_url || '',
          last_synced: new Date().toISOString()
        };
        
        // Try to update existing or create new
        const existingChannels = await YouTubeChannel.filter({ channel_id: data.channel.id });
        if (existingChannels && existingChannels.length > 0) {
          await YouTubeChannel.update(existingChannels[0].id, channelRecord);
        } else {
          await YouTubeChannel.create(channelRecord);
        }
      } else {
        toast.info("No YouTube channel connected. Please connect your account first.");
      }
    } catch (error) {
      console.error("Failed to load channel:", error);
      toast.error("Failed to load YouTube channel");
    } finally {
      setLoadingChannel(false);
    }
  }, []);

  const loadVideos = useCallback(async () => {
    if (!channel) return;
    
    setLoadingVideos(true);
    try {
      const videosList = await YouTubeVideo.filter({ 
        channel_id: channel.id 
      }, '-published_at');
      setVideos(videosList || []);
    } catch (error) {
      console.error("Failed to load videos:", error);
      toast.error("Failed to load videos");
    } finally {
      setLoadingVideos(false);
    }
  }, [channel]);

  const loadPlaylists = useCallback(async () => {
    if (!channel) return;
    
    setLoadingPlaylists(true);
    try {
      const playlistsList = await YouTubePlaylist.filter({ 
        channel_id: channel.id 
      }, '-created_at');
      setPlaylists(playlistsList || []);
    } catch (error) {
      console.error("Failed to load playlists:", error);
      toast.error("Failed to load playlists");
    } finally {
      setLoadingPlaylists(false);
    }
  }, [channel]);

  const loadAnalytics = useCallback(async () => {
    if (!channel) return;
    
    setLoadingAnalytics(true);
    try {
      const analyticsList = await YouTubeAnalytics.filter({ 
        channel_id: channel.id 
      }, '-created_at', 10);
      setAnalytics(analyticsList || []);
    } catch (error) {
      console.error("Failed to load analytics:", error);
      toast.error("Failed to load analytics");
    } finally {
      setLoadingAnalytics(false);
    }
  }, [channel]);

  const loadSubscriptions = useCallback(async () => {
    setLoadingSubscriptions(true);
    try {
      const youtubeManageSubscriptions = await importFunction('youtubeManageSubscriptions');
      if (!youtubeManageSubscriptions) {
        toast.error("YouTube Subscriptions function not available");
        return;
      }
      
      const { data } = await youtubeManageSubscriptions({ action: 'list' });
      if (data?.success) {
        setSubscriptions(data.subscriptions || []);
      }
    } catch (error) {
      console.error("Failed to load subscriptions:", error);
      toast.error("Failed to load subscriptions");
    } finally {
      setLoadingSubscriptions(false);
    }
  }, []);

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

      let thumbnailUrl = null;
      if (videoData.thumbnail_file) {
        const thumbUploadResult = await UploadFile({ file: videoData.thumbnail_file });
        thumbnailUrl = thumbUploadResult?.file_url;
      }

      const youtubeUploadVideo = await importFunction('youtubeUploadVideo');
      if (!youtubeUploadVideo) {
        toast.error("YouTube Upload function not available");
        return;
      }
      
      const { data } = await youtubeUploadVideo({
        title: videoData.title,
        description: videoData.description,
        tags: videoData.tags.split(',').map(tag => tag.trim()).filter(tag => tag),
        category_id: videoData.category_id,
        privacy_status: videoData.privacy_status,
        video_file_url: videoUploadResult.file_url,
        thumbnail_file_url: thumbnailUrl,
        scheduled_publish_time: videoData.scheduled_publish_time || null
      });
      
      if (data?.success) {
        toast.success("Video uploaded successfully!");
        setShowUploadVideo(false);
        setVideoData({
          title: '',
          description: '',
          tags: '',
          category_id: '22',
          privacy_status: 'PUBLIC',
          video_file: null,
          thumbnail_file: null,
          scheduled_publish_time: ''
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

  const handleCreatePlaylist = async () => {
    if (!playlistData.title) {
      toast.error("Please provide playlist title");
      return;
    }

    setCreatingPlaylist(true);
    try {
      const youtubeCreatePlaylist = await importFunction('youtubeCreatePlaylist');
      if (!youtubeCreatePlaylist) {
        toast.error("YouTube Create Playlist function not available");
        return;
      }
      
      const videoIds = playlistData.video_ids
        .split(',')
        .map(id => id.trim())
        .filter(id => id);
      
      const { data } = await youtubeCreatePlaylist({
        title: playlistData.title,
        description: playlistData.description,
        privacy_status: playlistData.privacy_status,
        video_ids: videoIds
      });
      
      if (data?.success) {
        toast.success(`Playlist created successfully! ${data.videos_added} videos added.`);
        setShowCreatePlaylist(false);
        setPlaylistData({
          title: '',
          description: '',
          privacy_status: 'PUBLIC',
          video_ids: ''
        });
        loadPlaylists();
      } else {
        toast.error(data?.error || "Failed to create playlist");
      }
    } catch (error) {
      console.error("Playlist creation failed:", error);
      toast.error("Failed to create playlist");
    } finally {
      setCreatingPlaylist(false);
    }
  };

  const handleFetchAnalytics = async () => {
    if (!channel) {
      toast.error("No channel available");
      return;
    }

    setFetchingAnalytics(true);
    try {
      const youtubeGetAnalytics = await importFunction('youtubeGetAnalytics');
      if (!youtubeGetAnalytics) {
        toast.error("YouTube Analytics function not available");
        return;
      }
      
      const { data } = await youtubeGetAnalytics({
        channel_id: channel.id,
        video_id: analyticsFilter.video_id || null,
        start_date: analyticsFilter.start_date,
        end_date: analyticsFilter.end_date
      });
      
      if (data?.success) {
        toast.success("Analytics fetched successfully!");
        setShowAnalyticsDialog(false);
        loadAnalytics();
      } else {
        toast.error(data?.error || "Failed to fetch analytics");
      }
    } catch (error) {
      console.error("Analytics fetch failed:", error);
      toast.error("Failed to fetch analytics");
    } finally {
      setFetchingAnalytics(false);
    }
  };

  useEffect(() => {
    loadChannel();
    loadSubscriptions();
  }, [loadChannel, loadSubscriptions]);

  useEffect(() => {
    if (channel) {
      loadVideos();
      loadPlaylists();
      loadAnalytics();
    }
  }, [channel, loadVideos, loadPlaylists, loadAnalytics]);

  const formatNumber = (num) => {
    if (!num) return '0';
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <Toaster richColors />
      
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-red-500 rounded-xl flex items-center justify-center">
            <Youtube className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">YouTube Manager</h1>
            <p className="text-gray-600">Complete video content management and analytics</p>
          </div>
        </div>
        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
          Video Marketing Platform
        </Badge>
      </header>

      {/* Channel Overview */}
      {channel && (
        <Card className="bg-gradient-to-r from-red-50 to-red-100 border-red-200">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {channel.thumbnail_url && (
                  <img 
                    src={channel.thumbnail_url} 
                    alt={channel.title}
                    className="w-16 h-16 rounded-full object-cover"
                  />
                )}
                <div>
                  <CardTitle className="text-xl text-red-900">{channel.title}</CardTitle>
                  <CardDescription className="text-red-700">
                    {formatNumber(channel.subscriber_count)} subscribers • {formatNumber(channel.video_count)} videos
                  </CardDescription>
                </div>
              </div>
              <Button variant="outline" onClick={loadChannel} disabled={loadingChannel}>
                {loadingChannel ? "Syncing..." : "Refresh Channel"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-red-900">{formatNumber(channel.view_count)}</div>
                <div className="text-sm text-red-700">Total Views</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-900">{formatNumber(channel.subscriber_count)}</div>
                <div className="text-sm text-red-700">Subscribers</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-900">{formatNumber(channel.video_count)}</div>
                <div className="text-sm text-red-700">Videos</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="videos" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="videos" className="flex items-center gap-2">
            <Play className="w-4 h-4" />
            Videos
          </TabsTrigger>
          <TabsTrigger value="playlists" className="flex items-center gap-2">
            <ListVideo className="w-4 h-4" />
            Playlists
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="subscriptions" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Subscriptions
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
                  <DialogTitle>Upload New Video</DialogTitle>
                  <DialogDescription>
                    Upload and publish a new video to your YouTube channel.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="video_title">Title</Label>
                    <Input
                      id="video_title"
                      value={videoData.title}
                      onChange={(e) => setVideoData({ ...videoData, title: e.target.value })}
                      placeholder="My Awesome Video"
                    />
                  </div>
                  <div>
                    <Label htmlFor="video_description">Description</Label>
                    <Textarea
                      id="video_description"
                      value={videoData.description}
                      onChange={(e) => setVideoData({ ...videoData, description: e.target.value })}
                      placeholder="Describe your video content..."
                      rows={4}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="video_category">Category</Label>
                      <Select
                        value={videoData.category_id}
                        onValueChange={(value) => setVideoData({ ...videoData, category_id: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {YOUTUBE_CATEGORIES.map((category) => (
                            <SelectItem key={category.id} value={category.id}>
                              {category.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="video_privacy">Privacy</Label>
                      <Select
                        value={videoData.privacy_status}
                        onValueChange={(value) => setVideoData({ ...videoData, privacy_status: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="PUBLIC">Public</SelectItem>
                          <SelectItem value="UNLISTED">Unlisted</SelectItem>
                          <SelectItem value="PRIVATE">Private</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="video_tags">Tags (comma-separated)</Label>
                    <Input
                      id="video_tags"
                      value={videoData.tags}
                      onChange={(e) => setVideoData({ ...videoData, tags: e.target.value })}
                      placeholder="tutorial, education, how-to"
                    />
                  </div>
                  <div>
                    <Label htmlFor="video_file">Video File</Label>
                    <Input
                      id="video_file"
                      type="file"
                      accept="video/*"
                      onChange={(e) => setVideoData({ ...videoData, video_file: e.target.files[0] })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="thumbnail_file">Custom Thumbnail (optional)</Label>
                    <Input
                      id="thumbnail_file"
                      type="file"
                      accept="image/*"
                      onChange={(e) => setVideoData({ ...videoData, thumbnail_file: e.target.files[0] })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="scheduled_time">Schedule Publication (optional)</Label>
                    <Input
                      id="scheduled_time"
                      type="datetime-local"
                      value={videoData.scheduled_publish_time}
                      onChange={(e) => setVideoData({ ...videoData, scheduled_publish_time: e.target.value })}
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
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-red-500 rounded-full" />
              </CardContent>
            </Card>
          ) : videos.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {videos.map((video) => (
                <Card key={video.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    {video.thumbnail_url && (
                      <img 
                        src={video.thumbnail_url} 
                        alt={video.title}
                        className="w-full h-32 object-cover rounded-lg mb-3"
                      />
                    )}
                    <CardTitle className="text-base line-clamp-2">{video.title}</CardTitle>
                    <div className="flex items-center justify-between">
                      <Badge variant={video.privacy_status === 'PUBLIC' ? 'default' : 'secondary'}>
                        {video.privacy_status}
                      </Badge>
                      <Badge variant={video.upload_status === 'PROCESSED' ? 'default' : 'outline'}>
                        {video.upload_status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        <span>{formatNumber(video.view_count)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>{new Date(video.published_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    {video.analytics && Object.keys(video.analytics).length > 0 && (
                      <div className="pt-2 border-t">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          {video.analytics.watch_time && (
                            <div>
                              <div className="text-gray-600">Watch Time</div>
                              <div className="font-medium">{formatDuration(video.analytics.watch_time)}</div>
                            </div>
                          )}
                          {video.analytics.click_through_rate && (
                            <div>
                              <div className="text-gray-600">CTR</div>
                              <div className="font-medium">{(video.analytics.click_through_rate * 100).toFixed(1)}%</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="w-full"
                      onClick={() => window.open(`https://www.youtube.com/watch?v=${video.video_id}`, '_blank')}
                    >
                      View on YouTube
                    </Button>
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
                  Upload your first video to start building your YouTube presence.
                </p>
                <Button onClick={() => setShowUploadVideo(true)}>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload First Video
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="playlists" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Playlist Management</h3>
            <Dialog open={showCreatePlaylist} onOpenChange={setShowCreatePlaylist}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Playlist
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create New Playlist</DialogTitle>
                  <DialogDescription>
                    Organize your videos into a new playlist.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="playlist_title">Playlist Title</Label>
                    <Input
                      id="playlist_title"
                      value={playlistData.title}
                      onChange={(e) => setPlaylistData({ ...playlistData, title: e.target.value })}
                      placeholder="My Video Series"
                    />
                  </div>
                  <div>
                    <Label htmlFor="playlist_description">Description</Label>
                    <Textarea
                      id="playlist_description"
                      value={playlistData.description}
                      onChange={(e) => setPlaylistData({ ...playlistData, description: e.target.value })}
                      placeholder="Describe your playlist..."
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label htmlFor="playlist_privacy">Privacy</Label>
                    <Select
                      value={playlistData.privacy_status}
                      onValueChange={(value) => setPlaylistData({ ...playlistData, privacy_status: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="PUBLIC">Public</SelectItem>
                        <SelectItem value="UNLISTED">Unlisted</SelectItem>
                        <SelectItem value="PRIVATE">Private</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="playlist_videos">Video IDs (comma-separated, optional)</Label>
                    <Textarea
                      id="playlist_videos"
                      value={playlistData.video_ids}
                      onChange={(e) => setPlaylistData({ ...playlistData, video_ids: e.target.value })}
                      placeholder="video_id_1, video_id_2, video_id_3"
                      rows={3}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Add existing video IDs to populate the playlist initially
                    </p>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreatePlaylist(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreatePlaylist} disabled={creatingPlaylist}>
                    {creatingPlaylist ? "Creating..." : "Create Playlist"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {loadingPlaylists ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-red-500 rounded-full" />
              </CardContent>
            </Card>
          ) : playlists.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {playlists.map((playlist) => (
                <Card key={playlist.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    {playlist.thumbnail_url && (
                      <img 
                        src={playlist.thumbnail_url} 
                        alt={playlist.title}
                        className="w-full h-32 object-cover rounded-lg mb-3"
                      />
                    )}
                    <CardTitle className="text-base">{playlist.title}</CardTitle>
                    <div className="flex items-center justify-between">
                      <Badge variant={playlist.privacy_status === 'PUBLIC' ? 'default' : 'secondary'}>
                        {playlist.privacy_status}
                      </Badge>
                      <Badge variant="outline">
                        {playlist.video_count} videos
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {playlist.description && (
                      <p className="text-sm text-gray-600 line-clamp-2">{playlist.description}</p>
                    )}
                    <div className="text-xs text-gray-500">
                      Created: {new Date(playlist.created_at).toLocaleDateString()}
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="w-full"
                      onClick={() => window.open(`https://www.youtube.com/playlist?list=${playlist.playlist_id}`, '_blank')}
                    >
                      View Playlist
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <ListVideo className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Playlists Yet</h3>
                <p className="text-gray-600 text-center mb-4">
                  Create playlists to organize your videos and improve discoverability.
                </p>
                <Button onClick={() => setShowCreatePlaylist(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create First Playlist
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Analytics Dashboard</h3>
            <Dialog open={showAnalyticsDialog} onOpenChange={setShowAnalyticsDialog}>
              <DialogTrigger asChild>
                <Button>
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Fetch Analytics
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Fetch YouTube Analytics</DialogTitle>
                  <DialogDescription>
                    Get detailed analytics for your channel or specific videos.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="analytics_video">Specific Video (optional)</Label>
                    <Select
                      value={analyticsFilter.video_id}
                      onValueChange={(value) => setAnalyticsFilter({ ...analyticsFilter, video_id: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All videos (channel analytics)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={null}>All videos (channel analytics)</SelectItem>
                        {videos.map((video) => (
                          <SelectItem key={video.video_id} value={video.video_id}>
                            {video.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="start_date">Start Date</Label>
                      <Input
                        id="start_date"
                        type="date"
                        value={analyticsFilter.start_date}
                        onChange={(e) => setAnalyticsFilter({ ...analyticsFilter, start_date: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label htmlFor="end_date">End Date</Label>
                      <Input
                        id="end_date"
                        type="date"
                        value={analyticsFilter.end_date}
                        onChange={(e) => setAnalyticsFilter({ ...analyticsFilter, end_date: e.target.value })}
                      />
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowAnalyticsDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleFetchAnalytics} disabled={fetchingAnalytics}>
                    {fetchingAnalytics ? "Fetching..." : "Fetch Analytics"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {loadingAnalytics ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-red-500 rounded-full" />
              </CardContent>
            </Card>
          ) : analytics.length > 0 ? (
            <div className="space-y-6">
              {analytics.map((analyticsData) => (
                <Card key={analyticsData.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">
                        {analyticsData.analytics_type === 'VIDEO' ? 'Video Analytics' : 'Channel Analytics'}
                      </CardTitle>
                      <Badge variant="outline">
                        {analyticsData.date_range_start} to {analyticsData.date_range_end}
                      </Badge>
                    </div>
                    <CardDescription>
                      Analytics for {analyticsData.analytics_type === 'CHANNEL' ? 'entire channel' : 'specific video'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">{formatNumber(analyticsData.metrics.views)}</div>
                        <div className="text-sm text-gray-600">Views</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">{formatDuration(analyticsData.metrics.watch_time)}</div>
                        <div className="text-sm text-gray-600">Watch Time</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">{analyticsData.metrics.subscriber_gain}</div>
                        <div className="text-sm text-gray-600">Subscribers Gained</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-red-600">{(analyticsData.engagement_metrics.engagement_rate || 0).toFixed(1)}%</div>
                        <div className="text-sm text-gray-600">Engagement Rate</div>
                      </div>
                    </div>
                    
                    {analyticsData.demographics && Object.keys(analyticsData.demographics).length > 0 && (
                      <div className="mt-6 pt-6 border-t">
                        <h4 className="font-semibold mb-3">Demographics</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {analyticsData.demographics.age_groups && Object.keys(analyticsData.demographics.age_groups).length > 0 && (
                            <div>
                              <h5 className="text-sm font-medium mb-2">Age Groups</h5>
                              <div className="space-y-1">
                                {Object.entries(analyticsData.demographics.age_groups).map(([age, percentage]) => (
                                  <div key={age} className="flex justify-between text-sm">
                                    <span>{age}</span>
                                    <span>{percentage?.toFixed(1)}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {analyticsData.demographics.gender_distribution && Object.keys(analyticsData.demographics.gender_distribution).length > 0 && (
                            <div>
                              <h5 className="text-sm font-medium mb-2">Gender Distribution</h5>
                              <div className="space-y-1">
                                {Object.entries(analyticsData.demographics.gender_distribution).map(([gender, percentage]) => (
                                  <div key={gender} className="flex justify-between text-sm">
                                    <span className="capitalize">{gender}</span>
                                    <span>{percentage?.toFixed(1)}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
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
                <BarChart3 className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Analytics Data</h3>
                <p className="text-gray-600 text-center mb-4">
                  Fetch analytics to see detailed insights about your channel performance.
                </p>
                <Button onClick={() => setShowAnalyticsDialog(true)}>
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Fetch Analytics
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="subscriptions" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Subscriptions</h3>
            <Button variant="outline" onClick={loadSubscriptions} disabled={loadingSubscriptions}>
              {loadingSubscriptions ? "Loading..." : "Refresh"}
            </Button>
          </div>

          {loadingSubscriptions ? (
            <Card>
              <CardContent className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-gray-200 border-t-red-500 rounded-full" />
              </CardContent>
            </Card>
          ) : subscriptions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {subscriptions.map((subscription) => (
                <Card key={subscription.subscription_id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    {subscription.thumbnail_url && (
                      <img 
                        src={subscription.thumbnail_url} 
                        alt={subscription.channel_title}
                        className="w-16 h-16 rounded-full object-cover mx-auto mb-3"
                      />
                    )}
                    <CardTitle className="text-center text-base">{subscription.channel_title}</CardTitle>
                    {subscription.channel_description && (
                      <CardDescription className="text-center line-clamp-2">
                        {subscription.channel_description}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="text-xs text-gray-500 text-center">
                      Subscribed: {new Date(subscription.published_at).toLocaleDateString()}
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="w-full"
                      onClick={() => window.open(`https://www.youtube.com/channel/${subscription.channel_id}`, '_blank')}
                    >
                      View Channel
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Users className="w-12 h-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Subscriptions</h3>
                <p className="text-gray-600 text-center">
                  Your channel subscriptions will appear here.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}