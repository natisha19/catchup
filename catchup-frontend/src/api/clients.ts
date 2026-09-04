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

export async function httpJson<T>(path: string, init?: RequestInit): Promise<T> {
  if (!apiConfig.baseUrl) {
    throw new ApiError("API base URL is not configured", 0);
  }
  const res = await fetch(`${apiConfig.baseUrl}${path}`, {
    headers: { Accept: "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    throw new ApiError(`Request failed: ${res.status}`, res.status);
  }
  if (res.status === 204 || res.status === 205) {
    return undefined as T;
  }
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
