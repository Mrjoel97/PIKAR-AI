// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * useVoiceSession — React hook for real-time voice conversations via WebSocket.
 *
 * Manages the browser mic → WebSocket → Gemini Live → WebSocket → speaker pipeline.
 *
 * Audio format:
 *   - Mic capture: 16kHz, 16-bit PCM, mono (via ScriptProcessorNode or AudioWorklet)
 *   - Speaker playback: 24kHz, 16-bit PCM, mono
 *
 * Protocol: See voice_session.py for the full WebSocket message protocol.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { getAccessToken } from '@/lib/supabase/client';
import { buildAgentWebSocketUrl } from '@/services/api';

interface VoiceSessionState {
    isConnected: boolean;
    isAgentSpeaking: boolean;
    agentTranscript: string;
    userTranscript: string;
    transcriptTurns: VoiceTranscriptTurn[];
    error: string | null;
    remainingSeconds: number | null;
    isWrappingUp: boolean;
    isTimedOut: boolean;
}

/** Callback invoked when the server sends a session_timeout message. */
export type OnSessionTimeout = () => void;

interface UseVoiceSessionOptions {
    onSessionTimeout?: OnSessionTimeout;
}

export interface VoiceSessionConnectOptions {
    startMode?: VoiceSessionStartMode;
    initialTurns?: VoiceTranscriptTurn[];
    resumeTranscript?: string;
}

interface UseVoiceSessionReturn extends VoiceSessionState {
    connect: (
        sessionId: string,
        options?: VoiceSessionConnectOptions,
    ) => Promise<void>;
    disconnect: () => void;
}

type VoiceSpeaker = 'user' | 'agent';
export type VoiceSessionStartMode = 'resume' | 'fresh';

export interface VoiceTranscriptTurn {
    speaker: VoiceSpeaker;
    text: string;
    tsMs?: number;
}

// PCM audio config
const MIC_SAMPLE_RATE = 16000;
const SPEAKER_SAMPLE_RATE = 24000;
const BUFFER_SIZE = 4096;
const CONNECTION_TIMEOUT_MS = 15000; // 15s timeout waiting for 'ready'
const HEARTBEAT_INTERVAL_MS = 20000; // Ping every 20s to detect dead connections
const LOCAL_VAD_RMS_THRESHOLD = 0.003;
const LOCAL_AUDIO_TRANSMIT_THRESHOLD = 0.0012;
const LOCAL_VAD_SILENCE_MS = 700;
const LOCAL_VAD_TRAILING_MS = 450;
const AGENT_RESPONSE_DELAY_MS = 250; // Keep voice turns feeling conversational instead of stalled
const VOICE_AUTH_LOOKUP_TIMEOUT_MS = 2500;
const PLAYBACK_BUFFER_TARGET_SAMPLES = Math.round(SPEAKER_SAMPLE_RATE * 0.35);
const REMOTE_TURN_ACTIVITY_TAIL_MS = 650;

/** Map WebSocket close codes to human-readable messages. */
function closeCodeMessage(code: number, reason?: string): string {
    if (reason) return reason;
    switch (code) {
        case 1000: return 'Session ended normally';
        case 1001: return 'Server is shutting down';
        case 1006: return 'Network connection lost — check your internet';
        case 1008: return 'Authentication failed — try refreshing the page';
        case 1011: return 'Server error — please try again';
        case 1013: return 'Server is busy — please try again in a moment';
        default: return `Connection closed (code ${code})`;
    }
}

/**
 * Downsample a Float32Array from sourceSampleRate to targetSampleRate
 * and convert to 16-bit PCM (Int16Array).
 */
