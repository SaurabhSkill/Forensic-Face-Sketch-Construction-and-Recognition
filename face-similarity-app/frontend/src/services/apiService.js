import axios from 'axios';
import { API_BASE_URL } from '../config';

// Configure axios to automatically include auth token in all requests (except login endpoints)
axios.interceptors.request.use(
  (config) => {
    // Don't add token to login/register endpoints
    const isAuthEndpoint = config.url?.includes('/api/auth/');
    
    if (!isAuthEndpoint) {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle 401 errors (expired/invalid token)
axios.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token expired or invalid
      const isAuthEndpoint = error.config?.url?.includes('/api/auth/');
      
      // Only redirect if not already on auth endpoint
      if (!isAuthEndpoint) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        
        // Show alert and redirect to login
        alert('Your session has expired. Please login again.');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// API Service functions
export const apiService = {
  // Face comparison
  compareFaces: async (sketchFile, photoFile) => {
    const formData = new FormData();
    formData.append('sketch', sketchFile);
    formData.append('photo', photoFile);

    const response = await axios.post(`${API_BASE_URL}/api/compare`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000, // 300 second timeout (5 minutes)
    });

    return response.data;
  },

  // Criminal database operations
  getCriminals: async () => {
    const response = await axios.get(`${API_BASE_URL}/api/criminals`);
    return response.data.criminals || [];
  },

  addCriminal: async (formData) => {
    const submitData = new FormData();
    submitData.append('photo', formData.photo);
    
    const profileData = {
      criminal_id: formData.criminal_id,
      status: formData.status,
      full_name: formData.full_name,
      aliases: formData.aliases,
      dob: formData.dob,
      sex: formData.sex,
      nationality: formData.nationality,
      ethnicity: formData.ethnicity,
      appearance: formData.appearance,
      locations: formData.locations,
      summary: formData.summary,
      forensics: formData.forensics,
      evidence: formData.evidence,
      witness: formData.witness
    };
    
    submitData.append('data', JSON.stringify(profileData));
    
    const response = await axios.post(
      `${API_BASE_URL}/api/criminals`,
      submitData,
      {
        headers: { 
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return response.data;
  },

  deleteCriminal: async (criminalId) => {
    const response = await axios.delete(`${API_BASE_URL}/api/criminals/${criminalId}`);
    return response.data;
  },

  searchCriminals: async (sketchFile, threshold = '0.6') => {
    const formData = new FormData();
    formData.append('sketch', sketchFile);
    formData.append('threshold', threshold);

    const response = await axios.post(`${API_BASE_URL}/api/criminals/search`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000, // 300 second timeout (5 minutes)
    });

    return response.data;
  },

  getCriminalPhotoUrl: (criminalId) => {
    return `${API_BASE_URL}/api/criminals/${criminalId}/photo`;
  }
};
