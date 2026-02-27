import { SavedWidget, WidgetDefinition, RenderOptions, validateWidgetDefinition } from '../types/widgets';

// Custom event name for widget changes (pin/unpin/save)
export const WIDGET_CHANGE_EVENT = 'pikar-widget-change';

// Custom event name for focusing a widget in the workspace (full-view mode)
export const WIDGET_FOCUS_EVENT = 'pikar-widget-focus';
// Custom event name for live workspace activity updates
export const WORKSPACE_ACTIVITY_EVENT = 'pikar-workspace-activity';

export interface WidgetChangeEventDetail {
    type: 'pin' | 'unpin' | 'save' | 'delete';
    widgetId?: string;
    userId: string;
}

export interface WidgetFocusEventDetail {
    widget: WidgetDefinition | null; // null to clear focus
    userId: string;
}

export type WorkspaceActivityPhase = 'running' | 'completed' | 'error';

export interface WorkspaceActivityTrace {
    type: 'thinking' | 'tool_use' | 'tool_output';
    content: string;
    toolName?: string;
}

export interface WorkspaceActivityEventDetail {
    userId: string;
    sessionId: string;
    phase: WorkspaceActivityPhase;
    agentName?: string;
    text?: string;
    traces?: WorkspaceActivityTrace[];
    updatedAt: string;
}

/**
 * Dispatch a custom event when widgets change.
 * This allows other components to react to widget state changes.
 */
function dispatchWidgetChange(detail: WidgetChangeEventDetail) {
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent(WIDGET_CHANGE_EVENT, { detail }));
    }
}

/**
 * Dispatch a custom event to focus a widget in the workspace (full-view mode).
 * This replaces all other widgets and shows the focused widget at full size.
 */
export function dispatchFocusWidget(widget: WidgetDefinition | null, userId: string) {
    if (typeof window !== 'undefined') {
        const detail: WidgetFocusEventDetail = { widget, userId };
        window.dispatchEvent(new CustomEvent(WIDGET_FOCUS_EVENT, { detail }));
    }
}

export function dispatchWorkspaceActivity(
    detail: Omit<WorkspaceActivityEventDetail, 'updatedAt'> & { updatedAt?: string }
) {
    if (typeof window !== 'undefined') {
        window.dispatchEvent(
            new CustomEvent(WORKSPACE_ACTIVITY_EVENT, {
                detail: {
                    ...detail,
                    updatedAt: detail.updatedAt || new Date().toISOString(),
                },
            })
        );
    }
}

export class WidgetDisplayService {
    private getStorageKey(userId: string, sessionId: string): string {
        return `pikar_widgets_${userId}_${sessionId}`;
    }

    private getPinnedStorageKey(userId: string): string {
        return `pikar_widgets_${userId}_pinned`;
    }

    /**
     * Save a widget to localStorage.
     */
    saveWidget(userId: string, sessionId: string, widget: WidgetDefinition, isPinned: boolean = false): SavedWidget | null {
        if (!validateWidgetDefinition(widget)) {
            console.warn('Invalid widget definition, skipping save', widget);
            return null;
        }

        try {
            // Create the SavedWidget object
            const id = crypto.randomUUID();
            const savedWidget: SavedWidget = {
                id,
                definition: widget,
                isMinimized: false,
                isPinned,
                createdAt: new Date().toISOString(),
                sessionId,
                userId,
            };

            // 1. Save to Session Storage
            const sessionKey = this.getStorageKey(userId, sessionId);
            const sessionWidgets = this.getSessionWidgets(userId, sessionId);
            sessionWidgets.push(savedWidget);
            localStorage.setItem(sessionKey, JSON.stringify(sessionWidgets));

            // 2. If pinned, save to Pinned Storage
            if (isPinned) {
                this.pinWidget(savedWidget.id, userId); // Fixed arity
                // Actually, let's reuse pinWidget or just duplicate the "addToPinned" logic to be safe/atomic here?
                // Simpler: Just rely on session storage first, then explicit pin?
                // The plan says "saveWidget" has "isPinned" arg.
                // If isPinned is true, we should ALSO add it to the pinned list.
                const pinnedKey = this.getPinnedStorageKey(userId);
                const pinnedWidgets = this.getPinnedWidgets(userId);
                // Avoid duplicates if ID somehow exists (statistically impossible with UUID but good practice)
                if (!pinnedWidgets.find(w => w.id === id)) {
                    pinnedWidgets.push(savedWidget);
                    localStorage.setItem(pinnedKey, JSON.stringify(pinnedWidgets));
                }
            }

            // Dispatch event to notify listeners
            dispatchWidgetChange({ type: 'save', widgetId: savedWidget.id, userId });

            return savedWidget;
        } catch (error) {
            console.error('Failed to save widget:', error);
            // Fallback or user notification logic could go here
            return null;
        }
    }

