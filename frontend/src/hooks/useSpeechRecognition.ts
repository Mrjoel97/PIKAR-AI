'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect, useRef, useCallback } from 'react';

import { createClient } from '@/lib/supabase/client';

interface UseSpeechRecognitionReturn {
  isRecording: boolean;
  isSupported: boolean;
  isTranscribing: boolean;
  transcript: string;
  transcriptVersion: number;
  interimTranscript: string;
  error: string | null;
  startRecording: () => void;
  stopRecording: () => void;
  toggleRecording: () => void;
  clearTranscript: () => void;
}

const AUTO_STOP_SILENCE_MS = 1400;
const MIN_RECORDING_MS = 400;
const SILENCE_CHECK_INTERVAL_MS = 120;
const AUDIO_LEVEL_THRESHOLD = 0.02;
const SUPPORTED_RECORDER_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
];

function pickRecorderMimeType(): string {
  if (typeof window === 'undefined' || typeof MediaRecorder === 'undefined') {
    return '';
  }
  if (typeof MediaRecorder.isTypeSupported !== 'function') {
    return SUPPORTED_RECORDER_MIME_TYPES[0];
  }
  for (const candidate of SUPPORTED_RECORDER_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }
  return '';
}

function recorderSupported(): boolean {
  return !!(
    typeof window !== 'undefined'
    && typeof navigator.mediaDevices?.getUserMedia === 'function'
    && typeof MediaRecorder !== 'undefined'
  );
}

