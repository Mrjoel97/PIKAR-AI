# Plan: Click-to-View Media in Workspace & Closable Widgets

This plan covers:
1. **User click on media in chat** → view that image/video in full focus in the workspace (right panel).
2. **Close any widget in the workspace** → workspace returns to showing only the brief card.
3. **Remotion video** → shown in full focus *inside* the workspace (not on top as overlay), with the whole video (all scenes) playable.

---

## Principle: Widgets always full focus in the workspace

**Widgets in the workspace must never appear minimized.** Whenever a widget is shown in the workspace (right panel), it must always be displayed in **full focus**—never as a collapsed/minimized card or thumbnail in a grid. The workspace either shows:
- the **brief card** only (default when no widget is selected), or  
- **one widget at a time in full focus** (when the user or agent has selected a widget to view).

Any UI that currently shows multiple widgets in a minimized or grid form in the workspace should be changed so that widgets are only ever opened/viewed in full focus (e.g. replace the grid with a list of widget titles or thumbnails that *open* in full focus on click, or show only the single focused widget and a way to pick another).

---

## Part 1: Click media in chat to view in workspace

### Goal
When a user clicks an image or video (or Remotion video spec) that appears in the chat interface, that media should open in **full focus in the workspace area** on the right. This must work:
- When the agent has just created the media (current behavior is agent-triggered only).
- When the user returns to the page after a refresh: they should be able to click any media in the chat history and view it in the workspace.

### Current state
- **Agent-triggered focus**: When the agent returns a widget (e.g. image/video), the app calls `dispatchFocusWidget(widget, userId)` in `useAgentChat.ts`, so the workspace shows it in full focus.
- **Chat UI**: `MessageItem` renders each message and its widget via `WidgetContainer`. Media widgets (image, video, video_spec) are rendered with `fullFocus` in the chat bubble but are **not clickable** to re-focus in the workspace.
- **Workspace**: `ActiveWorkspace` listens for `WIDGET_FOCUS_EVENT` and sets `focusedWidget`; when set, it shows the widget in full focus with “Back to brief” and close (X).

### Target behavior
- Any **image**, **video**, or **video_spec** rendered in the chat (in any message) is **clickable**.
- On click: the same widget is focused in the workspace (right panel), i.e. `dispatchFocusWidget(widget, userId)`.
- Works after refresh: messages (and their widgets) are restored from history; clicking a media widget in any message focuses it in the workspace. No extra persistence needed.

### Implementation steps

| Step | Task | Location / approach |
|------|------|---------------------|
| 1.1 | Expose “view in workspace” from chat | **`ChatInterface`** (or `useAgentChat`): provide a callback that accepts a `WidgetDefinition` and dispatches focus. Need `userId`: get from `createClient().auth.getUser()` or from existing context (e.g. `usePersona()` / `useChatSession()` if userId is available there). |
| 1.2 | Pass callback to MessageItem | **`ChatInterface`**: pass e.g. `onViewInWorkspace={(widget) => { getUserId().then(id => id && dispatchFocusWidget(widget, id)); }}` to each `MessageItem`. Only relevant for messages that have a media widget. |
| 1.3 | Make media clickable in MessageItem | **`MessageItem`**: for messages where `msg.widget` is type `image`, `video`, or `video_spec`, wrap the `WidgetContainer` (or the media content) in a clickable element (e.g. `<button type="button">` or `<div role="button" tabIndex={0} onClick={...} onKeyDown={...}>`). On click: call `onViewInWorkspace(msg.widget)`. Add clear affordance (e.g. “View in workspace” tooltip or icon on hover) and ensure accessibility (keyboard, aria-label). |
| 1.4 | Optional: visual affordance | Add a small “View in workspace” or expand icon on hover for media in chat so users discover the action. |

### Files to touch
- `frontend/src/components/chat/ChatInterface.tsx` – get userId, pass `onViewInWorkspace` to `MessageItem`.
- `frontend/src/components/chat/MessageItem.tsx` – accept `onViewInWorkspace`, wrap media in clickable area and call it on click.
- Optionally `frontend/src/hooks/useAgentChat.ts` – if callback is defined there and passed up.

