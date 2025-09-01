import React from 'react';
import { CheckCircle, Sparkles, Trophy, Target, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';

export const SuccessAnimation = ({ 
    title = "Success!", 
    message = "Your request has been completed",
    showConfetti = true 
}) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center py-8 text-center"
    >
        {showConfetti && (
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute inset-0 pointer-events-none"
            >
                {[...Array(6)].map((_, i) => (
                    <motion.div
                        key={i}
                        className="absolute w-2 h-2 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full"
                        initial={{ 
                            x: '50%', 
                            y: '50%',
                            scale: 0 
                        }}
                        animate={{ 
                            x: `${50 + (Math.random() - 0.5) * 200}%`,
                            y: `${50 + (Math.random() - 0.5) * 200}%`,
                            scale: [0, 1, 0],
                            rotate: 360
                        }}
                        transition={{ 
                            duration: 2,
                            delay: i * 0.1,
                            ease: "easeOut"
                        }}
                    />
                ))}
            </motion.div>
        )}
        
        <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ 
                type: "spring",
                stiffness: 200,
                damping: 10,
                delay: 0.2
            }}
            className="mb-4"
        >
            <div className="p-4 bg-green-100 dark:bg-green-900/30 rounded-full">
                <CheckCircle className="w-12 h-12 text-green-600 dark:text-green-400" />
            </div>
        </motion.div>
        
        <motion.h3
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="text-xl font-bold text-green-900 dark:text-green-100 mb-2"
        >
            {title}
        </motion.h3>
        
        <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-green-700 dark:text-green-300"
        >
            {message}
        </motion.p>
    </motion.div>
);

export const AchievementUnlocked = ({ 
    achievement = "First Analysis Complete!",
    description = "You've successfully completed your first AI analysis",
    icon: Icon = Trophy
}) => (
    <motion.div
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 100 }}
        className="fixed top-4 right-4 z-50 p-4 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg shadow-lg max-w-sm"
    >
        <div className="flex items-center gap-3">
            <motion.div
                initial={{ rotate: -180, scale: 0 }}
                animate={{ rotate: 0, scale: 1 }}
                transition={{ delay: 0.2 }}
            >
                <Icon className="w-8 h-8" />
            </motion.div>
            <div className="flex-1">
                <h4 className="font-bold text-sm">Achievement Unlocked!</h4>
                <p className="text-xs opacity-90">{achievement}</p>
                <p className="text-xs opacity-75 mt-1">{description}</p>
            </div>
        </div>
    </motion.div>
);

export const ResultsCard = ({ 
    title,
    children,
    onSave,
    onShare,
    isSaving = false
}) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
    >
        <div className="p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-purple-500" />
                    {title}
                </h3>
                <div className="flex items-center gap-2">
                    {onSave && (
                        <Button 
                            variant="outline" 
                            size="sm"
                            onClick={onSave}
                            disabled={isSaving}
                        >
                            {isSaving ? "Saving..." : "Save"}
                        </Button>
                    )}
                    {onShare && (
                        <Button 
                            variant="outline" 
                            size="sm"
                            onClick={onShare}
                        >
                            Share
                        </Button>
                    )}
                </div>
            </div>
            {children}
        </div>
    </motion.div>
);