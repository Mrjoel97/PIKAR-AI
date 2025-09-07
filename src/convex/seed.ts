import { action } from "./_generated/server";
import { v } from "convex/values";
import { api } from "./_generated/api";

export const seedDemo = action({
  args: {
    email: v.string(),
  },
  handler: async (ctx, args) => {
    // Create or find business + initiative for the email
    const seeded = await ctx.runMutation(api.initiatives.seedForEmail, {
      email: args.email,
    });

    // Also seed a rich set of AI agents for that business
    if (seeded?.businessId) {
      await ctx.runMutation(api.aiAgents.seedEnhancedForBusiness, {
        businessId: seeded.businessId,
      });
    }

    return {
      message: "Demo data seeded",
      ...seeded,
    };
  },
});
