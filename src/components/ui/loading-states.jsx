import React from 'react';
import { Loader2, FileText, BarChart, Users, Target } from 'lucide-react';
import { Card, CardContent, CardHeader } from './card';

export const GlobalLoader = ({ message = "Loading..." }) => (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg flex items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            <span className="font-medium">{message}</span>
        </div>
    </div>
);

export const SkeletonCard = () => (
    <Card>
        <CardHeader>
            <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2 animate-pulse mt-2"></div>
        </CardHeader>
        <CardContent>
            <div className="space-y-2">
                <div className="h-3 bg-gray-200 rounded animate-pulse"></div>
                <div className="h-3 bg-gray-200 rounded w-5/6 animate-pulse"></div>
                <div className="h-3 bg-gray-200 rounded w-4/6 animate-pulse"></div>
            </div>
        </CardContent>
    </Card>
);

export const TableSkeleton = ({ rows = 5, columns = 4 }) => (
    <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="flex gap-4">
                {Array.from({ length: columns }).map((_, j) => (
                    <div key={j} className="h-4 bg-gray-200 rounded flex-1 animate-pulse"></div>
                ))}
            </div>
        ))}
    </div>
);

export const AgentLoadingState = ({ agentName }) => {
    const getIcon = () => {
        switch (agentName) {
            case 'Strategic Planning': return <Target className="w-8 h-8 text-purple-500" />;
            case 'Data Analysis': return <BarChart className="w-8 h-8 text-blue-500" />;
            case 'Content Creation': return <FileText className="w-8 h-8 text-green-500" />;
            default: return <Users className="w-8 h-8 text-gray-500" />;
        }
    };

    return (
        <div className="flex flex-col items-center justify-center py-12">
            <div className="relative">
                {getIcon()}
                <Loader2 className="w-4 h-4 animate-spin absolute -top-1 -right-1 text-blue-600" />
            </div>
            <p className="mt-4 font-medium text-gray-700 dark:text-gray-300">
                {agentName} is processing...
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
                This may take a few moments
            </p>
        </div>
    );
};

export const ProgressiveLoader = ({ stages, currentStage = 0 }) => (
    <div className="space-y-4 p-6">
        {stages.map((stage, index) => (
            <div key={index} className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                    ${index < currentStage ? 'bg-green-500 text-white' : 
                      index === currentStage ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>
                    {index < currentStage ? '✓' : index + 1}
                </div>
                <span className={index <= currentStage ? 'text-gray-900' : 'text-gray-400'}>
                    {stage}
                </span>
                {index === currentStage && <Loader2 className="w-4 h-4 animate-spin text-blue-600" />}
            </div>
        ))}
    </div>
);