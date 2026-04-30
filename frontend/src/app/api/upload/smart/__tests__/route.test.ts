/**
 * @vitest-environment node
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

const fetchMock = vi.fn();

vi.stubGlobal('fetch', fetchMock);

async function loadRoute() {
  return import('../route');
}

function makeRequest() {
  const body = new FormData();
  body.append('file', new Blob(['hello world'], { type: 'text/plain' }), 'notes.txt');
  return new NextRequest('http://localhost/api/upload/smart', {
    method: 'POST',
    headers: {
      authorization: 'Bearer test-token',
    },
    body,
  });
}

describe('POST /api/upload/smart', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useRealTimers();
    fetchMock.mockReset();
    process.env.BACKEND_URL = 'https://backend.example.com';
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('returns 401 when the incoming request has no auth header', async () => {
    const { POST } = await loadRoute();
    const res = await POST(
      new NextRequest('http://localhost/api/upload/smart', {
        method: 'POST',
        body: new FormData(),
      }),
    );

    expect(res.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('returns 504 when the upstream backend never responds before the proxy timeout', async () => {
    vi.useFakeTimers();

    fetchMock.mockImplementation((_url: string, init?: RequestInit) => {
      const signal = init?.signal;
      return new Promise((_resolve, reject) => {
        signal?.addEventListener('abort', () => {
          reject(new DOMException('The operation was aborted.', 'AbortError'));
        });
      });
    });

    const { POST } = await loadRoute();
    const pending = POST(makeRequest());

    await vi.advanceTimersByTimeAsync(35_000);
    const res = await pending;

    expect(res.status).toBe(504);
    await expect(res.json()).resolves.toEqual({
      error: 'Smart upload proxy timed out while waiting for the backend.',
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