    /**
     * Retrieve widgets for a specific session.
     */
    getSessionWidgets(userId: string, sessionId: string): SavedWidget[] {
        try {
            const key = this.getStorageKey(userId, sessionId);
            const raw = localStorage.getItem(key);
            if (!raw) return [];
            return JSON.parse(raw) as SavedWidget[];
        } catch (e) {
            console.error('Error loading session widgets', e);
            return [];
        }
    }

    /**
     * Clear all widgets for a session (e.g. when syncing from loaded history).
     */
    clearSessionWidgets(userId: string, sessionId: string): void {
        try {
            const key = this.getStorageKey(userId, sessionId);
            localStorage.setItem(key, JSON.stringify([]));
            dispatchWidgetChange({ type: 'save', widgetId: '', userId });
        } catch (e) {
            console.error('Error clearing session widgets', e);
        }
    }

    /**
     * Get user's pinned widgets for dashboard display.
     */
    getPinnedWidgets(userId: string): SavedWidget[] {
        try {
            const key = this.getPinnedStorageKey(userId);
            const raw = localStorage.getItem(key);
            if (!raw) return [];
            return JSON.parse(raw) as SavedWidget[];
        } catch (e) {
            console.error('Error loading pinned widgets', e);
            return [];
        }
    }

    /**
     * Update widget UI state (minimized, etc).
     * Updates in BOTH session and pinned storage if present.
     */
    updateWidgetState(userId: string, widgetId: string, state: { isMinimized?: boolean }) {
        // We need userId to find where it might be.
        // However, the signature in plan was `updateWidgetState(widgetId: string, ...)` which assumes we know where it is?
        // Or maybe we search all known locations?
        // Without sessionId, we can't easily find it in session storage unless we look through ALL sessions.
        // The plan asks for: `updateWidgetState(widgetId: string, state: { isMinimized?: boolean })`
        // Implementation constraint: finding the widget.
        // I'll update the signature to include userId, and ideally sessionId if known.
        // If sessionId is NOT known, I might have to iterate all sessions (expensive).
        // Let's stick to the prompt's implied signature but add userId as it's LOCAL STORAGE, we need the key prefix.
        // Actually, I'll add userId because we need it for keys.

        // To implement "search everywhere" efficiently:
        // 1. Check pinned first.
        // 2. Check all sessions.

        // 1. Update in Pinned
        const pinnedKey = this.getPinnedStorageKey(userId);
        const pinnedWidgets = this.getPinnedWidgets(userId);
        const pinnedIndex = pinnedWidgets.findIndex(w => w.id === widgetId);
        if (pinnedIndex >= 0) {
            if (state.isMinimized !== undefined) pinnedWidgets[pinnedIndex].isMinimized = state.isMinimized;
            localStorage.setItem(pinnedKey, JSON.stringify(pinnedWidgets));
        }

        // 2. Update in all sessions (or specific if we knew it)
        // We need a helper to get all sessions to do this correctly without extra args.
        const sessions = this.getAllSessions(userId);
        for (const sid of sessions) {
            const sWidgets = this.getSessionWidgets(userId, sid);
            const idx = sWidgets.findIndex(w => w.id === widgetId);
            if (idx >= 0) {
                if (state.isMinimized !== undefined) sWidgets[idx].isMinimized = state.isMinimized;
                localStorage.setItem(this.getStorageKey(userId, sid), JSON.stringify(sWidgets));
                // Found it, we can break if we assume unique IDs (which we do)
                break;
            }
        }
    }

    /**
     * Delete widget from storage.
     */
    deleteWidget(userId: string, widgetId: string) {
        // Remove from Pinned
        const pinnedKey = this.getPinnedStorageKey(userId);
        let pinnedWidgets = this.getPinnedWidgets(userId);
        if (pinnedWidgets.some(w => w.id === widgetId)) {
            pinnedWidgets = pinnedWidgets.filter(w => w.id !== widgetId);
            localStorage.setItem(pinnedKey, JSON.stringify(pinnedWidgets));
        }

        // Remove from Sessions
        const sessions = this.getAllSessions(userId);
        for (const sid of sessions) {
            const key = this.getStorageKey(userId, sid);
            let sWidgets = this.getSessionWidgets(userId, sid);
            if (sWidgets.some(w => w.id === widgetId)) {
                sWidgets = sWidgets.filter(w => w.id !== widgetId);
                localStorage.setItem(key, JSON.stringify(sWidgets));
                break; // Valid optimization for unique IDs
            }
        }

        // Dispatch event to notify listeners
        dispatchWidgetChange({ type: 'delete', widgetId, userId });
    }

