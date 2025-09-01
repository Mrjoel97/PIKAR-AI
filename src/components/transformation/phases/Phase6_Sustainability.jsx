import React from 'react';
import PhaseLayout from './PhaseLayout';
import { toast } from 'sonner';

export default function Phase6_Sustainability({ initiative, deliverables, onUpdate, onPhaseComplete }) {
    
    const actions = [
        {
            title: "Embed Continuous Improvement",
            description: "Establish a culture and processes for ongoing improvement.",
            buttonText: "Embed Culture",
            onClick: () => toast.info("Continuous improvement features coming soon!"),
            isComplete: false,
        },
        {
            title: "Ensure Long-Term Sustainability",
            description: "Develop plans to ensure the long-term viability and success of the initiative.",
            buttonText: "Plan Sustainability",
            onClick: () => toast.info("Sustainability planning coming soon!"),
            isComplete: false,
        },
        {
            title: "Maximize Return on Investment",
            description: "Analyze and optimize for maximum long-term ROI.",
            buttonText: "Maximize ROI",
            onClick: () => toast.info("ROI maximization analysis coming soon!"),
            isComplete: false,
        }
    ];

    return (
        <PhaseLayout
            title="Phase 6: Sustainability"
            description="Achieve optimal business performance, ensure long-term sustainability, and embed a culture of continuous improvement."
            actions={actions}
            onPhaseComplete={onPhaseComplete}
            isPhaseComplete={actions.every(a => a.isComplete)}
            deliverables={deliverables.filter(d => d.phase === 'Sustainability')}
        />
    );
}