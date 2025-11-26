import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { RegisterData, AuthResponse, User, PurchaseRequest } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Extend AxiosRequestConfig to include _retry
interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as CustomAxiosRequestConfig;
    
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post<AuthResponse>(`${API_BASE_URL}/auth/refresh/`, {
          refresh: refreshToken,
        });
        
        const { access } = response.data;
        localStorage.setItem('access_token', access);
        
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (username: string, password: string) =>
    api.post<AuthResponse>('/auth/login/', { username, password }),
  register: (data: RegisterData) => api.post<AuthResponse>('/auth/register/', data),
  getProfile: () => api.get<User>('/auth/profile/'),
};

export const requestsAPI = {
  list: (params?: { status?: string }) => 
    api.get<{ results: PurchaseRequest[] } | PurchaseRequest[]>('/requests/', { params }),
  get: (id: string) => api.get<PurchaseRequest>(`/requests/${id}/`),
  create: (data: Partial<PurchaseRequest>) => api.post<PurchaseRequest>('/requests/', data),
  update: (id: string, data: Partial<PurchaseRequest>) => 
    api.put<PurchaseRequest>(`/requests/${id}/`, data),
  delete: (id: string) => api.delete(`/requests/${id}/`),
  approve: (id: string, comments: string) =>
    api.post<PurchaseRequest>(`/requests/${id}/approve/`, { comments }),
  reject: (id: string, comments: string) =>
    api.post<PurchaseRequest>(`/requests/${id}/reject/`, { comments }),
  cancel: (id: string, comments: string) =>
    api.post<PurchaseRequest>(`/requests/${id}/cancel/`, { comments }),
  submitProforma: (id: string, file: File) => {
    const formData = new FormData();
    formData.append('proforma', file);
    return api.post<{ message: string; extracted_data?: any }>(
      `/requests/${id}/submit_proforma/`, 
      formData, 
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
  },
  submitReceipt: (id: string, file: File) => {
    const formData = new FormData();
    formData.append('receipt', file);
    return api.post<{ message: string; validation_result?: any }>(
      `/requests/${id}/submit_receipt/`, 
      formData, 
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
  },
  downloadProforma: (id: string) => 
    api.get(`/requests/${id}/download_proforma/`, { responseType: 'blob' }),
  downloadReceipt: (id: string) => 
    api.get(`/requests/${id}/download_receipt/`, { responseType: 'blob' }),
  downloadPurchaseOrder: (id: string) => 
    api.get(`/requests/${id}/download_purchase_order/`, { responseType: 'blob' }),
};

export default api;

