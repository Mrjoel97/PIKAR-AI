// @vitest-environment jsdom
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import IterationPanel from '@/components/app-builder/IterationPanel';

describe('IterationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a textarea and submit button', () => {
    render(<IterationPanel onSubmit={vi.fn()} isIterating={false} />);
    expect(screen.getByRole('textbox')).toBeTruthy();
    expect(screen.getByRole('button', { name: /apply changes/i })).toBeTruthy();
  });

  it('submit button is disabled when textarea is empty', () => {
    render(<IterationPanel onSubmit={vi.fn()} isIterating={false} />);
    const button = screen.getByRole('button', { name: /apply changes/i }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it('submit button is disabled during iteration (isIterating=true)', () => {
    render(<IterationPanel onSubmit={vi.fn()} isIterating={true} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Make the button bigger' } });
    const button = screen.getByRole('button') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it('calls onSubmit with textarea value when submitted', () => {
    const onSubmit = vi.fn();
    render(<IterationPanel onSubmit={onSubmit} isIterating={false} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Make the button bigger' } });
    const button = screen.getByRole('button', { name: /apply changes/i });
    fireEvent.click(button);
    expect(onSubmit).toHaveBeenCalledWith('Make the button bigger');
  });
});
