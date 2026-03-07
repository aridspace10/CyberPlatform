import React, { useEffect, useState } from "react";
import { getUsers, createUser, updateUser, deleteUser } from "../api/users";

export default function UserManager() {

  const [users, setUsers] = useState([]);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");

  async function loadUsers() {
    const data = await getUsers();
    setUsers(data);
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleCreate() {
    await createUser(username, email);
    loadUsers();
  }

  async function handleDelete(id) {
    await deleteUser(id);
    loadUsers();
  }

  async function handleUpdate(id) {
    const newName = prompt("New username");
    const newEmail = prompt("New email");

    await updateUser(id, newName, newEmail);
    loadUsers();
  }

  return (
    <div>

      <h2>Add User</h2>

      <input
        placeholder="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />

      <input
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <button onClick={handleCreate}>Add</button>

      <h2>Users</h2>

      {users.map((u) => (
        <div key={u.id}>

          {u.username} ({u.email})

          <button onClick={() => handleUpdate(u.id)}>
            Update
          </button>

          <button onClick={() => handleDelete(u.id)}>
            Delete
          </button>

        </div>
      ))}

    </div>
  );
}