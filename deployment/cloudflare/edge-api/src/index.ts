export interface Env {
  AGENT_BACKEND_ORIGIN: string;
  PUBLIC_BACKEND_ORIGIN?: string;
  ALLOWED_ORIGINS?: string;
  ROUTE_MODE?: "agent-only" | "split";
  AGENT_ROUTE_PREFIXES?: string;
  PUBLIC_ROUTE_PREFIXES?: string;
  INTERNAL_PROXY_TOKEN?: string;
}

const DEFAULT_AGENT_PREFIXES = [
  "/a2a",
  "/briefing",
  "/app-builder",
  "/workflows",
  "/workflow-triggers",
  "/ws",
  "/vault",
  "/self-improvement",
  "/initiatives",
  "/reports",
  "/content",
  "/finance",
  "/sales",
  "/compliance",
  "/learning",
  "/kpis",
  "/governance",
  "/data-io",
  "/email-sequences",
  "/monitoring-jobs",
  "/byok",
  "/admin/chat",
  "/api/recruitment",
];

const DEFAULT_PUBLIC_PREFIXES = [
  "/health",
  "/webhooks",
  "/approvals",
  "/pages",
  "/community",
  "/account",
  "/teams",
  "/integrations",
  "/configuration",
  "/support",
  "/onboarding",
  "/action-history",
  "/suggestions",
  "/api-credentials",
  "/ad-approvals",
  "/outbound-webhooks",
];

function parsePrefixList(value: string | undefined, fallback: string[]): string[] {
  const source = value?.trim();
  if (!source) {
    return fallback;
  }

  return source
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => (item.startsWith("/") ? item : `/${item}`));
}

function normalizeOrigin(origin: string | undefined, label: string): string | null {
  const value = origin?.trim();
  if (!value) {
    return null;
  }

  try {
    const url = new URL(value);
    return url.origin;
  } catch {
    throw new Error(`${label} must be a valid absolute URL.`);
  }
}

function pathMatches(pathname: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function resolveTargetOrigin(pathname: string, env: Env): string {
  const agentOrigin = normalizeOrigin(env.AGENT_BACKEND_ORIGIN, "AGENT_BACKEND_ORIGIN");
  if (!agentOrigin) {
    throw new Error("AGENT_BACKEND_ORIGIN is required.");
  }

  const publicOrigin = normalizeOrigin(env.PUBLIC_BACKEND_ORIGIN, "PUBLIC_BACKEND_ORIGIN");
  const routeMode = env.ROUTE_MODE ?? "split";

  if (routeMode === "agent-only" || !publicOrigin) {
    return agentOrigin;
  }

  const publicPrefixes = parsePrefixList(env.PUBLIC_ROUTE_PREFIXES, DEFAULT_PUBLIC_PREFIXES);
  if (pathMatches(pathname, publicPrefixes)) {
    return publicOrigin;
  }

  const agentPrefixes = parsePrefixList(env.AGENT_ROUTE_PREFIXES, DEFAULT_AGENT_PREFIXES);
  if (pathMatches(pathname, agentPrefixes)) {
    return agentOrigin;
  }

  return publicOrigin;
}

function buildCorsHeaders(request: Request, env: Env): Headers {
  const headers = new Headers();
  const allowList = (env.ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const origin = request.headers.get("Origin");
  if (!origin) {
    return headers;
  }

  if (allowList.length === 0 || allowList.includes(origin)) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Access-Control-Allow-Credentials", "true");
    headers.set("Vary", "Origin");
  }

  return headers;
}

function handlePreflight(request: Request, env: Env): Response {
  const headers = buildCorsHeaders(request, env);
  headers.set("Access-Control-Allow-Methods", "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS");
  headers.set(
    "Access-Control-Allow-Headers",
    request.headers.get("Access-Control-Request-Headers") ?? "authorization,content-type",
  );
  headers.set("Access-Control-Max-Age", "86400");

  return new Response(null, { status: 204, headers });
}

function proxyUrl(request: Request, env: Env): URL {
  const incoming = new URL(request.url);
  const origin = resolveTargetOrigin(incoming.pathname, env);
  return new URL(`${origin}${incoming.pathname}${incoming.search}`);
}

async function proxyRequest(request: Request, env: Env): Promise<Response> {
  const target = proxyUrl(request, env);
  const headers = new Headers(request.headers);
  const publicOrigin = normalizeOrigin(env.PUBLIC_BACKEND_ORIGIN, "PUBLIC_BACKEND_ORIGIN");

  headers.set("x-forwarded-host", new URL(request.url).host);
  headers.set("x-forwarded-proto", "https");

  if (publicOrigin && target.origin === publicOrigin && env.INTERNAL_PROXY_TOKEN?.trim()) {
    headers.set("x-pikar-edge-token", env.INTERNAL_PROXY_TOKEN.trim());
  }

  const response = await fetch(
    new Request(target.toString(), {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    }),
  );

  const outgoing = new Headers(response.headers);
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => outgoing.set(key, value));
  outgoing.set("x-pikar-edge-target", target.origin);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: outgoing,
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health/edge") {
      return Response.json({
        ok: true,
        service: "pikar-edge-api",
        route_mode: env.ROUTE_MODE ?? "split",
      });
    }

    if (request.method === "OPTIONS") {
      return handlePreflight(request, env);
    }

    try {
      return await proxyRequest(request, env);
    } catch (error) {
      return Response.json(
        {
          ok: false,
          error: error instanceof Error ? error.message : "Unknown proxy error",
        },
        { status: 500 },
      );
    }
  },
};
