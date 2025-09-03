import { generateText } from 'ai'
import { openai } from '@ai-sdk/openai'

/**
 * Standardized agent runner used by WorkflowExecutor.
 * Returns: { text: string, raw: any }
 */
export default async function runAgent(agent_name, { prompt, input = {}, file_urls = [] } = {}) {
  const header = `You are the "${agent_name}" agent. Perform the task precisely. Use the provided input JSON as context. Return a clear, concise result.`;
  const context = Object.keys(input || {}).length ? `\n\nContext (JSON):\n${JSON.stringify(input, null, 2)}` : "";
  const finalPrompt = `${header}\n\nTask:\n${prompt || "No specific instructions"}${context}`;

  const filesNote = Array.isArray(file_urls) && file_urls.length ? `\n\nContext files (URLs):\n${file_urls.join('\n')}` : ''
  const { text } = await generateText({ model: openai('gpt-4o-mini'), prompt: finalPrompt + filesNote, temperature: 0.4, maxTokens: 900 })
  return { text, raw: text };
}