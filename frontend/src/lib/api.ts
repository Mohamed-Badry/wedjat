/**
 * Centralized API client for the Watchdog backend.
 * All API URL resolution, fetch wrappers, and error handling live here.
 */
import { env } from '$env/dynamic/public';

/**
 * Resolve the backend API base URL.
 * - Browser: uses PUBLIC_API_URL env var, falls back to localhost.
 * - SSR: always targets the Docker service name.
 */
export function getApiUrl(): string {
  if (env.PUBLIC_API_URL) {
    return env.PUBLIC_API_URL;
  }
  if (typeof window !== 'undefined') {
    return 'http://127.0.0.1:8000';
  }
  return 'http://backend:8000';
}

export function getWsUrl(): string {
  const url = getApiUrl();
  return url.replace(/^http/, 'ws');
}

/**
 * Typed fetch wrapper for the Watchdog REST API.
 * Handles URL resolution, JSON parsing, and error extraction.
 *
 * @param path  - API path (e.g. `/api/satellites`)
 * @param init  - Optional RequestInit (headers, method, body, etc.)
 * @param fetchFn - Optional fetch function override (use SvelteKit's `fetch` in loaders)
 * @returns Parsed JSON response
 * @throws Error with backend detail message or HTTP status
 */
export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit,
  fetchFn: typeof fetch = fetch,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (env.PUBLIC_MASTER_API_KEY) {
    headers.set('X-API-Key', env.PUBLIC_MASTER_API_KEY);
  }
  const res = await fetchFn(`${getApiUrl()}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `API error: HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/**
 * Fetch the satellite list — the most common loader pattern.
 * Returns an empty array on failure so pages always have a safe default.
 */
export async function fetchSatellites(
  fetchFn: typeof fetch = fetch,
): Promise<{ satellites: { name: string; norad_id: number }[] }> {
  try {
    return await apiFetch('/api/satellites', undefined, fetchFn);
  } catch {
    return { satellites: [] };
  }
}
