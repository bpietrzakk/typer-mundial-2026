import { ProtectedRoute } from '../context/AuthContext';
import { useAuth } from '../hooks/useAuth';
import AuthLoading from './AuthLoading';

// ProtectedRoute with the "waking up the server" spinner while /auth/me runs;
// the redirect to /login (or /register for invites) stays in ProtectedRoute
export default function ProtectedPage({ children }) {
  const { loading } = useAuth();
  if (loading) return <AuthLoading />;
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
