import { useState, useCallback, useEffect, useRef } from 'react';

interface UseTextToSpeechOptions {
    onStart?: () => void;
    onEnd?: () => void;
    onError?: (error: any) => void;
}

export function useTextToSpeech(options: UseTextToSpeechOptions = {}) {
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isSupported, setIsSupported] = useState(false);
    const synth = useRef<SpeechSynthesis | null>(null);

    useEffect(() => {
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            synth.current = window.speechSynthesis;
            setIsSupported(true);
        }
    }, []);

    const speak = useCallback((text: string) => {
        if (!synth.current) return;

        // Cancel any current speech
        synth.current.cancel();

        const utterance = new SpeechSynthesisUtterance(text);

        // Configure voice (prefer nicer voices if available)
        const voices = synth.current.getVoices();
        // Try to find a natural sounding English voice
        const preferredVoice = voices.find(v =>
            (v.name.includes('Google') && v.name.includes('US English')) ||
            (v.name.includes('Premium') && v.name.includes('English')) ||
            v.lang === 'en-US'
        );

        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }

        // Set some defaults
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Event handlers
        utterance.onstart = () => {
            setIsSpeaking(true);
            if (options.onStart) options.onStart();
        };

        utterance.onend = () => {
            setIsSpeaking(false);
            if (options.onEnd) options.onEnd();
        };

        utterance.onerror = (event) => {
            setIsSpeaking(false);
            console.error('TTS Error:', event);
            if (options.onError) options.onError(event);
        };

        synth.current.speak(utterance);
    }, [options]);

    const stop = useCallback(() => {
        if (synth.current) {
            synth.current.cancel();
            setIsSpeaking(false);
        }
    }, []);

    return {
        speak,
        stop,
        isSpeaking,
        isSupported
    };
}
