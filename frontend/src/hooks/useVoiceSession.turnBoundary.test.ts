import { describe, expect, it } from 'vitest'

import { shouldEmitAudioStreamEnd } from './useVoiceSession'

describe('shouldEmitAudioStreamEnd', () => {
    it('returns false before the silence window elapses', () => {
        expect(
            shouldEmitAudioStreamEnd({
                nowMs: 1_000,
                lastSpeechAtMs: 500,
                hasSpeechInTurn: true,
                audioStreamEnded: false,
                silenceWindowMs: 700,
            }),
        ).toBe(false)
    })

    it('returns true once the user has paused long enough after speaking', () => {
        expect(
            shouldEmitAudioStreamEnd({
                nowMs: 1_300,
                lastSpeechAtMs: 500,
                hasSpeechInTurn: true,
                audioStreamEnded: false,
                silenceWindowMs: 700,
            }),
        ).toBe(true)
    })

    it('returns false when the turn already ended or no speech was captured', () => {
        expect(
            shouldEmitAudioStreamEnd({
                nowMs: 1_300,
                lastSpeechAtMs: 500,
                hasSpeechInTurn: false,
                audioStreamEnded: false,
                silenceWindowMs: 700,
            }),
        ).toBe(false)

        expect(
            shouldEmitAudioStreamEnd({
                nowMs: 1_300,
                lastSpeechAtMs: 500,
                hasSpeechInTurn: true,
                audioStreamEnded: true,
                silenceWindowMs: 700,
            }),
        ).toBe(false)
    })
})
