
import { useEffect, useState } from "react";
import { Link, useNavigate } from 'react-router-dom';
import "./SessionsList.css"

export default function SessionList() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);

  const handleEnter = async (sessionId) => {
    navigate(`/game`, {state: {sessionId: sessionId}});
  }

  useEffect(() => {
    fetch("http://localhost:8000/api/sessions")
      .then(res => res.json())
      .then(data => setSessions(data.sessions));
  }, []);

  return (
  <div>
    <h2>Active Sessions</h2>

    <table className="session-table">
      <thead>
        <tr>
          <th>Session ID</th>
          <th>Players</th>
          <th></th>
        </tr>
      </thead>

      <tbody>
        {sessions.map((s) => (
          <tr key={s.id}>
            <td>{s.id}</td>
            <td>{s.players}</td>
            <td><button onClick={() => handleEnter(s.id)}>Enter</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
}