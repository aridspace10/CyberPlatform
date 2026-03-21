import { useState } from "react";
import { useAuth } from "../../auth/useAuth";
import { Link, useNavigate } from 'react-router-dom';
import './LoginPage.css';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/")
    } catch (err) {
      setError("ACCESS DENIED — INVALID CREDENTIALS");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleLogin();
  };

  return (
    <div className="login-page-wrapper">
      <div className="login-glow" />

      <div className="login-page">
        {/* Top bar */}
        <div className="login-header">
          <div className="login-header-dot" />
          <span className="login-header-title">
            <span>SYS://</span>AUTH_PORTAL
          </span>
        </div>

        {/* Main panel */}
        <div className="login-panel">
          {/* Logo */}
          <div className="login-logo">
            <div className="login-logo-icon">
              <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L3 7v5c0 5.25 3.75 10.15 9 11.35C17.25 22.15 21 17.25 21 12V7L12 2z" />
                <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="login-logo-name">CYBER<em>PLATFORM</em></div>
            <div className="login-logo-sub">Secure Operations Center</div>
          </div>

          {/* Divider */}
          <div className="login-divider">
            <div className="login-divider-line" />
            <span className="login-divider-text">authenticate</span>
            <div className="login-divider-line" />
          </div>

          {/* Username */}
          <div className="login-field">
            <label className="login-label">Operator ID</label>
            <div className="login-input-wrap">
              <span className="input-prefix">&gt;_</span>
              <input
                type="text"
                placeholder="username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                onKeyDown={handleKeyDown}
                autoComplete="username"
                spellCheck={false}
              />
              <div className="input-line" />
            </div>
          </div>

          {/* Password */}
          <div className="login-field">
            <label className="login-label">Access Key</label>
            <div className="login-input-wrap">
              <span className="input-prefix">🔑</span>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={handleKeyDown}
                autoComplete="current-password"
              />
              <div className="input-line" />
            </div>
          </div>
          
          {/* Signup */}
          <button className="already-btn" onClick={() => {navigate("/signup")}} disabled={loading}>
            <span>{"DON'T HAVE AN ACCOUNT?"}</span>
          </button>

          {/* Submit */}
          <button onClick={handleLogin} disabled={loading}>
            <span>{loading ? "VERIFYING..." : "INITIATE ACCESS"}</span>
          </button>

          {/* Error */}
          <div className="login-error">{error}</div>
        </div>

        {/* Footer */}
        <div className="login-footer">
          <span className="login-footer-status">
            <span className="status-dot" />
            SECURE CHANNEL ACTIVE
          </span>
          <span className="login-footer-version">v2.4.1</span>
        </div>
      </div>
    </div>
  );
} 