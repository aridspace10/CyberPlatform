import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { enterTutorial } from "../../api/sessions";
import { useAuth } from "../../auth/useAuth";
import SessionsList from "../../components/SessionsList";
import { SiteFooter, SiteHeader } from "../../SiteChrome";
import "./SessionsPage.css";

export default function SessionsPage() {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();
  const [enteringSandbox, setEnteringSandbox] = useState(false);
  const [sandboxError, setSandboxError] = useState("");

  const handleEnterSandbox = async () => {
    setEnteringSandbox(true);
    setSandboxError("");
    try {
      const data = await enterTutorial(user.id);
      navigate(`/game/${data.session_id}`);
    } catch (error) {
      setSandboxError(error.message || "Could not enter Sandbox. Please try again.");
    } finally {
      setEnteringSandbox(false);
    }
  };

  return <div className="homepage sessions-page">
    <a className="home-skip-link" href="#main-content">Skip to content</a>
    <SiteHeader user={user} loading={loading} enteringSandbox={enteringSandbox} onEnterSandbox={handleEnterSandbox} />
    <main className="sessions-main" id="main-content">
      <header className="sessions-page-header">
        <div>
          <p className="home-kicker">PLAY / SESSIONS</p>
          <h1>Find your <span>next session.</span></h1>
          <p>Browse open lobbies and return to sessions you have joined.</p>
        </div>
        {user ? <Link className="sessions-create" to="/session-create">Create a session <span aria-hidden="true">↗</span></Link> : <Link className="sessions-create" to="/login" state={{ from: "/session-create" }}>Sign in to create <span aria-hidden="true">↗</span></Link>}
      </header>
      {sandboxError && <p className="sessions-error-message" role="alert">{sandboxError}</p>}
      <SessionsList key={user?.id ?? "guest"} user={user} authLoading={loading} />
    </main>
    <SiteFooter user={user} onLogout={logout} />
  </div>;
}
