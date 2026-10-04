export const BACKEND_URL = (
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export const API_URL = `${BACKEND_URL}/api`;
export const USERS_URL = `${BACKEND_URL}/users`;
export const WEBSOCKET_URL = BACKEND_URL.replace(/^http/, "ws");
