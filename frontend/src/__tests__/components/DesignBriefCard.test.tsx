// @vitest-environment jsdom
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DesignBriefCard } from '@/components/app-builder/DesignBriefCard';
import type { DesignBrief } from '@/types/app-builder';

const mockBrief: DesignBrief = {
  colors: [
    { hex: '#1a1a2e', name: 'Navy' },
    { hex: '#e94560', name: 'Crimson' },
    { hex: '#f5f5f5', name: 'Ivory' },
  ],
  typography: { heading: 'Inter', body: 'Source Sans', scale: '1.25' },
  spacing: { base_unit: '4px', section_padding: '64px', card_padding: '24px' },
  raw_markdown: '# Design System\n\nColors: Navy, Crimson, Ivory\n',
};

describe('DesignBriefCard', () => {
  it('renders color swatches from design data', () => {
    render(<DesignBriefCard brief={mockBrief} onChange={vi.fn()} />);
    const swatches = screen.getAllByTestId('color-swatch');
    expect(swatches.length).toBe(3);
    // Each swatch has backgroundColor set from hex
    expect((swatches[0] as HTMLElement).style.backgroundColor).toBeTruthy();
  });

  it('renders typography fields', () => {
    render(<DesignBriefCard brief={mockBrief} onChange={vi.fn()} />);
    expect(screen.getByDisplayValue('Inter')).toBeTruthy();
    expect(screen.getByDisplayValue('Source Sans')).toBeTruthy();
  });

  it('calls onChange when color hex is edited', () => {
    const handleChange = vi.fn();
    render(<DesignBriefCard brief={mockBrief} onChange={handleChange} />);
    // Find the first color hex input by value
    const hexInput = screen.getByDisplayValue('#1a1a2e');
    fireEvent.change(hexInput, { target: { value: '#ffffff' } });
    expect(handleChange).toHaveBeenCalledOnce();
    const updated: DesignBrief = handleChange.mock.calls[0][0];
    expect(updated.colors[0].hex).toBe('#ffffff');
  });
});
