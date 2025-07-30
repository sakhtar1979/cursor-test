/**
 * Navigation Types for MintFlow Mobile App
 * Provides comprehensive type safety for React Navigation
 */

import { StackScreenProps } from '@react-navigation/stack';
import { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import { CompositeScreenProps } from '@react-navigation/native';

// Root Stack Navigator types
export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
  Onboarding: undefined;
  LinkBank: { returnTo?: keyof MainTabParamList };
  Settings: undefined;
  Profile: undefined;
  Security: undefined;
  TransactionDetail: { transactionId: string };
  AccountDetail: { accountId: string };
  BudgetDetail: { budgetId: string };
  GoalDetail: { goalId: string };
};

// Main Tab Navigator types
export type MainTabParamList = {
  Dashboard: undefined;
  Accounts: undefined;
  Transactions: undefined;
  Budgets: undefined;
  Goals: undefined;
  Insights: undefined;
};

// Auth Stack Navigator types
export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
  VerifyEmail: { email: string };
  ResetPassword: { token: string };
  MFASetup: undefined;
  MFAVerify: { userId: string };
};

// Screen prop types for type-safe navigation
export type RootStackScreenProps<T extends keyof RootStackParamList> = 
  StackScreenProps<RootStackParamList, T>;

export type MainTabScreenProps<T extends keyof MainTabParamList> = 
  CompositeScreenProps<
    BottomTabScreenProps<MainTabParamList, T>,
    RootStackScreenProps<keyof RootStackParamList>
  >;

export type AuthStackScreenProps<T extends keyof AuthStackParamList> = 
  StackScreenProps<AuthStackParamList, T>;

// Navigation prop types for components
export type NavigationProps = {
  navigation: any; // Will be properly typed based on screen
  route: any; // Will be properly typed based on screen
};

// Common navigation parameters
export type NavigationParams = {
  accountId?: string;
  transactionId?: string;
  budgetId?: string;
  goalId?: string;
  returnTo?: string;
  refresh?: boolean;
};

// Transaction related navigation types
export type TransactionStackParamList = {
  TransactionList: {
    accountId?: string;
    categoryId?: string;
    dateRange?: [Date, Date];
  };
  TransactionCreate: {
    accountId?: string;
    category?: string;
    amount?: number;
  };
  TransactionEdit: {
    transactionId: string;
  };
  TransactionSearch: undefined;
  TransactionCategories: undefined;
};

// Account related navigation types
export type AccountStackParamList = {
  AccountList: undefined;
  AccountDetail: {
    accountId: string;
    tab?: 'overview' | 'transactions' | 'statements';
  };
  AccountSettings: {
    accountId: string;
  };
  LinkNewAccount: {
    institutionId?: string;
  };
};

// Budget related navigation types
export type BudgetStackParamList = {
  BudgetList: undefined;
  BudgetDetail: {
    budgetId: string;
  };
  BudgetCreate: {
    categoryId?: string;
    amount?: number;
  };
  BudgetEdit: {
    budgetId: string;
  };
  BudgetCategories: undefined;
};

// Goal related navigation types
export type GoalStackParamList = {
  GoalList: undefined;
  GoalDetail: {
    goalId: string;
  };
  GoalCreate: {
    type?: 'savings' | 'debt_payoff' | 'investment';
    targetAmount?: number;
  };
  GoalEdit: {
    goalId: string;
  };
};

// Deep linking types
export type DeepLinkParams = {
  screen: keyof RootStackParamList;
  params?: any;
};

// Navigation theme type
export type NavigationTheme = {
  dark: boolean;
  colors: {
    primary: string;
    background: string;
    card: string;
    text: string;
    border: string;
    notification: string;
  };
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}