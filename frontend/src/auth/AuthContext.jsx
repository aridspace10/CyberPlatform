import { useCallback, useEffect, useRef, useState } from "react";
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
  if (!response.ok) {
    const error = new Error(response.status === 401
      ? "Your sign-in has expired"
      : "Could not check your sign-in. Please retry.");
    error.status = response.status;
    throw error;
  }

  const user = await response.json();
  if (!Number.isInteger(user?.id)) throw new Error("Invalid user response");
  return user;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(
    () => Boolean(localStorage.getItem("token"))
  );
  const requestId = useRef(0);

  const logout = useCallback(() => {
    requestId.current += 1;
    localStorage.removeItem("token");
    setUser(null);
    setAuthError("");
    setLoading(false);
  }, []);

  const loadUser = useCallback(async (token) => {
    const id = ++requestId.current;
    setLoading(true);
    setAuthError("");
    try {
      const currentUser = await getCurrentUser(token);
      if (id === requestId.current) setUser(currentUser);
      return currentUser;
    } catch (error) {
      if (id === requestId.current) {
        if (error.status === 401) logout();
        else setAuthError("Could not check your sign-in. Please retry.");
      }
      throw error;
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [logout]);

  const retryUser = useCallback(() => {
    const token = localStorage.getItem("token");
    return token ? loadUser(token) : Promise.reject(new Error("No saved sign-in"));
  }, [loadUser]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) loadUser(token).catch(() => {});
  }, [loadUser]);

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
    return loadUser(data.access_token);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, signup, authError, retryUser }}>
      {children}
    </AuthContext.Provider>
  );
}
