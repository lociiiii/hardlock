import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('hardlock_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('hardlock_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export const authApi = {
  register: (email, password) =>
    api.post('/auth/register', { email, password }),
  login: (email, password) =>
    api.post('/auth/login', { email, password }),
};

export const appsApi = {
  list: () => api.get('/apps'),
  create: (name, description) =>
    api.post('/apps', { name, description }),
  get: (id) => api.get(`/apps/${id}`),
};

export const licensesApi = {
  generate: (app_id, count = 1, max_devices = 1, expires_at = null) =>
    api.post('/licenses/generate', { app_id, count, max_devices, expires_at }),
  get: (key) => api.get(`/licenses/${key}`),
  revoke: (key) => api.post(`/licenses/${key}/revoke`),
};

export const adminApi = {
  stats: () => api.get('/admin/stats'),
  logs: (page = 1, limit = 50) =>
    api.get('/admin/logs', { params: { page, limit } }),
};

export default api;
