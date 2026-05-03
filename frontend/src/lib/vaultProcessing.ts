// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

const MIME_TYPES_BY_EXTENSION: Record<string, string> = {
  csv: 'text/csv',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  json: 'application/json',
  md: 'text/markdown',
  pdf: 'application/pdf',
  txt: 'text/plain',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

const PROCESS_RETRY_DELAYS_MS = [1500, 3000, 5000, 8000] as const
const DIRECT_VAULT_PROCESS_ENDPOINT = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '')}/vault/process`
  : '/api/vault/process'

type VaultProcessFailureShape = {
  detail?: unknown
  error?: unknown
  message?: unknown
  success?: unknown
}

export type VaultProcessResult =
  | {
      ok: true
      attempts: number
      data: Record<string, unknown>
      message: string | null
    }
  | {
      ok: false
      attempts: number
      message: string
      status: number | null
    }

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function getUploadMimeType(filename: string): string | null {
  const extension = filename.split('.').pop()?.toLowerCase() ?? ''
  return MIME_TYPES_BY_EXTENSION[extension] ?? null
}

function getFailureMessage(payload: VaultProcessFailureShape, fallback: string): string {
  if (typeof payload.message === 'string' && payload.message.trim()) {
    return payload.message
  }
  if (typeof payload.error === 'string' && payload.error.trim()) {
    return payload.error
  }
  if (typeof payload.detail === 'string' && payload.detail.trim()) {
    return payload.detail
  }
  return fallback
}

function isRetryableFailure(status: number | null, message: string): boolean {
  const normalized = message.toLowerCase()

  if (
    normalized.includes('storage-only')
    || normalized.includes('cannot be made searchable')
    || normalized.includes('supported searchable formats')
    || normalized.includes('extraction failed')
    || normalized.includes('mime type')
  ) {
    return false
  }

  if (status === 403 || status === 408 || status === 409 || status === 425 || status === 429) {
    return true
  }

  if (status !== null && status >= 500) {
    return true
  }

  return (
    normalized.includes('processing failed')
    || normalized.includes('file access not allowed')
    || normalized.includes('timed out')
    || normalized.includes('temporarily')
    || normalized.includes('try again')
  )
}

export function normalizeVaultUploadFile(file: File): File {
  const inferredType = getUploadMimeType(file.name)
  const currentType = file.type?.trim().toLowerCase() ?? ''

  if (!inferredType) {
    return file
  }

  if (currentType === inferredType) {
    return file
  }

  if (currentType && currentType !== 'application/octet-stream') {
    return file
  }

  return new File([file], file.name, {
    lastModified: file.lastModified,
    type: inferredType,
  })
}

export async function processVaultDocumentForSearch({
  accessToken,
  endpoint = DIRECT_VAULT_PROCESS_ENDPOINT,
  filePath,
  maxAttempts = 4,
}: {
  accessToken?: string | null
  endpoint?: string
  filePath: string
  maxAttempts?: number
}): Promise<VaultProcessResult> {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  let lastMessage = 'Processing failed'
  let lastStatus: number | null = null

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify({ file_path: filePath }),
      })
      const payload = (await response.json().catch(
        () => ({}) as VaultProcessFailureShape,
      )) as VaultProcessFailureShape

      if (response.ok && payload.success !== false) {
        return {
          ok: true,
          attempts: attempt,
          data: payload as Record<string, unknown>,
          message: typeof payload.message === 'string' ? payload.message : null,
        }
      }

      lastStatus = response.status
      lastMessage = getFailureMessage(payload, response.statusText || 'Processing failed')

      if (attempt >= maxAttempts || !isRetryableFailure(lastStatus, lastMessage)) {
        return {
          ok: false,
          attempts: attempt,
          message: lastMessage,
          status: lastStatus,
        }
      }
    } catch (error) {
      lastStatus = null
      lastMessage = error instanceof Error ? error.message : 'Processing failed'

      if (attempt >= maxAttempts) {
        return {
          ok: false,
          attempts: attempt,
          message: lastMessage,
          status: lastStatus,
        }
      }
    }

    const retryDelay = PROCESS_RETRY_DELAYS_MS[Math.min(attempt - 1, PROCESS_RETRY_DELAYS_MS.length - 1)]
    await wait(retryDelay)
  }

  return {
    ok: false,
    attempts: maxAttempts,
    message: lastMessage,
    status: lastStatus,
  }
}
