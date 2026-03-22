const API = "http://localhost:8000/users";

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

    return await res.json();
}