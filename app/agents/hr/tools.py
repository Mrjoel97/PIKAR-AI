# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools for the HR & Recruitment Agent."""


async def create_job(
    title: str, department: str, description: str, requirements: str
) -> dict:
    """Create a new job posting.

    Args:
        title: Job title.
        department: Department name.
        description: Job description.
        requirements: Job requirements.

    Returns:
        Dictionary containing the created job.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        job = await service.create_job(
            title, department, description, requirements, user_id=get_current_user_id()
        )
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_job(job_id: str) -> dict:
    """Retrieve a job by ID.

    Args:
        job_id: The unique job ID.

    Returns:
        Dictionary containing the job details.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        job = await service.get_job(job_id, user_id=get_current_user_id())
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_job(job_id: str, status: str = None, description: str = None) -> dict:
    """Update a job posting.

    Args:
        job_id: The unique job ID.
        status: New status (draft, published, closed).
        description: New description.

    Returns:
        Dictionary confirming the update.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        job = await service.update_job(
            job_id,
            status=status,
            description=description,
            user_id=get_current_user_id(),
        )
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_jobs(status: str = None, department: str = None) -> dict:
    """List job postings with optional filters.

    Args:
        status: Filter by status.
        department: Filter by department.

    Returns:
        Dictionary containing list of jobs.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        jobs = await service.list_jobs(
            status=status, department=department, user_id=get_current_user_id()
        )
        return {"success": True, "jobs": jobs, "count": len(jobs)}
    except Exception as e:
        return {"success": False, "error": str(e), "jobs": []}


