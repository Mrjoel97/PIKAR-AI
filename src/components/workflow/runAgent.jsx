import { InvokeLLM } from "@/api/integrations";

/**
 * Standardized agent runner used by WorkflowExecutor.
 * Returns: { text: string, raw: any }
 */
export default async function runAgent(agent_name, { prompt, input = {}, file_urls = [] } = {}) {
  const header = `You are the "${agent_name}" agent. Perform the task precisely. Use the provided input JSON as context. Return a clear, concise result.`;
  const context = Object.keys(input || {}).length ? `\n\nContext (JSON):\n${JSON.stringify(input, null, 2)}` : "";
  const finalPrompt = `${header}\n\nTask:\n${prompt || "No specific instructions"}${context}`;

  const args = { prompt: finalPrompt };
  if (Array.isArray(file_urls) && file_urls.length > 0) {
    args.file_urls = file_urls;
  }

  const res = await InvokeLLM(args);
  const text = typeof res === "string" ? res : JSON.stringify(res);
  return { text, raw: res };
}