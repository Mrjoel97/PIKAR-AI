import React from 'react';
import PhaseLayout from './PhaseLayout';
import { toast } from 'sonner';

export default function Phase5_Scale({ initiative, deliverables, onUpdate, onPhaseComplete }) {
    
    const actions = [
        {
            title: "Develop Scaling Strategy",
            description: "Create a plan to scale successful initiatives across the organization.",
            buttonText: "Develop Strategy",
            onClick: () => toast.info("Scaling strategy development coming soon!"),
            isComplete: false,
        },
        {
            title: "Replicate Best Practices",
            description: "Document and replicate best practices and lessons learned.",
            buttonText: "Replicate Practices",
            onClick: () => toast.info("Best practice replication coming soon!"),
            isComplete: false,
        },
        {
            title: "Manage Organizational Change",
            description: "Implement change management plans to ensure smooth adoption.",
            buttonText: "Manage Change",
            onClick: () => toast.info("Change management features coming soon!"),
            isComplete: false,
        }
    ];

    return (
        <PhaseLayout
            title="Phase 5: Scale & Expansion"
            description="Scale successful initiatives, expand capabilities to new areas, and replicate best practices to maximize impact."
            actions={actions}
            onPhaseComplete={onPhaseComplete}
            isPhaseComplete={actions.every(a => a.isComplete)}
            deliverables={deliverables.filter(d => d.phase === 'Scale & Expansion')}
        />
    );
}