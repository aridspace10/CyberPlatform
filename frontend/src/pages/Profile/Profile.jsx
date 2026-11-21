import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import { enterTutorial } from "../../api/sessions";
import { SiteFooter, SiteHeader } from "../../SiteChrome";
import {
  acceptFriendRequest, blockUser, declineFriendRequest, getBlockedUsers, getFriendRequests, getFriends,
  removeFriend, searchUsers, sendFriendRequest, unblockUser,
} from "../../api/users";
import "./Profile.css";

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState({ incoming: [], outgoing: [] });
  const [blocked, setBlocked] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [enteringSandbox, setEnteringSandbox] = useState(false);

  const handleEnterSandbox = async () => {
    setError("");
    setEnteringSandbox(true);
    try {
      const data = await enterTutorial(user.id);
      navigate(`/game/${data.session_id}`);
    } catch (err) {
      setError(err.message || "Could not enter Sandbox. Please try again.");
    } finally {
      setEnteringSandbox(false);
    }
  };

  const refresh = useCallback(async () => {
    const [nextFriends, nextRequests, nextBlocked] = await Promise.all([getFriends(), getFriendRequests(), getBlockedUsers()]);
    setFriends(nextFriends);
    setRequests(nextRequests);
    setBlocked(nextBlocked);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getFriends(), getFriendRequests(), getBlockedUsers()])
      .then(([nextFriends, nextRequests, nextBlocked]) => {
        if (!active) return;
        setFriends(nextFriends);
        setRequests(nextRequests);
        setBlocked(nextBlocked);
      })
      .catch((err) => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const handleSearch = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    const term = query.trim();
    if (!term) { setResults([]); return; }
    setSearching(true);
    try { setResults(await searchUsers(term)); }
    catch (err) { setError(err.message); }
    finally { setSearching(false); }
  };

  const act = async (action, successMessage) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
      await refresh();
      setMessage(successMessage);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const friendIds = new Set(friends.map((friend) => friend.id));
  const incomingIds = new Set(requests.incoming.map((request) => request.user.id));
  const outgoingIds = new Set(requests.outgoing.map((request) => request.user.id));
  const blockedIds = new Set(blocked.map((blockedUser) => blockedUser.id));

  return (
    <div className="homepage profile-page">
      <a className="home-skip-link" href="#main-content">Skip to content</a>
      <SiteHeader user={user} enteringSandbox={enteringSandbox} onEnterSandbox={handleEnterSandbox} />
      <main className="profile-main" id="main-content">
        <header className="profile-header">
          <p className="home-kicker">YOUR SPACE / PROFILE</p>
          <h1>Profile <span>&amp; friends.</span></h1>
          <p>Signed in as <strong>{user?.username}</strong>. Find people to practice with and manage your connections.</p>
        </header>

      {error && <p className="profile-notice profile-error" role="alert">{error}</p>}
      {message && <p className="profile-notice profile-success" role="status">{message}</p>}

      <div className="profile-grid">
        <section className="profile-card" aria-labelledby="find-friends-title">
          <h2 id="find-friends-title">Find friends</h2>
          <form className="profile-search" onSubmit={handleSearch}>
            <label htmlFor="friend-search">Search by username</label>
            <div className="profile-search-row">
              <input id="friend-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Enter a username" />
              <button type="submit" disabled={searching}>{searching ? "Searching..." : "Search"}</button>
            </div>
          </form>
          {results.length > 0 && <ul className="profile-list" aria-label="Search results">
            {results.filter((result) => result.id !== user?.id && !blockedIds.has(result.id)).map((result) => {
              const status = friendIds.has(result.id) ? "Friends"
                : outgoingIds.has(result.id) ? "Request sent"
                : incomingIds.has(result.id) ? "Request received" : null;
              return <li key={result.id}>
                <span>{result.username}</span>
                {status ? <span className="profile-status">{status}</span> :
                  <button disabled={busy} onClick={() => act(() => sendFriendRequest(result.id), `Friend request sent to ${result.username}`)}>Add friend</button>}
              </li>;
            })}
          </ul>}
        </section>

        <section className="profile-card" aria-labelledby="friends-title">
          <h2 id="friends-title">Friends <span className="profile-count">{friends.length}</span></h2>
          {loading ? <p className="profile-empty">Loading...</p> : friends.length === 0 ?
            <p className="profile-empty">No friends yet. Search for someone to add.</p> :
            <ul className="profile-list">{friends.map((friend) => <li key={friend.id}>
              <span>{friend.username}</span>
              <div className="profile-actions">
                <button className="profile-secondary" disabled={busy} onClick={() => act(() => removeFriend(friend.id), `${friend.username} removed from friends`)}>Remove</button>
                <button className="profile-secondary" disabled={busy} onClick={() => act(() => blockUser(friend.id), `${friend.username} blocked`)}>Block</button>
              </div>
            </li>)}</ul>}
        </section>

        <section className="profile-card" aria-labelledby="incoming-title">
          <h2 id="incoming-title">Incoming requests <span className="profile-count">{requests.incoming.length}</span></h2>
          {loading ? <p className="profile-empty">Loading...</p> : requests.incoming.length === 0 ?
            <p className="profile-empty">No incoming requests.</p> :
            <ul className="profile-list">{requests.incoming.map((request) => <li key={request.id}>
              <span>{request.user.username}</span>
              <div className="profile-actions">
                <button disabled={busy} onClick={() => act(() => acceptFriendRequest(request.id), `${request.user.username} added as a friend`)}>Accept</button>
                <button className="profile-secondary" disabled={busy} onClick={() => act(() => declineFriendRequest(request.id), "Request declined")}>Decline</button>
                <button className="profile-secondary" disabled={busy} onClick={() => act(() => blockUser(request.user.id), `${request.user.username} blocked`)}>Block</button>
              </div>
            </li>)}</ul>}
        </section>

        <section className="profile-card" aria-labelledby="blocked-title">
          <h2 id="blocked-title">Blocked accounts <span className="profile-count">{blocked.length}</span></h2>
          {loading ? <p className="profile-empty">Loading...</p> : blocked.length === 0 ?
            <p className="profile-empty">No blocked accounts.</p> :
            <ul className="profile-list">{blocked.map((blockedUser) => <li key={blockedUser.id}>
              <span>{blockedUser.username}</span>
              <button className="profile-secondary" disabled={busy} onClick={() => act(() => unblockUser(blockedUser.id), `${blockedUser.username} unblocked`)}>Unblock</button>
            </li>)}</ul>}
        </section>

        <section className="profile-card" aria-labelledby="outgoing-title">
          <h2 id="outgoing-title">Sent requests <span className="profile-count">{requests.outgoing.length}</span></h2>
          {loading ? <p className="profile-empty">Loading...</p> : requests.outgoing.length === 0 ?
            <p className="profile-empty">No pending requests.</p> :
            <ul className="profile-list">{requests.outgoing.map((request) => <li key={request.id}>
              <span>{request.user.username}</span>
              <button className="profile-secondary" disabled={busy} onClick={() => act(() => declineFriendRequest(request.id), "Request cancelled")}>Cancel</button>
            </li>)}</ul>}
        </section>
      </div>
      </main>
      <SiteFooter user={user} onLogout={logout} />
    </div>
  );
}
