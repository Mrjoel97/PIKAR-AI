#!/usr/bin/env python3
"""Check for print statements in production code."""

import re
import sys
from pathlib import Path


def check_file(filepath: str) -> list:
    """Check a Python file for print statements."""
    warnings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Match print( but not within strings or comments
            # Simple regex - doesn't handle all edge cases but good enough
            pattern = re.compile(r'(?<!["\'\'])\bprint\s*\(')
            
            for i, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue
                if pattern.search(line):
                    warnings.append(f"{filepath}:{i}: Print statement found (use logger)")
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
    
    return warnings


def main():
    """Main entry point."""
    files = sys.argv[1:]
    all_warnings = []
    
    for filepath in files:
        if filepath.endswith('.py'):
            warnings = check_file(filepath)
            all_warnings.extend(warnings)
    
    if all_warnings:
        for warning in all_warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        # Exit 0 for warnings only, not errors
        print("\nConsider replacing print() statements with logging for production code.", file=sys.stderr)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
