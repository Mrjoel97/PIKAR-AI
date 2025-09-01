import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle, AlertTriangle, XCircle, TestTube, Database, Shield } from 'lucide-react';
import { InvokeLLM } from '@/api/integrations';
import { toast } from 'sonner';

export default function MigrationValidator({ migration, onValidationComplete }) {
    const [validationResults, setValidationResults] = useState(null);
    const [isValidating, setIsValidating] = useState(false);

    const runValidation = async () => {
        setIsValidating(true);
        try {
            const validationPrompt = `You are the PIKAR AI Database Migration Validator. Analyze this migration for safety and compliance:

**Migration Name:** ${migration.migration_name}
**Type:** ${migration.migration_type}
**Description:** ${migration.description}

**Forward SQL:**
\`\`\`sql
${migration.migration_sql}
\`\`\`

**Rollback SQL:**
\`\`\`sql
${migration.rollback_sql}
\`\`\`

Perform comprehensive validation checks:

1. **Idempotency Check** - Can this migration run multiple times safely?
2. **Rollback Safety** - Is the rollback SQL correct and complete?
3. **Performance Impact** - Will this migration cause performance issues?
4. **Data Integrity** - Are there risks to existing data?
5. **Security Compliance** - Does this follow security best practices?
6. **Schema Consistency** - Will this maintain schema consistency?

Return validation results as JSON:
{
  "overall_score": <0-100>,
  "validation_checks": [
    {
      "check_name": "Idempotency Check",
      "status": "pass|warning|fail",
      "details": "Explanation of findings",
      "severity": "low|medium|high|critical"
    }
  ],
  "recommendations": ["rec1", "rec2"],
  "approval_status": "approved|requires_review|rejected"
}`;

            const result = await InvokeLLM({
                prompt: validationPrompt,
                response_json_schema: {
                    type: "object",
                    properties: {
                        overall_score: { type: "number" },
                        validation_checks: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    check_name: { type: "string" },
                                    status: { type: "string" },
                                    details: { type: "string" },
                                    severity: { type: "string" }
                                }
                            }
                        },
                        recommendations: { type: "array", items: { type: "string" } },
                        approval_status: { type: "string" }
                    }
                }
            });

            setValidationResults(result);
            if (onValidationComplete) {
                onValidationComplete(result);
            }
            toast.success("Migration validation completed!");
        } catch (error) {
            console.error("Validation error:", error);
            toast.error("Migration validation failed");
        } finally {
            setIsValidating(false);
        }
    };

    const getCheckStatusColor = (status) => {
        switch (status) {
            case 'pass': return 'bg-green-100 text-green-800';
            case 'warning': return 'bg-yellow-100 text-yellow-800';
            case 'fail': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getCheckStatusIcon = (status) => {
        switch (status) {
            case 'pass': return <CheckCircle className="w-4 h-4" />;
            case 'warning': return <AlertTriangle className="w-4 h-4" />;
            case 'fail': return <XCircle className="w-4 h-4" />;
            default: return <TestTube className="w-4 h-4" />;
        }
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'low': return 'text-green-600';
            case 'medium': return 'text-yellow-600';
            case 'high': return 'text-orange-600';
            case 'critical': return 'text-red-600';
            default: return 'text-gray-600';
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <TestTube className="w-5 h-5" />
                    Migration Validation
                </CardTitle>
                <CardDescription>
                    Automated safety and compliance validation for database migrations
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {!validationResults ? (
                    <div className="text-center py-8">
                        <TestTube className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                        <p className="text-gray-600 mb-4">Run validation to ensure migration safety and compliance</p>
                        <Button onClick={runValidation} disabled={isValidating}>
                            {isValidating ? (
                                <>
                                    <TestTube className="w-4 h-4 mr-2 animate-pulse" />
                                    Validating...
                                </>
                            ) : (
                                <>
                                    <Shield className="w-4 h-4 mr-2" />
                                    Run Validation
                                </>
                            )}
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* Overall Score */}
                        <div className="text-center p-6 bg-gray-50 rounded-lg">
                            <div className="text-3xl font-bold mb-2">{validationResults.overall_score}%</div>
                            <div className="text-sm text-gray-600 mb-3">Overall Validation Score</div>
                            <Progress value={validationResults.overall_score} className="mb-3" />
                            <Badge className={
                                validationResults.approval_status === 'approved' ? 'bg-green-100 text-green-800' :
                                validationResults.approval_status === 'requires_review' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                            }>
                                {validationResults.approval_status.replace(/_/g, ' ').toUpperCase()}
                            </Badge>
                        </div>

                        {/* Validation Checks */}
                        <div className="space-y-3">
                            <h4 className="font-medium">Validation Checks</h4>
                            {validationResults.validation_checks.map((check, index) => (
                                <div key={index} className="p-4 border rounded-lg">
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            {getCheckStatusIcon(check.status)}
                                            <span className="font-medium">{check.check_name}</span>
                                        </div>
                                        <div className="flex gap-2">
                                            <Badge className={getCheckStatusColor(check.status)}>
                                                {check.status}
                                            </Badge>
                                            <Badge variant="outline" className={getSeverityColor(check.severity)}>
                                                {check.severity}
                                            </Badge>
                                        </div>
                                    </div>
                                    <p className="text-sm text-gray-600">{check.details}</p>
                                </div>
                            ))}
                        </div>

                        {/* Recommendations */}
                        {validationResults.recommendations.length > 0 && (
                            <div className="space-y-3">
                                <h4 className="font-medium">Recommendations</h4>
                                <ul className="space-y-2">
                                    {validationResults.recommendations.map((rec, index) => (
                                        <li key={index} className="flex items-start gap-2 text-sm">
                                            <AlertTriangle className="w-4 h-4 mt-0.5 text-yellow-500" />
                                            {rec}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <Button onClick={runValidation} variant="outline" size="sm">
                            <TestTube className="w-4 h-4 mr-2" />
                            Re-run Validation
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}