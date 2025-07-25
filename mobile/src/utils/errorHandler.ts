import Toast from 'react-native-toast-message';
import { ApiError } from '../services/api';

export enum ErrorType {
  NETWORK = 'NETWORK',
  AUTH = 'AUTH',
  VALIDATION = 'VALIDATION',
  SERVER = 'SERVER',
  UNKNOWN = 'UNKNOWN',
}

export interface AppError {
  type: ErrorType;
  message: string;
  code?: string;
  originalError?: any;
  timestamp: Date;
}

export class ErrorHandler {
  static handleApiError(error: ApiError): AppError {
    let type: ErrorType;
    let message: string;

    switch (error.status) {
      case 400:
        type = ErrorType.VALIDATION;
        message = error.message || 'Invalid request. Please check your input.';
        break;
      case 401:
        type = ErrorType.AUTH;
        message = 'Session expired. Please log in again.';
        break;
      case 403:
        type = ErrorType.AUTH;
        message = 'Access denied. You don\'t have permission for this action.';
        break;
      case 404:
        type = ErrorType.SERVER;
        message = 'The requested resource was not found.';
        break;
      case 429:
        type = ErrorType.SERVER;
        message = 'Too many requests. Please try again later.';
        break;
      case 500:
        type = ErrorType.SERVER;
        message = 'Server error. Please try again later.';
        break;
      default:
        if (error.status >= 500) {
          type = ErrorType.SERVER;
          message = 'Server error. Please try again later.';
        } else {
          type = ErrorType.UNKNOWN;
          message = error.message || 'An unexpected error occurred.';
        }
    }

    return {
      type,
      message,
      code: error.code,
      originalError: error,
      timestamp: new Date(),
    };
  }

  static handleNetworkError(error: any): AppError {
    return {
      type: ErrorType.NETWORK,
      message: 'Network error. Please check your internet connection.',
      originalError: error,
      timestamp: new Date(),
    };
  }

  static handleGenericError(error: any): AppError {
    return {
      type: ErrorType.UNKNOWN,
      message: error.message || 'An unexpected error occurred.',
      originalError: error,
      timestamp: new Date(),
    };
  }

  static showError(error: AppError, options?: { 
    autoHide?: boolean;
    visibilityTime?: number;
    position?: 'top' | 'bottom';
  }) {
    const {
      autoHide = true,
      visibilityTime = 4000,
      position = 'top'
    } = options || {};

    Toast.show({
      type: 'error',
      text1: 'Error',
      text2: error.message,
      autoHide,
      visibilityTime,
      position,
    });
  }

  static showSuccess(message: string, options?: {
    autoHide?: boolean;
    visibilityTime?: number;
    position?: 'top' | 'bottom';
  }) {
    const {
      autoHide = true,
      visibilityTime = 3000,
      position = 'top'
    } = options || {};

    Toast.show({
      type: 'success',
      text1: 'Success',
      text2: message,
      autoHide,
      visibilityTime,
      position,
    });
  }

  static showWarning(message: string, options?: {
    autoHide?: boolean;
    visibilityTime?: number;
    position?: 'top' | 'bottom';
  }) {
    const {
      autoHide = true,
      visibilityTime = 3500,
      position = 'top'
    } = options || {};

    Toast.show({
      type: 'info',
      text1: 'Warning',
      text2: message,
      autoHide,
      visibilityTime,
      position,
    });
  }

  static logError(error: AppError) {
    console.error('App Error:', {
      type: error.type,
      message: error.message,
      code: error.code,
      timestamp: error.timestamp,
      originalError: error.originalError,
    });

    // In production, you might want to send this to a logging service
    // like Sentry, Crashlytics, etc.
    if (__DEV__) {
      console.trace('Error stack trace:', error.originalError);
    }
  }

  static isNetworkError(error: any): boolean {
    return error.type === ErrorType.NETWORK ||
           error.message?.includes('Network') ||
           error.message?.includes('timeout') ||
           error.message?.includes('connection');
  }

  static isAuthError(error: any): boolean {
    return error.type === ErrorType.AUTH ||
           error.status === 401 ||
           error.status === 403;
  }

  static shouldRetry(error: AppError, retryCount: number = 0): boolean {
    const maxRetries = 3;
    
    if (retryCount >= maxRetries) {
      return false;
    }

    return error.type === ErrorType.NETWORK ||
           (error.type === ErrorType.SERVER && error.originalError?.status >= 500);
  }
}

// Hook for using error handling in components
export const useErrorHandler = () => {
  const handleError = (error: any, context?: string) => {
    let appError: AppError;

    if (error.status) {
      // API Error
      appError = ErrorHandler.handleApiError(error);
    } else if (ErrorHandler.isNetworkError(error)) {
      appError = ErrorHandler.handleNetworkError(error);
    } else {
      appError = ErrorHandler.handleGenericError(error);
    }

    ErrorHandler.logError(appError);
    ErrorHandler.showError(appError);

    return appError;
  };

  const showSuccess = (message: string) => {
    ErrorHandler.showSuccess(message);
  };

  const showWarning = (message: string) => {
    ErrorHandler.showWarning(message);
  };

  return {
    handleError,
    showSuccess,
    showWarning,
  };
};