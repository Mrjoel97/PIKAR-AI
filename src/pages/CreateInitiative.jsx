
import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { BusinessInitiative, InitiativeDeliverable } from '@/api/entities';
import { InvokeLLM, UploadFile } from '@/api/integrations';
import { useNavigate } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { toast, Toaster } from 'sonner';
import { Target, ArrowLeft, BrainCircuit, Loader2, Upload, Mic, MicOff, Play } from 'lucide-react';

export default function CreateInitiative() {
    const [initiativeName, setInitiativeName] = useState('');
    const [initiativeDescription, setInitiativeDescription] = useState('');
    const [category, setCategory] = useState('');
    const [priority, setPriority] = useState('Medium');
    const [contextFile, setContextFile] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const [audioBlob, setAudioBlob] = useState(null);
    const [audioUrl, setAudioUrl] = useState(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        return () => {
            if (audioUrl) {
                URL.revokeObjectURL(audioUrl);
            }
        };
    }, [audioUrl]);

    const handleGenerateDescription = async () => {
        if (!initiativeName) {
            toast.error("Please enter an initiative name first.");
            return;
        }
        setIsLoading(true);
        try {
            const prompt = `You are the PIKAR AI Strategic Planning Agent. Based on the initiative name "${initiativeName}", generate a comprehensive, enterprise-grade business initiative description. It should cover the scope, objectives, potential benefits, and key activities. Be detailed and structure it for a formal business document.`;
            const description = await InvokeLLM({ prompt });
            setInitiativeDescription(description);
            toast.success("AI-powered description generated!");
        } catch (error) {
            console.error("Failed to generate description:", error);
            toast.error("Failed to generate description.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setContextFile(file);
            toast.info(`File "${file.name}" selected.`);
        }
    };

    const handleStartRecording = async () => {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorderRef.current = new MediaRecorder(stream);
                audioChunksRef.current = [];

                mediaRecorderRef.current.ondataavailable = (event) => {
                    audioChunksRef.current.push(event.data);
                };

                mediaRecorderRef.current.onstop = () => {
                    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                    setAudioBlob(audioBlob);
                    const url = URL.createObjectURL(audioBlob);
                    setAudioUrl(url);
                    toast.success("Recording complete!");
                };

                mediaRecorderRef.current.start();
                setIsRecording(true);
                toast.info("Recording started...");
            } catch (err) {
                console.error("Error accessing microphone:", err);
                toast.error("Could not access microphone. Please check permissions.");
            }
        }
    };

    const handleStopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            // Stop all tracks on the stream to turn off the microphone light
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
            setIsRecording(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!initiativeName || !initiativeDescription || !category || !priority) {
            toast.error("Please fill out all required fields.");
            return;
        }
        setIsLoading(true);
        try {
            let contextFileUrl = '';
            if (contextFile) {
                toast.info("Uploading context file...");
                const { file_url } = await UploadFile({ file: contextFile });
                contextFileUrl = file_url;
                toast.success("File uploaded successfully.");
            }

            let braindumpAudioUrl = '';
            if (audioBlob) {
                toast.info("Uploading audio recording...");
                const audioFile = new File([audioBlob], `braindump-${Date.now()}.webm`, { type: 'audio/webm' });
                const { file_url } = await UploadFile({ file: audioFile });
                braindumpAudioUrl = file_url;
                toast.success("Audio recording uploaded successfully.");
            }

            const newInitiative = await BusinessInitiative.create({
                initiative_name: initiativeName,
                initiative_description: initiativeDescription,
                category,
                priority,
                current_phase: 'Discovery & Assessment',
                status: 'Not Started',
                stakeholders: [],
                context_file_url: contextFileUrl,
                braindump_audio_url: braindumpAudioUrl,
            });

            // Create initial deliverable for Phase 1
            await InitiativeDeliverable.create({
                initiative_id: newInitiative.id,
                phase: 'Discovery & Assessment',
                deliverable_name: 'Initiative Charter Document',
                deliverable_type: 'Initiative Charter',
                status: 'Pending'
            });

            toast.success("Business initiative created successfully!");
            navigate(createPageUrl(`InitiativeDetails?id=${newInitiative.id}`));

        } catch (error) {
            console.error("Failed to create initiative:", error);
            toast.error("Failed to create the initiative.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto">
            <Toaster richColors />
            <div className="flex items-center gap-4 mb-8">
                <Button variant="outline" size="icon" onClick={() => navigate(-1)}>
                    <ArrowLeft className="w-4 h-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold">Create New Business Initiative</h1>
                    <p className="text-gray-500">Start a new transformation journey for your organization.</p>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Initiative Details</CardTitle>
                        <CardDescription>
                            Define the core aspects of your new initiative. Use the AI Assistant to help craft a compelling description.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="name">Initiative Name *</Label>
                            <Input
                                id="name"
                                placeholder="e.g., 'Global Market Expansion Q4 2024'"
                                value={initiativeName}
                                onChange={(e) => setInitiativeName(e.target.value)}
                                required
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="description">Initiative Description *</Label>
                            <div className="relative">
                                <Textarea
                                    id="description"
                                    placeholder="Describe the goals, scope, and expected outcomes of this initiative."
                                    value={initiativeDescription}
                                    onChange={(e) => setInitiativeDescription(e.target.value)}
                                    className="h-40 pr-32"
                                    required
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="absolute top-2 right-2"
                                    onClick={handleGenerateDescription}
                                    disabled={isLoading}
                                >
                                    {isLoading && initiativeDescription === '' ? (
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    ) : (
                                        <BrainCircuit className="w-4 h-4 mr-2" />
                                    )}
                                    AI Assist
                                </Button>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <Label htmlFor="category">Category *</Label>
                                <Select value={category} onValueChange={setCategory} required>
                                    <SelectTrigger id="category">
                                        <SelectValue placeholder="Select a category" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="Growth">Growth</SelectItem>
                                        <SelectItem value="Optimization">Optimization</SelectItem>
                                        <SelectItem value="Innovation">Innovation</SelectItem>
                                        <SelectItem value="Compliance">Compliance</SelectItem>
                                        <SelectItem value="Transformation">Transformation</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="priority">Priority *</Label>
                                <Select value={priority} onValueChange={setPriority} required>
                                    <SelectTrigger id="priority">
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
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Provide Context</CardTitle>
                        <CardDescription>
                            Upload a supporting document or record an audio "brain dump" of your idea for richer context.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
                        <div className="space-y-2">
                            <Label htmlFor="file-upload">Upload Document</Label>
                            <div className="flex items-center justify-center w-full">
                                <label htmlFor="file-upload" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700">
                                    <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center px-2">
                                        <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                            {contextFile ? contextFile.name : "Upload PDF, DOCX, TXT..."}
                                        </p>
                                    </div>
                                    <Input id="file-upload" type="file" className="hidden" onChange={handleFileChange} />
                                </label>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Record Audio</Label>
                            <div className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg bg-gray-50 dark:bg-gray-800 p-4">
                                {!isRecording && !audioBlob && (
                                    <Button type="button" variant="outline" onClick={handleStartRecording}>
                                        <Mic className="w-4 h-4 mr-2" />
                                        Start Recording
                                    </Button>
                                )}
                                {isRecording && (
                                    <Button type="button" variant="destructive" onClick={handleStopRecording}>
                                        <MicOff className="w-4 h-4 mr-2 animate-pulse" />
                                        Stop Recording
                                    </Button>
                                )}
                                {audioUrl && !isRecording && (
                                    <div className="flex flex-col items-center gap-2">
                                        <audio src={audioUrl} controls className="w-full" />
                                        <Button type="button" size="sm" variant="ghost" onClick={() => { setAudioBlob(null); setAudioUrl(null); }}>
                                            Record again
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>
                
                <div className="flex justify-end pt-4">
                    <Button type="submit" size="lg" disabled={isLoading}>
                        {isLoading ? (
                            <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        ) : (
                            <Target className="w-5 h-5 mr-2" />
                        )}
                        Create Initiative & Start Journey
                    </Button>
                </div>
            </form>
        </div>
    );
}
