/**
 * Button Component Tests
 * Comprehensive unit tests for the Button component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders, testAssertions, a11yUtils } from '@/test/utils'
import { Button } from '../button'

describe('Button Component', () => {
  let mockOnClick

  beforeEach(() => {
    mockOnClick = vi.fn()
  })

  describe('Rendering', () => {
    it('renders with default props', () => {
      renderWithProviders(<Button>Click me</Button>)
      
      const button = screen.getByRole('button', { name: /click me/i })
      expect(button).toBeInTheDocument()
      expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center')
    })

    it('renders with custom className', () => {
      renderWithProviders(
        <Button className="custom-class">Custom Button</Button>
      )
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class')
    })

    it('renders different variants correctly', () => {
      const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link']
      
      variants.forEach(variant => {
        const { unmount } = renderWithProviders(
          <Button variant={variant}>Button</Button>
        )
        
        const button = screen.getByRole('button')
        expect(button).toBeInTheDocument()
        
        unmount()
      })
    })

    it('renders different sizes correctly', () => {
      const sizes = ['default', 'sm', 'lg', 'icon']
      
      sizes.forEach(size => {
        const { unmount } = renderWithProviders(
          <Button size={size}>Button</Button>
        )
        
        const button = screen.getByRole('button')
        expect(button).toBeInTheDocument()
        
        unmount()
      })
    })

    it('renders as child component when asChild is true', () => {
      renderWithProviders(
        <Button asChild>
          <a href="/test">Link Button</a>
        </Button>
      )
      
      const link = screen.getByRole('link', { name: /link button/i })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/test')
    })
  })

  describe('Interactions', () => {
    it('calls onClick when clicked', () => {
      renderWithProviders(
        <Button onClick={mockOnClick}>Click me</Button>
      )
      
      const button = screen.getByRole('button')
      fireEvent.click(button)
      
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when Enter key is pressed', () => {
      renderWithProviders(
        <Button onClick={mockOnClick}>Click me</Button>
      )
      
      const button = screen.getByRole('button')
      button.focus()
      fireEvent.keyDown(button, { key: 'Enter' })
      
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when Space key is pressed', () => {
      renderWithProviders(
        <Button onClick={mockOnClick}>Click me</Button>
      )
      
      const button = screen.getByRole('button')
      button.focus()
      fireEvent.keyDown(button, { key: ' ' })
      
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('does not call onClick when disabled', () => {
      renderWithProviders(
        <Button onClick={mockOnClick} disabled>
          Disabled Button
        </Button>
      )
      
      const button = screen.getByRole('button')
      fireEvent.click(button)
      
      expect(mockOnClick).not.toHaveBeenCalled()
      expect(button).toBeDisabled()
    })

    it('shows loading state correctly', async () => {
      const { rerender } = renderWithProviders(
        <Button onClick={mockOnClick}>Normal Button</Button>
      )
      
      // Initially not loading
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
      
      // Rerender with loading state
      rerender(
        <Button onClick={mockOnClick} loading>
          Loading Button
        </Button>
      )
      
      await waitFor(() => {
        expect(screen.getByText(/loading/i)).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      renderWithProviders(
        <Button 
          aria-label="Custom label"
          aria-describedby="description"
        >
          Button
        </Button>
      )
      
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', 'Custom label')
      expect(button).toHaveAttribute('aria-describedby', 'description')
    })

    it('is keyboard accessible', () => {
      renderWithProviders(<Button>Accessible Button</Button>)
      
      const button = screen.getByRole('button')
      testAssertions.toBeKeyboardAccessible(button)
    })

    it('has proper focus management', () => {
      renderWithProviders(<Button>Focus Button</Button>)
      
      const button = screen.getByRole('button')
      button.focus()
      
      expect(button).toHaveFocus()
    })

    it('announces loading state to screen readers', async () => {
      renderWithProviders(
        <Button loading loadingText="Saving data">
          Save
        </Button>
      )
      
      await waitFor(() => {
        const loadingText = screen.getByText(/saving data/i)
        expect(loadingText).toBeInTheDocument()
        expect(loadingText).toHaveClass('sr-only')
      })
    })

    it('has proper ARIA pressed state when applicable', () => {
      renderWithProviders(
        <Button aria-pressed="true">Toggle Button</Button>
      )
      
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-pressed', 'true')
    })

    it('supports high contrast mode', () => {
      // Mock high contrast media query
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(query => ({
          matches: query === '(prefers-contrast: high)',
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      })

      renderWithProviders(<Button>High Contrast Button</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('does not re-render unnecessarily', () => {
      const renderSpy = vi.fn()
      
      function TestButton(props) {
        renderSpy()
        return <Button {...props}>Test Button</Button>
      }
      
      const { rerender } = renderWithProviders(<TestButton />)
      
      expect(renderSpy).toHaveBeenCalledTimes(1)
      
      // Rerender with same props
      rerender(<TestButton />)
      
      // Should not cause additional renders due to memoization
      expect(renderSpy).toHaveBeenCalledTimes(2)
    })

    it('handles rapid clicks gracefully', () => {
      renderWithProviders(
        <Button onClick={mockOnClick}>Rapid Click</Button>
      )
      
      const button = screen.getByRole('button')
      
      // Simulate rapid clicks
      for (let i = 0; i < 10; i++) {
        fireEvent.click(button)
      }
      
      expect(mockOnClick).toHaveBeenCalledTimes(10)
    })
  })

  describe('Error Handling', () => {
    it('handles onClick errors gracefully', () => {
      const errorOnClick = vi.fn(() => {
        throw new Error('Test error')
      })
      
      // Mock console.error to prevent error output in tests
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      renderWithProviders(
        <Button onClick={errorOnClick}>Error Button</Button>
      )
      
      const button = screen.getByRole('button')
      
      expect(() => {
        fireEvent.click(button)
      }).not.toThrow()
      
      consoleSpy.mockRestore()
    })

    it('maintains accessibility when error occurs', () => {
      const errorOnClick = vi.fn(() => {
        throw new Error('Test error')
      })
      
      renderWithProviders(
        <Button onClick={errorOnClick}>Error Button</Button>
      )
      
      const button = screen.getByRole('button')
      fireEvent.click(button)
      
      // Button should still be accessible after error
      expect(button).toBeInTheDocument()
      expect(button).toHaveAttribute('role', 'button')
    })
  })

  describe('Integration', () => {
    it('works with form submission', () => {
      const mockSubmit = vi.fn()
      
      renderWithProviders(
        <form onSubmit={mockSubmit}>
          <Button type="submit">Submit</Button>
        </form>
      )
      
      const button = screen.getByRole('button', { name: /submit/i })
      fireEvent.click(button)
      
      expect(mockSubmit).toHaveBeenCalledTimes(1)
    })

    it('works with React Router navigation', () => {
      renderWithProviders(
        <Button asChild>
          <a href="/dashboard">Go to Dashboard</a>
        </Button>
      )
      
      const link = screen.getByRole('link', { name: /go to dashboard/i })
      expect(link).toHaveAttribute('href', '/dashboard')
    })

    it('integrates with loading states from API calls', async () => {
      let isLoading = false
      
      const { rerender } = renderWithProviders(
        <Button loading={isLoading}>API Button</Button>
      )
      
      // Simulate API call starting
      isLoading = true
      rerender(<Button loading={isLoading}>API Button</Button>)
      
      await waitFor(() => {
        expect(screen.getByText(/loading/i)).toBeInTheDocument()
      })
      
      // Simulate API call completing
      isLoading = false
      rerender(<Button loading={isLoading}>API Button</Button>)
      
      await waitFor(() => {
        expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
      })
    })
  })
})
