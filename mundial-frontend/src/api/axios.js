import axios from 'axios';

// single axios instance for the whole app
// withCredentials sends the httpOnly auth cookie automatically
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
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

    if (error.response?.status === 401 && !isAuthCall) {
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export default api;
