// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ projectId: 'test-123' }),
}));

vi.mock('@/services/app-builder', () => ({
  listProjectScreens: vi.fn(),
  advanceStage: vi.fn(),
}));

import { listProjectScreens, advanceStage } from '@/services/app-builder';
import VerifyingPage from '@/app/app-builder/[projectId]/verifying/page';

const mockScreens = [
  { id: 'scr-1', project_id: 'test-123', name: 'Home', device_type: 'DESKTOP' as const, page_type: 'landing', page_slug: 'home', order_index: 0, approved: false, stitch_project_id: null, html_url: 'https://example.com/home.html' },
  { id: 'scr-2', project_id: 'test-123', name: 'About', device_type: 'DESKTOP' as const, page_type: 'about', page_slug: 'about', order_index: 1, approved: false, stitch_project_id: null, html_url: 'https://example.com/about.html' },
  { id: 'scr-3', project_id: 'test-123', name: 'Contact', device_type: 'DESKTOP' as const, page_type: 'contact', page_slug: 'contact', order_index: 2, approved: false, stitch_project_id: null, html_url: 'https://example.com/contact.html' },
];

describe('VerifyingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (listProjectScreens as ReturnType<typeof vi.fn>).mockResolvedValue(mockScreens);
    (advanceStage as ReturnType<typeof vi.fn>).mockResolvedValue({ stage: 'shipping' });
  });

  it('renders page tabs for all screens', async () => {
    render(<VerifyingPage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /home/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /about/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /contact/i })).toBeTruthy();
    });
  });

  it('clicking a tab changes the active iframe src', async () => {
    render(<VerifyingPage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /about/i })).toBeTruthy();
    });
    const aboutTab = screen.getByRole('button', { name: /about/i });
    fireEvent.click(aboutTab);
    await waitFor(() => {
      const iframe = screen.getByTitle(/page preview/i) as HTMLIFrameElement;
      expect(iframe.src).toContain('about.html');
    });
  });

  it('renders Approve & Ship button', async () => {
    render(<VerifyingPage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /approve.*ship/i })).toBeTruthy();
    });
  });
});
