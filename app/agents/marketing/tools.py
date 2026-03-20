# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Marketing Automation Agent."""


async def create_campaign(name: str, campaign_type: str, target_audience: str) -> dict:
    """Create a new marketing campaign.

    Args:
        name: Campaign name.
        campaign_type: Type (email, social, content, paid_ads).
        target_audience: Target audience description.

    Returns:
        Dictionary containing the created campaign.
    """
    from app.services.campaign_service import CampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignService()
        campaign = await service.create_campaign(
            name, campaign_type, target_audience, user_id=get_current_user_id()
        )
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_campaign(campaign_id: str) -> dict:
    """Retrieve a campaign by ID.

    Args:
        campaign_id: The unique campaign ID.

    Returns:
        Dictionary containing the campaign details.
    """
    from app.services.campaign_service import CampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignService()
        campaign = await service.get_campaign(
            campaign_id, user_id=get_current_user_id()
        )
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_campaign(
    campaign_id: str, status: str = None, name: str = None
) -> dict:
    """Update a campaign's status or name.

    Args:
        campaign_id: The unique campaign ID.
        status: New status (draft, active, paused, completed).
        name: New campaign name.

    Returns:
        Dictionary confirming the update.
    """
    from app.services.campaign_service import CampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignService()
        campaign = await service.update_campaign(
            campaign_id, status=status, name=name, user_id=get_current_user_id()
        )
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_campaigns(status: str = None, campaign_type: str = None) -> dict:
    """List campaigns with optional filters.

    Args:
        status: Filter by campaign status.
        campaign_type: Filter by campaign type.

    Returns:
        Dictionary containing list of campaigns.
    """
    from app.services.campaign_service import CampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignService()
        campaigns = await service.list_campaigns(
            status=status, campaign_type=campaign_type, user_id=get_current_user_id()
        )
        return {"success": True, "campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        return {"success": False, "error": str(e), "campaigns": []}


async def record_campaign_metrics(
    campaign_id: str, impressions: int = 0, clicks: int = 0, conversions: int = 0
) -> dict:
    """Record performance metrics for a campaign.

    Args:
        campaign_id: The unique campaign ID.
        impressions: Number of impressions.
        clicks: Number of clicks.
        conversions: Number of conversions.

    Returns:
        Dictionary with updated campaign metrics.
    """
    from app.services.campaign_service import CampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignService()
        result = await service.record_metrics(
            campaign_id, impressions, clicks, conversions, user_id=get_current_user_id()
        )
        return {"success": True, "campaign": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Blog Post Tools
# =============================================================================


async def create_blog_post(
    title: str,
    content: str = "",
    excerpt: str = None,
    category: str = None,
    tags: list[str] = None,
    seo_metadata: dict = None,
    featured_image_url: str = None,
    campaign_id: str = None,
) -> dict:
    """Create a new blog post draft with SEO metadata.

    Args:
        title: Blog post title.
        content: Blog post body in markdown or HTML.
        excerpt: Short summary for previews and social sharing.
        category: Blog category (e.g., 'marketing', 'product', 'industry').
        tags: List of tags for the post.
        seo_metadata: SEO metadata dict with keys: meta_title, meta_description, keywords, focus_keyword, og_image_url.
        featured_image_url: URL to the featured/hero image.
        campaign_id: Optional campaign this blog post belongs to.

    Returns:
        Dictionary containing the created blog post.
    """
    from app.services.blog_service import BlogService

    try:
        from app.services.request_context import get_current_user_id

        service = BlogService()
        post = await service.create_blog_post(
            title=title,
            content=content,
            excerpt=excerpt,
            category=category,
            tags=tags,
            seo_metadata=seo_metadata,
            featured_image_url=featured_image_url,
            campaign_id=campaign_id,
            user_id=get_current_user_id(),
        )
        return {"success": True, "blog_post": post}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_blog_post(post_id: str) -> dict:
    """Retrieve a blog post by its ID.

    Args:
        post_id: The unique blog post ID.

    Returns:
        Dictionary containing the blog post details.
    """
    from app.services.blog_service import BlogService

    try:
        from app.services.request_context import get_current_user_id

        service = BlogService()
        post = await service.get_blog_post(post_id, user_id=get_current_user_id())
        return {"success": True, "blog_post": post}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_blog_post(
    post_id: str,
    title: str = None,
    content: str = None,
    excerpt: str = None,
    category: str = None,
    tags: list[str] = None,
    seo_metadata: dict = None,
    featured_image_url: str = None,
    status: str = None,
) -> dict:
    """Update a blog post's content, metadata, or status.

    Args:
        post_id: The unique blog post ID.
        title: New title.
        content: New content body.
        excerpt: New excerpt.
        category: New category.
        tags: New tags list.
        seo_metadata: Updated SEO metadata.
        featured_image_url: New featured image URL.
        status: New status (draft, review, scheduled, published, archived).

    Returns:
        Dictionary with the updated blog post.
    """
    from app.services.blog_service import BlogService

    try:
        from app.services.request_context import get_current_user_id

        service = BlogService()
        post = await service.update_blog_post(
            post_id=post_id,
            title=title,
            content=content,
            excerpt=excerpt,
            category=category,
            tags=tags,
            seo_metadata=seo_metadata,
            featured_image_url=featured_image_url,
            status=status,
            user_id=get_current_user_id(),
        )
        return {"success": True, "blog_post": post}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def publish_blog_post(post_id: str) -> dict:
    """Publish a blog post — sets status to 'published' and records the publish timestamp.

    Args:
        post_id: The unique blog post ID to publish.

    Returns:
        Dictionary with the published blog post.
    """
    from app.services.blog_service import BlogService

    try:
        from app.services.request_context import get_current_user_id

        service = BlogService()
        post = await service.publish_blog_post(post_id, user_id=get_current_user_id())
        return {"success": True, "blog_post": post}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_blog_posts(
    status: str = None,
    category: str = None,
    campaign_id: str = None,
) -> dict:
    """List blog posts with optional filters.

    Args:
        status: Filter by status (draft, review, scheduled, published, archived).
        category: Filter by category.
        campaign_id: Filter by campaign ID.

    Returns:
        Dictionary with list of blog posts.
    """
    from app.services.blog_service import BlogService

    try:
        from app.services.request_context import get_current_user_id

        service = BlogService()
        posts = await service.list_blog_posts(
            status=status,
            category=category,
            campaign_id=campaign_id,
            user_id=get_current_user_id(),
        )
        return {"success": True, "blog_posts": posts, "count": len(posts)}
    except Exception as e:
        return {"success": False, "error": str(e), "blog_posts": []}


# =============================================================================
# Content Calendar Tools
# =============================================================================


async def schedule_content(
    title: str,
    content_type: str,
    scheduled_date: str,
    platform: str = None,
    scheduled_time: str = None,
    description: str = None,
    campaign_id: str = None,
    blog_post_id: str = None,
    metadata: dict = None,
) -> dict:
    """Schedule a content item on the editorial content calendar.

    Args:
        title: Content title or name.
        content_type: Type of content (blog, social, email, video, newsletter, ad, other).
        scheduled_date: Date to publish in YYYY-MM-DD format.
        platform: Target platform (twitter, linkedin, facebook, instagram, tiktok, youtube, blog, email).
        scheduled_time: Time to publish in HH:MM format.
        description: Content description or brief.
        campaign_id: Optional campaign this content belongs to.
        blog_post_id: Optional linked blog post ID.
        metadata: Additional metadata (target_audience, cta, hashtags, utm_params, notes).

    Returns:
        Dictionary containing the created calendar item.
    """
    from app.services.content_calendar_service import ContentCalendarService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentCalendarService()
        item = await service.schedule_content(
            title=title,
            content_type=content_type,
            scheduled_date=scheduled_date,
            platform=platform,
            scheduled_time=scheduled_time,
            description=description,
            campaign_id=campaign_id,
            blog_post_id=blog_post_id,
            metadata=metadata,
            user_id=get_current_user_id(),
        )
        return {"success": True, "calendar_item": item}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_content_calendar(
    start_date: str = None,
    end_date: str = None,
    content_type: str = None,
    status: str = None,
    platform: str = None,
    campaign_id: str = None,
) -> dict:
    """List content calendar items within a date range with optional filters.

    Args:
        start_date: Start of date range (YYYY-MM-DD).
        end_date: End of date range (YYYY-MM-DD).
        content_type: Filter by content type (blog, social, email, video, newsletter, ad).
        status: Filter by status (planned, in_progress, ready, scheduled, published, cancelled).
        platform: Filter by platform.
        campaign_id: Filter by campaign ID.

    Returns:
        Dictionary with list of calendar items sorted by date.
    """
    from app.services.content_calendar_service import ContentCalendarService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentCalendarService()
        items = await service.list_calendar(
            start_date=start_date,
            end_date=end_date,
            content_type=content_type,
            status=status,
            platform=platform,
            campaign_id=campaign_id,
            user_id=get_current_user_id(),
        )
        return {"success": True, "calendar_items": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e), "calendar_items": []}


async def update_calendar_item(
    item_id: str,
    title: str = None,
    scheduled_date: str = None,
    scheduled_time: str = None,
    status: str = None,
    platform: str = None,
    description: str = None,
) -> dict:
    """Update a content calendar item.

    Args:
        item_id: The unique calendar item ID.
        title: New title.
        scheduled_date: New date (YYYY-MM-DD).
        scheduled_time: New time (HH:MM).
        status: New status (planned, in_progress, ready, scheduled, published, cancelled).
        platform: New target platform.
        description: New description.

    Returns:
        Dictionary with the updated calendar item.
    """
    from app.services.content_calendar_service import ContentCalendarService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentCalendarService()
        item = await service.update_calendar_item(
            item_id=item_id,
            title=title,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            status=status,
            platform=platform,
            description=description,
            user_id=get_current_user_id(),
        )
        return {"success": True, "calendar_item": item}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_calendar_item(item_id: str) -> dict:
    """Delete a content calendar item.

    Args:
        item_id: The unique calendar item ID to delete.

    Returns:
        Dictionary confirming deletion.
    """
    from app.services.content_calendar_service import ContentCalendarService

    try:
        from app.services.request_context import get_current_user_id

        service = ContentCalendarService()
        deleted = await service.delete_calendar_item(
            item_id, user_id=get_current_user_id()
        )
        return {"success": deleted}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Email Template Tools
# =============================================================================


async def create_email_template(
    name: str,
    subject: str,
    body_html: str,
    body_text: str = "",
    category: str = "general",
    variables: list[str] = None,
    ab_variants: list[dict] = None,
    campaign_id: str = None,
    metadata: dict = None,
) -> dict:
    """Create a new email template with optional A/B variants.

    Args:
        name: Template name (e.g., 'Welcome Series - Day 1').
        subject: Email subject line.
        body_html: HTML email body with optional {{variable}} placeholders.
        body_text: Plain text fallback version.
        category: Template category (welcome, nurture, promotional, transactional, newsletter, re_engagement, announcement, general).
        variables: List of placeholder variable names used in the template (e.g., ['first_name', 'company_name']).
        ab_variants: A/B test variants — list of dicts with keys: variant_name, subject, body_html, body_text.
        campaign_id: Optional campaign this template belongs to.
        metadata: Additional metadata (tone, audience_segment, preview_text, estimated_read_time).

    Returns:
        Dictionary containing the created email template.
    """
    from app.services.email_template_service import EmailTemplateService

    try:
        from app.services.request_context import get_current_user_id

        service = EmailTemplateService()
        template = await service.create_template(
            name=name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            category=category,
            variables=variables,
            ab_variants=ab_variants,
            campaign_id=campaign_id,
            metadata=metadata,
            user_id=get_current_user_id(),
        )
        return {"success": True, "email_template": template}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_email_template(template_id: str) -> dict:
    """Retrieve an email template by its ID.

    Args:
        template_id: The unique email template ID.

    Returns:
        Dictionary containing the email template details.
    """
    from app.services.email_template_service import EmailTemplateService

    try:
        from app.services.request_context import get_current_user_id

        service = EmailTemplateService()
        template = await service.get_template(
            template_id, user_id=get_current_user_id()
        )
        return {"success": True, "email_template": template}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_email_template(
    template_id: str,
    name: str = None,
    subject: str = None,
    body_html: str = None,
    body_text: str = None,
    category: str = None,
    variables: list[str] = None,
    ab_variants: list[dict] = None,
    status: str = None,
) -> dict:
    """Update an email template.

    Args:
        template_id: The unique email template ID.
        name: New name.
        subject: New subject line.
        body_html: New HTML body.
        body_text: New plain text body.
        category: New category.
        variables: Updated variable list.
        ab_variants: Updated A/B variants.
        status: New status (draft, active, archived).

    Returns:
        Dictionary with the updated email template.
    """
    from app.services.email_template_service import EmailTemplateService

    try:
        from app.services.request_context import get_current_user_id

        service = EmailTemplateService()
        template = await service.update_template(
            template_id=template_id,
            name=name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            category=category,
            variables=variables,
            ab_variants=ab_variants,
            status=status,
            user_id=get_current_user_id(),
        )
        return {"success": True, "email_template": template}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_email_templates(
    category: str = None,
    status: str = None,
    campaign_id: str = None,
) -> dict:
    """List email templates with optional filters.

    Args:
        category: Filter by category (welcome, nurture, promotional, etc.).
        status: Filter by status (draft, active, archived).
        campaign_id: Filter by campaign ID.

    Returns:
        Dictionary with list of email templates.
    """
    from app.services.email_template_service import EmailTemplateService

    try:
        from app.services.request_context import get_current_user_id

        service = EmailTemplateService()
        templates = await service.list_templates(
            category=category,
            status=status,
            campaign_id=campaign_id,
            user_id=get_current_user_id(),
        )
        return {"success": True, "email_templates": templates, "count": len(templates)}
    except Exception as e:
        return {"success": False, "error": str(e), "email_templates": []}


# =============================================================================
# Content Repurposing Tool
# =============================================================================


async def repurpose_content(
    source_content: str,
    source_type: str = "blog",
    target_formats: list[str] = None,
    tone: str = "professional",
    brand_context: str = "",
) -> dict:
    """Repurpose content from one format into multiple target formats.

    Takes a source piece of content (e.g., a blog post) and generates adapted
    versions for different channels. The agent should use this output to then
    save each variant via the appropriate tool (schedule_content, create_email_template, etc.).

    Args:
        source_content: The original content text to repurpose.
        source_type: Type of the source content (blog, newsletter, video_script, whitepaper).
        target_formats: List of target formats to generate. Options: twitter_thread, linkedin_post, instagram_caption, email_newsletter, video_script, infographic_outline, podcast_notes.
        tone: Desired tone (professional, casual, witty, authoritative, conversational).
        brand_context: Optional brand voice guidelines or context to maintain consistency.

    Returns:
        Dictionary with repurposed content variants keyed by format.
    """
    if not target_formats:
        target_formats = ["twitter_thread", "linkedin_post", "email_newsletter"]

    format_instructions = {
        "twitter_thread": "Convert into a Twitter/X thread (5-8 tweets, each ≤280 chars). Lead with a hook. Use line breaks between tweets. End with a CTA.",
        "linkedin_post": "Convert into a LinkedIn post (1200-1500 chars). Professional tone, include a hook, key insights, and a discussion question at the end.",
        "instagram_caption": "Convert into an Instagram caption (≤2200 chars). Engaging opener, value-driven body, relevant hashtags (15-20), and a CTA.",
        "email_newsletter": "Convert into an email newsletter section. Subject line, preview text, 3-paragraph body with key takeaways, and a primary CTA button text.",
        "video_script": "Convert into a 60-90 second video script. Include: hook (5s), problem (10s), solution (30s), proof (15s), CTA (10s). Write in spoken language.",
        "infographic_outline": "Convert into an infographic outline: title, subtitle, 5-7 data points or key facts, source citations, and a concluding statement.",
        "podcast_notes": "Convert into podcast show notes: episode title, 3-sentence summary, key timestamps/topics, guest bio placeholder, and related links section.",
    }

    variants = {}
    for fmt in target_formats:
        instruction = format_instructions.get(fmt)
        if instruction:
            variants[fmt] = {
                "format": fmt,
                "instruction": instruction,
                "source_type": source_type,
                "tone": tone,
                "brand_context": brand_context,
                "source_excerpt": source_content[:500] + "..."
                if len(source_content) > 500
                else source_content,
            }

    return {
        "success": True,
        "source_type": source_type,
        "target_formats": target_formats,
        "repurposing_briefs": variants,
        "total_variants": len(variants),
        "instruction": (
            "Use these briefs to generate each content variant. "
            "For each variant, adapt the source content following the format-specific instruction. "
            "Maintain the core message while optimizing for each platform's best practices. "
            f"Apply {tone} tone throughout. "
            + (f"Follow brand guidelines: {brand_context}" if brand_context else "")
        ),
    }


# =============================================================================
# Campaign Orchestrator Tools
# =============================================================================


async def get_campaign_phase(campaign_id: str) -> dict:
    """Get the current phase and full phase history for a campaign.

    Shows the campaign's lifecycle stage (draft → review → approved → active → completed)
    and all past phase transitions with timestamps and notes.

    Args:
        campaign_id: The unique campaign ID.

    Returns:
        Dictionary with current_phase, campaign details, and phase_history.
    """
    from app.services.campaign_orchestrator_service import CampaignOrchestratorService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignOrchestratorService()
        result = await service.get_campaign_phase(
            campaign_id, user_id=get_current_user_id()
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def advance_campaign_phase(
    campaign_id: str,
    target_phase: str,
    notes: str = None,
) -> dict:
    """Advance a campaign to the next lifecycle phase.

    Valid phases: draft, review, approved, active, completed, paused.
    Transitions: draft→review, review→approved (creates approval request),
    approved→active, active→completed. Any phase can pause.

    When moving from review→approved, an approval request is created and
    an approval link is returned. The campaign advances only after approval.

    Args:
        campaign_id: The unique campaign ID.
        target_phase: The phase to advance to.
        notes: Optional notes for the transition (e.g., reason for pausing).

    Returns:
        Dictionary with transition result and optional approval_link.
    """
    from app.services.campaign_orchestrator_service import CampaignOrchestratorService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignOrchestratorService()
        result = await service.advance_phase(
            campaign_id=campaign_id,
            target_phase=target_phase,
            notes=notes,
            user_id=get_current_user_id(),
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def approve_campaign(campaign_id: str, notes: str = None) -> dict:
    """Approve a campaign that's currently in review phase.

    Shortcut for direct approval in chat — skips the magic link flow.
    Only works when the campaign is in the 'review' phase.

    Args:
        campaign_id: The unique campaign ID.
        notes: Optional approval notes.

    Returns:
        Dictionary confirming approval.
    """
    from app.services.campaign_orchestrator_service import CampaignOrchestratorService

    try:
        from app.services.request_context import get_current_user_id

        service = CampaignOrchestratorService()
        result = await service.approve_campaign(
            campaign_id=campaign_id,
            notes=notes,
            user_id=get_current_user_id(),
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# UTM Tracking Tools
# =============================================================================


async def generate_utm_params(
    campaign_name: str,
    source: str,
    medium: str,
    term: str = None,
    content: str = None,
) -> dict:
    """Generate UTM tracking parameters for a campaign link.

    Creates a standardized UTM parameter set that can be appended to any URL
    for campaign attribution tracking.

    Args:
        campaign_name: The campaign name (utm_campaign). Will be slugified.
        source: Traffic source (utm_source) — e.g., 'twitter', 'linkedin', 'newsletter', 'google'.
        medium: Marketing medium (utm_medium) — e.g., 'social', 'email', 'cpc', 'organic'.
        term: Paid keyword term (utm_term) — optional, for paid search campaigns.
        content: Content differentiator (utm_content) — optional, for A/B testing different links.

    Returns:
        Dictionary with utm_params dict and a ready-to-append query string.
    """
    import re

    def slugify(text):
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")

    params = {
        "utm_source": slugify(source),
        "utm_medium": slugify(medium),
        "utm_campaign": slugify(campaign_name),
    }
    if term:
        params["utm_term"] = slugify(term)
    if content:
        params["utm_content"] = slugify(content)

    query_string = "&".join(f"{k}={v}" for k, v in params.items())

    return {
        "success": True,
        "utm_params": params,
        "query_string": query_string,
        "example_url": f"https://example.com/page?{query_string}",
        "instruction": (
            "Append these UTM parameters to any link shared in this campaign. "
            "Use the query_string value directly: ?{query_string} or &{query_string} if the URL already has parameters."
        ),
    }


async def save_campaign_utm(
    campaign_id: str,
    source: str,
    medium: str,
    term: str = None,
    content: str = None,
) -> dict:
    """Save UTM tracking configuration to a campaign for consistent attribution.

    Stores the UTM config on the campaign so all links generated for this
    campaign automatically use the same tracking parameters.

    Args:
        campaign_id: The unique campaign ID.
        source: Default traffic source (utm_source).
        medium: Default marketing medium (utm_medium).
        term: Default paid keyword term (utm_term).
        content: Default content differentiator (utm_content).

    Returns:
        Dictionary with the updated campaign.
    """
    from app.services.campaign_service import CampaignService

    try:
        from app.services.request_context import get_current_user_id

        utm_config = {
            "source": source,
            "medium": medium,
        }
        if term:
            utm_config["term"] = term
        if content:
            utm_config["content"] = content

        service = CampaignService()
        # Use the raw update to set utm_config
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        effective_user_id = get_current_user_id()
        client = service.client if service.is_authenticated else AdminService().client
        query = (
            client.table("campaigns")
            .update({"utm_config": utm_config})
            .eq("id", campaign_id)
        )
        if not service.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return {"success": True, "campaign": response.data[0]}
        raise Exception("No data returned from update")
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Audience & Persona Tools
# =============================================================================


async def create_audience(
    name: str,
    description: str = None,
    demographics: dict = None,
    psychographics: dict = None,
    behavioral: dict = None,
    estimated_size: int = None,
    tags: list[str] = None,
) -> dict:
    """Create a reusable marketing audience segment.

    Defines a target audience with demographics, psychographics, and behavioral
    attributes that can be linked to campaigns and personas.

    Args:
        name: Audience name (e.g., 'Tech-savvy millennials in SaaS').
        description: Detailed audience description.
        demographics: Demographic attributes — {age_range, gender, location, income_bracket, education, job_title}.
        psychographics: Psychographic attributes — {interests[], values[], pain_points[], motivations[], lifestyle}.
        behavioral: Behavioral attributes — {purchase_frequency, brand_loyalty, channel_preferences[], device_usage}.
        estimated_size: Estimated audience size (number of people).
        tags: Tags for organization and filtering.

    Returns:
        Dictionary containing the created audience.
    """
    from app.services.audience_service import AudienceService

    try:
        from app.services.request_context import get_current_user_id

        service = AudienceService()
        audience = await service.create_audience(
            name=name,
            description=description,
            demographics=demographics,
            psychographics=psychographics,
            behavioral=behavioral,
            estimated_size=estimated_size,
            tags=tags,
            user_id=get_current_user_id(),
        )
        return {"success": True, "audience": audience}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_audience(audience_id: str) -> dict:
    """Retrieve a marketing audience by ID.

    Args:
        audience_id: The unique audience ID.

    Returns:
        Dictionary containing the audience details.
    """
    from app.services.audience_service import AudienceService

    try:
        from app.services.request_context import get_current_user_id

        service = AudienceService()
        audience = await service.get_audience(
            audience_id, user_id=get_current_user_id()
        )
        return {"success": True, "audience": audience}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_audience(
    audience_id: str,
    name: str = None,
    description: str = None,
    demographics: dict = None,
    psychographics: dict = None,
    behavioral: dict = None,
    estimated_size: int = None,
    tags: list[str] = None,
) -> dict:
    """Update a marketing audience segment.

    Args:
        audience_id: The unique audience ID.
        name: New name.
        description: New description.
        demographics: Updated demographics.
        psychographics: Updated psychographics.
        behavioral: Updated behavioral data.
        estimated_size: Updated estimated size.
        tags: Updated tags.

    Returns:
        Dictionary with the updated audience.
    """
    from app.services.audience_service import AudienceService

    try:
        from app.services.request_context import get_current_user_id

        service = AudienceService()
        audience = await service.update_audience(
            audience_id=audience_id,
            name=name,
            description=description,
            demographics=demographics,
            psychographics=psychographics,
            behavioral=behavioral,
            estimated_size=estimated_size,
            tags=tags,
            user_id=get_current_user_id(),
        )
        return {"success": True, "audience": audience}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_audiences() -> dict:
    """List all saved marketing audiences.

    Returns:
        Dictionary with list of audience segments.
    """
    from app.services.audience_service import AudienceService

    try:
        from app.services.request_context import get_current_user_id

        service = AudienceService()
        audiences = await service.list_audiences(user_id=get_current_user_id())
        return {"success": True, "audiences": audiences, "count": len(audiences)}
    except Exception as e:
        return {"success": False, "error": str(e), "audiences": []}


async def delete_audience(audience_id: str) -> dict:
    """Delete a marketing audience segment.

    Args:
        audience_id: The unique audience ID to delete.

    Returns:
        Dictionary confirming deletion.
    """
    from app.services.audience_service import AudienceService

    try:
        from app.services.request_context import get_current_user_id

        service = AudienceService()
        deleted = await service.delete_audience(
            audience_id, user_id=get_current_user_id()
        )
        return {"success": deleted}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_persona(
    name: str,
    role_title: str = None,
    company_type: str = None,
    bio: str = None,
    goals: list[str] = None,
    pain_points: list[str] = None,
    objections: list[str] = None,
    preferred_channels: list[str] = None,
    content_preferences: dict = None,
    buying_journey_stage: str = "awareness",
    audience_id: str = None,
    tags: list[str] = None,
) -> dict:
    """Create a buyer persona for targeted marketing.

    Defines a detailed buyer persona with goals, pain points, objections,
    and content preferences. Can be linked to an audience segment.

    Args:
        name: Persona name (e.g., 'Startup Sarah', 'Enterprise Eric').
        role_title: Job title (e.g., 'VP of Marketing', 'CTO').
        company_type: Company description (e.g., 'SaaS startup, 20-50 employees').
        bio: Background narrative describing this persona.
        goals: List of goals this persona wants to achieve.
        pain_points: List of pain points and frustrations.
        objections: Common objections when evaluating solutions.
        preferred_channels: Preferred communication channels (email, linkedin, twitter, blog, etc.).
        content_preferences: Content preferences — {formats[], tone, length, frequency}.
        buying_journey_stage: Stage in buying journey (awareness, consideration, decision, retention).
        audience_id: Optional link to a marketing audience segment.
        tags: Tags for organization.

    Returns:
        Dictionary containing the created persona.
    """
    from app.services.audience_service import PersonaService

    try:
        from app.services.request_context import get_current_user_id

        service = PersonaService()
        persona = await service.create_persona(
            name=name,
            role_title=role_title,
            company_type=company_type,
            bio=bio,
            goals=goals,
            pain_points=pain_points,
            objections=objections,
            preferred_channels=preferred_channels,
            content_preferences=content_preferences,
            buying_journey_stage=buying_journey_stage,
            audience_id=audience_id,
            tags=tags,
            user_id=get_current_user_id(),
        )
        return {"success": True, "persona": persona}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_persona(persona_id: str) -> dict:
    """Retrieve a buyer persona by ID.

    Args:
        persona_id: The unique persona ID.

    Returns:
        Dictionary containing the persona details.
    """
    from app.services.audience_service import PersonaService

    try:
        from app.services.request_context import get_current_user_id

        service = PersonaService()
        persona = await service.get_persona(persona_id, user_id=get_current_user_id())
        return {"success": True, "persona": persona}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_persona(
    persona_id: str,
    name: str = None,
    role_title: str = None,
    company_type: str = None,
    bio: str = None,
    goals: list[str] = None,
    pain_points: list[str] = None,
    objections: list[str] = None,
    preferred_channels: list[str] = None,
    content_preferences: dict = None,
    buying_journey_stage: str = None,
    audience_id: str = None,
    tags: list[str] = None,
) -> dict:
    """Update a buyer persona.

    Args:
        persona_id: The unique persona ID.
        name: New name.
        role_title: New role title.
        company_type: New company type.
        bio: New bio.
        goals: Updated goals.
        pain_points: Updated pain points.
        objections: Updated objections.
        preferred_channels: Updated channels.
        content_preferences: Updated content preferences.
        buying_journey_stage: Updated buying journey stage.
        audience_id: Updated audience link.
        tags: Updated tags.

    Returns:
        Dictionary with the updated persona.
    """
    from app.services.audience_service import PersonaService

    try:
        from app.services.request_context import get_current_user_id

        service = PersonaService()
        persona = await service.update_persona(
            persona_id=persona_id,
            name=name,
            role_title=role_title,
            company_type=company_type,
            bio=bio,
            goals=goals,
            pain_points=pain_points,
            objections=objections,
            preferred_channels=preferred_channels,
            content_preferences=content_preferences,
            buying_journey_stage=buying_journey_stage,
            audience_id=audience_id,
            tags=tags,
            user_id=get_current_user_id(),
        )
        return {"success": True, "persona": persona}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_personas(
    audience_id: str = None,
    buying_journey_stage: str = None,
) -> dict:
    """List buyer personas with optional filters.

    Args:
        audience_id: Filter by linked audience segment.
        buying_journey_stage: Filter by buying journey stage (awareness, consideration, decision, retention).

    Returns:
        Dictionary with list of personas.
    """
    from app.services.audience_service import PersonaService

    try:
        from app.services.request_context import get_current_user_id

        service = PersonaService()
        personas = await service.list_personas(
            audience_id=audience_id,
            buying_journey_stage=buying_journey_stage,
            user_id=get_current_user_id(),
        )
        return {"success": True, "personas": personas, "count": len(personas)}
    except Exception as e:
        return {"success": False, "error": str(e), "personas": []}


async def delete_persona(persona_id: str) -> dict:
    """Delete a buyer persona.

    Args:
        persona_id: The unique persona ID to delete.

    Returns:
        Dictionary confirming deletion.
    """
    from app.services.audience_service import PersonaService

    try:
        from app.services.request_context import get_current_user_id

        service = PersonaService()
        deleted = await service.delete_persona(
            persona_id, user_id=get_current_user_id()
        )
        return {"success": deleted}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Ad Campaign Tools
# =============================================================================


async def create_ad_campaign(
    campaign_id: str,
    platform: str,
    name: str,
    ad_type: str = "search",
    objective: str = "conversions",
    targeting: dict = None,
    bid_strategy: str = "manual_cpc",
    bid_amount: float = None,
    daily_budget: float = None,
    total_budget: float = None,
    currency: str = "USD",
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """Create a platform-specific ad campaign linked to a marketing campaign.

    Args:
        campaign_id: Parent marketing campaign ID (from create_campaign).
        platform: Ad platform — 'google_ads' or 'meta_ads'.
        name: Ad campaign name.
        ad_type: Ad type. Google: search, display, video, shopping, performance_max. Meta: feed, stories, reels, carousel, collection.
        objective: Campaign objective (awareness, traffic, engagement, leads, conversions, sales).
        targeting: Targeting config — {locations[], age_min, age_max, genders[], interests[], keywords[], audiences[], placements[]}.
        bid_strategy: Bidding strategy. Google: manual_cpc, maximize_clicks, maximize_conversions, target_cpa, target_roas. Meta: lowest_cost, cost_cap, bid_cap.
        bid_amount: Bid amount (CPC/CPA target or ROAS target depending on strategy).
        daily_budget: Daily spend cap in currency units.
        total_budget: Total lifetime budget.
        currency: Currency code (default USD).
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    Returns:
        Dictionary containing the created ad campaign.
    """
    from app.services.ad_management_service import AdCampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = AdCampaignService()
        ad_campaign = await service.create_ad_campaign(
            campaign_id=campaign_id,
            platform=platform,
            name=name,
            ad_type=ad_type,
            objective=objective,
            targeting=targeting,
            bid_strategy=bid_strategy,
            bid_amount=bid_amount,
            daily_budget=daily_budget,
            total_budget=total_budget,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ad_campaign": ad_campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_ad_campaign(ad_campaign_id: str) -> dict:
    """Retrieve an ad campaign by ID.

    Args:
        ad_campaign_id: The unique ad campaign ID.

    Returns:
        Dictionary containing the ad campaign details.
    """
    from app.services.ad_management_service import AdCampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = AdCampaignService()
        result = await service.get_ad_campaign(
            ad_campaign_id, user_id=get_current_user_id()
        )
        return {"success": True, "ad_campaign": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_ad_campaign(
    ad_campaign_id: str,
    name: str = None,
    status: str = None,
    targeting: dict = None,
    bid_strategy: str = None,
    bid_amount: float = None,
    daily_budget: float = None,
    total_budget: float = None,
) -> dict:
    """Update an ad campaign's settings, targeting, budget, or status.

    Args:
        ad_campaign_id: The unique ad campaign ID.
        name: New name.
        status: New status (draft, pending_review, active, paused, completed, rejected).
        targeting: Updated targeting config.
        bid_strategy: Updated bid strategy.
        bid_amount: Updated bid amount.
        daily_budget: Updated daily budget.
        total_budget: Updated total budget.

    Returns:
        Dictionary with the updated ad campaign.
    """
    from app.services.ad_management_service import AdCampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = AdCampaignService()
        result = await service.update_ad_campaign(
            ad_campaign_id=ad_campaign_id,
            name=name,
            status=status,
            targeting=targeting,
            bid_strategy=bid_strategy,
            bid_amount=bid_amount,
            daily_budget=daily_budget,
            total_budget=total_budget,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ad_campaign": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_ad_campaigns(
    campaign_id: str = None,
    platform: str = None,
    status: str = None,
) -> dict:
    """List ad campaigns with optional filters.

    Args:
        campaign_id: Filter by parent marketing campaign.
        platform: Filter by platform (google_ads, meta_ads).
        status: Filter by status.

    Returns:
        Dictionary with list of ad campaigns.
    """
    from app.services.ad_management_service import AdCampaignService

    try:
        from app.services.request_context import get_current_user_id

        service = AdCampaignService()
        results = await service.list_ad_campaigns(
            campaign_id=campaign_id,
            platform=platform,
            status=status,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ad_campaigns": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e), "ad_campaigns": []}


# =============================================================================
# Ad Creative Tools
# =============================================================================


async def create_ad_creative(
    ad_campaign_id: str,
    name: str,
    creative_type: str = "image",
    headline: str = None,
    description: str = None,
    call_to_action: str = None,
    primary_text: str = None,
    destination_url: str = None,
    media_urls: list[str] = None,
    specs: dict = None,
    ab_variant: str = None,
) -> dict:
    """Create an ad creative asset linked to an ad campaign.

    Args:
        ad_campaign_id: Parent ad campaign ID.
        name: Creative name (e.g., 'Summer Sale - Variant A').
        creative_type: Type (image, video, carousel, responsive, html5, text_only).
        headline: Ad headline (30-90 chars depending on platform).
        description: Ad description text.
        call_to_action: CTA button text (Learn More, Shop Now, Sign Up, Get Offer).
        primary_text: Main ad copy (Facebook/Instagram primary text field).
        destination_url: Landing page URL the ad links to.
        media_urls: List of image/video URLs for the creative.
        specs: Creative specs — {width, height, aspect_ratio, file_format, duration_seconds}.
        ab_variant: A/B test variant label (A, B, C).

    Returns:
        Dictionary containing the created creative.
    """
    from app.services.ad_management_service import AdCreativeService

    try:
        from app.services.request_context import get_current_user_id

        service = AdCreativeService()
        creative = await service.create_creative(
            ad_campaign_id=ad_campaign_id,
            name=name,
            creative_type=creative_type,
            headline=headline,
            description=description,
            call_to_action=call_to_action,
            primary_text=primary_text,
            destination_url=destination_url,
            media_urls=media_urls,
            specs=specs,
            ab_variant=ab_variant,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ad_creative": creative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_ad_creatives(
    ad_campaign_id: str = None,
    creative_type: str = None,
    status: str = None,
) -> dict:
    """List ad creatives with optional filters.

    Args:
        ad_campaign_id: Filter by ad campaign.
        creative_type: Filter by type (image, video, carousel, etc.).
        status: Filter by status (draft, approved, active, paused, rejected).

    Returns:
        Dictionary with list of creatives.
    """
    from app.services.ad_management_service import AdCreativeService

    try:
        from app.services.request_context import get_current_user_id

        service = AdCreativeService()
        results = await service.list_creatives(
            ad_campaign_id=ad_campaign_id,
            creative_type=creative_type,
            status=status,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ad_creatives": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e), "ad_creatives": []}


async def update_ad_creative(
    creative_id: str,
    headline: str = None,
    description: str = None,
    call_to_action: str = None,
    primary_text: str = None,
    destination_url: str = None,
    media_urls: list[str] = None,
    status: str = None,
) -> dict:
    """Update an ad creative.

    Args:
        creative_id: The unique creative ID.
        headline: New headline.
        description: New description.
        call_to_action: New CTA text.
        primary_text: New primary text.
        destination_url: New landing page URL.
        media_urls: Updated media URLs.
        status: New status (draft, approved, active, paused, rejected).

    Returns:
        Dictionary with the updated creative.
    """
    from app.services.ad_management_service import AdCreativeService

    try:
        from app.services.request_context import get_current_user_id

        service = AdCreativeService()
        result = await service.update_creative(
            creative_id=creative_id,
            headline=headline,
            description=description,
            call_to_action=call_to_action,
            primary_text=primary_text,
            destination_url=destination_url,
            media_urls=media_urls,
            status=status,
            user_id=get_current_user_id(),
        )
        return {"success": True, "ad_creative": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Ad Spend & ROAS Tools
# =============================================================================


async def record_ad_spend(
    ad_campaign_id: str,
    tracking_date: str,
    spend: float,
    impressions: int = 0,
    clicks: int = 0,
    conversions: int = 0,
    conversion_value: float = 0,
) -> dict:
    """Record daily ad spend and performance metrics.

    Upserts by (ad_campaign_id, tracking_date) — updates existing record if present.
    Automatically calculates CTR, CPC, CPA, and ROAS.

    Args:
        ad_campaign_id: The ad campaign ID.
        tracking_date: Date (YYYY-MM-DD).
        spend: Amount spent.
        impressions: Number of impressions.
        clicks: Number of clicks.
        conversions: Number of conversions.
        conversion_value: Revenue attributed to conversions.

    Returns:
        Dictionary with the spend record including calculated metrics.
    """
    from app.services.ad_management_service import AdSpendTrackingService

    try:
        from app.services.request_context import get_current_user_id

        service = AdSpendTrackingService()
        result = await service.record_daily_spend(
            ad_campaign_id=ad_campaign_id,
            tracking_date=tracking_date,
            spend=spend,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            conversion_value=conversion_value,
            user_id=get_current_user_id(),
        )
        return {"success": True, "spend_record": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_ad_performance(
    ad_campaign_id: str,
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """Get aggregated ad performance and ROAS for a campaign.

    Returns total spend, impressions, clicks, conversions, conversion value,
    average CTR/CPC/CPA, overall ROAS, and daily breakdown.

    Args:
        ad_campaign_id: The ad campaign ID.
        start_date: Start date filter (YYYY-MM-DD).
        end_date: End date filter (YYYY-MM-DD).

    Returns:
        Dictionary with aggregated performance metrics and daily breakdown.
    """
    from app.services.ad_management_service import AdSpendTrackingService

    try:
        from app.services.request_context import get_current_user_id

        service = AdSpendTrackingService()
        result = await service.get_spend_summary(
            ad_campaign_id=ad_campaign_id,
            start_date=start_date,
            end_date=end_date,
            user_id=get_current_user_id(),
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_budget_pacing(ad_campaign_id: str) -> dict:
    """Get budget pacing status for an ad campaign.

    Compares spend-to-date vs total/daily budget to determine if spending
    is on-track, underpacing, or overpacing. Provides actionable recommendations.

    Args:
        ad_campaign_id: The ad campaign ID.

    Returns:
        Dictionary with pacing_status (on_track, underpacing, overpacing),
        spend_to_date, budget_remaining, projected_total_spend, overall_roas,
        and recommendation.
    """
    from app.services.ad_management_service import AdSpendTrackingService

    try:
        from app.services.request_context import get_current_user_id

        service = AdSpendTrackingService()
        result = await service.get_budget_pacing(
            ad_campaign_id=ad_campaign_id,
            user_id=get_current_user_id(),
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}
