/**
 * Accessibility Service
 * Comprehensive accessibility implementation and monitoring service
 */

import { auditService } from './auditService';
import { errorHandlingService } from './errorHandlingService';

class AccessibilityService {
  constructor() {
    this.accessibilityConfig = {
      enableKeyboardNavigation: true,
      enableScreenReaderSupport: true,
      enableFocusManagement: true,
      enableColorContrastChecking: true,
      enableAriaLabels: true,
      announcePageChanges: true,
      enableReducedMotion: false
    };
    
    this.focusHistory = [];
    this.currentFocusIndex = -1;
    this.keyboardNavigationEnabled = true;
    this.screenReaderAnnouncements = [];
    this.accessibilityErrors = [];
  }

  /**
   * Initialize accessibility service
   */
  async initialize() {
    try {
      console.log('♿ Initializing Accessibility Service...');
      
      // Setup keyboard navigation
      if (this.accessibilityConfig.enableKeyboardNavigation) {
        await this.initializeKeyboardNavigation();
      }
      
      // Setup screen reader support
      if (this.accessibilityConfig.enableScreenReaderSupport) {
        await this.initializeScreenReaderSupport();
      }
      
      // Setup focus management
      if (this.accessibilityConfig.enableFocusManagement) {
        await this.initializeFocusManagement();
      }
      
      // Setup reduced motion preferences
      await this.initializeReducedMotionSupport();
      
      // Setup accessibility monitoring
      await this.initializeAccessibilityMonitoring();
      
      // Setup ARIA live regions
      await this.setupAriaLiveRegions();
      
      console.log('✅ Accessibility Service initialized');
      auditService.logSystem.configChange(null, 'accessibility_service_initialized', null, 'initialized');
    } catch (error) {
      console.error('Failed to initialize Accessibility Service:', error);
      auditService.logSystem.error(error, 'accessibility_service_initialization');
      throw error;
    }
  }

  /**
   * Initialize keyboard navigation
   */
  async initializeKeyboardNavigation() {
    // Global keyboard event handler
    document.addEventListener('keydown', this.handleGlobalKeyDown.bind(this));
    
    // Skip links for keyboard navigation
    this.createSkipLinks();
    
    // Focus trap management
    this.setupFocusTraps();
    
    // Tab order management
    this.setupTabOrderManagement();
  }

  /**
   * Handle global keyboard events
   * @param {KeyboardEvent} event - Keyboard event
   */
  handleGlobalKeyDown(event) {
    const { key, ctrlKey, altKey, shiftKey } = event;
    
    // Skip link navigation (Alt + S)
    if (altKey && key === 's') {
      event.preventDefault();
      this.activateSkipLinks();
      return;
    }
    
    // Focus management (Alt + F)
    if (altKey && key === 'f') {
      event.preventDefault();
      this.showFocusIndicators();
      return;
    }
    
    // Screen reader announcements (Alt + A)
    if (altKey && key === 'a') {
      event.preventDefault();
      this.announceCurrentContext();
      return;
    }
    
    // Escape key handling
    if (key === 'Escape') {
      this.handleEscapeKey(event);
      return;
    }
    
    // Arrow key navigation for custom components
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
      this.handleArrowKeyNavigation(event);
    }
    
