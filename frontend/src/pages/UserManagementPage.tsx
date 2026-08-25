import { useEffect, useState, type FormEvent } from "react";

import { createUser, listClubs, listUsers, setUserActive, setUserClub, type ClubOption } from "../api/admin";
import type { CurrentUser, Role } from "../api/auth";
import { useAuth } from "../auth/AuthContext";
import { ClubPicker } from "../components/ClubPicker";

export function UserManagementPage() {
  const { user: currentUser, csrfToken } = useAuth();
  const [users, setUsers] = useState<CurrentUser[]>([]);
  const [clubs, setClubs] = useState<ClubOption[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ username: "", password: "", display_name: "", email: "", role: "user" as Role, managed_club_team_id: 11 });
  const load = () => listUsers().then(setUsers).catch((e: Error) => setError(e.message));
  useEffect(() => { void load(); void listClubs().then(setClubs).catch((e: Error) => setError(e.message)); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      await createUser({ ...form, display_name: form.display_name || null, email: form.email || null }, csrfToken!);
      setForm({ username: "", password: "", display_name: "", email: "", role: "user", managed_club_team_id: 11 });
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not create user"); }
  }

  async function toggle(target: CurrentUser) {
    try {
      const updated = await setUserActive(target.id, !target.is_active, csrfToken!);
      setUsers((items) => items.map((item) => item.id === updated.id ? updated : item));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update user"); }
  }

  async function changeClub(target: CurrentUser, clubId: number) {
    try {
      const updated = await setUserClub(target.id, clubId, csrfToken!);
      setUsers((items) => items.map((item) => item.id === updated.id ? updated : item));
      if (target.id === currentUser?.id) window.location.reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update club"); }
  }

  return <main className="marketplace admin-page">
    <div className="marketplace__header"><div><p className="eyebrow">Administration</p><h1>Accounts</h1></div><p>Create accounts and control application access.</p></div>
    <form className="account-form" onSubmit={submit}>
      <label>Username<input required minLength={3} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></label>
      <label>Display name<input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} /></label>
      <label>Email<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
      <label>Password<input required minLength={8} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
      <label>Role<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}><option value="user">User</option><option value="admin">Admin</option></select></label>
      <label>Club<ClubPicker required label="Club for new account" clubs={clubs} value={form.managed_club_team_id} onChange={(clubId) => setForm({ ...form, managed_club_team_id: clubId })} /></label>
      <button>Create account</button>
    </form>
    {error && <p className="form-error">{error}</p>}
    <div className="account-list">{users.map((user) => <article key={user.id} className="account-row">
      <div><strong>{user.display_name || user.username}</strong><p>@{user.username} · {user.role}</p></div>
      <ClubPicker label={`Club for ${user.username}`} clubs={clubs} value={user.managed_club_team_id} onChange={(clubId) => void changeClub(user, clubId)} />
      <span className={user.is_active ? "status-active" : "status-disabled"}>{user.is_active ? "Active" : "Disabled"}</span>
      <button className="button--secondary" disabled={user.id === currentUser?.id} onClick={() => toggle(user)}>{user.is_active ? "Disable" : "Enable"}</button>
    </article>)}</div>
  </main>;
}
