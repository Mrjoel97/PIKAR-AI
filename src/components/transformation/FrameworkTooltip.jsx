import React from 'react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const frameworkDetails = {
    "SWOT": "Strengths, Weaknesses, Opportunities, Threats - A strategic planning technique.",
    "SNAP": "Simple, Nimble, Actionable, Practical - A framework for complexity reduction.",
    "MMR": "Mean Mixing Ratio - An advanced method for portfolio optimization.",
    "ISO 9001": "An international standard for Quality Management Systems (QMS)."
};

export default function FrameworkTooltip({ framework, children }) {
    const description = frameworkDetails[framework];
    if (!description) return <>{children}</>;

    return (
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger asChild>{children}</TooltipTrigger>
                <TooltipContent>
                    <p className="font-bold">{framework}</p>
                    <p>{description}</p>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}