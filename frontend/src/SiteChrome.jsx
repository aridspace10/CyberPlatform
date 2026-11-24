import { Link, useLocation } from "react-router-dom";
import "./Homepage.css";

export function SiteBrand() {
  return <Link className="home-brand" to="/" aria-label="CyberPlatform home"><span className="home-brand-mark" aria-hidden="true">&gt;_</span><span>CYBER<span>PLATFORM</span></span></Link>;
}

export function SiteHeader({ user, loading, enteringSandbox, onEnterSandbox }) {
  const pathname = useLocation().pathname;
  const isHome = pathname === "/";

  return <header className="home-header">
    <SiteBrand />
    <nav className="home-nav" aria-label="Main navigation">
      {!isHome && <Link to="/">Home</Link>}
      {isHome ? <><a href="#how-it-works">How it works</a><a href="#the-sandbox">The Sandbox</a></> : null}
      <Link to="/sessions" aria-current={pathname === "/sessions" ? "page" : undefined}>Sessions</Link>
      <Link to="/contact" aria-current={pathname === "/contact" ? "page" : undefined}>Contact us</Link>
      {user ? <Link to="/profile" aria-current={pathname === "/profile" ? "page" : undefined}>Profile</Link> : <Link to="/login">Sign in</Link>}
    </nav>
    {user ? (
      <button className="home-header-action" type="button" onClick={onEnterSandbox} disabled={enteringSandbox}>{enteringSandbox ? "Opening Sandbox…" : "Enter Sandbox"} <span aria-hidden="true">↗</span></button>
    ) : !loading ? (
      <Link className="home-header-action" to="/signup">Get started <span aria-hidden="true">↗</span></Link>
    ) : null}
  </header>;
}

export function SiteFooter({ user, onLogout }) {
  return <footer className="home-footer"><SiteBrand /><p>Practice makes progress.</p><div className="home-footer-links"><Link to="/contact">Contact us</Link>{user ? <button type="button" onClick={onLogout}>Sign out</button> : <Link to="/login">Sign in</Link>}<a href="#main-content">Back to top ↑</a></div></footer>;
}
