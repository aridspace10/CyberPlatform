import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./useAuth";

export default function ProtectedRoute({ children }) {
  const { user, loading, authError, retryUser } = useAuth();
  const location = useLocation();

  if (loading) return <div>Loading...</div>;

  if (!user && authError) {
    return <div role="alert"><p>{authError}</p><button type="button" onClick={() => retryUser().catch(() => {})}>Retry sign-in check</button></div>;
  }

  if (!user) {
    const from = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to="/login" state={{ from }} replace />;
  }

  return children;
}
