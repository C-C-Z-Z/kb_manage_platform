const API_BASE = "/api/v1";
let accessToken = "";
export class ApiError extends Error { status: number; code: string; constructor(message: string, status = 500, code = "REQUEST_FAILED") { super(message); this.name = "ApiError"; this.status = status; this.code = code; } }
export function setAccessToken(token: string): void { accessToken = token; }
export function getAccessToken(): string { return accessToken; }
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body !== undefined) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", "Bearer " + accessToken);
  const response = await fetch(API_BASE + path, { ...init, headers });
  if (response.status === 401) window.dispatchEvent(new Event("auth:unauthorized"));
  if (!response.ok) { const payload = await response.json().catch(() => ({})); throw new ApiError(String(payload.message || payload.detail || response.statusText || "请求失败"), response.status, String(payload.code || "REQUEST_FAILED")); }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}
