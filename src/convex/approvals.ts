import { v } from "convex/values";
import { mutation, query, internalMutation } from "./_generated/server";
import { Doc, Id } from "./_generated/dataModel";
import { internal } from "./_generated/api";

// Query to get approval queue items
export const getApprovalQueue = query({
  args: { 
    businessId: v.id("businesses"),
    assigneeId: v.optional(v.id("users")),
    status: v.optional(v.union(v.literal("pending"), v.literal("approved"), v.literal("rejected"))),
    priority: v.optional(v.union(v.literal("low"), v.literal("medium"), v.literal("high"), v.literal("urgent"))),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    let query = ctx.db
      .query("approvalQueue")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId));

    let approvals = await query.collect();

    // Filter by assignee if provided
    if (args.assigneeId) {
      approvals = approvals.filter(approval => approval.assigneeId === args.assigneeId);
    }

    // Filter by status if provided
    if (args.status) {
      approvals = approvals.filter(approval => approval.status === args.status);
    }

    // Filter by priority if provided
    if (args.priority) {
      approvals = approvals.filter(approval => approval.priority === args.priority);
    }

    // Sort by priority (urgent first) then by creation date
    const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 };
    approvals.sort((a, b) => {
      const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return a.createdAt - b.createdAt;
    });

    return approvals;
  },
});

// Query to get pending approvals for a user
export const getPendingApprovals = query({
  args: { 
    assigneeId: v.id("users"),
    businessId: v.optional(v.id("businesses")),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    let query = ctx.db
      .query("approvalQueue")
      .withIndex("by_assignee", (q) => q.eq("assigneeId", args.assigneeId))
      .filter((q) => q.eq(q.field("status"), "pending"));

    let approvals = await query.collect();

    // Filter by business if provided
    if (args.businessId) {
      approvals = approvals.filter(approval => approval.businessId === args.businessId);
    }

    // Sort by SLA deadline (most urgent first)
    approvals.sort((a, b) => {
      if (a.slaDeadline && b.slaDeadline) {
        return a.slaDeadline - b.slaDeadline;
      }
      if (a.slaDeadline && !b.slaDeadline) return -1;
      if (!a.slaDeadline && b.slaDeadline) return 1;
      return a.createdAt - b.createdAt;
    });

    // Apply limit if provided
    if (args.limit) {
      approvals = approvals.slice(0, args.limit);
    }

    return approvals;
  },
});

// Mutation to create an approval request
export const createApprovalRequest = mutation({
  args: {
    businessId: v.id("businesses"),
    workflowId: v.id("workflows"),
    stepId: v.id("workflowSteps"),
    assigneeId: v.id("users"),
    priority: v.optional(v.union(v.literal("low"), v.literal("medium"), v.literal("high"), v.literal("urgent"))),
    slaHours: v.optional(v.number()),
    comments: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .filter((q) => q.eq(q.field("email"), identity.email))
      .first();

    if (!user) {
      throw new Error("User not found");
    }

    const now = Date.now();
    const slaDeadline = args.slaHours 
      ? now + (args.slaHours * 60 * 60 * 1000)
      : undefined;

    const approvalId = await ctx.db.insert("approvalQueue", {
      businessId: args.businessId,
      workflowId: args.workflowId,
      stepId: args.stepId,
      assigneeId: args.assigneeId,
      requestedBy: user._id,
      status: "pending",
      priority: args.priority || "medium",
      createdAt: now,
      slaDeadline,
      comments: args.comments,
    });

    // Create notification for approver
    await ctx.runMutation(internal.notifications.sendNotification, {
      businessId: args.businessId,
      userId: args.assigneeId,
      type: "approval",
      title: "Approval Required",
      message: `You have a new approval request that requires your attention.`,
      data: {
        approvalId,
        workflowId: args.workflowId,
        stepId: args.stepId,
        priority: args.priority || "medium",
        slaDeadline,
      },
      priority: args.priority === "urgent" ? "high" : "medium",
    });

    // Track telemetry event
    await ctx.runMutation(internal.telemetry.trackSystemEvent, {
      businessId: args.businessId,
      userId: user._id,
      eventName: "approval_request_created",
      eventData: {
        approvalId,
        workflowId: args.workflowId,
        stepId: args.stepId,
        assigneeId: args.assigneeId,
        priority: args.priority || "medium",
      },
    });

    return approvalId;
  },
});

