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
    expect(EXECUTIVE_DURATION).toBeGreaterThan(PERSONA_DURATION);
    expect(OUTRO_DURATION).toBeGreaterThan(0);
    expect(TRANSITION_FRAMES).toBeGreaterThan(0);
  });

  it('has all brand colors defined', () => {
    expect(COLORS.bgDark).toBeDefined();
    expect(COLORS.accent).toBeDefined();
    expect(COLORS.solopreneur).toBeDefined();
    expect(COLORS.founder).toBeDefined();
    expect(COLORS.owner).toBeDefined();
    expect(COLORS.executive).toBeDefined();
  });
});

describe('LandingDemo persona data', () => {
  it('has exactly 4 persona scenes', () => {
    expect(PERSONA_SCENES).toHaveLength(4);
  });

  it('includes all expected personas', () => {
    const ids = PERSONA_SCENES.map((p) => p.id);
    expect(ids).toContain('solopreneur');
    expect(ids).toContain('founder');
    expect(ids).toContain('owner');
    expect(ids).toContain('executive');
  });

  it('each persona has required fields', () => {
    for (const persona of PERSONA_SCENES) {
      expect(persona.title).toBeTruthy();
      expect(persona.subtitle).toBeTruthy();
      expect(persona.emoji).toBeTruthy();
      expect(persona.gradient).toHaveLength(2);
      expect(persona.agents.length).toBeGreaterThanOrEqual(3);
      expect(persona.chatMessages.length).toBeGreaterThanOrEqual(3);
      expect(persona.caption).toBeTruthy();
    }
  });

  it('executive persona has the most agents', () => {
    const exec = PERSONA_SCENES.find((p) => p.id === 'executive')!;
    const others = PERSONA_SCENES.filter((p) => p.id !== 'executive');
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
        p.id === 'executive' ? EXECUTIVE_DURATION : PERSONA_DURATION
      ),
      OUTRO_DURATION,
    ];
    const expected =
      sceneDurations.reduce((sum, d) => sum + d * VIDEO_FPS, 0) -
      (sceneDurations.length - 1) * TRANSITION_FRAMES;
    expect(TOTAL_DURATION_FRAMES).toBe(expected);
  });

  it('total duration is approximately 2 minutes', () => {
    const totalSeconds = TOTAL_DURATION_FRAMES / VIDEO_FPS;
    // 8 + 25*3 + 30 + 8 = 121s minus transitions
    expect(totalSeconds).toBeGreaterThan(100);
    expect(totalSeconds).toBeLessThan(130);
  });
});
