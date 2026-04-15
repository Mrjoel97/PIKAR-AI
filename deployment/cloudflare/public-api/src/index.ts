export interface Env {
  FALLBACK_BACKEND_ORIGIN: string;
  ALLOWED_ORIGINS?: string;
  INTERNAL_PROXY_TOKEN?: string;
  SUPABASE_URL?: string;
  SUPABASE_ANON_KEY?: string;
  SUPABASE_SERVICE_ROLE_KEY?: string;
  LINKEDIN_CLIENT_SECRET?: string;
  LINKEDIN_WEBHOOK_SECRET?: string;
  [key: string]: string | undefined;
}

const DEFAULT_SESSION_CONFIG = {
  max_concurrent_streams: 4,
  memory_eviction_minutes: 30,
  max_active_sessions_in_memory: 20,
} as const;

const BUILT_IN_TOOLS_INFO = [
  {
    id: "tavily",
    name: "Web Search (Tavily)",
    description: "AI-powered web search - automatically used for research tasks.",
  },
  {
    id: "firecrawl",
    name: "Web Scraping (Firecrawl)",
    description: "Content extraction from webpages - automatically used for deep research.",
  },
] as const;

const CONFIGURABLE_TOOLS_INFO = [
  {
    id: "stitch",
    name: "Landing Page Builder (Stitch)",
    description: "Generate professional landing pages with AI. Creates HTML and React components.",
    envVar: "STITCH_API_KEY",
    docsUrl: "https://stitch.withgoogle.com/docs",
  },
  {
    id: "stripe",
    name: "Payments (Stripe)",
    description: "Accept payments, create checkout sessions, and manage subscriptions for landing pages.",
    envVar: "STRIPE_API_KEY",
    docsUrl: "https://stripe.com/docs",
  },
  {
    id: "canva",
    name: "Media Creation (Canva)",
    description: "Create professional graphics, social media posts, and visual content with AI.",
    envVar: "CANVA_API_KEY",
    docsUrl: "https://www.canva.dev/docs",
  },
  {
    id: "resend",
    name: "Email Service (Resend)",
    description: "Send transactional emails and notifications to users and customers.",
    envVar: "RESEND_API_KEY",
    docsUrl: "https://resend.com/docs",
  },
  {
    id: "hubspot",
    name: "CRM Integration (HubSpot)",
    description: "Sync contacts, track deals, and manage customer relationships.",
    envVar: "HUBSPOT_API_KEY",
    docsUrl: "https://developers.hubspot.com/docs",
  },
] as const;

const SOCIAL_PLATFORMS_INFO = [
  {
    platform: "twitter",
    display_name: "Twitter / X",
    icon: "twitter",
    config_keys: ["TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET"],
  },
  {
    platform: "linkedin",
    display_name: "LinkedIn",
    icon: "linkedin",
    config_keys: ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
  },
  {
    platform: "facebook",
    display_name: "Facebook",
    icon: "facebook",
    config_keys: ["FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"],
  },
  {
    platform: "instagram",
    display_name: "Instagram",
    icon: "instagram",
    config_keys: ["FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"],
  },
  {
    platform: "youtube",
    display_name: "YouTube",
    icon: "youtube",
    config_keys: ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
  },
  {
    platform: "tiktok",
    display_name: "TikTok",
    icon: "tiktok",
    config_keys: ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
  },
] as const;

const INBOUND_PROVIDER_SECRETS: Record<string, string> = {
  stripe: "STRIPE_WEBHOOK_SECRET",
  hubspot: "HUBSPOT_WEBHOOK_SECRET",
  resend: "RESEND_WEBHOOK_SECRET",
  github: "GITHUB_WEBHOOK_SECRET",
  slack: "SLACK_WEBHOOK_SECRET",
  shopify: "SHOPIFY_WEBHOOK_SECRET",
};

