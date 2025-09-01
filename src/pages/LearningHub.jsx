
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LearningPath, UserProgress, Achievement, LearningChallenge } from '@/api/entities';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { 
    GraduationCap, Trophy, Target, Star, Zap, Clock, 
    PlayCircle, CheckCircle, Lock, Award, Users, Flame,
    BookOpen, TrendingUp, Brain, Rocket
} from 'lucide-react';
import { toast, Toaster } from 'sonner';

export default function LearningHub() {
    const [learningPaths, setLearningPaths] = useState([]);
    const [userProgress, setUserProgress] = useState([]);
    const [achievements, setAchievements] = useState([]);
    const [challenges, setChallenges] = useState([]);
    const [userStats, setUserStats] = useState({
        totalPoints: 0,
        level: 1,
        streak: 0,
        pathsCompleted: 0,
        badgesEarned: 0,
        rank: 'Novice'
    });
    const [isLoading, setIsLoading] = useState(true);

    const loadLearningData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [paths, progress, userAchievements, activeChallenges] = await Promise.all([
                LearningPath.list(),
                UserProgress.list(),
                Achievement.list('-unlock_date'),
                LearningChallenge.filter({ status: 'active' })
            ]);
            
            setLearningPaths(paths);
            setUserProgress(progress);
            setAchievements(userAchievements);
            setChallenges(activeChallenges);
            calculateUserStats(progress, userAchievements);
        } catch (error) {
            console.error("Error loading learning data:", error);
            toast.error("Failed to load learning hub data");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        loadLearningData();
    }, [loadLearningData]);

    const calculateUserStats = (progress, achievements) => {
        const totalPoints = achievements.reduce((sum, ach) => sum + (ach.points_value || 0), 0) +
                          progress.reduce((sum, prog) => sum + (prog.points_earned || 0), 0);
        const level = Math.floor(totalPoints / 1000) + 1;
        const pathsCompleted = progress.filter(p => p.status === 'completed').length;
        
        setUserStats({
            totalPoints,
            level,
            streak: 7, // Mock data - would calculate from actual activity
            pathsCompleted,
            badgesEarned: achievements.length,
            rank: getRankFromLevel(level)
        });
    };

    const getRankFromLevel = (level) => {
        if (level >= 20) return 'AI Master';
        if (level >= 15) return 'Expert Strategist';
        if (level >= 10) return 'Advanced Practitioner';
        if (level >= 5) return 'Skilled User';
        return 'Novice';
    };

    const getDifficultyColor = (difficulty) => {
        switch (difficulty) {
            case 'beginner': return 'bg-green-100 text-green-800';
            case 'intermediate': return 'bg-blue-100 text-blue-800';
            case 'advanced': return 'bg-purple-100 text-purple-800';
            case 'expert': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getRarityColor = (rarity) => {
        switch (rarity) {
            case 'common': return 'text-gray-600';
            case 'uncommon': return 'text-green-600';
            case 'rare': return 'text-blue-600';
            case 'epic': return 'text-purple-600';
            case 'legendary': return 'text-yellow-600';
            default: return 'text-gray-600';
        }
    };

    if (isLoading) {
        return (
            <div className="max-w-7xl mx-auto p-6">
                <div className="animate-pulse space-y-6">
                    <div className="h-8 bg-gray-200 rounded w-1/3"></div>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <div key={i} className="h-24 bg-gray-200 rounded"></div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <Toaster richColors />
            
            {/* Header */}
            <div className="text-center">
                <h1 className="text-4xl font-bold text-gray-900 dark:text-white flex items-center justify-center gap-3">
                    <GraduationCap className="w-10 h-10 text-blue-600" />
                    PIKAR Learning Hub
                </h1>
                <p className="text-xl text-gray-600 dark:text-gray-400 mt-2">
                    Master AI-powered business intelligence through gamified learning
                </p>
            </div>

            {/* User Stats Dashboard */}
            <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
                <Card className="text-center">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <Star className="w-5 h-5 text-yellow-500" />
                            <span className="text-2xl font-bold">{userStats.level}</span>
                        </div>
                        <p className="text-sm text-gray-600">Level</p>
                    </CardContent>
                </Card>
                
                <Card className="text-center">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <Zap className="w-5 h-5 text-blue-500" />
                            <span className="text-2xl font-bold">{userStats.totalPoints.toLocaleString()}</span>
                        </div>
                        <p className="text-sm text-gray-600">Points</p>
                    </CardContent>
                </Card>

                <Card className="text-center">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <Flame className="w-5 h-5 text-orange-500" />
                            <span className="text-2xl font-bold">{userStats.streak}</span>
                        </div>
                        <p className="text-sm text-gray-600">Day Streak</p>
                    </CardContent>
                </Card>

                <Card className="text-center">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <CheckCircle className="w-5 h-5 text-green-500" />
                            <span className="text-2xl font-bold">{userStats.pathsCompleted}</span>
                        </div>
                        <p className="text-sm text-gray-600">Completed</p>
                    </CardContent>
                </Card>

                <Card className="text-center">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <Trophy className="w-5 h-5 text-purple-500" />
                            <span className="text-2xl font-bold">{userStats.badgesEarned}</span>
                        </div>
                        <p className="text-sm text-gray-600">Badges</p>
                    </CardContent>
                </Card>

                <Card className="text-center">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <Award className="w-5 h-5 text-indigo-500" />
                            <span className="text-lg font-bold">{userStats.rank}</span>
                        </div>
                        <p className="text-sm text-gray-600">Rank</p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Content Tabs */}
            <Tabs defaultValue="paths" className="space-y-6">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="paths" className="flex items-center gap-2">
                        <BookOpen className="w-4 h-4" />
                        Learning Paths
                    </TabsTrigger>
                    <TabsTrigger value="challenges" className="flex items-center gap-2">
                        <Target className="w-4 h-4" />
                        Challenges
                    </TabsTrigger>
                    <TabsTrigger value="achievements" className="flex items-center gap-2">
                        <Trophy className="w-4 h-4" />
                        Achievements
                    </TabsTrigger>
                    <TabsTrigger value="leaderboard" className="flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        Leaderboard
                    </TabsTrigger>
                </TabsList>

                {/* Learning Paths Tab */}
                <TabsContent value="paths" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {learningPaths.map((path) => {
                            const progress = userProgress.find(p => p.learning_path_id === path.id);
                            const completionPercentage = progress?.completion_percentage || 0;
                            const isLocked = path.prerequisites && path.prerequisites.length > 0; // Simplified logic
                            
                            return (
                                <Card key={path.id} className={`hover:shadow-lg transition-shadow ${isLocked ? 'opacity-60' : ''}`}>
                                    <CardHeader>
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1">
                                                <CardTitle className="flex items-center gap-2">
                                                    {isLocked ? <Lock className="w-4 h-4" /> : <BookOpen className="w-4 h-4" />}
                                                    {path.path_name}
                                                </CardTitle>
                                                <div className="flex gap-2 mt-2">
                                                    <Badge className={getDifficultyColor(path.difficulty_level)}>
                                                        {path.difficulty_level}
                                                    </Badge>
                                                    <Badge variant="outline">
                                                        {path.total_points} pts
                                                    </Badge>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-2xl font-bold text-blue-600">
                                                    {completionPercentage}%
                                                </div>
                                                <div className="text-sm text-gray-500">Complete</div>
                                            </div>
                                        </div>
                                        <CardDescription className="mt-2">
                                            {path.description}
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            <Progress value={completionPercentage} className="h-2" />
                                            
                                            <div className="flex items-center justify-between text-sm text-gray-600">
                                                <span className="flex items-center gap-1">
                                                    <Clock className="w-4 h-4" />
                                                    {path.estimated_duration}
                                                </span>
                                                <span>{path.modules?.length || 0} modules</span>
                                            </div>

                                            <div className="flex gap-2">
                                                {!isLocked ? (
                                                    <>
                                                        <Link to={createPageUrl(`LearningPath?id=${path.id}`)} className="flex-1">
                                                            <Button className="w-full" variant={completionPercentage > 0 ? "default" : "default"}>
                                                                {completionPercentage > 0 ? "Continue" : "Start Learning"}
                                                                <PlayCircle className="w-4 h-4 ml-2" />
                                                            </Button>
                                                        </Link>
                                                        <Button variant="outline" size="icon">
                                                            <BookOpen className="w-4 h-4" />
                                                        </Button>
                                                    </>
                                                ) : (
                                                    <Button disabled className="w-full">
                                                        <Lock className="w-4 h-4 mr-2" />
                                                        Locked
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                </TabsContent>

                {/* Challenges Tab */}
                <TabsContent value="challenges" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {challenges.map((challenge) => (
                            <Card key={challenge.id} className="hover:shadow-lg transition-shadow">
                                <CardHeader>
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <CardTitle className="flex items-center gap-2">
                                                <Target className="w-5 h-5 text-orange-500" />
                                                {challenge.challenge_name}
                                            </CardTitle>
                                            <div className="flex gap-2 mt-2">
                                                <Badge className={getDifficultyColor(challenge.difficulty)}>
                                                    {challenge.difficulty}
                                                </Badge>
                                                <Badge variant="outline" className="capitalize">
                                                    {challenge.challenge_type}
                                                </Badge>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-xl font-bold text-orange-600">
                                                {challenge.reward_points}
                                            </div>
                                            <div className="text-sm text-gray-500">points</div>
                                        </div>
                                    </div>
                                    <CardDescription>
                                        {challenge.description}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="flex items-center gap-1">
                                                <Users className="w-4 h-4" />
                                                {challenge.participants} participants
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <TrendingUp className="w-4 h-4" />
                                                {challenge.completion_rate}% completed
                                            </span>
                                        </div>
                                        
                                        <Progress value={challenge.completion_rate} className="h-2" />
                                        
                                        <div className="text-sm text-gray-600">
                                            <p><strong>Requirements:</strong></p>
                                            <ul className="list-disc list-inside ml-2 mt-1">
                                                {challenge.requirements?.slice(0, 2).map((req, index) => (
                                                    <li key={index}>{req}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        
                                        <Button className="w-full">
                                            <Rocket className="w-4 h-4 mr-2" />
                                            Join Challenge
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>

                {/* Achievements Tab */}
                <TabsContent value="achievements" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {achievements.map((achievement) => (
                            <Card key={achievement.id} className="text-center hover:shadow-lg transition-shadow">
                                <CardContent className="p-6">
                                    <div className={`text-6xl mb-4 ${getRarityColor(achievement.rarity)}`}>
                                        <Trophy className="w-12 h-12 mx-auto" />
                                    </div>
                                    <h3 className="font-bold text-lg mb-2">{achievement.achievement_name}</h3>
                                    <p className="text-sm text-gray-600 mb-3">{achievement.description}</p>
                                    <div className="flex items-center justify-center gap-2">
                                        <Badge className={`${getRarityColor(achievement.rarity)} bg-opacity-10`}>
                                            {achievement.rarity}
                                        </Badge>
                                        <Badge variant="outline">
                                            {achievement.points_value} pts
                                        </Badge>
                                    </div>
                                    {achievement.unlock_date && (
                                        <p className="text-xs text-gray-500 mt-2">
                                            Earned {new Date(achievement.unlock_date).toLocaleDateString()}
                                        </p>
                                    )}
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>

                {/* Leaderboard Tab */}
                <TabsContent value="leaderboard" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Trophy className="w-5 h-5 text-yellow-500" />
                                Global Leaderboard
                            </CardTitle>
                            <CardDescription>
                                Top learners on the PIKAR AI platform
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {/* Mock leaderboard data */}
                                {[
                                    { rank: 1, name: "You", points: userStats.totalPoints, level: userStats.level, badge: "🥇" },
                                    { rank: 2, name: "Alex Chen", points: 15420, level: 18, badge: "🥈" },
                                    { rank: 3, name: "Sarah Johnson", points: 14890, level: 17, badge: "🥉" },
                                    { rank: 4, name: "Mike Rodriguez", points: 13750, level: 16, badge: "" },
                                    { rank: 5, name: "Emma Wilson", points: 12980, level: 15, badge: "" }
                                ].map((user) => (
                                    <div key={user.rank} className={`flex items-center justify-between p-4 rounded-lg ${user.name === 'You' ? 'bg-blue-50 border-2 border-blue-200' : 'bg-gray-50'}`}>
                                        <div className="flex items-center gap-4">
                                            <div className="text-2xl font-bold w-8">
                                                {user.badge || `#${user.rank}`}
                                            </div>
                                            <div>
                                                <div className="font-semibold flex items-center gap-2">
                                                    {user.name}
                                                    {user.name === 'You' && <Badge>You</Badge>}
                                                </div>
                                                <div className="text-sm text-gray-600">Level {user.level}</div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-bold text-lg">{user.points.toLocaleString()}</div>
                                            <div className="text-sm text-gray-600">points</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
