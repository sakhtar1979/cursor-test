/**
 * Error Handler for MintFlow Mobile App
 * Provides comprehensive error handling with user notifications and recovery
 */

import { Alert, Platform } from 'react-native';
import Toast from 'react-native-toast-message';
import { ApiError } from '../services/api';
import * as Sentry from '@sentry/react-native';
import crashlytics from '@react-native-firebase/crashlytics';

export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  metadata?: Record<string, any>;
}

export interface ErrorRecoveryAction {
  label: string;
  action: () => void;
}

class ErrorHandler {
  private static instance: ErrorHandler;
  private isEnabled = true;

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  constructor() {
    this.setupGlobalErrorHandlers();
  }

  private setupGlobalErrorHandlers(): void {
    // Handle unhandled promise rejections
    if (typeof global !== 'undefined') {
      global.onunhandledrejection = (event: PromiseRejectionEvent) => {
        this.handleError(
          new Error(`Unhandled Promise Rejection: ${event.reason}`),
          'Unexpected error occurred',
          { type: 'unhandled_promise_rejection' }
        );
      };
    }

    // Handle uncaught exceptions
    if (typeof ErrorUtils !== 'undefined') {
      const originalHandler = ErrorUtils.getGlobalHandler();
      
      ErrorUtils.setGlobalHandler((error: Error, isFatal?: boolean) => {
        this.handleError(
          error,
          'Application error occurred',
          { type: 'uncaught_exception', isFatal }
        );
        
        // Call original handler
        if (originalHandler) {
          originalHandler(error, isFatal);
        }
      });
    }
  }

  handleError(
    error: Error | ApiError | any,
    userMessage?: string,
    context?: ErrorContext,
    recoveryActions?: ErrorRecoveryAction[]
  ): void {
    if (!this.isEnabled) return;

    try {
      // Log error details
      this.logError(error, context);

      // Report to crash analytics
      this.reportError(error, context);

      // Show user-friendly message
      this.showUserNotification(error, userMessage, recoveryActions);

    } catch (handlerError) {
      console.error('Error in error handler:', handlerError);
    }
  }

  private logError(error: any, context?: ErrorContext): void {
    const errorInfo = {
      message: error.message || 'Unknown error',
      stack: error.stack,
      name: error.name,
      code: error.code,
      status: error.status,
      timestamp: new Date().toISOString(),
      platform: Platform.OS,
      context,
    };

    console.error('Error handled:', errorInfo);
  }

  private reportError(error: any, context?: ErrorContext): void {
    try {
      // Report to Sentry
      if (Sentry.getCurrentHub()) {
        Sentry.withScope(scope => {
          scope.setTag('component', context?.component || 'unknown');
          scope.setTag('action', context?.action || 'unknown');
          
          if (context?.userId) {
            scope.setUser({ id: context.userId });
          }
          
          if (context?.metadata) {
            scope.setContext('metadata', context.metadata);
          }
          
          Sentry.captureException(error);
        });
      }

      // Report to Firebase Crashlytics
      if (crashlytics) {
        crashlytics().recordError(error);
        
        if (context?.userId) {
          crashlytics().setUserId(context.userId);
        }
        
        if (context?.component) {
          crashlytics().setAttribute('component', context.component);
        }
        
        if (context?.action) {
          crashlytics().setAttribute('action', context.action);
        }
      }
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    }
  }

  private showUserNotification(
    error: any,
    userMessage?: string,
    recoveryActions?: ErrorRecoveryAction[]
  ): void {
    const message = this.getUserFriendlyMessage(error, userMessage);
    const isNetworkError = this.isNetworkError(error);
    const isCriticalError = this.isCriticalError(error);

    if (isCriticalError && recoveryActions?.length) {
      this.showCriticalErrorAlert(message, recoveryActions);
    } else if (isNetworkError) {
      this.showNetworkErrorToast(message);
    } else {
      this.showErrorToast(message);
    }
  }

  private getUserFriendlyMessage(error: any, userMessage?: string): string {
    if (userMessage) return userMessage;

    // Handle specific API errors
    if (error instanceof ApiError || error.code) {
      switch (error.code) {
        case 'NETWORK_ERROR':
          return 'Network connection failed. Please check your internet connection.';
        case 'AUTHENTICATION_FAILED':
          return 'Authentication failed. Please log in again.';
        case 'PERMISSION_DENIED':
          return 'You do not have permission to perform this action.';
        case 'RESOURCE_NOT_FOUND':
          return 'The requested resource was not found.';
        case 'RATE_LIMIT_EXCEEDED':
          return 'Too many requests. Please try again later.';
        case 'VALIDATION_ERROR':
          return 'Please check your input and try again.';
        case 'SERVER_ERROR':
          return 'Server error occurred. Our team has been notified.';
        case 'MAINTENANCE_MODE':
          return 'Service is temporarily under maintenance. Please try again later.';
        default:
          return error.message || 'An unexpected error occurred.';
      }
    }

    // Handle common error types
    if (this.isNetworkError(error)) {
      return 'Network connection failed. Please check your internet connection.';
    }

    if (error.message?.includes('timeout')) {
      return 'Request timed out. Please try again.';
    }

    if (error.message?.includes('JSON')) {
      return 'Data parsing error. Please try again.';
    }

    return error.message || 'An unexpected error occurred.';
  }

