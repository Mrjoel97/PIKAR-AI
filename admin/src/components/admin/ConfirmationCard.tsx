'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import type { ConfirmationData } from '@/hooks/useAdminChat';

/**
 * ConfirmationCard renders an action confirmation prompt from the AdminAgent.
 * The Confirm button is colour-coded by risk level and disabled after first click
 * to prevent duplicate submissions.
 */
interface ConfirmationCardProps {
  confirmation: ConfirmationData;
  onConfirm: (token: string) => void;
  onReject: () => void;
  isProcessing: boolean;
}

const riskColors: Record<string, { badge: string; button: string }> = {
  high: {
    badge: 'bg-red-900 text-red-300 border border-red-700',
    button: 'bg-red-600 hover:bg-red-700 disabled:bg-red-800 text-white',
  },
  medium: {
    badge: 'bg-amber-900 text-amber-300 border border-amber-700',
    button: 'bg-amber-600 hover:bg-amber-700 disabled:bg-amber-800 text-white',
  },
  low: {
    badge: 'bg-green-900 text-green-300 border border-green-700',
    button: 'bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white',
  },
};

export function ConfirmationCard({
  confirmation,
  onConfirm,
  onReject,
  isProcessing,
}: ConfirmationCardProps) {
  const [clicked, setClicked] = useState(false);
  const { token, action_details } = confirmation;
  const risk = action_details.risk_level ?? 'medium';
  const colors = riskColors[risk] ?? riskColors.medium;
  const isDisabled = isProcessing || clicked;

  const handleConfirm = () => {
    if (isDisabled) return;
    setClicked(true);
    onConfirm(token);
  };

  return (
    <div className="my-3 rounded-xl border border-amber-700 bg-amber-950/40 p-4 max-w-sm">
      {/* Header */}
      <div className="flex items-start gap-2 mb-3">
        <AlertTriangle size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-amber-200">Confirmation Required</p>
          <p className="text-sm font-medium text-gray-100 mt-0.5">{action_details.action}</p>
        </div>
        {/* Risk level badge */}
        <span
          className={`flex-shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${colors.badge}`}
        >
          {risk}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-300 mb-4 leading-relaxed">{action_details.description}</p>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onReject}
          disabled={isProcessing}
          className="flex-1 px-3 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isDisabled}
          className={`flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed ${colors.button}`}
        >
          {isDisabled && clicked ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Confirming…
            </>
          ) : (
            'Confirm'
          )}
        </button>
      </div>
    </div>
  );
}
