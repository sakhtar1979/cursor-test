import React, { useEffect, useState } from 'react';
import {
  StatusBar,
  useColorScheme,
  AppState,
  Linking,
  Alert,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Provider as PaperProvider } from 'react-native-paper';
import SplashScreen from 'react-native-splash-screen';
import Toast from 'react-native-toast-message';
import NetInfo from '@react-native-community/netinfo';
import PushNotification from 'react-native-push-notification';

// Store
import { store, persistor } from './store/store';

// Theme
import { lightTheme, darkTheme } from './styles/theme';

// Navigation
import AppNavigator from './navigation/AppNavigator';
import AuthNavigator from './navigation/AuthNavigator';

// Components
import LoadingScreen from './components/LoadingScreen';
import NetworkStatusBanner from './components/NetworkStatusBanner';

// Hooks
import { useAuth } from './hooks/useAuth';
import { useNotifications } from './hooks/useNotifications';

// Services
import { setupPushNotifications } from './services/notifications';
import { setupBiometrics } from './services/biometrics';
import { initializeAnalytics } from './services/analytics';

// Utils
import { navigationRef } from './navigation/RootNavigation';

const Stack = createNativeStackNavigator();

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

const AppContent: React.FC = () => {
  const isDarkMode = useColorScheme() === 'dark';
  const { isAuthenticated, isLoading, user } = useAuth();
  const { requestPermissions } = useNotifications();
  
  const [isNetworkConnected, setIsNetworkConnected] = useState(true);
  const [appState, setAppState] = useState(AppState.currentState);

  const theme = isDarkMode ? darkTheme : lightTheme;

  useEffect(() => {
    // Initialize app
    const initializeApp = async () => {
      try {
        // Setup push notifications
        await setupPushNotifications();
        await requestPermissions();
        
        // Setup biometrics if user is authenticated
        if (isAuthenticated) {
          await setupBiometrics();
        }
        
        // Initialize analytics
        await initializeAnalytics();
        
        // Hide splash screen
        setTimeout(() => {
          SplashScreen.hide();
        }, 1000);
        
      } catch (error) {
        console.error('App initialization error:', error);
        SplashScreen.hide();
      }
    };

    initializeApp();
  }, [isAuthenticated, requestPermissions]);

  // Monitor network connectivity
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsNetworkConnected(state.isConnected ?? false);
    });

    return unsubscribe;
  }, []);

  // Handle app state changes
  useEffect(() => {
    const handleAppStateChange = (nextAppState: string) => {
      if (appState.match(/inactive|background/) && nextAppState === 'active') {
        // App has come to the foreground
        console.log('App has come to the foreground!');
        
        // Refresh data when app becomes active
        queryClient.invalidateQueries();
      }
      setAppState(nextAppState);
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription?.remove();
  }, [appState]);

  // Handle deep links
  useEffect(() => {
    const handleDeepLink = (url: string) => {
      console.log('Deep link received:', url);
      // Handle deep link navigation
      // Example: mintflow://transaction/123
      if (url.includes('transaction/')) {
        const transactionId = url.split('transaction/')[1];
        // Navigate to transaction details
      }
    };

    const subscription = Linking.addEventListener('url', ({ url }) => {
      handleDeepLink(url);
    });

    // Check if app was opened via deep link
    Linking.getInitialURL().then((url) => {
      if (url) {
        handleDeepLink(url);
      }
    });

    return () => subscription?.remove();
  }, []);

  // Setup push notification handlers
  useEffect(() => {
    PushNotification.configure({
      onNotification: function(notification) {
        console.log('NOTIFICATION:', notification);
        
        // Handle notification tap
        if (notification.userInteraction) {
          // User tapped notification
          const { data } = notification;
          
          if (data?.type === 'budget_alert') {
            // Navigate to budget screen
            navigationRef.navigate('Budget' as never);
          } else if (data?.type === 'transaction_update') {
            // Navigate to transactions
            navigationRef.navigate('Transactions' as never);
          }
        }
      },
      
      permissions: {
        alert: true,
        badge: true,
        sound: true,
      },
      
      popInitialNotification: true,
      requestPermissions: false, // We handle this manually
    });
  }, []);

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <NavigationContainer ref={navigationRef}>
      <StatusBar
        barStyle={isDarkMode ? 'light-content' : 'dark-content'}
        backgroundColor={theme.colors.primary}
      />
      
      {/* Network status banner */}
      {!isNetworkConnected && <NetworkStatusBanner />}
      
      {/* Main navigation */}
      {isAuthenticated ? <AppNavigator /> : <AuthNavigator />}
      
      {/* Toast messages */}
      <Toast />
    </NavigationContainer>
  );
};

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <PersistGate loading={<LoadingScreen />} persistor={persistor}>
        <QueryClientProvider client={queryClient}>
          <PaperProvider theme={lightTheme}>
            <AppContent />
          </PaperProvider>
        </QueryClientProvider>
      </PersistGate>
    </Provider>
  );
};

export default App;