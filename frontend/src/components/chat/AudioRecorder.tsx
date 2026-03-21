import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Brain } from 'lucide-react';

interface AudioRecorderProps {
    onRecordingComplete: (blob: Blob) => void;
    disabled?: boolean;
}

export function AudioRecorder({ onRecordingComplete, disabled }: AudioRecorderProps) {
    const [isRecording, setIsRecording] = useState(false);
    const [duration, setDuration] = useState(0);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const isRecordingRef = useRef(isRecording);

    useEffect(() => {
        isRecordingRef.current = isRecording;
    }, [isRecording]);

    useEffect(() => {
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, []);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
                onRecordingComplete(blob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
            setDuration(0);
            timerRef.current = setInterval(() => {
                setDuration(prev => {
                    const next = prev + 1;
                    if (next >= 900) { // 15 minutes max
                        stopRecording();
                    }
                    return next;
                });
            }, 1000);
        } catch (err) {
            console.error('Error accessing microphone:', err);
            alert('Could not access microphone. Please check permissions.');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecordingRef.current) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex items-center">
            {isRecording ? (
                <div className="flex items-center gap-2 bg-indigo-50 dark:bg-indigo-900/20 px-3 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-800 animate-pulse mr-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                    <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400 tabular-nums w-[3ch]">
                        {formatTime(duration)}
                    </span>
                    <button
                        onClick={stopRecording}
                        className="ml-1 p-1 bg-indigo-100 dark:bg-indigo-800 rounded-full hover:bg-indigo-200 dark:hover:bg-indigo-700 transition-colors"
                        title="Stop Recording"
                    >
                        <Square size={10} className="text-indigo-600 dark:text-indigo-300 fill-current" />
                    </button>
                </div>
            ) : (
                <button
                    onClick={startRecording}
                    disabled={disabled}
                    className={`p-1.5 rounded-lg transition-colors ${disabled ? 'opacity-50 cursor-not-allowed text-slate-400' : 'text-slate-400 hover:text-indigo-500 hover:bg-slate-100 dark:hover:bg-slate-700'
                        }`}
                    title="Brain Dump (Record Audio)"
                >
                    <Brain size={18} />
                </button>
            )}
        </div>
    );
}
