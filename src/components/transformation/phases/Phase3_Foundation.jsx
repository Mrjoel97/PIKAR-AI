import React from 'react';
import PhaseLayout from './PhaseLayout';
import { toast } from 'sonner';

export default function Phase3_Foundation({ initiative, deliverables, onUpdate, onPhaseComplete }) {
    
    const actions = [
        {
            title: "Build Core Infrastructure",
            description: "Set up the necessary technical and operational infrastructure.",
            buttonText: "Build Infrastructure",
            onClick: () => toast.info("Infrastructure building coming soon!"),
            isComplete: false,
        },
        {
            title: "Implement Foundational Systems",
            description: "Deploy and configure core systems and platforms.",
            buttonText: "Implement Systems",
            onClick: () => toast.info("System implementation coming soon!"),
            isComplete: false,
        },
        {
            title: "Activate Governance Model",
            description: "Put the defined governance structures and processes into action.",
            buttonText: "Activate Governance",
            onClick: () => toast.info("Governance activation coming soon!"),
            isComplete: false,
        }
    ];

    return (
        <PhaseLayout
            title="Phase 3: Foundation & Infrastructure"
            description="Establish core infrastructure, build foundational capabilities, and implement governance structures."
            actions={actions}
            onPhaseComplete={onPhaseComplete}
            isPhaseComplete={actions.every(a => a.isComplete)}
            deliverables={deliverables.filter(d => d.phase === 'Foundation & Infrastructure')}
        />
    );
}