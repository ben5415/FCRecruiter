import { getApiError } from "./errors";

export type Role = "manager" | "player" | "doctor" | "coach";

export interface CurrentUser {
  id: number;
  username: string;
  display_name: string | null;
  email: string | null;
  role: Role;
  is_active: boolean;
  tenant_id: number;
  tenant: {
    id: number;
    name: string;
    slug: string;
    club: { club_team_id: number; club_name: string | null };
  };
}

export interface AuthResponse {
  user: CurrentUser;
  csrf_token: string;
}

export async function getMe(): Promise<AuthResponse | null> {
  const response = await fetch("/api/auth/me", { credentials: "include" });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(await getApiError(response));
  return response.json();
}

export async function login(identifier: string, password: string): Promise<AuthResponse> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, password }),
  });
  if (!response.ok) throw new Error(await getApiError(response));
  return response.json();
}

export async function logout(csrfToken: string): Promise<void> {
  const response = await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRF-Token": csrfToken },
  });
  if (!response.ok) throw new Error(await getApiError(response));
}
