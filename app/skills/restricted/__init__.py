# Restricted Skills Module
# 
# This module contains skills that require elevated access permissions.
# These include security testing, penetration testing, and administrative skills.
#
# Access to these skills is controlled by:
# 1. ALLOW_SECURITY_SKILLS environment variable
# 2. User role-based permissions (future implementation)
# 3. Audit logging of all usage

import os
import logging
from typing import Dict, List, Optional, Set
from functools import wraps

logger = logging.getLogger(__name__)

# Configuration
ALLOW_SECURITY_SKILLS = os.environ.get("ALLOW_SECURITY_SKILLS", "false").lower() == "true"
SECURITY_SKILLS_AUDIT_LOG = os.environ.get("SECURITY_SKILLS_AUDIT_LOG", "true").lower() == "true"

# Skill categories that require restricted access
RESTRICTED_CATEGORIES: Set[str] = {
    "penetration_testing",
    "security_testing",
    "exploit_development",
    "privilege_escalation",
    "network_attacks",
    "web_attacks",
}

# Specific skill names that are restricted
RESTRICTED_SKILL_NAMES: Set[str] = {
    # Penetration testing
    "active-directory-attacks",
    "aws-penetration-testing",
    "cloud-penetration-testing",
    "metasploit-framework",
    "pentest-commands",
    "privilege-escalation-methods",
    "linux-privilege-escalation",
    "windows-privilege-escalation",
    
    # Web attacks
    "sql-injection-testing",
    "xss-testing",
    "html-injection-testing",
    "idor-vulnerability-testing",
    "file-path-traversal-testing",
    "broken-authentication",
    "api-fuzzing-bug-bounty",
    
    # Network attacks
    "ssh-penetration-testing",
    "smtp-penetration-testing",
    "wordpress-penetration-testing",
    "shodan-reconnaissance-pentesting",
    "wireshark-network-traffic-analysis",
    "network-101",
    "burp-suite-web-application-testing",
    
    # Other restricted
    "ethical-hacking-methodology",
    "red-team-tactics",
}


class RestrictedSkillAccessError(Exception):
    """Raised when access to a restricted skill is denied."""
    pass


def is_skill_restricted(skill_name: str, skill_category: Optional[str] = None) -> bool:
    """Check if a skill requires restricted access.
    
    Args:
        skill_name: The name/ID of the skill.
        skill_category: Optional category of the skill.
        
    Returns:
        True if the skill is restricted, False otherwise.
    """
    # Normalize skill name
    normalized_name = skill_name.lower().replace("_", "-").replace(" ", "-")
    
    # Check against restricted names
    if normalized_name in RESTRICTED_SKILL_NAMES:
        return True
    
    # Check against restricted categories
    if skill_category and skill_category.lower() in RESTRICTED_CATEGORIES:
        return True
    
    # Check for keywords that indicate restricted content
    restricted_keywords = [
        "penetration", "pentest", "exploit", "attack", "hack",
        "privilege-escalation", "privesc", "injection", "xss",
        "metasploit", "burp-suite", "sqlmap", "nmap",
    ]
    
    for keyword in restricted_keywords:
        if keyword in normalized_name:
            return True
    
    return False


def check_skill_access(skill_name: str, user_id: Optional[str] = None) -> bool:
    """Check if access to a restricted skill is allowed.
    
    Args:
        skill_name: The name/ID of the skill.
        user_id: Optional user ID for role-based access control.
        
    Returns:
        True if access is allowed, False otherwise.
    """
    if not is_skill_restricted(skill_name):
        return True
    
    # Check global flag
    if not ALLOW_SECURITY_SKILLS:
        logger.warning(
            f"Access denied to restricted skill '{skill_name}'. "
            "Set ALLOW_SECURITY_SKILLS=true to enable."
        )
        return False
    
    # Log access (for audit)
    if SECURITY_SKILLS_AUDIT_LOG:
        logger.info(
            f"RESTRICTED_SKILL_ACCESS: skill={skill_name} user={user_id or 'anonymous'} "
            f"allowed=true"
        )
    
    return True


def audit_skill_usage(skill_name: str, user_id: Optional[str], action: str, success: bool) -> None:
    """Log skill usage for audit purposes.
    
    Args:
        skill_name: The name/ID of the skill.
        user_id: The user ID accessing the skill.
        action: The action performed (e.g., 'execute', 'view').
        success: Whether the action was successful.
    """
    if not SECURITY_SKILLS_AUDIT_LOG:
        return
    
    log_data = {
        "event": "RESTRICTED_SKILL_USAGE",
        "skill": skill_name,
        "user": user_id or "anonymous",
        "action": action,
        "success": success,
    }
    
    if success:
        logger.info(f"RESTRICTED_SKILL_USAGE: {log_data}")
    else:
        logger.warning(f"RESTRICTED_SKILL_USAGE_FAILED: {log_data}")


def require_security_access(func):
    """Decorator to restrict access to security-sensitive functions.
    
    Usage:
        @require_security_access
        def my_security_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        skill_name = func.__name__
        
        if not check_skill_access(skill_name):
            raise RestrictedSkillAccessError(
                f"Access to '{skill_name}' is restricted. "
                "Set ALLOW_SECURITY_SKILLS=true to enable."
            )
        
        return func(*args, **kwargs)
    
    return wrapper


def get_restricted_skills_list() -> Dict[str, List[str]]:
    """Get a categorized list of all restricted skills.
    
    Returns:
        Dictionary mapping categories to lists of skill names.
    """
    return {
        "penetration_testing": [
            "active-directory-attacks",
            "aws-penetration-testing",
            "cloud-penetration-testing",
            "metasploit-framework",
            "pentest-commands",
        ],
        "privilege_escalation": [
            "privilege-escalation-methods",
            "linux-privilege-escalation",
            "windows-privilege-escalation",
        ],
        "web_attacks": [
            "sql-injection-testing",
            "xss-testing",
            "html-injection-testing",
            "idor-vulnerability-testing",
            "file-path-traversal-testing",
            "broken-authentication",
            "api-fuzzing-bug-bounty",
        ],
        "network_attacks": [
            "ssh-penetration-testing",
            "smtp-penetration-testing",
            "wordpress-penetration-testing",
            "shodan-reconnaissance-pentesting",
            "wireshark-network-traffic-analysis",
            "network-101",
            "burp-suite-web-application-testing",
        ],
        "methodology": [
            "ethical-hacking-methodology",
            "red-team-tactics",
        ],
    }


def filter_restricted_skills(skills: List[Dict]) -> List[Dict]:
    """Filter out restricted skills from a list if access is not allowed.
    
    Args:
        skills: List of skill dictionaries with 'name' and optionally 'category'.
        
    Returns:
        Filtered list of skills.
    """
    if ALLOW_SECURITY_SKILLS:
        return skills
    
    return [
        skill for skill in skills
        if not is_skill_restricted(
            skill.get("name", ""),
            skill.get("category")
        )
    ]
