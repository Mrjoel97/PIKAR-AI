import React from 'react';
import PhaseLayout from './PhaseLayout';
import { toast } from 'sonner';

export default function Phase2_PlanningAndDesign({ initiative, deliverables, onUpdate, onPhaseComplete }) {
    
    const actions = [
        {
            title: "Develop Strategic Plan",
            description: "Create a detailed strategic plan and implementation roadmap.",
            buttonText: "Develop Plan",
            onClick: () => toast.info("Strategic plan development coming soon!"),
            isComplete: false,
        },
        {
            title: "Design Target Architecture",
            description: "Define the target state for processes, systems, and organization.",
            buttonText: "Design Architecture",
            onClick: () => toast.info("Target architecture design coming soon!"),
            isComplete: false,
        },
        {
            title: "Establish Governance Framework",
            description: "Set up the governance model for decision-making and oversight.",
            buttonText: "Set Up Governance",
            onClick: () => toast.info("Governance framework setup coming soon!"),
            isComplete: false,
        }
    ];

    return (
        <PhaseLayout
            title="Phase 2: Strategic Planning & Design"
            description="Develop a comprehensive strategic plan, design the target state, and create a detailed implementation roadmap."
            actions={actions}
            onPhaseComplete={onPhaseComplete}
            isPhaseComplete={actions.every(a => a.isComplete)}
            deliverables={deliverables.filter(d => d.phase === 'Planning & Design')}
        />
    );
}