import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { sendContactReport } from "../../api/contact";
import { useAuth } from "../../auth/useAuth";
import "./ContactPage.css";

const initialReport = {
  name: "", email: "", category: "bug", subject: "", description: "",
  steps: "", expected: "", actual: "", page: "", device: "",
};

export default function ContactPage() {
  const { user } = useAuth();
  const location = useLocation();
  const [report, setReport] = useState(() => ({
    ...initialReport,
    page: location.state?.page || "",
  }));
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [reference, setReference] = useState("");

  useEffect(() => {
    if (!user) return;
    setReport((current) => ({
      ...current,
      name: current.name || user.username || "",
      email: current.email || user.email || "",
    }));
  }, [user]);

  const update = (event) => {
    const { name, value } = event.target;
    setReport((current) => ({ ...current, [name]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSending(true);
    try {
      const result = await sendContactReport(report);
      setReference(result.reference);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="contact-page">
      <a className="contact-skip" href="#contact-main">Skip to form</a>
      <header className="contact-header">
        <Link className="contact-brand" to="/"><span aria-hidden="true">&gt;_</span> CYBER<strong>PLATFORM</strong></Link>
        <Link to="/">← Back to home</Link>
      </header>

      <main id="contact-main" className="contact-layout">
        <div className="contact-intro">
          <p className="contact-eyebrow">SUPPORT / CONTACT US</p>
          <h1>Tell us what<br /><span>went wrong.</span></h1>
          <p>Found an issue or have an idea? Send us the details and we’ll use them to investigate. You can contact us without signing in.</p>
          <div className="contact-tip">
            <span>HELP US HELP YOU</span>
            <p>Include what you were doing, what you expected, and any error message you saw. Please don’t include passwords or other sensitive information.</p>
          </div>
        </div>

        <section className="contact-panel" aria-labelledby="contact-form-title">
          {reference ? (
            <div className="contact-success" role="status">
              <span className="contact-success-icon" aria-hidden="true">✓</span>
              <h2>Message sent</h2>
              <p>Thanks for letting us know. Keep this reference if you need to follow up:</p>
              <strong>{reference}</strong>
              <Link to="/">Return home →</Link>
            </div>
          ) : (
            <>
              <div className="contact-panel-heading">
                <span>01 / YOUR REPORT</span>
                <h2 id="contact-form-title">How can we help?</h2>
                <p>Fields marked * are required.</p>
              </div>
              <form onSubmit={submit}>
                <div className="contact-row">
                  <label>Your name *<input name="name" value={report.name} onChange={update} autoComplete="name" maxLength={100} required placeholder="Your name or username" /></label>
                  <label>Email for replies *<input type="email" name="email" value={report.email} onChange={update} autoComplete="email" maxLength={254} required placeholder="you@example.com" /></label>
                </div>
                <label>What is this about? *
                  <select name="category" value={report.category} onChange={update} required>
                    <option value="bug">Something isn’t working</option>
                    <option value="account">Account or sign in</option>
                    <option value="gameplay">Sandbox or gameplay</option>
                    <option value="suggestion">Suggestion</option>
                    <option value="other">Something else</option>
                  </select>
                </label>
                <label>Short summary *<input name="subject" value={report.subject} onChange={update} maxLength={120} minLength={3} required placeholder="e.g. Sandbox won't load after signing in" /></label>
                <label>What happened? *<textarea name="description" value={report.description} onChange={update} minLength={10} maxLength={5000} required rows={5} placeholder="Tell us what you were trying to do and what happened instead." /></label>

                <div className="contact-detail-heading"><h3>Details that help us investigate</h3><span>Optional</span></div>
                <label>Steps to reproduce<textarea name="steps" value={report.steps} onChange={update} maxLength={2000} rows={3} placeholder="1. Opened the Sandbox&#10;2. Typed a command&#10;3. Saw an error" /></label>
                <div className="contact-row">
                  <label>What did you expect?<textarea name="expected" value={report.expected} onChange={update} maxLength={1000} rows={3} placeholder="What should have happened?" /></label>
                  <label>What happened instead?<textarea name="actual" value={report.actual} onChange={update} maxLength={1000} rows={3} placeholder="Include the exact error text, if any." /></label>
                </div>
                <div className="contact-row">
                  <label>Page or feature<input name="page" value={report.page} onChange={update} maxLength={300} placeholder="e.g. Sandbox, profile, or a URL" /></label>
                  <label>Device and browser<input name="device" value={report.device} onChange={update} maxLength={300} placeholder="e.g. Windows 11, Chrome" /></label>
                </div>
                {error && <p className="contact-error" role="alert">{error}</p>}
                <button className="contact-submit" type="submit" disabled={sending}>{sending ? "Sending…" : "Send report →"}</button>
              </form>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
