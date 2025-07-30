/**
 * API Service for MintFlow Mobile App
 * Handles all HTTP requests with authentication, error handling, and retry logic
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import Config from '../config';

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  status?: number;
}

class ApiService {
  private baseURL: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private isRefreshingToken = false;
  private failedQueue: Array<{
    resolve: (value: string) => void;
    reject: (reason: any) => void;
  }> = [];

  constructor() {
    this.baseURL = Config.API_BASE_URL;
    this.loadTokens();
  }

  private async loadTokens(): Promise<void> {
    try {
      const [accessToken, refreshToken] = await Promise.all([
        AsyncStorage.getItem('access_token'),
        AsyncStorage.getItem('refresh_token'),
      ]);
      
      this.accessToken = accessToken;
      this.refreshToken = refreshToken;
    } catch (error) {
      console.error('Failed to load tokens from storage:', error);
    }
  }

  private async saveTokens(accessToken: string, refreshToken?: string): Promise<void> {
    try {
      this.accessToken = accessToken;
      await AsyncStorage.setItem('access_token', accessToken);
      
      if (refreshToken) {
        this.refreshToken = refreshToken;
        await AsyncStorage.setItem('refresh_token', refreshToken);
      }
    } catch (error) {
      console.error('Failed to save tokens to storage:', error);
    }
  }

  private async clearTokens(): Promise<void> {
    try {
      this.accessToken = null;
      this.refreshToken = null;
      await Promise.all([
        AsyncStorage.removeItem('access_token'),
        AsyncStorage.removeItem('refresh_token'),
      ]);
    } catch (error) {
      console.error('Failed to clear tokens from storage:', error);
    }
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': `MintFlow-Mobile/${Config.APP_VERSION} (${Platform.OS})`,
    };

    if (this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }

    return headers;
  }

  private async refreshAccessToken(): Promise<string> {
    if (this.isRefreshingToken) {
      // If already refreshing, queue the request
      return new Promise((resolve, reject) => {
        this.failedQueue.push({ resolve, reject });
      });
    }

    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    this.isRefreshingToken = true;

    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: this.refreshToken,
        }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      const newAccessToken = data.access_token;
      const newRefreshToken = data.refresh_token;

      await this.saveTokens(newAccessToken, newRefreshToken);

      // Resolve all queued requests
      this.failedQueue.forEach(({ resolve }) => resolve(newAccessToken));
      this.failedQueue = [];

      return newAccessToken;
    } catch (error) {
      // Reject all queued requests
      this.failedQueue.forEach(({ reject }) => reject(error));
      this.failedQueue = [];

      // Clear tokens and redirect to login
      await this.clearTokens();
      throw error;
    } finally {
      this.isRefreshingToken = false;
    }
  }

  private async makeRequest<T>(
    url: string,
    options: RequestInit,
    retryCount = 0
  ): Promise<ApiResponse<T>> {
    const maxRetries = 3;
    const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;

    try {
      const response = await fetch(fullUrl, {
        ...options,
        headers: {
          ...this.getHeaders(),
          ...options.headers,
        },
      });

      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && this.refreshToken && retryCount === 0) {
        try {
          await this.refreshAccessToken();
          return this.makeRequest(url, options, retryCount + 1);
        } catch (refreshError) {
          await this.clearTokens();
          throw new ApiError('Authentication failed', 'AUTHENTICATION_FAILED');
        }
      }

      // Handle other HTTP errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.message || `HTTP ${response.status}`,
          errorData.code || 'HTTP_ERROR',
          errorData.details,
          response.status
        );
      }

      const data = await response.json();
      return {
        data,
        status: response.status,
        message: data.message,
      };
    } catch (error) {
      // Retry on network errors
      if (retryCount < maxRetries && this.isNetworkError(error)) {
        await this.delay(Math.pow(2, retryCount) * 1000); // Exponential backoff
        return this.makeRequest(url, options, retryCount + 1);
      }

      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError(
        'Network request failed',
        'NETWORK_ERROR',
        error
      );
    }
  }

  private isNetworkError(error: any): boolean {
    return (
      error instanceof TypeError ||
      error.name === 'NetworkError' ||
      error.code === 'NETWORK_REQUEST_FAILED'
    );
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Public API methods
  async get<T>(url: string): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(url, {
      method: 'GET',
    });
  }

  async post<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(url, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(url, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(url, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(url: string): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(url, {
      method: 'DELETE',
    });
  }

  async upload<T>(url: string, file: FormData): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(url, {
      method: 'POST',
      body: file,
      headers: {
        // Don't set Content-Type for FormData, let the browser set it
      },
    });
  }

  // Authentication methods
  async login(email: string, password: string): Promise<ApiResponse<any>> {
    const response = await this.post('/auth/login', { email, password });
    
    if (response.data.access_token) {
      await this.saveTokens(
        response.data.access_token,
        response.data.refresh_token
      );
    }
    
    return response;
  }

  async logout(): Promise<void> {
    try {
      if (this.accessToken) {
        await this.post('/auth/logout');
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      await this.clearTokens();
    }
  }

  async register(userData: {
    email: string;
    password: string;
    confirm_password: string;
    full_name: string;
    phone_number?: string;
    consent_given: boolean;
  }): Promise<ApiResponse<any>> {
    return this.post('/auth/register', userData);
  }

  async verifyEmail(token: string): Promise<ApiResponse<any>> {
    return this.post('/auth/verify-email', { token });
  }

  async resetPassword(email: string): Promise<ApiResponse<any>> {
    return this.post('/auth/reset-password', { email });
  }

  async confirmPasswordReset(
    token: string,
    newPassword: string,
    confirmPassword: string
  ): Promise<ApiResponse<any>> {
    return this.post('/auth/reset-password/confirm', {
      token,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
  }

  // MFA methods
  async setupMFA(password: string): Promise<ApiResponse<any>> {
    return this.post('/auth/mfa/setup', { password });
  }

  async verifyMFA(totpCode: string): Promise<ApiResponse<any>> {
    return this.post('/auth/mfa/verify', { totp_code: totpCode });
  }

  async disableMFA(password: string, totpCode: string): Promise<ApiResponse<any>> {
    return this.post('/auth/mfa/disable', {
      password,
      totp_code: totpCode,
    });
  }

  // User profile methods
  async getUserProfile(): Promise<ApiResponse<any>> {
    return this.get('/auth/me');
  }

  async updateProfile(data: {
    full_name?: string;
    phone_number?: string;
    username?: string;
  }): Promise<ApiResponse<any>> {
    return this.put('/auth/me', data);
  }

  async changePassword(
    currentPassword: string,
    newPassword: string,
    confirmPassword: string
  ): Promise<ApiResponse<any>> {
    return this.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_new_password: confirmPassword,
    });
  }

  // Token management
  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  async getAccessToken(): Promise<string | null> {
    return this.accessToken;
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<any>> {
    return this.get('/health');
  }
}

// Custom error class
class ApiError extends Error {
  public code: string;
  public details?: any;
  public status?: number;

  constructor(message: string, code: string, details?: any, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

export { ApiError };
export const apiService = new ApiService();