
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

export default function CorrectiveActionForm({ onClose, onSuccess }) {
    const [formData, setFormData] = useState({
        title: '',
        non_conformity: '',
        root_cause_analysis: '',
        action_plan: '',
        assigned_to: '',
        due_date: '',
        priority: 'Medium',
        verification_method: '',
        iso_clause: ''
    });
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!formData.title || !formData.non_conformity || !formData.action_plan || !formData.assigned_to || !formData.due_date) {
            toast.error("Please fill in all required fields");
            return;
        }

        setIsSubmitting(true);
        try {
            await CorrectiveAction.create(formData);
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
                                onChange={(e) => setFormData({...formData, title: e.target.value})}
                                placeholder="Brief description of the corrective action"
                                required
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="non-conformity">Non-Conformity Description *</Label>
                            <Textarea
                                id="non-conformity"
                                value={formData.non_conformity}
                                onChange={(e) => setFormData({...formData, non_conformity: e.target.value})}
                                placeholder="Describe the non-conformity or issue that was identified"
                                className="h-24"
                                required
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="root-cause">Root Cause Analysis</Label>
                            <Textarea
                                id="root-cause"
                                value={formData.root_cause_analysis}
                                onChange={(e) => setFormData({...formData, root_cause_analysis: e.target.value})}
                                placeholder="Analysis of the root cause(s) that led to this non-conformity"
                                className="h-24"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="action-plan">Corrective Action Plan *</Label>
                            <Textarea
                                id="action-plan"
                                value={formData.action_plan}
                                onChange={(e) => setFormData({...formData, action_plan: e.target.value})}
                                placeholder="Detailed plan to address the non-conformity and prevent recurrence"
                                className="h-32"
                                required
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="assigned-to">Assigned To *</Label>
                                <Input
                                    id="assigned-to"
                                    value={formData.assigned_to}
                                    onChange={(e) => setFormData({...formData, assigned_to: e.target.value})}
                                    placeholder="Person responsible"
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="due-date">Due Date *</Label>
                                <Input
                                    id="due-date"
                                    type="date"
                                    value={formData.due_date}
                                    onChange={(e) => setFormData({...formData, due_date: e.target.value})}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="priority">Priority</Label>
                                <Select value={formData.priority} onValueChange={(value) => setFormData({...formData, priority: value})}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="Low">Low</SelectItem>
                                        <SelectItem value="Medium">Medium</SelectItem>
                                        <SelectItem value="High">High</SelectItem>
                                        <SelectItem value="Critical">Critical</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="verification">Verification Method</Label>
                                <Input
                                    id="verification"
                                    value={formData.verification_method}
                                    onChange={(e) => setFormData({...formData, verification_method: e.target.value})}
                                    placeholder="How completion will be verified"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="iso-clause">ISO 9001 Clause</Label>
                                <Input
                                    id="iso-clause"
                                    value={formData.iso_clause}
                                    onChange={(e) => setFormData({...formData, iso_clause: e.target.value})}
                                    placeholder="e.g., 8.7"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 pt-4 border-t">
                            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={isSubmitting}>
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Creating...
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
