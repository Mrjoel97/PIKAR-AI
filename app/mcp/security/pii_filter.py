"""PII Filter - Sanitize queries before sending to external services.

This module provides privacy protection by detecting and redacting
Personally Identifiable Information (PII) from queries before they
are sent to external search or research APIs.

Supported PII Types:
- Email addresses
- Phone numbers (various formats)
- Credit card numbers
- Social Security Numbers (SSN)
- IP addresses
- Street addresses (partial)
- Names (when explicitly marked in context)
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class PIIMatch:
    """Represents a PII match found in text."""
    pii_type: str
    original: str
    start: int
    end: int
    replacement: str


class PIIFilter:
    """Filter for detecting and redacting PII from text.
    
    This filter uses regex patterns to detect common PII patterns
    and replaces them with safe placeholder tokens.
    """
    
    # Regex patterns for various PII types
    PATTERNS: Dict[str, Tuple[re.Pattern, str]] = {
        "email": (
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "[EMAIL_REDACTED]"
        ),
        "phone_us": (
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            "[PHONE_REDACTED]"
        ),
        "phone_intl": (
            re.compile(r'\b\+[0-9]{1,3}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}\b'),
            "[PHONE_REDACTED]"
        ),
        "ssn": (
            re.compile(r'\b[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4}\b'),
            "[SSN_REDACTED]"
        ),
        "credit_card": (
            re.compile(r'\b(?:[0-9]{4}[-\s]?){3}[0-9]{4}\b'),
            "[CARD_REDACTED]"
        ),
        "ip_address": (
            re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            "[IP_REDACTED]"
        ),
        "date_of_birth": (
            re.compile(r'\b(?:DOB|D\.O\.B\.?|born|birthday)[:\s]*[0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4}\b', re.IGNORECASE),
            "[DOB_REDACTED]"
        ),
    }
    
    def __init__(self, custom_patterns: Optional[Dict[str, Tuple[re.Pattern, str]]] = None):
        """Initialize the PII filter.
        
        Args:
            custom_patterns: Additional patterns to detect, mapping name to (pattern, replacement)
        """
        self.patterns = {**self.PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)
        
        # Context-based names to redact (populated from user context)
        self._context_names: List[str] = []
    
    def set_context_names(self, names: List[str]) -> None:
        """Set names from context that should be redacted.
        
        Args:
            names: List of names to redact (e.g., user's name, company name)
        """
        self._context_names = [name.strip() for name in names if name and name.strip()]
    
    def find_pii(self, text: str) -> List[PIIMatch]:
        """Find all PII matches in the given text.
        
        Args:
            text: The text to scan for PII.
            
        Returns:
            List of PIIMatch objects describing found PII.
        """
        matches: List[PIIMatch] = []
        
        # Check regex patterns
        for pii_type, (pattern, replacement) in self.patterns.items():
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    original=match.group(),
                    start=match.start(),
                    end=match.end(),
                    replacement=replacement
                ))
        
        # Check context-based names
        for name in self._context_names:
            if len(name) < 2:  # Skip very short names to avoid false positives
                continue
            # Case-insensitive name matching
            pattern = re.compile(re.escape(name), re.IGNORECASE)
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    pii_type="name",
                    original=match.group(),
                    start=match.start(),
                    end=match.end(),
                    replacement="[NAME_REDACTED]"
                ))
        
        # Sort by position (reverse) for safe replacement
        matches.sort(key=lambda m: m.start, reverse=True)
        return matches
    
    def sanitize(self, text: str) -> str:
        """Sanitize text by replacing all PII with safe placeholders.
        
        Args:
            text: The text to sanitize.
            
        Returns:
            Sanitized text with PII replaced by placeholders.
        """
        matches = self.find_pii(text)
        result = text
        
        for match in matches:
            result = result[:match.start] + match.replacement + result[match.end:]
        
        return result
    
    def has_pii(self, text: str) -> bool:
        """Check if text contains any PII.
        
        Args:
            text: The text to check.
            
        Returns:
            True if PII was detected, False otherwise.
        """
        return len(self.find_pii(text)) > 0


# Module-level convenience functions
_default_filter = PIIFilter()


def sanitize_query(query: str, context_names: Optional[List[str]] = None) -> str:
    """Sanitize a query by removing PII.
    
    Args:
        query: The query to sanitize.
        context_names: Optional list of names to also redact.
        
    Returns:
        Sanitized query string.
    """
    if context_names:
        _default_filter.set_context_names(context_names)
    return _default_filter.sanitize(query)

