import { DurableObject } from "cloudflare:workers";

export interface Env {
  AGENT_BACKEND_ORIGIN: string;
  PUBLIC_BACKEND_ORIGIN?: string;
  ALLOWED_ORIGINS?: string;
  ROUTE_MODE?: "agent-only" | "split";
  AGENT_ROUTE_PREFIXES?: string;
  PUBLIC_ROUTE_PREFIXES?: string;
  INTERNAL_PROXY_TOKEN?: string;
  EDGE_RATE_LIMITER: DurableObjectNamespace<EdgeRateLimiter>;
}

type RateLimitRule = {
  limit: number;
  periodSeconds: number;
};

type RateLimitPatternRule = {
  method: string;
  pattern: RegExp;
  limit: number;
  periodSeconds: number;
};

type RateLimitDecision = {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAfterSeconds: number;
};

const EDGE_RATE_LIMIT_RULES: Record<string, RateLimitRule> = {
  "GET /action-history": { limit: 120, periodSeconds: 60 },
  "GET /action-history/": { limit: 120, periodSeconds: 60 },
  "GET /api-credentials": { limit: 120, periodSeconds: 60 },
  "GET /api-credentials/": { limit: 120, periodSeconds: 60 },
  "GET /integrations/providers": { limit: 120, periodSeconds: 60 },
  "POST /approvals/create": { limit: 5, periodSeconds: 60 },
  "GET /approvals/pending/list": { limit: 60, periodSeconds: 60 },
  "GET /approvals/history": { limit: 60, periodSeconds: 60 },
  "GET /ad-approvals/pending": { limit: 60, periodSeconds: 60 },
  "GET /outbound-webhooks/events": { limit: 60, periodSeconds: 60 },
  "GET /outbound-webhooks/endpoints": { limit: 120, periodSeconds: 60 },
  "POST /outbound-webhooks/endpoints": { limit: 20, periodSeconds: 60 },
  "GET /pages": { limit: 120, periodSeconds: 60 },
  "POST /pages/import": { limit: 10, periodSeconds: 60 },
  "POST /account/facebook-deletion-callback": { limit: 5, periodSeconds: 60 },
  "POST /account/export": { limit: 3, periodSeconds: 60 },
  "DELETE /account/delete": { limit: 3, periodSeconds: 60 },
  "GET /onboarding/status": { limit: 120, periodSeconds: 60 },
  "POST /onboarding/business-context": { limit: 30, periodSeconds: 60 },
  "POST /onboarding/preferences": { limit: 30, periodSeconds: 60 },
  "POST /onboarding/agent-setup": { limit: 30, periodSeconds: 60 },
  "POST /onboarding/switch-persona": { limit: 30, periodSeconds: 60 },
  "POST /onboarding/complete": { limit: 10, periodSeconds: 60 },
  "POST /onboarding/extract-context": { limit: 10, periodSeconds: 60 },
  "GET /community/posts": { limit: 120, periodSeconds: 60 },
  "POST /community/posts": { limit: 30, periodSeconds: 60 },
  "GET /support/tickets": { limit: 120, periodSeconds: 60 },
  "POST /support/tickets": { limit: 30, periodSeconds: 60 },
  "GET /teams/invites/details": { limit: 60, periodSeconds: 60 },
  "POST /teams/invites": { limit: 30, periodSeconds: 60 },
  "POST /teams/invites/accept": { limit: 30, periodSeconds: 60 },
  "GET /teams/workspace": { limit: 120, periodSeconds: 60 },
  "GET /teams/members": { limit: 120, periodSeconds: 60 },
  "GET /teams/analytics": { limit: 60, periodSeconds: 60 },
  "GET /teams/shared/initiatives": { limit: 120, periodSeconds: 60 },
  "GET /teams/shared/workflows": { limit: 120, periodSeconds: 60 },
  "GET /teams/activity": { limit: 60, periodSeconds: 60 },
  "GET /configuration/mcp-status": { limit: 30, periodSeconds: 60 },
  "GET /configuration/session-config": { limit: 120, periodSeconds: 60 },
  "GET /configuration/user-configs": { limit: 120, periodSeconds: 60 },
  "GET /configuration/social-status": { limit: 120, periodSeconds: 60 },
  "GET /configuration/google-workspace-status": { limit: 120, periodSeconds: 60 },
  "GET /configuration/settings": { limit: 120, periodSeconds: 60 },
  "PATCH /configuration/settings": { limit: 20, periodSeconds: 60 },
  "GET /finance/invoices": { limit: 120, periodSeconds: 60 },
  "GET /finance/assumptions": { limit: 120, periodSeconds: 60 },
  "GET /finance/revenue-timeseries": { limit: 60, periodSeconds: 60 },
  "GET /sales/contacts": { limit: 120, periodSeconds: 60 },
  "GET /sales/contacts/activities": { limit: 60, periodSeconds: 60 },
  "GET /sales/connected-accounts": { limit: 120, periodSeconds: 60 },
  "GET /sales/campaigns": { limit: 120, periodSeconds: 60 },
  "GET /sales/page-analytics": { limit: 60, periodSeconds: 60 },
  "GET /content/bundles": { limit: 120, periodSeconds: 60 },
  "GET /content/bundles/deliverables": { limit: 120, periodSeconds: 60 },
  "GET /content/campaigns": { limit: 120, periodSeconds: 60 },
  "GET /reports": { limit: 120, periodSeconds: 60 },
  "GET /reports/categories": { limit: 120, periodSeconds: 60 },
  "GET /governance/audit-log": { limit: 60, periodSeconds: 60 },
  "GET /governance/portfolio-health": { limit: 60, periodSeconds: 60 },
  "GET /governance/approval-chains": { limit: 60, periodSeconds: 60 },
  "GET /learning/courses": { limit: 120, periodSeconds: 60 },
  "GET /learning/progress": { limit: 120, periodSeconds: 60 },
  "GET /suggestions": { limit: 120, periodSeconds: 60 },
  "GET /webhooks/events": { limit: 60, periodSeconds: 60 },
};

