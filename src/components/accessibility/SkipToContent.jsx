/**
 * Skip to Content Component
 * WCAG 2.1 AA Compliant Skip Navigation Link
 */

import React from 'react'

export default function SkipToContent() {
  const handleSkip = (e) => {
    e.preventDefault()
    const mainContent = document.getElementById('main-content')
    if (mainContent) {
      mainContent.focus()
      mainContent.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <a
      href="#main-content"
      onClick={handleSkip}
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded-md focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200"
    >
      Skip to main content
    </a>
  )
}

/**
 * Accessible Main Content Wrapper
 * Provides proper landmark structure
 */
export function MainContent({ children, className = '' }) {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className={`outline-none ${className}`}
      role="main"
      aria-label="Main content"
    >
      {children}
    </main>
  )
}

/**
 * Accessible Page Header
 * Provides proper heading hierarchy
 */
export function PageHeader({ title, description, children, level = 1 }) {
  const HeadingTag = `h${level}`
  
  return (
    <header className="mb-6" role="banner">
      <div className="flex items-center justify-between">
        <div>
          <HeadingTag className="text-3xl font-bold text-gray-900">
            {title}
          </HeadingTag>
          {description && (
            <p className="mt-2 text-gray-600" id={`${title.toLowerCase().replace(/\s+/g, '-')}-description`}>
              {description}
            </p>
          )}
        </div>
        {children && (
          <div className="flex items-center gap-2">
            {children}
          </div>
        )}
      </div>
    </header>
  )
}

/**
 * Accessible Navigation Landmark
 */
export function NavigationLandmark({ children, ariaLabel, className = '' }) {
  return (
    <nav
      className={className}
      role="navigation"
      aria-label={ariaLabel}
    >
      {children}
    </nav>
  )
}

/**
 * Accessible Section with Proper Heading
 */
export function AccessibleSection({ 
  title, 
  children, 
  level = 2, 
  className = '',
  id = null 
}) {
  const HeadingTag = `h${level}`
  const sectionId = id || title.toLowerCase().replace(/\s+/g, '-')
  
  return (
    <section 
      className={className}
      aria-labelledby={`${sectionId}-heading`}
    >
      <HeadingTag 
        id={`${sectionId}-heading`}
        className="text-xl font-semibold text-gray-900 mb-4"
      >
        {title}
      </HeadingTag>
      {children}
    </section>
  )
}

/**
 * Accessible Status Announcer
 * For dynamic content updates
 */
export function StatusAnnouncer({ message, priority = 'polite' }) {
  if (!message) return null
  
  return (
    <div
      role="status"
      aria-live={priority}
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  )
}

/**
 * Accessible Loading State
 */
export function AccessibleLoading({ message = 'Loading...', className = '' }) {
  return (
    <div 
      className={`flex items-center justify-center p-8 ${className}`}
      role="status"
      aria-live="polite"
    >
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
      <span className="text-gray-600">{message}</span>
    </div>
  )
}

/**
 * Accessible Error State
 */
export function AccessibleError({ 
  title = 'Error', 
  message, 
  onRetry = null, 
  className = '' 
}) {
  return (
    <div 
      className={`p-6 border border-red-200 rounded-lg bg-red-50 ${className}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg 
            className="h-5 w-5 text-red-400" 
            viewBox="0 0 20 20" 
            fill="currentColor"
            aria-hidden="true"
          >
            <path 
              fillRule="evenodd" 
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" 
              clipRule="evenodd" 
            />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">
            {title}
          </h3>
          {message && (
            <p className="mt-1 text-sm text-red-700">
              {message}
            </p>
          )}
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 text-sm font-medium text-red-800 hover:text-red-900 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-red-50 rounded"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Accessible Form Field
 */
export function AccessibleFormField({ 
  label, 
  id, 
  error = null, 
  description = null, 
  required = false,
  children 
}) {
  const errorId = error ? `${id}-error` : null
  const descriptionId = description ? `${id}-description` : null
  
  return (
    <div className="space-y-2">
      <label 
        htmlFor={id}
        className="block text-sm font-medium text-gray-700"
      >
        {label}
        {required && (
          <span className="text-red-500 ml-1" aria-label="required">
            *
          </span>
        )}
      </label>
      
      {description && (
        <p 
          id={descriptionId}
          className="text-sm text-gray-600"
        >
          {description}
        </p>
      )}
      
      <div>
        {React.cloneElement(children, {
          id,
          'aria-describedby': [descriptionId, errorId].filter(Boolean).join(' ') || undefined,
          'aria-invalid': error ? 'true' : undefined,
          'aria-required': required ? 'true' : undefined
        })}
      </div>
      
      {error && (
        <p 
          id={errorId}
          className="text-sm text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  )
}

/**
 * Accessible Button with Loading State
 */
export function AccessibleButton({ 
  children, 
  isLoading = false, 
  loadingText = 'Loading...', 
  disabled = false,
  className = '',
  ...props 
}) {
  return (
    <button
      disabled={disabled || isLoading}
      className={`relative focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      aria-disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <span className="sr-only">
          {loadingText}
        </span>
      )}
      <span className={isLoading ? 'opacity-0' : ''}>
        {children}
      </span>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
        </div>
      )}
    </button>
  )
}