// Mutation to approve or reject an approval request
export const processApproval = mutation({
  args: {
    approvalId: v.id("approvalQueue"),
    action: v.union(v.literal("approve"), v.literal("reject")),
    comments: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .filter((q) => q.eq(q.field("email"), identity.email))
      .first();

    if (!user) {
      throw new Error("User not found");
    }

    const approval = await ctx.db.get(args.approvalId);
    if (!approval) {
      throw new Error("Approval request not found");
    }

    // Check if user is authorized to process this approval
    if (approval.assigneeId !== user._id) {
      throw new Error("Not authorized to process this approval");
    }

    if (approval.status !== "pending") {
      throw new Error("Approval request has already been processed");
    }

    const now = Date.now();
    const updateData: any = {
      status: args.action === "approve" ? "approved" : "rejected",
      comments: args.comments,
    };

    if (args.action === "approve") {
      updateData.approvedAt = now;
      updateData.approvedBy = user._id;
    } else {
      updateData.rejectedAt = now;
      updateData.rejectedBy = user._id;
      updateData.rejectionReason = args.comments;
    }

    await ctx.db.patch(args.approvalId, updateData);

    // Create notification for requester
    await ctx.runMutation(internal.notifications.sendNotification, {
      businessId: approval.businessId,
      userId: approval.requestedBy,
      type: "approval",
      title: `Approval ${args.action === "approve" ? "Approved" : "Rejected"}`,
      message: `Your approval request has been ${args.action}d by ${user.name || user.email}.`,
      data: {
        approvalId: args.approvalId,
        workflowId: approval.workflowId,
        stepId: approval.stepId,
        action: args.action,
        comments: args.comments,
      },
      priority: args.action === "reject" ? "high" : "medium",
    });

    // If approved, we could update the workflow step status here
    // For now, we'll just track the approval - the step status update
    // should be handled by the workflow orchestration system

    // Track telemetry event
    await ctx.runMutation(internal.telemetry.trackSystemEvent, {
      businessId: approval.businessId,
      userId: user._id,
      eventName: `approval_${args.action}d`,
      eventData: {
        approvalId: args.approvalId,
        workflowId: approval.workflowId,
        stepId: approval.stepId,
        processingTime: now - approval.createdAt,
        comments: args.comments,
      },
    });

    return args.approvalId;
  },
});

