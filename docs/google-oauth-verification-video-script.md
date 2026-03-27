# Google OAuth Verification Video Script — Pikar AI

> **Purpose:** This script guides you through recording the YouTube video required
> for Google OAuth verification. Follow each section in order while screen-recording.
>
> **Video length target:** 3–5 minutes
> **Recording tool:** OBS Studio, Loom, or any screen recorder with mic input

---

## Pre-Recording Checklist

Before you hit record, have these ready:

- [ ] **Google Cloud Console** open at: https://console.cloud.google.com/apis/credentials
- [ ] **Pikar AI app** running locally (`make local-backend` + `cd frontend && npm run dev`)
- [ ] Browser with **no Google account signed in** (use Incognito or sign out)
- [ ] A **test Google account** you can sign in with
- [ ] The app should have **some demo data** (emails in Gmail, calendar events, etc.)

---

## SECTION 1: App Identity & OAuth Client Details (0:00 – 0:45)

### What to show:

1. **Open Google Cloud Console → APIs & Services → Credentials**
2. **Show the OAuth consent screen configuration:**
   - Navigate to: APIs & Services → OAuth consent screen
   - Show the **app name**: "Pikar AI"
   - Show the **user support email**
   - Show the **developer contact email**
   - Show the **app logo** (if uploaded)
   - Show the **app domain / authorized domains**

3. **Show the OAuth Client ID:**
   - Go back to Credentials tab
   - Click on the OAuth 2.0 Client ID used by the app
   - Show the **Client ID** clearly on screen
   - Show the **Authorized redirect URIs:**
     - `https://<your-domain>/auth/callback`
     - `http://localhost:3000/auth/callback` (dev)
   - Show the **Authorized JavaScript origins**

### Narration script:

> "This is Pikar AI, a multi-agent AI executive system for business operations.
> Here is our OAuth consent screen showing the app name 'Pikar AI',
> our support email, and developer contact information.
>
> This is our OAuth 2.0 Client ID: [read it out or pause on screen].
> Our authorized redirect URI is [your domain]/auth/callback,
> which handles the OAuth code exchange via Supabase Auth."

---

## SECTION 2: Requested Scopes Overview (0:45 – 1:15)

### What to show:

1. **Still in OAuth consent screen → Scopes section**
2. Show all configured scopes. The app requests:

| Scope | Classification | Purpose |
|-------|---------------|---------|
| `email` | Basic | User email for account identification |
| `profile` | Basic | User name and profile picture |
| `gmail.readonly` | **Restricted** | Read inbox for daily briefings and email triage |
| `gmail.modify` | **Restricted** | Archive emails and manage labels after triage |
| `gmail.send` | **Restricted** | Send emails on behalf of the user via AI agents |
| `calendar` | **Sensitive** | Read/write calendar events for scheduling |

### Narration script:

> "Our application requests the following scopes:
> Basic scopes — email and profile — for account identification.
> Three restricted Gmail scopes — readonly, modify, and send —
> which I'll demonstrate the specific use of in a moment.
> And the sensitive Calendar scope for event management.
> Let me now walk through the user experience."

---

## SECTION 3: OAuth Grant Flow — User Experience (1:15 – 2:15)

### What to show (step by step):

1. **Open the Pikar AI login page** (`/auth/login`)
   - Show the "Continue with Google" button clearly

2. **Click "Continue with Google"**
   - The app calls `supabase.auth.signInWithOAuth({ provider: 'google' })`
   - This redirects to Google's consent screen

3. **Google consent screen appears** — PAUSE AND SHOW CLEARLY:
   - Show the app name "Pikar AI" on Google's consent screen
   - Show each scope being requested (Google lists them)
   - **Scroll through all requested permissions slowly**
   - Show the "Allow" / "Cancel" options
   - Highlight that the user sees exactly what access is being granted

4. **Click "Allow"**
   - Google redirects to `/auth/callback` with an authorization code
   - Supabase exchanges the code for tokens
   - User is redirected to `/dashboard/command-center`

5. **Show the dashboard loaded successfully**
   - User is now authenticated
   - Google provider tokens are stored securely in Supabase Auth

### Narration script:

> "Here's our login page. The user clicks 'Continue with Google.'
> Google shows its standard consent screen listing Pikar AI
> and all the permissions we're requesting.
>
> [Scroll through scopes on consent screen]
>
> The user can see exactly what access Pikar AI will have:
> reading their Gmail, managing email labels, sending emails on their behalf,
> and accessing their Google Calendar.
>
> When the user clicks 'Allow', Google sends an authorization code
> to our callback URL. Supabase Auth handles the secure token exchange,
> and the user arrives at their dashboard."

---

## SECTION 4: gmail.readonly — Daily Briefing & Email Triage (2:15 – 3:00)

### What to show:

1. **From the dashboard, ask the AI agent to check your inbox:**
   - Type in the chat: "Check my inbox" or "What emails do I have?"
   - The agent calls `read_inbox()` which uses `GmailReader.list_messages()`
   - Show the agent returning a summary of unread emails

2. **Show the Daily Briefing feature:**
   - Navigate to Dashboard → Briefing (if available)
   - Or ask: "Give me my morning briefing"
   - Show how the agent reads recent emails to generate a briefing summary

