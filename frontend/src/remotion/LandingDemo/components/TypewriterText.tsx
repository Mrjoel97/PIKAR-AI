import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

interface TypewriterTextProps {
  text: string;
  startFrame?: number;
  charsPerFrame?: number;
  showCursor?: boolean;
  style?: React.CSSProperties;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  startFrame = 0,
  charsPerFrame = 0.6,
  showCursor = true,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = Math.max(0, frame - startFrame);

  const charsToShow = Math.min(text.length, Math.floor(localFrame * charsPerFrame));
  const visibleText = text.slice(0, charsToShow);
  const isDone = charsToShow >= text.length;

  const cursorOpacity = isDone
    ? interpolate(frame % (fps / 2), [0, fps / 4, fps / 2], [1, 0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 1;

  return (
    <span style={style}>
      {visibleText}
      {showCursor && (
        <span style={{ opacity: cursorOpacity, color: '#0dccf2' }}>{'\u258C'}</span>
      )}
    </span>
  );
};
