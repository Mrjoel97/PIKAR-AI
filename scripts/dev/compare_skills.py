
import sys
from pathlib import Path
PLANNED_SKILLS = """
remotion-best-practices, skill-creator, copywriting, audit-website,
marketing-psychology, programmatic-seo, pdf, marketing-ideas, copy-editing,
social-content, pricing-strategy, page-cro, launch-strategy, pptx,
competitor-alternatives, xlsx, analytics-tracking, baoyu-slide-deck,
onboarding-cro, schema-markup, brainstorming, email-sequence,
baoyu-article-illustrator, docx, paid-ads, signup-flow-cro, free-tool-strategy,
form-cro, paywall-upgrade-cro, referral-program, baoyu-cover-image, popup-cro,
supabase-postgres-best-practices, baoyu-xhs-images, baoyu-comic, ui-ux-pro-max,
baoyu-post-to-x, canvas-design, test-driven-development, doc-coauthoring,
theme-factory, writing-plans, executing-plans, using-superpowers,
verification-before-completion, ship-learn-next, baoyu-image-gen,
threejs-animation, skill-judge, feedback-mastery, humanizer,
startup-metrics-framework, html-to-pdf, startup-financial-modeling, image-enhancer
"""

# List from external_skills.py (Implemented)
IMPLEMENTED_SKILLS = [
    "analytics_tracking", "competitor_alternatives", "copy_editing", "copywriting",
    "email_sequence", "form_cro", "free_tool_strategy", "launch_strategy",
    "marketing_ideas", "marketing_psychology", "onboarding_cro", "page_cro",
    "paid_ads", "paywall_upgrade_cro", "popup_cro", "pricing_strategy",
    "programmatic_seo", "referral_program", "schema_markup", "seo_audit",
    "signup_flow_cro", "social_media_strategy",
    "brainstorming", "dispatching_parallel_agents", "executing_plans",
    "subagent_driven_development", "systematic_debugging", "test_driven_development",
    "using_superpowers", "verification_before_completion", "writing_plans", "writing_skills",
    "frontend_design", "react_native_best_practices", "ui_ux_pro_max",
    "vercel_react_best_practices", "web_design_guidelines"
]

def normalize(name):
    return name.strip().replace("-", "_").lower()

def main():
    planned = set()
    for line in PLANNED_SKILLS.strip().split('\n'):
        for item in line.split(','):
            if item.strip():
                planned.add(normalize(item))

    implemented = set(normalize(s) for s in IMPLEMENTED_SKILLS)

    missing = planned - implemented
    extra = implemented - planned

    print(f"Planned Count: {len(planned)}")
    print(f"Implemented (in external_skills.py) Count: {len(implemented)}")

    # Check .agent/skills for missing ones
    agent_skills_dir = Path("c:/Users/expert/Documents/PKA/Pikar-Ai/.agent/skills")
    physical_skills = set()
    if agent_skills_dir.exists():
        for item in agent_skills_dir.iterdir():
            physical_skills.add(normalize(item.name))

    print(f"Physical (.agent/skills) Count: {len(physical_skills)}")

    missing_from_code = planned - implemented
    found_in_fs = missing_from_code & physical_skills
    truly_missing = missing_from_code - physical_skills

    print("\n--- Missing from Code but Found in .agent/skills ---")
    for s in sorted(found_in_fs):
        print(f"- {s}")

    print("\n--- truly Missing (Not in code OR file system) ---")
    for s in sorted(truly_missing):
        print(f"- {s}")

    print("\n--- Extra Skills (Implemented but not in Appendix A list) ---")
    for s in sorted(extra):
        print(f"- {s}")

if __name__ == "__main__":
    main()