function computeAudioLevel(samples: Uint8Array<ArrayBufferLike>): number {
  let sumSquares = 0;
  for (let i = 0; i < samples.length; i++) {
    const centered = (samples[i] - 128) / 128;
    sumSquares += centered * centered;
  }
  return Math.sqrt(sumSquares / Math.max(samples.length, 1));
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [transcriptVersion, setTranscriptVersion] = useState(0);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserBufferRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const silenceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recorderMimeTypeRef = useRef('');
  const stopRequestedRef = useRef(false);
  const lastSpeechAtRef = useRef(0);
  const recordingStartedAtRef = useRef(0);
  const hasDetectedSpeechRef = useRef(false);
  const transcriptVersionRef = useRef(0);

  useEffect(() => {
    const supported = recorderSupported();
    setIsSupported(supported);
    recorderMimeTypeRef.current = supported ? pickRecorderMimeType() : '';
  }, []);

  const cleanupAudioResources = useCallback((stopTracks: boolean = true) => {
    if (silenceIntervalRef.current) {
      clearInterval(silenceIntervalRef.current);
      silenceIntervalRef.current = null;
    }

    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    analyserRef.current = null;
    analyserBufferRef.current = null;

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => { /* noop */ });
      audioContextRef.current = null;
    }

    if (stopTracks && mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    hasDetectedSpeechRef.current = false;
    lastSpeechAtRef.current = 0;
    recordingStartedAtRef.current = 0;
  }, []);

  const transcribeBlob = useCallback(async (blob: Blob): Promise<string> => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    if (!token) {
      throw new Error('Authentication required for voice transcription');
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const formData = new FormData();
    const mimeType = blob.type || recorderMimeTypeRef.current || 'audio/webm';
    const extension = mimeType.includes('ogg') ? 'ogg' : mimeType.includes('mpeg') ? 'mp3' : 'webm';
    formData.append('audio', blob, `speech-input.${extension}`);
    formData.append('language_code', 'en-US');

    const response = await fetch(`${apiBaseUrl}/ws/voice/transcribe`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || `HTTP ${response.status}`);
    }
    if (!payload?.success || !payload?.transcript?.trim()) {
      throw new Error(payload?.error || 'No speech detected. Please try again.');
    }
    return String(payload.transcript).trim();
  }, []);

  const finalizeRecording = useCallback(async () => {
    const mimeType = recorderMimeTypeRef.current || 'audio/webm';
    const blob = new Blob(chunksRef.current, { type: mimeType });
    chunksRef.current = [];

    if (!blob.size) {
      setIsTranscribing(false);
      setInterimTranscript('');
      setError('No audio captured. Please try again.');
      stopRequestedRef.current = false;
      return;
    }

    try {
      const text = await transcribeBlob(blob);
      setTranscript(text);
      transcriptVersionRef.current += 1;
      setTranscriptVersion(transcriptVersionRef.current);
      setError(null);
    } catch (error: unknown) {
      setTranscript('');
      setError(getErrorMessage(error, 'Voice transcription failed. Please try again.'));
    } finally {
      setIsTranscribing(false);
      setInterimTranscript('');
      stopRequestedRef.current = false;
    }
  }, [transcribeBlob]);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || stopRequestedRef.current) {
      return;
    }

    stopRequestedRef.current = true;
    setIsRecording(false);
    setIsTranscribing(true);
    setInterimTranscript('Transcribing...');
    cleanupAudioResources(false);

    try {
      if (recorder.state !== 'inactive') {
        recorder.stop();
      } else {
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
        mediaRecorderRef.current = null;
        void finalizeRecording();
      }
    } catch {
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
      mediaRecorderRef.current = null;
      stopRequestedRef.current = false;
      setIsTranscribing(false);
      setInterimTranscript('');
      setError('Failed to stop recording. Please try again.');
    }
  }, [cleanupAudioResources, finalizeRecording]);

  const startRecording = useCallback(async () => {
    if (!recorderSupported()) {
      setIsSupported(false);
      setError('Voice input is not supported in this browser.');
      return;
    }
    if (isRecording || isTranscribing) {
      return;
    }

    setTranscript('');
    setInterimTranscript('');
    setError(null);
    chunksRef.current = [];
    stopRequestedRef.current = false;
    hasDetectedSpeechRef.current = false;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;

      recorderMimeTypeRef.current = pickRecorderMimeType();
      const recorder = recorderMimeTypeRef.current
        ? new MediaRecorder(stream, { mimeType: recorderMimeTypeRef.current })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorderMimeTypeRef.current = recorder.mimeType || recorderMimeTypeRef.current || 'audio/webm';

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onerror = () => {
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
        mediaRecorderRef.current = null;
        cleanupAudioResources();
        setIsRecording(false);
        setIsTranscribing(false);
        setError('Voice capture failed. Please try again.');
      };
      recorder.onstop = () => {
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
        mediaRecorderRef.current = null;
        void finalizeRecording();
      };

      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = source;
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyserRef.current = analyser;
      analyserBufferRef.current = new Uint8Array(new ArrayBuffer(analyser.fftSize));
      source.connect(analyser);

      recorder.start(250);
      recordingStartedAtRef.current = Date.now();
      lastSpeechAtRef.current = recordingStartedAtRef.current;
      setIsRecording(true);

      silenceIntervalRef.current = setInterval(() => {
        if (!analyserRef.current || !analyserBufferRef.current || stopRequestedRef.current) {
          return;
        }
        analyserRef.current.getByteTimeDomainData(analyserBufferRef.current);
        const level = computeAudioLevel(analyserBufferRef.current);
        const now = Date.now();
        if (level >= AUDIO_LEVEL_THRESHOLD) {
          hasDetectedSpeechRef.current = true;
          lastSpeechAtRef.current = now;
        }
        if (
          hasDetectedSpeechRef.current
          && (now - recordingStartedAtRef.current) >= MIN_RECORDING_MS
          && (now - lastSpeechAtRef.current) >= AUTO_STOP_SILENCE_MS
        ) {
          stopRecording();
        }
      }, SILENCE_CHECK_INTERVAL_MS);
    } catch (error: unknown) {
      cleanupAudioResources();
      setIsRecording(false);
      setIsTranscribing(false);
      setError(getErrorMessage(error, 'Could not access microphone. Please check permissions.'));
    }
  }, [cleanupAudioResources, finalizeRecording, isRecording, isTranscribing, stopRecording]);

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  const clearTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
    setError(null);
  }, []);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          // noop
        }
      }
      cleanupAudioResources();
    };
  }, [cleanupAudioResources]);

  return {
    isRecording,
    isSupported,
    isTranscribing,
    transcript,
    transcriptVersion,
    interimTranscript,
    error,
    startRecording,
    stopRecording,
    toggleRecording,
    clearTranscript,
  };
}
