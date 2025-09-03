
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { CorrectiveAction } from '@/api/entities';
import { X, AlertTriangle, Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useValidation } from '@/hooks/useValidation';
import { CorrectiveActionCreateSchema } from '@/lib/validation/schemas';
import ErrorBoundary from '@/components/ErrorBoundary';

function CorrectiveActionForm({ onClose, onSuccess }) {
    const initialData = {
        title: '',
        non_conformity: '',
        root_cause_analysis: '',
        action_plan: '',
        assigned_to: '',
        due_date: '',
        priority: 'Medium',
        verification_method: '',
        iso_clause: ''
    };

    const {
        data: formData,
        errors,
        isValid,
        isValidating,
        updateField,
        handleBlur,
        validateAll,
        getFieldError,
        hasFieldError
    } = useValidation(CorrectiveActionCreateSchema, initialData, {
        validateOnChange: false,
        validateOnBlur: true
    });

    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validate all fields
        const validation = await validateAll();
        if (!validation.success) {
            toast.error("Please fix the validation errors before submitting");
            return;
        }

        setIsSubmitting(true);
        try {
            await CorrectiveAction.create(validation.data);
            toast.success("Corrective action created successfully!");
            onSuccess();
        } catch (error) {
            console.error("Error creating corrective action:", error);
            toast.error("Failed to create corrective action");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-3xl max-h-[90vh] overflow-y-auto">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <AlertTriangle className="w-6 h-6 text-orange-600" />
                            <CardTitle>New Corrective Action</CardTitle>
                        </div>
                        <Button variant="ghost" size="sm" onClick={onClose}>
                            <X className="w-4 h-4" />
                        </Button>
                    </div>
                    <CardDescription>
                        Create a corrective action to address non-conformities and drive continuous improvement
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="title">Action Title *</Label>
                            <Input
                                id="title"
                                value={formData.title}
                                onChange={(e) => updateField('title', e.target.value)}
                                onBlur={() => handleBlur('title')}
                                placeholder="Brief description of the corrective action"
                                className={hasFieldError('title') ? 'border-red-500' : ''}
                                required
                            />
                            {hasFieldError('title') && (
                                <p className="text-sm text-red-600">{getFieldError('title')}</p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="non-conformity">Non-Conformity Description *</Label>
                            <Textarea
                                id="non-conformity"
                                value={formData.non_conformity}
                                onChange={(e) => updateField('non_conformity', e.target.value)}
                                onBlur={() => handleBlur('non_conformity')}
                                placeholder="Describe the non-conformity or issue that was identified"
                                className={`h-24 ${hasFieldError('non_conformity') ? 'border-red-500' : ''}`}
                                required
                            />
                            {hasFieldError('non_conformity') && (
                                <p className="text-sm text-red-600">{getFieldError('non_conformity')}</p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="root-cause">Root Cause Analysis</Label>
                            <Textarea
                                id="root-cause"
                                value={formData.root_cause_analysis}
                                onChange={(e) => updateField('root_cause_analysis', e.target.value)}
                                onBlur={() => handleBlur('root_cause_analysis')}
                                placeholder="Analysis of the root cause(s) that led to this non-conformity"
                                className={`h-24 ${hasFieldError('root_cause_analysis') ? 'border-red-500' : ''}`}
                            />
                            {hasFieldError('root_cause_analysis') && (
                                <p className="text-sm text-red-600">{getFieldError('root_cause_analysis')}</p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="action-plan">Corrective Action Plan *</Label>
                            <Textarea
                                id="action-plan"
                                value={formData.action_plan}
                                onChange={(e) => updateField('action_plan', e.target.value)}
                                onBlur={() => handleBlur('action_plan')}
                                placeholder="Detailed plan to address the non-conformity and prevent recurrence"
                                className={`h-32 ${hasFieldError('action_plan') ? 'border-red-500' : ''}`}
                                required
                            />
                            {hasFieldError('action_plan') && (
                                <p className="text-sm text-red-600">{getFieldError('action_plan')}</p>
                            )}
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="assigned-to">Assigned To *</Label>
                                <Input
                                    id="assigned-to"
                                    value={formData.assigned_to}
                                    onChange={(e) => updateField('assigned_to', e.target.value)}
                                    onBlur={() => handleBlur('assigned_to')}
                                    placeholder="Person responsible"
                                    className={hasFieldError('assigned_to') ? 'border-red-500' : ''}
                                    required
                                />
                                {hasFieldError('assigned_to') && (
                                    <p className="text-sm text-red-600">{getFieldError('assigned_to')}</p>
                                )}
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="due-date">Due Date *</Label>
                                <Input
                                    id="due-date"
                                    type="date"
                                    value={formData.due_date}
                                    onChange={(e) => updateField('due_date', e.target.value)}
                                    onBlur={() => handleBlur('due_date')}
                                    className={hasFieldError('due_date') ? 'border-red-500' : ''}
                                    required
                                />
                                {hasFieldError('due_date') && (
                                    <p className="text-sm text-red-600">{getFieldError('due_date')}</p>
                                )}
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="priority">Priority</Label>
                                <Select
                                    value={formData.priority}
                                    onValueChange={(value) => updateField('priority', value)}
                                >
                                    <SelectTrigger className={hasFieldError('priority') ? 'border-red-500' : ''}>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="Low">Low</SelectItem>
                                        <SelectItem value="Medium">Medium</SelectItem>
                                        <SelectItem value="High">High</SelectItem>
                                        <SelectItem value="Critical">Critical</SelectItem>
                                    </SelectContent>
                                </Select>
                                {hasFieldError('priority') && (
                                    <p className="text-sm text-red-600">{getFieldError('priority')}</p>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="verification">Verification Method</Label>
                                <Input
                                    id="verification"
                                    value={formData.verification_method}
                                    onChange={(e) => updateField('verification_method', e.target.value)}
                                    onBlur={() => handleBlur('verification_method')}
                                    placeholder="How completion will be verified"
                                    className={hasFieldError('verification_method') ? 'border-red-500' : ''}
                                />
                                {hasFieldError('verification_method') && (
                                    <p className="text-sm text-red-600">{getFieldError('verification_method')}</p>
                                )}
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="iso-clause">ISO 9001 Clause</Label>
                                <Input
                                    id="iso-clause"
                                    value={formData.iso_clause}
                                    onChange={(e) => updateField('iso_clause', e.target.value)}
                                    onBlur={() => handleBlur('iso_clause')}
                                    placeholder="e.g., 8.7"
                                    className={hasFieldError('iso_clause') ? 'border-red-500' : ''}
                                />
                                {hasFieldError('iso_clause') && (
                                    <p className="text-sm text-red-600">{getFieldError('iso_clause')}</p>
                                )}
                            </div>
                        </div>

                        {/* Display general validation errors */}
                        {Object.keys(errors).length > 0 && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                <div className="flex items-center gap-2 text-red-800 mb-2">
                                    <AlertTriangle className="w-4 h-4" />
                                    <span className="font-medium">Please fix the following errors:</span>
                                </div>
                                <ul className="text-sm text-red-700 space-y-1">
                                    {Object.entries(errors).map(([field, error]) => (
                                        <li key={field}>• {error}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="flex justify-end gap-3 pt-4 border-t">
                            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                disabled={isSubmitting || isValidating || !isValid}
                                className={!isValid ? 'opacity-50 cursor-not-allowed' : ''}
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Creating...
                                    </>
                                ) : isValidating ? (
                                    <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Validating...
                                    </>
                                ) : (
                                    <>
                                        <Plus className="w-4 h-4 mr-2" />
                                        Create Action
                                    </>
                                )}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}

// Wrap with ErrorBoundary for production safety
export default function CorrectiveActionFormWithErrorBoundary(props) {
    return (
        <ErrorBoundary>
            <CorrectiveActionForm {...props} />
        </ErrorBoundary>
    );
}
