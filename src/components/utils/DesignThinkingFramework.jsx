import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';
import { Lightbulb, Users, Search, TestTube, Beaker, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';

const stages = [
    { id: 'empathize', name: 'Empathize', icon: Users, description: "Understand user needs" },
    { id: 'define', name: 'Define', icon: Search, description: "Frame the problem" },
    { id: 'ideate', name: 'Ideate', icon: Lightbulb, description: "Brainstorm solutions" },
    { id: 'prototype', name: 'Prototype', icon: Beaker, description: "Create a concept" },
    { id: 'test', name: 'Test', icon: TestTube, description: "Validate the concept" },
];

export default function DesignThinkingFramework({ initialProblem, onComplete }) {
    const [activeStep, setActiveStep] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [workshopState, setWorkshopState] = useState({
        initialProblem: initialProblem || '',
        empathize: { input: '', output: '' },
        define: { input: '', output: '' },
        ideate: { input: '', output: '' },
        prototype: { input: '', output: '' },
        test: { input: '', output: '' },
    });
    const [finalConcept, setFinalConcept] = useState(null);

    const handleInputChange = (stage, value) => {
        setWorkshopState(prev => ({
            ...prev,
            [stage]: { ...prev[stage], input: value }
        }));
    };

    const generateStageOutput = useCallback(async () => {
        const currentStage = stages[activeStep].id;
        const currentInput = workshopState[currentStage].input;
        
        if (!currentInput && currentStage !== 'ideate') {
            toast.error("Please provide input for this stage.");
            return;
        }

        setIsLoading(true);
        let prompt = `You are the PIKAR AI Strategic Innovation Agent, facilitating a Design Thinking workshop.

**WORKSHOP CONTEXT**
- **Initial Problem:** ${workshopState.initialProblem}
- **Current Stage:** ${stages[activeStep].name}
`;

        switch(currentStage) {
            case 'empathize':
                prompt += `**User Persona/Context:**\n${currentInput}\n\nGenerate a detailed Empathy Map (Says, Thinks, Does, Feels) for this user.`;
                break;
            case 'define':
                prompt += `**Empathy Findings:**\n${workshopState.empathize.output}\n\n**User Needs/Insights:**\n${currentInput}\n\nSynthesize these findings into 3-5 clearly defined, actionable problem statements using the "How Might We..." format.`;
                break;
            case 'ideate':
                 prompt += `**Problem Statement:**\n${workshopState.define.output}\n\nGenerate a diverse list of at least 10 innovative solutions. Use brainstorming techniques like SCAMPER, mind mapping, or reverse brainstorming. Group ideas by theme.`;
                break;
            case 'prototype':
                prompt += `**Selected Idea:**\n${currentInput}\n\nBased on the selected idea, describe a low-fidelity prototype concept. Detail its key features, user flow, and the core user experience it aims to deliver. This should be a textual description suitable for creating a basic wireframe.`;
                break;
            case 'test':
                prompt += `**Prototype Concept:**\n${workshopState.prototype.output}\n\n**Testing Goals:**\n${currentInput}\n\nCreate a concise user testing plan. Include a test script with key tasks for the user, and define success metrics for validating the concept.`;
                break;
        }

        try {
            const { text: output } = await generateText({ model: openai('gpt-4o-mini'), prompt, temperature: 0.5, maxTokens: 1000 });
            setWorkshopState(prev => ({
                ...prev,
                [currentStage]: { ...prev[currentStage], output }
            }));
            setActiveStep(prev => prev + 1);
        } catch (error) {
            console.error("Error in Design Thinking stage:", error);
            toast.error("An error occurred during AI generation.");
        } finally {
            setIsLoading(false);
        }
    }, [activeStep, workshopState]);

    const handleCompleteWorkshop = () => {
        const finalOutput = {
            problemStatement: workshopState.define.output,
            solutionConcept: workshopState.prototype.output,
            validationPlan: workshopState.test.output
        };
        setFinalConcept(finalOutput);
        if (onComplete) {
            onComplete(finalOutput);
        }
        toast.success("Design Thinking workshop completed successfully!");
    };
    
    const renderStageContent = () => {
        const currentStageId = stages[activeStep].id;
        const { input, output } = workshopState[currentStageId];
        const CurrentIcon = stages[activeStep].icon;

        return (
            <Card className="mt-4">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <CurrentIcon className="w-6 h-6" />
                        Stage {activeStep + 1}: {stages[activeStep].name}
                    </CardTitle>
                    <CardDescription>{stages[activeStep].description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {currentStageId !== 'ideate' && (
                         <Textarea
                            placeholder={`Input for ${stages[activeStep].name} stage...`}
                            value={input}
                            onChange={(e) => handleInputChange(currentStageId, e.target.value)}
                            className="h-24"
                        />
                    )}
                    <Button onClick={generateStageOutput} disabled={isLoading}>
                        {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : `Generate ${stages[activeStep].name} Insights`}
                    </Button>
                    {output && (
                        <div className="p-4 border rounded-md bg-gray-50 dark:bg-gray-800">
                             <h4 className="font-semibold mb-2">AI-Generated Output:</h4>
                             <ReactMarkdown className="prose dark:prose-invert max-w-none">{output}</ReactMarkdown>
                        </div>
                    )}
                </CardContent>
            </Card>
        );
    };

    const renderProgressStepper = () => {
        return (
            <div className="flex items-center justify-between mb-6">
                {stages.map((stage, index) => {
                    const Icon = stage.icon;
                    const isActive = index === activeStep;
                    const isCompleted = index < activeStep;
                    const isAvailable = index <= activeStep;

                    return (
                        <div key={stage.id} className="flex items-center">
                            <div
                                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 cursor-pointer transition-colors ${
                                    isCompleted 
                                        ? 'bg-green-500 border-green-500 text-white' 
                                        : isActive 
                                        ? 'bg-blue-500 border-blue-500 text-white' 
                                        : isAvailable
                                        ? 'border-gray-300 hover:border-blue-300'
                                        : 'border-gray-200 text-gray-400'
                                }`}
                                onClick={() => isAvailable && setActiveStep(index)}
                            >
                                {isCompleted ? (
                                    <CheckCircle className="w-5 h-5" />
                                ) : (
                                    <Icon className="w-5 h-5" />
                                )}
                            </div>
                            {index < stages.length - 1 && (
                                <div className={`w-12 h-0.5 mx-2 ${isCompleted ? 'bg-green-500' : 'bg-gray-200'}`} />
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <Card>
             <CardHeader>
                <CardTitle>Design Thinking Workshop</CardTitle>
                <CardDescription>Follow the 5 stages to innovate and solve complex problems.</CardDescription>
            </CardHeader>
            <CardContent>
                {renderProgressStepper()}
                
                {activeStep < stages.length && renderStageContent()}

                {activeStep === stages.length && (
                    <div className="text-center p-8">
                        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                        <h3 className="text-2xl font-bold">Workshop Complete!</h3>
                        <p className="text-gray-500 mb-6">You have successfully completed all stages of the Design Thinking process.</p>
                        <Button onClick={handleCompleteWorkshop}>Finalize & View Concept</Button>
                    </div>
                )}
                 {finalConcept && (
                    <Card className="mt-6">
                        <CardHeader><CardTitle>Final Innovation Concept</CardTitle></CardHeader>
                        <CardContent className="space-y-4">
                           <div>
                                <h4 className="font-semibold">Problem Statement</h4>
                                <ReactMarkdown className="prose dark:prose-invert max-w-none p-2 border rounded-md">{finalConcept.problemStatement || "N/A"}</ReactMarkdown>
                           </div>
                           <div>
                                <h4 className="font-semibold">Solution Concept</h4>
                                <ReactMarkdown className="prose dark:prose-invert max-w-none p-2 border rounded-md">{finalConcept.solutionConcept || "N/A"}</ReactMarkdown>
                           </div>
                           <div>
                                <h4 className="font-semibold">Validation Plan</h4>
                                <ReactMarkdown className="prose dark:prose-invert max-w-none p-2 border rounded-md">{finalConcept.validationPlan || "N/A"}</ReactMarkdown>
                           </div>
                        </CardContent>
                    </Card>
                )}
            </CardContent>
        </Card>
    );
}