const EDGE_RATE_LIMIT_PATTERN_RULES: RateLimitPatternRule[] = [
  {
    method: "GET",
    pattern: /^\/account\/deletion-status\/[^/]+$/,
    limit: 60,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/integrations\/[^/]+\/authorize$/,
    limit: 60,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/integrations\/[^/]+\/callback$/,
    limit: 60,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/approvals\/[^/]+$/,
    limit: 5,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/approvals\/[^/]+\/decision$/,
    limit: 5,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/ad-approvals\/[^/]+$/,
    limit: 30,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/ad-approvals\/[^/]+\/decide$/,
    limit: 10,
    periodSeconds: 60,
  },
  {
    method: "PATCH",
    pattern: /^\/outbound-webhooks\/endpoints\/[^/]+$/,
    limit: 30,
    periodSeconds: 60,
  },
  {
    method: "DELETE",
    pattern: /^\/outbound-webhooks\/endpoints\/[^/]+$/,
    limit: 20,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/outbound-webhooks\/endpoints\/[^/]+\/deliveries$/,
    limit: 60,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/outbound-webhooks\/endpoints\/[^/]+\/test$/,
    limit: 10,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/pages\/[^/]+$/,
    limit: 120,
    periodSeconds: 60,
  },
  {
    method: "PATCH",
    pattern: /^\/pages\/[^/]+$/,
    limit: 30,
    periodSeconds: 60,
  },
  {
    method: "DELETE",
    pattern: /^\/pages\/[^/]+$/,
    limit: 30,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/pages\/[^/]+\/publish$/,
    limit: 20,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/pages\/[^/]+\/unpublish$/,
    limit: 20,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/pages\/[^/]+\/duplicate$/,
    limit: 10,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/pages\/[^/]+\/submit$/,
    limit: 30,
    periodSeconds: 60,
  },
  {
    method: "PATCH",
    pattern: /^\/support\/tickets\/[^/]+$/,
    limit: 30,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/community\/posts\/[^/]+$/,
    limit: 120,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/reports\/[^/]+$/,
    limit: 120,
    periodSeconds: 60,
  },
  {
    method: "GET",
    pattern: /^\/governance\/approval-chains\/[^/]+$/,
    limit: 60,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/community\/posts\/[^/]+\/comments$/,
    limit: 30,
    periodSeconds: 60,
  },
  {
    method: "POST",
    pattern: /^\/community\/posts\/[^/]+\/upvote$/,
    limit: 60,
    periodSeconds: 60,
  },
  {
    method: "DELETE",
    pattern: /^\/support\/tickets\/[^/]+$/,
    limit: 30,
    periodSeconds: 60,
  },
];

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
  "/compliance",
  "/kpis",
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
  "/finance",
  "/sales",
  "/content",
  "/governance",
  "/reports",
  "/learning",
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

