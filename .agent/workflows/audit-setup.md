---
description: Audit current setup and propose improvements for agent reliability and configuration.
---
# Audit Setup Workflow

Follow these steps chronologically to audit the user's current setup.

1. **Run Configuration Audit**
   - Call the `audit_user_setup_tool` to scan the current configuration, skill usage, and journey metrics.

2. **Display Results**
   - Use `create_table_widget` to display the key metrics and the audit score in a visually appealing way.

3. **Provide Recommendations**
   - Present the top 3 improvements generated from the audit strictly as actionable bullet points.

4. **Offer Auto-Configuration**
   - Inform the user that you can help them complete the recommendations immediately (e.g., auto-configure recommended tools or unblock stalled initiatives using other agents/workflows).
