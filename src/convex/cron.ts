import { cronJobs } from "convex/server";
import { internal } from "./_generated/api";
import { internalMutation } from "./_generated/server";

const crons = cronJobs();

// Local scheduled jobs to avoid cross-module references

export const checkWorkflowSLAsCron = internalMutation({
  args: {},
  handler: async (ctx) => {
    const now = Date.now();
    const twoHoursFromNow = now + 2 * 60 * 60 * 1000;

    // Find steps due within 2 hours or overdue and not completed
    const steps = await ctx.db.query("workflowSteps").collect();
    const pending = steps.filter(
      (s) =>
        s.status !== "completed" &&
        s.dueDate !== undefined &&
        s.dueDate <= twoHoursFromNow &&
        s.assigneeId
    );

    for (const step of pending) {
      await ctx.db.insert("notifications", {
        businessId: step.businessId,
        userId: step.assigneeId!,
        type: "sla_warning",
        title: "Task Due Soon",
        message: `Task "${step.name}" is due soon.`,
        data: {
          stepId: step._id,
          workflowId: step.workflowId,
          dueDate: step.dueDate,
        },
        isRead: false,
        priority: "high",
        createdAt: now,
        expiresAt: now + 7 * 24 * 60 * 60 * 1000,
      });
    }
    return pending.length;
  },
});

export const checkApprovalSLABreachesCron = internalMutation({
  args: {},
  handler: async (ctx) => {
    const now = Date.now();
    const warningThreshold = now + 2 * 60 * 60 * 1000;

    const upcomingBreaches = await ctx.db
      .query("approvalQueue")
      .withIndex("by_sla_deadline", (q) => q.lt("slaDeadline", warningThreshold))
      .filter((q) => q.eq(q.field("status"), "pending"))
      .collect();

    const approvalsNeedingWarning = upcomingBreaches.filter(
      (approval) => approval.slaDeadline && approval.slaDeadline > now
    );

    for (const approval of approvalsNeedingWarning) {
      await ctx.db.insert("notifications", {
        businessId: approval.businessId,
        userId: approval.assigneeId,
        type: "sla_warning",
        title: "Approval SLA Warning",
        message: `Approval request is approaching SLA deadline in less than 2 hours.`,
        data: {
          approvalId: approval._id,
          workflowId: approval.workflowId,
          stepId: approval.stepId,
          slaDeadline: approval.slaDeadline,
        },
        isRead: false,
        priority: "high",
        createdAt: now,
        expiresAt: now + 7 * 24 * 60 * 60 * 1000,
      });
    }

    return approvalsNeedingWarning.length;
  },
});

export const cleanupExpiredNotificationsCron = internalMutation({
  args: {},
  handler: async (ctx) => {
    const now = Date.now();
    const expired = await ctx.db
      .query("notifications")
      .withIndex("by_expires_at", (q) => q.lt("expiresAt", now))
      .collect();

    for (const n of expired) {
      await ctx.db.delete(n._id);
    }
    return expired.length;
  },
});

export const cleanupOldTelemetryEventsCron = internalMutation({
  args: {},
  handler: async (ctx) => {
    const ninetyDaysAgo = Date.now() - 90 * 24 * 60 * 60 * 1000;
    const oldEvents = await ctx.db
      .query("telemetryEvents")
      .withIndex("by_timestamp", (q) => q.lt("timestamp", ninetyDaysAgo))
      .collect();

    for (const e of oldEvents) {
      await ctx.db.delete(e._id);
    }
    return oldEvents.length;
  },
});

// Schedule (use interval/cron explicitly)
crons.interval("sla-checks", { minutes: 15 }, internal.cron.checkWorkflowSLAsCron, {});
crons.interval("approval-sla-checks", { minutes: 30 }, internal.cron.checkApprovalSLABreachesCron, {});
crons.cron("cleanup-notifications", "0 2 * * *", internal.cron.cleanupExpiredNotificationsCron, {});
crons.cron("cleanup-telemetry", "0 3 * * 0", internal.cron.cleanupOldTelemetryEventsCron, {});

export default crons;