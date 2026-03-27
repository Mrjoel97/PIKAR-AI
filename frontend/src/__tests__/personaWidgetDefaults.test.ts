// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect } from 'vitest';
import {
  getDefaultWidgetsForPersona,
  PERSONA_DEFAULT_WIDGETS,
} from '@/components/personas/personaWidgetDefaults';

describe('personaWidgetDefaults', () => {
  describe('PERSONA_DEFAULT_WIDGETS', () => {
    it('has entries for all four personas', () => {
      expect(PERSONA_DEFAULT_WIDGETS).toHaveProperty('solopreneur');
      expect(PERSONA_DEFAULT_WIDGETS).toHaveProperty('startup');
      expect(PERSONA_DEFAULT_WIDGETS).toHaveProperty('sme');
      expect(PERSONA_DEFAULT_WIDGETS).toHaveProperty('enterprise');
    });
  });

  describe('getDefaultWidgetsForPersona', () => {
    it('returns exactly 4 widgets for solopreneur with correct types', () => {
      const widgets = getDefaultWidgetsForPersona('solopreneur');
      expect(widgets).toHaveLength(4);
      const types = widgets.map((w) => w.type);
      expect(types).toContain('revenue_chart');
      expect(types).toContain('morning_briefing');
      expect(types).toContain('kanban_board');
      expect(types).toContain('campaign_hub');
    });

    it('returns exactly 4 widgets for startup with correct types', () => {
      const widgets = getDefaultWidgetsForPersona('startup');
      expect(widgets).toHaveLength(4);
      const types = widgets.map((w) => w.type);
      expect(types).toContain('revenue_chart');
      expect(types).toContain('morning_briefing');
      expect(types).toContain('initiative_dashboard');
      expect(types).toContain('workflow_observability');
    });

    it('returns exactly 4 widgets for sme with correct types', () => {
      const widgets = getDefaultWidgetsForPersona('sme');
      expect(widgets).toHaveLength(4);
      const types = widgets.map((w) => w.type);
      expect(types).toContain('department_activity');
      expect(types).toContain('morning_briefing');
      expect(types).toContain('revenue_chart');
      expect(types).toContain('workflow_observability');
    });

    it('returns exactly 4 widgets for enterprise with correct types', () => {
      const widgets = getDefaultWidgetsForPersona('enterprise');
      expect(widgets).toHaveLength(4);
      const types = widgets.map((w) => w.type);
      expect(types).toContain('department_activity');
      expect(types).toContain('morning_briefing');
      expect(types).toContain('revenue_chart');
      expect(types).toContain('boardroom');
    });

    it('returns empty array for null persona', () => {
      const widgets = getDefaultWidgetsForPersona(null);
      expect(widgets).toEqual([]);
    });

    it('returns empty array for unknown persona string', () => {
      const widgets = getDefaultWidgetsForPersona('unknown');
      expect(widgets).toEqual([]);
    });

    it('every widget has a non-empty title string', () => {
      const personas = ['solopreneur', 'startup', 'sme', 'enterprise'] as const;
      for (const persona of personas) {
        const widgets = getDefaultWidgetsForPersona(persona);
        for (const widget of widgets) {
          expect(typeof widget.title).toBe('string');
          expect(widget.title!.length).toBeGreaterThan(0);
        }
      }
    });

    it('every widget has a data object (not null)', () => {
      const personas = ['solopreneur', 'startup', 'sme', 'enterprise'] as const;
      for (const persona of personas) {
        const widgets = getDefaultWidgetsForPersona(persona);
        for (const widget of widgets) {
          expect(widget.data).toBeDefined();
          expect(typeof widget.data).toBe('object');
          expect(widget.data).not.toBeNull();
        }
      }
    });

    it('every widget has dismissible set to true', () => {
      const personas = ['solopreneur', 'startup', 'sme', 'enterprise'] as const;
      for (const persona of personas) {
        const widgets = getDefaultWidgetsForPersona(persona);
        for (const widget of widgets) {
          expect(widget.dismissible).toBe(true);
        }
      }
    });
  });
});
