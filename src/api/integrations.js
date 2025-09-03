import { generateText } from 'ai'
import { openai } from '@ai-sdk/openai'
import { supabase } from '@/lib/supabase'

function tryParseJSON(text, fallback) {
  try {
    const s = text.indexOf('{')
    const e = text.lastIndexOf('}') + 1
    if (s >= 0 && e > s) return JSON.parse(text.slice(s, e))
    return JSON.parse(text)
  } catch {
    return fallback
  }
}

export async function InvokeLLM({ prompt, response_json_schema, file_urls } = {}) {
  // Include file URLs in prompt if provided
  let fullPrompt = prompt
  if (Array.isArray(file_urls) && file_urls.length) {
    fullPrompt = `${prompt}\n\nContext files (URLs):\n${file_urls.join('\n')}`
  }
  const { text } = await generateText({ model: openai('gpt-4o-mini'), prompt: fullPrompt, temperature: 0.7, maxTokens: 1400 })
  if (response_json_schema) {
    // Best-effort JSON parsing when a schema is requested
    return tryParseJSON(text, {})
  }
  return text
}

export async function UploadFile({ file, pathPrefix = 'uploads' }) {
  if (!file) throw new Error('file is required')
  const fileName = `${Date.now()}-${file.name}`
  const path = `${pathPrefix}/${fileName}`
  const { error } = await supabase.storage.from('uploads').upload(path, file, { upsert: true })
  if (error) throw error
  const { data } = supabase.storage.from('uploads').getPublicUrl(path)
  return { file_url: data.publicUrl }
}

export async function ExtractDataFromUploadedFile({ file_url, json_schema }) {
  // CSV-first extractor; attempts to fetch and parse CSV to JSON rows matching schema
  try {
    if (!file_url) throw new Error('file_url is required')
    const res = await fetch(file_url)
    const contentType = res.headers.get('content-type') || ''
    const text = await res.text()
    if (contentType.includes('text/csv') || file_url.toLowerCase().endsWith('.csv')) {
      const rows = csvToJson(text)
      const filtered = filterToSchema(rows, json_schema)
      return { status: 'success', output: filtered }
    }
    // Fallback: try to get structured JSON via AI if schema provided
    if (json_schema) {
      const prompt = `You are given a file's textual content below. Transform it into JSON that fits this JSON Schema: ${JSON.stringify(json_schema)}. Only output valid JSON.\n\nContent:\n${text.slice(0, 24000)}`
      const { text: aiText } = await generateText({ model: openai('gpt-4o-mini'), prompt, temperature: 0.2, maxTokens: 1300 })
      const parsed = tryParseJSON(aiText, null)
      if (parsed) return { status: 'success', output: parsed }
    }
    return { status: 'error', message: 'Unsupported file type or parsing failed' }
  } catch (e) {
    return { status: 'error', message: String(e?.message || e) }
  }
}

function csvToJson(csv) {
  const lines = csv.split(/\r?\n/).filter(Boolean)
  if (lines.length === 0) return []
  const headers = lines[0].split(',').map(h => h.trim())
  const data = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',')
    const obj = {}
    headers.forEach((h, idx) => { obj[h] = parseCsvValue(cols[idx]) })
    data.push(obj)
  }
  return data
}

function parseCsvValue(v) {
  if (v == null) return null
  const t = v.trim()
  if (t === '') return ''
  const num = Number(t)
  return isNaN(num) ? t : num
}

function filterToSchema(rows, schema) {
  if (!schema || !Array.isArray(rows)) return rows
  const itemSchema = schema.type === 'array' ? schema.items : schema
  const allowed = itemSchema?.properties ? Object.keys(itemSchema.properties) : null
  if (!allowed) return rows
  return rows.map(r => {
    const o = {}
    allowed.forEach(k => { if (r.hasOwnProperty(k)) o[k] = r[k] })
    return o
  })
}

// Placeholders for compatibility; wire to your provider if needed
export async function SendEmail() { throw new Error('SendEmail not implemented in this build') }
export async function GenerateImage() { throw new Error('GenerateImage not implemented in this build') }
