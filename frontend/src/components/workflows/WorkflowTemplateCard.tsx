'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { WorkflowTemplate } from '@/services/workflows';
import { PlayIcon } from '@heroicons/react/24/outline';

interface WorkflowTemplateCardProps {
    template: WorkflowTemplate;
    onStart: (template: WorkflowTemplate) => void;
}

export default function WorkflowTemplateCard({ template, onStart }: WorkflowTemplateCardProps) {
    return (
        <motion.div
            whileHover={{ y: -4, boxShadow: "0 10px 30px -10px rgba(0,0,0,0.1)" }}
            className="group relative bg-white border border-slate-200 rounded-3xl p-6 transition-all duration-300"
        >
            <div className="absolute top-6 right-6">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 capitalize">
                    {template.category}
                </span>
            </div>

            <h3 className="text-lg font-semibold text-slate-900 mb-2 pr-16 leading-tight">
                {template.name}
            </h3>

            <p className="text-slate-500 text-sm mb-6 line-clamp-3 min-h-[60px]">
                {template.description}
            </p>

            <button
                onClick={() => onStart(template)}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
            >
                <PlayIcon className="w-4 h-4" />
                <span className="text-sm font-medium">Start Workflow</span>
            </button>
        </motion.div>
    );
}