    // Enter and Space key handling for custom interactive elements
    if (key === 'Enter' || key === ' ') {
      this.handleActivationKeys(event);
    }
  }

  /**
   * Create skip links for keyboard navigation
   */
  createSkipLinks() {
    const skipLinksContainer = document.createElement('div');
    skipLinksContainer.id = 'skip-links';
    skipLinksContainer.className = 'skip-links';
    skipLinksContainer.innerHTML = `
      <a href="#main-content" class="skip-link">Skip to main content</a>
      <a href="#navigation" class="skip-link">Skip to navigation</a>
      <a href="#search" class="skip-link">Skip to search</a>
    `;
    
    // Add CSS for skip links
    const style = document.createElement('style');
    style.textContent = `
      .skip-links {
        position: absolute;
        top: -40px;
        left: 6px;
        z-index: 1000;
      }
      .skip-link {
        position: absolute;
        top: -40px;
        left: 6px;
        background: #000;
        color: #fff;
        padding: 8px;
        text-decoration: none;
        border-radius: 4px;
        font-size: 14px;
        font-weight: bold;
        z-index: 1001;
        transition: top 0.3s;
      }
      .skip-link:focus {
        top: 6px;
      }
    `;
    
    document.head.appendChild(style);
    document.body.insertBefore(skipLinksContainer, document.body.firstChild);
  }

  /**
   * Initialize screen reader support
   */
  async initializeScreenReaderSupport() {
    // Create announcement regions
    this.createAnnouncementRegions();
    
    // Setup page change announcements
    this.setupPageChangeAnnouncements();
    
    // Setup dynamic content announcements
    this.setupDynamicContentAnnouncements();
    
    // Setup form validation announcements
    this.setupFormValidationAnnouncements();
  }

  /**
   * Create ARIA live regions for announcements
   */
  createAnnouncementRegions() {
    // Polite announcements (non-interrupting)
    const politeRegion = document.createElement('div');
    politeRegion.id = 'aria-live-polite';
    politeRegion.setAttribute('aria-live', 'polite');
    politeRegion.setAttribute('aria-atomic', 'true');
    politeRegion.className = 'sr-only';
    
    // Assertive announcements (interrupting)
    const assertiveRegion = document.createElement('div');
    assertiveRegion.id = 'aria-live-assertive';
    assertiveRegion.setAttribute('aria-live', 'assertive');
    assertiveRegion.setAttribute('aria-atomic', 'true');
    assertiveRegion.className = 'sr-only';
    
    // Status announcements
    const statusRegion = document.createElement('div');
    statusRegion.id = 'aria-status';
    statusRegion.setAttribute('role', 'status');
    statusRegion.setAttribute('aria-live', 'polite');
    statusRegion.className = 'sr-only';
    
    // Add screen reader only CSS
    const style = document.createElement('style');
    style.textContent = `
      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }
    `;
    
    document.head.appendChild(style);
    document.body.appendChild(politeRegion);
    document.body.appendChild(assertiveRegion);
    document.body.appendChild(statusRegion);
  }

  /**
   * Announce message to screen readers
   * @param {string} message - Message to announce
   * @param {string} priority - Priority level (polite, assertive, status)
   */
  announce(message, priority = 'polite') {
    if (!message) return;
    
    const regionId = priority === 'assertive' ? 'aria-live-assertive' : 
                    priority === 'status' ? 'aria-status' : 'aria-live-polite';
    
    const region = document.getElementById(regionId);
    if (region) {
      // Clear previous message
      region.textContent = '';
      
      // Set new message after a brief delay to ensure screen readers pick it up
      setTimeout(() => {
        region.textContent = message;
        
        // Log announcement
        this.screenReaderAnnouncements.push({
          message,
          priority,
          timestamp: new Date().toISOString()
        });
        
        // Keep only last 50 announcements
        if (this.screenReaderAnnouncements.length > 50) {
          this.screenReaderAnnouncements.shift();
        }
      }, 100);
    }
  }

  /**
   * Initialize focus management
   */
  async initializeFocusManagement() {
    // Track focus changes
    document.addEventListener('focusin', this.handleFocusIn.bind(this));
    document.addEventListener('focusout', this.handleFocusOut.bind(this));
    
    // Setup focus indicators
    this.setupFocusIndicators();
    
    // Setup focus restoration
    this.setupFocusRestoration();
  }

  /**
   * Handle focus in events
   * @param {FocusEvent} event - Focus event
   */
  handleFocusIn(event) {
    const element = event.target;
    
    // Add to focus history
    this.focusHistory.push({
      element,
      timestamp: Date.now(),
      tagName: element.tagName,
      id: element.id,
      className: element.className
    });
    
    // Keep focus history manageable
    if (this.focusHistory.length > 100) {
      this.focusHistory.shift();
    }
    
    // Announce focus change for screen readers if needed
    this.announceFocusChange(element);
  }

  /**
   * Handle focus out events
   * @param {FocusEvent} event - Focus event
   */
  handleFocusOut(event) {
    // Log focus out for debugging
    if (process.env.NODE_ENV === 'development') {
      console.log('Focus out:', event.target);
    }
  }

  /**
   * Setup focus indicators
   */
  setupFocusIndicators() {
    const style = document.createElement('style');
    style.textContent = `
      /* Enhanced focus indicators */
      *:focus {
        outline: 2px solid #0066cc;
        outline-offset: 2px;
      }
      
      /* High contrast focus indicators */
      @media (prefers-contrast: high) {
        *:focus {
          outline: 3px solid #000;
          outline-offset: 2px;
        }
      }
      
      /* Focus indicators for interactive elements */
      button:focus,
      a:focus,
      input:focus,
      select:focus,
      textarea:focus,
      [tabindex]:focus {
        outline: 2px solid #0066cc;
        outline-offset: 2px;
        box-shadow: 0 0 0 4px rgba(0, 102, 204, 0.2);
      }
      
      /* Skip focus outline for mouse users */
      .js-focus-visible *:focus:not(.focus-visible) {
        outline: none;
        box-shadow: none;
      }
    `;
    
    document.head.appendChild(style);
    
    // Add focus-visible polyfill behavior
    document.body.classList.add('js-focus-visible');
  }

  /**
   * Initialize reduced motion support
   */
  async initializeReducedMotionSupport() {
    // Check user's motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    if (prefersReducedMotion) {
      this.accessibilityConfig.enableReducedMotion = true;
      document.body.classList.add('reduce-motion');
      
      // Add reduced motion CSS
      const style = document.createElement('style');
      style.textContent = `
        @media (prefers-reduced-motion: reduce) {
          *,
          *::before,
          *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
          }
        }
        
        .reduce-motion * {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.01ms !important;
        }
      `;
      
      document.head.appendChild(style);
      
      this.announce('Reduced motion mode is active', 'status');
    }
  }

  /**
   * Setup ARIA live regions
   */
  async setupAriaLiveRegions() {
    // Already handled in createAnnouncementRegions
    // This method can be extended for additional live regions
  }

  /**
   * Initialize accessibility monitoring
   */
  async initializeAccessibilityMonitoring() {
    // Monitor for accessibility violations
    this.startAccessibilityMonitoring();
    
    // Setup periodic accessibility checks
    setInterval(() => {
      this.performAccessibilityCheck();
    }, 30000); // Every 30 seconds
  }

  /**
   * Perform accessibility check
   */
  performAccessibilityCheck() {
    const violations = [];
    
    // Check for missing alt text
    const images = document.querySelectorAll('img:not([alt])');
    if (images.length > 0) {
      violations.push(`${images.length} images missing alt text`);
    }
    
    // Check for missing form labels
    const inputs = document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])');
    const unlabeledInputs = Array.from(inputs).filter(input => {
      const label = document.querySelector(`label[for="${input.id}"]`);
      return !label && input.type !== 'hidden';
    });
    
    if (unlabeledInputs.length > 0) {
      violations.push(`${unlabeledInputs.length} form inputs missing labels`);
    }
    
    // Check for missing headings
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    if (headings.length === 0) {
      violations.push('No heading elements found on page');
    }
    
    // Log violations
    if (violations.length > 0) {
      this.accessibilityErrors.push({
        violations,
        timestamp: new Date().toISOString(),
        url: window.location.href
      });
      
      if (process.env.NODE_ENV === 'development') {
        console.warn('Accessibility violations found:', violations);
      }
    }
  }

  /**
   * Get accessibility statistics
   * @returns {Object} Accessibility statistics
   */
  getAccessibilityStats() {
    return {
      keyboardNavigationEnabled: this.keyboardNavigationEnabled,
      focusHistoryLength: this.focusHistory.length,
      announcementsCount: this.screenReaderAnnouncements.length,
      errorsCount: this.accessibilityErrors.length,
      reducedMotionEnabled: this.accessibilityConfig.enableReducedMotion,
      recentAnnouncements: this.screenReaderAnnouncements.slice(-5),
      recentErrors: this.accessibilityErrors.slice(-5),
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Handle escape key
   * @param {KeyboardEvent} event - Keyboard event
   */
  handleEscapeKey(event) {
    // Close modals, dropdowns, etc.
    const openModal = document.querySelector('[role="dialog"][aria-hidden="false"]');
    if (openModal) {
      const closeButton = openModal.querySelector('[aria-label*="close"], [aria-label*="Close"]');
      if (closeButton) {
        closeButton.click();
      }
    }
  }

  /**
   * Handle arrow key navigation
   * @param {KeyboardEvent} event - Keyboard event
   */
  handleArrowKeyNavigation(event) {
    const element = event.target;
    const role = element.getAttribute('role');
    
    // Handle specific ARIA roles
    if (role === 'tablist' || role === 'menubar' || role === 'listbox') {
      event.preventDefault();
      this.handleAriaNavigation(element, event.key);
    }
  }

  /**
   * Handle activation keys (Enter/Space)
   * @param {KeyboardEvent} event - Keyboard event
   */
  handleActivationKeys(event) {
    const element = event.target;
    const role = element.getAttribute('role');
    
    // Handle custom interactive elements
    if (role === 'button' || role === 'tab' || role === 'menuitem') {
      event.preventDefault();
      element.click();
    }
  }

  /**
   * Announce focus change
   * @param {Element} element - Focused element
   */
  announceFocusChange(element) {
    const ariaLabel = element.getAttribute('aria-label');
    const ariaLabelledBy = element.getAttribute('aria-labelledby');
    const title = element.getAttribute('title');
    const text = element.textContent?.trim();
    
    let announcement = '';
    
    if (ariaLabel) {
      announcement = ariaLabel;
    } else if (ariaLabelledBy) {
      const labelElement = document.getElementById(ariaLabelledBy);
      announcement = labelElement?.textContent?.trim() || '';
    } else if (title) {
      announcement = title;
    } else if (text && text.length < 100) {
      announcement = text;
    }
    
    if (announcement && element.tagName) {
      const role = element.getAttribute('role') || element.tagName.toLowerCase();
      this.announce(`${announcement}, ${role}`, 'polite');
    }
  }

  /**
   * Setup page change announcements
   */
  setupPageChangeAnnouncements() {
    // Listen for route changes (if using React Router)
    if (window.history && window.history.pushState) {
      const originalPushState = window.history.pushState;
      window.history.pushState = (...args) => {
        originalPushState.apply(window.history, args);
        setTimeout(() => {
          this.announcePageChange();
        }, 100);
      };
    }
  }

  /**
   * Announce page change
   */
  announcePageChange() {
    const title = document.title;
    const mainHeading = document.querySelector('h1');
    const headingText = mainHeading?.textContent?.trim();
    
    const announcement = headingText || title || 'Page changed';
    this.announce(`Navigated to ${announcement}`, 'assertive');
  }

  /**
   * Setup dynamic content announcements
   */
  setupDynamicContentAnnouncements() {
    // This would be integrated with React components
    // to announce dynamic content changes
  }

  /**
   * Setup form validation announcements
   */
  setupFormValidationAnnouncements() {
    // This would be integrated with form validation
    // to announce validation errors
  }

  /**
   * Cleanup service
   */
  cleanup() {
    document.removeEventListener('keydown', this.handleGlobalKeyDown.bind(this));
    document.removeEventListener('focusin', this.handleFocusIn.bind(this));
    document.removeEventListener('focusout', this.handleFocusOut.bind(this));
  }
}

// Create and export singleton instance
export const accessibilityService = new AccessibilityService();

export default accessibilityService;
