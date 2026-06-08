import api from './axios';

// login — backend sets JWT in httpOnly cookie
export const login = async (email, password) => {
  const res = await api.post('/auth/login', { email, password });
  return res.data;
};

// register — auto-login (backend sets cookie on register too)
export const register = async (nick, email, password) => {
  const res = await api.post('/auth/register', { nick, email, password });
  return res.data;
};

// logout — backend clears the cookie
export const logout = async () => {
  await api.post('/auth/logout');
};

// refresh — get a fresh token before the old one expires
export const refresh = async () => {
  const res = await api.post('/auth/refresh');
  return res.data;
};

// check if user is still logged in (cookie valid?)
export const getMe = async () => {
  const res = await api.get('/auth/me');
  return res.data;
};

// confirm account from the email link (?token=...)
export const verifyEmail = async (token) => {
  const res = await api.post('/auth/verify-email', { token });
  return res.data;
};

// ask for a fresh verification email
export const resendVerification = async (email) => {
  await api.post('/auth/resend-verification', { email });
};

// request a password reset link
export const forgotPassword = async (email) => {
  await api.post('/auth/forgot-password', { email });
};

// set a new password using the token from the reset link
export const resetPassword = async (token, password) => {
  await api.post('/auth/reset-password', { token, password });
};
