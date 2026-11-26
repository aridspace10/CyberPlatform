import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getSessions } from "../api/sessions";
import "./SessionsList.css";

const visibilityLabels = {
  public: "Public",
  private: "Private",
  friends_only: "Friends only",
};
const REFRESH_INTERVAL_MS = 10_000;

export default function SessionsList({ user, authLoading }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const hasLoaded = useRef(false);
  const requestId = useRef(0);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    const currentRequest = ++requestId.current;
    if (hasLoaded.current) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const result = await getSessions();
      if (requestId.current === currentRequest) setSessions(result.sessions || []);
    } catch (err) {
      if (requestId.current === currentRequest) setError(err.message || "Could not load sessions.");
    } finally {
      if (requestId.current === currentRequest) {
        inFlight.current = false;
        hasLoaded.current = true;
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    if (authLoading) return undefined;
    refresh();
    const timer = window.setInterval(() => { if (!document.hidden) refresh(); }, REFRESH_INTERVAL_MS);
    const onVisible = () => { if (!document.hidden) refresh(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      requestId.current += 1;
      inFlight.current = false;
    };
  }, [authLoading, refresh]);

  return <section className="sessions-list" aria-labelledby="sessions-list-title">
    <div className="sessions-list-heading">
      <div>
        <p className="home-kicker">OPEN LOBBIES &amp; YOUR SESSIONS</p>
        <h2 id="sessions-list-title">Available sessions <span>{!loading ? String(sessions.length).padStart(2, "0") : "--"}</span></h2>
        <p className="sessions-refresh-note">Refreshes every 10 seconds while this page is open.{refreshing && <span role="status"> Updating…</span>}</p>
      </div>
      <button type="button" onClick={refresh} disabled={loading || refreshing}>Refresh list</button>
    </div>

    {loading && <p className="sessions-message" role="status">Loading sessions…</p>}
    {error && <p className="sessions-message sessions-error" role="alert">{error} <button type="button" onClick={refresh}>Try again</button></p>}
    {!loading && sessions.length === 0 && !error && <div className="sessions-empty">
      <span aria-hidden="true">&gt;_</span>
      <h3>No sessions available yet.</h3>
      <p>Create a session to start practicing with others.</p>
      {user && <Link to="/session-create">Create a session <span aria-hidden="true">↗</span></Link>}
    </div>}
    {!loading && sessions.length > 0 && <div className="sessions-table-wrap">
      <table className="session-table">
        <thead><tr><th scope="col">Session</th><th scope="col">Mode</th><th scope="col">Access</th><th scope="col">Status</th><th scope="col">Online</th><th scope="col"><span className="sessions-sr-only">Action</span></th></tr></thead>
        <tbody>{sessions.map(session => <tr key={session.id}>
          <td><span className="session-id">#{session.id}</span><strong>{session.name || "Untitled session"}</strong></td>
          <td>{session.play_type === "SinglePlayer" ? "Solo" : "Versus"}</td>
          <td>{visibilityLabels[session.visibility] || session.visibility}</td>
          <td><span className={`session-state session-state-${session.state || "unknown"}`}>{session.state || "Unknown"}</span></td>
          <td>{session.connected_players}</td>
          <td><Link className="session-enter" to={user ? `/game/${session.id}` : "/login"} state={user ? undefined : { from: `/game/${session.id}` }}>{user ? session.member ? "Open →" : "Join →" : "Sign in →"}</Link></td>
        </tr>)}</tbody>
      </table>
    </div>}
  </section>;
}
