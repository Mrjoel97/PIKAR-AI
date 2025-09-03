/**
 * Accessible Components
 * Enhanced components with comprehensive accessibility features
 */

import React, { useRef, useEffect, useState, forwardRef } from 'react';
import { accessibilityService } from '@/services/accessibilityService';
import { PropTypes } from '@/services/typeSafetyService';

/**
 * Accessible Button Component
 */
export const AccessibleButton = forwardRef(({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'medium',
  ariaLabel,
  ariaDescribedBy,
  ariaPressed,
  loading = false,
  loadingText = 'Loading...',
  className = '',
  ...props
}, ref) => {
  const buttonRef = useRef(null);
  const [isPressed, setIsPressed] = useState(false);

  // Handle keyboard activation
  const handleKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setIsPressed(true);
      if (!disabled && !loading && onClick) {
        onClick(event);
      }
    }
  };

  const handleKeyUp = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      setIsPressed(false);
    }
  };

  const handleClick = (event) => {
    if (!disabled && !loading && onClick) {
      onClick(event);
    }
  };

  // Announce loading state changes
  useEffect(() => {
    if (loading) {
      accessibilityService.announce(loadingText, 'polite');
    }
  }, [loading, loadingText]);

  const buttonClasses = `
    accessible-button
    accessible-button--${variant}
    accessible-button--${size}
    ${disabled ? 'accessible-button--disabled' : ''}
    ${loading ? 'accessible-button--loading' : ''}
    ${isPressed ? 'accessible-button--pressed' : ''}
    ${className}
  `.trim();

  return (
    <button
      ref={ref || buttonRef}
      className={buttonClasses}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onKeyUp={handleKeyUp}
      disabled={disabled || loading}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      aria-pressed={ariaPressed}
      aria-busy={loading}
      role="button"
      tabIndex={disabled ? -1 : 0}
      {...props}
    >
      {loading ? (
        <>
          <span className="accessible-button__spinner" aria-hidden="true" />
          <span className="sr-only">{loadingText}</span>
          {children}
        </>
      ) : (
        children
      )}
    </button>
  );
});

AccessibleButton.displayName = 'AccessibleButton';

AccessibleButton.propTypes = {
  children: PropTypes.node.isRequired,
  onClick: PropTypes.func,
  disabled: PropTypes.bool,
  variant: PropTypes.oneOf(['primary', 'secondary', 'danger', 'ghost']),
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  ariaLabel: PropTypes.string,
  ariaDescribedBy: PropTypes.string,
  ariaPressed: PropTypes.bool,
  loading: PropTypes.bool,
  loadingText: PropTypes.string,
  className: PropTypes.string
};

/**
 * Accessible Input Component
 */
export const AccessibleInput = forwardRef(({
  label,
  id,
  type = 'text',
  value,
  onChange,
  onBlur,
  onFocus,
  placeholder,
  disabled = false,
  required = false,
  error,
  helpText,
  autoComplete,
  className = '',
  ...props
}, ref) => {
  const inputRef = useRef(null);
  const [isFocused, setIsFocused] = useState(false);
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const errorId = error ? `${inputId}-error` : undefined;
  const helpId = helpText ? `${inputId}-help` : undefined;

  const handleFocus = (event) => {
    setIsFocused(true);
    if (onFocus) onFocus(event);
  };

  const handleBlur = (event) => {
    setIsFocused(false);
    if (onBlur) onBlur(event);
  };

  const handleChange = (event) => {
    if (onChange) onChange(event);
  };

  // Announce validation errors
  useEffect(() => {
    if (error) {
      accessibilityService.announce(`Error: ${error}`, 'assertive');
    }
  }, [error]);

  const inputClasses = `
    accessible-input
    ${error ? 'accessible-input--error' : ''}
    ${disabled ? 'accessible-input--disabled' : ''}
    ${isFocused ? 'accessible-input--focused' : ''}
    ${className}
  `.trim();

  const describedBy = [errorId, helpId].filter(Boolean).join(' ') || undefined;

  return (
    <div className="accessible-input-group">
      {label && (
        <label 
          htmlFor={inputId}
          className={`accessible-label ${required ? 'accessible-label--required' : ''}`}
        >
          {label}
          {required && <span aria-label="required" className="accessible-label__required">*</span>}
        </label>
      )}
      
      <input
        ref={ref || inputRef}
        id={inputId}
        type={type}
        value={value}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        autoComplete={autoComplete}
        className={inputClasses}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={describedBy}
        {...props}
      />
      
      {helpText && (
        <div id={helpId} className="accessible-help-text">
          {helpText}
        </div>
      )}
      
      {error && (
        <div id={errorId} className="accessible-error-text" role="alert">
          {error}
        </div>
      )}
    </div>
  );
});

AccessibleInput.displayName = 'AccessibleInput';

AccessibleInput.propTypes = {
  label: PropTypes.string,
  id: PropTypes.string,
  type: PropTypes.string,
  value: PropTypes.string,
  onChange: PropTypes.func,
  onBlur: PropTypes.func,
  onFocus: PropTypes.func,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  required: PropTypes.bool,
  error: PropTypes.string,
  helpText: PropTypes.string,
  autoComplete: PropTypes.string,
  className: PropTypes.string
};

/**
 * Accessible Modal Component
 */
