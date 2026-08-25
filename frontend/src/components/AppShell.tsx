import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getTeamTheme } from "../auth/teamTheme";


export function AppShell() {
  const { user, logout } = useAuth();
  const [logoutError, setLogoutError] = useState("");

  async function handleLogout() {
    setLogoutError("");
    try {
      await logout();
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Could not log out");
    }
  }
  return (
    <div className="app-layout" data-theme={getTeamTheme(user?.managed_club_team_id)}>
      <header className="topbar">
        <NavLink className="brand" to="/marketplace">
          {user?.managed_club.club_name || "Football Recruitment Hub"}
        </NavLink>
        <nav className="main-nav" aria-label="Main navigation">
          <NavLink to="/squad">Squad</NavLink>
          <NavLink to="/marketplace">Marketplace</NavLink>
          {user?.role === "admin" && <NavLink to="/admin/users">Accounts</NavLink>}
          <span className="nav-user">{user?.display_name || user?.username}</span>
          <button className="nav-logout" onClick={() => void handleLogout()}>Log out</button>
        </nav>
      </header>
      {logoutError && <div className="topbar-error" role="alert">{logoutError}</div>}
      <Outlet />
    </div>
  );
}
