// AI Copy Generation Service (Vercel AI SDK + OpenAI)
// Requires packages: ai, @ai-sdk/openai

import { generateText } from 'ai'
import { openai } from '@ai-sdk/openai'

const model = openai('gpt-4o-mini')

export type SocialCopyInput = {
  platform: 'facebook' | 'instagram' | 'twitter' | 'linkedin' | 'youtube' | 'tiktok'
  persona?: string
  tone?: 'professional' | 'friendly' | 'playful' | 'authoritative' | 'witty'
  audience?: string
  campaignGoal?: 'awareness' | 'engagement' | 'traffic' | 'conversions'
  brandVoice?: string
  product?: string
  keyPoints?: string[]
  hashtags?: string[]
}

export async function generateSocialCopy(input: SocialCopyInput) {
  const prompt = `You are an expert social media copywriter.
Platform: ${input.platform}
Persona: ${input.persona || 'General brand persona'}
Tone: ${input.tone || 'friendly'}
Audience: ${input.audience || 'broad'}
Campaign goal: ${input.campaignGoal || 'engagement'}
Brand voice: ${input.brandVoice || 'clear and concise'}
Product: ${input.product || 'our solution'}
Key points: ${(input.keyPoints || []).join('; ')}
Hashtags: ${(input.hashtags || []).join(' ')}

Return JSON with fields: {
  "headline": string,
  "body": string,
  "cta": string,
  "hashtags": string[]
}
Make sure body length fits platform norms and includes variation potential for A/B testing.`

  const result = await generateText({ model, prompt, temperature: 0.7, maxTokens: 600 })

  try {
    const jsonStart = result.text.indexOf('{')
    const jsonEnd = result.text.lastIndexOf('}') + 1
    const json = JSON.parse(result.text.slice(jsonStart, jsonEnd))
    return json
  } catch (e) {
    return {
      headline: 'Discover what’s possible',
      body: result.text.trim(),
      cta: 'Learn more',
      hashtags: input.hashtags || []
    }
  }
}

export async function generateHashtags(topic: string, count = 10) {
  const prompt = `Generate ${count} high-quality hashtags for social media based on the topic: ${topic}.
Return JSON array of strings.
Avoid banned or sensitive terms.`
  const result = await generateText({ model, prompt, temperature: 0.5, maxTokens: 200 })
  try {
    const jsonStart = result.text.indexOf('[')
    const jsonEnd = result.text.lastIndexOf(']') + 1
    return JSON.parse(result.text.slice(jsonStart, jsonEnd))
  } catch (e) {
    return result.text
      .split(/\s|,|#/)
      .map(s => s.trim())
      .filter(Boolean)
      .slice(0, count)
      .map(s => (s.startsWith('#') ? s : `#${s}`))
  }
}

export async function outlineAdVariants(input: SocialCopyInput, variants = 2) {
  const prompt = `Create ${variants} ad copy variants for ${input.platform}.
Tone: ${input.tone || 'friendly'}; Goal: ${input.campaignGoal || 'engagement'}.
Return JSON array with items: {"variant_name","headline","body","cta","hypothesis"}`
  const result = await generateText({ model, prompt, temperature: 0.8, maxTokens: 800 })
  try {
    const jsonStart = result.text.indexOf('[')
    const jsonEnd = result.text.lastIndexOf(']') + 1
    return JSON.parse(result.text.slice(jsonStart, jsonEnd))
  } catch (e) {
    return [
      { variant_name: 'A', headline: 'Unlock value', body: result.text.slice(0, 160), cta: 'Get started', hypothesis: 'Short benefit-led copy improves CTR' },
      { variant_name: 'B', headline: 'Transform your workflow', body: result.text.slice(160, 320), cta: 'Try now', hypothesis: 'Vision-led message increases engagement' }
    ]
  }
}

