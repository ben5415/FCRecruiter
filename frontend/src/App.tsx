import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { PlayersPage } from "./pages/PlayersPage";
import { SquadPage } from "./pages/SquadPage";
import "./styles.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate replace to="/squad" />} />
          <Route path="squad" element={<SquadPage />} />
          <Route path="marketplace" element={<PlayersPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
