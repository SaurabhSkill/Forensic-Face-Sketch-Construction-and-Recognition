import axios from 'axios';

// Ensure the API_URL ends with '/api' if the env variable doesn't include it
const baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001';
const API_URL = baseUrl.endsWith('/api') ? baseUrl : `${baseUrl}/api`;

// Create a configured axios instance
const api = axios.create({
  baseURL: API_URL,
});

// Add request interceptor to inject token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle unauthorized errors (token expired, etc.)
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Service to handle Case Management API requests
 */
const caseService = {
  /**
   * Get all cases for the current user (or all if admin)
   */
  getAllCases: async () => {
    const response = await api.get('/cases');
    return response.data;
  },

  /**
   * Get details for a specific case
   */
  getCaseById: async (caseId) => {
    const response = await api.get(`/cases/${caseId}`);
    return response.data;
  },

  /**
   * Create a new case
   */
  createCase: async (caseData) => {
    const response = await api.post('/cases', caseData);
    return response.data;
  },

  /**
   * Update an existing case
   */
  updateCase: async (caseId, updateData) => {
    const response = await api.put(`/cases/${caseId}`, updateData);
    return response.data;
  },

  /**
   * Delete a case
   */
  deleteCase: async (caseId) => {
    const response = await api.delete(`/cases/${caseId}`);
    return response.data;
  },

  /**
   * Get notes for a specific case
   */
  getCaseNotes: async (caseId) => {
    const response = await api.get(`/cases/${caseId}/notes`);
    return response.data;
  },

  /**
   * Add a note to a case
   */
  createCaseNote: async (caseId, noteData) => {
    const response = await api.post(`/cases/${caseId}/notes`, noteData);
    return response.data;
  }
};

export default caseService;
