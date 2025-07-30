/**
 * Configuration for MintFlow Mobile App
 * Centralizes all app configuration and environment variables
 */

import { Platform } from 'react-native';

// Environment type
export type Environment = 'development' | 'staging' | 'production';

// Get environment from build configuration
const getEnvironment = (): Environment => {
  if (__DEV__) {
    return 'development';
  }
  
  // This would be set during build process
  const env = process.env.NODE_ENV as Environment;
  return env || 'production';
};

const ENV = getEnvironment();

// API Configuration
const API_CONFIGS = {
  development: {
    API_BASE_URL: 'http://localhost:8000/api/v1',
    WS_BASE_URL: 'ws://localhost:8000/ws',
  },
  staging: {
    API_BASE_URL: 'https://staging-api.mintflow.com/api/v1',
    WS_BASE_URL: 'wss://staging-api.mintflow.com/ws',
  },
  production: {
    API_BASE_URL: 'https://api.mintflow.com/api/v1',
    WS_BASE_URL: 'wss://api.mintflow.com/ws',
  },
};

const Config = {
  // Environment
  ENV,
  IS_DEV: ENV === 'development',
  IS_STAGING: ENV === 'staging',
  IS_PRODUCTION: ENV === 'production',

  // App Information
  APP_NAME: 'MintFlow',
  APP_VERSION: '1.0.0',
  BUILD_NUMBER: '1',
  BUNDLE_ID: Platform.select({
    ios: 'com.mintflow.app',
    android: 'com.mintflow.app',
  }),

  // API Configuration
  ...API_CONFIGS[ENV],

  // Authentication
  AUTH_TOKEN_KEY: 'access_token',
  REFRESH_TOKEN_KEY: 'refresh_token',
  USER_KEY: 'user_data',
  
  // Session Configuration
  SESSION_TIMEOUT: 30 * 60 * 1000, // 30 minutes
  REFRESH_THRESHOLD: 5 * 60 * 1000, // 5 minutes before expiry
  
  // Request Configuration
  REQUEST_TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second

  // Cache Configuration
  CACHE_DURATION: {
    SHORT: 5 * 60 * 1000, // 5 minutes
    MEDIUM: 30 * 60 * 1000, // 30 minutes
    LONG: 24 * 60 * 60 * 1000, // 24 hours
  },

  // Analytics Configuration
  ANALYTICS_ENABLED: ENV === 'production',
  CRASHLYTICS_ENABLED: ENV !== 'development',
  
  // Feature Flags
  FEATURES: {
    BIOMETRIC_AUTH: true,
    PUSH_NOTIFICATIONS: true,
    OFFLINE_MODE: true,
    DEEP_LINKING: true,
    RECEIPT_SCANNING: true,
    INVESTMENT_TRACKING: ENV !== 'development',
    BUSINESS_ACCOUNTS: false, // Coming soon
    CRYPTO_TRACKING: false, // Coming soon
  },

  // Plaid Configuration
  PLAID: {
    ENV: ENV === 'production' ? 'production' : 'sandbox',
    CLIENT_NAME: 'MintFlow',
    PRODUCTS: ['transactions', 'accounts', 'identity'],
    COUNTRY_CODES: ['US'],
    WEBHOOK_URL: `${API_CONFIGS[ENV].API_BASE_URL}/webhooks/plaid`,
  },

  // Security Configuration
  SECURITY: {
    PIN_LENGTH: 4,
    MAX_LOGIN_ATTEMPTS: 5,
    LOCKOUT_DURATION: 15 * 60 * 1000, // 15 minutes
    BIOMETRIC_TIMEOUT: 5 * 60 * 1000, // 5 minutes
    SESSION_STORAGE_ENCRYPTION: true,
  },

  // UI Configuration
  UI: {
    THEME_STORAGE_KEY: 'app_theme',
    LANGUAGE_STORAGE_KEY: 'app_language',
    DEFAULT_CURRENCY: 'USD',
    DATE_FORMAT: 'MM/DD/YYYY',
    TIME_FORMAT: '12h',
    
    // Animation durations
    ANIMATION: {
      FAST: 200,
      NORMAL: 300,
      SLOW: 500,
    },
    
    // Pagination
    PAGE_SIZE: 20,
    INFINITE_SCROLL_THRESHOLD: 0.7,
  },

  // Push Notifications
  NOTIFICATIONS: {
    BUDGET_ALERTS: true,
    TRANSACTION_ALERTS: true,
    BILL_REMINDERS: true,
    GOAL_UPDATES: true,
    SECURITY_ALERTS: true,
  },

  // Storage Keys
  STORAGE_KEYS: {
    // Authentication
    ACCESS_TOKEN: '@mintflow:access_token',
    REFRESH_TOKEN: '@mintflow:refresh_token',
    USER_DATA: '@mintflow:user_data',
    BIOMETRIC_ENABLED: '@mintflow:biometric_enabled',
    
    // App Settings
    THEME: '@mintflow:theme',
    LANGUAGE: '@mintflow:language',
    CURRENCY: '@mintflow:currency',
    NOTIFICATIONS: '@mintflow:notifications',
    
    // Cache
    ACCOUNTS_CACHE: '@mintflow:accounts_cache',
    TRANSACTIONS_CACHE: '@mintflow:transactions_cache',
    ANALYTICS_CACHE: '@mintflow:analytics_cache',
    
    // Onboarding
    ONBOARDING_COMPLETED: '@mintflow:onboarding_completed',
    TUTORIAL_COMPLETED: '@mintflow:tutorial_completed',
  },

  // External Services
  EXTERNAL_SERVICES: {
    SENTRY_DSN: ENV === 'production' ? 'your-sentry-dsn' : '',
    AMPLITUDE_API_KEY: ENV === 'production' ? 'your-amplitude-key' : '',
    BRANCH_KEY: Platform.select({
      ios: 'your-branch-ios-key',
      android: 'your-branch-android-key',
    }),
  },

  // Development Configuration
  DEV: {
    REDUX_LOGGER: ENV === 'development',
    FLIPPER_ENABLED: ENV === 'development' && Platform.OS === 'ios',
    MOCK_API: false, // Set to true for offline development
    SHOW_DEV_MENU: ENV === 'development',
  },

  // Legal & Compliance
  LEGAL: {
    TERMS_URL: 'https://mintflow.com/terms',
    PRIVACY_URL: 'https://mintflow.com/privacy',
    SUPPORT_EMAIL: 'support@mintflow.com',
    SUPPORT_PHONE: '+1-800-MINTFLOW',
  },

  // App Store Configuration
  APP_STORE: {
    IOS_APP_ID: '123456789',
    ANDROID_PACKAGE_NAME: 'com.mintflow.app',
    REVIEW_PROMPT_DELAY: 7 * 24 * 60 * 60 * 1000, // 7 days
    MIN_SESSIONS_FOR_REVIEW: 10,
  },

  // Banking Configuration
  BANKING: {
    SYNC_INTERVALS: {
      TRANSACTIONS: 30 * 60 * 1000, // 30 minutes
      ACCOUNTS: 60 * 60 * 1000, // 1 hour
      BALANCES: 15 * 60 * 1000, // 15 minutes
    },
    MAX_TRANSACTION_HISTORY: 2 * 365 * 24 * 60 * 60 * 1000, // 2 years
    CATEGORIZATION_CONFIDENCE_THRESHOLD: 0.8,
  },

  // Limits & Constraints
  LIMITS: {
    MAX_ACCOUNTS: 50,
    MAX_BUDGETS: 20,
    MAX_GOALS: 10,
    MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
    MAX_PHOTO_SIZE: 5 * 1024 * 1024, // 5MB
  },
};