// Query to get approval analytics
export const getApprovalAnalytics = query({
  args: { 
    businessId: v.id("businesses"),
    timeRange: v.optional(v.number()), // days
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const timeRange = args.timeRange || 30; // Default 30 days
    const startTime = Date.now() - (timeRange * 24 * 60 * 60 * 1000);

    const approvals = await ctx.db
      .query("approvalQueue")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .filter((q) => q.gt(q.field("createdAt"), startTime))
      .collect();

    const totalApprovals = approvals.length;
    const pendingApprovals = approvals.filter(a => a.status === "pending").length;
    const approvedApprovals = approvals.filter(a => a.status === "approved").length;
    const rejectedApprovals = approvals.filter(a => a.status === "rejected").length;

    // Calculate SLA compliance
    const processedApprovals = approvals.filter(a => a.status !== "pending");
    const slaBreaches = processedApprovals.filter(a => {
      if (!a.slaDeadline) return false;
      const processedAt = a.approvedAt || a.rejectedAt || Date.now();
      return processedAt > a.slaDeadline;
    }).length;

    // Calculate average processing time
    const avgProcessingTime = processedApprovals.length > 0
      ? processedApprovals.reduce((sum, a) => {
          const processedAt = a.approvedAt || a.rejectedAt || Date.now();
          return sum + (processedAt - a.createdAt);
        }, 0) / processedApprovals.length
      : 0;

    // Group by priority
    const priorityStats = {
      urgent: approvals.filter(a => a.priority === "urgent").length,
      high: approvals.filter(a => a.priority === "high").length,
      medium: approvals.filter(a => a.priority === "medium").length,
      low: approvals.filter(a => a.priority === "low").length,
    };

    // Group by assignee
    const assigneeStats: Record<string, { pending: number; approved: number; rejected: number }> = {};
    approvals.forEach(approval => {
      const assigneeId = approval.assigneeId;
      if (!assigneeStats[assigneeId]) {
        assigneeStats[assigneeId] = { pending: 0, approved: 0, rejected: 0 };
      }
      if (approval.status === "pending") assigneeStats[assigneeId].pending++;
      else if (approval.status === "approved") assigneeStats[assigneeId].approved++;
      else if (approval.status === "rejected") assigneeStats[assigneeId].rejected++;
    });

    return {
      totalApprovals,
      pendingApprovals,
      approvedApprovals,
      rejectedApprovals,
      approvalRate: totalApprovals > 0 ? (approvedApprovals / totalApprovals) * 100 : 0,
      rejectionRate: totalApprovals > 0 ? (rejectedApprovals / totalApprovals) * 100 : 0,
      slaBreaches,
      slaComplianceRate: processedApprovals.length > 0 ? ((processedApprovals.length - slaBreaches) / processedApprovals.length) * 100 : 100,
      avgProcessingTimeHours: avgProcessingTime / (1000 * 60 * 60),
      priorityStats,
      assigneeStats,
      timeRange,
    };
  },
});

// Query to get overdue approvals
export const getOverdueApprovals = query({
  args: { 
    businessId: v.id("businesses"),
    assigneeId: v.optional(v.id("users")),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const now = Date.now();
    let query = ctx.db
      .query("approvalQueue")
      .withIndex("by_sla_deadline", (q) => q.lt("slaDeadline", now))
      .filter((q) => q.eq(q.field("status"), "pending"));

    let approvals = await query.collect();

    // Filter by business
    approvals = approvals.filter(approval => approval.businessId === args.businessId);

    // Filter by assignee if provided
    if (args.assigneeId) {
      approvals = approvals.filter(approval => approval.assigneeId === args.assigneeId);
    }

    return approvals.sort((a, b) => (a.slaDeadline || 0) - (b.slaDeadline || 0));
  },
});

// Scheduled function to send SLA breach notifications
export const checkApprovalSLABreaches = internalMutation({
  args: {},
  handler: async (ctx) => {
    const now = Date.now();
    const warningThreshold = now + (2 * 60 * 60 * 1000); // 2 hours from now

    // Get approvals that are approaching SLA deadline
    const upcomingBreaches = await ctx.db
      .query("approvalQueue")
      .withIndex("by_sla_deadline", (q) => q.lt("slaDeadline", warningThreshold))
      .filter((q) => q.eq(q.field("status"), "pending"))
      .collect();

    const approvalsNeedingWarning = upcomingBreaches.filter(approval => 
      approval.slaDeadline && approval.slaDeadline > now
    );

    for (const approval of approvalsNeedingWarning) {
      // Check if we already sent a warning for this approval
      const existingWarning = await ctx.db
        .query("notifications")
        .withIndex("by_user", (q) => q.eq("userId", approval.assigneeId))
        .filter((q) => 
          q.and(
            q.eq(q.field("type"), "sla_warning"),
            q.eq(q.field("data.approvalId"), approval._id)
          )
        )
        .first();

      if (!existingWarning) {
        await ctx.runMutation(internal.notifications.sendNotification, {
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
          priority: "high",
        });
      }
    }

    return approvalsNeedingWarning.length;
  },
});