function float32ToPcm16(samples: Float32Array, sourceSampleRate: number, targetSampleRate: number): Int16Array {
    const ratio = sourceSampleRate / targetSampleRate;
    const newLength = Math.round(samples.length / ratio);
    const result = new Int16Array(newLength);
    for (let i = 0; i < newLength; i++) {
        const srcIndex = Math.round(i * ratio);
        const s = Math.max(-1, Math.min(1, samples[srcIndex] ?? 0));
        result[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return result;
}

/**
 * Convert base64-encoded audio bytes to a Uint8Array.
 */
function base64ToBytes(base64: string): Uint8Array {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}

/**
 * Convert a little-endian 16-bit PCM byte buffer into Float32 samples.
 */
function pcm16BytesToFloat32(bytes: Uint8Array): Float32Array {
    const sampleCount = Math.floor(bytes.byteLength / 2);
    const float32 = new Float32Array(sampleCount);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let i = 0; i < sampleCount; i++) {
        float32[i] = view.getInt16(i * 2, true) / 0x8000;
    }
    return float32;
}

function resampleFloat32(
    samples: Float32Array,
    sourceSampleRate: number,
    targetSampleRate: number,
): Float32Array {
    if (samples.length === 0 || sourceSampleRate === targetSampleRate) {
        return samples;
    }

    const ratio = sourceSampleRate / targetSampleRate;
    const newLength = Math.max(1, Math.round(samples.length / ratio));
    const result = new Float32Array(newLength);

    for (let i = 0; i < newLength; i++) {
        const position = i * ratio;
        const index = Math.floor(position);
        const nextIndex = Math.min(index + 1, samples.length - 1);
        const alpha = position - index;
        const start = samples[index] ?? 0;
        const end = samples[nextIndex] ?? start;
        result[i] = start + (end - start) * alpha;
    }
    return result;
}

function parsePcmSampleRate(mimeType?: string): number {
    if (!mimeType) return SPEAKER_SAMPLE_RATE;

    const rateMatch = mimeType.match(/rate=(\d+)/i);
    if (rateMatch) {
        const parsed = Number.parseInt(rateMatch[1], 10);
        if (Number.isFinite(parsed) && parsed > 0) {
            return parsed;
        }
    }

    return SPEAKER_SAMPLE_RATE;
}

/**
 * Convert a base64-encoded audio chunk to Float32Array for playback.
 * Handles raw PCM from Gemini Live plus encoded fallbacks if the backend
 * ever returns a different audio MIME type.
 */
async function decodeAgentAudioChunk(
    base64: string,
    mimeType: string | undefined,
    context: AudioContext,
): Promise<Float32Array> {
    const bytes = base64ToBytes(base64);
    const normalizedMime = mimeType?.toLowerCase() ?? 'audio/pcm;rate=24000';

    if (normalizedMime.includes('audio/pcm') || normalizedMime.includes('audio/l16')) {
        const sampleRate = parsePcmSampleRate(normalizedMime);
        const pcm = pcm16BytesToFloat32(bytes);
        return resampleFloat32(pcm, sampleRate, SPEAKER_SAMPLE_RATE);
    }

    const chunkBuffer = bytes.slice().buffer;
    const decoded = await context.decodeAudioData(chunkBuffer);
    const channelCount = Math.max(decoded.numberOfChannels, 1);
    const mono = new Float32Array(decoded.length);

    for (let channelIndex = 0; channelIndex < channelCount; channelIndex++) {
        const channel = decoded.getChannelData(channelIndex);
        for (let sampleIndex = 0; sampleIndex < decoded.length; sampleIndex++) {
            mono[sampleIndex] += (channel[sampleIndex] ?? 0) / channelCount;
        }
    }

    return resampleFloat32(mono, decoded.sampleRate, SPEAKER_SAMPLE_RATE);
}

/**
 * Convert a base64-encoded 16-bit PCM buffer to Float32Array for playback.
 */
function pcm16ToFloat32(base64: string): Float32Array {
    const bytes = base64ToBytes(base64);
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 0x8000;
    }
    return float32;
}

export function drainPlaybackQueue(queue: Float32Array[], targetSamples: number): Float32Array | null {
    if (queue.length === 0) {
        return null;
    }

    let totalSamples = 0;
    const segments: Float32Array[] = [];
    while (queue.length > 0 && totalSamples < targetSamples) {
        const next = queue.shift();
        if (!next) break;
        segments.push(next);
        totalSamples += next.length;
    }

    if (segments.length === 0) {
        return null;
    }
    if (segments.length === 1) {
        return segments[0];
    }

    const merged = new Float32Array(totalSamples);
    let offset = 0;
    for (const segment of segments) {
        merged.set(segment, offset);
        offset += segment.length;
    }
    return merged;
}

