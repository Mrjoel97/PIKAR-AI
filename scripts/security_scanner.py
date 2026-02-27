#!/usr/bin/env python3
"""Security Scanner for CI/CD - Detects restricted security skills in codebase."""

import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Set

# Restricted patterns to detect
RESTRICTED_PATTERNS = {
    "penetration_testing": [
        r"penetration\s*testing", r"pentest", r"metasploit", r"burp\s*suite",
        r"sqlmap", r"exploit\s*development", r"ad\s*attack", r"kerberos\s*attack"
    ],
    "injection_attacks": [
        r"sql\s*injection", r"xss", r"cross\s*site", r"ldap\s*injection",
        r"html\s*injection", r"command\s*injection"
    ],
    "privilege_escalation": [
        r"privilege\s*escalation", r"privesc", r"pass\s*the\s*hash",
        r"golden\s*ticket", r"root\s*access"
    ],
    "dangerous_code": [
        r"eval\s*\(", r"exec\s*\(", r"compile\s*\(",
        r"subprocess\..*shell\s*=\s*True", r"os\.system\s*\("
    ]
}

SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", "tests", ".pytest_cache", "restricted"}
SKIP_EXTENSIONS = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2"}

APPROVED_SKILLS = {
    "security_best_practices", "secure_coding", "owasp", "security_awareness",
    "threat_modeling", "security_audit", "vulnerability_scanning_safe"
}

class SecurityFinding:
    def __init__(self, file: str, line: int, pattern: str, matched: str, category: str):
        self.file = file
        self.line = line
        self.pattern = pattern
        self.matched = matched
        self.category = category
    
    def to_dict(self):
        return {"file": self.file, "line": self.line, "pattern": self.pattern, "matched": self.matched, "category": self.category}

def should_skip(path: str) -> bool:
    path_lower = path.lower()
    if any(skip in path_lower for skip in SKIP_DIRS):
        return True
    if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    return False

def scan_file(filepath: str) -> List[SecurityFinding]:
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except:
        return findings
    
    for i, line in enumerate(lines, 1):
        for category, patterns in RESTRICTED_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Check if it's an approved skill context
                    if "skill" in filepath.lower() or "auto_mapped" in filepath:
                        # Allow if it's in APPROVED_SKILLS
                        matched_text = match.group().lower()
                        if any(approved in matched_text for approved in APPROVED_SKILLS):
                            continue
                    
                    findings.append(SecurityFinding(filepath, i, pattern, match.group(), category))
    return findings

def scan_directory(root_dir: str) -> Dict:
    all_findings = []
    files_scanned = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if should_skip(filepath):
                continue
            
            files_scanned += 1
            findings = scan_file(filepath)
            all_findings.extend(findings)
    
    return {
        "files_scanned": files_scanned,
        "total_findings": len(all_findings),
        "findings": [f.to_dict() for f in all_findings]
    }

def main():
    root = "app/skills"  # Focus on skills directory
    
    print("=" * 60)
    print("SECURITY SCANNER - Restricted Skills Detection")
    print("=" * 60)
    print(f"\nScanning: {root}")
    
    result = scan_directory(root)
    
    print(f"\nFiles scanned: {result['files_scanned']}")
    print(f"Findings: {result['total_findings']}")
    
    if result['findings']:
        print("\n" + "-" * 60)
        print("RESTRICTED CONTENT DETECTED:")
        print("-" * 60)
        
        # Group by file
        by_file = {}
        for f in result['findings']:
            key = f"{f['file']}:{f['line']}"
            if key not in by_file:
                by_file[key] = []
            by_file[key].append(f)
        
        for loc, findings in sorted(by_file.items()):
            print(f"\n{loc}")
            for f in findings:
                print(f"  [{f['category']}] {f['matched']}")
        
        print("\n" + "=" * 60)
        print("ACTION REQUIRED:")
        print("  1. Review each finding")
        print("  2. Move restricted skills to app/skills/restricted/")
        print("  3. Add to ALLOW_SECURITY_SKILLS=true in production only")
        print("=" * 60)
        
        # Exit with error to block CI
        sys.exit(1)
    else:
        print("\n✓ No restricted security content detected.")
        print("=" * 60)

if __name__ == "__main__":
    main()
