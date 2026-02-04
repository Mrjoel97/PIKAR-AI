import json

PERSONAS = {
    "solopreneur": [
        "First Client Acquisition", "Automated Invoicing Setup", "Personal Brand Building",
        "Portfolio Website Launch", "Social Media Content Strategy", "Client Onboarding Automation",
        "Expense Tracking Setup", "Quarterly Tax Prep", "Service Pricing Strategy",
        "Virtual Assistant Hiring", "Cold Email Outreach", "LinkedIn Networking",
        "Google Business Profile Optimization", "Project Management Setup", "Proposal Template Creation",
        "Contract Template Creation", "Customer Feedback Loop", "Email List Building",
        "Webinar Funnel Setup", "Online Course Launch", "Affiliate Program Setup",
        "Podcast Launch", "Blog Content Calendar", "SEO Basic Setup",
        "Time Blocking Schedule", "Remote Office Setup", "Health Insurance Research",
        "Liability Insurance Setup", "Bank Account Separation", "Emergency Fund Planning",
        "Retirement Saving Setup", "Networking Event Caldendar", "Client Gift Strategy",
        "Review Management", "Upsell Strategy", "Legacy Client Migration",
        "Productivity Tool Stack", "Data Backup Strategy", "Password Management", "Brand Voice Guide"
    ],
    "startup": [
        "Seed Fundraising", "MVP Launch", "First 10 Hires",
        "Co-founder Agreement", "Entity Incorporation", "Cap Table Setup",
        "Product Market Fit Validation", "Beta User Recruitment", "Waitlist Growth Strategy",
        "Investor Update Template", "Board Meeting Deck", "Pitch Deck Iteration",
        "Employee Stock Option Plan", "Remote Team Culture", "Agile Workflow Setup",
        "CI/CD Pipeline Setup", "Security Compliance (SOC2 Prep)", "Data Privacy Policy",
        "Terms of Service Draft", "Trademark Registration", "Competitor Analysis",
        "Unit Economics Analysis", "Burn Rate Monitoring", "Runway Extension Strategy",
        "Growth Hacking Experiments", "Viral Loop Design", "Referral Program V1",
        "Product Hunt Launch", "TechCrunch Outreach", "AngelList Profile",
        "YCombinator Application", "Accelerator Prep", "Series A Prep",
        "Strategic Pivot Analysis", "Customer Discovery Interviews", "Churn Analysis",
        "Server Cost Optimization", "Analytics Stack Setup", "Internal Dashboard Build", "Knowledge Base Create"
    ],
    "sme": [
        "Performance Review Cycle", "Supply Chain Optimization", "New Market Expansion",
        "Department Budgeting", "Management Training Program", "Diversity & Inclusion Initiative",
        "Employee Wellness Program", "Office Hybrid Policy", "IT Asset Lifecycle",
        "Cybersecurity Audit", "Disaster Recovery Plan", "CRM Migration",
        "ERP Implementation", "Sales Commission Structure", "Customer Success Playbook",
        "NPS Survey Campaign", "Brand Refresh", "Website Replatforming",
        "Vendor Consolidation", "Procurement Policy", "Expense Policy Update",
        "Travel Policy Update", "Recruitment Agency ROI", "Internship Program",
        "Corporate Social Responsibility", "Sustainability Report", "Annual Report Design",
        "Town Hall Meeting Deck", "Leadership Offsite", "Succession Planning",
        "Key Account Management", "Partner Channel Strategy", "Reseller Program",
        "Loyalty Program Revamp", "Inventory Turnover Analysis", "Cash Flow Forecasting",
        "Debt Refinancing", "Insurance Renewal", "Legal Retainer Review", "Compliance Training"
    ],
    "enterprise": [
        "Global Compliance Audit", "Merger & Acquisition Integration", "Enterprise-wide ERP Rollout",
        "Digital Transformation Roadmap", "Cloud Migration Strategy", "Data Lake Architecture",
        "AI Governance Framework", "Global Payroll Consolidation", "Shared Services Center",
        "Center of Excellence Setup", "Innovation Lab Launch", "Corporate Venture Capital",
        "Board Governance Review", "Investor Relations Quarterly", "ESG Strategy",
        "Diversity Annual Report", "Global Mobility Program", "Executive Compensation Review",
        "Union Negotiation Strategy", "Crisis Communication Playbook", "Cyber Incident Response",
        "Business Continuity Test", "Supply Chain Resilience", "Global Tax Strategy",
        "Transfer Pricing Study", "Brand Architecture Review", "Global Marketing Campaign",
        "Product Portfolio Rationalization", "Legacy System Sunsetting", "Mainframe Modernization",
        "Zero Trust Security Model", "GDPR/CCPA Compliance", "Whistleblower Hotline",
        "Internal Audit Cycle", "Strategic Vendor Review", "Real Estate Portfolio",
        "Corporate University", "Leadership Development Program", "Change Management Framework", "Global Knowledge Management"
    ]
}

def generate_sql():
    sql = [
        "-- Migration: 0017_seed_user_journeys.sql",
        "-- Description: Seed 160 User Journeys (40 per persona)",
        "BEGIN;",
        "DELETE FROM user_journeys;" 
    ]
    
    values = []
    for persona, titles in PERSONAS.items():
        for title in titles:
            # Create a simple default stage structure
            stages = json.dumps([
                {"name": "Start", "status": "pending"},
                {"name": "In Progress", "status": "pending"},
                {"name": "Complete", "status": "pending"}
            ])
            # Escape single quotes in title
            safe_title = title.replace("'", "''")
            description = f"Standard journey for {safe_title} in {persona} context."
            
            val = f"('{persona}', '{safe_title}', '{description}', '{stages}'::jsonb)"
            values.append(val)
    
    # Insert in batches of 50 to avoid huge query string if needed, but 160 is fine for one statement
    if values:
        sql.append("INSERT INTO user_journeys (persona, title, description, stages)")
        sql.append("VALUES")
        sql.append(",\n".join(values) + ";")
    
    sql.append("COMMIT;")
    
    with open("c:/Users/expert/Documents/PKA/Pikar-Ai/supabase/migrations/0017_seed_user_journeys.sql", "w") as f:
        f.write("\n".join(sql))

if __name__ == "__main__":
    generate_sql()
    print("Migration file 0017_seed_user_journeys.sql generated successfully.")
