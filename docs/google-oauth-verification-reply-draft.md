# Draft Reply to Google OAuth Verification Team

> **To:** Google API OAuth Dev Verification
> **Subject:** Re: API OAuth Dev Verification — Project 706895462845
> **Date:** April 12, 2026

---

Hello Google Verification Team,

Thank you for your detailed review of our application (Project ID: my-project-pk-484623). We have addressed all three items raised in your feedback.

---

## 1. Privacy Policy Update

Our privacy policy URL has been updated. The previous URL (`/privacypolicy`) now redirects to the correct location:

**Updated Privacy Policy URL:** https://www.pikar-ai.com/privacy

The privacy policy has been updated (April 12, 2026) with the following additions to specifically address Google user data handling:

- **Section 3a** — Now explicitly lists all Google OAuth scopes requested by the application, including the newly added Drive (`drive.file`), Sheets (`spreadsheets`), Docs (`documents`), and Forms (`forms.body`) scopes, with descriptions of what data each scope accesses.
- **Section 3b** — Describes how each type of Google data is used (daily briefings, email triage, report generation, document creation, form surveys, etc.).
- **Section 3c** — Documents data sharing practices (AI processing via Google Gemini, infrastructure provider Supabase).
- **Section 3d** — Details storage and security practices (TLS 1.2+, RLS, OAuth token handling, temporary caching).
- **Section 3e** — Explains data retention periods and provides clear deletion instructions.
- **Section 3f** — **NEW: Google API Services Limited Use Disclosure** — Explicitly states adherence to the Google API Services User Data Policy and Limited Use requirements.
- **Section 3g** — **NEW: Complete scope reference table** — Lists every OAuth scope, its classification (Basic/Sensitive/Restricted), and its purpose. Includes both sign-in scopes and the separate YouTube social connection scopes.

---

## 2. OAuth Consent Testing Instructions — All Scopes

Our application has **two OAuth consent flows**:

### Flow 1: Main Sign-In (10 scopes)

**How to access the OAuth consent screen:**

1. Navigate to **https://www.pikar-ai.com/auth/login**
2. Click **"Continue with Google"**
3. Google's consent screen will appear showing:
   - `email`, `profile` (Basic)
   - `gmail.readonly`, `gmail.modify`, `gmail.send` (Restricted)
   - `calendar`, `drive.file`, `spreadsheets`, `documents`, `forms.body` (Sensitive)
4. Click **"Allow"** to complete sign-in
5. You will be redirected to the dashboard at `/dashboard/command-center`

### Flow 2: YouTube Social Connection (2 scopes)

**How to access the YouTube OAuth consent screen:**

1. After signing in, click the **user avatar** in the top-right corner
2. Navigate to **Settings → Social Accounts** (or go directly to `/dashboard/settings/social`)
3. Find **"YouTube"** in the platform list (shows "Not Connected")
4. Click **"Connect"** next to YouTube
5. A **separate** Google consent screen appears requesting:
   - `youtube.upload` (Sensitive)
   - `youtube` (Sensitive)
6. Click **"Allow"** to connect YouTube
7. YouTube status changes to **"Connected"** on the Social Accounts page

---

## 3. Scope Functionality Testing Instructions

After completing OAuth consent, here is how to test each scope in the application:

### Gmail Scopes

| Scope | How to Test |
|-------|-------------|
| `gmail.readonly` | From the dashboard, type in the AI chat: **"Check my inbox"** or **"Give me my morning briefing"**. The agent reads recent emails and presents a summary. |
| `gmail.modify` | After inbox triage, type: **"Archive the low-priority emails"**. The agent removes INBOX/UNREAD labels from selected emails. |
| `gmail.send` | Type: **"Send an email to [address] about [topic]"**. The agent drafts the email and asks for your approval before sending. Verify delivery in Gmail Sent folder. |

### Calendar Scope

| Scope | How to Test |
|-------|-------------|
| `calendar` | Type: **"What's on my calendar this week?"** to read events. Type: **"Schedule a team meeting for tomorrow at 2pm"** to create an event. Verify in Google Calendar. |

### Drive / Docs / Sheets / Forms Scopes

| Scope | How to Test |
|-------|-------------|
| `drive.file` + `spreadsheets` | Type: **"Create a Google Sheet with a revenue summary"**. The agent creates a new spreadsheet in Google Drive. Verify the file appears in Google Drive and contains formatted data. |
| `drive.file` + `documents` | Type: **"Draft a project proposal in Google Docs"**. The agent creates a new document. Verify the file appears in Google Drive with formatted content. |
| `forms.body` | Type: **"Create a customer satisfaction survey as a Google Form"**. The agent creates a form with questions. Verify the form appears in Google Drive. |

### YouTube Scopes (requires Flow 2 connection)

| Scope | How to Test |
|-------|-------------|
| `youtube.upload` + `youtube` | After connecting YouTube via Settings → Social Accounts, type: **"Upload the latest video to YouTube"** or use the social publishing workflow. The agent uploads content to the connected YouTube channel. |

---

## Summary of Changes Made

1. **Privacy policy URL:** `/privacypolicy` now permanently redirects to `/privacy`
2. **Privacy policy content:** Updated with Limited Use Disclosure, complete scope table, and expanded Google data documentation
3. **OAuth consent flow:** Added `drive.file`, `spreadsheets`, `documents`, and `forms.body` scopes to the sign-in flow
4. **Google Cloud Console:** The OAuth consent screen configuration has been updated to include all scopes listed above

Please let us know if you need any additional information or clarification.

Best regards,
Joel Feruzi
Pikar AI

---

> **Note to self:** Before sending this reply, ensure:
> - [ ] The updated privacy policy is deployed to production
> - [ ] The OAuth consent screen in Google Cloud Console includes the new scopes: `drive.file`, `spreadsheets`, `documents`, `forms.body`
> - [ ] Test the `/privacypolicy` → `/privacy` redirect works on production
> - [ ] Test the sign-in flow shows the new scopes on Google's consent screen
> - [ ] Record and upload the updated verification video (see `docs/google-oauth-verification-video-script.md`)
