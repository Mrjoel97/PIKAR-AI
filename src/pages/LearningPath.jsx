
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { LearningPath as LearningPathEntity, UserProgress } from '@/api/entities';
import { InvokeLLM } from '@/api/integrations';
import { createPageUrl } from '@/utils';
import { 
    ArrowLeft, PlayCircle, CheckCircle, Clock, Star, 
    BookOpen, Award, ChevronRight, Brain, Target 
} from 'lucide-react';
import { toast, Toaster } from 'sonner';
import ReactMarkdown from 'react-markdown';

export default function LearningPathPage() {
    const [searchParams] = useSearchParams();
    const pathId = searchParams.get('id');
    
    const [learningPath, setLearningPath] = useState(null);
    const [userProgress, setUserProgress] = useState(null);
    const [currentModule, setCurrentModule] = useState(null);
    const [moduleContent, setModuleContent] = useState('');
    const [isGeneratingContent, setIsGeneratingContent] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    const loadLearningPath = useCallback(async () => {
        setIsLoading(true);
        try {
            const [pathData, progressData] = await Promise.all([
                LearningPathEntity.get(pathId),
                UserProgress.filter({ learning_path_id: pathId })
            ]);
            
            setLearningPath(pathData);
            setUserProgress(progressData[0] || {
                learning_path_id: pathId,
                current_module: 0,
                completed_modules: [],
                points_earned: 0,
                completion_percentage: 0,
                status: 'not_started'
            });
            
            // Set current module
            const currentModuleIndex = progressData[0]?.current_module || 0;
            setCurrentModule(pathData.modules[currentModuleIndex]);
        } catch (error) {
            console.error("Error loading learning path:", error);
            toast.error("Failed to load learning path");
        } finally {
            setIsLoading(false);
        }
    }, [pathId]);

    useEffect(() => {
        if (pathId) {
            loadLearningPath();
        }
    }, [pathId, loadLearningPath]);

    const generateModuleContent = async (module) => {
        setIsGeneratingContent(true);
        const prompt = `You are the PIKAR AI Learning Content Generator. Create engaging, practical learning content for this module:

**Learning Path:** ${learningPath.path_name}
**Module:** ${module.module_name}
**Type:** ${module.module_type}
**Target Audience:** ${learningPath.difficulty_level} level users

**Learning Objectives for this Path:**
${learningPath.learning_objectives?.join('\n')}

**Module Requirements:**
${module.content}

Generate comprehensive learning content that includes:
1. **Introduction** - Why this module matters
2. **Core Concepts** - Key information with examples
3. **Practical Application** - How to apply this in PIKAR AI
4. **Pro Tips** - Advanced techniques and best practices
5. **Common Pitfalls** - What to avoid

Make the content engaging, practical, and specific to PIKAR AI's features. Use markdown formatting for better readability.`;

        try {
            const content = await InvokeLLM({ prompt });
            setModuleContent(content);
        } catch (error) {
            console.error("Error generating content:", error);
            toast.error("Failed to generate module content");
        } finally {
            setIsGeneratingContent(false);
        }
    };

    const completeModule = async () => {
        const completedModules = [...(userProgress.completed_modules || []), userProgress.current_module];
        const nextModuleIndex = userProgress.current_module + 1;
        const newCompletionPercentage = Math.round((completedModules.length / learningPath.modules.length) * 100);
        const pointsEarned = (userProgress.points_earned || 0) + (currentModule.points_value || 0);

        try {
            const updatedProgress = {
                ...userProgress,
                current_module: nextModuleIndex,
                completed_modules: completedModules,
                completion_percentage: newCompletionPercentage,
                points_earned: pointsEarned,
                status: nextModuleIndex >= learningPath.modules.length ? 'completed' : 'in_progress'
            };

            await UserProgress.update(userProgress.id, updatedProgress);
            setUserProgress(updatedProgress);

            // Move to next module or show completion
            if (nextModuleIndex < learningPath.modules.length) {
                setCurrentModule(learningPath.modules[nextModuleIndex]);
                setModuleContent('');
            } else {
                toast.success("🎉 Congratulations! You've completed this learning path!");
            }

            toast.success(`Module completed! +${currentModule.points_value} points`);
        } catch (error) {
            console.error("Error completing module:", error);
            toast.error("Failed to complete module");
        }
    };

    if (isLoading) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <div className="animate-pulse space-y-6">
                    <div className="h-8 bg-gray-200 rounded w-1/3"></div>
                    <div className="h-64 bg-gray-200 rounded"></div>
                </div>
            </div>
        );
    }

    if (!learningPath) {
        return (
            <div className="max-w-4xl mx-auto p-6 text-center">
                <h1 className="text-2xl font-bold text-gray-900">Learning Path Not Found</h1>
                <Link to={createPageUrl("LearningHub")}>
                    <Button className="mt-4">Back to Learning Hub</Button>
                </Link>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <Toaster richColors />
            
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link to={createPageUrl("LearningHub")}>
                    <Button variant="outline" size="icon">
                        <ArrowLeft className="w-4 h-4" />
                    </Button>
                </Link>
                <div className="flex-1">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        {learningPath.path_name}
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                        {learningPath.description}
                    </p>
                </div>
                <div className="text-right">
                    <div className="text-2xl font-bold text-blue-600">
                        {userProgress.completion_percentage}% Complete
                    </div>
                    <div className="text-sm text-gray-500">
                        {userProgress.points_earned || 0} / {learningPath.total_points} points
                    </div>
                </div>
            </div>

            {/* Progress Overview */}
            <Card>
                <CardContent className="p-6">
                    <div className="space-y-4">
                        <Progress value={userProgress.completion_percentage} className="h-3" />
                        <div className="flex justify-between text-sm text-gray-600">
                            <span>Module {(userProgress.current_module || 0) + 1} of {learningPath.modules.length}</span>
                            <span>{userProgress.completed_modules?.length || 0} modules completed</span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Module Navigation Sidebar */}
                <div className="lg:col-span-1">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Modules</CardTitle>
                        </CardHeader>
                        <CardContent className="p-2">
                            <div className="space-y-2">
                                {learningPath.modules.map((module, index) => {
                                    const isCompleted = userProgress.completed_modules?.includes(index);
                                    const isCurrent = userProgress.current_module === index;
                                    const isLocked = index > (userProgress.current_module || 0);

                                    return (
                                        <button
                                            key={index}
                                            onClick={() => {
                                                if (!isLocked) {
                                                    setCurrentModule(module);
                                                    setModuleContent('');
                                                }
                                            }}
                                            disabled={isLocked}
                                            className={`w-full text-left p-3 rounded-lg transition-colors ${
                                                isCurrent ? 'bg-blue-100 border-2 border-blue-300' :
                                                isCompleted ? 'bg-green-50 border border-green-200' :
                                                isLocked ? 'bg-gray-50 text-gray-400' : 'hover:bg-gray-50'
                                            }`}
                                        >
                                            <div className="flex items-center gap-2 mb-1">
                                                {isCompleted ? (
                                                    <CheckCircle className="w-4 h-4 text-green-500" />
                                                ) : isCurrent ? (
                                                    <PlayCircle className="w-4 h-4 text-blue-500" />
                                                ) : isLocked ? (
                                                    <Clock className="w-4 h-4 text-gray-400" />
                                                ) : (
                                                    <BookOpen className="w-4 h-4 text-gray-600" />
                                                )}
                                                <span className="font-medium text-sm">{module.module_name}</span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <Badge variant="outline" className="text-xs capitalize">
                                                    {module.module_type}
                                                </Badge>
                                                <span className="text-xs text-gray-500">
                                                    {module.points_value} pts
                                                </span>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Main Content Area */}
                <div className="lg:col-span-3">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Brain className="w-5 h-5 text-blue-500" />
                                {currentModule?.module_name}
                            </CardTitle>
                            <CardDescription>
                                <Badge className="capitalize">{currentModule?.module_type}</Badge>
                                <span className="ml-2">{currentModule?.points_value} points available</span>
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {moduleContent ? (
                                <>
                                    <div className="prose max-w-none">
                                        <ReactMarkdown>{moduleContent}</ReactMarkdown>
                                    </div>
                                    
                                    <div className="flex justify-between pt-6 border-t">
                                        <Button variant="outline">
                                            <BookOpen className="w-4 h-4 mr-2" />
                                            Take Notes
                                        </Button>
                                        <Button onClick={completeModule}>
                                            Complete Module
                                            <ChevronRight className="w-4 h-4 ml-2" />
                                        </Button>
                                    </div>
                                </>
                            ) : (
                                <div className="text-center py-12">
                                    <Target className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                                    <h3 className="text-xl font-semibold mb-2">Ready to learn?</h3>
                                    <p className="text-gray-600 mb-6">
                                        Generate personalized content for this module to begin your learning journey.
                                    </p>
                                    <Button 
                                        onClick={() => generateModuleContent(currentModule)}
                                        disabled={isGeneratingContent}
                                        size="lg"
                                    >
                                        {isGeneratingContent ? (
                                            <>Generating Content...</>
                                        ) : (
                                            <>
                                                <PlayCircle className="w-5 h-5 mr-2" />
                                                Start Learning
                                            </>
                                        )}
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
