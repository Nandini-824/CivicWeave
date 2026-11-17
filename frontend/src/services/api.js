import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export const authAPI = {
  register: (data) => api.post('/api/auth/register', data),
  login: (email, password) => {
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);
    return api.post('/api/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
  me: () => api.get('/api/auth/me'),
};

export const complaintAPI = {
  create: (data) => api.post('/api/complaints', data),
  my: () => api.get('/api/complaints/my'),
  get: (id) => api.get(`/api/complaints/${id}`),
  timeline: (id) => api.get(`/api/complaints/${id}/timeline`),
  uploadImage: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/api/complaints/upload-image', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  feedback: (id, data) => api.post(`/api/complaints/${id}/feedback`, data),
  list: () => api.get('/api/complaints'),
  updateStatus: (id, data) => api.patch(`/api/complaints/${id}/status`, data),
};

export const aiAPI = {
  classify: (data) => api.post('/api/ai/classify', data),
  analyze: (data) => api.post('/api/ai/analyze-complaint', data),
  findRelated: (data) => api.post('/api/ai/find-related', data),
};

export const incidentAPI = {
  list: (params) => api.get('/api/incidents', { params }),
  get: (id) => api.get(`/api/incidents/${id}`),
  nearby: (params) => api.get('/api/incidents/nearby', { params }),
  mapData: (params) => api.get('/api/incidents/map-data', { params }),
  support: (id) => api.post(`/api/incidents/${id}/support`),
  withdrawSupport: (id) => api.delete(`/api/incidents/${id}/support`),
  updatePriority: (id, data) => api.patch(`/api/incidents/${id}/priority`, data),
  updateStatus: (id, data) => api.patch(`/api/incidents/${id}/status`, data),
};

export const officerAPI = {
  dashboard: () => api.get('/api/officer/dashboard'),
  complaints: () => api.get('/api/officer/complaints'),
  incidents: (params) => api.get('/api/officer/incidents', { params }),
  candidates: () => api.get('/api/officer/incident-candidates'),
  confirmLink: (id) => api.post(`/api/officer/incident-links/${id}/confirm`),
  rejectLink: (id) => api.post(`/api/officer/incident-links/${id}/reject`),
};

export const adminAPI = {
  dashboard: () => api.get('/api/admin/dashboard'),
  departments: () => api.get('/api/admin/departments'),
  createDepartment: (data) => api.post('/api/admin/departments', data),
  updateDepartment: (id, data) => api.patch(`/api/admin/departments/${id}`, data),
  officers: () => api.get('/api/admin/officers'),
  createOfficer: (data) => api.post('/api/admin/officers', data),
  jurisdictions: () => api.get('/api/admin/jurisdictions'),
  createJurisdiction: (data) => api.post('/api/admin/jurisdictions', data),
  complaints: () => api.get('/api/admin/complaints'),
  incidents: () => api.get('/api/admin/incidents'),
};

export const notificationAPI = {
  list: () => api.get('/api/notifications'),
  markRead: (id) => api.patch(`/api/notifications/${id}/read`),
};

export default api;
