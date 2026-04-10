# Phase 53: Multi-User & Teams - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable workspace owners to invite team members, manage roles, and enforce content visibility:

1. **Email invitations** — Admin sends branded email invitations via Resend API with accept link. Invited users can sign up and join in one flow (TEAM-01).
2. **Workspace join flow** — Accepting an invite joins the workspace immediately, granting access to shared initiatives, workflows, and content (TEAM-02).
3. **Role management** — Admin can change member roles (admin/member) and remove members. Role changes take effect immediately on next request (TEAM-03).
4. **Permission enforcement** — Members cannot access admin-only pages (team settings, billing, admin panel, workspace settings). Attempting to do so redirects to dashboard with a toast notification (TEAM-04).

**Out of scope for Phase 53** (deferred):
- Editor/Viewer granular roles (only Admin + Member for now)
- Per-member content isolation within a workspace (flat visibility)
- Department-scoped content visibility (Phase 52 departments are for routing, not visibility)
- Approval workflows for member-created content
- Workspace deletion flow (admin can rename but delete is deferred)
- Cross-workspace content sharing
- Member activity tracking / last active timestamps

</domain>

<decisions>
## Implementation Decisions

### Invitation Delivery (TEAM-01)

- **Email service:** **Resend API** — `RESEND_API_KEY` already in `frontend/.env`. Send branded HTML emails via Resend's send endpoint. Pikar AI branded template.
- **Email content:** "**{inviter_name}** invited you to join **{workspace_name}** on Pikar AI as a **{role}**." + primary CTA button "Accept Invitation" linking to `/invite/{token}`.
- **Token expiry:** **7 days** (already configured in `WorkspaceService.create_invite_link(expires_hours=168)`).
- **Accept flow:** Invite link goes to `/invite/{token}`. If user is logged in → join workspace immediately. If not → show signup form pre-filled with invited email, then auto-join after signup. Seamless onboarding for new users.
- **Resend/revoke:** Admins can resend (generates new token, extends expiry) or revoke (deletes token) from the pending invites section.

### Team Management UI (TEAM-01, TEAM-03)

- **Page location:** `/dashboard/settings/team` — under existing dashboard settings. Accessible via sidebar settings icon or settings page navigation.
- **Member list:** Table/list with: avatar, name, email, role badge (Admin=blue, Member=gray), joined date. Workspace owner has a permanent "Owner" badge and cannot be demoted.
- **Remove member:** Admin clicks "Remove" → confirmation dialog "Remove {name} from {workspace}?" → member is removed and loses access immediately. Owner cannot be removed.
- **Pending invites section:** Below the member list. Shows: invited email, assigned role, sent date, expiry countdown ("Expires in 3 days"), and "Resend" + "Revoke" action buttons.
- **Invite form:** "Invite team member" button at top → inline form with email input + role selector (Admin/Member) + "Send Invite" button.

### Role Model & Permissions (TEAM-03, TEAM-04)

- **Two roles only:** **Admin** and **Member**. Workspace owner is permanently Admin and cannot be demoted or removed.
- **Role change timing:** **Immediate on next request.** Role is stored in `workspace_members` table. `require_role()` middleware resolves role fresh on every request by querying the DB (already implemented). No session invalidation or cache needed.
- **Admin-only pages/actions:**
  - Team settings: invite, remove, role change (`/dashboard/settings/team`)
  - Billing & subscription management (`/dashboard/billing`, Stripe portal)
  - Admin panel: entire `/admin/*` section (analytics, monitoring, observability, governance)
  - Workspace settings: rename workspace, workspace-level config
- **Member access:** All non-admin features — chat, initiatives, workflows, content creation, integrations, department dashboards. Members can create freely (no approval required).
- **Permission error UX:** Member attempting admin-only page → **redirect to /dashboard with toast notification:** "This page is for workspace admins. Contact your admin for access." Non-disruptive, clear.
- **Frontend enforcement:** Admin-only nav items hidden for members (not shown with lock icon — that pattern is for tier gating from Phase 52, not role gating). Server-side enforcement via `require_role("admin")` middleware as backup.

### Shared Content Visibility (TEAM-02, TEAM-04)

- **Sharing model:** **Team-visible by default** (per PROJECT.md established pattern).
  - **Workspace-shared:** Initiatives, workflows, published content, integrations — visible to all workspace members.
  - **User-private:** Chat history, drafts, personal settings — visible only to the individual.
