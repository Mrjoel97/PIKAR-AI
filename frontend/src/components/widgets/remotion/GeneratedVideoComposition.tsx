/**
 * Server-side render: Updated for "Pro" multi-scene video generation.
 * Supports:
 * - Sequential scenes with cross-dissolve transitions
 * - Video clips (Veo) or static images
 * - Background audio loops
 * - Dynamic text overlays with animations
 */
import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  Img,
  interpolate,
  Video,
  Audio,
  spring,
} from 'remotion';

// --- Types ---
export interface CaptionCue {
  text: string;
  startFrame: number;
  endFrame: number;
}

export interface SceneTransition {
  type?: 'fade' | 'slide-left' | 'slide-right';
  durationFrames?: number;
}

export interface SceneInput {
  text: string;
  duration: number; // in seconds
  imageUrl?: string;
  videoUrl?: string; // Veo video URL
  voiceoverUrl?: string; // TTS audio URL
  captions?: CaptionCue[];
  transition?: SceneTransition;
}

export interface GeneratedVideoInputProps {
  scenes: SceneInput[];
  fps?: number;
  durationInFrames?: number; // Added for metadata
  bgMusicUrl?: string; // Background music loop
  bgMusicVolume?: number;
  voiceoverVolume?: number;
}

const TRANSITION_DURATION = 15; // frames

// --- Styles ---
const MODERN_STYLE = {
  bg: '#1a1a2e',
  color: '#ffffff',
  fontFamily: 'Inter, system-ui, sans-serif',
};

// --- Components ---

function SceneContent({
  text,
  imageUrl,
  videoUrl,
  voiceoverUrl,
  captions,
  transitionDurationFrames,
  transitionType,
  isFirstScene,
  isLastScene,
  voiceoverVolume = 1,
  durationInFrames,
}: SceneInput & {
  durationInFrames: number;
  transitionDurationFrames: number;
  transitionType: 'fade' | 'slide-left' | 'slide-right';
  isFirstScene: boolean;
  isLastScene: boolean;
  voiceoverVolume?: number;
}) {
  const frame = useCurrentFrame();
  const fps = 30;

  // Text Animation (Slide up & Fade in)
  const textEntrance = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const textTranslateY = interpolate(textEntrance, [0, 1], [50, 0]);
  const textOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

  // Ken Burns effect for static images
  const isStaticImage = !!imageUrl && !videoUrl;
  const targetScale = isStaticImage ? 1.15 : 1.05;
  const scale = interpolate(frame, [0, durationInFrames], [1, targetScale], {
    extrapolateRight: 'clamp',
  });
  const panX = isStaticImage ? interpolate(frame, [0, durationInFrames], [0, -20]) : 0;
  const panY = isStaticImage ? interpolate(frame, [0, durationInFrames], [0, -10]) : 0;

  const inProgress = transitionDurationFrames > 0
    ? interpolate(frame, [0, transitionDurationFrames], [0, 1], { extrapolateRight: 'clamp' })
    : 1;
  const outProgress = transitionDurationFrames > 0
    ? interpolate(
      frame,
      [Math.max(0, durationInFrames - transitionDurationFrames), durationInFrames],
      [1, 0],
      { extrapolateLeft: 'clamp' },
    )
    : 1;

  const entryOpacity = isFirstScene ? 1 : inProgress;
  const exitOpacity = isLastScene ? 1 : outProgress;
  const sceneOpacity = Math.max(0, Math.min(1, entryOpacity * exitOpacity));

  const slideInOffset = !isFirstScene
    ? interpolate(inProgress, [0, 1], [transitionType === 'slide-left' ? 60 : -60, 0])
    : 0;
  const slideOutOffset = !isLastScene
    ? interpolate(
      outProgress,
      [0, 1],
      [transitionType === 'slide-left' ? -60 : 60, 0],
    )
    : 0;

  const translateX = transitionType === 'fade' ? 0 : slideInOffset + slideOutOffset;

  const activeCaptions = (captions || []).filter(
    (cue) => frame >= cue.startFrame && frame <= cue.endFrame,
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: MODERN_STYLE.bg,
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
        opacity: sceneOpacity,
        transform: `translateX(${translateX}px)`,
      }}
    >
      {/* Background Media */}
      <AbsoluteFill>
        {videoUrl ? (
          <Video
            src={videoUrl}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${scale})`,
            }}
            // Mute video if we have separate bg music/voiceover to avoid clash, or keep it.
            // Assuming Veo videos are silent for now.
            muted={true}
          />
        ) : imageUrl ? (
          <Img
            src={imageUrl}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${scale}) translate(${panX}px, ${panY}px)`,
            }}
          />
        ) : null}

        {/* Dark overlay for text readability */}
        <AbsoluteFill style={{ backgroundColor: 'rgba(0,0,0,0.3)' }} />
      </AbsoluteFill>

      {/* Voiceover (if provided) */}
      {voiceoverUrl && <Audio src={voiceoverUrl} volume={voiceoverVolume} />}

      {/* Text Overlay */}
      <h1
        style={{
          color: MODERN_STYLE.color,
          fontFamily: MODERN_STYLE.fontFamily,
          fontSize: 70,
          fontWeight: 700,
          textAlign: 'center',
          maxWidth: '80%',
          opacity: textOpacity,
          transform: `translateY(${textTranslateY}px)`,
          zIndex: 1,
          textShadow: '0 4px 12px rgba(0,0,0,0.6)',
        }}
      >
        {text}
      </h1>

      {activeCaptions.length > 0 && (
        <div
          style={{
            position: 'absolute',
            bottom: 72,
            left: '8%',
            right: '8%',
            textAlign: 'center',
            color: '#fff',
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: 42,
            fontWeight: 600,
            textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)',
            zIndex: 2,
          }}
        >
          {activeCaptions[0]?.text}
        </div>
      )}
    </AbsoluteFill>
  );
}

export function GeneratedVideoComposition({
  scenes,
  fps = 30,
  bgMusicUrl,
  bgMusicVolume = 0.5,
  voiceoverVolume = 1,
}: GeneratedVideoInputProps) {
  let currentStartFrame = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Background Music Loop */}
      {bgMusicUrl && (
        <Audio
          src={bgMusicUrl}
          loop
          volume={bgMusicVolume}
        />
      )}

      {/* Scenes Sequence */}
      {scenes.map((scene, i) => {
        const sceneDurationFrames = Math.round(scene.duration * fps);
        const transitionDurationFrames = Math.min(
          sceneDurationFrames - 1,
          Math.max(0, scene.transition?.durationFrames ?? TRANSITION_DURATION),
        );
        const myStart = i === 0 ? currentStartFrame : currentStartFrame - transitionDurationFrames;
        currentStartFrame = myStart + sceneDurationFrames;

        return (
          <Sequence
            key={i}
            from={myStart}
            durationInFrames={sceneDurationFrames}
          >
            <SceneContent
              {...scene}
              durationInFrames={sceneDurationFrames}
              transitionDurationFrames={transitionDurationFrames}
              transitionType={scene.transition?.type ?? 'fade'}
              isFirstScene={i === 0}
              isLastScene={i === scenes.length - 1}
              voiceoverVolume={voiceoverVolume}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
}
