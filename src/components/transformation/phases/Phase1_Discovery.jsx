import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { FileText, Lightbulb, Loader2 } from 'lucide-react';
import { InitiativeDeliverable } from '@/api/entities';
import { InvokeLLM } from '@/api/integrations';
import { toast } from 'sonner';

const phaseMilestones = [
  { id: 'ms1', text: 'Identify and validate business opportunities' },
  { id: 'ms2', text: 'Assess current state capabilities and gaps' },
  { id: 'ms3', text: 'Define initial scope and success criteria' },
  { id: 'ms4', text: 'Establish stakeholder alignment' },
];

export default function Phase1_Discovery({ initiative, deliverables, onComplete }) {
    const [completedMilestones, setCompletedMilestones] = useState(
        deliverables.map(d => d.deliverable_type)
    );
    const [isLoading, setIsLoading] = useState(false);

    const handleGenerateDeliverable = async (milestoneText, deliverableType) => {
        setIsLoading(true);
        toast.info(`Generating ${deliverableType}...`);
        try {
            const prompt = `For the business initiative "${initiative.initiative_name}" (${initiative.initiative_description}), generate a concise "${deliverableType}" document.`;
            const content = await InvokeLLM({ prompt, add_context_from_internet: true });
            
            await InitiativeDeliverable.create({
                initiative_id: initiative.id,
                phase: "Discovery & Assessment",
                deliverable_name: `${deliverableType} for ${initiative.initiative_name}`,
                deliverable_type: deliverableType,
                content: content,
            });

            setCompletedMilestones([...completedMilestones, deliverableType]);
            toast.success(`${deliverableType} generated successfully.`);
        } catch (error) {
            console.error(`Error generating ${deliverableType}:`, error);
            toast.error(`Failed to generate ${deliverableType}.`);
        } finally {
            setIsLoading(false);
        }
    };
    
    const allMilestonesCompleted = phaseMilestones.every(ms => 
        completedMilestones.includes(ms.text.split(' ').join('_'))
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>Phase 1: Discovery & Assessment</CardTitle>
                <CardDescription>Identify opportunities, assess capabilities, define scope, and align stakeholders.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div>
                    <h4 className="font-semibold mb-3">Milestones & Deliverables</h4>
                    <div className="space-y-4">
                        {phaseMilestones.map(milestone => {
                            const deliverableType = milestone.text.split(' ').join('_');
                            const isCompleted = completedMilestones.includes(deliverableType);
                            return (
                                <div key={milestone.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                                    <div className="flex items-center gap-3">
                                        <Checkbox checked={isCompleted} disabled />
                                        <span className={isCompleted ? 'line-through' : ''}>{milestone.text}</span>
                                    </div>
                                    {isCompleted ? (
                                        <Button variant="ghost" size="sm" className="text-green-600">
                                            <FileText className="w-4 h-4 mr-2" /> View
                                        </Button>
                                    ) : (
                                        <Button 
                                            size="sm" 
                                            variant="outline"
                                            onClick={() => handleGenerateDeliverable(milestone.text, deliverableType)}
                                            disabled={isLoading}
                                        >
                                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lightbulb className="w-4 h-4 mr-2" />}
                                            Generate
                                        </Button>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
                
                <div className="pt-6 border-t">
                    <Button 
                        onClick={() => onComplete("Discovery & Assessment", [])} 
                        disabled={!allMilestonesCompleted || isLoading}
                        className="w-full"
                    >
                        Mark Phase as Complete & Proceed to Planning
                    </Button>
                    {!allMilestonesCompleted && (
                        <p className="text-xs text-center text-gray-500 mt-2">
                            All milestones must be completed to proceed.
                        </p>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}