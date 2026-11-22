import { Navigate } from "react-router-dom";
import { useAuth } from "./useAuth";

export default function ProtectedRoute({ children }) {
  const { user, loading, authError, retryUser } = useAuth();

  if (loading) return <div>Loading...</div>;

  if (!user && authError) {
    return <div role="alert"><p>{authError}</p><button type="button" onClick={() => retryUser().catch(() => {})}>Retry sign-in check</button></div>;
  }

  if (!user) return <Navigate to="/login" />;

  return children;
}
