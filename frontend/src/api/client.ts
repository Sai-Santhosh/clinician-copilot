import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          useAuthStore.getState().updateTokens(access_token, refresh_token);

          // Retry original request
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // Refresh failed, logout
          useAuthStore.getState().logout();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token, logout
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// API helper functions
export const api = {
  // Auth
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password });
    return response.data;
  },

  refreshToken: async (refreshToken: string) => {
    const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },

  getMe: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  // Patients
  getPatients: async (search?: string) => {
    const params = search ? { search } : {};
    const response = await apiClient.get('/patients', { params });
    return response.data;
  },

  getPatient: async (id: number) => {
    const response = await apiClient.get(`/patients/${id}`);
    return response.data;
  },

  createPatient: async (data: { name: string; external_id?: string; dob?: string }) => {
    const response = await apiClient.post('/patients', data);
    return response.data;
  },

  updatePatient: async (id: number, data: { name?: string; external_id?: string; dob?: string }) => {
    const response = await apiClient.put(`/patients/${id}`, data);
    return response.data;
  },

  // Sessions
  getPatientSessions: async (patientId: number) => {
    const response = await apiClient.get(`/sessions/patients/${patientId}/sessions`);
    return response.data;
  },

  getSession: async (id: number) => {
    const response = await apiClient.get(`/sessions/${id}`);
    return response.data;
  },

  getSessionTranscript: async (id: number) => {
    const response = await apiClient.get(`/sessions/${id}/transcript`);
    return response.data;
  },

  createSession: async (patientId: number, transcript: string) => {
    const response = await apiClient.post(`/sessions/patients/${patientId}/sessions`, {
      transcript,
    });
    return response.data;
  },

  generateAiSuggestions: async (sessionId: number, options?: {
    prompt_version?: string;
    model_name?: string;
    mode?: 'full' | 'safe';
    temperature?: number;
  }) => {
    const response = await apiClient.post(`/sessions/${sessionId}/generate`, options || {});
    return response.data;
  },

  getSessionSuggestions: async (sessionId: number) => {
    const response = await apiClient.get(`/sessions/${sessionId}/suggestions`);
    return response.data;
  },

  // Note versions
  getSessionVersions: async (sessionId: number) => {
    const response = await apiClient.get(`/notes/sessions/${sessionId}/versions`);
    return response.data;
  },

  getVersion: async (versionId: number) => {
    const response = await apiClient.get(`/notes/versions/${versionId}`);
    return response.data;
  },

  updateVersion: async (versionId: number, data: {
    soap_json?: string;
    dx_json?: string;
    meds_json?: string;
    safety_json?: string;
  }) => {
    const response = await apiClient.put(`/notes/versions/${versionId}`, data);
    return response.data;
  },

  finalizeVersion: async (versionId: number) => {
    const response = await apiClient.post(`/notes/versions/${versionId}/finalize`);
    return response.data;
  },

  rollbackVersion: async (sessionId: number, targetVersionId: number) => {
    const response = await apiClient.post(`/notes/sessions/${sessionId}/rollback`, {
      target_version_id: targetVersionId,
    });
    return response.data;
  },

  // Audit logs (admin only)
  getAuditLogs: async (params?: {
    actor_user_id?: number;
    entity_type?: string;
    entity_id?: number;
    action?: string;
    limit?: number;
    offset?: number;
  }) => {
    const response = await apiClient.get('/audit/logs', { params });
    return response.data;
  },
};
