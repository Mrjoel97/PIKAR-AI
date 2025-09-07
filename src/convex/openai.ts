"use node";

import { action } from "./_generated/server";
import { v } from "convex/values";
import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";

// Simple non-streaming completion using Vercel AI SDK with OpenAI provider.
// Requires OPENAI_API_KEY to be set in Convex environment variables.
export const complete = action({
  args: {
    prompt: v.string(),
    model: v.optional(v.string()), // e.g., "gpt-4o-mini", "gpt-4o", "gpt-4.1"
  },
  handler: async (_ctx, args) => {
    if (!process.env.OPENAI_API_KEY) {
      throw new Error("Missing OPENAI_API_KEY. Set it in Convex project environment.");
    }
    const modelId = args.model ?? "gpt-4o-mini";

    const result = await generateText({
      model: openai(modelId),
      prompt: args.prompt,
    });

    return {
      text: result.text,
      usage: result.usage, // token usage, input/output counts
      model: modelId,
    };
  },
});
