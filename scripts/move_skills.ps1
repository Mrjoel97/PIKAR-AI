$agenticSkills = @(
    "copywriting", "copy-editing", "proof-reading", "writing-skills", "baoyu-comic", "baoyu-article-illustrator", "social-content",
    "marketing-ideas", "marketing-psychology", "launch-strategy", "pricing-strategy", "competitor-alternatives", "brainstorming", "free-tool-strategy",
    "seo-audit", "programmatic-seo", "schema-markup", "page-cro", "form-cro", "popup-cro", "signup-flow-cro", "onboarding-cro", "paywall-upgrade-cro",
    "remotion", "html-to-pdf", "pdf", "docx", "xlsx", "ui-ux-pro-max", "web-design-guidelines",
    "email-sequence", "referral-program", "paid-ads",
    "analytics-tracking", "audit-website", "doc-coauthoring"
)

$managementSkills = @(
    "architecture-patterns", "api-design-principles", "database-schema-designer", "design-md", "frontend-design", "spec-to-code-compliance",
    "react-components", "fastapi-templates", "react-modernization", "react-state-management", "react-native-best-practices", "nodejs-backend-patterns", "python-packaging", "vercel-react-best-practices", "gcp-cloud-run", "supabase-best-practices", "mcp-builder",
    "conductor_task", "conductor_phase", "scaffold_feature", "dependency-updater", "dispatching-parallel-agents", "workflow-orchestration-patterns", "executing-plans", "writing-plans", "subagent-driven-development", "verification-before-completion", "test-driven-development",
    "game-changing-features", "audit-context-building",
    "python-testing-patterns", "systematic-debugging", "using-superpowers", "auth-implementation-patterns"
)

# Move Agentic Skills
foreach ($skill in $agenticSkills) {
    if (Test-Path ".agent\skills\$skill") {
        Write-Host "Moving $skill to apps\agent-skills"
        Move-Item -Path ".agent\skills\$skill" -Destination "apps\agent-skills" -Force
    } else {
        Write-Host "Skipping $skill (not found)"
    }
}

# Move ThreeJS Skills (Wildcard)
Get-ChildItem ".agent\skills\threejs-*" | ForEach-Object {
    Write-Host "Moving $($_.Name) to apps\agent-skills"
    Move-Item -Path $_.FullName -Destination "apps\agent-skills" -Force
}

# Move Management Skills
foreach ($skill in $managementSkills) {
    if (Test-Path ".agent\skills\$skill") {
        Write-Host "Moving $skill to tools\management-skills"
        Move-Item -Path ".agent\skills\$skill" -Destination "tools\management-skills" -Force
    } else {
        Write-Host "Skipping $skill (not found)"
    }
}
