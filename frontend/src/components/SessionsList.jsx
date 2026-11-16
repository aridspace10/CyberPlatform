
import { useEffect, useState } from "react";
import { useNavigate } from 'react-router-dom';
import "./SessionsList.css"
import { API_URL } from "../api/config";

export default function SessionList() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const handleEnter = async (sessionId) => {
    navigate(`/game/${sessionId}`);
  }

  useEffect(() => {
    fetch(`${API_URL}/sessions`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    })
      .then(res => {
        if (!res.ok) throw new Error("Could not load sessions");
        return res.json();
      })
      .then(data => setSessions(data.sessions || []))
      .catch(() => setError("Could not load sessions. Refresh to try again."))
      .finally(() => setLoading(false));
  }, []);

  return (
  <div>
    <h2>Active Sessions</h2>

    <table className="session-table">
      <thead>
        <tr>
          <th>Session ID</th>
          <th>Name</th>
          <th>Type</th>
          <th>Players</th>
          <th></th>
        </tr>
      </thead>

      <tbody>
        {loading && <tr><td colSpan={5}>Loading sessions...</td></tr>}
        {error && <tr><td colSpan={5} role="alert">{error}</td></tr>}
        {!loading && !error && sessions.length === 0 && (
          <tr>
            <td colSpan={5}>No sessions available. Create a Versus game to play with others.</td>
          </tr>
        )}
        {sessions.map((s) => (
          <tr key={s.id}>
            <td>{s.id}</td>
            <td>{s.name}</td>
            <td>{{ public: "Public", private: "Private", friends_only: "Friends Only" }[s.visibility]}</td>
            <td>{s.players}</td>
            <td><button onClick={() => handleEnter(s.id)}>Enter</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
}
