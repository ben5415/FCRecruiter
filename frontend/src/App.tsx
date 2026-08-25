import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { UserManagementPage } from "./pages/UserManagementPage";
import { PlayersPage } from "./pages/PlayersPage";
import { SquadPage } from "./pages/SquadPage";
import "./styles.css";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider><Routes>
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}><Route element={<AppShell />}>
          <Route index element={<Navigate replace to="/squad" />} /><Route path="squad" element={<SquadPage />} /><Route path="marketplace" element={<PlayersPage />} />
          <Route element={<ProtectedRoute adminOnly />}><Route path="admin/users" element={<UserManagementPage />} /></Route>
        </Route></Route>
      </Routes></AuthProvider>
    </BrowserRouter>
  );
}

export default App;
