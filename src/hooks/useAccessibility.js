/**
 * Accessibility Hooks
 * Custom hooks for accessibility features and utilities
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { accessibilityService } from '@/services/accessibilityService';

/**
 * Hook for screen reader announcements
 * @param {string} message - Message to announce
 * @param {string} priority - Priority level (polite, assertive, status)
 */
export const useAnnouncement = () => {
  const announce = useCallback((message, priority = 'polite') => {
    accessibilityService.announce(message, priority);
  }, []);

  return announce;
};

/**
 * Hook for focus management
 * @param {boolean} shouldFocus - Whether to focus the element
 * @param {Array} deps - Dependencies for focus effect
 */
export const useFocus = (shouldFocus = false, deps = []) => {
  const elementRef = useRef(null);

  useEffect(() => {
    if (shouldFocus && elementRef.current) {
      elementRef.current.focus();
    }
  }, [shouldFocus, ...deps]);

  return elementRef;
};

/**
 * Hook for focus trap (modal, dropdown, etc.)
 * @param {boolean} isActive - Whether the focus trap is active
 */
export const useFocusTrap = (isActive = false) => {
  const containerRef = useRef(null);
  const previousFocusRef = useRef(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    // Store previous focus
    previousFocusRef.current = document.activeElement;

    // Get focusable elements
    const focusableElements = containerRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    // Focus first element
    if (firstFocusable) {
      firstFocusable.focus();
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Tab') {
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

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      
      // Restore previous focus
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [isActive]);

  return containerRef;
};

/**
 * Hook for keyboard navigation
 * @param {Array} items - Items to navigate
 * @param {Object} options - Navigation options
 */
export const useKeyboardNavigation = (items, options = {}) => {
  const {
    orientation = 'vertical',
    loop = true,
    onSelect,
    initialIndex = -1
  } = options;

  const [focusedIndex, setFocusedIndex] = useState(initialIndex);
  const containerRef = useRef(null);

  const handleKeyDown = useCallback((event) => {
    const { key } = event;
    const isVertical = orientation === 'vertical';
    
    let nextIndex = focusedIndex;

    switch (key) {
      case isVertical ? 'ArrowDown' : 'ArrowRight':
        event.preventDefault();
        nextIndex = focusedIndex < items.length - 1 ? focusedIndex + 1 : (loop ? 0 : focusedIndex);
        break;
        
      case isVertical ? 'ArrowUp' : 'ArrowLeft':
        event.preventDefault();
        nextIndex = focusedIndex > 0 ? focusedIndex - 1 : (loop ? items.length - 1 : focusedIndex);
        break;
        
      case 'Home':
        event.preventDefault();
        nextIndex = 0;
        break;
        
      case 'End':
        event.preventDefault();
        nextIndex = items.length - 1;
        break;
        
      case 'Enter':
      case ' ':
        event.preventDefault();
        if (onSelect && focusedIndex >= 0) {
          onSelect(items[focusedIndex], focusedIndex);
        }
        break;
        
      default:
        return;
    }

    if (nextIndex !== focusedIndex) {
      setFocusedIndex(nextIndex);
    }
  }, [focusedIndex, items, orientation, loop, onSelect]);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyDown);
      return () => container.removeEventListener('keydown', handleKeyDown);
    }
  }, [handleKeyDown]);

  return {
    containerRef,
    focusedIndex,
    setFocusedIndex
  };
};

/**
 * Hook for ARIA live region announcements
 * @param {string} regionType - Type of live region (polite, assertive, status)
 */
export const useLiveRegion = (regionType = 'polite') => {
  const [message, setMessage] = useState('');

  const announce = useCallback((newMessage) => {
    setMessage(''); // Clear first to ensure screen readers pick up the change
    setTimeout(() => {
      setMessage(newMessage);
      accessibilityService.announce(newMessage, regionType);
    }, 100);
  }, [regionType]);

  return { message, announce };
};

/**
 * Hook for reduced motion preference
 */
export const useReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (event) => {
      setPrefersReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersReducedMotion;
};

/**
 * Hook for high contrast preference
 */
