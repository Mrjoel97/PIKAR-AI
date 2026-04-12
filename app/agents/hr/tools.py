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
