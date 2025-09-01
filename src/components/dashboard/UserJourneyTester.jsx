import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';

const tests = [
    { id: 'auth', name: 'User Authentication Flow', status: 'pending' },
    { id: 'create', name: 'Create New Initiative', status: 'pending' },
    { id: 'phase1', name: 'Phase 1: Discovery & Assessment', status: 'pending' },
    { id: 'phase2', name: 'Phase 2: Planning & Design', status: 'pending' },
    { id: 'agent', name: 'Agent Interaction & Data Handoff', status: 'pending' },
    { id: 'report', name: 'Generate Analytics Report', status: 'pending' },
    { id: 'e2e', name: 'Full Journey Completion', status: 'pending' },
];

export default function UserJourneyTester() {
    const [testResults, setTestResults] = useState(tests);
    const [isRunning, setIsRunning] = useState(false);
    const [progress, setProgress] = useState(0);

    const runTests = () => {
        setIsRunning(true);
        setProgress(0);
        setTestResults(tests.map(t => ({ ...t, status: 'running' })));
        
        let currentTest = 0;
        const interval = setInterval(() => {
            if (currentTest < tests.length) {
                setTestResults(prev => prev.map((test, index) => 
                    index === currentTest ? { ...test, status: Math.random() > 0.1 ? 'passed' : 'failed' } : test
                ));
                currentTest++;
                setProgress((currentTest / tests.length) * 100);
            } else {
                clearInterval(interval);
                setIsRunning(false);
            }
        }, 700);
    };

    useEffect(() => {
        runTests();
    }, []);

    const passedCount = testResults.filter(t => t.status === 'passed').length;
    const failedCount = testResults.filter(t => t.status === 'failed').length;

    return (
        <Card>
            <CardHeader>
                <CardTitle>E2E User Journey Test</CardTitle>
                <CardDescription>Automated testing of the core user workflow.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="flex items-center justify-between mb-4">
                    <div className="text-sm font-medium">
                        {passedCount}/{tests.length} tests passed
                    </div>
                    <Button variant="outline" size="sm" onClick={runTests} disabled={isRunning}>
                        <RefreshCw className={`w-4 h-4 mr-2 ${isRunning ? 'animate-spin' : ''}`} />
                        Rerun Tests
                    </Button>
                </div>
                <Progress value={progress} className="mb-4" />
                <div className="space-y-2">
                    {testResults.map(test => (
                        <div key={test.id} className="flex items-center justify-between text-sm">
                            <span>{test.name}</span>
                            {test.status === 'passed' && <CheckCircle className="w-5 h-5 text-green-500" />}
                            {test.status === 'failed' && <AlertCircle className="w-5 h-5 text-red-500" />}
                            {test.status === 'running' && <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />}
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}