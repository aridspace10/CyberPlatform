import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { enterTutorial } from "./api/sessions";
import { useAuth } from "./auth/useAuth";
import SessionList from "./components/SessionsList";
import "./Homepage.css";

const steps = [
  ["01", "pwd · ls · cd", "Find your way around", "See where you are, discover what is nearby, and move through a virtual file system one command at a time."],
  ["02", "mkdir · touch · mv", "Make it your own", "Create folders and files, then move things around. Every action gives you something new to inspect."],
  ["03", "cat · grep · wc", "Look a little closer", "Read files, search their contents, and count what you find as your command-line confidence grows."],
];

function TerminalPreview() {
  return (
    <div className="home-terminal" role="img" aria-label="Illustrative terminal preview showing pwd, ls, and mkdir commands in a simulated file system">
      <div className="home-terminal-bar">
        <span className="home-terminal-dots" aria-hidden="true"><i /><i /><i /></span>
        <span>sandbox / terminal</span>
        <span className="home-terminal-connected">● preview</span>
      </div>
      <div className="home-terminal-screen">
        <div className="home-terminal-green">CYBERPLATFORM // VIRTUAL SHELL</div>
        <div className="home-terminal-muted">A place to try things out. Start with a command.</div>
        <div><span className="home-terminal-green">you@cyber:/$</span> pwd</div>
        <div className="home-terminal-output">/</div>
        <div><span className="home-terminal-green">you@cyber:/$</span> mkdir practice</div>
        <div><span className="home-terminal-green">you@cyber:/$</span> cd practice</div>
        <div><span className="home-terminal-green">you@cyber:/practice$</span> touch notes.txt</div>
        <div><span className="home-terminal-green">you@cyber:/practice$</span> ls</div>
        <div className="home-terminal-output">notes.txt</div>
        <div><span className="home-terminal-green">you@cyber:/practice$</span> <span className="home-terminal-cursor" /></div>
      </div>
      <div className="home-terminal-foot"><span>● SIMULATED ENVIRONMENT</span><span>Preview only</span></div>
    </div>
  );
}

