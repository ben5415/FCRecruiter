import { NavLink, Outlet } from "react-router-dom";


export function AppShell() {
  return (
    <div className="app-layout">
      <header className="topbar">
        <NavLink className="brand" to="/marketplace">
          Football Recruitment Hub
        </NavLink>
        <nav className="main-nav" aria-label="Main navigation">
          <NavLink to="/squad">Squad</NavLink>
          <NavLink to="/marketplace">Marketplace</NavLink>
        </nav>
      </header>
      <Outlet />
    </div>
  );
}
