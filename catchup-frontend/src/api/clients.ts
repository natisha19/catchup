/**
 * Single place where transport configuration lives.
 * The real HTTP API implementations will use this; nothing else in the app
 * may call fetch directly or hardcode URLs.
 */
export const apiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL as string | undefined,
  mode: (import.meta.env.VITE_API_MODE as "mock" | "http" | undefined) ?? "mock",
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let sessionToken: string | undefined;

export function setSessionToken(token: string | undefined): void {
  sessionToken = token;
}

export function getSessionToken(): string | undefined {
  return sessionToken;
}

/**
 * Mint a signed session from the backend and remember it. Identity is real but
 * demo-grade: the backend signs {user_id, iat, exp} with a server secret. Used
 * only in http mode; mock mode never calls this.
 */
export async function ensureSession(userId = "default-user"): Promise<boolean> {
  if (!apiConfig.baseUrl || apiConfig.mode !== "http") {
    return false;
  }
  try {
    const res = await fetch(`${apiConfig.baseUrl}/auth/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) return false;
    const body = (await res.json()) as { token: string };
    sessionToken = body.token;
    return true;
  } catch {
    sessionToken = undefined;
    return false;
  }
}

export async function httpJson<T>(path: string, init?: RequestInit): Promise<T> {
  if (!apiConfig.baseUrl) {
    throw new ApiError("API base URL is not configured", 0);
  }
  let res: Response;
  try {
    res = await fetch(`${apiConfig.baseUrl}${path}`, {
      headers: {
        Accept: "application/json",
        ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
        ...init?.headers,
      },
      ...init,
    });
  } catch {
    throw new ApiError(`Could not reach the API at ${apiConfig.baseUrl}`, 0);
  }
  if (!res.ok) {
    throw new ApiError(await errorMessage(res), res.status);
  }
  if (res.status === 204 || res.status === 205) {
    return undefined as T;
  }
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/**
 * Backend errors follow FastAPI's `{ "detail": string }` envelope. Prefer the
 * real detail when present; fall back to a status-based message otherwise.
 */
async function errorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }
  } catch {
    // Non-JSON error body — fall through to the generic message.
  }
  return `Request failed: ${res.status}`;
}
