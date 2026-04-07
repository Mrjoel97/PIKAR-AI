/**
 * @vitest-environment jsdom
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import React from 'react';
import { RootErrorBoundary } from '../src/components/errors/RootErrorBoundary';

interface ThrowerProps {
  shouldThrow: boolean;
  message?: string;
}

function Thrower({ shouldThrow, message = 'boom' }: ThrowerProps) {
  if (shouldThrow) {
    throw new Error(message);
  }
  return <div>child rendered</div>;
}

describe('RootErrorBoundary', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Silence noisy React error logs from intentional throws and capture calls.
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    cleanup();
  });

  it('renders children when no error is thrown', () => {
    render(
      <RootErrorBoundary>
        <div>ok</div>
      </RootErrorBoundary>,
    );
    expect(screen.getByText('ok')).toBeDefined();
  });

  it('renders fallback UI containing "Something went wrong" when a child throws', () => {
    render(
      <RootErrorBoundary>
        <Thrower shouldThrow={true} />
      </RootErrorBoundary>,
    );
    expect(screen.getByText('Something went wrong')).toBeDefined();
  });

  it('fallback UI contains a "Try again" button', () => {
    render(
      <RootErrorBoundary>
        <Thrower shouldThrow={true} />
      </RootErrorBoundary>,
    );
    const button = screen.getByRole('button', { name: /try again/i });
    expect(button).toBeDefined();
  });

  it('clicking "Try again" resets the boundary state and re-renders children', () => {
    // Use a wrapper component so we can flip the throw flag between renders.
    function Wrapper({ shouldThrow }: { shouldThrow: boolean }) {
      return (
        <RootErrorBoundary>
          <Thrower shouldThrow={shouldThrow} />
        </RootErrorBoundary>
      );
    }

    const { rerender } = render(<Wrapper shouldThrow={true} />);
    expect(screen.getByText('Something went wrong')).toBeDefined();

    // Flip the flag so the child stops throwing, then click Try again to reset.
    rerender(<Wrapper shouldThrow={false} />);
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    expect(screen.getByText('child rendered')).toBeDefined();
  });

  it('fallback UI contains a "Go to Dashboard" link with href="/dashboard"', () => {
    render(
      <RootErrorBoundary>
        <Thrower shouldThrow={true} />
      </RootErrorBoundary>,
    );
    const link = screen.getByRole('link', { name: /go to dashboard/i });
    expect(link).toBeDefined();
    expect(link.getAttribute('href')).toBe('/dashboard');
  });

  it('logs error and component stack to console.error when a child throws', () => {
    render(
      <RootErrorBoundary>
        <Thrower shouldThrow={true} message="kaboom" />
      </RootErrorBoundary>,
    );

    // Find at least one console.error call from the boundary that includes our marker.
    const calls = consoleErrorSpy.mock.calls;
    const boundaryCall = calls.find(
      (args) =>
        typeof args[0] === 'string' &&
        args[0].includes('RootErrorBoundary caught an error'),
    );
    expect(boundaryCall).toBeDefined();
    if (boundaryCall) {
      // The second arg is the Error instance, the third is the component stack string.
      expect(boundaryCall[1]).toBeInstanceOf(Error);
      expect((boundaryCall[1] as Error).message).toBe('kaboom');
      expect(typeof boundaryCall[2]).toBe('string');
      expect((boundaryCall[2] as string).length).toBeGreaterThan(0);
    }
  });

  it('auto-resets when resetKeys prop changes between renders', () => {
    function Wrapper({
      shouldThrow,
      resetKey,
    }: {
      shouldThrow: boolean;
      resetKey: string;
    }) {
      return (
        <RootErrorBoundary resetKeys={[resetKey]}>
          <Thrower shouldThrow={shouldThrow} />
        </RootErrorBoundary>
      );
    }

    const { rerender } = render(<Wrapper shouldThrow={true} resetKey="a" />);
    expect(screen.getByText('Something went wrong')).toBeDefined();

    // Stop throwing AND change the resetKey — boundary should auto-reset without
    // any click on "Try again".
    rerender(<Wrapper shouldThrow={false} resetKey="b" />);

    expect(screen.getByText('child rendered')).toBeDefined();
  });
});
