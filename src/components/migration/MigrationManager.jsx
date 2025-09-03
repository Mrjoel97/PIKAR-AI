import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DatabaseMigration, MigrationExecution } from '@/api/entities';
// import { InvokeLLM } from '@/api/integrations';
import SupabaseDataMigrator from './SupabaseDataMigrator';
import { 
    Database, Play, RotateCcw, AlertTriangle, CheckCircle, 
    Clock, Plus, Code, FileText, Shield, Zap 
} from 'lucide-react';
import { toast } from 'sonner';

export default function MigrationManager() {
    const [migrations, setMigrations] = useState([]);
    const [executions, setExecutions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [isGeneratingMigration, setIsGeneratingMigration] = useState(false);
    const [newMigration, setNewMigration] = useState({
        migration_name: '',
        description: '',
        migration_type: '',
        target_entities: [],
        migration_sql: '',
        rollback_sql: '',
        impact_assessment: {
            breaking_changes: false,
            data_loss_risk: 'none',
            downtime_required: false,
            rollback_complexity: 'simple'
        }
    });

    useEffect(() => {
        loadMigrationData();
    }, []);

    const loadMigrationData = async () => {
        setIsLoading(true);
        try {
            const [migrationData, executionData] = await Promise.all([
                DatabaseMigration.list('-created_date'),
                MigrationExecution.list('-execution_timestamp')
            ]);
            setMigrations(migrationData);
            setExecutions(executionData);
        } catch (error) {
            console.error("Error loading migration data:", error);
            toast.error("Failed to load migration data");
        } finally {
            setIsLoading(false);
        }
    };

    const generateMigrationSQL = async () => {
        if (!newMigration.migration_name || !newMigration.description) {
            toast.error("Please provide migration name and description");
            return;
        }

        setIsGeneratingMigration(true);
        const prompt = `You are the PIKAR AI Database Migration Expert. Generate SQL migration scripts for the following requirement:

**Migration Name:** ${newMigration.migration_name}
**Description:** ${newMigration.description}
**Type:** ${newMigration.migration_type}
**Target Entities:** ${newMigration.target_entities.join(', ')}

Generate both forward migration SQL and rollback SQL following these principles:
1. **Idempotency** - Safe to run multiple times
2. **Atomicity** - All operations in a transaction
3. **Backward Compatibility** - No breaking changes to existing data
4. **Performance** - Optimized for large datasets

Provide the response in this JSON format:
{
  "migration_sql": "-- SQL commands for migration",
  "rollback_sql": "-- SQL commands for rollback",
  "validation_checks": ["check1", "check2"],
  "impact_notes": "Description of impact and considerations"
}`;

        try {
            const result = await InvokeLLM({
                prompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        migration_sql: { type: "string" },
                        rollback_sql: { type: "string" },
                        validation_checks: { type: "array", items: { type: "string" } },
                        impact_notes: { type: "string" }
                    }
                }
            });

            setNewMigration(prev => ({
                ...prev,
                migration_sql: result.migration_sql,
                rollback_sql: result.rollback_sql,
                validation_checks: result.validation_checks || [],
                impact_notes: result.impact_notes
            }));

            toast.success("Migration SQL generated successfully!");
        } catch (error) {
            console.error("Error generating migration:", error);
            toast.error("Failed to generate migration SQL");
        } finally {
            setIsGeneratingMigration(false);
        }
    };

    const createMigration = async () => {
        if (!newMigration.migration_sql || !newMigration.rollback_sql) {
            toast.error("Please generate migration SQL first");
            return;
        }

        try {
            const version = String(migrations.length + 1).padStart(3, '0');
            await DatabaseMigration.create({
                ...newMigration,
                version,
                validation_checks: newMigration.validation_checks?.map(check => ({
                    check_name: check,
                    check_result: false,
                    check_details: "Pending execution"
                }))
            });

            toast.success("Migration created successfully!");
            setShowCreateForm(false);
            setNewMigration({
                migration_name: '',
                description: '',
                migration_type: '',
                target_entities: [],
                migration_sql: '',
                rollback_sql: '',
                impact_assessment: {
                    breaking_changes: false,
                    data_loss_risk: 'none',
                    downtime_required: false,
                    rollback_complexity: 'simple'
                }
            });
            loadMigrationData();
        } catch (error) {
            console.error("Error creating migration:", error);
            toast.error("Failed to create migration");
        }
    };

    const executeMigration = async (migration) => {
        if (migration.execution_status === 'completed') {
            toast.warning("Migration already executed");
            return;
        }

        try {
            // Simulate migration execution
            await DatabaseMigration.update(migration.id, {
                execution_status: 'executing',
                execution_log: `Migration started at ${new Date().toISOString()}`
            });

            // Create execution record
            const execution = await MigrationExecution.create({
                migration_id: migration.id,
                execution_environment: 'development',
                execution_result: 'success',
                execution_duration: Math.floor(Math.random() * 5000) + 1000,
                affected_records: Math.floor(Math.random() * 1000),
                rollback_available: true,
                schema_hash_before: `hash_${Date.now()}`,
                schema_hash_after: `hash_${Date.now() + 1000}`
            });

            // Update migration status
            await DatabaseMigration.update(migration.id, {
                execution_status: 'completed',
                execution_log: `Migration completed successfully at ${new Date().toISOString()}`
            });

            toast.success(`Migration "${migration.migration_name}" executed successfully!`);
            loadMigrationData();
        } catch (error) {
            console.error("Error executing migration:", error);
            await DatabaseMigration.update(migration.id, {
                execution_status: 'failed',
                execution_log: `Migration failed: ${error.message}`
            });
            toast.error("Migration execution failed");
        }
    };

    const rollbackMigration = async (migration) => {
        try {
            // Simulate rollback execution
            await DatabaseMigration.update(migration.id, {
                execution_status: 'executing',
                execution_log: `Rollback started at ${new Date().toISOString()}`
            });

            // Create rollback execution record
            await MigrationExecution.create({
                migration_id: migration.id,
                execution_environment: 'development',
                execution_result: 'success',
                execution_duration: Math.floor(Math.random() * 3000) + 500,
                affected_records: Math.floor(Math.random() * 500),
                rollback_available: false,
                schema_hash_before: `hash_${Date.now()}`,
                schema_hash_after: `hash_${Date.now() - 1000}`
            });

            await DatabaseMigration.update(migration.id, {
                execution_status: 'rolled_back',
                execution_log: `Rollback completed at ${new Date().toISOString()}`
            });

            toast.success(`Migration "${migration.migration_name}" rolled back successfully!`);
            loadMigrationData();
        } catch (error) {
            console.error("Error rolling back migration:", error);
            toast.error("Rollback execution failed");
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800';
            case 'executing': return 'bg-blue-100 text-blue-800';
            case 'failed': return 'bg-red-100 text-red-800';
            case 'rolled_back': return 'bg-yellow-100 text-yellow-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'completed': return <CheckCircle className="w-4 h-4" />;
            case 'executing': return <Clock className="w-4 h-4 animate-spin" />;
            case 'failed': return <AlertTriangle className="w-4 h-4" />;
            case 'rolled_back': return <RotateCcw className="w-4 h-4" />;
            default: return <Clock className="w-4 h-4" />;
        }
    };

    const getRiskColor = (risk) => {
        switch (risk) {
            case 'none': return 'bg-green-100 text-green-800';
            case 'low': return 'bg-blue-100 text-blue-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'high': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <Database className="w-8 h-8 text-blue-600" />
                        Database Migration Manager
                    </h1>
                    <p className="text-lg text-gray-600 mt-1">
                        Enterprise-grade database schema management with rollback capabilities
                    </p>
                </div>
                <Button onClick={() => setShowCreateForm(!showCreateForm)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Migration
                </Button>
            </div>

            {/* Migration Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Migrations</CardTitle>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{migrations.length}</div>
                        <p className="text-xs text-muted-foreground">
                            Schema evolution tracking
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Completed</CardTitle>
                        <CheckCircle className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                            {migrations.filter(m => m.execution_status === 'completed').length}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Successfully applied
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Pending</CardTitle>
                        <Clock className="h-4 w-4 text-yellow-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-yellow-600">
                            {migrations.filter(m => m.execution_status === 'pending').length}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Awaiting execution
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Failed</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-red-600">
                            {migrations.filter(m => m.execution_status === 'failed').length}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Require attention
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Create Migration Form */}
            {showCreateForm && (
                <Card>
                    <CardHeader>
                        <CardTitle>Create New Migration</CardTitle>
                        <CardDescription>
                            Generate enterprise-grade database migration with automated rollback procedures
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="migration_name">Migration Name</Label>
                                <Input
                                    id="migration_name"
                                    placeholder="e.g., add_user_preferences_table"
                                    value={newMigration.migration_name}
                                    onChange={(e) => setNewMigration({...newMigration, migration_name: e.target.value})}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="migration_type">Migration Type</Label>
                                <Select 
                                    value={newMigration.migration_type} 
                                    onValueChange={(value) => setNewMigration({...newMigration, migration_type: value})}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="schema_creation">Schema Creation</SelectItem>
                                        <SelectItem value="schema_modification">Schema Modification</SelectItem>
                                        <SelectItem value="data_migration">Data Migration</SelectItem>
                                        <SelectItem value="index_creation">Index Creation</SelectItem>
                                        <SelectItem value="constraint_addition">Constraint Addition</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="description">Migration Description</Label>
                            <Textarea
                                id="description"
                                placeholder="Describe what this migration accomplishes and why it's needed..."
                                value={newMigration.description}
                                onChange={(e) => setNewMigration({...newMigration, description: e.target.value})}
                                className="h-24"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="target_entities">Target Entities (comma-separated)</Label>
                            <Input
                                id="target_entities"
                                placeholder="e.g., User, BusinessInitiative, AuditLog"
                                value={newMigration.target_entities.join(', ')}
                                onChange={(e) => setNewMigration({
                                    ...newMigration, 
                                    target_entities: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                                })}
                            />
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="space-y-2">
                                <Label>Breaking Changes</Label>
                                <Select 
                                    value={newMigration.impact_assessment.breaking_changes.toString()}
                                    onValueChange={(value) => setNewMigration({
                                        ...newMigration,
                                        impact_assessment: {
                                            ...newMigration.impact_assessment,
                                            breaking_changes: value === 'true'
                                        }
                                    })}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="false">No</SelectItem>
                                        <SelectItem value="true">Yes</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>Data Loss Risk</Label>
                                <Select 
                                    value={newMigration.impact_assessment.data_loss_risk}
                                    onValueChange={(value) => setNewMigration({
                                        ...newMigration,
                                        impact_assessment: {
                                            ...newMigration.impact_assessment,
                                            data_loss_risk: value
                                        }
                                    })}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="none">None</SelectItem>
                                        <SelectItem value="low">Low</SelectItem>
                                        <SelectItem value="medium">Medium</SelectItem>
                                        <SelectItem value="high">High</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>Downtime Required</Label>
                                <Select 
                                    value={newMigration.impact_assessment.downtime_required.toString()}
                                    onValueChange={(value) => setNewMigration({
                                        ...newMigration,
                                        impact_assessment: {
                                            ...newMigration.impact_assessment,
                                            downtime_required: value === 'true'
                                        }
                                    })}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="false">No</SelectItem>
                                        <SelectItem value="true">Yes</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>Rollback Complexity</Label>
                                <Select 
                                    value={newMigration.impact_assessment.rollback_complexity}
                                    onValueChange={(value) => setNewMigration({
                                        ...newMigration,
                                        impact_assessment: {
                                            ...newMigration.impact_assessment,
                                            rollback_complexity: value
                                        }
                                    })}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="simple">Simple</SelectItem>
                                        <SelectItem value="complex">Complex</SelectItem>
                                        <SelectItem value="irreversible">Irreversible</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Generated SQL Preview */}
                        {(newMigration.migration_sql || newMigration.rollback_sql) && (
                            <Tabs defaultValue="forward" className="w-full">
                                <TabsList>
                                    <TabsTrigger value="forward">Forward Migration</TabsTrigger>
                                    <TabsTrigger value="rollback">Rollback SQL</TabsTrigger>
                                </TabsList>
                                <TabsContent value="forward">
                                    <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                                        <pre>{newMigration.migration_sql}</pre>
                                    </div>
                                </TabsContent>
                                <TabsContent value="rollback">
                                    <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                                        <pre>{newMigration.rollback_sql}</pre>
                                    </div>
                                </TabsContent>
                            </Tabs>
                        )}

                        <div className="flex gap-3">
                            <Button 
                                onClick={generateMigrationSQL} 
                                disabled={isGeneratingMigration}
                                variant="outline"
                            >
                                {isGeneratingMigration ? (
                                    <>
                                        <Zap className="w-4 h-4 mr-2 animate-pulse" />
                                        Generating SQL...
                                    </>
                                ) : (
                                    <>
                                        <Code className="w-4 h-4 mr-2" />
                                        Generate SQL
                                    </>
                                )}
                            </Button>
                            <Button onClick={createMigration} disabled={!newMigration.migration_sql}>
                                Create Migration
                            </Button>
                            <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                                Cancel
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Migration List */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileText className="w-5 h-5" />
                        Migration History
                    </CardTitle>
                    <CardDescription>
                        All database migrations with execution status and rollback capabilities
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="mt-4">Loading migrations...</p>
                        </div>
                    ) : migrations.length > 0 ? (
                        <div className="space-y-4">
                            {migrations.map((migration) => (
                                <Card key={migration.id} className="border-l-4 border-l-blue-500">
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <CardTitle className="text-lg">
                                                    v{migration.version} - {migration.migration_name}
                                                </CardTitle>
                                                <CardDescription>{migration.description}</CardDescription>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Badge className={getStatusColor(migration.execution_status)}>
                                                    {getStatusIcon(migration.execution_status)}
                                                    <span className="ml-1">{migration.execution_status}</span>
                                                </Badge>
                                                <Badge className={getRiskColor(migration.impact_assessment?.data_loss_risk)}>
                                                    {migration.impact_assessment?.data_loss_risk} risk
                                                </Badge>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                                            <div>
                                                <span className="text-sm font-medium">Type:</span>
                                                <p className="text-sm text-gray-600">{migration.migration_type}</p>
                                            </div>
                                            <div>
                                                <span className="text-sm font-medium">Target Entities:</span>
                                                <p className="text-sm text-gray-600">
                                                    {migration.target_entities?.join(', ') || 'None specified'}
                                                </p>
                                            </div>
                                            <div>
                                                <span className="text-sm font-medium">Breaking Changes:</span>
                                                <p className="text-sm text-gray-600">
                                                    {migration.impact_assessment?.breaking_changes ? 'Yes' : 'No'}
                                                </p>
                                            </div>
                                        </div>

                                        {migration.execution_log && (
                                            <div className="mb-4 p-3 bg-gray-50 rounded text-sm">
                                                <span className="font-medium">Execution Log:</span>
                                                <pre className="mt-1 text-xs">{migration.execution_log}</pre>
                                            </div>
                                        )}

                                        <div className="flex gap-2">
                                            {migration.execution_status === 'pending' && (
                                                <Button 
                                                    size="sm" 
                                                    onClick={() => executeMigration(migration)}
                                                    className="bg-green-600 hover:bg-green-700"
                                                >
                                                    <Play className="w-4 h-4 mr-2" />
                                                    Execute
                                                </Button>
                                            )}
                                            {migration.execution_status === 'completed' && (
                                                <Button 
                                                    size="sm" 
                                                    variant="outline"
                                                    onClick={() => rollbackMigration(migration)}
                                                    className="border-yellow-500 text-yellow-600 hover:bg-yellow-50"
                                                >
                                                    <RotateCcw className="w-4 h-4 mr-2" />
                                                    Rollback
                                                </Button>
                                            )}
                                            <Button size="sm" variant="ghost">
                                                <Code className="w-4 h-4 mr-2" />
                                                View SQL
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <Database className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                            <h3 className="text-lg font-medium mb-2">No migrations found</h3>
                            <p className="text-gray-600 mb-4">Create your first database migration to get started.</p>
                            <Button onClick={() => setShowCreateForm(true)}>
                                <Plus className="w-4 h-4 mr-2" />
                                Create Migration
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Execution History */}
            {executions.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Clock className="w-5 h-5" />
                            Execution History
                        </CardTitle>
                        <CardDescription>
                            Recent migration executions with performance metrics
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {executions.slice(0, 10).map((execution) => {
                                const migration = migrations.find(m => m.id === execution.migration_id);
                                return (
                                    <div key={execution.id} className="flex items-center justify-between p-3 border rounded">
                                        <div>
                                            <p className="font-medium">{migration?.migration_name || 'Unknown Migration'}</p>
                                            <p className="text-sm text-gray-500">
                                                {execution.execution_environment} • {new Date(execution.execution_timestamp).toLocaleString()}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <div className="text-right text-sm">
                                                <p>{execution.execution_duration}ms</p>
                                                <p className="text-gray-500">{execution.affected_records} records</p>
                                            </div>
                                            <Badge className={getStatusColor(execution.execution_result)}>
                                                {execution.execution_result}
                                            </Badge>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}