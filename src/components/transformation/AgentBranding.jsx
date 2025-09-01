import React from 'react';
import {
  Bot, LayoutDashboard, PenSquare, Settings, User, Lightbulb, Users, BarChart, Sparkles, DollarSign, UserCheck, ShieldCheck, SlidersHorizontal, Cpu, Network, Shield, Route, Award
} from "lucide-react";

const agentDetails = {
    "Strategic Planning": { icon: Lightbulb, color: "text-purple-500" },
    "Content Creation": { icon: PenSquare, color: "text-blue-500" },
    "Customer Support": { icon: Users, color: "text-green-500" },
    "Sales Intelligence": { icon: BarChart, color: "text-orange-500" },
    "Data Analysis": { icon: Bot, color: "text-sky-500" },
    "Marketing Automation": { icon: Sparkles, color: "text-pink-500" },
    "Financial Analysis": { icon: DollarSign, color: "text-teal-500" },
    "HR & Recruitment": { icon: UserCheck, color: "text-indigo-500" },
    "Compliance & Risk": { icon: ShieldCheck, color: "text-red-500" },
    "Operations Optimization": { icon: SlidersHorizontal, color: "text-gray-500" },
};

export default function AgentBranding({ agentName }) {
    const details = agentDetails[agentName] || { icon: Bot, color: "text-gray-400" };
    const Icon = details.icon;

    return (
        <span className={`inline-flex items-center gap-1 font-semibold ${details.color}`}>
            <Icon className="w-4 h-4" />
            {agentName}
        </span>
    );
}