async def add_candidate(
    name: str, email: str, job_id: str, resume_url: str = None
) -> dict:
    """Add a new candidate application.

    Args:
        name: Candidate name.
        email: Candidate email.
        job_id: ID of the job they are applying for.
        resume_url: Optional URL to resume.

    Returns:
        Dictionary containing the new candidate record.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        candidate = await service.add_candidate(
            name, email, job_id, resume_url=resume_url, user_id=get_current_user_id()
        )
        return {"success": True, "candidate": candidate}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_candidate_status(candidate_id: str, status: str) -> dict:
    """Update a candidate's status.

    Args:
        candidate_id: The unique candidate ID.
        status: New status (applied, interviewing, offer, rejected, hired).

    Returns:
        Dictionary confirming the update.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        candidate = await service.update_candidate_status(
            candidate_id, status, user_id=get_current_user_id()
        )
        return {"success": True, "candidate": candidate}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_candidates(job_id: str = None, status: str = None) -> dict:
    """List candidates filtered by job or status.

    Args:
        job_id: Filter by job ID.
        status: Filter by candidate status.

    Returns:
        Dictionary containing list of candidates.
    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        candidates = await service.list_candidates(
            job_id=job_id, status=status, user_id=get_current_user_id()
        )
        return {"success": True, "candidates": candidates, "count": len(candidates)}
    except Exception as e:
        return {"success": False, "error": str(e), "candidates": []}


# ==========================
# Salary Benchmarking Helpers
# ==========================

# Base salary bands by seniority level (USD annual, derived from
# compensation_benchmarking skill percentile framework).
_SENIORITY_BANDS: dict[str, tuple[int, int]] = {
    "junior": (50_000, 75_000),
    "entry": (50_000, 75_000),
    "mid": (75_000, 110_000),
    "senior": (110_000, 160_000),
    "lead": (150_000, 220_000),
    "principal": (150_000, 220_000),
    "executive": (180_000, 300_000),
    "director": (180_000, 300_000),
}

# Department-level salary modifiers (multiplier applied to base band).
_DEPARTMENT_MODIFIERS: dict[str, float] = {
    "engineering": 1.15,
    "data": 1.15,
    "sales": 1.05,
    "marketing": 1.05,
    "operations": 1.00,
    "hr": 1.00,
    "human resources": 1.00,
    "support": 0.90,
    "customer support": 0.90,
}


def _compute_salary_band(
    seniority_level: str,
    department: str,
) -> tuple[int, int]:
    """Compute a salary band based on seniority and department.

    Args:
        seniority_level: Job seniority tier (junior, mid, senior, lead, executive).
        department: Department name for modifier lookup.

    Returns:
        Tuple of (salary_min, salary_max) as integers.

    """
    level = seniority_level.lower().strip()
    base_min, base_max = _SENIORITY_BANDS.get(level, _SENIORITY_BANDS["mid"])

    dept_key = department.lower().strip()
    modifier = _DEPARTMENT_MODIFIERS.get(dept_key, 1.00)

    return int(base_min * modifier), int(base_max * modifier)


# ==========================
# Job Description Generator
# ==========================


async def generate_job_description(
    title: str,
    department: str,
    seniority_level: str = "mid",
    key_skills: str = "",
    location: str = "remote",
) -> dict:
    """Generate a complete job description with salary benchmarking.

    Produces a structured job posting with responsibilities, requirements,
    compensation range, and persists it via RecruitmentService.

    Args:
        title: Job title (e.g. "Marketing Manager").
        department: Department name (e.g. "Marketing").
        seniority_level: Seniority tier: junior, mid, senior, lead, executive.
        key_skills: Comma-separated key skills for the role.
        location: Work location (default: remote).

    Returns:
        Dictionary with success flag, persisted job record, and formatted description.

    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        salary_min, salary_max = _compute_salary_band(seniority_level, department)

        # Build structured job description sections
        skills_list = [s.strip() for s in key_skills.split(",") if s.strip()]
        skills_text = (
            ", ".join(skills_list) if skills_list else "relevant domain expertise"
        )

        responsibilities = _build_responsibilities(department, seniority_level)
        requirements_must = _build_requirements_must(
            department, seniority_level, skills_text
        )
        requirements_nice = _build_requirements_nice(department, seniority_level)

        description = (
            f"## {title} -- {department}\n\n"
            f"**Location:** {location}\n"
            f"**Seniority:** {seniority_level.capitalize()}\n\n"
            "### Overview\n\n"
            f"We are looking for a {seniority_level}-level {title} to join our "
            f"{department} team. This role requires strong {skills_text} expertise "
            "and the ability to drive impactful outcomes in a fast-paced "
            "environment.\n\n"
            "### Responsibilities\n\n"
            f"{responsibilities}\n\n"
            "### Requirements\n\n"
            "**Must-haves:**\n"
            f"{requirements_must}\n\n"
            "**Nice-to-haves:**\n"
            f"{requirements_nice}\n\n"
            "### Compensation\n\n"
            f"- **Salary Range:** ${salary_min:,} - ${salary_max:,} per year\n"
            "- Compensation is commensurate with experience and qualifications.\n\n"
            "### Benefits\n\n"
            "- Comprehensive health, dental, and vision insurance\n"
            "- Flexible PTO and remote work options\n"
            "- Professional development budget\n"
            "- 401(k) with company match\n"
            "- Equity participation (where applicable)\n\n"
            "### How to Apply\n\n"
            "Submit your resume and a brief cover letter explaining why you are "
            "a great fit for this role. We review applications on a rolling basis.\n"
        )

        # Persist to database
        service = RecruitmentService()
        job = await service.create_job(
            title=title,
            department=department,
            description=description,
            requirements=requirements_must + "\n" + requirements_nice,
            status="draft",
            user_id=get_current_user_id(),
            salary_min=salary_min,
            salary_max=salary_max,
            seniority_level=seniority_level,
            responsibilities=responsibilities,
        )

        return {
            "success": True,
            "job": job,
            "job_description": description,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_responsibilities(department: str, seniority: str) -> str:
    """Build a responsibilities section based on role context.

    Args:
        department: Department name.
        seniority: Seniority level string.

    Returns:
        Formatted bullet-list string of responsibilities.

    """
    dept = department.lower().strip()
    level = seniority.lower().strip()

    dept_map: dict[str, list[str]] = {
        "engineering": [
            "Design, develop, and maintain scalable software systems",
            "Participate in code reviews and uphold engineering standards",
            "Collaborate with product and design teams on requirements",
            "Write and maintain comprehensive tests and documentation",
            "Resolve performance bottlenecks and technical debt",
        ],
        "marketing": [
            "Develop and execute multi-channel marketing strategies",
            "Analyze campaign performance metrics and optimize ROI",
            "Manage brand messaging and positioning across touchpoints",
            "Coordinate with sales, product, and creative on GTM plans",
            "Conduct market research for trends and opportunities",
        ],
        "sales": [
            "Build and manage a sales pipeline to meet revenue targets",
            "Develop relationships with prospects and existing clients",
            "Prepare and deliver compelling sales presentations",
            "Negotiate contracts aligned with company objectives",
            "Track and report on sales metrics and forecasts",
        ],
        "data": [
            "Build and maintain data pipelines and analytics infra",
            "Develop dashboards, reports, and self-service tools",
            "Translate business questions into data analyses",
            "Ensure data quality, integrity, and governance standards",
            "Apply statistical and ML methods for actionable insights",
        ],
        "hr": [
            "Manage end-to-end recruitment and candidate experience",
            "Develop and implement HR policies aligned with culture",
            "Administer benefits, compensation, and performance programs",
            "Support employee relations and engagement initiatives",
            "Ensure compliance with labor laws and policies",
        ],
        "operations": [
            "Streamline and optimize operational workflows",
            "Monitor KPIs and drive continuous improvement",
            "Coordinate cross-functional projects and resources",
            "Manage vendor relationships and procurement activities",
            "Develop and maintain standard operating procedures",
        ],
    }

    base_items = dept_map.get(
        dept,
        [
            f"Drive {department} initiatives aligned with strategy",
            f"Collaborate cross-functionally on {department} projects",
            "Analyze data and metrics to inform decision-making",
            "Prepare reports and presentations for stakeholders",
            "Identify and implement process improvements",
        ],
    )

    # Seniority-specific additions
    if level in ("senior", "lead", "principal", "executive", "director"):
        base_items = [
            *base_items,
            "Mentor and guide junior team members on best practices",
            "Contribute to strategic planning and roadmap definition",
        ]
    if level in ("lead", "principal", "executive", "director"):
        base_items = [
            *base_items,
            "Lead cross-departmental initiatives in executive forums",
        ]

    return "\n".join(f"- {item}" for item in base_items[:8])


def _build_requirements_must(
    department: str, seniority: str, skills_text: str
) -> str:
    """Build must-have requirements.

    Args:
        department: Department name.
        seniority: Seniority level string.
        skills_text: Comma-separated skills string.

    Returns:
        Formatted bullet-list string of must-have requirements.

    """
    level = seniority.lower().strip()

    years_map = {
        "junior": "1-2",
        "entry": "0-1",
        "mid": "3-5",
        "senior": "5-8",
        "lead": "7-10",
        "principal": "8-12",
        "executive": "10+",
        "director": "10+",
    }
    years = years_map.get(level, "3-5")

    items = [
        f"{years} years of experience in {department.lower()} or a related field",
        f"Demonstrated expertise in {skills_text}",
        "Strong analytical and problem-solving skills",
        "Excellent written and verbal communication abilities",
        f"Proven track record of delivering results in a {level}-level role",
    ]

    if level in ("senior", "lead", "principal", "executive", "director"):
        items = [
            *items,
            "Experience leading projects and mentoring team members",
            "Strategic thinking with the ability to translate vision into execution",
        ]

    return "\n".join(f"- {item}" for item in items[:7])


def _build_requirements_nice(department: str, seniority: str) -> str:
    """Build nice-to-have requirements.

    Args:
        department: Department name.
        seniority: Seniority level string.

    Returns:
        Formatted bullet-list string of nice-to-have requirements.

    """
    dept = department.lower().strip()
    items = [
        "Experience in a fast-paced, high-growth environment",
        f"Familiarity with industry-standard {dept} tools and platforms",
        "Advanced degree or relevant certifications",
    ]
    if seniority.lower() in ("senior", "lead", "principal"):
        items.append("Prior experience in a startup or scaling company")

    return "\n".join(f"- {item}" for item in items[:4])


# ==========================
# Interview Question Generator
# ==========================

# Department-specific technical question templates.
_DEPT_TECHNICAL_QUESTIONS: dict[str, list[str]] = {
    "engineering": [
        "Walk us through how you would design a {level} system "
        "to handle {competency}. What trade-offs would you consider?",
        "Describe your approach to debugging a production issue "
        "related to {competency}.",
    ],
    "marketing": [
        "How would you measure the ROI of a campaign focused "
        "on {competency}? Walk us through your analytics approach.",
        "Describe how you would develop a strategy for "
        "{competency} with a limited budget.",
    ],
    "sales": [
        "Walk us through your pipeline management approach "
        "when dealing with {competency}.",
        "How do you handle objections related to {competency} "
        "during a complex enterprise deal?",
    ],
    "data": [
        "How would you design a data pipeline for {competency}? "
        "What tools and validation steps would you include?",
        "Describe your approach to ensuring data quality "
        "when working on {competency}.",
    ],
    "hr": [
        "Describe how you would handle an employee relations "
        "scenario involving {competency}.",
        "How would you design a policy framework "
        "addressing {competency}?",
    ],
    "operations": [
        "How would you optimize a workflow related "
        "to {competency}? What metrics would you track?",
        "Describe your approach to vendor management "
        "when dealing with {competency}.",
    ],
}

# Seniority-adjusted question prefixes for behavioral questions.
_SENIORITY_BEHAVIORAL: dict[str, str] = {
    "junior": (
        "Describe a time when you were learning about {competency}. "
        "What was the situation, what steps did you take, "
        "and what did you learn?"
    ),
    "entry": (
        "Tell me about a project or coursework where you applied "
        "{competency}. What was the task, how did you approach it, "
        "and what was the outcome?"
    ),
    "mid": (
        "Describe a situation where you independently managed "
        "{competency}. What was the challenge, what actions "
        "did you take, and what was the result?"
    ),
    "senior": (
        "Tell me about a time you led an initiative involving "
        "{competency} that had significant business impact. "
        "What was the situation, your strategy, and the outcome?"
    ),
    "lead": (
        "Describe a situation where you drove organizational "
        "change around {competency}. What was the strategic "
        "context, how did you lead the effort, and what was "
        "the measurable impact?"
    ),
    "executive": (
        "Tell me about a strategic decision you made regarding "
        "{competency} that affected the entire organization. "
        "What was at stake, what was your approach, "
        "and what were the results?"
    ),
}


async def generate_interview_questions(
    job_id: str,
    focus_areas: str = "",
    num_questions: int = 8,
) -> dict:
    """Generate role-specific interview questions with scoring rubric.

    Fetches the job details, parses competencies from requirements,
    and generates STAR behavioral and department-specific technical
    questions tailored to the role's seniority level.

    Args:
        job_id: ID of the job to generate questions for.
        focus_areas: Optional comma-separated focus areas to emphasize.
        num_questions: Target number of questions (default: 8).

    Returns:
        Dictionary with questions, scoring rubric, and interview guide.

    """
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        job = await service.get_job(job_id, user_id=get_current_user_id())

        title = job.get("title", "Unknown Role")
        department = job.get("department", "General")
        seniority = job.get("seniority_level", "mid") or "mid"
        requirements = job.get("requirements", "")

        # Parse competencies from requirements text
        competencies = _parse_competencies(requirements, focus_areas)

        # Generate behavioral questions (one per competency)
        questions: list[dict] = []
        scoring_rubric: dict[str, dict] = {}

        level = seniority.lower().strip()
        template = _SENIORITY_BEHAVIORAL.get(
            level, _SENIORITY_BEHAVIORAL["mid"]
        )

        for comp in competencies:
            q_text = template.format(competency=comp)
            questions.append({
                "question": q_text,
                "competency": comp,
                "category": "behavioral",
                "seniority_target": level,
            })
            scoring_rubric[comp] = {
                1: f"Cannot articulate experience with {comp}",
                3: f"Demonstrates working knowledge of {comp} "
                   f"with concrete examples",
                5: f"Shows mastery of {comp} with measurable "
                   f"impact and strategic thinking",
            }

        # Add department-specific technical questions
        dept_key = department.lower().strip()
        dept_templates = _DEPT_TECHNICAL_QUESTIONS.get(
            dept_key, _DEPT_TECHNICAL_QUESTIONS.get("operations", [])
        )
        for i, tmpl in enumerate(dept_templates):
            comp = competencies[i % len(competencies)] if competencies else "the role"
            q_text = tmpl.format(competency=comp, level=level)
            questions.append({
                "question": q_text,
                "competency": comp,
                "category": "technical",
                "seniority_target": level,
            })
            rubric_key = f"technical_{comp}"
            scoring_rubric[rubric_key] = {
                1: f"Cannot demonstrate technical depth in {comp}",
                3: f"Shows solid technical understanding of {comp}",
                5: f"Exhibits expert-level technical mastery of "
                   f"{comp} with innovative approaches",
            }

        # Trim to requested count
        questions = questions[:num_questions]

        # Build formatted interview guide
        guide_lines = [
            f"# Interview Guide: {title}",
            f"**Department:** {department}",
            f"**Seniority:** {seniority.capitalize()}",
            f"**Total Questions:** {len(questions)}",
            "",
        ]
        for idx, q in enumerate(questions, 1):
            guide_lines.append(
                f"**Q{idx} [{q['category'].upper()}] "
                f"({q['competency']}):**"
            )
            guide_lines.append(q["question"])
            guide_lines.append("")

        guide_lines.append("## Scoring Rubric")
        for comp_name, scores in scoring_rubric.items():
            guide_lines.append(f"\n**{comp_name}:**")
            for score, desc in scores.items():
                guide_lines.append(f"  {score} - {desc}")

        return {
            "success": True,
            "job_title": title,
            "questions": questions,
            "scoring_rubric": scoring_rubric,
            "interview_guide": "\n".join(guide_lines),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _parse_competencies(
    requirements: str, focus_areas: str = ""
) -> list[str]:
    """Parse competency list from requirements and focus areas text.

    Args:
        requirements: Raw requirements text (comma or newline separated).
        focus_areas: Optional additional focus areas.

    Returns:
        Deduplicated list of competency strings.

    """
    raw = requirements + ", " + focus_areas if focus_areas else requirements
    # Split on commas, newlines, and bullet points
    parts: list[str] = []
    for segment in raw.replace("\n", ",").replace("- ", ",").split(","):
        cleaned = segment.strip().strip("-").strip()
        if cleaned and len(cleaned) > 1:
            parts.append(cleaned)

    # Deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


# ==========================
# Hiring Funnel Tools
# ==========================


async def get_hiring_funnel(job_id: str | None = None) -> dict:
    """Get the hiring funnel visualization data for a specific job or all open positions.

    Shows candidate counts per stage (applied, screening, interviewing, offer, hired)
    with conversion rates between stages for pipeline analysis.

    Args:
        job_id: Optional job ID. If omitted, returns funnel for all open positions.

    Returns:
        Dictionary with success flag and funnel data.
    """
    from app.services.hiring_funnel_service import HiringFunnelService

    try:
        from app.services.request_context import get_current_user_id

        service = HiringFunnelService()
        if job_id:
            data = await service.get_funnel_for_job(
                job_id, user_id=get_current_user_id()
            )
        else:
            data = await service.get_funnel_summary(user_id=get_current_user_id())
        return {"success": True, "funnel": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==========================
# Training Assignment Tools
# ==========================


async def assign_training(
    training_name: str = "Training Module",
    assignee: str = "Team",
    description: str = "",
    due_date: str = "",
) -> dict:
    """Assign a training module to a team member or team.

    Creates a durable training_assignment record in the database and logs
    an audit event. Replaces the degraded placeholder (Phase 65-04 HR-06).

    Args:
        training_name: Name of the training module to assign.
        assignee: Person or team to assign the training to.
        description: Optional description of the training assignment.
        due_date: Optional due date in YYYY-MM-DD format.

    Returns:
        Dictionary with success flag, status, and the assignment record.
    """
    from app.agents.data.tools import track_event
    from app.services.training_service import TrainingService

    try:
        from app.services.request_context import get_current_user_id

        service = TrainingService()
        assignment = await service.assign_training(
            training_name=training_name,
            assignee=assignee,
            description=description or None,
            due_date=due_date or None,
            user_id=get_current_user_id(),
        )

        await track_event(
            event_name="assign_training",
            category="hr",
            properties=f'{{"training_name":"{training_name}","assignee":"{assignee}"}}',
        )

        return {
            "success": True,
            "status": "completed",
            "assignment": assignment,
            "tool": "assign_training",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "tool": "assign_training"}


# ==========================
# Job Board Tools
# ==========================


async def post_job_board(
    role: str = "Open Role",
    job_id: str = "",
    department: str = "",
) -> dict:
    """Publish a job posting to the job board.

    If job_id is provided, publishes that specific job. Otherwise searches
    for a draft job matching the role title (case-insensitive) and publishes it.
    If no matching draft exists, creates a new published job.

    Replaces the degraded placeholder (Phase 65-04 HR-06).

    Args:
        role: Job title / role name to publish.
        job_id: Optional specific job ID to publish.
        department: Optional department for new job creation.

    Returns:
        Dictionary with success flag, status, and the job record.
    """
    from app.agents.data.tools import track_event
    from app.services.recruitment_service import RecruitmentService

    try:
        from app.services.request_context import get_current_user_id

        service = RecruitmentService()
        user_id = get_current_user_id()

        if job_id:
            # Publish specific job by ID
            job = await service.update_job(
                job_id, status="published", user_id=user_id
            )
        else:
            # Search for a matching draft job
            drafts = await service.list_jobs(status="draft", user_id=user_id)
            matching = None
            for draft in drafts:
                if role.lower() in draft.get("title", "").lower():
                    matching = draft
                    break

            if matching:
                job = await service.update_job(
                    matching["id"], status="published", user_id=user_id
                )
            else:
                # Create a new published job
                job = await service.create_job(
                    title=role,
                    department=department or "General",
                    description=f"Published job posting for {role}",
                    requirements="See job description",
                    status="published",
                    user_id=user_id,
                )

        await track_event(
            event_name="post_job_board",
            category="hr",
            properties=f'{{"role":"{role}","job_id":"{job.get("id", "")}"}}',
        )

        return {
            "success": True,
            "status": "completed",
            "job": job,
            "tool": "post_job_board",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "tool": "post_job_board"}


# ==========================
# Department-Specific Onboarding Equipment
# ==========================

_DEPARTMENT_EQUIPMENT: dict[str, list[str]] = {
    "engineering": [
        "Laptop with development specs",
        "External monitors (2x)",
        "IDE license (JetBrains / VS Code extensions)",
        "GitHub / GitLab access",
        "CI/CD pipeline credentials",
    ],
    "data": [
        "Laptop with development specs",
        "External monitors (2x)",
        "IDE license and notebook environment",
        "Data warehouse read access",
        "BI tool licenses (Tableau / Looker)",
    ],
    "marketing": [
        "Laptop",
        "Design tool licenses (Figma / Canva Pro)",
        "Analytics platform access (GA4 / Mixpanel)",
        "Social media management accounts",
        "Brand asset library access",
    ],
    "sales": [
        "Laptop",
        "CRM access (HubSpot / Salesforce)",
        "Phone/headset for calls",
        "Sales enablement platform access",
        "Demo environment credentials",
    ],
    "hr": [
        "Laptop",
        "HRIS platform access",
        "Applicant tracking system access",
        "Payroll system credentials",
    ],
    "operations": [
        "Laptop",
        "Project management tool access",
        "Vendor management portal credentials",
        "Internal wiki editor access",
    ],
    "support": [
        "Laptop",
        "Help desk platform access",
        "Knowledge base editor access",
        "Phone/headset for calls",
    ],
}

_STANDARD_PRE_BOARDING: list[str] = [
    "Company email account setup",
    "Slack / Teams workspace invitation",
    "Building access badge / VPN credentials",
    "Welcome package shipped",
    "Buddy / onboarding mentor assigned",
]

_STANDARD_DAY_1: list[str] = [
    "Welcome meeting with manager",
    "IT setup and equipment walkthrough",
    "HR paperwork and benefits enrollment",
    "Office tour (virtual or in-person)",
    "Lunch with the team",
    "End-of-day check-in with buddy",
]

_STANDARD_WEEK_1: list[str] = [
    "Compliance and security training",
    "1:1 meetings with each team member",
    "Read team documentation and wiki",
    "Shadow key meetings and standups",
    "Complete first starter task",
    "Buddy check-in (end of week)",
]

_DEPARTMENT_TRAINING: dict[str, list[str]] = {
    "engineering": [
        "Codebase walkthrough",
        "Architecture overview",
        "Dev environment setup guide",
    ],
    "data": [
        "Data dictionary review",
        "Pipeline architecture walkthrough",
        "Query standards training",
    ],
    "marketing": [
        "Brand guidelines review",
        "Campaign analytics walkthrough",
        "Content calendar orientation",
    ],
    "sales": [
        "Product demo training",
        "CRM workflow walkthrough",
        "Sales playbook review",
    ],
    "hr": [
        "HRIS system training",
        "Compliance framework review",
        "Recruitment process walkthrough",
    ],
    "operations": [
        "SOP library review",
        "Vendor management walkthrough",
        "Process documentation training",
    ],
    "support": [
        "Help desk workflow training",
        "Escalation process review",
        "Knowledge base orientation",
    ],
}

_SENIORITY_MILESTONES: dict[str, dict[str, str]] = {
    "junior": {
        "30_days": "Learn core systems, complete all onboarding training, deliver first guided task",
        "60_days": "Own small features or tasks independently, contribute to team processes",
        "90_days": "Deliver consistent independent work, participate in planning discussions",
    },
    "entry": {
        "30_days": "Complete onboarding, learn team workflows, shadow senior team members",
        "60_days": "Handle routine tasks independently, start contributing to projects",
        "90_days": "Demonstrate growing autonomy, take ownership of a small workstream",
    },
    "mid": {
        "30_days": "Ramp on core systems and processes, build relationships across team",
        "60_days": "Own projects independently, identify improvement opportunities",
        "90_days": "Full contributor driving outcomes, mentor newer team members",
    },
    "senior": {
        "30_days": "Deep-dive into systems, identify technical debt or process gaps",
        "60_days": "Lead a project or initiative, propose architectural improvements",
        "90_days": "Drive strategic outcomes, mentor the team, influence roadmap",
    },
    "lead": {
        "30_days": "Understand organizational landscape, meet all stakeholders, assess team dynamics",
        "60_days": "Define team strategy and roadmap, establish leadership rhythm",
        "90_days": "Drive cross-functional initiatives, deliver measurable organizational impact",
    },
    "executive": {
        "30_days": "Assess organizational state, build executive relationships, define vision",
        "60_days": "Launch strategic initiatives, align team with company objectives",
        "90_days": "Deliver transformational results, establish thought leadership",
    },
}


def _build_onboarding_checklist(department: str, seniority: str) -> dict:
    """Build a department- and seniority-specific onboarding checklist.

    Args:
        department: Department name.
        seniority: Seniority level string.

    Returns:
        Dictionary with pre_boarding, day_1, week_1, thirty_sixty_ninety sections.
    """
    dept_key = department.lower().strip()
    level = seniority.lower().strip()

    # Pre-boarding: department equipment + standard items
    dept_equipment = _DEPARTMENT_EQUIPMENT.get(
        dept_key, _DEPARTMENT_EQUIPMENT.get("operations", [])
    )
    pre_boarding = [*dept_equipment, *_STANDARD_PRE_BOARDING]

    # Day 1: standard items
    day_1 = list(_STANDARD_DAY_1)

    # Week 1: standard items + department-specific training
    dept_training = _DEPARTMENT_TRAINING.get(
        dept_key, ["Team-specific onboarding modules"]
    )
    week_1 = [*_STANDARD_WEEK_1, *dept_training]

    # 30-60-90: seniority-specific milestones
    milestones = _SENIORITY_MILESTONES.get(level, _SENIORITY_MILESTONES["mid"])

    return {
        "pre_boarding": pre_boarding,
        "day_1": day_1,
        "week_1": week_1,
        "thirty_sixty_ninety": milestones,
    }


# ==========================
# Auto-Onboarding Tool
# ==========================


async def auto_generate_onboarding(candidate_id: str) -> dict:
    """Auto-generate an onboarding checklist for a hired candidate.

    Fetches the candidate and their job details, generates a department-
    and seniority-specific onboarding checklist, and registers the hired
    candidate as a team member in the org chart.

    Args:
        candidate_id: The UUID of the hired candidate.

    Returns:
        Dictionary with success flag, onboarding_checklist, and team_member record.
    """
    from app.services.recruitment_service import RecruitmentService
    from app.services.team_org_service import TeamOrgService

    try:
        from app.services.request_context import get_current_user_id

        user_id = get_current_user_id()

        # Fetch candidate and job details
        recruit_service = RecruitmentService()
        candidate = await recruit_service.get_candidate(candidate_id, user_id=user_id)
        job = await recruit_service.get_job(candidate["job_id"], user_id=user_id)

        department = job.get("department", "General")
        seniority = job.get("seniority_level", "mid") or "mid"
        title = job.get("title", candidate.get("name", "New Hire"))

        # Build onboarding checklist
        checklist = _build_onboarding_checklist(department, seniority)

        # Create team member record
        org_service = TeamOrgService()
        member = await org_service.add_team_member(
            name=candidate["name"],
            email=candidate.get("email"),
            position=title,
            department=department,
            candidate_id=candidate["id"],
            job_id=job["id"],
            user_id=user_id,
        )

        return {
            "success": True,
            "onboarding_checklist": checklist,
            "team_member": member,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==========================
# Team Org Chart Tool
# ==========================


async def get_team_org_chart(department: str | None = None) -> dict:
    """Get the team organization chart showing members and open positions.

    Retrieves the human team org chart with reporting relationships
    and vacancy nodes from published recruitment jobs.

    Args:
        department: Optional department filter. If provided, only returns
            members and positions in that department.

    Returns:
        Dictionary with success flag and org_chart data.
    """
    from app.services.team_org_service import TeamOrgService

    try:
        from app.services.request_context import get_current_user_id

        service = TeamOrgService()
        data = await service.get_org_chart(user_id=get_current_user_id())

        # Filter by department if specified
        if department:
            dept_lower = department.lower().strip()
            data["members"] = [
                m
                for m in data["members"]
                if (m.get("department") or "").lower().strip() == dept_lower
            ]
            data["open_positions"] = [
                p
                for p in data["open_positions"]
                if (p.get("department") or "").lower().strip() == dept_lower
            ]
            data["departments"] = [
                d
                for d in data["departments"]
                if d.lower().strip() == dept_lower
            ]

        return {"success": True, "org_chart": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
