// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { DeviceType } from '@/types/app-builder';

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
  },
}));

import DevicePreviewFrame from '@/components/app-builder/DevicePreviewFrame';

describe('DevicePreviewFrame', () => {
  const onDeviceChange = vi.fn();
  const htmlUrl = 'https://example.com/screen.html';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders an iframe with src equal to the provided htmlUrl', () => {
    render(
      <DevicePreviewFrame
        htmlUrl={htmlUrl}
        device="DESKTOP"
        onDeviceChange={onDeviceChange}
      />,
    );

    const iframe = screen.getByTitle(/preview/i) as HTMLIFrameElement;
    expect(iframe.src).toBe(htmlUrl);
  });

  it('renders 3 device tab buttons (Desktop, Mobile, Tablet)', () => {
    render(
      <DevicePreviewFrame
        htmlUrl={htmlUrl}
        device="DESKTOP"
        onDeviceChange={onDeviceChange}
      />,
    );

    expect(screen.getByRole('button', { name: /desktop/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /mobile/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /tablet/i })).toBeTruthy();
  });

  it('clicking a device tab calls onDeviceChange with the device type', () => {
    render(
      <DevicePreviewFrame
        htmlUrl={htmlUrl}
        device="DESKTOP"
        onDeviceChange={onDeviceChange}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /mobile/i }));
    expect(onDeviceChange).toHaveBeenCalledWith('MOBILE' as DeviceType);
  });

  it('iframe has sandbox="allow-scripts allow-same-origin" attribute', () => {
    render(
      <DevicePreviewFrame
        htmlUrl={htmlUrl}
        device="DESKTOP"
        onDeviceChange={onDeviceChange}
      />,
    );

    const iframe = screen.getByTitle(/preview/i) as HTMLIFrameElement;
    expect(iframe.getAttribute('sandbox')).toBe('allow-scripts allow-same-origin');
  });
});
