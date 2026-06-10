import axios from 'axios';
import router from '../router';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

let isRefreshing = false;
let pendingRequests = [];

const processQueue = (error, token = null) => {
  pendingRequests.forEach(p => {
    if (error) p.reject(error);
    else p.resolve(token);
  });
  pendingRequests = [];
};

export const setAuthData = (data) => {
  if (data?.access)        localStorage.setItem('access_token', data.access);
  if (data?.refresh)       localStorage.setItem('refresh_token', data.refresh);
  if (data?.org_role)      localStorage.setItem('org_role', data.org_role);
  if (data?.org_slug)      localStorage.setItem('org_slug', data.org_slug);
  if (data?.email)         localStorage.setItem('user_email', data.email);
  if (data?.display_name)  localStorage.setItem('display_name', data.display_name);
};

export const clearAuthData = () => {
  ['access_token', 'refresh_token', 'org_role', 'org_slug', 'user_email', 'display_name']
    .forEach(key => localStorage.removeItem(key));
};

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (!error.response || error.response.status !== 401) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      clearAuthData();
      router.replace('/login');
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      clearAuthData();
      router.replace('/login');
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingRequests.push({ resolve, reject });
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    isRefreshing = true;

    try {
      // FIX: correct URL construction (no double slash, no missing slash)
      const base = api.defaults.baseURL;
      const refreshURL = base.endsWith('/') ? `${base}token/refresh/` : `${base}/token/refresh/`;

      const response = await axios.post(refreshURL, { refresh: refreshToken });

      const newAccessToken = response.data.access;
      const newRefreshToken = response.data.refresh; // FIX: save rotated refresh token

      localStorage.setItem('access_token', newAccessToken);
      if (newRefreshToken) localStorage.setItem('refresh_token', newRefreshToken);

      api.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`;
      processQueue(null, newAccessToken);

      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);

    } catch (refreshError) {
      processQueue(refreshError, null);
      clearAuthData();
      router.replace('/login');
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;