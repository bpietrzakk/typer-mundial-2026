import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import * as authApi from '../api/auth';

const AuthContext = createContext(null);

// hook for components to consume auth state
export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true until initial /auth/me resolves

  // on mount — check if the user is already logged in (cookie still valid)
  useEffect(() => {
    authApi.getMe()
      .then((u) => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  // periodic token refresh — every 6 days (cookie lives 7 days)
  useEffect(() => {
    if (!user) return;
    const SIX_DAYS_MS = 6 * 24 * 60 * 60 * 1000;
    const interval = setInterval(() => {
      authApi.refresh().catch(() => {
        // refresh failed — session expired, force re-login
        setUser(null);
      });
    }, SIX_DAYS_MS);
    return () => clearInterval(interval);
  }, [user]);

  const login = useCallback(async (email, password) => {
    const u = await authApi.login(email, password);
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (nick, email, password) => {
    await authApi.register(nick, email, password);
    // register only sets an auth cookie when email verification is NOT
    // required. probe /auth/me to find out which mode the backend is in:
    // success -> we're logged in; 401 -> must verify the email first.
    try {
      const me = await authApi.getMe();
      setUser(me);
      return { verified: true };
    } catch {
      setUser(null);
      return { verified: false };
    }
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const value = {
    user,
    login,
    register,
    logout,
    isLoggedIn: !!user,
    loading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// wrapper component that redirects unauthenticated users to /login
export function ProtectedRoute({ children }) {
  const { isLoggedIn, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    // show a centered spinner while checking auth status
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-10 h-10 border-4 border-mundial-teal/30 border-t-mundial-teal rounded-full animate-spin" />
      </div>
    );
  }

  if (!isLoggedIn) {
    // save where the user wanted to go so we can redirect after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
