import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { QualityDocument } from '@/api/entities';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { Upload, X, Loader2, FileText, Award } from 'lucide-react';
import { toast } from 'sonner';

export default function DocumentUploadForm({ onClose, onSuccess }) {
    const [formData, setFormData] = useState({
        document_name: '',
        document_type: '',
        iso_section: '',
        owner: '',
        department: '',
        review_due_date: ''
    });
    const [file, setFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file || !formData.document_name || !formData.document_type) {
            toast.error("Please fill in required fields and select a file");
            return;
        }

        setIsUploading(true);
        try {
            const { file_url } = await UploadFile({ file });
            
            const aiAnalysisPrompt = `You are the PIKAR AI Compliance & Risk Agent analyzing a ${formData.document_type} document for ISO 9001:2015 compliance.

Document Details:
- Name: ${formData.document_name}
- Type: ${formData.document_type}
- ISO Section: ${formData.iso_section}
- Department: ${formData.department}

Please analyze this document and provide:
1. A compliance score (0-100)
2. A brief summary of compliance status
3. List of identified gaps or areas for improvement
4. Specific recommendations for compliance enhancement

Return your response as JSON with this structure:
{
  "score": <number>,
  "summary": "<brief compliance summary>",
  "gaps": ["<gap 1>", "<gap 2>"],
  "recommendations": ["<rec 1>", "<rec 2>"]
}`;

            const analysisResult = await InvokeLLM({
                prompt: aiAnalysisPrompt,
                file_urls: [file_url],
                response_json_schema: {
                    type: "object",
                    properties: {
                        score: { type: "number" },
                        summary: { type: "string" },
                        gaps: { type: "array", items: { type: "string" } },
                        recommendations: { type: "array", items: { type: "string" } }
                    }
                }
            });

            await QualityDocument.create({
                ...formData,
                file_url,
                compliance_analysis: analysisResult,
                status: 'Draft',
                version: 1
            });

            toast.success("Document uploaded and analyzed successfully!");
            onSuccess();
        } catch (error) {
            console.error("Error uploading document:", error);
            toast.error("Failed to upload document");
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Award className="w-6 h-6 text-blue-600" />
                            <CardTitle>Upload Quality Document</CardTitle>
                        </div>
                        <Button variant="ghost" size="sm" onClick={onClose}>
                            <X className="w-4 h-4" />
                        </Button>
                    </div>
                    <CardDescription>
                        Upload a document for AI-powered ISO 9001:2015 compliance analysis
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="doc-name">Document Name *</Label>
                                <Input
                                    id="doc-name"
                                    value={formData.document_name}
                                    onChange={(e) => setFormData({...formData, document_name: e.target.value})}
                                    placeholder="e.g., Quality Policy Manual"
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="doc-type">Document Type *</Label>
                                <Select value={formData.document_type} onValueChange={(value) => setFormData({...formData, document_type: value})}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="SOP">Standard Operating Procedure</SelectItem>
                                        <SelectItem value="Policy">Policy</SelectItem>
                                        <SelectItem value="Work Instruction">Work Instruction</SelectItem>
                                        <SelectItem value="Audit Report">Audit Report</SelectItem>
                                        <SelectItem value="Process Map">Process Map</SelectItem>
                                        <SelectItem value="Risk Assessment">Risk Assessment</SelectItem>
                                        <SelectItem value="Training Material">Training Material</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="iso-section">ISO 9001:2015 Section</Label>
                                <Input
                                    id="iso-section"
                                    value={formData.iso_section}
                                    onChange={(e) => setFormData({...formData, iso_section: e.target.value})}
                                    placeholder="e.g., 8.5.1"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="owner">Document Owner</Label>
                                <Input
                                    id="owner"
                                    value={formData.owner}
                                    onChange={(e) => setFormData({...formData, owner: e.target.value})}
                                    placeholder="e.g., Quality Manager"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="department">Department</Label>
                                <Input
                                    id="department"
                                    value={formData.department}
                                    onChange={(e) => setFormData({...formData, department: e.target.value})}
                                    placeholder="e.g., Quality Assurance"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="due-date">Review Due Date</Label>
                                <Input
                                    id="due-date"
                                    type="date"
                                    value={formData.review_due_date}
                                    onChange={(e) => setFormData({...formData, review_due_date: e.target.value})}
                                />
                            </div>
                        </div>
                        
                        <div className="space-y-2">
                            <Label>Document File *</Label>
                            <div className="border-2 border-dashed rounded-lg p-6 text-center">
                                <input
                                    type="file"
                                    onChange={(e) => setFile(e.target.files[0])}
                                    className="hidden"
                                    id="file-input"
                                    accept=".pdf,.doc,.docx,.txt"
                                />
                                <label htmlFor="file-input" className="cursor-pointer">
                                    <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                                    <p className="text-sm text-gray-600">
                                        {file ? file.name : "Click to upload or drag and drop"}
                                    </p>
                                    <p className="text-xs text-gray-400">PDF, DOC, DOCX, TXT files supported</p>
                                </label>
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 pt-4">
                            <Button type="button" variant="outline" onClick={onClose} disabled={isUploading}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={isUploading}>
                                {isUploading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <FileText className="w-4 h-4 mr-2" />
                                        Upload & Analyze
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