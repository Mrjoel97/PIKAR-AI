/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import SettingsPage from '@/app/settings/page';

// Mock the persona hook
const usePersonaMock = vi.fn();
vi.mock('@/contexts/PersonaContext', () => ({
  usePersona: () => usePersonaMock(),
}));

describe('SettingsPage Persona', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Startup specific settings', () => {
    usePersonaMock.mockReturnValue({ persona: 'startup' });
    render(<SettingsPage />);
    expect(screen.getByText(/Startup Settings/i)).toBeDefined();
  });

  it('renders Enterprise specific settings', () => {
    usePersonaMock.mockReturnValue({ persona: 'enterprise' });
    render(<SettingsPage />);
    expect(screen.getByText(/Enterprise Compliance/i)).toBeDefined();
  });
});
