import axios from 'axios';
import { loginUrlWithNext } from '../utils/nextPath';

// single axios instance for the whole app
// withCredentials sends the httpOnly auth cookie automatically
const api = axios.create({
  // '/api' = vite dev proxy / vercel rewrite / nginx, all strip the prefix
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// response interceptor — redirect to login on 401 for protected pages.
// skip ALL /auth/* calls: those handle their own errors in the page
// (e.g. a 401 on login means bad credentials — show the message, don't
// hard-reload to /login which would wipe the error before it renders)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    const isAuthCall = url.includes('/auth/');
    // public calls made on guest pages (invite preview) handle errors themselves
    const skipRedirect = Boolean(error.config?.skipAuthRedirect);

    // keep the page in ?next= so login brings the player back to it
    const onLogin = window.location.pathname.startsWith('/login');
    if (error.response?.status === 401 && !isAuthCall && !skipRedirect && !onLogin) {
      window.location.href = loginUrlWithNext();
    }

    return Promise.reject(error);
  }
);

export default api;
