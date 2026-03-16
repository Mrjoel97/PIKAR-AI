import { useEffect, useRef, useCallback } from 'react';

interface SwipeGestureOptions {
  /** Called when swipe-right from left edge is detected (open) */
  onSwipeOpen: () => void;
  /** Called when swipe-left is detected (close) */
  onSwipeClose: () => void;
  /** Whether the sidebar is currently open */
  isOpen: boolean;
  /** Whether gesture detection is enabled (disable on desktop) */
  enabled: boolean;
  /** Max X position from left edge to start swipe-open (default: 20px) */
  edgeThreshold?: number;
  /** Min horizontal distance to trigger (default: 75px) */
  minSwipeDistance?: number;
}

export function useSwipeGesture({
  onSwipeOpen,
  onSwipeClose,
  isOpen,
  enabled,
  edgeThreshold = 20,
  minSwipeDistance = 75,
}: SwipeGestureOptions) {
  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const touchCurrent = useRef<{ x: number } | null>(null);

  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      if (!enabled) return;
      const touch = e.touches[0];
      touchStart.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
      touchCurrent.current = { x: touch.clientX };
    },
    [enabled]
  );

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!enabled || !touchStart.current) return;
      touchCurrent.current = { x: e.touches[0].clientX };
    },
    [enabled]
  );

  const handleTouchEnd = useCallback(() => {
    if (!enabled || !touchStart.current || !touchCurrent.current) {
      touchStart.current = null;
      touchCurrent.current = null;
      return;
    }

    const deltaX = touchCurrent.current.x - touchStart.current.x;
    const startX = touchStart.current.x;

    if (!isOpen && startX <= edgeThreshold && deltaX >= minSwipeDistance) {
      // Swipe right from left edge → open
      onSwipeOpen();
    } else if (isOpen && deltaX <= -minSwipeDistance) {
      // Swipe left while open → close
      onSwipeClose();
    }

    touchStart.current = null;
    touchCurrent.current = null;
  }, [enabled, isOpen, edgeThreshold, minSwipeDistance, onSwipeOpen, onSwipeClose]);

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchmove', handleTouchMove, { passive: true });
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [enabled, handleTouchStart, handleTouchMove, handleTouchEnd]);
}
