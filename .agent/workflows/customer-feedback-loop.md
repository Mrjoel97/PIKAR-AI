---
description: Create customer feedback loops with Google Forms for collecting and analyzing customer insights
---

# Customer Feedback Loop Workflow

This workflow helps users set up automated customer feedback collection using Google Forms.

## Prerequisites
- Google OAuth connected via Supabase
- GCP scope: `https://www.googleapis.com/auth/forms.body`

## Steps

### 1. Create Feedback Form
Create a customer satisfaction survey:
```
User: "I want to collect customer feedback for my business"
Agent: What's your business name and what specific feedback are you looking for?
User: "Acme Corp - product quality and customer service feedback"
Agent: create_feedback_form(
  title="Acme Corp Customer Feedback Survey",
  business_name="Acme Corp"
)
→ Returns: share_url for customers
```

### 2. Customize Questions (Optional)
Add custom questions:
```
Agent: create_custom_form(
  title="Product Feedback",
  description="Help us improve our products",
  questions=[
    {"title": "Which product did you purchase?", "type": "text", "required": True},
    {"title": "How would you rate the quality?", "type": "scale", "required": True},
    {"title": "What features would you like?", "type": "paragraph"}
  ]
)
```

### 3. Share Form URL
Provide shareable link to user:
```
Agent: "Here's your feedback form URL: https://docs.google.com/forms/d/xxx
       Share this with customers via:
       - Email campaigns
       - Your website
       - Social media
       - Post-purchase follow-up emails"
```

### 4. Collect Responses
Wait for customer responses, then analyze:
```
User: "How's my feedback coming along?"
Agent: get_form_responses()
→ Returns: response count, submitted answers
```

### 5. Analyze Feedback
Generate insights from responses:
```
User: "Give me a summary of the feedback"
Agent: analyze_feedback()
→ Returns: response count, trends, recommendations
```

### 6. Generate Report
Create a formal feedback report:
```
Agent: generate_presentation(
  title="Customer Feedback Report - Q1 2026",
  slides=[
    {"type": "summary", "data": feedback_analysis},
    {"type": "metrics", "data": satisfaction_scores}
  ]
)
```

### 7. Schedule Recurring Analysis
Set up automated feedback reporting:
```
Agent: schedule_report(
  frequency="weekly",
  report_format="pptx",
  recipients=["team@acmecorp.com"]
)
```

## Integration with Other Tools

| Tool | Purpose |
|------|---------|
| **Gmail** | Email feedback form to customers |
| **Sheets** | Export responses to spreadsheet |
| **Calendar** | Schedule follow-up meetings |
| **Docs** | Create action plan document |

## Best Practices
- Keep surveys short (5-7 questions max)
- Use scale questions for quantitative metrics
- Use paragraph questions for qualitative insights
- Analyze feedback weekly for timely action
- Close the loop: tell customers what you improved
