'use client';

import { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { fetchWithAuth } from '@/services/api';

interface MessageFeedbackProps {
  interactionId: string;
}

/**
 * Thumbs-up / thumbs-down feedback buttons for agent messages.
 *
 * Renders only when a valid interactionId is provided. Clicking a thumb
 * optimistically updates the visual state and fires a POST to the
 * self-improvement feedback endpoint.
 */
export function MessageFeedback({ interactionId }: MessageFeedbackProps) {
  const [selected, setSelected] = useState<'positive' | 'negative' | null>(null);

  // Guard: do not render if interactionId is missing
  if (!interactionId) return null;

  const handleClick = async (rating: 'positive' | 'negative') => {
    // Optimistic UI — update immediately
    setSelected(rating);

    try {
      await fetchWithAuth(`/self-improvement/interactions/${interactionId}/feedback`, {
        method: 'POST',
        body: JSON.stringify({ rating }),
      });
    } catch (err) {
      // Do NOT revert optimistic state — visual feedback matters more
      console.error('[MessageFeedback] Failed to submit feedback:', err);
    }
  };

  return (
    <div className="mt-1 flex items-center gap-1">
      <button
        type="button"
        aria-label="Rate positive"
        aria-pressed={selected === 'positive'}
        onClick={() => handleClick('positive')}
        className={`rounded-md p-1 transition-colors ${
          selected === 'positive'
            ? 'text-emerald-500'
            : 'text-slate-300 hover:text-slate-500'
        }`}
      >
        <ThumbsUp size={16} fill={selected === 'positive' ? 'currentColor' : 'none'} />
      </button>
      <button
        type="button"
        aria-label="Rate negative"
        aria-pressed={selected === 'negative'}
        onClick={() => handleClick('negative')}
        className={`rounded-md p-1 transition-colors ${
          selected === 'negative'
            ? 'text-rose-500'
            : 'text-slate-300 hover:text-slate-500'
        }`}
      >
        <ThumbsDown size={16} fill={selected === 'negative' ? 'currentColor' : 'none'} />
      </button>
    </div>
  );
}
