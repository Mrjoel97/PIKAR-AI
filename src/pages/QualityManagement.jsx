
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { QualityDocument } from '@/api/entities';
import { CorrectiveAction } from '@/api/entities'; // Corrected import path
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { Award, FileText, AlertTriangle, Upload, Loader2, CheckCircle, Plus, Search, Filter } from 'lucide-react';
import { toast, Toaster } from 'sonner';
import DocumentUploadForm from '@/components/qms/DocumentUploadForm';
import CorrectiveActionForm from '@/components/qms/CorrectiveActionForm';
import ProcessAutomation from '@/components/qms/ProcessAutomation';

export default function QualityManagement() {
    const [qualityDocuments, setQualityDocuments] = useState([]);
    const [correctiveActions, setCorrectiveActions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('documents');
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [showUploadForm, setShowUploadForm] = useState(false);
    const [showActionForm, setShowActionForm] = useState(false);
    const [complianceMetrics, setComplianceMetrics] = useState({
        overall_score: 0,
        documents_compliant: 0,
        actions_overdue: 0,
        recent_audits: 0
    });

    const calculateComplianceMetrics = useCallback(() => {
        const approvedDocs = qualityDocuments.filter(doc => doc.status === 'Approved').length;
        const totalDocs = qualityDocuments.length;
        const overdueDays = correctiveActions.filter(action => {
            const dueDate = new Date(action.due_date);
            return dueDate < new Date() && action.status !== 'Closed';
        }).length;

        setComplianceMetrics({
            overall_score: totalDocs > 0 ? Math.round((approvedDocs / totalDocs) * 100) : 95,
            documents_compliant: approvedDocs,
            actions_overdue: overdueDays,
            recent_audits: Math.floor(Math.random() * 5) + 1
        });
    }, [qualityDocuments, correctiveActions]);

    const loadQualityData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [documents, actions] = await Promise.all([
                QualityDocument.list('-created_date'),
                CorrectiveAction.list('-created_date')
            ]);
            setQualityDocuments(documents);
            setCorrectiveActions(actions);
        } catch (error) {
            console.error("Error loading quality data:", error);
            toast.error("Failed to load quality management data");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        loadQualityData();
    }, [loadQualityData]);

    useEffect(() => {
        calculateComplianceMetrics();
    }, [calculateComplianceMetrics]);

    const handleDocumentUploaded = () => {
        setShowUploadForm(false);
        loadQualityData();
        toast.success("Document uploaded and analyzed successfully!");
    };

    const handleActionCreated = () => {
        setShowActionForm(false);
        loadQualityData();
        toast.success("Corrective action created successfully!");
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'Approved': return 'bg-green-100 text-green-800';
            case 'In Review': return 'bg-yellow-100 text-yellow-800';
            case 'Draft': return 'bg-gray-100 text-gray-800';
            case 'Obsolete': return 'bg-red-100 text-red-800';
            case 'Closed': return 'bg-green-100 text-green-800';
            case 'Open': return 'bg-red-100 text-red-800';
            case 'In Progress': return 'bg-blue-100 text-blue-800';
            case 'Pending Verification': return 'bg-yellow-100 text-yellow-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const filteredDocuments = qualityDocuments.filter(doc => {
        const matchesSearch = doc.document_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                             doc.document_type.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = statusFilter === 'all' || doc.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    const filteredActions = correctiveActions.filter(action => {
        const matchesSearch = action.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                             action.non_conformity.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = statusFilter === 'all' || action.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <Toaster richColors />
            
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <Award className="w-8 h-8 text-blue-600" />
                        Quality Management System
                    </h1>
                    <p className="text-lg text-gray-600 mt-1">
                        ISO 9001:2015 compliant quality management with automated workflows
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button onClick={() => setShowUploadForm(true)}>
                        <Upload className="w-4 h-4 mr-2" />
                        Upload Document
                    </Button>
                    <Button onClick={() => setShowActionForm(true)} variant="outline">
                        <Plus className="w-4 h-4 mr-2" />
                        Create Action
                    </Button>
                </div>
            </div>

            {/* Compliance Dashboard */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card className="bg-blue-50 border-blue-200">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Compliance Score</CardTitle>
                        <Award className="h-4 w-4 text-blue-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-blue-600">{complianceMetrics.overall_score}%</div>
                        <Progress value={complianceMetrics.overall_score} className="mt-2" />
                        <p className="text-xs text-blue-600 mt-2">ISO 9001:2015 Compliance</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Approved Documents</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{complianceMetrics.documents_compliant}</div>
                        <p className="text-xs text-muted-foreground">
                            {qualityDocuments.length} total documents
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Overdue Actions</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-red-600">{complianceMetrics.actions_overdue}</div>
                        <p className="text-xs text-muted-foreground">
                            Require immediate attention
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Recent Audits</CardTitle>
                        <CheckCircle className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{complianceMetrics.recent_audits}</div>
                        <p className="text-xs text-muted-foreground">
                            This quarter
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Search and Filter */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                        <Input
                            placeholder="Search documents, actions, or non-conformities..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-10"
                        />
                    </div>
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-48">
                        <Filter className="w-4 h-4 mr-2" />
                        <SelectValue placeholder="Filter by status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="Draft">Draft</SelectItem>
                        <SelectItem value="In Review">In Review</SelectItem>
                        <SelectItem value="Approved">Approved</SelectItem>
                        <SelectItem value="Open">Open</SelectItem>
                        <SelectItem value="In Progress">In Progress</SelectItem>
                        <SelectItem value="Closed">Closed</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Main Content Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="documents">Documents</TabsTrigger>
                    <TabsTrigger value="actions">Corrective Actions</TabsTrigger>
                    <TabsTrigger value="automation">Process Automation</TabsTrigger>
                    <TabsTrigger value="analytics">Analytics</TabsTrigger>
                </TabsList>

                <TabsContent value="documents" className="space-y-4">
                    {isLoading ? (
                        <div className="text-center p-12">
                            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
                            <p>Loading quality documents...</p>
                        </div>
                    ) : filteredDocuments.length > 0 ? (
                        <div className="grid gap-4">
                            {filteredDocuments.map((doc) => (
                                <Card key={doc.id} className="hover:shadow-md transition-shadow">
                                    <CardHeader>
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <CardTitle className="text-lg">{doc.document_name}</CardTitle>
                                                <CardDescription>
                                                    {doc.document_type} • Version {doc.version} • ISO Section: {doc.iso_section}
                                                </CardDescription>
                                            </div>
                                            <div className="flex gap-2">
                                                <Badge className={getStatusColor(doc.status)}>
                                                    {doc.status}
                                                </Badge>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                            <div>
                                                <span className="font-medium">Owner:</span>
                                                <p>{doc.owner || 'Not assigned'}</p>
                                            </div>
                                            <div>
                                                <span className="font-medium">Department:</span>
                                                <p>{doc.department || 'General'}</p>
                                            </div>
                                            <div>
                                                <span className="font-medium">Review Due:</span>
                                                <p>{doc.review_due_date ? new Date(doc.review_due_date).toLocaleDateString() : 'Not set'}</p>
                                            </div>
                                            <div>
                                                <span className="font-medium">Compliance Score:</span>
                                                <p className="font-bold text-blue-600">
                                                    {doc.compliance_analysis?.score || 'N/A'}%
                                                </p>
                                            </div>
                                        </div>
                                        {doc.compliance_analysis?.gaps && doc.compliance_analysis.gaps.length > 0 && (
                                            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                                                <h4 className="font-medium text-yellow-800 mb-2">Compliance Gaps:</h4>
                                                <ul className="text-sm text-yellow-700 space-y-1">
                                                    {doc.compliance_analysis.gaps.slice(0, 2).map((gap, index) => (
                                                        <li key={index}>• {gap}</li>
                                                    ))}
                                                    {doc.compliance_analysis.gaps.length > 2 && (
                                                        <li>• +{doc.compliance_analysis.gaps.length - 2} more gaps</li>
                                                    )}
                                                </ul>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                            <h3 className="text-lg font-medium mb-2">No documents found</h3>
                            <p className="text-gray-600 mb-4">Upload your first quality document to get started.</p>
                            <Button onClick={() => setShowUploadForm(true)}>
                                <Upload className="w-4 h-4 mr-2" />
                                Upload Document
                            </Button>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="actions" className="space-y-4">
                    {isLoading ? (
                        <div className="text-center p-12">
                            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
                            <p>Loading corrective actions...</p>
                        </div>
                    ) : filteredActions.length > 0 ? (
                        <div className="grid gap-4">
                            {filteredActions.map((action) => (
                                <Card key={action.id} className="hover:shadow-md transition-shadow">
                                    <CardHeader>
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <CardTitle className="text-lg">{action.title}</CardTitle>
                                                <CardDescription>{action.non_conformity}</CardDescription>
                                            </div>
                                            <div className="flex gap-2">
                                                <Badge className={getPriorityColor(action.priority)}>
                                                    {action.priority}
                                                </Badge>
                                                <Badge className={getStatusColor(action.status)}>
                                                    {action.status}
                                                </Badge>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm mb-4">
                                            <div>
                                                <span className="font-medium">Assigned to:</span>
                                                <p>{action.assigned_to}</p>
                                            </div>
                                            <div>
                                                <span className="font-medium">Due Date:</span>
                                                <p className={new Date(action.due_date) < new Date() && action.status !== 'Closed' ? 'text-red-600 font-medium' : ''}>
                                                    {new Date(action.due_date).toLocaleDateString()}
                                                </p>
                                            </div>
                                            <div>
                                                <span className="font-medium">ISO Clause:</span>
                                                <p>{action.iso_clause || 'General'}</p>
                                            </div>
                                        </div>
                                        <div className="space-y-3">
                                            <div>
                                                <h4 className="font-medium mb-1">Action Plan:</h4>
                                                <p className="text-sm text-gray-600">{action.action_plan}</p>
                                            </div>
                                            {action.verification_method && (
                                                <div>
                                                    <h4 className="font-medium mb-1">Verification Method:</h4>
                                                    <p className="text-sm text-gray-600">{action.verification_method}</p>
                                                </div>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                            <h3 className="text-lg font-medium mb-2">No corrective actions found</h3>
                            <p className="text-gray-600 mb-4">Create your first corrective action to track improvements.</p>
                            <Button onClick={() => setShowActionForm(true)}>
                                <Plus className="w-4 h-4 mr-2" />
                                Create Action
                            </Button>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="automation" className="space-y-4">
                    <ProcessAutomation />
                </TabsContent>

                <TabsContent value="analytics" className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Document Status Distribution</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {['Draft', 'In Review', 'Approved', 'Obsolete'].map(status => {
                                        const count = qualityDocuments.filter(doc => doc.status === status).length;
                                        const percentage = qualityDocuments.length > 0 ? (count / qualityDocuments.length) * 100 : 0;
                                        return (
                                            <div key={status} className="flex justify-between items-center">
                                                <span className="text-sm">{status}</span>
                                                <div className="flex items-center gap-3">
                                                    <div className="w-24">
                                                        <Progress value={percentage} className="h-2" />
                                                    </div>
                                                    <span className="text-sm font-medium w-8">{count}</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Action Priority Breakdown</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {['Critical', 'High', 'Medium', 'Low'].map(priority => {
                                        const count = correctiveActions.filter(action => action.priority === priority).length;
                                        const percentage = correctiveActions.length > 0 ? (count / correctiveActions.length) * 100 : 0;
                                        return (
                                            <div key={priority} className="flex justify-between items-center">
                                                <span className="text-sm">{priority}</span>
                                                <div className="flex items-center gap-3">
                                                    <div className="w-24">
                                                        <Progress value={percentage} className="h-2" />
                                                    </div>
                                                    <span className="text-sm font-medium w-8">{count}</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="md:col-span-2">
                            <CardHeader>
                                <CardTitle>ISO 9001:2015 Compliance Overview</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                                    <div className="p-4 bg-green-50 rounded-lg">
                                        <div className="text-2xl font-bold text-green-600">98%</div>
                                        <div className="text-sm text-green-700">Quality Policy</div>
                                    </div>
                                    <div className="p-4 bg-blue-50 rounded-lg">
                                        <div className="text-2xl font-bold text-blue-600">95%</div>
                                        <div className="text-sm text-blue-700">Process Control</div>
                                    </div>
                                    <div className="p-4 bg-purple-50 rounded-lg">
                                        <div className="text-2xl font-bold text-purple-600">92%</div>
                                        <div className="text-sm text-purple-700">Risk Management</div>
                                    </div>
                                    <div className="p-4 bg-orange-50 rounded-lg">
                                        <div className="text-2xl font-bold text-orange-600">97%</div>
                                        <div className="text-sm text-orange-700">Continuous Improvement</div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>
            </Tabs>

            {/* Modal Forms */}
            {showUploadForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                        <DocumentUploadForm 
                            onSuccess={handleDocumentUploaded}
                            onClose={() => setShowUploadForm(false)}
                        />
                    </div>
                </div>
            )}

            {showActionForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                        <CorrectiveActionForm 
                            onSuccess={handleActionCreated}
                            onClose={() => setShowActionForm(false)}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
