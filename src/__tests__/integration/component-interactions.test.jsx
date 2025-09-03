/**
 * Component Interactions Integration Tests
 * Testing complex component interactions and data flow
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, testDataFactories, mockBase44Client } from '@/test/utils'
import Dashboard from '@/pages/Dashboard'
import CampaignCreation from '@/pages/CampaignCreation'
import ContentCreation from '@/pages/ContentCreation'
import { authService } from '@/services/authService'
import { campaignService } from '@/services/campaignService'
import { agentService } from '@/services/agentService'

// Mock services
vi.mock('@/services/authService')
vi.mock('@/services/campaignService')
vi.mock('@/services/agentService')
vi.mock('@/api/base44Client', () => ({
  base44: mockBase44Client,
  validatedBase44: mockBase44Client
}))

describe('Component Interactions Integration', () => {
  const mockUser = testDataFactories.user()
  const mockCampaigns = [
    testDataFactories.campaign({ id: '1', name: 'Campaign 1', status: 'active' }),
    testDataFactories.campaign({ id: '2', name: 'Campaign 2', status: 'draft' }),
    testDataFactories.campaign({ id: '3', name: 'Campaign 3', status: 'completed' })
  ]
  const mockAnalytics = testDataFactories.analytics()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock authenticated user
    authService.getCurrentUser.mockReturnValue(mockUser)
    authService.isAuthenticated = true
    
    // Mock campaign service
    campaignService.getCampaigns.mockResolvedValue({
      success: true,
      data: mockCampaigns
    })
    
    campaignService.createCampaign.mockResolvedValue({
      success: true,
      data: testDataFactories.campaign({ id: '4', name: 'New Campaign' })
    })
    
    // Mock agent service
    agentService.getAgents.mockResolvedValue({
      success: true,
      data: [testDataFactories.agent()]
    })
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Dashboard Component Interactions', () => {
    it('loads and displays campaign data with analytics', async () => {
      // Mock analytics data
      campaignService.getCampaignAnalytics.mockResolvedValue({
        success: true,
        data: mockAnalytics
      })

      renderWithProviders(<Dashboard />)

      // Should show loading state initially
      expect(screen.getByText(/loading/i)).toBeInTheDocument()

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('Campaign 1')).toBeInTheDocument()
        expect(screen.getByText('Campaign 2')).toBeInTheDocument()
        expect(screen.getByText('Campaign 3')).toBeInTheDocument()
      })

      // Should display analytics metrics
      await waitFor(() => {
        expect(screen.getByText('1000')).toBeInTheDocument() // Total users
        expect(screen.getByText('750')).toBeInTheDocument() // Active users
      })

      // Verify API calls
      expect(campaignService.getCampaigns).toHaveBeenCalledTimes(1)
      expect(campaignService.getCampaignAnalytics).toHaveBeenCalledTimes(1)
    })

    it('handles campaign status filtering', async () => {
      renderWithProviders(<Dashboard />)

      // Wait for campaigns to load
      await waitFor(() => {
        expect(screen.getByText('Campaign 1')).toBeInTheDocument()
      })

      // Find and click status filter
      const statusFilter = screen.getByRole('combobox', { name: /status/i })
      await userEvent.click(statusFilter)

      // Select 'active' filter
      const activeOption = screen.getByRole('option', { name: /active/i })
      await userEvent.click(activeOption)

      // Should show only active campaigns
      await waitFor(() => {
        expect(screen.getByText('Campaign 1')).toBeInTheDocument()
        expect(screen.queryByText('Campaign 2')).not.toBeInTheDocument() // Draft
        expect(screen.queryByText('Campaign 3')).not.toBeInTheDocument() // Completed
      })
    })

    it('navigates to campaign creation from dashboard', async () => {
      const user = userEvent.setup()

      renderWithProviders(<Dashboard />)

      // Wait for dashboard to load
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
      })

      // Find and click create campaign button
      const createButton = screen.getByRole('button', { name: /create campaign/i })
      await user.click(createButton)

      // Should navigate to campaign creation
      await waitFor(() => {
        expect(window.location.pathname).toBe('/campaigns/create')
      })
    })

    it('refreshes data when refresh button is clicked', async () => {
      const user = userEvent.setup()

      renderWithProviders(<Dashboard />)

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Campaign 1')).toBeInTheDocument()
      })

      // Clear mock call history
      vi.clearAllMocks()

      // Find and click refresh button
      const refreshButton = screen.getByRole('button', { name: /refresh/i })
      await user.click(refreshButton)

      // Should reload data
      await waitFor(() => {
        expect(campaignService.getCampaigns).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Campaign Creation Flow', () => {
    it('completes full campaign creation workflow', async () => {
      const user = userEvent.setup()

      renderWithProviders(<CampaignCreation />)

      // Fill in campaign form
      const nameInput = screen.getByLabelText(/campaign name/i)
      const descriptionInput = screen.getByLabelText(/description/i)
      const budgetInput = screen.getByLabelText(/budget/i)

      await user.type(nameInput, 'Test Campaign')
      await user.type(descriptionInput, 'Test campaign description')
      await user.type(budgetInput, '5000')

      // Select campaign type
      const typeSelect = screen.getByRole('combobox', { name: /type/i })
      await user.click(typeSelect)
      const socialOption = screen.getByRole('option', { name: /social media/i })
      await user.click(socialOption)

      // Submit form
      const submitButton = screen.getByRole('button', { name: /create campaign/i })
      await user.click(submitButton)

      // Should call create campaign API
      await waitFor(() => {
        expect(campaignService.createCampaign).toHaveBeenCalledWith({
          name: 'Test Campaign',
          description: 'Test campaign description',
          budget: 5000,
          type: 'social'
        })
      })

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/campaign created successfully/i)).toBeInTheDocument()
      })
    })

    it('validates form fields before submission', async () => {
      const user = userEvent.setup()

      renderWithProviders(<CampaignCreation />)

      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /create campaign/i })
      await user.click(submitButton)

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/campaign name is required/i)).toBeInTheDocument()
        expect(screen.getByText(/budget is required/i)).toBeInTheDocument()
      })

      // Should not call API
      expect(campaignService.createCampaign).not.toHaveBeenCalled()
    })

    it('handles campaign creation errors', async () => {
      const user = userEvent.setup()

      // Mock API error
      campaignService.createCampaign.mockResolvedValueOnce({
        success: false,
        error: 'Budget exceeds limit for your tier'
      })

      renderWithProviders(<CampaignCreation />)

      // Fill and submit form
      await user.type(screen.getByLabelText(/campaign name/i), 'Test Campaign')
      await user.type(screen.getByLabelText(/budget/i), '100000')

      const submitButton = screen.getByRole('button', { name: /create campaign/i })
      await user.click(submitButton)

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/budget exceeds limit/i)).toBeInTheDocument()
      })
    })
  })

  describe('Content Creation Integration', () => {
    it('integrates with AI agent for content generation', async () => {
      const user = userEvent.setup()

      // Mock agent execution
      agentService.executeAgent.mockResolvedValue({
        success: true,
        data: {
          content: 'Generated social media content about AI innovation',
          metadata: {
            tokensUsed: 150,
            executionTime: 2.5
          }
        }
      })

      renderWithProviders(<ContentCreation />)

      // Fill in content request form
      const promptInput = screen.getByLabelText(/content prompt/i)
      const toneSelect = screen.getByRole('combobox', { name: /tone/i })

      await user.type(promptInput, 'Create content about AI innovation')
      await user.click(toneSelect)
      await user.click(screen.getByRole('option', { name: /professional/i }))

      // Generate content
      const generateButton = screen.getByRole('button', { name: /generate content/i })
      await user.click(generateButton)

      // Should call agent service
      await waitFor(() => {
        expect(agentService.executeAgent).toHaveBeenCalledWith({
          type: 'content-creation',
          prompt: 'Create content about AI innovation',
          parameters: {
            tone: 'professional'
          }
        })
      })

      // Should display generated content
      await waitFor(() => {
        expect(screen.getByText(/generated social media content/i)).toBeInTheDocument()
      })
    })

    it('allows editing and saving generated content', async () => {
      const user = userEvent.setup()

      // Mock initial content generation
      agentService.executeAgent.mockResolvedValue({
        success: true,
        data: {
          content: 'Initial generated content'
        }
      })

      // Mock content saving
      campaignService.saveContent.mockResolvedValue({
        success: true,
        data: { id: 'content-123' }
      })

      renderWithProviders(<ContentCreation />)

      // Generate initial content
      await user.type(screen.getByLabelText(/content prompt/i), 'Test prompt')
      await user.click(screen.getByRole('button', { name: /generate content/i }))

      // Wait for content to appear
      await waitFor(() => {
        expect(screen.getByText(/initial generated content/i)).toBeInTheDocument()
      })

      // Edit the content
      const contentEditor = screen.getByRole('textbox', { name: /content editor/i })
      await user.clear(contentEditor)
      await user.type(contentEditor, 'Edited content with improvements')

      // Save content
      const saveButton = screen.getByRole('button', { name: /save content/i })
      await user.click(saveButton)

      // Should call save API
      await waitFor(() => {
        expect(campaignService.saveContent).toHaveBeenCalledWith({
          content: 'Edited content with improvements',
          type: 'social-media'
        })
      })

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/content saved successfully/i)).toBeInTheDocument()
      })
    })
  })

  describe('Real-time Updates', () => {
    it('updates campaign status in real-time', async () => {
      renderWithProviders(<Dashboard />)

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Campaign 1')).toBeInTheDocument()
      })

      // Simulate real-time update
      const updatedCampaign = { ...mockCampaigns[0], status: 'paused' }
      
      // Mock WebSocket or polling update
      campaignService.getCampaigns.mockResolvedValueOnce({
        success: true,
        data: [updatedCampaign, ...mockCampaigns.slice(1)]
      })

      // Trigger update (simulate polling or WebSocket message)
      fireEvent(window, new CustomEvent('campaign-updated', {
        detail: { campaignId: '1', status: 'paused' }
      }))

      // Should update status in UI
      await waitFor(() => {
        expect(screen.getByText(/paused/i)).toBeInTheDocument()
      })
    })

    it('shows notifications for important events', async () => {
      renderWithProviders(<Dashboard />)

      // Simulate notification event
      fireEvent(window, new CustomEvent('notification', {
        detail: {
          type: 'success',
          message: 'Campaign "Test Campaign" has been approved',
          duration: 5000
        }
      }))

      // Should show notification
      await waitFor(() => {
        expect(screen.getByText(/campaign "test campaign" has been approved/i)).toBeInTheDocument()
      })

      // Notification should disappear after duration
      await waitFor(() => {
        expect(screen.queryByText(/campaign "test campaign" has been approved/i)).not.toBeInTheDocument()
      }, { timeout: 6000 })
    })
  })

  describe('Error Boundary Integration', () => {
    it('catches and displays component errors gracefully', async () => {
      // Mock component error
      const ErrorComponent = () => {
        throw new Error('Test component error')
      }

      // Mock console.error to prevent error output in tests
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      renderWithProviders(<ErrorComponent />)

      // Should show error boundary
      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      })

      // Should have retry button
      const retryButton = screen.getByRole('button', { name: /try again/i })
      expect(retryButton).toBeInTheDocument()

      consoleSpy.mockRestore()
    })

    it('recovers from errors when retry is clicked', async () => {
      const user = userEvent.setup()
      let shouldError = true

      const ConditionalErrorComponent = () => {
        if (shouldError) {
          throw new Error('Test error')
        }
        return <div>Component recovered</div>
      }

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      renderWithProviders(<ConditionalErrorComponent />)

      // Should show error initially
      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
      })

      // Fix the error condition
      shouldError = false

      // Click retry
      const retryButton = screen.getByRole('button', { name: /try again/i })
      await user.click(retryButton)

      // Should recover and show component
      await waitFor(() => {
        expect(screen.getByText(/component recovered/i)).toBeInTheDocument()
      })

      consoleSpy.mockRestore()
    })
  })

  describe('Performance Integration', () => {
    it('handles large datasets efficiently', async () => {
      // Mock large dataset
      const largeCampaignList = Array.from({ length: 1000 }, (_, i) => 
        testDataFactories.campaign({ id: `campaign-${i}`, name: `Campaign ${i}` })
      )

      campaignService.getCampaigns.mockResolvedValue({
        success: true,
        data: largeCampaignList
      })

      const startTime = performance.now()
      
      renderWithProviders(<Dashboard />)

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('Campaign 0')).toBeInTheDocument()
      })

      const endTime = performance.now()
      const renderTime = endTime - startTime

      // Should render within reasonable time (less than 2 seconds)
      expect(renderTime).toBeLessThan(2000)
    })

    it('implements virtual scrolling for large lists', async () => {
      const largeCampaignList = Array.from({ length: 10000 }, (_, i) => 
        testDataFactories.campaign({ id: `campaign-${i}`, name: `Campaign ${i}` })
      )

      campaignService.getCampaigns.mockResolvedValue({
        success: true,
        data: largeCampaignList
      })

      renderWithProviders(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Campaign 0')).toBeInTheDocument()
      })

      // Should only render visible items (not all 10,000)
      const renderedItems = screen.getAllByText(/Campaign \d+/)
      expect(renderedItems.length).toBeLessThan(100) // Virtual scrolling should limit rendered items
    })
  })
})
