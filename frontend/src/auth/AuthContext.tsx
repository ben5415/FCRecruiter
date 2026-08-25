import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { getMe, login as loginRequest, logout as logoutRequest, type CurrentUser } from "../api/auth";

interface AuthValue {
  user: CurrentUser | null;
  csrfToken: string | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((auth) => {
        setUser(auth?.user ?? null);
        setCsrfToken(auth?.csrf_token ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(identifier: string, password: string) {
    const auth = await loginRequest(identifier, password);
    setUser(auth.user);
    setCsrfToken(auth.csrf_token);
  }

  async function logout() {
    if (csrfToken) await logoutRequest(csrfToken);
    setUser(null);
    setCsrfToken(null);
  }

  return <AuthContext.Provider value={{ user, csrfToken, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