export default function Homepage() {
  const navigate = useNavigate();
  const { user, logout, loading } = useAuth();
  const [sandboxError, setSandboxError] = useState("");
  const [enteringSandbox, setEnteringSandbox] = useState(false);

  const handleEnterSandbox = async () => {
    if (!user) {
      navigate("/login");
      return;
    }
    setSandboxError("");
    setEnteringSandbox(true);
    try {
      const data = await enterTutorial(user.id);
      navigate(`/game/${data.session_id}`);
    } catch (error) {
      setSandboxError(error.message || "Could not enter Sandbox. Please try again.");
    } finally {
      setEnteringSandbox(false);
    }
  };

  const sandboxButton = (label) => (
    <button className="home-button home-button-primary" type="button" onClick={handleEnterSandbox} disabled={enteringSandbox}>
      {enteringSandbox ? "Opening your Sandbox…" : label} <span aria-hidden="true">↗</span>
    </button>
  );

  return (
    <div className="homepage">
      <a className="home-skip-link" href="#main-content">Skip to content</a>
      <header className="home-header">
        <Link className="home-brand" to="/" aria-label="CyberPlatform home"><span className="home-brand-mark" aria-hidden="true">&gt;_</span><span>CYBER<span>PLATFORM</span></span></Link>
        <nav className="home-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#the-sandbox">The Sandbox</a>
          {user ? <Link to="/profile">Profile</Link> : <Link to="/login">Sign in</Link>}
        </nav>
        {user ? (
          <button className="home-header-action" type="button" onClick={handleEnterSandbox} disabled={enteringSandbox}>Enter Sandbox <span aria-hidden="true">↗</span></button>
        ) : !loading ? (
          <Link className="home-header-action" to="/signup">Get started <span aria-hidden="true">↗</span></Link>
        ) : null}
      </header>

      <main id="main-content">
        <section className="home-hero" aria-labelledby="home-title">
          <div className="home-hero-copy">
            <p className="home-eyebrow"><span className="home-live-dot" /> YOUR COMMAND LINE STARTS HERE</p>
            <h1 id="home-title">Learn the terminal <span>by using it.</span></h1>
            <p className="home-lead">Explore a Linux-style command line in your browser. Create files, try commands, and see what happens in a simulated space made for practice.</p>
            <div className="home-actions">
              {user ? sandboxButton("Enter your Sandbox") : <Link className="home-button home-button-primary" to="/signup">Create an account <span aria-hidden="true">↗</span></Link>}
              <a className="home-button home-button-secondary" href="#how-it-works">See how it works <span aria-hidden="true">↓</span></a>
            </div>
            {user && <p className="home-welcome">Signed in as <strong>{user.username}</strong></p>}
            {sandboxError && <p className="home-error" role="alert">{sandboxError}</p>}
            <div className="home-highlights" aria-label="Sandbox highlights">
              <span>✓ No installation</span><span>✓ A space of your own</span><span>✓ Learn at your pace</span>
            </div>
          </div>
          <div className="home-hero-visual">
            <span className="home-visual-caption">AN OPEN INVITATION TO EXPERIMENT</span>
            <TerminalPreview />
            <span className="home-visual-caption home-visual-index">FIG. 01 / THE SANDBOX</span>
          </div>
        </section>

        <section className="home-strip" aria-label="About the experience"><span>PRACTICE MODE: ON</span><p>Real commands. A virtual file system. Room to figure things out.</p><span aria-hidden="true">✳</span></section>

        <section className="home-section" id="how-it-works" aria-labelledby="home-how-title">
          <div className="home-section-heading"><div><p className="home-kicker">01 / HOW IT WORKS</p><h2 id="home-how-title">Start with a prompt.<br /><span>See where it takes you.</span></h2></div><p>The Sandbox gives you a place to build command-line habits through exploration. Type a command, read the response, and use what you learn for the next step.</p></div>
          <div className="home-step-grid">
            {steps.map(([number, commands, title, description]) => <article className="home-step" key={number}><span className="home-step-number">{number}</span><span className="home-step-command">{commands}</span><h3>{title}</h3><p>{description}</p><span className="home-step-arrow" aria-hidden="true">↗</span></article>)}
          </div>
        </section>

        <section className="home-sandbox" id="the-sandbox" aria-labelledby="home-sandbox-title">
          <div className="home-sandbox-mark" aria-hidden="true">&gt;_</div>
          <div className="home-sandbox-copy"><p className="home-kicker">02 / THE SANDBOX</p><h2 id="home-sandbox-title">Your place to<br /><span>try the next command.</span></h2><p>Work inside a simulated file system, where you can make directories, inspect files, and follow your curiosity. Your Sandbox is tied to your account, so you can save your work and come back to it.</p>
            {user ? <button className="home-text-link" type="button" onClick={handleEnterSandbox} disabled={enteringSandbox}>{enteringSandbox ? "Opening Sandbox…" : "Open your Sandbox"} <span aria-hidden="true">→</span></button> : <Link className="home-text-link" to="/signup">Make your space <span aria-hidden="true">→</span></Link>}
          </div>
          <div className="home-sandbox-note"><span>THE IDEA</span><p>Learn by trying.<br />Keep what you discover.</p></div>
        </section>

        <section className="home-cta" aria-labelledby="home-cta-title">
          <p className="home-kicker">READY WHEN YOU ARE</p><h2 id="home-cta-title">Your next command<br />is up to you<span>.</span></h2><p>Open the Sandbox and start exploring. The first step can be as simple as <code>ls</code>.</p>
          {user ? sandboxButton("Enter your Sandbox") : <div className="home-cta-actions"><Link className="home-button home-button-primary" to="/signup">Create an account <span aria-hidden="true">↗</span></Link><Link to="/login">Already have an account? Sign in</Link></div>}
        </section>

        {import.meta.env.DEV && <section className="home-dev-tools" aria-label="Local development tools"><h2>Local development tools</h2><p>Multiplayer sessions are still under development.</p><Link to="/session-create">Create a session</Link><SessionList /></section>}
      </main>

      <footer className="home-footer"><Link className="home-brand" to="/" aria-label="CyberPlatform home"><span className="home-brand-mark" aria-hidden="true">&gt;_</span><span>CYBER<span>PLATFORM</span></span></Link><p>Practice makes progress.</p><div className="home-footer-links">{user ? <button type="button" onClick={logout}>Sign out</button> : <Link to="/login">Sign in</Link>}<a href="#main-content">Back to top ↑</a></div></footer>
    </div>
  );
}
