import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { UserManagementPage } from "./pages/UserManagementPage";
import { PlayersPage } from "./pages/PlayersPage";
import { SquadPage } from "./pages/SquadPage";
import { EventsPage } from "./pages/EventsPage";
import { PlayerDetailPage } from "./pages/PlayerDetailPage";
import { TacticsPage } from "./pages/TacticsPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { AgentSettingsPage } from "./pages/AgentSettingsPage";
import { RagTestPage } from "./pages/RagTestPage";
import "./styles.css";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider><Routes>
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}><Route element={<AppShell />}>
          <Route index element={<Navigate replace to="/squad" />} /><Route path="squad" element={<SquadPage />} /><Route path="marketplace" element={<PlayersPage />} /><Route path="players/:playerId" element={<PlayerDetailPage />} /><Route path="events" element={<EventsPage />} /><Route path="tactics" element={<TacticsPage />} />
          <Route element={<ProtectedRoute managerOnly />}><Route path="admin/users" element={<UserManagementPage />} /><Route path="knowledge" element={<KnowledgePage />} /><Route path="agent-settings" element={<AgentSettingsPage />} /><Route path="rag-test" element={<RagTestPage />} /></Route>
        </Route></Route>
      </Routes></AuthProvider>
    </BrowserRouter>
  );
}

export default App;
