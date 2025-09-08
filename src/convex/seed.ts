import { Id } from "./_generated/dataModel";
import { action } from "./_generated/server";
import { v } from "convex/values";
import { api, internal } from "./_generated/api";
import type { FullAppInspectionReport } from "./inspector";

export const run = action({
  args: {},
  handler: async (ctx): Promise<{
    message: string;
    summary: FullAppInspectionReport["summary"];
    timestamp: number;
  }> => {
    const report: FullAppInspectionReport = await ctx.runAction(
      api.inspector.runInspection,
      {}
    );
    return {
      message: "Inspection completed",
      summary: report.summary,
      timestamp: report.timestamp,
    };
  }
});

export const seedDemo: any = action({
  args: {
    email: v.string(),
  },
  handler: async (ctx, args): Promise<{
    message: string;
    businessId?: Id<"businesses">;
    initiativeId?: Id<"initiatives">;
    diagnosticId?: Id<"diagnostics">;
  }> => {
    // Ensure a user exists for the provided email before seeding
    await ctx.runMutation(api.users.ensureSeedUser, { email: args.email });

    // Create or find business + initiative for the email
    const seeded: {
      businessId?: Id<"businesses">;
      initiativeId?: Id<"initiatives">;
      diagnosticId?: Id<"diagnostics">;
    } = await ctx.runMutation(api.initiatives.seedForEmail, {
      email: args.email,
    });

    // Seed AI agents bypassing RBAC using an internal mutation
    if (seeded?.businessId) {
      await ctx.runMutation(internal.aiAgents.seedForBusinessInternal, {
        businessId: seeded.businessId,
      });
    }

    return {
      message: "Demo data seeded",
      ...seeded,
    };
  },
});