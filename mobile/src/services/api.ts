import AsyncStorage from '@react-native-async-storage/async-storage';
import { Config } from '../config';

export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: number;
}

export interface ApiError {
  message: string;
  status: number;
  code?: string;
}

export class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseURL = Config.API_URL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (token) {
        return {
          ...this.defaultHeaders,
          'Authorization': `Bearer ${token}`,
        };
      }
      return this.defaultHeaders;
    } catch (error) {
      console.error('Error getting auth headers:', error);
      return this.defaultHeaders;
    }
  }

  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const contentType = response.headers.get('content-type');
    let data: any;

    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const error: ApiError = {
        message: data.message || `HTTP error! status: ${response.status}`,
        status: response.status,
        code: data.code,
      };

      // Handle token expiration
      if (response.status === 401) {
        await this.handleTokenExpiration();
      }

      throw error;
    }

    return {
      data,
      message: data.message,
      status: response.status,
    };
  }

  private async handleTokenExpiration(): Promise<void> {
    try {
      const refreshToken = await AsyncStorage.getItem('refresh_token');
      if (refreshToken) {
        const response = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: this.defaultHeaders,
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (response.ok) {
          const data = await response.json();
          await AsyncStorage.setItem('access_token', data.access_token);
          if (data.refresh_token) {
            await AsyncStorage.setItem('refresh_token', data.refresh_token);
          }
        } else {
          // Refresh failed, clear tokens and redirect to login
          await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user']);
          // You might want to emit an event or use a navigation service here
        }
      }
    } catch (error) {
      console.error('Error refreshing token:', error);
      await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user']);
    }
  }

  async get<T = any>(endpoint: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
    const headers = await this.getAuthHeaders();
    let url = `${this.baseURL}${endpoint}`;

    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      url += `?${searchParams.toString()}`;
    }

    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    return this.handleResponse<T>(response);
  }

  async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  async put<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  async patch<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PATCH',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers,
    });

    return this.handleResponse<T>(response);
  }

  async upload<T = any>(endpoint: string, formData: FormData): Promise<ApiResponse<T>> {
    const token = await AsyncStorage.getItem('access_token');
    const headers: Record<string, string> = {
      'Accept': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    return this.handleResponse<T>(response);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();