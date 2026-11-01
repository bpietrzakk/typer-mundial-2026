import { createContext, useContext } from 'react';

// auth context object lives here (not in AuthContext.jsx) so fast refresh
// keeps working — a .jsx file should only export components
export const AuthContext = createContext(null);

// hook for components to consume auth state
export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
};
