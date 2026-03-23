// @vitest-environment jsdom
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SitemapCard } from '@/components/app-builder/SitemapCard';

const testSitemap = [
  { page: 'home', title: 'Home', sections: ['hero'], device_targets: ['desktop'] },
  { page: 'about', title: 'About', sections: ['team'], device_targets: ['desktop'] },
  { page: 'contact', title: 'Contact', sections: ['form'], device_targets: ['desktop'] },
];

describe('SitemapCard — reorder and remove', () => {
  it('renders all sitemap page titles', () => {
    render(<SitemapCard sitemap={testSitemap} onChange={() => {}} />);
    expect(screen.getByDisplayValue('Home')).toBeTruthy();
    expect(screen.getByDisplayValue('About')).toBeTruthy();
    expect(screen.getByDisplayValue('Contact')).toBeTruthy();
  });

  it('remove button calls onChange with page removed', () => {
    const onChange = vi.fn();
    render(<SitemapCard sitemap={testSitemap} onChange={onChange} />);
    const removeBtn = screen.getByRole('button', { name: /remove about/i });
    fireEvent.click(removeBtn);
    expect(onChange).toHaveBeenCalledTimes(1);
    const updated = onChange.mock.calls[0][0];
    expect(updated).toHaveLength(2);
    expect(updated.find((p: { page: string }) => p.page === 'about')).toBeUndefined();
  });

  it('remove button is hidden when readOnly', () => {
    render(<SitemapCard sitemap={testSitemap} onChange={() => {}} readOnly />);
    expect(screen.queryByRole('button', { name: /remove/i })).toBeNull();
  });

  it('remove button is hidden when only 1 page', () => {
    const singlePage = [testSitemap[0]];
    render(<SitemapCard sitemap={singlePage} onChange={() => {}} />);
    expect(screen.queryByRole('button', { name: /remove/i })).toBeNull();
  });

  it('move up swaps page with previous', () => {
    const onChange = vi.fn();
    render(<SitemapCard sitemap={testSitemap} onChange={onChange} />);
    const moveUpBtn = screen.getByRole('button', { name: /move about up/i });
    fireEvent.click(moveUpBtn);
    expect(onChange).toHaveBeenCalledTimes(1);
    const updated = onChange.mock.calls[0][0];
    expect(updated[0].page).toBe('about');
    expect(updated[1].page).toBe('home');
    expect(updated[2].page).toBe('contact');
  });

  it('move down swaps page with next', () => {
    const onChange = vi.fn();
    render(<SitemapCard sitemap={testSitemap} onChange={onChange} />);
    const moveDownBtn = screen.getByRole('button', { name: /move home down/i });
    fireEvent.click(moveDownBtn);
    expect(onChange).toHaveBeenCalledTimes(1);
    const updated = onChange.mock.calls[0][0];
    expect(updated[0].page).toBe('about');
    expect(updated[1].page).toBe('home');
    expect(updated[2].page).toBe('contact');
  });

  it('move up button is disabled on first page', () => {
    render(<SitemapCard sitemap={testSitemap} onChange={() => {}} />);
    const moveUpBtn = screen.getByRole('button', { name: /move home up/i }) as HTMLButtonElement;
    expect(moveUpBtn.disabled).toBe(true);
  });

  it('move down button is disabled on last page', () => {
    render(<SitemapCard sitemap={testSitemap} onChange={() => {}} />);
    const moveDownBtn = screen.getByRole('button', { name: /move contact down/i }) as HTMLButtonElement;
    expect(moveDownBtn.disabled).toBe(true);
  });
});
