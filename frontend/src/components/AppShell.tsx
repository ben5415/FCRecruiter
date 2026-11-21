import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getTeamTheme } from "../auth/teamTheme";


export function AppShell() {
  const { user, logout } = useAuth();
  const [logoutError, setLogoutError] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => window.localStorage.getItem("sidebar-collapsed") === "true",
  );

  function toggleSidebar() {
    setSidebarCollapsed((current) => {
      window.localStorage.setItem("sidebar-collapsed", String(!current));
      return !current;
    });
  }

  async function handleLogout() {
    setLogoutError("");
    try {
      await logout();
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Could not log out");
    }
  }
  return (
    <div className={sidebarCollapsed ? "app-layout app-layout--collapsed" : "app-layout"} data-theme={getTeamTheme(user?.tenant.club.club_team_id)}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <NavLink className="brand" to="/marketplace">
            <span>{user?.tenant.club.club_name || "Football Recruitment Hub"}</span>
          </NavLink>
          <button
            aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
            className="sidebar-toggle"
            onClick={toggleSidebar}
            type="button"
          >
            <svg aria-hidden="true" viewBox="0 0 20 20"><path d="m12.5 5-5 5 5 5" /></svg>
          </button>
        </div>
        <nav className="main-nav" aria-label="Main navigation">
          <div className="nav-links">
            <NavLink data-short="S" to="/squad"><span>Squad</span></NavLink>
            <NavLink data-short="M" to="/marketplace"><span>Marketplace</span></NavLink>
            <NavLink data-short="E" to="/events"><span>Events</span></NavLink>
            <NavLink data-short="T" to="/tactics"><span>Tactics</span></NavLink>
            {user?.role === "manager" && <NavLink data-short="K" to="/knowledge"><span>Knowledge</span></NavLink>}
            {user?.role === "manager" && <NavLink data-short="G" to="/agent-settings"><span>Agent Settings</span></NavLink>}
            {user?.role === "manager" && <NavLink data-short="A" to="/admin/users"><span>Accounts</span></NavLink>}
          </div>
          <div className="account-menu">
            <span className="nav-user"><small>Signed in as</small>{user?.display_name || user?.username}</span>
            <button className="nav-logout" onClick={() => void handleLogout()}>Log out</button>
          </div>
        </nav>
      </aside>
      <div className="app-content">
        {logoutError && <div className="topbar-error" role="alert">{logoutError}</div>}
        <Outlet />
      </div>
    </div>
  );
}
