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

// response interceptor — redirect to login on 401
// skip redirect for /auth/me and /auth/refresh (expected to 401 when not logged in)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    const isAuthCheck = url.includes('/auth/me') || url.includes('/auth/refresh');

    if (error.response?.status === 401 && !isAuthCheck) {
      // push to login without hard reload — preserves React state
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export default api;