const INBOUND_SIGNATURE_HEADERS: Record<string, string> = {
  stripe: "Stripe-Signature",
  hubspot: "X-HubSpot-Signature-v3",
  github: "X-Hub-Signature-256",
  slack: "X-Slack-Signature",
  shopify: "X-Shopify-Hmac-SHA256",
};

function hasConfigValue(value: string | undefined): boolean {
  return Boolean(value?.trim());
}

function buildBuiltInToolStatus(env: Env) {
  return BUILT_IN_TOOLS_INFO.map((tool) => {
    const configured =
      tool.id === "tavily"
        ? hasConfigValue(env.TAVILY_API_KEY)
        : hasConfigValue(env.FIRECRAWL_API_KEY);

    return {
      id: tool.id,
      name: tool.name,
      description: tool.description,
      is_built_in: true,
      configured,
      status: configured
        ? "Configured server-side and ready for automatic use"
        : "Bundled in the app, but inactive until its API key is configured",
    };
  });
}

function buildConfigurableToolStatus(env: Env) {
  return CONFIGURABLE_TOOLS_INFO.map((tool) => ({
    id: tool.id,
    name: tool.name,
    description: tool.description,
    configured: hasConfigValue(env[tool.envVar]),
    env_var: tool.envVar,
    docs_url: tool.docsUrl,
    is_built_in: false,
  }));
}

function buildSchedulerReadiness(env: Env) {
  const schedulerSecretConfigured = hasConfigValue(env.SCHEDULER_SECRET);

  return {
    configuration_ready: schedulerSecretConfigured,
    worker_schedule_tick_enabled: true,
    secure_endpoints_enabled: true,
    deployment_required: true,
    status: schedulerSecretConfigured
      ? "App is ready to be deployed for scheduled jobs"
      : "Scheduled jobs need one more configuration step",
    message: schedulerSecretConfigured
      ? "Scheduler authentication is configured and the worker can execute saved report schedules. You still need always-on API and worker services plus an external scheduler for unattended runs."
      : "Add SCHEDULER_SECRET in the server environment to secure scheduled endpoints. The worker-side schedule tick is already wired, but unattended runs still require always-on deployment.",
  };
}

function buildMcpStatusResponse(env: Env) {
  return {
    built_in_tools: buildBuiltInToolStatus(env),
    configurable_tools: buildConfigurableToolStatus(env),
    scheduler_readiness: buildSchedulerReadiness(env),
  };
}

function buildErrorResponse(
  request: Request,
  env: Env,
  status: number,
  body: Record<string, unknown>,
  route: "blocked" | "native" = "native",
): Response {
  const response = Response.json(body, { status });
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  response.headers.set("x-pikar-public-route", route);
  return response;
}

function isTrustedEdgeRequest(request: Request, env: Env): boolean {
  const expected = env.INTERNAL_PROXY_TOKEN?.trim();
  if (!expected) {
    return false;
  }

  return request.headers.get("x-pikar-edge-token") === expected;
}

