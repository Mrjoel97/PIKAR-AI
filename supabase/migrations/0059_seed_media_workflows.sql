-- Migration: 0059_seed_media_workflows.sql
-- Description: Add media-first workflow templates and clarify editorial workflow descriptions

INSERT INTO workflow_templates (name, description, category, phases)
VALUES
(
    'Content Creation Workflow',
    'Editorial content production for blogs, articles, reports, and written resources.',
    'marketing',
    '[{"name":"Ideate","steps":[{"name":"Brainstorm","tool":"generate_ideas"}]},{"name":"Draft","steps":[{"name":"Write Copy","tool":"generate_content"}]},{"name":"Publish","steps":[{"name":"Distribute","tool":"publish_content"}]}]'::jsonb
),
(
    'Content Creation Workflow (Extended)',
    'Editorial content production for blogs, articles, and written resources with AI assistance.',
    'content',
    '[{"name":"Ideate","steps":[{"name":"Generate Ideas","tool":"quick_research","description":"Brainstorm content topics","required_approval":false}]},{"name":"Research","steps":[{"name":"Gather Info","tool":"mcp_web_search","description":"Research topic depth","required_approval":false}]},{"name":"Outline","steps":[{"name":"Create Outline","tool":"save_content","description":"Structure the content","required_approval":true}]},{"name":"Draft","steps":[{"name":"Write Content","tool":"save_content","description":"Write the first draft","required_approval":false}]},{"name":"Edit","steps":[{"name":"Refine and Polish","tool":"update_content","description":"Grammar and style check","required_approval":false}]},{"name":"Approve","steps":[{"name":"Final Review","tool":"list_content","description":"Human sign-off","required_approval":true}]},{"name":"Publish","steps":[{"name":"Distribute","tool":"update_content","description":"Publish to platform","required_approval":false}]}]'::jsonb
),
(
    'UGC Ad Campaign Workflow',
    'Produce a vertical UGC-style ad package with video, captions, and publish-ready metadata.',
    'marketing',
    '[{"name":"Template","steps":[{"name":"Review UGC Deliverable Template","tool":"get_media_deliverable_templates","description":"Load the recommended UGC request and output contract for alignment","required_approval":false}]},{"name":"Production","steps":[{"name":"Generate UGC Ad","tool":"execute_content_pipeline","description":"Create a vertical UGC-style product video ad with a drafted social caption","required_approval":false}]}]'::jsonb
),
(
    'Product Video Ad Workflow',
    'Produce a product-led video ad with captions, video metadata, and platform-ready copy.',
    'marketing',
    '[{"name":"Template","steps":[{"name":"Review Product Video Deliverable Template","tool":"get_media_deliverable_templates","description":"Load the recommended request and output contract for a product video ad","required_approval":false}]},{"name":"Production","steps":[{"name":"Generate Product Video Ad","tool":"execute_content_pipeline","description":"Create a product video ad with drafted platform copy and delivery metadata","required_approval":false}]}]'::jsonb
),
(
    'Product Photoshoot Bundle Workflow',
    'Generate a structured product photoshoot bundle with stills, bundle metadata, and companion video deliverables.',
    'content',
    '[{"name":"Template","steps":[{"name":"Review Photoshoot Deliverable Template","tool":"get_media_deliverable_templates","description":"Load the recommended request and output contract for a product photoshoot bundle","required_approval":false}]},{"name":"Bundle","steps":[{"name":"Create Photoshoot Bundle","tool":"create_product_photoshoot_bundle","description":"Generate hero, lifestyle, detail, packaging, macro, and variant deliverables with a reusable manifest","required_approval":false}]}]'::jsonb
)
ON CONFLICT (name) DO UPDATE
SET description = EXCLUDED.description,
    category = EXCLUDED.category,
    phases = EXCLUDED.phases;
