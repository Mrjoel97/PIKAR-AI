// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useCallback, useEffect, useRef } from 'react';

interface UseTextToSpeechOptions {
    onStart?: () => void;
    onEnd?: () => void;
    onError?: (error: unknown) => void;
}

export function useTextToSpeech(options: UseTextToSpeechOptions = {}) {
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isSupported] = useState(
        () => typeof window !== 'undefined' && 'speechSynthesis' in window,
    );
    const synth = useRef<SpeechSynthesis | null>(null);
    const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

    useEffect(() => {
        if (!isSupported || typeof window === 'undefined') {
            return;
        }

        synth.current = window.speechSynthesis;

        const updateVoices = () => {
            voicesRef.current = synth.current?.getVoices() ?? [];
        };

        updateVoices();
        synth.current.addEventListener('voiceschanged', updateVoices);
        return () => synth.current?.removeEventListener('voiceschanged', updateVoices);
    }, [isSupported]);

    const speak = useCallback((text: string) => {
        if (!synth.current) return;

        // Cancel any current speech
        synth.current.cancel();

        const utterance = new SpeechSynthesisUtterance(text);

        // Prefer warm, natural-sounding feminine English voices when the live
        // brainstorm transport is unavailable and we need browser TTS fallback.
        const preferredVoice = [...voicesRef.current]
            .map((voice) => {
                const normalizedName = voice.name.toLowerCase();
                const normalizedLang = voice.lang.toLowerCase();
                let score = 0;

                if (normalizedLang.startsWith('en-us')) score += 10;
                else if (normalizedLang.startsWith('en')) score += 7;

                if (normalizedName.includes('female')) score += 12;
                if (/(karen|samantha|victoria|allison|ava|aria|zira|jenny|emma|serena|moira|salli|natasha|lisa)/.test(normalizedName)) {
                    score += 10;
                }
                if (/(natural|neural|premium|studio|wavenet|enhanced)/.test(normalizedName)) {
                    score += 6;
                }
                if (normalizedName.includes('google') && normalizedName.includes('english')) score += 4;
                if (!voice.localService) score += 2;

                return { voice, score };
            })
            .sort((left, right) => right.score - left.score)[0]?.voice;

        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }

        // Slightly slower and softer settings make the fallback feel less robotic.
        utterance.rate = 0.96;
        utterance.pitch = 1.08;
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