function normalizeOrigin(origin: string | undefined, label: string): string {
  const value = origin?.trim();
  if (!value) {
    throw new Error(`${label} is required.`);
  }

  try {
    const url = new URL(value);
    return url.origin;
  } catch {
    throw new Error(`${label} must be a valid absolute URL.`);
  }
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

function buildLiveResponse() {
  return {
    status: "ok",
    version: "1",
    service: "live",
    latency_ms: 0,
    details: {
      served_by: "cloudflare-public-api",
      layer: "public-origin",
    },
    checked_at: new Date().toISOString(),
  };
}

function buildStartupResponse(env: Env) {
  const fallbackOrigin = normalizeOrigin(
    env.FALLBACK_BACKEND_ORIGIN,
    "FALLBACK_BACKEND_ORIGIN",
  );

  return {
    status: "ready",
    checks: {
      cloudflare_public_api: "ok",
      fallback_origin: fallbackOrigin,
    },
  };
}

function jsonWithCors(data: unknown, request: Request, env: Env): Response {
  const response = Response.json(data);
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  response.headers.set("x-pikar-public-route", "native");
  return response;
}

function requireEdgeAccess(request: Request, env: Env): Response | null {
  if (isTrustedEdgeRequest(request, env)) {
    return null;
  }

  return buildErrorResponse(
    request,
    env,
    403,
    {
      ok: false,
      error: "This route is only available through the main API entrypoint.",
    },
    "blocked",
  );
}

function getSupabaseRequestContext(request: Request, env: Env) {
  const supabaseUrl = normalizeOrigin(env.SUPABASE_URL, "SUPABASE_URL");
  const anonKey = env.SUPABASE_ANON_KEY?.trim();
  if (!anonKey) {
    throw new Error("SUPABASE_ANON_KEY is required.");
  }

  const authorization = request.headers.get("authorization")?.trim();
  if (!authorization?.startsWith("Bearer ")) {
    return null;
  }

  return {
    supabaseUrl,
    headers: {
      apikey: anonKey,
      Authorization: authorization,
      Accept: "application/json",
    },
  };
}

async function fetchSupabaseRows<T>(request: Request, env: Env, path: string): Promise<T> {
  const context = getSupabaseRequestContext(request, env);
  if (!context) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "GET",
    headers: context.headers,
  });

  if (response.status === 401 || response.status === 403) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  if (!response.ok) {
    throw new Error(`Supabase request failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function fetchSupabaseUser(
  request: Request,
  env: Env,
): Promise<{
  id?: string | null;
  email?: string | null;
  identities?: Array<{
    provider?: string | null;
    identity_data?: {
      email?: string | null;
    } | null;
  }> | null;
}> {
  const context = getSupabaseRequestContext(request, env);
  if (!context) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const response = await fetch(`${context.supabaseUrl}/auth/v1/user`, {
    method: "GET",
    headers: context.headers,
  });

  if (response.status === 401 || response.status === 403) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  if (!response.ok) {
    throw new Error(`Supabase auth user request failed with ${response.status}.`);
  }

  return (await response.json()) as {
    id?: string | null;
    email?: string | null;
    identities?: Array<{
      provider?: string | null;
      identity_data?: {
        email?: string | null;
      } | null;
    }> | null;
  };
}

function getSupabaseAdminContext(env: Env) {
  const supabaseUrl = normalizeOrigin(env.SUPABASE_URL, "SUPABASE_URL");
  const serviceRoleKey = env.SUPABASE_SERVICE_ROLE_KEY?.trim();
  if (!serviceRoleKey) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is required.");
  }

  return {
    supabaseUrl,
    headers: {
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    },
  };
}

async function fetchSupabaseAdminRows<T>(env: Env, path: string): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "GET",
    headers: context.headers,
  });

  if (!response.ok) {
    throw new Error(`Supabase admin request failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function insertSupabaseAdminRow<T>(
  env: Env,
  path: string,
  payload: Record<string, unknown>,
): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "return=representation");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin insert failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function upsertSupabaseAdminRow<T>(
  env: Env,
  path: string,
  payload: Record<string, unknown>,
): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "resolution=ignore-duplicates,return=representation");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin upsert failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

function constantTimeEqual(left: string, right: string): boolean {
  if (left.length !== right.length) {
    return false;
  }

  let diff = 0;
  for (let index = 0; index < left.length; index += 1) {
    diff |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }

  return diff === 0;
}

