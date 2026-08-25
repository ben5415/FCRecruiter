import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  if (user) return <Navigate replace to="/squad" />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(identifier, password);
      navigate("/squad", { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="login-page">
    <form className="login-card" onSubmit={submit}>
      <p className="eyebrow">Club access</p><h1>Sign in</h1>
      <label>Username or email<input required autoFocus value={identifier} onChange={(e) => setIdentifier(e.target.value)} /></label>
      <label>Password<input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      {error && <p className="form-error">{error}</p>}
      <button disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
    </form>
  </main>;
}
