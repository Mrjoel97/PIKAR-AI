"use node";

import { action } from "./_generated/server";
import { v } from "convex/values";
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

// Simple text generation via Vercel AI SDK + OpenAI
export const generate = action({
  args: {
    prompt: v.string(),
    model: v.optional(v.string()), // e.g., "gpt-4o-mini", "gpt-4o", "gpt-4.1"
    temperature: v.optional(v.number()),
    maxTokens: v.optional(v.number()),
  },
  handler: async (_ctx, args) => {
    // Fail fast if key is not present
    if (!process.env.OPENAI_API_KEY) {
      throw new Error("OPENAI_API_KEY is not configured");
    }

    const modelName = args.model || "gpt-4o-mini";
    const temperature = args.temperature ?? 0.7;
    const maxOutputTokens = args.maxTokens ?? 512;

    const { text } = await generateText({
      model: openai(modelName),
      prompt: args.prompt,
      temperature,
      maxOutputTokens,
    });

    return { text, model: modelName };
  },
});