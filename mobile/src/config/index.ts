import { Platform } from 'react-native';

// Environment variables from .env file
const ENV = {
  API_URL: process.env.API_URL || 'http://localhost:8000',
  ENVIRONMENT: process.env.ENVIRONMENT || 'development',
  VERSION: process.env.VERSION || '1.0.0',
  BUILD_NUMBER: process.env.BUILD_NUMBER || '1',
  SENTRY_DSN: process.env.SENTRY_DSN || '',
  PLAID_ENV: process.env.PLAID_ENV || 'sandbox',
};

export const Config = {
  // API Configuration
  API_URL: ENV.API_URL,
  API_TIMEOUT: 30000, // 30 seconds
  
  // App Configuration
  APP_NAME: 'MintFlow',
  VERSION: ENV.VERSION,
  BUILD_NUMBER: ENV.BUILD_NUMBER,
  ENVIRONMENT: ENV.ENVIRONMENT,
  
  // Feature Flags
  FEATURES: {
    BIOMETRIC_AUTH: true,
    PUSH_NOTIFICATIONS: true,
    DARK_MODE: true,
    RECEIPT_SCANNING: true,
    LOCATION_SERVICES: true,
    ANALYTICS: true,
  },
  
  // External Services
  SENTRY_DSN: ENV.SENTRY_DSN,
  PLAID_ENV: ENV.PLAID_ENV,
  
  // Cache Configuration
  CACHE_TTL: {
    ACCOUNTS: 5 * 60 * 1000, // 5 minutes
    TRANSACTIONS: 2 * 60 * 1000, // 2 minutes
    BUDGETS: 10 * 60 * 1000, // 10 minutes
    INSIGHTS: 30 * 60 * 1000, // 30 minutes
  },
  
  // Security
  MAX_LOGIN_ATTEMPTS: 5,
  LOGIN_LOCKOUT_DURATION: 15 * 60 * 1000, // 15 minutes
  
  // UI Configuration
  PAGINATION: {
    TRANSACTIONS_PER_PAGE: 20,
    ACCOUNTS_PER_PAGE: 10,
    INSIGHTS_PER_PAGE: 5,
  },
  
  // Platform specific configs
  PLATFORM: Platform.OS,
  IS_IOS: Platform.OS === 'ios',
  IS_ANDROID: Platform.OS === 'android',
  
  // Development helpers
  IS_DEV: ENV.ENVIRONMENT === 'development',
  IS_STAGING: ENV.ENVIRONMENT === 'staging',
  IS_PROD: ENV.ENVIRONMENT === 'production',
};

// Type definitions
export type Environment = 'development' | 'staging' | 'production';
export type PlaidEnvironment = 'sandbox' | 'development' | 'production';

// Validation
if (!Config.API_URL) {
  throw new Error('API_URL is required in environment configuration');
}

export default Config;