import type { CurrentUser, Role } from "./auth";
import { getApiError } from "./errors";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "include" });
  if (!response.ok) {
    throw new Error(await getApiError(response));
  }
  return response.json();
}

export async function listUsers(): Promise<CurrentUser[]> {
  const result = await request<{ items: CurrentUser[] }>("/api/admin/users");
  return result.items;
}

export interface NewUser {
  username: string;
  password: string;
  display_name: string | null;
  email: string | null;
  role: Role;
}

export function createUser(payload: NewUser, csrfToken: string): Promise<CurrentUser> {
  return request("/api/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function setUserActive(id: number, isActive: boolean, csrfToken: string): Promise<CurrentUser> {
  return request(`/api/admin/users/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify({ is_active: isActive }),
  });
}

export function deleteUser(id: number, csrfToken: string): Promise<{ message: string }> {
  return request(`/api/admin/users/${id}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function updateUserPassword(id: number, password: string, csrfToken: string): Promise<{ message: string }> {
  return request(`/api/admin/users/${id}/password`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify({ password }),
  });
}
