import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "./api/health";
import "./styles.css";

type ConnectionState =
  | { kind: "loading" }
  | { kind: "connected"; health: HealthResponse }
  | { kind: "error"; message: string };

function App() {
  const [connection, setConnection] = useState<ConnectionState>({
    kind: "loading",
  });

  useEffect(() => {
    getHealth()
      .then((health) => setConnection({ kind: "connected", health }))
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Unknown error";
        setConnection({ kind: "error", message });
      });
  }, []);

  return (
    <main className="app-shell">
      <section className="welcome-card">
        <p className="eyebrow">Development shell</p>
        <h1>Football Recruitment Hub</h1>
        <p className="description">
          React 前端和 FastAPI 后端框架已经连接。下一步可以从球员目录模块开始。
        </p>

        <div className={`status status--${connection.kind}`}>
          {connection.kind === "loading" && "正在连接后端…"}
          {connection.kind === "connected" && (
            <>
              <span className="status-dot" aria-hidden="true" />
              {connection.health.service} · {connection.health.environment}
            </>
          )}
          {connection.kind === "error" && `后端连接失败：${connection.message}`}
        </div>
      </section>
    </main>
  );
}

export default App;
