// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect } from 'vitest';
import {
    determinePersonaPreview,
    PERSONA_INFO,
    type BusinessContextInput,
    type PersonaType,
} from '@/services/onboarding';

/** Helper to build a minimal BusinessContextInput with overrides. */
const makeContext = (
    overrides: Partial<BusinessContextInput> = {}
): BusinessContextInput => ({
    company_name: 'Test Co',
    industry: '',
    description: 'A test company',
    goals: [],
    ...overrides,
});

// ============================================================================
// determinePersonaPreview
// ============================================================================

describe('determinePersonaPreview', () => {
    // ------------------------------------------------------------------
    // 1. Direct ID mappings
    // ------------------------------------------------------------------
    describe('direct ID mappings', () => {
        it.each<[string, PersonaType]>([
            ['solo', 'solopreneur'],
            ['startup', 'startup'],
            ['sme-small', 'sme'],
            ['sme-large', 'sme'],
            ['enterprise', 'enterprise'],
        ])('team_size "%s" maps to "%s"', (teamSize, expected) => {
            expect(determinePersonaPreview(makeContext({ team_size: teamSize }))).toBe(expected);
        });
    });

    // ------------------------------------------------------------------
    // 2. Legacy / pattern mappings
    // ------------------------------------------------------------------
    describe('legacy pattern mappings', () => {
        it.each<[string, PersonaType]>([
            ['200+', 'enterprise'],
            ['500+', 'enterprise'],
            ['51-200', 'sme'],
            ['11-50', 'sme'],
            ['just me', 'solopreneur'],
        ])('team_size containing "%s" maps to "%s"', (teamSize, expected) => {
            expect(determinePersonaPreview(makeContext({ team_size: teamSize }))).toBe(expected);
        });

        it('team_size containing "sme" maps to sme', () => {
            expect(
                determinePersonaPreview(makeContext({ team_size: 'we are sme level' }))
            ).toBe('sme');
        });

        it('team_size containing "solopreneur" maps to solopreneur', () => {
            expect(
                determinePersonaPreview(makeContext({ team_size: 'solopreneur' }))
            ).toBe('solopreneur');
        });

        it('team_size exactly "1" maps to solopreneur', () => {
            expect(determinePersonaPreview(makeContext({ team_size: '1' }))).toBe('solopreneur');
        });
    });

    // ------------------------------------------------------------------
    // 3. Role-based mappings
    // ------------------------------------------------------------------
    describe('role-based mappings', () => {
        it('role containing "freelance" maps to solopreneur', () => {
            expect(
                determinePersonaPreview(makeContext({ role: 'Freelance Designer' }))
            ).toBe('solopreneur');
        });

        it('role containing "consultant" maps to solopreneur', () => {
            expect(
                determinePersonaPreview(makeContext({ role: 'IT Consultant' }))
            ).toBe('solopreneur');
        });
    });

    // ------------------------------------------------------------------
    // 4. Corporate + senior role → enterprise
    // ------------------------------------------------------------------
    describe('corporate industry with senior roles', () => {
        it.each(['VP of Sales', 'Chief Technology Officer', 'Head of Engineering'])(
            'corporate industry + role "%s" maps to enterprise',
            (role) => {
                expect(
                    determinePersonaPreview(
                        makeContext({ industry: 'Corporate Finance', role })
                    )
                ).toBe('enterprise');
            }
        );

        it('corporate industry without senior role does NOT map to enterprise', () => {
            expect(
                determinePersonaPreview(
                    makeContext({ industry: 'Corporate Finance', role: 'Analyst' })
                )
            ).toBe('startup'); // falls through to default
        });
    });

    // ------------------------------------------------------------------
    // 5. Default (empty / unknown) → startup
    // ------------------------------------------------------------------
    describe('default fallback', () => {
        it('returns startup for empty context', () => {
            expect(determinePersonaPreview(makeContext())).toBe('startup');
        });

        it('returns startup for unknown team_size', () => {
            expect(
                determinePersonaPreview(makeContext({ team_size: 'unknown' }))
            ).toBe('startup');
        });

        it('returns startup for random values', () => {
            expect(
                determinePersonaPreview(
                    makeContext({ team_size: 'xyz', role: 'wizard', industry: 'magic' })
                )
            ).toBe('startup');
        });
    });

    // ------------------------------------------------------------------
    // 6. Case insensitivity
    // ------------------------------------------------------------------
    describe('case insensitivity', () => {
        it('"SOLO" maps to solopreneur', () => {
            expect(determinePersonaPreview(makeContext({ team_size: 'SOLO' }))).toBe(
                'solopreneur'
            );
        });

        it('"Enterprise" maps to enterprise', () => {
            expect(
                determinePersonaPreview(makeContext({ team_size: 'Enterprise' }))
            ).toBe('enterprise');
        });

        it('"SME-SMALL" maps to sme', () => {
            expect(
                determinePersonaPreview(makeContext({ team_size: 'SME-SMALL' }))
            ).toBe('sme');
        });

        it('"STARTUP" maps to startup', () => {
            expect(
                determinePersonaPreview(makeContext({ team_size: 'STARTUP' }))
            ).toBe('startup');
        });
    });

    // ------------------------------------------------------------------
    // 7. Edge cases: undefined team_size / role
    // ------------------------------------------------------------------
    describe('edge cases with undefined fields', () => {
        it('handles undefined team_size gracefully', () => {
            expect(
                determinePersonaPreview(makeContext({ team_size: undefined }))
            ).toBe('startup');
        });

        it('handles undefined role gracefully', () => {
            expect(
                determinePersonaPreview(makeContext({ role: undefined }))
            ).toBe('startup');
        });

        it('handles both team_size and role undefined', () => {
            expect(
                determinePersonaPreview(
                    makeContext({ team_size: undefined, role: undefined })
                )
            ).toBe('startup');
        });
    });
});

// ============================================================================
// PERSONA_INFO constant
// ============================================================================

describe('PERSONA_INFO', () => {
    const expectedPersonas: PersonaType[] = ['solopreneur', 'startup', 'sme', 'enterprise'];

    it('defines all 4 persona types', () => {
        expect(Object.keys(PERSONA_INFO)).toHaveLength(4);
        for (const key of expectedPersonas) {
            expect(PERSONA_INFO).toHaveProperty(key);
        }
    });

    it.each(expectedPersonas)('persona "%s" has all required fields', (persona) => {
        const info = PERSONA_INFO[persona];
        expect(info.id).toBe(persona);
        expect(typeof info.title).toBe('string');
        expect(info.title.length).toBeGreaterThan(0);
        expect(typeof info.description).toBe('string');
        expect(info.description.length).toBeGreaterThan(0);
        expect(typeof info.icon).toBe('string');
        expect(info.icon.length).toBeGreaterThan(0);
        expect(typeof info.color).toBe('string');
        expect(info.color.length).toBeGreaterThan(0);
    });
});
