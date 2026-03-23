'use client';

import { useState } from 'react';
import { CheckCircle } from 'lucide-react';

interface ApprovalCheckpointCardProps {
  screenName: string;
  onApprove: () => Promise<void>;
  isApproved: boolean;
}

/**
 * GSD-style approval checkpoint card.
 * Uses double-click protection via local clicked state (Phase 7 pattern).
 * Approved state shows a green banner — does NOT auto-advance stage.
 */
export default function ApprovalCheckpointCard({
  screenName,
  onApprove,
  isApproved,
}: ApprovalCheckpointCardProps) {
  const [clicked, setClicked] = useState(false);

  const handleApprove = async () => {
    if (clicked) return;
    setClicked(true);
    try {
      await onApprove();
    } finally {
      setClicked(false);
    }
  };

  if (isApproved) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 p-4">
        <CheckCircle className="h-5 w-5 shrink-0 text-green-600" />
        <div>
          <p className="text-sm font-semibold text-green-800">Screen approved</p>
          <p className="text-xs text-green-700">{screenName} is ready to move forward.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
      <h3 className="text-sm font-semibold text-indigo-900">{screenName}</h3>
      <p className="mt-1 text-xs text-indigo-700">
        Happy with this design? Approve to continue.
      </p>
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          onClick={handleApprove}
          disabled={clicked}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
        >
          Approve screen
        </button>
      </div>
    </div>
  );
}