  private isNetworkError(error: any): boolean {
    return (
      error.code === 'NETWORK_ERROR' ||
      error.name === 'NetworkError' ||
      error.message?.includes('Network request failed') ||
      error.message?.includes('fetch')
    );
  }

  private isCriticalError(error: any): boolean {
    return (
      error.code === 'AUTHENTICATION_FAILED' ||
      error.status === 401 ||
      error.code === 'CRITICAL_SYSTEM_ERROR'
    );
  }

  private showErrorToast(message: string): void {
    Toast.show({
      type: 'error',
      text1: 'Error',
      text2: message,
      visibilityTime: 4000,
      autoHide: true,
      topOffset: 60,
    });
  }

  private showNetworkErrorToast(message: string): void {
    Toast.show({
      type: 'error',
      text1: 'Connection Error',
      text2: message,
      visibilityTime: 6000,
      autoHide: true,
      topOffset: 60,
      onPress: () => {
        Toast.hide();
        // Could trigger retry logic here
      },
    });
  }

  private showSuccessToast(message: string): void {
    Toast.show({
      type: 'success',
      text1: 'Success',
      text2: message,
      visibilityTime: 3000,
      autoHide: true,
      topOffset: 60,
    });
  }

  private showInfoToast(message: string): void {
    Toast.show({
      type: 'info',
      text1: 'Info',
      text2: message,
      visibilityTime: 3000,
      autoHide: true,
      topOffset: 60,
    });
  }

  private showCriticalErrorAlert(
    message: string,
    recoveryActions: ErrorRecoveryAction[]
  ): void {
    const buttons = recoveryActions.map(action => ({
      text: action.label,
      onPress: action.action,
    }));

    Alert.alert(
      'Critical Error',
      message,
      [
        ...buttons,
        {
          text: 'OK',
          style: 'cancel',
        },
      ],
      { cancelable: false }
    );
  }

  // Public methods for manual error reporting
  showSuccess(message: string): void {
    this.showSuccessToast(message);
  }

  showInfo(message: string): void {
    this.showInfoToast(message);
  }

  showWarning(message: string): void {
    Toast.show({
      type: 'error', // Using error type for warning appearance
      text1: 'Warning',
      text2: message,
      visibilityTime: 4000,
      autoHide: true,
      topOffset: 60,
    });
  }

  // Network error handling with retry
  handleNetworkError(
    error: any,
    retryCallback?: () => void,
    context?: ErrorContext
  ): void {
    const recoveryActions: ErrorRecoveryAction[] = [];
    
    if (retryCallback) {
      recoveryActions.push({
        label: 'Retry',
        action: retryCallback,
      });
    }

    this.handleError(
      error,
      'Network connection failed. Please check your internet connection.',
      context,
      recoveryActions
    );
  }

  // Authentication error handling
  handleAuthError(error: any, logoutCallback: () => void): void {
    this.handleError(
      error,
      'Your session has expired. Please log in again.',
      { component: 'auth' },
      [
        {
          label: 'Log In',
          action: logoutCallback,
        },
      ]
    );
  }

  // Validation error handling
  handleValidationError(error: any, fields?: string[]): void {
    let message = 'Please check your input and try again.';
    
    if (fields?.length) {
      message = `Please check the following fields: ${fields.join(', ')}`;
    }
    
    if (error.details?.validation_errors) {
      const fieldErrors = Object.keys(error.details.validation_errors);
      if (fieldErrors.length > 0) {
        message = `Please check: ${fieldErrors.join(', ')}`;
      }
    }

    this.handleError(error, message, { component: 'validation' });
  }

  // Financial data error handling
  handleFinancialDataError(error: any, dataType: string): void {
    this.handleError(
      error,
      `Failed to load ${dataType}. Please try again or contact support if the problem persists.`,
      { component: 'financial_data', action: `load_${dataType}` }
    );
  }

  // Banking connection error handling
  handleBankingError(error: any, bankName?: string): void {
    let message = 'Banking connection failed. Please try reconnecting your account.';
    
    if (bankName) {
      message = `Connection to ${bankName} failed. Please try reconnecting your account.`;
    }

    this.handleError(
      error,
      message,
      { component: 'banking', action: 'connect_account' }
    );
  }

  // Enable/disable error handling
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  // Clear all active toast messages
  clearNotifications(): void {
    Toast.hide();
  }

  // Test error handling (for development)
  testError(type: 'network' | 'auth' | 'critical' | 'validation' = 'network'): void {
    if (__DEV__) {
      switch (type) {
        case 'network':
          this.handleNetworkError(new Error('Test network error'));
          break;
        case 'auth':
          this.handleAuthError(new Error('Test auth error'), () => console.log('Logout'));
          break;
        case 'critical':
          this.handleError(
            new Error('Test critical error'),
            'Critical system error',
            { component: 'test' },
            [{ label: 'Restart', action: () => console.log('Restart') }]
          );
          break;
        case 'validation':
          this.handleValidationError(new Error('Test validation error'), ['email', 'password']);
          break;
      }
    }
  }
}

// Export singleton instance
export const errorHandler = ErrorHandler.getInstance();