export const useHighContrast = () => {
  const [prefersHighContrast, setPrefersHighContrast] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: high)');
    setPrefersHighContrast(mediaQuery.matches);

    const handleChange = (event) => {
      setPrefersHighContrast(event.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersHighContrast;
};

/**
 * Hook for managing ARIA attributes
 * @param {Object} initialAttributes - Initial ARIA attributes
 */
export const useAriaAttributes = (initialAttributes = {}) => {
  const [attributes, setAttributes] = useState(initialAttributes);

  const updateAttribute = useCallback((key, value) => {
    setAttributes(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const removeAttribute = useCallback((key) => {
    setAttributes(prev => {
      const newAttributes = { ...prev };
      delete newAttributes[key];
      return newAttributes;
    });
  }, []);

  const getAriaProps = useCallback(() => {
    const ariaProps = {};
    Object.entries(attributes).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        ariaProps[key.startsWith('aria-') ? key : `aria-${key}`] = value;
      }
    });
    return ariaProps;
  }, [attributes]);

  return {
    attributes,
    updateAttribute,
    removeAttribute,
    getAriaProps
  };
};

/**
 * Hook for accessible form validation
 * @param {Object} validationRules - Validation rules
 */
export const useAccessibleValidation = (validationRules = {}) => {
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const announce = useAnnouncement();

  const validate = useCallback((fieldName, value) => {
    const rule = validationRules[fieldName];
    if (!rule) return null;

    if (rule.required && (!value || value.trim() === '')) {
      return rule.requiredMessage || `${fieldName} is required`;
    }

    if (rule.pattern && !rule.pattern.test(value)) {
      return rule.patternMessage || `${fieldName} format is invalid`;
    }

    if (rule.minLength && value.length < rule.minLength) {
      return rule.minLengthMessage || `${fieldName} must be at least ${rule.minLength} characters`;
    }

    if (rule.maxLength && value.length > rule.maxLength) {
      return rule.maxLengthMessage || `${fieldName} must be no more than ${rule.maxLength} characters`;
    }

    if (rule.custom && !rule.custom(value)) {
      return rule.customMessage || `${fieldName} is invalid`;
    }

    return null;
  }, [validationRules]);

  const validateField = useCallback((fieldName, value) => {
    const error = validate(fieldName, value);
    
    setErrors(prev => ({
      ...prev,
      [fieldName]: error
    }));

    // Announce validation errors
    if (error && touched[fieldName]) {
      announce(`Error in ${fieldName}: ${error}`, 'assertive');
    }

    return !error;
  }, [validate, touched, announce]);

  const validateAll = useCallback((values) => {
    const newErrors = {};
    let isValid = true;

    Object.keys(validationRules).forEach(fieldName => {
      const error = validate(fieldName, values[fieldName]);
      if (error) {
        newErrors[fieldName] = error;
        isValid = false;
      }
    });

    setErrors(newErrors);

    // Announce validation summary
    const errorCount = Object.keys(newErrors).length;
    if (errorCount > 0) {
      announce(`Form has ${errorCount} error${errorCount > 1 ? 's' : ''}`, 'assertive');
    }

    return isValid;
  }, [validationRules, validate, announce]);

  const markFieldTouched = useCallback((fieldName) => {
    setTouched(prev => ({
      ...prev,
      [fieldName]: true
    }));
  }, []);

  const clearErrors = useCallback(() => {
    setErrors({});
    setTouched({});
  }, []);

  return {
    errors,
    touched,
    validateField,
    validateAll,
    markFieldTouched,
    clearErrors
  };
};

/**
 * Hook for accessible data table
 * @param {Array} data - Table data
 * @param {Array} columns - Column definitions
 */
export const useAccessibleTable = (data, columns) => {
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');
  const [selectedRows, setSelectedRows] = useState(new Set());
  const announce = useAnnouncement();

  const handleSort = useCallback((columnKey) => {
    const newDirection = sortColumn === columnKey && sortDirection === 'asc' ? 'desc' : 'asc';
    setSortColumn(columnKey);
    setSortDirection(newDirection);
    
    const column = columns.find(col => col.key === columnKey);
    const columnName = column?.title || columnKey;
    announce(`Table sorted by ${columnName}, ${newDirection}ending`, 'polite');
  }, [sortColumn, sortDirection, columns, announce]);

  const toggleRowSelection = useCallback((rowId) => {
    setSelectedRows(prev => {
      const newSelection = new Set(prev);
      if (newSelection.has(rowId)) {
        newSelection.delete(rowId);
        announce('Row deselected', 'polite');
      } else {
        newSelection.add(rowId);
        announce('Row selected', 'polite');
      }
      return newSelection;
    });
  }, [announce]);

  const selectAllRows = useCallback(() => {
    const allRowIds = data.map((row, index) => row.id || index);
    setSelectedRows(new Set(allRowIds));
    announce(`All ${allRowIds.length} rows selected`, 'polite');
  }, [data, announce]);

  const clearSelection = useCallback(() => {
    setSelectedRows(new Set());
    announce('Selection cleared', 'polite');
  }, [announce]);

  const sortedData = React.useMemo(() => {
    if (!sortColumn) return data;

    return [...data].sort((a, b) => {
      const aValue = a[sortColumn];
      const bValue = b[sortColumn];
      
      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortColumn, sortDirection]);

  return {
    sortedData,
    sortColumn,
    sortDirection,
    selectedRows,
    handleSort,
    toggleRowSelection,
    selectAllRows,
    clearSelection
  };
};

export default {
  useAnnouncement,
  useFocus,
  useFocusTrap,
  useKeyboardNavigation,
  useLiveRegion,
  useReducedMotion,
  useHighContrast,
  useAriaAttributes,
  useAccessibleValidation,
  useAccessibleTable
};