### Acceptance criteria
- User clicks an image in the chat → workspace (right) shows that image in full focus.
- User clicks a video in the chat → workspace shows that video in full focus.
- User clicks a Remotion (video_spec) in the chat → workspace shows that video in full focus.
- After page refresh, user can click any media in chat history and it opens in the workspace.

---

## Part 2: Close widgets in workspace (full focus only)

### Goal
- When a widget is shown in **full focus** in the workspace, the user can close it and return to the default view (brief card only).
- **No minimized widgets in the workspace**: per the principle above, the workspace never shows widgets in a minimized/grid form; it shows either the brief or one widget in full focus. So “closing” applies to the currently focused widget (and optionally to removing a widget from the “session list” so it no longer appears as an option to open).
- Closing any widget returns the workspace to the default view (brief card only, or brief + list of available widgets to open in full focus).

### Current state
- **Full focus**: `ActiveWorkspace` already has “Back to brief” and an X button that call `closeFocusMode()` → `setFocusedWidget(null)`. So closing in full-focus mode is implemented.
- **Session widgets grid**: In `PersonaDashboardLayout`, session widgets (non-media, non-briefing) are currently rendered in a **grid** with `WidgetContainer` (some with minimized state). Per the principle, this must change: the workspace must not render widgets as minimized. Either (a) remove the grid and show only a list of widget titles/thumbnails that open in full focus when clicked, or (b) show only the single focused widget in full focus and a way to pick another from the session; no minimized widget cards in the workspace.
- Pinned widgets today have `onDismiss` (unpin). Same rule: when shown in the workspace, they must appear in full focus only (e.g. open from a list, not as minimized cards in a grid).

### Target behavior
- **Full focus only**: Keep existing “Back to brief” and X for the focused widget. The workspace never shows a minimized widget.
- **Session/pinned widgets**: Do not render session or pinned widgets in a minimized grid in the workspace. Instead, e.g. show a compact list or row of “Recent widgets” / “Pinned” as clickable items that open the chosen widget in **full focus**. Each such widget, when open, can be closed (and optionally removed from the list) via “Back to brief” or X; on close, remove from storage if desired and clear focus so the workspace shows only the brief (and the list of available widgets, if that list is part of the default view).
- **Close/dismiss**: When the user closes the focused widget: (1) `setFocusedWidget(null)` (or `dispatchFocusWidget(null, userId)`), (2) optionally `WidgetDisplayService.deleteWidget(userId, widget.id)` if “close” should also remove it from the session list. Workspace then shows the default view (brief only, or brief + widget list).

### Implementation steps

| Step | Task | Location / approach |
|------|------|---------------------|
| 2.1 | No minimized widgets in workspace | **`PersonaDashboardLayout`** / **`ActiveWorkspace`**: Remove or replace the current “session widgets grid” that renders multiple widgets with `WidgetContainer` in minimized/card form. Replace with a default view that shows only the **brief card** and, if desired, a **list or row of widget titles/thumbnails** (session + pinned) that, when clicked, open that widget in **full focus** (e.g. `dispatchFocusWidget(widget.definition, userId)`). No widget in the workspace should be rendered with `isMinimized={true}` or in a small card. |
| 2.2 | Close focused widget | When a widget is in full focus, “Back to brief” and X already call `closeFocusMode()`. Optionally, on close, call `WidgetDisplayService.deleteWidget(userId, widget.id)` if the widget has an id and “close” should remove it from the session list. Ensure `dispatchFocusWidget(null, userId)` is used so the workspace clears focus and returns to the default view (brief + widget list if present). |
| 2.3 | Dismiss/remove from list | If the default view includes a list of “Recent” or “Pinned” widgets, each entry can have a small dismiss (X) that calls `deleteWidget` and refreshes the list; do not render that widget in a minimized form—only remove it from the list so it can no longer be opened. |

### Files to touch
- `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` – replace session widgets grid with a full-focus-only flow (e.g. list of widgets that open in full focus; no minimized grid).
- `frontend/src/components/dashboard/ActiveWorkspace.tsx` – default view shows brief only (and optional widget list); when a widget is focused, show only that widget in full focus with “Back to brief” and X.
- `frontend/src/components/widgets/WidgetRegistry.tsx` – ensure close (X) is shown when `onDismiss` is provided for the full-focus widget view.

