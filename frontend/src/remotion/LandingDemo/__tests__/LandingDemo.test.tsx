import { describe, it, expect } from 'vitest';
import { PERSONA_SCENES } from '../data/personas';
import {
  VIDEO_FPS,
  VIDEO_WIDTH,
  VIDEO_HEIGHT,
  INTRO_DURATION,
  PERSONA_DURATION,
  EXECUTIVE_DURATION,
  OUTRO_DURATION,
  TRANSITION_FRAMES,
  COLORS,
  VOICEOVER_LINES,
} from '../constants';
import { TOTAL_DURATION_FRAMES } from '../duration';

describe('LandingDemo constants', () => {
  it('has valid video dimensions', () => {
    expect(VIDEO_WIDTH).toBe(1920);
    expect(VIDEO_HEIGHT).toBe(1080);
    expect(VIDEO_FPS).toBe(30);
  });

  it('has valid scene durations', () => {
    expect(INTRO_DURATION).toBeGreaterThan(0);
    expect(PERSONA_DURATION).toBeGreaterThan(0);
    expect(EXECUTIVE_DURATION).toBeGreaterThanOrEqual(PERSONA_DURATION);
    expect(OUTRO_DURATION).toBeGreaterThan(0);
    expect(TRANSITION_FRAMES).toBeGreaterThan(0);
  });

  it('has cinematic scene durations', () => {
    expect(INTRO_DURATION).toBe(12);
    expect(PERSONA_DURATION).toBe(30);
    expect(EXECUTIVE_DURATION).toBe(30);
    expect(OUTRO_DURATION).toBe(10);
  });

  it('has all brand colors defined', () => {
    expect(COLORS.bgDark).toBeDefined();
    expect(COLORS.accent).toBeDefined();
    expect(COLORS.solopreneur).toBeDefined();
    expect(COLORS.startup).toBeDefined();
    expect(COLORS.sme).toBeDefined();
    expect(COLORS.enterprise).toBeDefined();
  });

  it('has voiceover narration lines', () => {
    expect(VOICEOVER_LINES).toHaveLength(4);
    for (const line of VOICEOVER_LINES) {
      expect(typeof line).toBe('string');
      expect(line.length).toBeGreaterThan(0);
    }
  });
});

describe('LandingDemo persona data', () => {
  it('has exactly 4 persona scenes', () => {
    expect(PERSONA_SCENES).toHaveLength(4);
  });

  it('includes all expected personas', () => {
    const ids = PERSONA_SCENES.map((p) => p.id);
    expect(ids).toContain('solopreneur');
    expect(ids).toContain('startup');
    expect(ids).toContain('sme');
    expect(ids).toContain('enterprise');
  });

  it('each persona has required fields', () => {
    for (const persona of PERSONA_SCENES) {
      expect(persona.title).toBeTruthy();
      expect(persona.subtitle).toBeTruthy();
      expect(persona.emoji).toBeTruthy();
      expect(persona.gradient).toHaveLength(2);
      expect(persona.tierFeatures).toHaveLength(4);
      expect(persona.agents.length).toBeGreaterThanOrEqual(3);
      expect(persona.greeting).toBeTruthy();
      expect(persona.chatMessages.length).toBeGreaterThanOrEqual(3);
      expect(persona.caption).toBeTruthy();
    }
  });

  it('each persona has descriptive tier features', () => {
    for (const persona of PERSONA_SCENES) {
      for (const feature of persona.tierFeatures) {
        expect(typeof feature).toBe('string');
        expect(feature.length).toBeGreaterThan(5);
      }
    }
  });

  it('each persona has a greeting string', () => {
    for (const persona of PERSONA_SCENES) {
      expect(typeof persona.greeting).toBe('string');
      expect(persona.greeting.length).toBeGreaterThan(10);
    }
  });

  it('executive persona has the most agents', () => {
    const exec = PERSONA_SCENES.find((p) => p.id === 'enterprise')!;
    const others = PERSONA_SCENES.filter((p) => p.id !== 'enterprise');
    for (const other of others) {
      expect(exec.agents.length).toBeGreaterThanOrEqual(other.agents.length);
    }
  });

  it('chat messages have valid delay ordering', () => {
    for (const persona of PERSONA_SCENES) {
      const delays = persona.chatMessages.map((m) => m.delaySeconds);
      for (let i = 1; i < delays.length; i++) {
        expect(delays[i]).toBeGreaterThanOrEqual(delays[i - 1]);
      }
    }
  });
});

describe('LandingDemo composition', () => {
  it('exports TOTAL_DURATION_FRAMES as a positive number', () => {
    expect(TOTAL_DURATION_FRAMES).toBeGreaterThan(0);
  });

  it('total duration matches expected calculation', () => {
    const sceneDurations = [
      INTRO_DURATION,
      ...PERSONA_SCENES.map((p) =>
        p.id === 'enterprise' ? EXECUTIVE_DURATION : PERSONA_DURATION,
      ),
      OUTRO_DURATION,
    ];
    const expected =
      sceneDurations.reduce((sum, d) => sum + d * VIDEO_FPS, 0) -
      (sceneDurations.length - 1) * TRANSITION_FRAMES;
    expect(TOTAL_DURATION_FRAMES).toBe(expected);
  });

  it('total duration is approximately 2.5 minutes', () => {
    const totalSeconds = TOTAL_DURATION_FRAMES / VIDEO_FPS;
    // 12 + 30*3 + 30 + 10 = 142s minus transitions
    expect(totalSeconds).toBeGreaterThan(130);
    expect(totalSeconds).toBeLessThan(150);
  });
});
