import { useEffect, useState, type FormEvent } from "react";

import { createUser, deleteUser, listUsers, setUserActive, updateUserPassword } from "../api/admin";
import type { CurrentUser, Role } from "../api/auth";
import { useAuth } from "../auth/AuthContext";
import { RolePicker } from "../components/RolePicker";

export function UserManagementPage() {
  const { user: currentUser, csrfToken } = useAuth();
  const [users, setUsers] = useState<CurrentUser[]>([]);
  const [error, setError] = useState("");
  const [passwordTarget, setPasswordTarget] = useState<CurrentUser | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [form, setForm] = useState<{ username: string; password: string; display_name: string; email: string; role: Role }>({ username: "", password: "", display_name: "", email: "", role: "player" });
  const load = () => listUsers().then(setUsers).catch((e: Error) => setError(e.message));
  useEffect(() => { void load(); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      await createUser({ ...form, display_name: form.display_name || null, email: form.email || null }, csrfToken!);
      setForm({ username: "", password: "", display_name: "", email: "", role: "player" });
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not create user"); }
  }

  async function toggle(target: CurrentUser) {
    try {
      const updated = await setUserActive(target.id, !target.is_active, csrfToken!);
      setUsers((items) => items.map((item) => item.id === updated.id ? updated : item));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update user"); }
  }

  async function remove(target: CurrentUser) {
    if (!window.confirm(`Delete account “${target.username}”? This action cannot be undone.`)) return;
    setError("");
    try {
      await deleteUser(target.id, csrfToken!);
      setUsers((items) => items.filter((item) => item.id !== target.id));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not delete user"); }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    if (!passwordTarget) return;
    setError("");
    try {
      await updateUserPassword(passwordTarget.id, newPassword, csrfToken!);
      setPasswordTarget(null);
      setNewPassword("");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update password"); }
  }

  return <main className="marketplace admin-page">
    <div className="marketplace__header"><div><p className="eyebrow">{currentUser?.tenant.name} · Manager</p><h1>Accounts</h1></div><p>Manage users within this club workspace.</p></div>
    <p className="required-note"><span aria-hidden="true">*</span> Required fields</p>
    <form className="account-form" onSubmit={submit}>
      <label><span>Username <span className="required-mark" aria-hidden="true">*</span></span><input required minLength={3} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></label>
      <label>Display name<input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} /></label>
      <label>Email<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
      <label><span>Password <span className="required-mark" aria-hidden="true">*</span></span><input required minLength={8} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
      <label>Role<RolePicker value={form.role} onChange={(role) => setForm({ ...form, role })} /></label>
      <button>Create account</button>
    </form>
    {error && <p className="form-error">{error}</p>}
    <div className="account-list">{users.map((user) => <article key={user.id} className="account-row">
      <div><strong>{user.display_name || user.username}</strong><p>@{user.username} · {user.role}</p></div>
      <span className={user.is_active ? "status-active" : "status-disabled"}>{user.is_active ? "Active" : "Disabled"}</span>
      <div className="account-actions">
        <button className="button--secondary" disabled={user.id === currentUser?.id} onClick={() => toggle(user)}>{user.is_active ? "Disable" : "Enable"}</button>
        <button className="button--secondary" onClick={() => { setPasswordTarget(user); setNewPassword(""); }}>Change password</button>
        <button className="button--danger" disabled={user.id === currentUser?.id} onClick={() => void remove(user)}>Delete</button>
      </div>
    </article>)}</div>
    {passwordTarget && <div className="modal-backdrop" role="presentation" onMouseDown={() => setPasswordTarget(null)}>
      <form className="password-dialog" role="dialog" aria-modal="true" aria-labelledby="password-dialog-title" onMouseDown={(event) => event.stopPropagation()} onSubmit={changePassword}>
        <p className="eyebrow">Account security</p>
        <h2 id="password-dialog-title">Change password</h2>
        <p>Set a new password for <strong>{passwordTarget.username}</strong>. Their other sessions will be signed out.</p>
        <label><span>New password <span className="required-mark" aria-hidden="true">*</span></span><input autoFocus required minLength={8} type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
        <div className="dialog-actions"><button className="button--secondary" type="button" onClick={() => setPasswordTarget(null)}>Cancel</button><button type="submit">Update password</button></div>
      </form>
    </div>}
  </main>;
}