    /**
     * Mark widget as pinned for dashboard persistence.
     */
    pinWidget(widgetId: string, userId: string): void {
        // Find the widget first. It must exist in a session?
        // Or maybe we are pinning a specific instance.
        // Search sessions for it.
        let foundWidget: SavedWidget | undefined;

        const sessions = this.getAllSessions(userId);
        for (const sid of sessions) {
            const widgets = this.getSessionWidgets(userId, sid);
            foundWidget = widgets.find(w => w.id === widgetId);
            if (foundWidget) break;
        }

        if (!foundWidget) {
            console.warn('Cannot pin widget: not found', widgetId);
            return;
        }

        // Calculate key
        const pinnedKey = this.getPinnedStorageKey(userId);
        const pinnedWidgets = this.getPinnedWidgets(userId);

        // Update isPinned in the source (session) as well?
        // Yes, UI might want to reflect that.
        this.updateWidgetInternal(userId, widgetId, { isPinned: true });

        // Add to pinned list if not present
        if (!pinnedWidgets.find(w => w.id === widgetId)) {
            const toPin = { ...foundWidget, isPinned: true };
            pinnedWidgets.push(toPin);
            localStorage.setItem(pinnedKey, JSON.stringify(pinnedWidgets));
        }

        // Dispatch event to notify listeners
        dispatchWidgetChange({ type: 'pin', widgetId, userId });
    }

    private updateWidgetInternal(userId: string, widgetId: string, updates: Partial<SavedWidget>) {
        // Helper to update properties across storage locations without re-implementing find logic
        const sessions = this.getAllSessions(userId);
        for (const sid of sessions) {
            const key = this.getStorageKey(userId, sid);
            const sWidgets = this.getSessionWidgets(userId, sid);
            const idx = sWidgets.findIndex(w => w.id === widgetId);
            if (idx !== -1) {
                sWidgets[idx] = { ...sWidgets[idx], ...updates };
                localStorage.setItem(key, JSON.stringify(sWidgets));
                return;
            }
        }
    }

    /**
     * Remove widget from pinned collection.
     */
    unpinWidget(widgetId: string, userId: string): void {
        const pinnedKey = this.getPinnedStorageKey(userId);
        let pinnedWidgets = this.getPinnedWidgets(userId);

        if (pinnedWidgets.some(w => w.id === widgetId)) {
            pinnedWidgets = pinnedWidgets.filter(w => w.id !== widgetId);
            localStorage.setItem(pinnedKey, JSON.stringify(pinnedWidgets));

            // Also update the 'isPinned' status in the session storage so the star toggles off
            this.updateWidgetInternal(userId, widgetId, { isPinned: false });

            // Dispatch event to notify listeners
            dispatchWidgetChange({ type: 'unpin', widgetId, userId });
        }
    }

    /**
     * Return unique session IDs from localStorage.
     * Helper method required by plan.
     */
    getAllSessions(userId: string): string[] {
        const sessions: string[] = [];
        const prefix = `pikar_widgets_${userId}_`;
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(prefix) && !key.endsWith('_pinned')) {
                // Extract session ID: pikar_widgets_{userId}_{sessionId}
                const parts = key.split('_');
                // Parts: ['pikar', 'widgets', userId, sessionId...]
                // Handle potential underscores in userId or sessionId?
                // Assuming standard UUIDs or simple strings, basic split might be risky if userId has underscores.
                // Safer: remove prefix
                const sessionId = key.substring(prefix.length);
                if (sessionId) sessions.push(sessionId);
            }
        }
        return sessions;
    }

    /**
     * Serialize widgets to JSON for backup.
     */
    exportWidgets(userId: string): string {
        const allData: Record<string, any> = {
            pinned: this.getPinnedWidgets(userId),
            sessions: {}
        };

        const sessions = this.getAllSessions(userId);
        for (const sid of sessions) {
            allData.sessions[sid] = this.getSessionWidgets(userId, sid);
        }

        return JSON.stringify(allData);
    }

    /**
     * Restore widgets from JSON.
     */
    importWidgets(userId: string, json: string): void {
        try {
            const data = JSON.parse(json);
            if (data.pinned && Array.isArray(data.pinned)) {
                localStorage.setItem(this.getPinnedStorageKey(userId), JSON.stringify(data.pinned));
            }
            if (data.sessions) {
                for (const [sid, widgets] of Object.entries(data.sessions)) {
                    localStorage.setItem(this.getStorageKey(userId, sid), JSON.stringify(widgets));
                }
            }
        } catch (e) {
            console.error('Failed to import widgets', e);
        }
    }

    /**
      * Statistics for UI display.
      */
    getWidgetCount(userId: string): { total: number, pinned: number, sessions: number } {
        const pinned = this.getPinnedWidgets(userId);
        const sessions = this.getAllSessions(userId);
        let totalSessionWidgets = 0;
        for (const sid of sessions) {
            totalSessionWidgets += this.getSessionWidgets(userId, sid).length;
        }

        // Note: total might include duplicates if we count "instances".
        // Usually users want to know "how many pinned" and "how many in history".
        // We'll return the raw counts.
        return {
            total: pinned.length + totalSessionWidgets,
            pinned: pinned.length,
            sessions: sessions.length
        };
    }
}