3. **Show email triage:**
   - Ask: "Triage my unread emails by priority"
   - Agent reads inbox, classifies emails, presents prioritized list

### Narration script:

> "The gmail.readonly scope allows our AI agents to read the user's inbox.
> Here I ask the agent to check my inbox — it retrieves unread messages
> and presents a summary.
>
> This is used for our Daily Briefing feature, where the agent reads
> recent emails each morning and generates an executive summary.
>
> It's also used for email triage — the agent reads and classifies
> emails by priority so the user can focus on what matters most."

---

## SECTION 5: gmail.modify — Email Management (3:00 – 3:30)

### What to show:

1. **Ask the agent to archive processed emails:**
   - "Archive the low-priority emails from my triage"
   - Agent calls `archive_email()` which uses `GmailReader.modify_message()`
     with `remove_labels=["INBOX", "UNREAD"]`
   - Show the emails disappearing from inbox

2. **Show label management:**
   - "Mark this email as read"
   - Agent calls `modify_message()` to remove the UNREAD label

### Narration script:

> "The gmail.modify scope lets the agent manage email labels.
> After triaging, I can tell the agent to archive low-priority emails —
> it removes the INBOX and UNREAD labels, keeping the inbox clean.
> Users can also ask the agent to mark specific emails as read.
> No email content is ever deleted — only labels are modified."

---

## SECTION 6: gmail.send — Sending Emails (3:30 – 4:00)

### What to show:

1. **Ask the agent to draft and send an email:**
   - "Send an email to [test address] about the Q1 report"
   - Agent calls `send_email()` which uses `GmailService.send_email()`
   - Show the agent composing and sending the email
   - **Note:** If you have approval workflows enabled, show the
     approval step before sending

2. **Show the sent email in Gmail:**
   - Open Gmail → Sent folder
   - Show the email that was just sent via the agent

### Narration script:

> "The gmail.send scope allows agents to send emails on the user's behalf.
> Here I ask the agent to send a follow-up email — it drafts the message
> and sends it through the user's Gmail account.
>
> For safety, our system includes an approval workflow —
> the agent shows the draft and asks for user confirmation before sending.
> Here in the Sent folder you can see the email was delivered successfully."

---

## SECTION 7: calendar — Event Management (4:00 – 4:30)

### What to show:

1. **Ask the agent to show upcoming events:**
   - "What's on my calendar this week?"
   - Agent calls `list_events()` which uses `GoogleCalendarService.list_upcoming_events()`
   - Show the formatted list of events

2. **Ask the agent to create an event:**
   - "Schedule a team sync for tomorrow at 2pm"
   - Agent calls `create_event()` which uses `GoogleCalendarService.create_event()`
   - Show the event created in Google Calendar

3. **Show the Calendar widget on the dashboard** (if available)

### Narration script:

> "The calendar scope allows our agents to read and create events.
> I can ask 'What's on my calendar this week?' and the agent retrieves
> upcoming events from Google Calendar.
>
> I can also schedule meetings — here I ask the agent to create a team sync,
> and it creates the event directly in Google Calendar with the correct
> time, title, and attendees."

---

## SECTION 8: Data Handling & Security (4:30 – 5:00)

### What to show:

1. **Briefly show the Settings page** — Google Workspace connection status
2. **Mention key security points** (can be on-screen text):
   - OAuth tokens stored securely in Supabase Auth (never in client-side storage)
   - Refresh tokens used for background access with user consent
   - Users can revoke access at any time via Google Account settings
   - All API calls use the user's own credentials — no service account impersonation
   - App does not store email content permanently

### Narration script:

> "Regarding data security: OAuth tokens are stored securely in Supabase Auth,
> never exposed to the client. Users can see their connection status
> in Settings and disconnect at any time.
>
> All Google API calls use the user's own OAuth credentials.
> We do not store email content permanently — it's processed in real-time
> by our AI agents and only summaries or user-approved actions persist.
>
> Users can revoke Pikar AI's access at any time through their
> Google Account security settings. Thank you for reviewing our application."

---

## Post-Recording Checklist

- [ ] Video clearly shows the **app name** ("Pikar AI") and **OAuth Client ID**
- [ ] Google consent screen with **all scopes listed** is visible
- [ ] Each scope has a **clear demonstration** of its use in the app
- [ ] No sensitive data (real passwords, API keys, private emails) visible
- [ ] Video is **under 5 minutes** (Google reviewers watch many of these)
- [ ] Upload to YouTube as **Unlisted** and submit the link in Google Cloud Console

---

## Google Cloud Console Scopes Configuration Reference

Make sure your OAuth consent screen has these exact scopes configured:

```
# Basic (non-sensitive)
email
profile
openid

# Sensitive
https://www.googleapis.com/auth/calendar

# Restricted (requires security assessment)
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.send
```

---

## Tips for Passing Review

1. **Be methodical** — show each scope's usage one at a time
2. **Show real data** — Google reviewers want to see actual functionality, not mockups
3. **Explain necessity** — briefly say WHY each scope is needed (don't just show it)
4. **Show the consent screen clearly** — zoom in if needed
5. **Show the Client ID** — they cross-reference this with your submission
6. **Keep it concise** — reviewers appreciate efficiency
7. **Use a test account** — don't expose real personal/business emails
