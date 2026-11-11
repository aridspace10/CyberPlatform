import { USERS_URL } from "./config";

const API = USERS_URL;

export async function getUsers() {
  const res = await fetch(API);
  return await res.json();
}

export async function createUser(username, email, password) {
  const res = await fetch(API + "/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password })
  });

  return await res.json();
}

export async function updateUser(id, username, email) {
  const res = await fetch(`${API}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email })
  });

  return await res.json();
}

export async function deleteUser(id) {
  await fetch(`${API}/${id}`, {
    method: "DELETE"
  });
}

export async function loginUser(username, password) {
    const res = await fetch(API + "/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || "Could not sign in");
    }
    return data;
}

async function friendRequest(path, options = {}) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
    },
  });

  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Friend action failed");
  return data;
}

export const searchUsers = (query) =>
  friendRequest(`/search?query=${encodeURIComponent(query)}`);

export const getFriends = () => friendRequest("/me/friends");

export const getFriendRequests = () => friendRequest("/me/friend-requests");

export const sendFriendRequest = (userId) =>
  friendRequest("/me/friend-requests", {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });

export const acceptFriendRequest = (requestId) =>
  friendRequest(`/me/friend-requests/${requestId}/accept`, { method: "POST" });

export const declineFriendRequest = (requestId) =>
  friendRequest(`/me/friend-requests/${requestId}`, { method: "DELETE" });

export const removeFriend = (userId) =>
  friendRequest(`/me/friends/${userId}`, { method: "DELETE" });
