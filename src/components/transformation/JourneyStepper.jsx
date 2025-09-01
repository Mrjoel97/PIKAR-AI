import React from 'react';
import { Check, Dot } from 'lucide-react';

export default function JourneyStepper({ currentPhase, phases }) {
    const defaultPhases = [
        "Discovery & Assessment", 
        "Planning & Design", 
        "Foundation & Infrastructure",
        "Execution & Optimization", 
        "Scale & Expansion", 
        "Sustainability"
    ];

    // Use provided phases or default phases, ensure it's always an array
    const phasesList = Array.isArray(phases) ? phases : defaultPhases;
    const currentPhaseIndex = phasesList.indexOf(currentPhase || '');

    return (
        <div className="flex items-center justify-between w-full">
            {phasesList.map((phase, index) => {
                const isCompleted = index < currentPhaseIndex;
                const isActive = index === currentPhaseIndex;

                return (
                    <React.Fragment key={phase}>
                        <div className="flex flex-col items-center text-center">
                            <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center border-2
                                ${isCompleted ? 'bg-blue-600 border-blue-600 text-white' : ''}
                                ${isActive ? 'bg-blue-100 border-blue-600 text-blue-600' : ''}
                                ${!isCompleted && !isActive ? 'bg-gray-100 border-gray-300 text-gray-400' : ''}`}
                            >
                                {isCompleted ? <Check className="w-5 h-5" /> : index + 1}
                            </div>
                            <p className={`mt-2 text-xs font-medium max-w-[80px]
                                ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>
                                {phase}
                            </p>
                        </div>
                        {index < phasesList.length - 1 && (
                            <div className={`flex-1 h-1 mx-2
                                ${isCompleted ? 'bg-blue-600' : 'bg-gray-200'}`}
                            />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}