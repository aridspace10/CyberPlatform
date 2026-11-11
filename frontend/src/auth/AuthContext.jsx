import { useCallback, useEffect, useState } from "react";
import { createUser, loginUser } from "../api/users";
import { AuthContext } from "./auth-context";
import { BACKEND_URL } from "../api/config";
import validator from 'validator';
import passwordValidator from 'password-validator';

const schema = new passwordValidator();
schema
  .min(8)
  .max(100)
  .uppercase()
  .lowercase()
  .digits(1)
  .symbols(1)
  .not().spaces()
  .not().oneOf(['Password1', 'Password!']);

async function getCurrentUser(token) {
  const response = await fetch(`${BACKEND_URL}/users/me`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) throw new Error("Your sign-in has expired");

  const user = await response.json();
  if (!Number.isInteger(user?.id)) throw new Error("Invalid user response");
  return user;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(
    () => Boolean(localStorage.getItem("token"))
  );

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
    setLoading(false);
  }, []);

  // Load user on app start
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) return;

    getCurrentUser(token)
      .then(currentUser => {
        setUser(currentUser);
        setLoading(false);
      })
      .catch(logout);
  }, [logout]);

  const signup = async (username, email, password, cpassword) => {
    if (!validator.isEmail(email)) {
        return "Email given is not valid"
    }

    if (username.length < 4) {
        return "Username must be at least 4 characters"
    }

    if (!schema.validate(password)) {
        return "Password must be 8–100 characters with uppercase and lowercase letters, a number, and a symbol (no spaces)"
    }

    if (password !== cpassword) {
        return "Password and Confirm Password are not the same"
    }
    return await createUser(username, email, password);
  }


  const login = async (username, password) => {
    const data = await loginUser(username, password);

    localStorage.setItem("token", data.access_token);

    try {
      setUser(await getCurrentUser(data.access_token));
    } catch (error) {
      logout();
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, signup }}>
      {children}
    </AuthContext.Provider>
  );
}