- **Peer access:** **Flat visibility** — all members see all workspace content. No per-member isolation within the workspace.
- **Create permissions:** **Members can create freely.** Both admins and members can create initiatives, workflows, and content. Admin-only actions are limited to team/billing/admin management.
- **Removed member content:** **Content stays in workspace, ownership transfers to workspace owner.** When a member is removed, their shared content (initiatives, workflows) remains. The `created_by` field updates to the workspace owner's user_id. No data loss.

### Claude's Discretion

The planner may decide the following without re-asking:
- Exact Resend email template HTML/styling (should match Pikar AI branding)
- Avatar placeholder for members without profile pictures (initials circle)
- Toast notification duration and styling (use existing toast/sonner pattern)
- Whether invite email includes workspace logo
- Exact confirmation dialog copy for member removal
- Database query optimization for workspace-scoped content filtering
- Whether to add a "Leave workspace" option for non-owner members (probably yes, but planner decides)

</decisions>

<specifics>
## Specific Ideas

- The invite email should feel professional and trustworthy — "You've been invited by a person you know" not "SIGN UP NOW." Include the inviter's name prominently.
- Team settings page should be simple for small teams (2-10 people). Don't over-engineer for 100+ member teams — that's not the beta target.
- Role badges should use the same badge component/styling as the SubscriptionBadge from Phase 50 — visual consistency across badge types.
- The toast for "admin-only page" should be informational, not punishing. Member should feel guided, not rejected.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`app/services/workspace_service.py`** — 10 methods: `create_workspace`, `get_workspace_for_user`, `get_member_role`, `create_invite_link`, `accept_invite`, `list_members`, `update_member_role`, `remove_member`, etc. Backend CRUD is ~90% done.
- **`app/middleware/workspace_role.py`** — `require_role(*allowed_roles)` dependency. Solo users pass through. Team members gated by role. Already used by some routes.
- **`app/services/workspace_data_filter.py`** — Filters query results by workspace scope. Used by data_io and other services.
- **`app/routers/teams.py`** — 9 endpoints for team management (list members, invite, accept, update role, remove). Backend API surface mostly done.
- **`app/routers/teams_rbac.py`** — RBAC-specific endpoints.
- **`supabase/migrations/20260403200000_teams_rbac.sql`** — `workspaces`, `workspace_members`, `workspace_invites` tables with full RLS policies.
- **Resend integration** — `RESEND_API_KEY`, `RESEND_FROM_ADDRESS`, `RESEND_AUDIENCE_ID` already configured in frontend/.env.
- **`sonner` toast library** — Already used throughout the frontend for notifications.
- **`SubscriptionBadge` component** — Reusable badge pattern for role badges.

### Established Patterns

- **`require_role("admin")` dependency** — FastAPI middleware pattern for role-gating endpoints.
- **Toast notifications via `sonner`** — Used in chat, billing, settings pages.
- **Dashboard settings pattern** — `/dashboard/settings` already exists with multiple subsections.
- **Confirmation dialog pattern** — Used in approval workflows, delete actions.

### Integration Points

- **Sidebar navigation** — Need to conditionally hide admin-only nav items for members (different from Phase 52's lock icons — role gating hides, tier gating shows with lock).
- **PremiumShell** — Shell layout component. May need to read workspace role to conditionally render admin sections.
- **`/invite/{token}` route** — New Next.js page for invite acceptance. Needs to handle both logged-in and not-logged-in states.
- **Supabase Auth** — Invite accept flow may need to coordinate with Supabase signup.

</code_context>

<deferred>
## Deferred Ideas

- **Editor/Viewer granular roles** — Only Admin + Member for now. Finer granularity when customer demand warrants.
- **Per-member content isolation** — Flat visibility is the v7.0 model. Per-member isolation would be a Phase 54+ feature.
- **Workspace deletion flow** — Admin can rename but not delete workspace in Phase 53. Deletion with data export is deferred.
- **Cross-workspace membership** — Users belong to one workspace at a time. Multi-workspace is deferred.
- **Member activity tracking / last active** — Not in Phase 53 member list. Can be added later.
- **Bulk invite (CSV upload)** — One-at-a-time invites only for now.

</deferred>

---

*Phase: 53-multi-user-teams*
*Context gathered: 2026-04-09*
