import { useEffect, useState } from "react";
import { createUser, loginUser } from "../api/users";
import { AuthContext } from "./auth-context";
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

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(
    () => Boolean(localStorage.getItem("token"))
  );

  const API = "http://localhost:8000";

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    setLoading(false);
  };

  // Load user on app start
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) return;

    fetch(`${API}/users/me`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(res => res.json())
      .then(data => {
        setUser(data);
        setLoading(false);
      })
      .catch(() => {
        logout();
      });
  }, []);

  const signup = async (username, email, password, cpassword) => {
    if (!validator.isEmail(email)) {
        return "Email given is not valid"
    }

    if (username.length < 4) {
        return "Username must be at least 4 characters"
    }

    if (!schema.validate(password)) {
        return "Password Invalid"
    }

    if (password !== cpassword) {
        return "Password and Confirm Password are not the same"
    }
    const data = await createUser(username, email, password);
    return data
  }


  const login = async (username, password) => {
    const data = await loginUser(username, password);

    localStorage.setItem("token", data.access_token);

    // fetch user after login
    const meRes = await fetch(`${API}/users/me`, {
      headers: {
        Authorization: `Bearer ${data.access_token}`
      }
    });

    const userData = await meRes.json();
    setUser(userData);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, signup }}>
      {children}
    </AuthContext.Provider>
  );
}
