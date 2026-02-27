'use client'
import { useState, useEffect, useRef, useCallback } from 'react';

// TypeScript declarations for Web Speech API
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface SpeechRecognitionConstructor {
  new(): SpeechRecognition;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

interface UseSpeechRecognitionReturn {
  isRecording: boolean;
  isSupported: boolean;
  transcript: string;
  interimTranscript: string;
  error: string | null;
  startRecording: () => void;
  stopRecording: () => void;
  toggleRecording: () => void;
  clearTranscript: () => void;
}

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isRecordingRef = useRef(false);

  // Check browser support on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
      setIsSupported(!!SpeechRecognitionAPI);
    }
  }, []);

  // Cooldown tracking to avoid restarting recognition too fast
  const lastEndTimeRef = useRef(0);

  // Helper: build (or rebuild) the SpeechRecognition instance
  const rebuildRecognition = () => {
    if (typeof window === 'undefined') return;

    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;

    // Abort old instance if any
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch { /* ignore */ }
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      console.log('Speech recognition started');
      isRecordingRef.current = true;
      setIsRecording(true);
      setError(null);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      let final = '';

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (final) {
        setTranscript(final.trim());
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('Speech recognition error:', event.error);
      let errorMessage = 'Speech recognition error';

      switch (event.error) {
        case 'no-speech':
          // During continuous listening, no-speech is common and not a real error
          // Just silently end — the auto-listen loop will restart if needed
          isRecordingRef.current = false;
          setIsRecording(false);
          return;
        case 'audio-capture':
          errorMessage = 'No microphone found. Please check your microphone.';
          break;
        case 'not-allowed':
          errorMessage = 'Microphone access denied. Please allow microphone access in your browser.';
          break;
        case 'network':
          // Chrome kills the recognition instance after network errors
          // Rebuild it so the next startRecording call works
          console.warn('Speech recognition network error — rebuilding instance');
          isRecordingRef.current = false;
          setIsRecording(false);
          lastEndTimeRef.current = Date.now();
          rebuildRecognition();
          return; // Don't show error to user — auto-listen will retry
        case 'aborted':
          // User aborted, not really an error
          isRecordingRef.current = false;
          setIsRecording(false);
          return;
        default:
          errorMessage = `Error: ${event.error}`;
      }

      setError(errorMessage);
      isRecordingRef.current = false;
      setIsRecording(false);
    };

    recognition.onend = () => {
      console.log('Speech recognition ended');
      isRecordingRef.current = false;
      setIsRecording(false);
      lastEndTimeRef.current = Date.now();
    };

    recognitionRef.current = recognition;
  };

  // Build initial instance on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      console.log('Speech Recognition API not supported');
      return;
    }

    rebuildRecognition();

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // Ignore
        }
      }
    };
  }, []);

  const startRecording = useCallback(() => {
    if (!recognitionRef.current) {
      setError('Speech recognition not available');
      return;
    }

    if (isRecordingRef.current) {
      console.log('Already recording');
      return;
    }

    // Enforce minimum cooldown between sessions to avoid Chrome network errors
    const elapsed = Date.now() - lastEndTimeRef.current;
    const MIN_GAP_MS = 500;
    if (elapsed < MIN_GAP_MS) {
      const delay = MIN_GAP_MS - elapsed;
      console.log(`Waiting ${delay}ms before starting recognition (cooldown)`);
      setTimeout(() => {
        if (!isRecordingRef.current) {
          startRecording();
        }
      }, delay);
      return;
    }

    // Reset state
    setTranscript('');
    setInterimTranscript('');
    setError(null);

    try {
      recognitionRef.current.start();
      console.log('Started recording');
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      // Instance might be dead — rebuild and retry once
      rebuildRecognition();
      setTimeout(() => {
        try {
          recognitionRef.current?.start();
        } catch (retryErr) {
          setError('Failed to start recording. Please try again.');
        }
      }, 300);
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (!recognitionRef.current) return;

    if (!isRecordingRef.current) {
      console.log('Not recording');
      return;
    }

    try {
      recognitionRef.current.stop();
      console.log('Stopped recording');
    } catch (err) {
      console.error('Failed to stop speech recognition:', err);
    }
  }, []);

  const toggleRecording = useCallback(() => {
    if (isRecordingRef.current) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [startRecording, stopRecording]);

  const clearTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
  }, []);

  return {
    isRecording,
    isSupported,
    transcript,
    interimTranscript,
    error,
    startRecording,
    stopRecording,
    toggleRecording,
    clearTranscript,
  };
}
