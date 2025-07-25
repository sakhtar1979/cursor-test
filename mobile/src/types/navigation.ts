import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { CompositeNavigationProp, RouteProp } from '@react-navigation/native';

// Define the root stack parameter list
export type RootStackParamList = {
  // Auth Stack
  Welcome: undefined;
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
  
  // Main App Stack
  Main: undefined;
  ConnectBank: undefined;
  TransactionDetails: { transactionId: string };
  BudgetDetails: { budgetId: string };
  GoalDetails: { goalId: string };
  Profile: undefined;
  Settings: undefined;
};

// Define the main tab parameter list
export type MainTabParamList = {
  Dashboard: undefined;
  Accounts: undefined;
  Transactions: undefined;
  Budget: undefined;
  Goals: undefined;
  Insights: undefined;
};

// Composite navigation prop for screens that can navigate to both stack and tab screens
export type AppNavigationProp = CompositeNavigationProp<
  NativeStackNavigationProp<RootStackParamList>,
  BottomTabNavigationProp<MainTabParamList>
>;

// Individual screen navigation props
export type DashboardNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList, 'Dashboard'>,
  NativeStackNavigationProp<RootStackParamList>
>;

export type AccountsNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList, 'Accounts'>,
  NativeStackNavigationProp<RootStackParamList>
>;

export type TransactionsNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList, 'Transactions'>,
  NativeStackNavigationProp<RootStackParamList>
>;

export type BudgetNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList, 'Budget'>,
  NativeStackNavigationProp<RootStackParamList>
>;

export type GoalsNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList, 'Goals'>,
  NativeStackNavigationProp<RootStackParamList>
>;

export type InsightsNavigationProp = CompositeNavigationProp<
  BottomTabNavigationProp<MainTabParamList, 'Insights'>,
  NativeStackNavigationProp<RootStackParamList>
>;

// Route props
export type DashboardRouteProp = RouteProp<MainTabParamList, 'Dashboard'>;
export type TransactionDetailsRouteProp = RouteProp<RootStackParamList, 'TransactionDetails'>;
export type BudgetDetailsRouteProp = RouteProp<RootStackParamList, 'BudgetDetails'>;
export type GoalDetailsRouteProp = RouteProp<RootStackParamList, 'GoalDetails'>;

// Screen props combining navigation and route
export type DashboardScreenProps = {
  navigation: DashboardNavigationProp;
  route: DashboardRouteProp;
};

export type TransactionDetailsScreenProps = {
  navigation: AppNavigationProp;
  route: TransactionDetailsRouteProp;
};

export type BudgetDetailsScreenProps = {
  navigation: AppNavigationProp;
  route: BudgetDetailsRouteProp;
};

export type GoalDetailsScreenProps = {
  navigation: AppNavigationProp;
  route: GoalDetailsRouteProp;
};

// Navigation reference type
declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}