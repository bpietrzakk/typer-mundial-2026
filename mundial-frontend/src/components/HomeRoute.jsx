import { useAuth } from '../hooks/useAuth';
import AuthLoading from './AuthLoading';

// "/" for everybody: guests get the landing page, logged in players the app
export default function HomeRoute({ guest, children }) {
  const { isLoggedIn, loading } = useAuth();

  if (loading) return <AuthLoading />;

  return isLoggedIn ? children : guest;
}
