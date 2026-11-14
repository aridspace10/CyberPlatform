import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import {
  acceptFriendRequest, declineFriendRequest, getFriendRequests, getFriends,
  removeFriend, searchUsers, sendFriendRequest,
} from "../../api/users";
import "./Profile.css";

export default function Profile() {
  const { user } = useAuth();
  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState({ incoming: [], outgoing: [] });
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    const [nextFriends, nextRequests] = await Promise.all([getFriends(), getFriendRequests()]);
    setFriends(nextFriends);
    setRequests(nextRequests);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getFriends(), getFriendRequests()])
      .then(([nextFriends, nextRequests]) => {
        if (!active) return;
        setFriends(nextFriends);
        setRequests(nextRequests);
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

  return (
    <main className="profile-page">
      <header className="profile-header">
        <Link className="profile-back" to="/">← Home</Link>
        <h1>Profile &amp; Friends</h1>
        <p>Signed in as <strong>{user?.username}</strong></p>
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
            {results.filter((result) => result.id !== user?.id).map((result) => {
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
              <button className="profile-secondary" disabled={busy} onClick={() => act(() => removeFriend(friend.id), `${friend.username} removed from friends`)}>Remove</button>
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
              </div>
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
  );
}
