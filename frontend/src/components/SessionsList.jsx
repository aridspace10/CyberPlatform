
import { useEffect, useState } from "react";

export default function SessionList() {

  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/api/sessions")
      .then(res => res.json())
      .then(data => setSessions(data.sessions));
  }, []);

  return (
    <div>
      <h2>Active Sessions</h2>

      {sessions.map(s => (
        <div key={s.id}>
          Session: {s.id} | Players: {s.players}
        </div>
      ))}
    </div>
  );
}