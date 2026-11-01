import { useAuth } from '../hooks/useAuth';

// "/" for everybody: guests get the landing page, logged in players the app
export default function HomeRoute({ guest, children }) {
  const { isLoggedIn, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-10 h-10 border-4 border-brand/30 border-t-brand rounded-full animate-spin" />
      </div>
    );
  }

  return isLoggedIn ? children : guest;
}
