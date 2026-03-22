'use client';

import { motion } from 'framer-motion';

interface GenerationProgressProps {
  currentStep: string;
  variantsGenerated: number;
  totalVariants: number;
}

/**
 * Step-by-step progress indicator shown during variant generation.
 * Displays a pulsing status label and a progress bar.
 */
export default function GenerationProgress({
  currentStep,
  variantsGenerated,
  totalVariants,
}: GenerationProgressProps) {
  const pct = totalVariants > 0 ? (variantsGenerated / totalVariants) * 100 : 0;

  return (
    <div
      data-testid="generation-progress"
      className="flex flex-col gap-4 rounded-xl border border-indigo-100 bg-indigo-50 p-6"
    >
      <motion.p
        className="text-sm font-medium text-indigo-700"
        animate={{ opacity: [1, 0.5, 1] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        {currentStep || 'Generating variants...'}
      </motion.p>

      {totalVariants > 0 && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-indigo-500">
            <span>Variants</span>
            <span>
              {variantsGenerated} / {totalVariants}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-indigo-200">
            <motion.div
              className="h-full rounded-full bg-indigo-500"
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
