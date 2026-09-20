import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ACCESS_COOKIE = "sentinel_admin_access";
const REFRESH_COOKIE = "sentinel_admin_refresh";
const ADMIN_ROLES = new Set([
  "SUPERVISOR",
  "MENTAL_HEALTH_PROFESSIONAL",
  "ADMIN",
  "SUPER_ADMIN",
]);
const REQUEST_TIMEOUT_MS = 20_000;

type BackendTokens = {
  access_token: string;
  refresh_token: string;
};

type BackendUser = {
  id: string;
  email: string;
  full_name?: string | null;
  name?: string | null;
  role: string;
  is_active?: boolean;
  onboarding_complete?: boolean;
  mfa_enabled?: boolean;
  created_at?: string;
};

function backendOrigin(): string {
  const raw = process.env.BACKEND_API_URL?.trim() || "http://127.0.0.1:8000";
  const parsed = new URL(raw);
  const loopback = parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost" || parsed.hostname === "[::1]";
  if (!loopback && parsed.protocol !== "https:") {
    throw new Error("BACKEND_API_URL must use HTTPS outside local development");
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error("BACKEND_API_URL must be a credential-free API origin");
  }
  return parsed.origin;
}

async function backendFetch(
  pathname: string,
  init: RequestInit = {},
  accessToken?: string,
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body != null) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(`${backendOrigin()}${pathname}`, {
    ...init,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
}

function cookieOptions(request: NextRequest, maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "strict" as const,
    secure: request.nextUrl.protocol === "https:",
    path: "/",
    maxAge,
  };
}

async function saveTokens(request: NextRequest, tokens: BackendTokens): Promise<void> {
  const store = await cookies();
  store.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(request, 30 * 60));
  store.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(request, 7 * 24 * 60 * 60));
}

async function clearTokens(): Promise<void> {
  const store = await cookies();
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}

async function refreshAccess(request: NextRequest): Promise<string | null> {
  const store = await cookies();
  const refreshToken = store.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) return null;

  const response = await backendFetch("/api/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    await clearTokens();
    return null;
  }
  const tokens = (await response.json()) as BackendTokens;
  await saveTokens(request, tokens);
  return tokens.access_token;
}

async function authorizedFetch(
  request: NextRequest,
  pathname: string,
  init: RequestInit = {},
): Promise<Response | null> {
  const store = await cookies();
  let accessToken = store.get(ACCESS_COOKIE)?.value;
  if (!accessToken) return null;

  let response = await backendFetch(pathname, init, accessToken);
  if (response.status !== 401) return response;

  accessToken = await refreshAccess(request) ?? undefined;
  if (!accessToken) return response;
  response = await backendFetch(pathname, init, accessToken);
  return response;
}

function safeUser(user: BackendUser) {
  const role = user.role === "PERSONNEL" ? "USER" : user.role;
  return {
    id: user.id,
    email: user.email,
    name: user.full_name ?? user.name ?? null,
    serviceNumber: null,
    unit: null,
    rank: null,
    role,
    status: user.is_active === false ? "SUSPENDED" : "ACTIVE",
    firstLogin: user.onboarding_complete === false,
    onboardingComplete: user.onboarding_complete !== false,
    emailVerified: true,
    mfaEnabled: user.mfa_enabled === true,
    lastLoginAt: null,
    createdAt: user.created_at ?? new Date(0).toISOString(),
  };
}

async function errorResponse(response: Response): Promise<NextResponse> {
  let error = `Cloud API request failed (${response.status})`;
  let code: string | undefined;
  try {
    const payload = await response.json() as {
      detail?: string | { message?: string; code?: string };
      error?: string;
      code?: string;
    };
    if (typeof payload.detail === "string") error = payload.detail;
    else if (payload.detail?.message) error = payload.detail.message;
    else if (payload.error) error = payload.error;
    code = payload.code ?? (typeof payload.detail === "object" ? payload.detail.code : undefined);
  } catch {
    // Preserve the generic status message for non-JSON upstream failures.
  }
  return NextResponse.json({ error, ...(code ? { code } : {}) }, { status: response.status });
}

async function login(request: NextRequest): Promise<NextResponse> {
  let body: { email?: string; password?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
  if (!body.email || !body.password) {
    return NextResponse.json({ error: "Email and password are required" }, { status: 422 });
  }

  const response = await backendFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: body.email, password: body.password }),
  });
  if (!response.ok) return errorResponse(response);

  const tokens = (await response.json()) as BackendTokens;
  const profileResponse = await backendFetch("/api/users/me", { method: "GET" }, tokens.access_token);
  if (!profileResponse.ok) return errorResponse(profileResponse);
  const profile = (await profileResponse.json()) as BackendUser;
  if (!ADMIN_ROLES.has(profile.role)) {
    return NextResponse.json(
      { error: "Personnel accounts must use the CRPF MHS mobile application", code: "ADMIN_ONLY" },
      { status: 403 },
    );
  }

  await saveTokens(request, tokens);
  return NextResponse.json({ user: safeUser(profile) });
}

async function me(request: NextRequest): Promise<NextResponse> {
  const response = await authorizedFetch(request, "/api/users/me", { method: "GET" });
  if (!response) return NextResponse.json({ user: null });
  if (response.status === 401) {
    await clearTokens();
    return NextResponse.json({ user: null });
  }
  if (!response.ok) return errorResponse(response);
  const profile = (await response.json()) as BackendUser;
  if (!ADMIN_ROLES.has(profile.role)) {
    await clearTokens();
    return NextResponse.json({ user: null });
  }
  return NextResponse.json({ user: safeUser(profile) });
}

async function logout(request: NextRequest): Promise<NextResponse> {
  const response = await authorizedFetch(request, "/api/auth/logout", { method: "POST" });
  await clearTokens();
  if (response && !response.ok && response.status !== 401) return errorResponse(response);
  return NextResponse.json({ ok: true });
}

async function proxyAdmin(request: NextRequest, segments: string[]): Promise<NextResponse> {
  if (segments[0] !== "admin") {
    return NextResponse.json({ error: "Unsupported cloud API route" }, { status: 404 });
  }
  const upstreamPath = `/api/${segments.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const body = request.method === "GET" || request.method === "HEAD"
    ? undefined
    : await request.text();
  const response = await authorizedFetch(request, upstreamPath, {
    method: request.method,
    body: body || undefined,
  });
  if (!response) {
    return NextResponse.json({ error: "Authentication required", code: "UNAUTHENTICATED" }, { status: 401 });
  }
  if (!response.ok) return errorResponse(response);
  if (response.status === 204) return new NextResponse(null, { status: 204 });
  return new NextResponse(await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}

async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  try {
    const { path } = await context.params;
    const route = path.join("/");
    if (route === "auth/login" && request.method === "POST") return login(request);
    if (route === "auth/me" && request.method === "GET") return me(request);
    if (route === "auth/logout" && request.method === "POST") return logout(request);
    return proxyAdmin(request, path);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Cloud API unavailable";
    return NextResponse.json({ error: message, code: "CLOUD_UNAVAILABLE" }, { status: 503 });
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const DELETE = handle;
