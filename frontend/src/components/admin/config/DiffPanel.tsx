'use client';

/** Props for DiffPanel */
export interface DiffPanelProps {
  /** Unified diff string returned by the preview-diff endpoint */
  diff: string;
}

/**
 * DiffPanel renders a unified diff with color-coded lines.
 *
 * Lines starting with + are green (additions), - are red (deletions),
 * @@ are blue (hunk headers), and all other lines are gray (context).
 */
export function DiffPanel({ diff }: DiffPanelProps) {
  if (!diff || diff.trim() === '') {
    return (
      <div className="bg-gray-900 rounded-lg p-4 text-sm text-gray-500 italic">
        No changes detected.
      </div>
    );
  }

  const lines = diff.split('\n');

  return (
    <pre className="text-xs font-mono bg-gray-900 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap border border-gray-700 leading-relaxed">
      {lines.map((line, idx) => {
        let colorClass = 'text-gray-300';
        if (line.startsWith('+')) colorClass = 'text-green-400';
        else if (line.startsWith('-')) colorClass = 'text-red-400';
        else if (line.startsWith('@@')) colorClass = 'text-blue-400';

        return (
          <span key={idx} className={`block ${colorClass}`}>
            {line || '\u00A0'}
          </span>
        );
      })}
    </pre>
  );
}
