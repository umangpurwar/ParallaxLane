import axios from 'axios';
import router from '../router';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

export const STAFF_ROLES = ['owner', 'admin', 'invigilator'];

const ORG_KEYS = ['org_slug', 'org_role', 'org_name', 'org_plan'];
const SESSION_KEYS = [
  'access_token', 'refresh_token', 'org_role', 'org_slug', 'org_name', 'org_plan',
  'user_email', 'display_name', 'username', 'email',
];

let isRefreshing = false;
let pendingRequests = [];

const processQueue = (error, token = null) => {
  pendingRequests.forEach(p => {
    if (error) p.reject(error);
    else p.resolve(token);
  });
  pendingRequests = [];
};

/** Remove active organisation context (Org Home is the only place that sets it). */
export const clearOrgContext = () => {
  ORG_KEYS.forEach((key) => localStorage.removeItem(key));
};

/** Persist JWT + user identity only. Never stores organisation context. */
export const setSessionData = (data) => {
  if (!data) return;

  if (data.access) localStorage.setItem('access_token', data.access);
  if (data.refresh) localStorage.setItem('refresh_token', data.refresh);

  const email = data.email;
  const displayName = data.display_name || data.username || email;

  if (email) {
    localStorage.setItem('user_email', email);
    localStorage.setItem('email', email);
  }
  if (displayName) {
    localStorage.setItem('display_name', displayName);
    localStorage.setItem('username', displayName);
  }

  clearOrgContext();
};

/** Persist organisation context after explicit selection on Org Home. */
export const setOrgContext = (data) => {
  if (!data) return;

  const orgSlug = data.org_slug || data.slug;
  const orgRole = data.org_role || data.role;
  const orgName = data.org_name || data.name;
  const orgPlan = data.org_plan || data.plan;

  if (orgSlug) localStorage.setItem('org_slug', orgSlug);
  if (orgRole) localStorage.setItem('org_role', orgRole);
  if (orgName) localStorage.setItem('org_name', orgName);
  if (orgPlan) localStorage.setItem('org_plan', orgPlan);
};

/** @deprecated Use setSessionData or setOrgContext explicitly. */
export const setAuthData = (data) => {
  setSessionData(data);
  const orgSlug = data?.org_slug || data?.slug;
  if (orgSlug) setOrgContext(data);
};

/** After login / register / OAuth — always land on Org Home. */
export const redirectAfterAuth = (router) => {
  router.push('/org-home');
};

/** Route to the correct dashboard after the user picks an organisation on Org Home. */
export const redirectAfterOrgSelect = (router, role) => {
  if (STAFF_ROLES.includes(role)) {
    router.push('/admin');
  } else {
    router.push('/dashboard');
  }
};

/** Leave current dashboard and return to Org Home to pick another organisation. */
export const goToOrgHome = (router) => {
  clearOrgContext();
  router.push('/org-home');
};

export const logout = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  try {
    if (refreshToken) {
      await api.post('accounts/logout/', { refresh: refreshToken });
    }
  } catch {
    // proceed with local cleanup even if server logout fails
  }
  clearAuthData();
};

export const clearAuthData = () => {
  SESSION_KEYS.forEach((key) => localStorage.removeItem(key));
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
      const base = api.defaults.baseURL;
      const refreshURL = base.endsWith('/') ? `${base}token/refresh/` : `${base}/token/refresh/`;

      const response = await axios.post(refreshURL, { refresh: refreshToken });

      const newAccessToken = response.data.access;
      const newRefreshToken = response.data.refresh;

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
