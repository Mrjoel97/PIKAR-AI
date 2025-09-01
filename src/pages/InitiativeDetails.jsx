import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { BusinessInitiative, InitiativeDeliverable } from '@/api/entities';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Edit, Trash2, CheckCircle, Clock } from 'lucide-react';
import JourneyStepper from '@/components/transformation/JourneyStepper';
import PhaseLayout from '@/components/transformation/phases/PhaseLayout';
import { toast, Toaster } from 'sonner';
import { createPageUrl } from '@/utils';

const DEFAULT_PHASES = [
    "Discovery & Assessment", 
    "Planning & Design", 
    "Foundation & Infrastructure",
    "Execution & Optimization", 
    "Scale & Expansion", 
    "Sustainability"
];

export default function InitiativeDetails() {
    const [initiative, setInitiative] = useState(null);
    const [deliverables, setDeliverables] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const navigate = useNavigate();
    const urlParams = new URLSearchParams(window.location.search);
    const initiativeId = urlParams.get('id');

    const loadData = useCallback(async () => {
        if (!initiativeId) {
            toast.error("No initiative ID provided.");
            setIsLoading(false);
            return;
        }
        setIsLoading(true);
        try {
            const fetchedInitiative = await BusinessInitiative.get(initiativeId);
            const fetchedDeliverables = await InitiativeDeliverable.filter({ initiative_id: initiativeId });
            setInitiative(fetchedInitiative);
            setDeliverables(Array.isArray(fetchedDeliverables) ? fetchedDeliverables : []);
        } catch (error) {
            console.error("Error loading initiative details:", error);
            toast.error("Failed to load initiative details.");
            navigate(createPageUrl("TransformationHub"));
        } finally {
            setIsLoading(false);
        }
    }, [initiativeId, navigate]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handlePhaseComplete = async (phaseName, generatedDeliverables) => {
        try {
            // Mark phase complete and save deliverables
            toast.success(`${phaseName} phase marked as complete!`);
            
            // Move to the next phase
            const currentIndex = DEFAULT_PHASES.indexOf(phaseName);
            if (currentIndex !== -1 && currentIndex < DEFAULT_PHASES.length - 1) {
                const nextPhase = DEFAULT_PHASES[currentIndex + 1];
                await BusinessInitiative.update(initiativeId, { current_phase: nextPhase });
                loadData(); // Reload data to reflect changes
            } else if (currentIndex === DEFAULT_PHASES.length - 1) {
                // Last phase completed
                await BusinessInitiative.update(initiativeId, { status: 'Completed' });
                loadData();
            }
        } catch (error) {
            console.error("Error completing phase:", error);
            toast.error("Failed to complete phase");
        }
    };
    
    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    if (isLoading) return <div className="text-center p-12">Loading initiative...</div>;
    if (!initiative) return <div className="text-center p-12">Initiative not found.</div>;

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <Toaster richColors />
            <Button variant="outline" onClick={() => navigate(createPageUrl("TransformationHub"))}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Transformation Hub
            </Button>

            {/* Initiative Header */}
            <Card>
                <CardHeader>
                    <div className="flex justify-between items-start">
                        <div>
                            <CardTitle className="text-3xl">{initiative.initiative_name || 'Untitled Initiative'}</CardTitle>
                            <CardDescription className="mt-2">{initiative.initiative_description || 'No description provided'}</CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                             <Badge variant={initiative.status === 'Completed' ? 'default' : 'outline'} className={initiative.status === 'Completed' ? 'bg-green-600 text-white' : ''}>
                                {initiative.status === 'Completed' ? <CheckCircle className="w-4 h-4 mr-2" /> : <Clock className="w-4 h-4 mr-2" />}
                                {initiative.status || 'Not Started'}
                            </Badge>
                            <Button variant="outline" size="icon"><Edit className="w-4 h-4" /></Button>
                            <Button variant="destructive" size="icon"><Trash2 className="w-4 h-4" /></Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="flex gap-4">
                    <Badge variant="secondary">Category: {initiative.category || 'General'}</Badge>
                    <Badge className={getPriorityColor(initiative.priority)}>Priority: {initiative.priority || 'Medium'}</Badge>
                </CardContent>
            </Card>

            {/* Journey Stepper */}
            <JourneyStepper 
                currentPhase={initiative.current_phase || DEFAULT_PHASES[0]} 
                phases={DEFAULT_PHASES}
            />

            {/* Phase Content */}
            <PhaseLayout 
                phase={initiative.current_phase || DEFAULT_PHASES[0]}
                initiative={initiative} 
                deliverables={deliverables.filter(d => d.phase === (initiative.current_phase || DEFAULT_PHASES[0]))}
                onPhaseComplete={handlePhaseComplete}
            />
        </div>
    );
}