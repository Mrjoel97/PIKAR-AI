// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Templated prompts for vault → agent actions.
 *
 * Each action turns a list of selected vault assets into a prefilled chat
 * message that the user can review and send. Templates live here so they
 * are easy to tune without touching the UI.
 */

export type VaultActionId = 'post_social' | 'use_campaign' | 'draft_email' | 'custom';

export interface VaultActionItem {
  id: string;
  filename: string;
  file_type: string | null;
  signed_url: string;
}

function renderAssetList(items: VaultActionItem[]): string {
  return items
    .map((item) => `- ${item.filename} (${item.file_type ?? 'unknown'}): ${item.signed_url}`)
    .join('\n');
}

export function buildVaultActionPrompt(
  action: VaultActionId,
  items: VaultActionItem[],
): string {
  const list = renderAssetList(items);

  switch (action) {
    case 'post_social':
      return [
        'Please post these assets to social media. Suggest captions for LinkedIn and X, and recommend the best platform for each asset.',
        '',
        'Assets:',
        list,
      ].join('\n');

    case 'use_campaign':
      return [
        'Build a marketing campaign that uses these assets. Recommend the channel mix, sequencing, and key messaging.',
        '',
        'Assets:',
        list,
      ].join('\n');

    case 'draft_email':
      return [
        'Draft an email using these assets as inline images or attachments. Ask me who the recipient list is and what the goal of the email is.',
        '',
        'Assets:',
        list,
      ].join('\n');

    case 'custom':
      return ['Assets:', list].join('\n');

    default:
      throw new Error(`Unknown vault action: ${String(action)}`);
  }
}
