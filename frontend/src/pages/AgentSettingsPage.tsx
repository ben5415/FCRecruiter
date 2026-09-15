import { useEffect, useState } from "react";
import { disableAgentVersion, enableAgentVersion, listAgentVersions, registerCurrentAgent, type AgentDefinition } from "../api/agentSettings";
import { useAuth } from "../auth/AuthContext";

export function AgentSettingsPage() {
  const { csrfToken } = useAuth();
  const [versions, setVersions] = useState<AgentDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function load() { setLoading(true); try { setVersions(await listAgentVersions()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load Agent versions"); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  async function act(action: () => Promise<unknown>, success: string) { setWorking(true); setError(""); setNotice(""); try { await action(); await load(); setNotice(success); } catch (reason) { setError(reason instanceof Error ? reason.message : "Agent operation failed"); } finally { setWorking(false); } }
  return <main className="marketplace agent-settings-page">
    <div className="marketplace__header"><div><p className="eyebrow">Agent governance</p><h1>Agent Settings</h1></div><p>Register the Recruitment Agent configuration bundled with this deployment, then choose the active version.</p></div>
    <section className="agent-settings-summary"><div><h2>Recruitment Agent</h2><p>Prompt, Tool allowlist and output schema are read from server code and cannot be edited here.</p></div><button disabled={working || !csrfToken} onClick={() => void act(() => registerCurrentAgent(csrfToken!), "Current code configuration registered.")}>Register current version</button></section>
    {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="form-success" role="status">{notice}</p>}
    <div className="agent-version-list">{loading && <p>Loading Agent versions…</p>}{!loading && versions.length === 0 && <div className="empty-state"><h2>No registered version</h2><p>Register the current code configuration, then enable it before running recruitment analysis.</p></div>}
      {versions.map((version) => <article className="agent-version-row" key={version.id}><div><p className="eyebrow">Version {version.version}</p><h2>{version.name}</h2><p>{version.description}</p></div><div className="agent-version-tools"><strong>{version.tool_names.length} Tools</strong><small>{version.tool_names.join(", ")}</small></div><span className={`status-${version.status}`}>{version.status}</span><div className="agent-version-actions">{version.status === "active" ? <button className="button--danger" disabled={working || !csrfToken} onClick={() => void act(() => disableAgentVersion(version.version, csrfToken!), `Version ${version.version} disabled.`)}>Disable</button> : <button disabled={working || !csrfToken} onClick={() => void act(() => enableAgentVersion(version.version, csrfToken!), `Version ${version.version} enabled.`)}>Enable</button>}</div></article>)}
    </div>
  </main>;
}