export const AccessibleModal = ({
  isOpen,
  onClose,
  title,
  children,
  closeOnEscape = true,
  closeOnOverlayClick = true,
  initialFocus,
  className = ''
}) => {
  const modalRef = useRef(null);
  const overlayRef = useRef(null);
  const previousFocusRef = useRef(null);
  const [focusableElements, setFocusableElements] = useState([]);

  // Focus management
  useEffect(() => {
    if (isOpen) {
      // Store previous focus
      previousFocusRef.current = document.activeElement;
      
      // Find focusable elements
      const focusable = modalRef.current?.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      setFocusableElements(Array.from(focusable || []));
      
      // Set initial focus
      setTimeout(() => {
        if (initialFocus && modalRef.current?.contains(initialFocus)) {
          initialFocus.focus();
        } else if (focusable && focusable.length > 0) {
          focusable[0].focus();
        }
      }, 100);
      
      // Announce modal opening
      accessibilityService.announce(`Modal opened: ${title}`, 'assertive');
      
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    } else {
      // Restore previous focus
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
      
      // Restore body scroll
      document.body.style.overflow = '';
    }
    
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen, title, initialFocus]);

  // Keyboard event handling
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (!isOpen) return;
      
      if (event.key === 'Escape' && closeOnEscape) {
        event.preventDefault();
        onClose();
      }
      
      if (event.key === 'Tab') {
        // Focus trap
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];
        
        if (event.shiftKey) {
          if (document.activeElement === firstFocusable) {
            event.preventDefault();
            lastFocusable?.focus();
          }
        } else {
          if (document.activeElement === lastFocusable) {
            event.preventDefault();
            firstFocusable?.focus();
          }
        }
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, closeOnEscape, onClose, focusableElements]);

  const handleOverlayClick = (event) => {
    if (closeOnOverlayClick && event.target === overlayRef.current) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      className="accessible-modal-overlay"
      onClick={handleOverlayClick}
      role="presentation"
    >
      <div
        ref={modalRef}
        className={`accessible-modal ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-content"
      >
        <div className="accessible-modal__header">
          <h2 id="modal-title" className="accessible-modal__title">
            {title}
          </h2>
          <button
            className="accessible-modal__close"
            onClick={onClose}
            aria-label="Close modal"
            type="button"
          >
            ×
          </button>
        </div>
        
        <div id="modal-content" className="accessible-modal__content">
          {children}
        </div>
      </div>
    </div>
  );
};

AccessibleModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  closeOnEscape: PropTypes.bool,
  closeOnOverlayClick: PropTypes.bool,
  initialFocus: PropTypes.object,
  className: PropTypes.string
};

/**
 * Accessible Navigation Component
 */
export const AccessibleNavigation = ({
  items,
  currentPath,
  orientation = 'horizontal',
  ariaLabel = 'Main navigation',
  className = ''
}) => {
  const navRef = useRef(null);
  const [focusedIndex, setFocusedIndex] = useState(-1);

  const handleKeyDown = (event, index) => {
    const { key } = event;
    const isHorizontal = orientation === 'horizontal';
    
    let nextIndex = index;
    
    if ((isHorizontal && key === 'ArrowRight') || (!isHorizontal && key === 'ArrowDown')) {
      event.preventDefault();
      nextIndex = index < items.length - 1 ? index + 1 : 0;
    } else if ((isHorizontal && key === 'ArrowLeft') || (!isHorizontal && key === 'ArrowUp')) {
      event.preventDefault();
      nextIndex = index > 0 ? index - 1 : items.length - 1;
    } else if (key === 'Home') {
      event.preventDefault();
      nextIndex = 0;
    } else if (key === 'End') {
      event.preventDefault();
      nextIndex = items.length - 1;
    }
    
    if (nextIndex !== index) {
      setFocusedIndex(nextIndex);
      const nextLink = navRef.current?.querySelectorAll('a')[nextIndex];
      nextLink?.focus();
    }
  };

  return (
    <nav
      ref={navRef}
      className={`accessible-navigation accessible-navigation--${orientation} ${className}`}
      aria-label={ariaLabel}
      role="navigation"
    >
      <ul className="accessible-navigation__list" role="menubar">
        {items.map((item, index) => (
          <li key={item.id || index} className="accessible-navigation__item" role="none">
            <a
              href={item.href}
              className={`accessible-navigation__link ${
                currentPath === item.href ? 'accessible-navigation__link--current' : ''
              }`}
              role="menuitem"
              aria-current={currentPath === item.href ? 'page' : undefined}
              tabIndex={focusedIndex === index ? 0 : -1}
              onKeyDown={(e) => handleKeyDown(e, index)}
              onFocus={() => setFocusedIndex(index)}
            >
              {item.icon && (
                <span className="accessible-navigation__icon" aria-hidden="true">
                  {item.icon}
                </span>
              )}
              <span className="accessible-navigation__text">{item.label}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
};

AccessibleNavigation.propTypes = {
  items: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string,
    href: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    icon: PropTypes.node
  })).isRequired,
  currentPath: PropTypes.string,
  orientation: PropTypes.oneOf(['horizontal', 'vertical']),
  ariaLabel: PropTypes.string,
  className: PropTypes.string
};

export default {
  AccessibleButton,
  AccessibleInput,
  AccessibleModal,
  AccessibleNavigation
};
