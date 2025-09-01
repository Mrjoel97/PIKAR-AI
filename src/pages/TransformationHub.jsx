import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BusinessInitiative } from '@/api/entities';
import { Link, useNavigate } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { Route, Plus, Target, CheckCircle, Clock } from 'lucide-react';
import { toast, Toaster } from 'sonner';
import { motion } from 'framer-motion';

const phases = [
  "Discovery & Assessment",
  "Planning & Design",
  "Foundation & Infrastructure",
  "Execution & Optimization",
  "Scale & Expansion",
  "Sustainability"
];

export default function TransformationHub() {
    const [initiatives, setInitiatives] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        loadInitiatives();
    }, []);

    const loadInitiatives = async () => {
        setIsLoading(true);
        try {
            const fetchedInitiatives = await BusinessInitiative.list('-created_date');
            setInitiatives(fetchedInitiatives);
        } catch (error) {
            console.error("Error loading initiatives:", error);
            toast.error("Failed to load business initiatives.");
        } finally {
            setIsLoading(false);
        }
    };
    
    const getPhaseColor = (phase) => {
        const colors = [
            'border-emerald-500', 'border-emerald-600', 'border-emerald-700', 
            'border-emerald-800', 'border-emerald-900', 'border-emerald-600'
        ];
        return colors[phases.indexOf(phase)] || 'border-emerald-500';
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800 border-red-200';
            case 'High': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'Medium': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
            case 'Low': return 'bg-green-100 text-green-800 border-green-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'Completed': return <CheckCircle className="w-4 h-4 text-emerald-600" />;
            case 'In Progress': return <Clock className="w-4 h-4 text-emerald-600 animate-pulse" />;
            default: return <Clock className="w-4 h-4 text-gray-400" />;
        }
    };

    const handleCardClick = (id) => {
        navigate(createPageUrl(`InitiativeDetails?id=${id}`));
    };

    return (
        <div className="max-w-full mx-auto space-y-8 bg-pikar-hero min-h-screen p-6">
            <Toaster richColors />
            
            {/* Header with premium emerald branding */}
            <motion.div 
                className="flex items-center justify-between"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
            >
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3 bg-gradient-to-r from-emerald-900 to-emerald-700 bg-clip-text text-transparent">
                        <Route className="w-8 h-8 text-emerald-600" />
                        Transformation Hub
                    </h1>
                    <p className="text-lg text-gray-600 mt-1">
                        Visualize and manage your entire business transformation journey.
                    </p>
                </div>
                <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                >
                    <Link to={createPageUrl("CreateInitiative")}>
                        <Button size="lg" className="bg-emerald-900 hover:bg-emerald-800">
                            <Plus className="w-5 h-5 mr-2" />
                            New Initiative
                        </Button>
                    </Link>
                </motion.div>
            </motion.div>

            {/* Kanban-style Board with consistent emerald theming */}
            {isLoading ? (
                <div className="text-center p-12">
                    <motion.div 
                        className="w-12 h-12 border-4 border-emerald-200 border-t-emerald-600 rounded-full mx-auto"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    <p className="mt-4 text-emerald-700">Loading Initiatives...</p>
                </div>
            ) : initiatives.length === 0 ? (
                 <Card className="text-center py-16 px-6 border-dashed border-2 border-emerald-200 bg-emerald-50/50">
                    <Target className="mx-auto h-12 w-12 text-emerald-400" />
                    <h3 className="mt-2 text-xl font-medium text-emerald-900">No Initiatives Found</h3>
                    <p className="mt-1 text-emerald-700">Get started by creating your first business transformation initiative.</p>
                    <div className="mt-6">
                         <Link to={createPageUrl("CreateInitiative")}>
                            <Button className="bg-emerald-900 hover:bg-emerald-800">
                                <Plus className="mr-2 h-4 w-4" /> Create New Initiative
                            </Button>
                        </Link>
                    </div>
                </Card>
            ) : (
                <motion.div 
                    className="flex space-x-4 overflow-x-auto pb-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5 }}
                >
                    {phases.map((phase, index) => (
                        <motion.div 
                            key={phase} 
                            className="min-w-[320px] flex-shrink-0"
                            initial={{ opacity: 0, x: 50 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1, duration: 0.5 }}
                        >
                            <Card className="bg-white border-emerald-100 h-full">
                                <CardHeader className={`border-b-4 ${getPhaseColor(phase)}`}>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <span className="text-emerald-600">{index + 1}</span> {phase}
                                    </CardTitle>
                                    <CardDescription>
                                        {initiatives.filter(i => i.current_phase === phase).length} initiatives
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="p-4 space-y-3">
                                    {initiatives
                                        .filter(i => i.current_phase === phase)
                                        .map(initiative => (
                                            <motion.div
                                                key={initiative.id}
                                                whileHover={{ scale: 1.02, y: -2 }}
                                                whileTap={{ scale: 0.98 }}
                                                transition={{ duration: 0.18 }}
                                            >
                                                <Card 
                                                    className="bg-white hover:shadow-lg cursor-pointer border-emerald-50 hover:border-emerald-200"
                                                    onClick={() => handleCardClick(initiative.id)}
                                                >
                                                    <CardContent className="p-4">
                                                        <div className="flex justify-between items-start">
                                                            <p className="font-semibold text-md text-emerald-900">{initiative.initiative_name}</p>
                                                            {getStatusIcon(initiative.status)}
                                                        </div>
                                                        <p className="text-sm text-gray-500 mt-1">{initiative.category}</p>
                                                        <div className="mt-3 flex justify-between items-center">
                                                            <Badge className={getPriorityColor(initiative.priority)}>
                                                                {initiative.priority}
                                                            </Badge>
                                                            <span className="text-xs text-gray-400">
                                                                Updated: {new Date(initiative.updated_date).toLocaleDateString()}
                                                            </span>
                                                        </div>
                                                    </CardContent>
                                                </Card>
                                            </motion.div>
                                        ))}
                                    {initiatives.filter(i => i.current_phase === phase).length === 0 && (
                                        <div className="text-center p-6 text-emerald-500 text-sm">
                                            No initiatives in this phase.
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </motion.div>
                    ))}
                </motion.div>
            )}
        </div>
    );
}