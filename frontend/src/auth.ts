import { reactive } from "vue";
import { authApi } from "./api/auth";
import { setAccessToken } from "./api/client";
import type { CurrentUser } from "./types";
export const authState = reactive<{ user: CurrentUser | null; loading: boolean }>({ user: null, loading: false });
export async function login(username: string, password: string): Promise<void> { authState.loading = true; try { const token = await authApi.login(username, password); setAccessToken(token.access_token); authState.user = token.user; } finally { authState.loading = false; } }
export async function logout(): Promise<void> { try { if (authState.user) await authApi.logout(); } finally { setAccessToken(""); authState.user = null; } }
export function hasPermission(code: string): boolean { return Boolean(authState.user?.permission_codes.includes(code)); }
window.addEventListener("auth:unauthorized", () => { setAccessToken(""); authState.user = null; });
