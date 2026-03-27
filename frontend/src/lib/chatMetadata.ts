// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export interface MessageMetadata {
  agent?: string;
  confidence?: number;
  tool_calls?: string[];
  widgets?: Record<string, unknown>[];
  [key: string]: unknown;
}

/**
 * Extract metadata from an SSE event object.
 */
export function extractMessageMetadataFromEvent(
  event: Record<string, unknown>,
): MessageMetadata | undefined {
  const result = event?.result as Record<string, unknown> | undefined;
  const metadata = (event?.metadata ?? result?.metadata) as
    | MessageMetadata
    | undefined;
  if (!metadata || typeof metadata !== 'object') return undefined;
  return metadata;
}

/**
 * Extract metadata from A2A content parts array.
 */
export function extractMessageMetadataFromParts(
  parts: unknown[] | undefined,
): MessageMetadata | undefined {
  if (!Array.isArray(parts)) return undefined;
  for (const part of parts) {
    if (
      typeof part === 'object' &&
      part !== null &&
      'metadata' in part &&
      typeof (part as Record<string, unknown>).metadata === 'object'
    ) {
      return (part as Record<string, unknown>).metadata as MessageMetadata;
    }
  }
  return undefined;
}
