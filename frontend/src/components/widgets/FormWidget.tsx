'use client'
import React, { useState, FormEvent } from 'react';
import { WidgetDefinition, FormDataDefinition, FieldDefinition } from '@/types/widgets';
import { Send, CheckCircle2 } from 'lucide-react';

interface FormWidgetProps {
    definition: WidgetDefinition;
    onAction?: (action: string, data: any) => void;
}

export default function FormWidget({ definition, onAction }: FormWidgetProps) {
    const data = definition.data as unknown as FormDataDefinition;
    const { fields = [], submitLabel = 'Submit' } = data;
    const [values, setValues] = useState<Record<string, string>>(() => {
        const initial: Record<string, string> = {};
        fields.forEach(f => {
            if (f.defaultValue) initial[f.name] = f.defaultValue;
            else if (f.type === 'select' && f.options && f.options.length > 0) initial[f.name] = f.options[0];
            else initial[f.name] = '';
        });
        return initial;
    });
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();

        // Basic validation check (HTML5 validation handles UI)
        const missing = fields.filter(f => f.required && !values[f.name]);
        if (missing.length > 0) return;

        if (onAction) {
            onAction('submit_form', values);
            setSubmitted(true);
        }
    };

    const handleChange = (name: string, value: string) => {
        setValues(prev => ({ ...prev, [name]: value }));
    };

    if (submitted) {
        return (
            <div className="flex flex-col items-center justify-center p-8 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-800 rounded-full flex items-center justify-center mb-4 text-green-600 dark:text-green-400">
                    <CheckCircle2 size={24} />
                </div>
                <h3 className="text-lg font-semibold text-green-800 dark:text-green-300">Submitted Successfully</h3>
                <p className="text-sm text-green-600 dark:text-green-400 mb-4 text-center">
                    The agent has received your form data.
                </p>
                <button
                    onClick={() => setSubmitted(false)}
                    className="text-sm text-green-700 hover:underline"
                >
                    Submit another response
                </button>
            </div>
        );
    }

    return (
        <div className="w-full">
            <h2 className="text-lg font-semibold mb-4 text-slate-800 dark:text-slate-200">
                {definition.title}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                {fields.map((field) => (
                    <div key={field.name} className="space-y-1">
                        <label
                            htmlFor={field.name}
                            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
                        >
                            {field.label}
                            {field.required && <span className="text-red-500 ml-1">*</span>}
                        </label>

                        {field.type === 'textarea' ? (
                            <textarea
                                id={field.name}
                                required={field.required}
                                value={values[field.name]}
                                onChange={(e) => handleChange(field.name, e.target.value)}
                                rows={3}
                                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                placeholder={field.placeholder}
                            />
                        ) : field.type === 'select' ? (
                            <select
                                id={field.name}
                                required={field.required}
                                value={values[field.name]}
                                onChange={(e) => handleChange(field.name, e.target.value)}
                                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all appearance-none"
                            >
                                {field.options?.map(opt => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>
                        ) : (
                            <input
                                type={field.type}
                                id={field.name}
                                required={field.required}
                                value={values[field.name]}
                                onChange={(e) => handleChange(field.name, e.target.value)}
                                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                placeholder={field.placeholder}
                            />
                        )}
                    </div>
                ))}

                <div className="pt-2">
                    <button
                        type="submit"
                        className="w-full inline-flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-sm"
                    >
                        <span>{submitLabel}</span>
                        <Send size={16} className="ml-2" />
                    </button>
                </div>
            </form>
        </div>
    );
}
