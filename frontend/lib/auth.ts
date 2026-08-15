const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export type AuthUser = { id: string; email: string; display_name?: string | null; role: "ADMIN" | "USER"; status: string };
export type AuthTokens = { access_token: string; refresh_token: string; expires_in: number };

export async function login(email: string, password: string): Promise<AuthTokens> {
  const response = await fetch(`${API_BASE}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail ?? "Unable to sign in");
  const tokens = await response.json() as AuthTokens;
  sessionStorage.setItem("nicheforge_access_token", tokens.access_token);
  return tokens;
}

export async function currentUser(): Promise<AuthUser> {
  const token = sessionStorage.getItem("nicheforge_access_token");
  const response = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token ?? ""}` } });
  if (!response.ok) throw new Error("Authentication expired");
  return response.json();
}

export function logout(): void { sessionStorage.removeItem("nicheforge_access_token"); }