// Type-safe config export
export default Config as typeof Config;

// Helper functions
export const getApiUrl = (endpoint: string): string => {
  return `${Config.API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
};

export const getWebSocketUrl = (endpoint: string): string => {
  return `${Config.WS_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
};

export const isFeatureEnabled = (feature: keyof typeof Config.FEATURES): boolean => {
  return Config.FEATURES[feature];
};

export const getStorageKey = (key: keyof typeof Config.STORAGE_KEYS): string => {
  return Config.STORAGE_KEYS[key];
};

export const isDevelopment = (): boolean => Config.IS_DEV;
export const isProduction = (): boolean => Config.IS_PRODUCTION;
export const isStaging = (): boolean => Config.IS_STAGING;

// Environment-specific configurations
export const getPlaidConfig = () => ({
  environment: Config.PLAID.ENV,
  clientName: Config.PLAID.CLIENT_NAME,
  products: Config.PLAID.PRODUCTS,
  countryCodes: Config.PLAID.COUNTRY_CODES,
});

export const getAnalyticsConfig = () => ({
  enabled: Config.ANALYTICS_ENABLED,
  sentryDsn: Config.EXTERNAL_SERVICES.SENTRY_DSN,
  amplitudeKey: Config.EXTERNAL_SERVICES.AMPLITUDE_API_KEY,
});

// Validation
const validateConfig = () => {
  const requiredKeys = ['API_BASE_URL', 'APP_NAME', 'APP_VERSION'];
  
  for (const key of requiredKeys) {
    if (!Config[key as keyof typeof Config]) {
      console.warn(`Missing required config: ${key}`);
    }
  }
  
  if (Config.IS_PRODUCTION && !Config.EXTERNAL_SERVICES.SENTRY_DSN) {
    console.warn('Sentry DSN not configured for production');
  }
};

// Run validation in development
if (Config.IS_DEV) {
  validateConfig();
}

// Export environment for backwards compatibility
export { ENV };