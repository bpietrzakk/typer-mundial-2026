import { useState, useEffect, useCallback } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import * as authApi from '../api/auth';
import { isInvitePath } from '../utils/pendingInvite';
import { AuthContext, useAuth } from '../hooks/useAuth';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true until initial /auth/me resolves

  // on mount — check if the user is already logged in (cookie still valid).
  // the backend renews a day-old cookie on any request, so no refresh timer here
  useEffect(() => {
    authApi.getMe()
      .then((u) => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

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

  const updateUser = useCallback((updated) => {
    setUser((prev) => ({ ...prev, ...updated }));
  }, []);

  const value = {
    user,
    login,
    register,
    logout,
    updateUser,
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
        <div className="w-10 h-10 border-4 border-brand/30 border-t-brand rounded-full animate-spin" />
      </div>
    );
  }

  if (!isLoggedIn) {
    // save where the user wanted to go so we can redirect after login.
    // invite links go to sign-up first — invited friends rarely have an account
    const target = isInvitePath(location.pathname) ? '/register' : '/login';
    return <Navigate to={target} state={{ from: location }} replace />;
  }

  return children;
}