function getRateLimitKey(request: Request, url: URL): string | null {
  if (url.hostname !== "api.pikar-ai.com") {
    return null;
  }

  const rule = getRateLimitRule(request, url);
  if (!rule) {
    return null;
  }

  const clientIp =
    request.headers.get("cf-connecting-ip")?.trim() ||
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    "unknown";

  return `${request.method}:${url.pathname}:${clientIp}`;
}

function getRateLimitRule(request: Request, url: URL): RateLimitRule | null {
  const exactRule = EDGE_RATE_LIMIT_RULES[`${request.method} ${url.pathname}`];
  if (exactRule) {
    return exactRule;
  }

  const patternRule = EDGE_RATE_LIMIT_PATTERN_RULES.find(
    (item) => item.method === request.method && item.pattern.test(url.pathname),
  );
  if (!patternRule) {
    return null;
  }

  return {
    limit: patternRule.limit,
    periodSeconds: patternRule.periodSeconds,
  };
}

async function checkEdgeRateLimit(
  request: Request,
  env: Env,
  url: URL,
): Promise<RateLimitDecision | null> {
  const key = getRateLimitKey(request, url);
  if (!key) {
    return null;
  }

  const rule = getRateLimitRule(request, url);
  if (!rule) {
    return null;
  }

  const stub = env.EDGE_RATE_LIMITER.getByName(key);
  return stub.check(rule.limit, rule.periodSeconds);
}

function applyRateLimitHeaders(headers: Headers, rateLimit: RateLimitDecision | null): void {
  if (!rateLimit) {
    return;
  }

  headers.set("x-pikar-rate-limit-limit", String(rateLimit.limit));
  headers.set("x-pikar-rate-limit-remaining", String(rateLimit.remaining));
  headers.set("x-pikar-rate-limit-reset", String(rateLimit.resetAfterSeconds));
}

function buildRateLimitResponse(
  request: Request,
  env: Env,
  rateLimit: RateLimitDecision,
): Response {
  const response = Response.json(
    {
      ok: false,
      error: "Rate limit exceeded",
      retry_after_seconds: rateLimit.resetAfterSeconds,
    },
    { status: 429 },
  );
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  applyRateLimitHeaders(response.headers, rateLimit);
  response.headers.set("Retry-After", String(rateLimit.resetAfterSeconds));
  return response;
}

function proxyUrl(request: Request, env: Env): URL {
  const incoming = new URL(request.url);
  const origin = resolveTargetOrigin(incoming.pathname, env);
  return new URL(`${origin}${incoming.pathname}${incoming.search}`);
}

async function proxyRequest(
  request: Request,
  env: Env,
  rateLimit: RateLimitDecision | null = null,
): Promise<Response> {
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
  applyRateLimitHeaders(outgoing, rateLimit);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: outgoing,
  });
}

type RateLimitState = {
  count: number;
  resetAt: number;
};

export class EdgeRateLimiter extends DurableObject<Env> {
  async check(limit: number, periodSeconds: number): Promise<RateLimitDecision> {
    const now = Date.now();
    const existing = await this.ctx.storage.get<RateLimitState>("window");

    let count = 0;
    let resetAt = now + periodSeconds * 1000;
    if (existing && existing.resetAt > now) {
      count = existing.count;
      resetAt = existing.resetAt;
    }

    count += 1;
    await this.ctx.storage.put("window", { count, resetAt });
    await this.ctx.storage.setAlarm(resetAt);

    return {
      allowed: count <= limit,
      limit,
      remaining: Math.max(0, limit - count),
      resetAfterSeconds: Math.max(1, Math.ceil((resetAt - now) / 1000)),
    };
  }

  async alarm(): Promise<void> {
    await this.ctx.storage.deleteAll();
  }
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
      const rateLimit = await checkEdgeRateLimit(request, env, url);
      if (rateLimit && !rateLimit.allowed) {
        return buildRateLimitResponse(request, env, rateLimit);
      }

      return await proxyRequest(request, env, rateLimit);
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
