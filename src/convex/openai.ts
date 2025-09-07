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

    // Basic input validation
    const prompt = args.prompt.trim();
    if (prompt.length === 0) {
      throw new Error("Prompt must not be empty.");
    }
    if (prompt.length > 8000) {
      throw new Error("Prompt is too long. Max 8000 characters.");
    }

    const modelName = args.model || "gpt-4o-mini";
    const temperature = args.temperature ?? 0.7;
    const maxOutputTokens = args.maxTokens ?? 512;

    try {
      const { text } = await generateText({
        model: openai(modelName),
        prompt,
        temperature,
        maxOutputTokens,
      });

      return { text, model: modelName };
    } catch (err) {
      // Minimal detailed logging for diagnostics (server-side only)
      console.error("OpenAI generation error:", {
        message: (err as any)?.message,
        name: (err as any)?.name,
        status: (err as any)?.status,
        code: (err as any)?.code,
      });

      const status = (err as any)?.status as number | undefined;
      if (status === 401) {
        throw new Error("Invalid OpenAI API key. Please verify OPENAI_API_KEY.");
      }
      if (status === 429) {
        throw new Error(
          "Rate limit reached. Please wait and try again or reduce request frequency."
        );
      }
      if (status === 500 || status === 503) {
        throw new Error("OpenAI service is temporarily unavailable. Try again later.");
      }

      // Generic fallback
      const message =
        (err as any)?.message ?? "Unexpected error while generating AI response.";
      throw new Error(`AI generation failed: ${message}`);
    }
  },
});