### Acceptance criteria
- **Widgets in the workspace are never minimized**: the workspace either shows the brief (and optional widget list) or one widget in full focus.
- From full-focus view, user clicks “Back to brief” or X → workspace shows the default view (brief card, and optional list of widgets to open).
- User can open a widget from the list (if present) and it always opens in full focus; closing it returns to the default view.

---

## Part 3: Remotion video in workspace (full focus, whole video)

### Goal
- The Remotion (video_spec) widget must be viewed **in full focus inside the workspace** (right panel), not as an overlay on top of the page.
- The user must be able to **view the whole video with all scenes** (play from start to end with all sequences).

### Current state
- When the agent (or user via Part 1) focuses a `video_spec` widget, `ActiveWorkspace` renders `WidgetContainer` with `fullFocus={true}` in the same way as image/video. So the Remotion content is already rendered **inside** the workspace content area (not a modal/overlay).
- `VideoSpecWidget` uses `@remotion/player` with `GeneratedVideoComposition`; `inputProps` include `scenes` and `fps`, and `durationInFrames` is passed from the backend (total of all scene frames). So the **entire composition** (all scenes in sequence) is already playable in the Player.

### Target behavior
- **Placement**: Remotion stays in the workspace panel (no change). If any layout or z-index makes it appear “on top” of the workspace, adjust so it is clearly the main content of the workspace when in focus (e.g. ensure it’s inside the same scroll/container as “Back to brief”).
- **Whole video**: Confirm that `durationInFrames` and `scenes` from the backend result in the Player showing and playing all scenes from start to end. No “single scene” limitation.

### Implementation steps

| Step | Task | Location / approach |
|------|------|---------------------|
| 3.1 | Verify Remotion is workspace content, not overlay | **`ActiveWorkspace`**: Ensure the focus-mode block that renders `WidgetContainer` for `video_spec` is inside the main workspace layout (no fixed/absolute overlay that covers the whole page). The current structure (focus block with “Back to brief” + `WidgetContainer` below) is correct; only verify in the browser and fix any CSS (e.g. z-index, position) if the Remotion player appears as an overlay. |
| 3.2 | Verify full video with all scenes | **Backend**: `canva_media` already sends `scenes`, `fps`, and `durationInFrames` (total_frames). **Frontend**: `GeneratedVideoComposition` iterates over all `scenes` and renders a `Sequence` for each; `Player` receives `durationInFrames` so the timeline covers the whole video. Spot-check: multi-scene payload from backend results in multiple sequences and full duration in the Player. Add a short comment in `VideoSpecWidget` or `GeneratedVideoComposition` that “all scenes are played in sequence for the full duration” if helpful for future maintainers. |

### Files to touch
- `frontend/src/components/dashboard/ActiveWorkspace.tsx` – optional CSS/layout check.
- `frontend/src/components/widgets/VideoSpecWidget.tsx` or `GeneratedVideoComposition.tsx` – optional comment; no logic change if behavior is already correct.

### Acceptance criteria
- Remotion video_spec is shown in the workspace (right) in full focus, not as a modal or overlay on top of the app.
- User can play the full video from start to end with all scenes (no single-scene-only behavior).

---

## Summary

| Part | Summary |
|------|--------|
| **Principle** | **Widgets in the workspace never appear minimized; they always appear in full focus.** Default view = brief card (and optional list of widgets to open). When a widget is shown, it is the only content in full focus. |
| 1 | Add click handler on media (image/video/video_spec) in chat that calls `dispatchFocusWidget(widget, userId)` so the user can view it in the workspace; works after refresh. |
| 2 | Remove minimized/grid widget view from the workspace. Show only brief or one widget in full focus; add optional list of session/pinned widgets that open in full focus on click. Keep “Back to brief”/X to close the focused widget and return to default view. |
| 3 | Confirm Remotion is rendered in the workspace content area and that the whole video (all scenes) is playable; fix layout/CSS if needed. |

## Dependency order
- Part 1 and Part 2 can be implemented in parallel.
- Part 3 is verification and minor tweaks; can be done after or in parallel with 1 and 2.