async function signHmacSha256Hex(secret: string, payload: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign("HMAC", key, payload);
  return Array.from(new Uint8Array(signature))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function signHmacSha256Base64(secret: string, payload: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign("HMAC", key, payload);
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

async function signRawHmacSha256Base64(keyBytes: Uint8Array, payload: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign("HMAC", key, payload);
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

async function sha256Hex(payload: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", payload);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function stableJsonStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJsonStringify(item)).join(",")}]`;
  }

  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => `${JSON.stringify(key)}:${stableJsonStringify(item)}`);

  return `{${entries.join(",")}}`;
}

function extractLinkedInEventType(payload: Record<string, unknown>): string {
  const eventType = payload.eventType;
  if (typeof eventType === "string" && eventType.trim()) {
    return eventType;
  }

  const fallback = payload.type;
  if (typeof fallback === "string" && fallback.trim()) {
    return fallback;
  }

  return "unknown";
}

function extractLinkedInOrganizationId(payload: Record<string, unknown>): string | null {
  const data = asRecord(payload.data);
  const nestedOrganization = data?.organization;
  if (typeof nestedOrganization === "string" && nestedOrganization.trim()) {
    return nestedOrganization;
  }

  const organizationId = payload.organizationId;
  if (typeof organizationId === "string" && organizationId.trim()) {
    return organizationId;
  }

  return null;
}

function extractLinkedInActorUrn(payload: Record<string, unknown>): string | null {
  const data = asRecord(payload.data);
  const nestedActor = data?.actor;
  if (typeof nestedActor === "string" && nestedActor.trim()) {
    return nestedActor;
  }

  const actor = payload.actor;
  if (typeof actor === "string" && actor.trim()) {
    return actor;
  }

  return null;
}

async function resolveLinkedInUserId(
  env: Env,
  actorUrn: string | null,
): Promise<string | null> {
  if (!actorUrn) {
    return null;
  }

  const params = new URLSearchParams({
    select: "user_id",
    platform: "eq.linkedin",
    platform_user_id: `eq.${actorUrn}`,
    status: "eq.active",
    limit: "1",
  });

  const rows = await fetchSupabaseAdminRows<Array<{ user_id?: string | null }>>(
    env,
    `/rest/v1/connected_accounts?${params.toString()}`,
  );

  return rows[0]?.user_id ?? null;
}

async function storeLinkedInWebhookEvent(
  env: Env,
  payload: Record<string, unknown>,
): Promise<{ id?: string | null }> {
  const actorUrn = extractLinkedInActorUrn(payload);
  const userId = await resolveLinkedInUserId(env, actorUrn);

  const rows = await insertSupabaseAdminRow<Array<{ id?: string | null }>>(
    env,
    "/rest/v1/social_webhook_events?select=id",
    {
      platform: "linkedin",
      event_type: extractLinkedInEventType(payload),
      payload,
      linkedin_org_id: extractLinkedInOrganizationId(payload),
      user_id: userId,
      status: "pending",
      received_at: new Date().toISOString(),
    },
  );

  return rows[0] ?? {};
}

function getInboundSecretEnvVar(provider: string, env: Env): string | null {
  const mapped = INBOUND_PROVIDER_SECRETS[provider];
  if (mapped) {
    return mapped;
  }

  const dynamic = `${provider.toUpperCase().replace(/[^A-Z0-9]+/g, "_")}_WEBHOOK_SECRET`;
  if (hasConfigValue(env[dynamic])) {
    return dynamic;
  }

  return null;
}

function verifyInboundSignature(
  body: Uint8Array,
  signatureHeader: string,
  expectedHex: string,
): boolean {
  void body;
  if (!signatureHeader) {
    return false;
  }

  const normalized = signatureHeader.startsWith("sha256=")
    ? signatureHeader.slice(7)
    : signatureHeader;

  return constantTimeEqual(normalized, expectedHex);
}

function decodeBase64(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function canonicalRequestUrl(request: Request): string {
  const url = new URL(request.url);
  const proto = request.headers.get("x-forwarded-proto")?.trim() || url.protocol.replace(":", "");
  const host = request.headers.get("x-forwarded-host")?.trim() || url.host;
  return `${proto}://${host}${url.pathname}${url.search}`;
}

function isFreshUnixTimestamp(
  value: string,
  toleranceSeconds: number,
  multiplier: number,
): boolean {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return false;
  }

  const now = Date.now() / 1000;
  const timestamp = numeric / multiplier;
  return Math.abs(now - timestamp) <= toleranceSeconds;
}

async function verifyHubSpotWebhook(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<boolean> {
  const secret = env.HUBSPOT_CLIENT_SECRET?.trim() || env.HUBSPOT_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const timestamp = request.headers.get("X-HubSpot-Request-Timestamp")?.trim() ?? "";
  const signature = request.headers.get("X-HubSpot-Signature-v3")?.trim() ?? "";
  if (!timestamp || !signature || !isFreshUnixTimestamp(timestamp, 300, 1000)) {
    return false;
  }

  const source = `${request.method}${canonicalRequestUrl(request)}${new TextDecoder().decode(rawBody)}${timestamp}`;
  const expected = await signHmacSha256Base64(secret, new TextEncoder().encode(source));
  return constantTimeEqual(expected, signature);
}

async function verifyResendWebhook(request: Request, env: Env, rawBody: Uint8Array): Promise<boolean> {
  const secret = env.RESEND_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const svixId = request.headers.get("svix-id")?.trim() ?? "";
  const svixTimestamp = request.headers.get("svix-timestamp")?.trim() ?? "";
  const svixSignature = request.headers.get("svix-signature")?.trim() ?? "";
  if (!svixId || !svixTimestamp || !svixSignature || !isFreshUnixTimestamp(svixTimestamp, 300, 1)) {
    return false;
  }

  const encodedSecret = secret.startsWith("whsec_") ? secret.slice("whsec_".length) : secret;
  const signedContent = new TextEncoder().encode(`${svixId}.${svixTimestamp}.`);
  const payload = new Uint8Array(signedContent.length + rawBody.length);
  payload.set(signedContent);
  payload.set(rawBody, signedContent.length);
  const expected = await signRawHmacSha256Base64(decodeBase64(encodedSecret), payload);

  return svixSignature
    .split(/\s+/)
    .map((value) => value.replace(/^v1,/, ""))
    .some((candidate) => constantTimeEqual(expected, candidate));
}

async function verifyShopifyWebhook(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<boolean> {
  const secret = env.SHOPIFY_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const provided = request.headers.get("X-Shopify-Hmac-SHA256")?.trim() ?? "";
  if (!provided) {
    return false;
  }

  const expected = await signHmacSha256Base64(secret, rawBody);
  return constantTimeEqual(expected, provided);
}

async function verifyStripeWebhook(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<boolean> {
  const secret = env.STRIPE_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const header = request.headers.get("Stripe-Signature")?.trim() ?? "";
  if (!header) {
    return false;
  }

  let timestamp = "";
  const signatures: string[] = [];
  for (const part of header.split(",")) {
    const [key, value] = part.split("=", 2);
    if (!key || !value) {
      continue;
    }

    if (key === "t") {
      timestamp = value;
    } else if (key === "v1") {
      signatures.push(value);
    }
  }

  if (!timestamp || signatures.length === 0 || !isFreshUnixTimestamp(timestamp, 300, 1)) {
    return false;
  }

  const signedPayload = new TextEncoder().encode(
    `${timestamp}.${new TextDecoder().decode(rawBody)}`,
  );
  const expected = await signHmacSha256Hex(secret, signedPayload);
  return signatures.some((candidate) => constantTimeEqual(expected, candidate));
}

async function extractInboundEventId(payload: Record<string, unknown>): Promise<string> {
  const eventId = payload.id;
  if (
    typeof eventId === "string" ||
    typeof eventId === "number" ||
    typeof eventId === "bigint"
  ) {
    return String(eventId);
  }

  const serialized = stableJsonStringify(payload);
  return (await sha256Hex(new TextEncoder().encode(serialized))).slice(0, 32);
}

function extractInboundEventType(payload: Record<string, unknown>): string {
  const type = payload.type;
  if (typeof type === "string" && type.trim()) {
    return type;
  }

  const fallback = payload.event;
  if (typeof fallback === "string" && fallback.trim()) {
    return fallback;
  }

  return "unknown";
}

async function storeGenericInboundWebhook(
  env: Env,
  provider: string,
  payload: Record<string, unknown>,
): Promise<{ status: "received" | "duplicate"; event_id: string }> {
  const eventId = await extractInboundEventId(payload);
  const eventType = extractInboundEventType(payload);
  const rows = await upsertSupabaseAdminRow<Array<{ id?: string | null }>>(
    env,
    "/rest/v1/webhook_events?on_conflict=provider,event_id&select=id",
    {
      provider,
      event_id: eventId,
      event_type: eventType,
      payload,
      status: "pending",
    },
  );

  const rowId = rows[0]?.id;
  if (!rowId) {
    return {
      status: "duplicate",
      event_id: eventId,
    };
  }

  await insertSupabaseAdminRow<Array<{ id?: string | null }>>(
    env,
    "/rest/v1/ai_jobs?select=id",
    {
      job_type: "webhook_inbound_process",
      priority: 8,
      input_data: {
        webhook_event_id: rowId,
        provider,
        event_type: eventType,
      },
    },
  );

  return {
    status: "received",
    event_id: eventId,
  };
}

async function buildUserConfigsResponse(request: Request, env: Env) {
  const rows = await fetchSupabaseRows<Array<Record<string, unknown>>>(
    request,
    env,
    "/rest/v1/user_configurations?select=config_key,config_value,updated_at",
  );

  return { configs: rows };
}

async function buildSessionConfigResponse(request: Request, env: Env) {
  try {
    const rows = await fetchSupabaseRows<Array<{ config_value?: string | null }>>(
      request,
      env,
      "/rest/v1/user_configurations?select=config_value&config_key=eq.sessions&limit=1",
    );

    if (!rows.length || !rows[0]?.config_value) {
      return DEFAULT_SESSION_CONFIG;
    }

    const parsed = JSON.parse(rows[0].config_value) as Record<string, unknown>;
    return {
      ...DEFAULT_SESSION_CONFIG,
      ...parsed,
    };
  } catch (error) {
    if (error instanceof Response) {
      throw error;
    }

    return DEFAULT_SESSION_CONFIG;
  }
}

async function buildSocialStatusResponse(request: Request, env: Env) {
  const rows = await fetchSupabaseRows<
    Array<{
      platform: string;
      platform_username?: string | null;
      status?: string | null;
      connected_at?: string | null;
    }>
  >(
    request,
    env,
    "/rest/v1/connected_accounts?select=platform,platform_username,status,connected_at",
  );

  const connectionMap = new Map(rows.map((row) => [row.platform, row]));

  return {
    platforms: SOCIAL_PLATFORMS_INFO.map((platform) => {
      const connection = connectionMap.get(platform.platform);

      return {
        platform: platform.platform,
        display_name: platform.display_name,
        icon: platform.icon,
        connected: connection?.status === "active",
        username: connection?.platform_username ?? null,
        connected_at: connection?.connected_at ?? null,
        requires_config: platform.config_keys.some((key) => !hasConfigValue(env[key])),
        config_keys: [...platform.config_keys],
      };
    }),
  };
}

async function buildGoogleWorkspaceStatusResponse(request: Request, env: Env) {
  const user = await fetchSupabaseUser(request, env);
  const identities = user.identities ?? [];
  const googleIdentity = identities.find((identity) => identity.provider === "google");

  if (!googleIdentity) {
    return {
      connected: false,
      provider: null,
      message: "Sign in with Google to enable Google Workspace features",
    };
  }

  return {
    connected: true,
    email: user.email ?? googleIdentity.identity_data?.email ?? "",
    provider: "google",
    features: [
      "Google Docs - Create and edit documents",
      "Google Sheets - Create spreadsheets and track data",
      "Google Forms - Create surveys and feedback forms",
      "Google Calendar - Schedule events and meetings",
      "Gmail - Send emails on your behalf",
    ],
    message: "Google Workspace is connected and ready to use",
  };
}

async function buildWebhookEventsResponse(request: Request, env: Env, url: URL) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const limitRaw = Number(url.searchParams.get("limit") ?? "50");
  const limit = Number.isFinite(limitRaw)
    ? Math.max(1, Math.min(200, Math.trunc(limitRaw)))
    : 50;

  const params = new URLSearchParams({
    select: "id,platform,event_type,status,received_at,processed_at",
    user_id: `eq.${user.id}`,
    order: "received_at.desc",
    limit: String(limit),
  });

  const platform = url.searchParams.get("platform")?.trim();
  if (platform) {
    params.set("platform", `eq.${platform}`);
  }

  const status = url.searchParams.get("status")?.trim();
  if (status) {
    params.set("status", `eq.${status}`);
  }

  const events = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/social_webhook_events?${params.toString()}`,
  );

  return { events };
}

async function proxyVerifiedWebhook(request: Request, env: Env): Promise<Response> {
  return proxyFallback(request, env, "native-verified-proxy");
}

async function maybeHandleNativeRoute(request: Request, env: Env, url: URL): Promise<Response | null> {
  const corsHeaders = buildCorsHeaders(request, env);

  if (url.pathname === "/health/live") {
    const response = Response.json(buildLiveResponse());
    corsHeaders.forEach((value, key) => response.headers.set(key, value));
    response.headers.set("x-pikar-public-route", "native");
    return response;
  }

  if (url.pathname === "/health/startup") {
    const response = Response.json(buildStartupResponse(env));
    corsHeaders.forEach((value, key) => response.headers.set(key, value));
    response.headers.set("x-pikar-public-route", "native");
    return response;
  }

  if (url.pathname === "/webhooks/linkedin" && request.method === "GET") {
    const challengeCode = url.searchParams.get("challengeCode")?.trim();
    if (!challengeCode) {
      return buildErrorResponse(request, env, 400, {
        detail: "Missing challengeCode query parameter",
      });
    }

    const clientSecret = env.LINKEDIN_CLIENT_SECRET?.trim();
    if (!clientSecret) {
      return buildErrorResponse(request, env, 500, {
        detail: "LinkedIn client secret not configured",
      });
    }

    return jsonWithCors(
      {
        challengeCode,
        challengeResponse: await signHmacSha256Hex(
          clientSecret,
          new TextEncoder().encode(challengeCode),
        ),
      },
      request,
      env,
    );
  }

  if (url.pathname === "/webhooks/linkedin" && request.method === "POST") {
    const webhookSecret = env.LINKEDIN_WEBHOOK_SECRET?.trim();
    if (!webhookSecret) {
      return buildErrorResponse(request, env, 500, {
        detail: "LinkedIn webhook secret not configured",
      });
    }

    const providedSignature = request.headers.get("X-LinkedIn-Signature")?.trim();
    if (!providedSignature) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    const rawBody = new Uint8Array(await request.arrayBuffer());
    const expectedSignature = await signHmacSha256Hex(webhookSecret, rawBody);
    if (!constantTimeEqual(expectedSignature, providedSignature)) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(new TextDecoder().decode(rawBody));
    } catch {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    const payload = asRecord(parsed);
    if (!payload) {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    const stored = await storeLinkedInWebhookEvent(env, payload);
    return jsonWithCors(
      {
        status: "received",
        event_id: stored.id ?? null,
      },
      request,
      env,
    );
  }

  if (url.pathname === "/webhooks/hubspot" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.HUBSPOT_CLIENT_SECRET?.trim() && !env.HUBSPOT_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyHubSpotWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  if (url.pathname === "/webhooks/resend" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.RESEND_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyResendWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 401, {
        detail: "Invalid webhook signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  if (url.pathname === "/webhooks/shopify" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.SHOPIFY_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyShopifyWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  if (url.pathname === "/webhooks/stripe" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.STRIPE_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyStripeWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  const inboundMatch = /^\/webhooks\/inbound\/([^/]+)$/.exec(url.pathname);
  if (inboundMatch && request.method === "POST") {
    const provider = decodeURIComponent(inboundMatch[1]).trim().toLowerCase();
    const envVar = getInboundSecretEnvVar(provider, env);
    if (!envVar) {
      return buildErrorResponse(request, env, 404, {
        detail: `Unknown provider: ${provider}`,
      });
    }

    const secret = env[envVar]?.trim();
    if (!secret) {
      return buildErrorResponse(request, env, 500, {
        detail: "Webhook secret not configured",
      });
    }

    const signatureHeaderName =
      INBOUND_SIGNATURE_HEADERS[provider] ?? `X-${provider.replace(/(^.|[-_].)/g, (part) => part.replace(/[-_]/g, "").toUpperCase())}-Signature`;
    const providedSignature = request.headers.get(signatureHeaderName)?.trim() ?? "";
    const rawBody = new Uint8Array(await request.arrayBuffer());
    const expectedSignature = await signHmacSha256Hex(secret, rawBody);
    if (!verifyInboundSignature(rawBody, providedSignature, expectedSignature)) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(new TextDecoder().decode(rawBody));
    } catch {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    const payload = asRecord(parsed);
    if (!payload) {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    return jsonWithCors(await storeGenericInboundWebhook(env, provider, payload), request, env);
  }

  if (url.pathname === "/webhooks/events" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildWebhookEventsResponse(request, env, url), request, env);
  }

  if (url.pathname === "/configuration/mcp-status") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(buildMcpStatusResponse(env), request, env);
  }

  if (url.pathname === "/configuration/user-configs") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildUserConfigsResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/session-config") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSessionConfigResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/social-status") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSocialStatusResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/google-workspace-status") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildGoogleWorkspaceStatusResponse(request, env), request, env);
  }

  if (url.pathname === "/health/public") {
    return jsonWithCors(
      {
        ok: true,
        service: "pikar-public-api",
        mode: "phase-2",
        checked_at: new Date().toISOString(),
      },
      request,
      env,
    );
  }

  return null;
}

async function proxyFallback(
  request: Request,
  env: Env,
  route: "fallback" | "native-verified-proxy" = "fallback",
): Promise<Response> {
  const incoming = new URL(request.url);
  const origin = normalizeOrigin(env.FALLBACK_BACKEND_ORIGIN, "FALLBACK_BACKEND_ORIGIN");
  const target = new URL(`${origin}${incoming.pathname}${incoming.search}`);
  const headers = new Headers(request.headers);

  if (!headers.has("x-forwarded-host")) {
    headers.set("x-forwarded-host", incoming.host);
  }
  if (!headers.has("x-forwarded-proto")) {
    headers.set("x-forwarded-proto", incoming.protocol.replace(":", ""));
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
  outgoing.set("x-pikar-public-route", route);
  outgoing.set("x-pikar-public-target", target.origin);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: outgoing,
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return handlePreflight(request, env);
    }

    try {
      return (await maybeHandleNativeRoute(request, env, url)) ?? (await proxyFallback(request, env));
    } catch (error) {
      if (error instanceof Response) {
        const headers = new Headers(error.headers);
        const corsHeaders = buildCorsHeaders(request, env);
        corsHeaders.forEach((value, key) => headers.set(key, value));
        headers.set("x-pikar-public-route", "native");
        return new Response(error.body, {
          status: error.status,
          statusText: error.statusText,
          headers,
        });
      }

      return Response.json(
        {
          ok: false,
          error: error instanceof Error ? error.message : "Unknown public API error",
        },
        { status: 500 },
      );
    }
  },
};
