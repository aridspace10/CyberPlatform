import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSessions } from "../api/sessions";
import "./SessionsList.css";

const visibilityLabels = {
  public: "Public",
  private: "Private",
  friends_only: "Friends only",
};

export default function SessionsList({ user, authLoading }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setSessions((await getSessions()).sessions || []);
    } catch (err) {
      setError(err.message || "Could not load sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (!authLoading) refresh(); }, [authLoading, refresh]);

  return <section className="sessions-list" aria-labelledby="sessions-list-title">
    <div className="sessions-list-heading">
      <div>
        <p className="home-kicker">OPEN LOBBIES &amp; YOUR SESSIONS</p>
        <h2 id="sessions-list-title">Available sessions <span>{!loading && !error ? String(sessions.length).padStart(2, "0") : "--"}</span></h2>
      </div>
      <button type="button" onClick={refresh} disabled={loading}>Refresh list</button>
    </div>

    {loading && <p className="sessions-message" role="status">Loading sessions…</p>}
    {error && <p className="sessions-message sessions-error" role="alert">{error} <button type="button" onClick={refresh}>Try again</button></p>}
    {!loading && !error && sessions.length === 0 && <div className="sessions-empty">
      <span aria-hidden="true">&gt;_</span>
      <h3>No sessions available yet.</h3>
      <p>Create a session to start practicing with others.</p>
      {user && <Link to="/session-create">Create a session <span aria-hidden="true">↗</span></Link>}
    </div>}
    {!loading && !error && sessions.length > 0 && <div className="sessions-table-wrap">
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
