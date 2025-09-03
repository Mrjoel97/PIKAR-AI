/**
 * PIKAR AI Accessibility Tests
 * WCAG 2.1 AA Compliance Testing
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { BrowserRouter } from 'react-router-dom'
import SkipToContent, { 
  MainContent, 
  PageHeader, 
  NavigationLandmark,
  AccessibleSection,
  AccessibleFormField,
  AccessibleButton,
  AccessibleLoading,
  AccessibleError
} from '@/components/accessibility/SkipToContent'
import Layout from '@/pages/Layout'
import TierPricingCards from '@/components/pricing/TierPricingCards'
import TrialManager from '@/components/trial/TrialManager'

// Extend Jest matchers
expect.extend(toHaveNoViolations)

// Mock contexts
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'test-user', email: 'test@pikar-ai.com' }
  })
}))

vi.mock('@/hooks/useTier', () => ({
  useTier: () => ({
    currentTier: { id: 'startup', name: 'Startup' },
    isUserInTrial: () => true,
    getTrialDaysRemaining: () => 5
  })
}))

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}

describe('PIKAR AI Accessibility Compliance', () => {
  describe('Skip to Content', () => {
    it('should render skip to content link', () => {
      render(<SkipToContent />)
      
      const skipLink = screen.getByText('Skip to main content')
      expect(skipLink).toBeInTheDocument()
      expect(skipLink).toHaveAttribute('href', '#main-content')
    })

    it('should be visually hidden by default but visible on focus', () => {
      render(<SkipToContent />)
      
      const skipLink = screen.getByText('Skip to main content')
      expect(skipLink).toHaveClass('sr-only')
      expect(skipLink).toHaveClass('focus:not-sr-only')
    })

    it('should have proper focus styles', () => {
      render(<SkipToContent />)
      
      const skipLink = screen.getByText('Skip to main content')
      expect(skipLink).toHaveClass('focus:ring-2')
      expect(skipLink).toHaveClass('focus:ring-blue-500')
    })
  })

  describe('Main Content Landmark', () => {
    it('should render with proper ARIA attributes', () => {
      render(
        <MainContent>
          <div>Test content</div>
        </MainContent>
      )
      
      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
      expect(main).toHaveAttribute('id', 'main-content')
      expect(main).toHaveAttribute('tabIndex', '-1')
      expect(main).toHaveAttribute('aria-label', 'Main content')
    })

    it('should pass axe accessibility tests', async () => {
      const { container } = render(
        <MainContent>
          <h1>Page Title</h1>
          <p>Page content</p>
        </MainContent>
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Page Header Component', () => {
    it('should render with proper heading hierarchy', () => {
      render(
        <PageHeader 
          title="Dashboard" 
          description="Manage your PIKAR AI workspace"
          level={1}
        />
      )
      
      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toHaveTextContent('Dashboard')
      
      const description = screen.getByText('Manage your PIKAR AI workspace')
      expect(description).toBeInTheDocument()
    })

    it('should support different heading levels', () => {
      render(
        <PageHeader 
          title="Section Title" 
          level={2}
        />
      )
      
      const heading = screen.getByRole('heading', { level: 2 })
      expect(heading).toHaveTextContent('Section Title')
    })

    it('should pass axe accessibility tests', async () => {
      const { container } = render(
        <PageHeader 
          title="Test Page" 
          description="Test description"
        />
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Navigation Landmark', () => {
    it('should render with proper ARIA attributes', () => {
      render(
        <NavigationLandmark ariaLabel="Main navigation">
          <ul>
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/settings">Settings</a></li>
          </ul>
        </NavigationLandmark>
      )
      
      const nav = screen.getByRole('navigation')
      expect(nav).toBeInTheDocument()
      expect(nav).toHaveAttribute('aria-label', 'Main navigation')
    })

    it('should pass axe accessibility tests', async () => {
      const { container } = render(
        <NavigationLandmark ariaLabel="Test navigation">
          <ul>
            <li><a href="/test">Test Link</a></li>
          </ul>
        </NavigationLandmark>
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Accessible Form Fields', () => {
    it('should render with proper labels and associations', () => {
      render(
        <AccessibleFormField
          label="Email Address"
          id="email"
          required={true}
          description="Enter your email address"
        >
          <input type="email" />
        </AccessibleFormField>
      )
      
      const label = screen.getByText('Email Address')
      const input = screen.getByRole('textbox')
      const description = screen.getByText('Enter your email address')
      const required = screen.getByText('*')
      
      expect(label).toBeInTheDocument()
      expect(input).toHaveAttribute('id', 'email')
      expect(input).toHaveAttribute('aria-required', 'true')
      expect(input).toHaveAttribute('aria-describedby')
      expect(description).toBeInTheDocument()
      expect(required).toBeInTheDocument()
    })

    it('should handle error states properly', () => {
      render(
        <AccessibleFormField
          label="Password"
          id="password"
          error="Password is required"
        >
          <input type="password" />
        </AccessibleFormField>
      )
      
      const input = screen.getByLabelText('Password')
      const error = screen.getByText('Password is required')
      
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(error).toHaveAttribute('role', 'alert')
    })

    it('should pass axe accessibility tests', async () => {
      const { container } = render(
        <AccessibleFormField
          label="Test Field"
          id="test"
          description="Test description"
          error="Test error"
        >
          <input type="text" />
        </AccessibleFormField>
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Accessible Buttons', () => {
    it('should render with proper loading states', () => {
      render(
        <AccessibleButton 
          isLoading={true}
          loadingText="Saving changes..."
        >
          Save
        </AccessibleButton>
      )
      
      const button = screen.getByRole('button')
      const loadingText = screen.getByText('Saving changes...')
      
      expect(button).toHaveAttribute('aria-disabled', 'true')
      expect(loadingText).toHaveClass('sr-only')
    })

    it('should handle disabled states', () => {
      render(
        <AccessibleButton disabled={true}>
          Disabled Button
        </AccessibleButton>
      )
      
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('disabled')
      expect(button).toHaveAttribute('aria-disabled', 'true')
    })

    it('should pass axe accessibility tests', async () => {
      const { container } = render(
        <AccessibleButton>
          Test Button
        </AccessibleButton>
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Loading States', () => {
    it('should render with proper ARIA attributes', () => {
      render(<AccessibleLoading message="Loading dashboard..." />)
      
      const loading = screen.getByRole('status')
      const message = screen.getByText('Loading dashboard...')
      
      expect(loading).toHaveAttribute('aria-live', 'polite')
      expect(message).toBeInTheDocument()
    })

    it('should pass axe accessibility tests', async () => {
      const { container } = render(
        <AccessibleLoading message="Loading..." />
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Error States', () => {
    it('should render with proper ARIA attributes', () => {
      render(
        <AccessibleError 
          title="Connection Error"
          message="Unable to connect to server"
          onRetry={() => {}}
        />
      )
      
      const error = screen.getByRole('alert')
      const title = screen.getByText('Connection Error')
      const message = screen.getByText('Unable to connect to server')
      const retryButton = screen.getByText('Try again')
      
      expect(error).toHaveAttribute('aria-live', 'assertive')
      expect(title).toBeInTheDocument()
      expect(message).toBeInTheDocument()
      expect(retryButton).toBeInTheDocument()
    })

    it('should pass axe accessibility tests', async () => {
      const { container } = render(
        <AccessibleError 
          title="Test Error"
          message="Test message"
        />
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Complex Components', () => {
    it('should test TierPricingCards accessibility', async () => {
      const { container } = renderWithRouter(<TierPricingCards />)
      
      // Check for proper headings
      const headings = screen.getAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
      
      // Check for proper button labels
      const buttons = screen.getAllByRole('button')
      buttons.forEach(button => {
        expect(button).toHaveAccessibleName()
      })
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('should test TrialManager accessibility', async () => {
      const { container } = render(<TrialManager />)
      
      // Check for proper status indicators
      const status = screen.getByRole('status', { hidden: true })
      expect(status).toBeInTheDocument()
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Color Contrast', () => {
    it('should have sufficient color contrast for text', async () => {
      const { container } = render(
        <div>
          <h1 className="text-gray-900">High Contrast Heading</h1>
          <p className="text-gray-600">Medium Contrast Text</p>
          <button className="bg-blue-600 text-white">High Contrast Button</button>
        </div>
      )
      
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true }
        }
      })
      
      expect(results).toHaveNoViolations()
    })
  })

  describe('Focus Management', () => {
    it('should have visible focus indicators', () => {
      render(
        <div>
          <button className="focus:ring-2 focus:ring-blue-500">
            Focusable Button
          </button>
          <a href="/test" className="focus:ring-2 focus:ring-blue-500">
            Focusable Link
          </a>
        </div>
      )
      
      const button = screen.getByRole('button')
      const link = screen.getByRole('link')
      
      expect(button).toHaveClass('focus:ring-2')
      expect(link).toHaveClass('focus:ring-2')
    })
  })

  describe('Keyboard Navigation', () => {
    it('should support keyboard navigation', async () => {
      const { container } = render(
        <div>
          <button>First Button</button>
          <button>Second Button</button>
          <a href="/test">Test Link</a>
        </div>
      )
      
      const results = await axe(container, {
        rules: {
          'keyboard': { enabled: true },
          'focus-order-semantics': { enabled: true }
        }
      })
      
      expect(results).toHaveNoViolations()
    })
  })

  describe('Screen Reader Support', () => {
    it('should have proper ARIA labels and descriptions', () => {
      render(
        <div>
          <button aria-label="Close dialog">×</button>
          <input aria-describedby="help-text" />
          <div id="help-text">Help text for input</div>
          <div role="status" aria-live="polite">Status message</div>
        </div>
      )
      
      const button = screen.getByRole('button')
      const input = screen.getByRole('textbox')
      const status = screen.getByRole('status')
      
      expect(button).toHaveAttribute('aria-label', 'Close dialog')
      expect(input).toHaveAttribute('aria-describedby', 'help-text')
      expect(status).toHaveAttribute('aria-live', 'polite')
    })
  })
})
