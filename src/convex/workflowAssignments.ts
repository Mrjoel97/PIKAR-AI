import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { Doc, Id } from "./_generated/dataModel";
import { internal } from "./_generated/api";

// Query to get workflow steps assigned to a user
export const getAssignedSteps = query({
  args: { 
    userId: v.id("users"),
    businessId: v.optional(v.id("businesses")),
    status: v.optional(v.union(v.literal("pending"), v.literal("in_progress"), v.literal("completed"), v.literal("blocked"))),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    let query = ctx.db
      .query("workflowSteps")
      .withIndex("by_assignee", (q) => q.eq("assigneeId", args.userId));

    if (args.businessId) {
      query = query.filter((q) => q.eq(q.field("businessId"), args.businessId));
    }

    if (args.status) {
      query = query.filter((q) => q.eq(q.field("status"), args.status));
    }

    const steps = await query.collect();

    // Get workflow details for each step
    const stepsWithWorkflows = await Promise.all(
      steps.map(async (step) => {
        const workflow = await ctx.db.get(step.workflowId);
        return {
          ...step,
          workflow,
        };
      })
    );

    return stepsWithWorkflows;
  },
});

// Query to get steps due soon
export const getStepsDueSoon = query({
  args: { 
    userId: v.id("users"),
    hoursAhead: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const hoursAhead = args.hoursAhead || 24;
    const dueTime = Date.now() + (hoursAhead * 60 * 60 * 1000);

    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_assignee", (q) => q.eq("assigneeId", args.userId))
      .filter((q) => 
        q.and(
          q.neq(q.field("status"), "completed"),
          q.lte(q.field("dueDate"), dueTime),
          q.neq(q.field("dueDate"), undefined)
        )
      )
      .collect();

    // Get workflow details
    const stepsWithWorkflows = await Promise.all(
      steps.map(async (step) => {
        const workflow = await ctx.db.get(step.workflowId);
        return {
          ...step,
          workflow,
        };
      })
    );

    return stepsWithWorkflows;
  },
});

// Mutation to assign a step to a user
export const assignStep = mutation({
  args: {
    stepId: v.id("workflowSteps"),
    assigneeId: v.id("users"),
    dueDate: v.optional(v.number()),
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

    const step = await ctx.db.get(args.stepId);
    if (!step) {
      throw new Error("Workflow step not found");
    }

    // Update the step with assignment details
    await ctx.db.patch(args.stepId, {
      assigneeId: args.assigneeId,
      dueDate: args.dueDate,
      assignedAt: Date.now(),
      assignedBy: user._id,
      status: "pending",
    });

    // Send notification to assignee
    await ctx.runMutation(internal.notifications.sendNotification, {
      businessId: step.businessId,
      userId: args.assigneeId,
      type: "assignment",
      title: "New Task Assignment",
      message: `You have been assigned a new task: ${step.name}`,
      data: {
        stepId: args.stepId,
        workflowId: step.workflowId,
        dueDate: args.dueDate,
      },
      priority: args.dueDate && args.dueDate < Date.now() + (24 * 60 * 60 * 1000) ? "high" : "medium",
    });

    return args.stepId;
  },
});

// Mutation to update step status
export const updateStepStatus = mutation({
  args: {
    stepId: v.id("workflowSteps"),
    status: v.union(v.literal("pending"), v.literal("in_progress"), v.literal("completed"), v.literal("blocked")),
    notes: v.optional(v.string()),
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

    const step = await ctx.db.get(args.stepId);
    if (!step) {
      throw new Error("Workflow step not found");
    }

    // Check if user is assigned to this step or has permission
    if (step.assigneeId !== user._id) {
      // TODO: Add permission check for managers/admins
      throw new Error("Not authorized to update this step");
    }

    const updateData: any = {
      status: args.status,
    };

    if (args.status === "completed") {
      updateData.completedAt = Date.now();
      updateData.completedBy = user._id;
    }

    if (args.notes) {
      updateData.notes = args.notes;
    }

    await ctx.db.patch(args.stepId, updateData);

    // Send notification for completion
    if (args.status === "completed" && step.assignedBy) {
      await ctx.runMutation(internal.notifications.sendNotification, {
        businessId: step.businessId,
        userId: step.assignedBy,
        type: "workflow_completion",
        title: "Task Completed",
        message: `${step.name} has been completed by ${user.name || user.email}`,
        data: {
          stepId: args.stepId,
          workflowId: step.workflowId,
          completedBy: user._id,
        },
      });
    }

    return args.stepId;
  },
});

// Query to get workflow step details with assignment info
export const getStepDetails = query({
  args: { stepId: v.id("workflowSteps") },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const step = await ctx.db.get(args.stepId);
    if (!step) {
      return null;
    }

    // Get assignee details
    const assignee = step.assigneeId ? await ctx.db.get(step.assigneeId) : null;
    const assignedBy = step.assignedBy ? await ctx.db.get(step.assignedBy) : null;
    const completedBy = step.completedBy ? await ctx.db.get(step.completedBy) : null;
    const workflow = await ctx.db.get(step.workflowId);

    return {
      ...step,
      assignee: assignee ? {
        _id: assignee._id,
        name: assignee.name,
        email: assignee.email,
      } : null,
      assignedBy: assignedBy ? {
        _id: assignedBy._id,
        name: assignedBy.name,
        email: assignedBy.email,
      } : null,
      completedBy: completedBy ? {
        _id: completedBy._id,
        name: completedBy.name,
        email: completedBy.email,
      } : null,
      workflow,
    };
  },
});

// Query to get assignment analytics for a business
export const getAssignmentAnalytics = query({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .collect();

    const totalSteps = steps.length;
    const assignedSteps = steps.filter(s => s.assigneeId).length;
    const completedSteps = steps.filter(s => s.status === "completed").length;
    const overdueTasks = steps.filter(s => 
      s.dueDate && s.dueDate < Date.now() && s.status !== "completed"
    ).length;

    // Group by assignee
    const assigneeStats: Record<string, { assigned: number; completed: number; overdue: number }> = {};
    
    steps.forEach(step => {
      if (step.assigneeId) {
        const assigneeId = step.assigneeId;
        if (!assigneeStats[assigneeId]) {
          assigneeStats[assigneeId] = { assigned: 0, completed: 0, overdue: 0 };
        }
        
        assigneeStats[assigneeId].assigned++;
        
        if (step.status === "completed") {
          assigneeStats[assigneeId].completed++;
        }
        
        if (step.dueDate && step.dueDate < Date.now() && step.status !== "completed") {
          assigneeStats[assigneeId].overdue++;
        }
      }
    });

    return {
      totalSteps,
      assignedSteps,
      completedSteps,
      overdueTasks,
      assignmentRate: totalSteps > 0 ? (assignedSteps / totalSteps) * 100 : 0,
      completionRate: assignedSteps > 0 ? (completedSteps / assignedSteps) * 100 : 0,
      assigneeStats,
    };
  },
});