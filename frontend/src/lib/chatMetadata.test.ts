// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, expect, it } from 'vitest';

import { extractMessageMetadataFromEvent } from './chatMetadata';

describe('chatMetadata', () => {
  it('extracts structured research metadata from function responses', () => {
    const metadata = extractMessageMetadataFromEvent({
      content: {
        parts: [
          {
            function_response: {
              response: {
                result: {
                  topic: 'AI copilots for SMBs',
                  research_type: 'market',
                  confidence_score: 0.84,
                  quick_answer: 'Demand is growing quickly in SMB operations.',
                  citations: [
                    {
                      number: 1,
                      title: 'Example Source',
                      url: 'https://example.com/source',
                      snippet: 'Useful market evidence.',
                    },
                  ],
                  contradictions: ['Two sources disagree on market size.'],
                  recommended_next_questions: ['What changed most recently in 2025 and 2026?'],
                  key_findings: ['SMB adoption is increasing.'],
                },
              },
            },
          },
        ],
      },
    });

    expect(metadata?.research?.topic).toBe('AI copilots for SMBs');
    expect(metadata?.research?.confidenceScore).toBe(0.84);
    expect(metadata?.research?.citations[0].url).toBe('https://example.com/source');
    expect(metadata?.research?.contradictions[0]).toContain('market size');
  });

  it('returns undefined for non-research tool responses', () => {
    const metadata = extractMessageMetadataFromEvent({
      content: {
        parts: [
          {
            function_response: {
              response: {
                result: {
                  success: true,
                  message: 'Nothing to see here',
                },
              },
            },
          },
        ],
      },
    });

    expect(metadata).toBeUndefined();
  });
});