async function resumeAudioContext(context: AudioContext | null): Promise<void> {
    if (!context || context.state === 'closed' || context.state === 'running') {
        return;
    }

    try {
        await context.resume();
    } catch {
        // Some browsers may reject resume if the page lost its user gesture.
        // Playback code will retry before the next chunk starts.
    }
}

export function useVoiceSession(options: UseVoiceSessionOptions = {}): UseVoiceSessionReturn {
    const onSessionTimeoutRef = useRef(options.onSessionTimeout);
    onSessionTimeoutRef.current = options.onSessionTimeout;

    const [state, setState] = useState<VoiceSessionState>({
        isConnected: false,
        isAgentSpeaking: false,
        agentTranscript: '',
        userTranscript: '',
        transcriptTurns: [],
        error: null,
        remainingSeconds: null,
        isWrappingUp: false,
        isTimedOut: false,
    });

    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const micStreamRef = useRef<MediaStream | null>(null);
    const scriptNodeRef = useRef<ScriptProcessorNode | null>(null);
    const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);

    // Playback queue: Gemini sends many small audio chunks, we queue and play them sequentially
    const playbackQueueRef = useRef<Float32Array[]>([]);
    const audioDecodeChainRef = useRef<Promise<void>>(Promise.resolve());
    const isPlayingRef = useRef(false);
    const playbackContextRef = useRef<AudioContext | null>(null);
    const currentPlaybackSourceRef = useRef<AudioBufferSourceNode | null>(null);
    const micMonitorGainRef = useRef<GainNode | null>(null);
    const heartbeatRef = useRef<NodeJS.Timeout | null>(null);
    const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const connectAttemptRef = useRef(0);
    const lastSpeechAtRef = useRef(0);
    const hasSpeechInTurnRef = useRef(false);
    const audioStreamEndedRef = useRef(true);
    const lastRemoteActivityAtRef = useRef(0);
    const remoteTurnCompleteRef = useRef(true);

    // 3-second thinking pause: buffer agent audio before starting playback on new turns
    const pendingTurnDelayRef = useRef<NodeJS.Timeout | null>(null);
    const isAwaitingNewTurnRef = useRef(true);

    // Full transcript accumulator for brainstorm conclusion
    const fullAgentTranscriptRef = useRef('');
    const fullUserTranscriptRef = useRef('');

    const appendTranscriptChunk = useCallback((speaker: VoiceSpeaker, rawText: string) => {
        const text = rawText.replace(/\s+/g, ' ').trim();
        if (!text) return;

        setState(prev => {
            const turns = [...prev.transcriptTurns];
            const last = turns[turns.length - 1];

            if (last && last.speaker === speaker) {
                if (text === last.text) {
                    return prev;
                }
                // Gemini may resend cumulative partials for the current turn; prefer the longer one.
                if (text.startsWith(last.text)) {
                    turns[turns.length - 1] = { ...last, text };
                } else if (last.text.startsWith(text) || last.text.includes(text)) {
                    return prev;
                } else {
                    turns[turns.length - 1] = { ...last, text: `${last.text} ${text}`.trim() };
                }
            } else {
                turns.push({ speaker, text, tsMs: Date.now() });
            }

            return { ...prev, transcriptTurns: turns };
        });
    }, []);

    const interruptPlayback = useCallback(() => {
        // Cancel pending thinking-pause timer
        if (pendingTurnDelayRef.current) {
            clearTimeout(pendingTurnDelayRef.current);
            pendingTurnDelayRef.current = null;
        }
        isAwaitingNewTurnRef.current = true;
        lastRemoteActivityAtRef.current = 0;
        remoteTurnCompleteRef.current = true;

        playbackQueueRef.current = [];
        audioDecodeChainRef.current = Promise.resolve();
        isPlayingRef.current = false;

        const source = currentPlaybackSourceRef.current;
        currentPlaybackSourceRef.current = null;
        if (source) {
            source.onended = null;
            try {
                source.stop();
            } catch {
                // No-op if the source already ended.
            }
            try {
                source.disconnect();
            } catch {
                // No-op.
            }
        }

        setState(prev => ({ ...prev, isAgentSpeaking: false }));
    }, []);

    const playNextChunk = useCallback(() => {
        const chunk = drainPlaybackQueue(
            playbackQueueRef.current,
            PLAYBACK_BUFFER_TARGET_SAMPLES,
        );
        if (!chunk) {
            isPlayingRef.current = false;
            currentPlaybackSourceRef.current = null;
            const remoteTurnSettled = remoteTurnCompleteRef.current
                || (Date.now() - lastRemoteActivityAtRef.current) > REMOTE_TURN_ACTIVITY_TAIL_MS;
            if (remoteTurnSettled && !pendingTurnDelayRef.current) {
                setState(prev => ({ ...prev, isAgentSpeaking: false }));
            }
            return;
        }

        lastRemoteActivityAtRef.current = Date.now();
        isPlayingRef.current = true;
        setState(prev => ({ ...prev, isAgentSpeaking: true }));
        const ctx = playbackContextRef.current;
        if (!ctx) {
            isPlayingRef.current = false;
            return;
        }

        const startPlayback = () => {
            const buffer = ctx.createBuffer(1, chunk.length, SPEAKER_SAMPLE_RATE);
            // TS 5.9 types `copyToChannel` narrowly; clone into a fresh Float32Array to satisfy it.
            buffer.copyToChannel(Float32Array.from(chunk), 0);

            const source = ctx.createBufferSource();
            source.buffer = buffer;
            source.connect(ctx.destination);
            currentPlaybackSourceRef.current = source;
            source.onended = () => {
                if (currentPlaybackSourceRef.current === source) {
                    currentPlaybackSourceRef.current = null;
                }
                playNextChunk();
            };
            source.start();
        };

        // Resume context before source.start(); some browsers otherwise accept the
        // source without ever emitting audible playback for the first turn.
        if (ctx.state === 'suspended') {
            void ctx.resume()
                .then(() => {
                    if (ctx.state !== 'closed') {
                        startPlayback();
                    }
                })
                .catch(() => {
                    isPlayingRef.current = false;
                    setState(prev => ({
                        ...prev,
                        isAgentSpeaking: false,
                        error: prev.error ?? 'Audio playback is blocked. Check browser audio permissions and try again.',
                    }));
                });
            return;
        }

        startPlayback();
    }, []);

    const enqueueAudio = useCallback((base64Data: string, mimeType?: string) => {
        audioDecodeChainRef.current = audioDecodeChainRef.current
            .catch(() => {
                // Keep the decode chain alive after prior chunk failures.
            })
            .then(async () => {
                const ctx = playbackContextRef.current;
                if (!ctx || ctx.state === 'closed') {
                    return;
                }

                try {
                    const float32 = mimeType
                        ? await decodeAgentAudioChunk(base64Data, mimeType, ctx)
                        : pcm16ToFloat32(base64Data);
                    if (!float32.length || playbackContextRef.current !== ctx || ctx.state === 'closed') {
                        return;
                    }

                    playbackQueueRef.current.push(float32);
                    lastRemoteActivityAtRef.current = Date.now();
                    remoteTurnCompleteRef.current = false;

                    if (!isPlayingRef.current && !pendingTurnDelayRef.current) {
                        if (isAwaitingNewTurnRef.current) {
                            // First audio chunk of new agent turn — add a tiny buffer for smoother playback.
                            isAwaitingNewTurnRef.current = false;
                            pendingTurnDelayRef.current = setTimeout(() => {
                                pendingTurnDelayRef.current = null;
                                if (playbackQueueRef.current.length > 0 && !isPlayingRef.current) {
                                    playNextChunk();
                                }
                            }, AGENT_RESPONSE_DELAY_MS);
                        } else {
                            playNextChunk();
                        }
                    }
                } catch (error) {
                    console.error('[VoiceSession] Failed to decode agent audio:', error);
                    setState(prev => ({
                        ...prev,
                        error: prev.error ?? 'Agent audio could not be decoded. Please retry the brainstorm session.',
                    }));
                }
            });
    }, [playNextChunk]);

    const connect = useCallback(async (
        sessionId: string,
        options?: VoiceSessionConnectOptions,
    ) => {
        const attemptId = ++connectAttemptRef.current;
        const startMode = options?.startMode === 'fresh' ? 'fresh' : 'resume';
        const initialTurns = [...(options?.initialTurns ?? [])];
        const resumedAgentTranscript = initialTurns
            .filter((turn) => turn.speaker === 'agent')
            .map((turn) => turn.text.trim())
            .filter(Boolean)
            .join(' ')
            .trim();
        const resumedUserTranscript = initialTurns
            .filter((turn) => turn.speaker === 'user')
            .map((turn) => turn.text.trim())
            .filter(Boolean)
            .join(' ')
            .trim();
        const resumeTranscript = options?.resumeTranscript?.trim() ?? '';

        // Clean up any existing connection
        if (heartbeatRef.current) {
            clearInterval(heartbeatRef.current);
            heartbeatRef.current = null;
        }
        if (connectionTimeoutRef.current) {
            clearTimeout(connectionTimeoutRef.current);
            connectionTimeoutRef.current = null;
        }
        if (wsRef.current) {
            try {
                wsRef.current.close();
            } catch {
                // No-op if the socket is already closing.
            }
            wsRef.current = null;
        }
        cleanupResources();

        setState({
            isConnected: false,
            isAgentSpeaking: false,
            agentTranscript: resumedAgentTranscript,
            userTranscript: resumedUserTranscript,
            transcriptTurns: initialTurns,
            error: null,
            remainingSeconds: null,
            isWrappingUp: false,
            isTimedOut: false,
        });
        fullAgentTranscriptRef.current = resumedAgentTranscript
            ? `${resumedAgentTranscript} `
            : '';
        fullUserTranscriptRef.current = resumedUserTranscript
            ? `${resumedUserTranscript} `
            : '';
        lastSpeechAtRef.current = 0;
        hasSpeechInTurnRef.current = false;
        audioStreamEndedRef.current = true;
        lastRemoteActivityAtRef.current = 0;
        remoteTurnCompleteRef.current = true;

        try {
            // Get auth token
            const token = await getAccessToken({
                timeoutMs: VOICE_AUTH_LOOKUP_TIMEOUT_MS,
            }).catch((error) => {
                console.warn('[VoiceSession] Failed to resolve access token:', error);
                return null;
            });
            if (!token) {
                const err = 'Not authenticated';
                setState(prev => ({ ...prev, error: err }));
                throw new Error(err);
            }

            // Request mic permission
            const micStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: { ideal: MIC_SAMPLE_RATE },
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            micStreamRef.current = micStream;

            // Create audio contexts
            const captureCtx = new AudioContext({ sampleRate: MIC_SAMPLE_RATE });
            audioContextRef.current = captureCtx;

            const playbackCtx = new AudioContext({ sampleRate: SPEAKER_SAMPLE_RATE });
            playbackContextRef.current = playbackCtx;

            // Unlock audio contexts while we are still inside the user-initiated
            // brainstorm action. Without this, some browsers keep the speaker
            // context suspended and the greeting audio never becomes audible.
            await Promise.allSettled([
                resumeAudioContext(captureCtx),
                resumeAudioContext(playbackCtx),
            ]);

            // Connect to WebSocket using a Promise to wait for 'ready'
            await new Promise<void>((resolve, reject) => {
                const wsUrl = buildAgentWebSocketUrl(`/ws/voice/${sessionId}`);
                const ws = new WebSocket(wsUrl);
                wsRef.current = ws;
                let isConnected = false;
                let isSettled = false;
                const isCurrentAttempt = () => connectAttemptRef.current === attemptId && wsRef.current === ws;
                const settleResolve = () => {
                    if (isSettled) return;
                    isSettled = true;
                    resolve();
                };
                const settleReject = (error: Error) => {
                    if (isSettled) return;
                    isSettled = true;
                    reject(error);
                };

                ws.onopen = () => {
                    if (!isCurrentAttempt()) {
                        settleReject(new Error('Voice connection superseded'));
                        return;
                    }
                    // Send auth as first message
                    ws.send(JSON.stringify({
                        type: 'auth',
                        token,
                        start_mode: startMode,
                        ...(resumeTranscript ? { resume_transcript: resumeTranscript } : {}),
                    }));
                };

                // Start connection timeout
                connectionTimeoutRef.current = setTimeout(() => {
                    if (!isCurrentAttempt()) return;
                    if (!isConnected && ws.readyState !== WebSocket.CLOSED) {
                        ws.close();
                        const err = 'Voice connection timed out — server may be unavailable';
                        setState(prev => ({ ...prev, error: err }));
                        settleReject(new Error(err));
                    }
                }, CONNECTION_TIMEOUT_MS);

                ws.onmessage = (event) => {
                    if (!isCurrentAttempt()) {
                        settleReject(new Error('Voice connection superseded'));
                        return;
                    }
                    try {
                        const msg = JSON.parse(event.data);
                        switch (msg.type) {
                            case 'ready':
                                isConnected = true;
                                if (connectionTimeoutRef.current) {
                                    clearTimeout(connectionTimeoutRef.current);
                                    connectionTimeoutRef.current = null;
                                }
                                setState(prev => ({ ...prev, isConnected: true, error: null }));
                                if (captureCtx.state === 'closed' || playbackCtx.state === 'closed') {
                                    const err = 'Voice connection was interrupted during startup';
                                    setState(prev => ({ ...prev, error: err }));
                                    settleReject(new Error(err));
                                    return;
                                }
                                void resumeAudioContext(playbackCtx);
                                void resumeAudioContext(captureCtx);
                                startMicCapture(captureCtx, micStream, ws);
                                // Start heartbeat pings
                                heartbeatRef.current = setInterval(() => {
                                    if (ws.readyState === WebSocket.OPEN) {
                                        try {
                                            ws.send(JSON.stringify({ type: 'ping' }));
                                        } catch {
                                            // Socket may have closed between the check and the send
                                        }
                                    } else {
                                        setState(prev => ({
                                            ...prev,
                                            error: 'Voice connection lost — you can still finalize your session',
                                            isConnected: false,
                                        }));
                                        if (heartbeatRef.current) {
                                            clearInterval(heartbeatRef.current);
                                            heartbeatRef.current = null;
                                        }
                                    }
                                }, HEARTBEAT_INTERVAL_MS);
                                settleResolve();
                                break;
                            case 'audio':
                                enqueueAudio(
                                    msg.data,
                                    typeof msg.mime_type === 'string' ? msg.mime_type : undefined,
                                );
                                break;
                            case 'transcript':
                                lastRemoteActivityAtRef.current = Date.now();
                                fullAgentTranscriptRef.current += msg.text;
                                appendTranscriptChunk('agent', msg.text);
                                setState(prev => ({
                                    ...prev,
                                    agentTranscript: fullAgentTranscriptRef.current,
                                }));
                                break;
                            case 'user_transcript':
                                fullUserTranscriptRef.current += msg.text + ' ';
                                appendTranscriptChunk('user', msg.text);
                                setState(prev => ({
                                    ...prev,
                                    userTranscript: fullUserTranscriptRef.current.trim(),
                                }));
                                break;
                            case 'turn_complete':
                                // Only clear speaking state if playback is truly finished.
                                // turn_complete means the model finished generating, but
                                // audio may still be queued or playing on the client.
                                remoteTurnCompleteRef.current = true;
                                if (!isPlayingRef.current && playbackQueueRef.current.length === 0 && !pendingTurnDelayRef.current) {
                                    setState(prev => ({ ...prev, isAgentSpeaking: false }));
                                }
                                isAwaitingNewTurnRef.current = true;
                                break;
                            case 'interrupted':
                                interruptPlayback();
                                break;
                            case 'time_warning':
                                setState(prev => ({
                                    ...prev,
                                    remainingSeconds: msg.remaining_seconds ?? null,
                                    isWrappingUp: true,
                                }));
                                break;
                            case 'session_timeout':
                                setState(prev => ({
                                    ...prev,
                                    remainingSeconds: 0,
                                    isTimedOut: true,
                                }));
                                onSessionTimeoutRef.current?.();
                                break;
                            case 'error':
                                if (connectionTimeoutRef.current) {
                                    clearTimeout(connectionTimeoutRef.current);
                                    connectionTimeoutRef.current = null;
                                }
                                setState(prev => ({ ...prev, error: msg.message }));
                                if (!isConnected) settleReject(new Error(msg.message));
                                break;
                        }
                    } catch (e) {
                        console.error('[VoiceSession] Error parsing message:', e);
                    }
                };

                ws.onerror = (err) => {
                    if (!isCurrentAttempt()) {
                        settleReject(new Error('Voice connection superseded'));
                        return;
                    }
                    console.error('[VoiceSession] WebSocket error:', err);
                    if (connectionTimeoutRef.current) {
                        clearTimeout(connectionTimeoutRef.current);
                        connectionTimeoutRef.current = null;
                    }
                    const errorMsg = isConnected
                        ? 'Voice connection error — you can still finalize your session'
                        : 'Failed to connect — check your network or try again';
                    setState(prev => ({ ...prev, error: errorMsg }));
                    if (!isConnected) settleReject(new Error(errorMsg));
                };

                ws.onclose = (event) => {
                    if (!isCurrentAttempt()) {
                        settleReject(new Error('Voice connection superseded'));
                        return;
                    }
                    console.log('[VoiceSession] WebSocket closed:', event.code, event.reason);
                    if (heartbeatRef.current) {
                        clearInterval(heartbeatRef.current);
                        heartbeatRef.current = null;
                    }
                    if (connectionTimeoutRef.current) {
                        clearTimeout(connectionTimeoutRef.current);
                        connectionTimeoutRef.current = null;
                    }
                    cleanupResources();
                    const msg = closeCodeMessage(event.code, event.reason);
                    setState(prev => ({
                        ...prev,
                        isConnected: false,
                        ...(event.code !== 1000 ? { error: msg } : {}),
                    }));
                    if (!isConnected) settleReject(new Error(msg));
                };
            });
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to start voice session';
            console.error('[VoiceSession] Failed to connect:', err);
            setState(prev => ({
                ...prev,
                error: message,
            }));
            throw err;
        }
    }, [appendTranscriptChunk, enqueueAudio, interruptPlayback]);

    const startMicCapture = (ctx: AudioContext, stream: MediaStream, ws: WebSocket) => {
        const hasLiveTrack = stream.getTracks().some((track) => track.readyState !== 'ended');
        if (ctx.state === 'closed' || !stream.active || !hasLiveTrack) {
            return;
        }

        const source = ctx.createMediaStreamSource(stream);
        sourceNodeRef.current = source;

        // ScriptProcessorNode for broad browser compat (AudioWorklet is newer but needs module loading)
        const scriptNode = ctx.createScriptProcessor(BUFFER_SIZE, 1, 1);
        scriptNodeRef.current = scriptNode;
        scriptNode.onaudioprocess = (e) => {
            if (ws.readyState !== WebSocket.OPEN) return;

            // Resume capture context if browser auto-suspended it
            if (ctx.state === 'suspended') {
                ctx.resume().catch(() => {});
            }

            // Keep the brainstorm voice flow half-duplex: while the agent is
            // speaking (or has queued audio about to play), do not forward mic
            // audio back to the server. That prevents the agent from hearing
            // its own voice and stalling the next user turn.
            const recentRemoteActivity = !remoteTurnCompleteRef.current
                && (Date.now() - lastRemoteActivityAtRef.current) <= REMOTE_TURN_ACTIVITY_TAIL_MS;
            const agentAudioActive = isPlayingRef.current
                || recentRemoteActivity
                || playbackQueueRef.current.length > 0
                || Boolean(pendingTurnDelayRef.current);
            if (agentAudioActive) {
                lastSpeechAtRef.current = 0;
                hasSpeechInTurnRef.current = false;
                audioStreamEndedRef.current = true;
                return;
            }

            const inputData = e.inputBuffer.getChannelData(0);
            let sumSquares = 0;
            for (let i = 0; i < inputData.length; i++) {
                sumSquares += inputData[i] * inputData[i];
            }
            const rms = Math.sqrt(sumSquares / Math.max(inputData.length, 1));
            const now = Date.now();
            const crossesSpeechThreshold = rms >= LOCAL_VAD_RMS_THRESHOLD;
            const crossesTransmitThreshold = crossesSpeechThreshold
                || rms >= LOCAL_AUDIO_TRANSMIT_THRESHOLD;

            if (crossesTransmitThreshold) {
                lastSpeechAtRef.current = now;
                hasSpeechInTurnRef.current = true;
                audioStreamEndedRef.current = false;
            }

            const recentlySpoke = hasSpeechInTurnRef.current
                && (now - lastSpeechAtRef.current) <= LOCAL_VAD_TRAILING_MS;
            const shouldTransmitAudio = crossesTransmitThreshold
                || recentlySpoke
                || hasSpeechInTurnRef.current;

            if (shouldTransmitAudio) {
                const pcm16 = float32ToPcm16(inputData, ctx.sampleRate, MIC_SAMPLE_RATE);
                const uint8 = new Uint8Array(pcm16.buffer);

                let binary = '';
                for (let i = 0; i < uint8.length; i++) {
                    binary += String.fromCharCode(uint8[i]);
                }
                const base64 = btoa(binary);
                ws.send(JSON.stringify({ type: 'audio', data: base64 }));
            }

            if (
                hasSpeechInTurnRef.current
                && !audioStreamEndedRef.current
                && (now - lastSpeechAtRef.current) >= LOCAL_VAD_SILENCE_MS
            ) {
                ws.send(JSON.stringify({ type: 'audio_stream_end' }));
                audioStreamEndedRef.current = true;
                hasSpeechInTurnRef.current = false;
            }
        };

        source.connect(scriptNode);
        // ScriptProcessorNode must be connected to an output to process.
        // Route it through a muted gain node to avoid mic sidetone in speakers.
        const monitorGain = ctx.createGain();
        monitorGain.gain.value = 0;
        micMonitorGainRef.current = monitorGain;
        scriptNode.connect(monitorGain);
        monitorGain.connect(ctx.destination);
    };

    const cleanupResources = useCallback(() => {
        if (currentPlaybackSourceRef.current) {
            currentPlaybackSourceRef.current.onended = null;
            try {
                currentPlaybackSourceRef.current.stop();
            } catch {
                // No-op if already stopped.
            }
            try {
                currentPlaybackSourceRef.current.disconnect();
            } catch {
                // No-op.
            }
            currentPlaybackSourceRef.current = null;
        }

        // Stop mic
        if (micStreamRef.current) {
            micStreamRef.current.getTracks().forEach(t => t.stop());
            micStreamRef.current = null;
        }

        // Disconnect audio nodes
        if (scriptNodeRef.current) {
            scriptNodeRef.current.disconnect();
            scriptNodeRef.current = null;
        }
        if (sourceNodeRef.current) {
            sourceNodeRef.current.disconnect();
            sourceNodeRef.current = null;
        }
        if (micMonitorGainRef.current) {
            micMonitorGainRef.current.disconnect();
            micMonitorGainRef.current = null;
        }

        // Close audio contexts
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => { });
            audioContextRef.current = null;
        }
        if (playbackContextRef.current) {
            playbackContextRef.current.close().catch(() => { });
            playbackContextRef.current = null;
        }

        // Clear playback queue and turn delay
        if (pendingTurnDelayRef.current) {
            clearTimeout(pendingTurnDelayRef.current);
            pendingTurnDelayRef.current = null;
        }
        playbackQueueRef.current = [];
        audioDecodeChainRef.current = Promise.resolve();
        isPlayingRef.current = false;
        isAwaitingNewTurnRef.current = true;
        lastSpeechAtRef.current = 0;
        hasSpeechInTurnRef.current = false;
        audioStreamEndedRef.current = true;
        lastRemoteActivityAtRef.current = 0;
        remoteTurnCompleteRef.current = true;
    }, []);

    const disconnect = useCallback(() => {
        connectAttemptRef.current += 1;
        if (heartbeatRef.current) {
            clearInterval(heartbeatRef.current);
            heartbeatRef.current = null;
        }
        if (connectionTimeoutRef.current) {
            clearTimeout(connectionTimeoutRef.current);
            connectionTimeoutRef.current = null;
        }
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'end' }));
            wsRef.current.close();
        }
        wsRef.current = null;
        cleanupResources();
        setState(prev => ({ ...prev, isConnected: false, isAgentSpeaking: false }));
        // Note: Do not clear transcripts here so the caller can read them after disconnect
    }, [cleanupResources]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            connectAttemptRef.current += 1;
            if (heartbeatRef.current) {
                clearInterval(heartbeatRef.current);
                heartbeatRef.current = null;
            }
            if (connectionTimeoutRef.current) {
                clearTimeout(connectionTimeoutRef.current);
                connectionTimeoutRef.current = null;
            }
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            cleanupResources();
        };
    }, [cleanupResources]);

    return {
        ...state,
        connect,
        disconnect,
    };
}
