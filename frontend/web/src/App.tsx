import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Provider } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import { ThemeProvider } from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';

// Store and Theme
import { store } from './store/store';
import { theme } from './styles/theme';
import GlobalStyles from './styles/GlobalStyles';

// Components
import Layout from './components/Layout/Layout';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import LoadingSpinner from './components/UI/LoadingSpinner';

// Pages
import Landing from './pages/Landing/Landing';
import Login from './pages/Auth/Login';
import Register from './pages/Auth/Register';
import ForgotPassword from './pages/Auth/ForgotPassword';
import Dashboard from './pages/Dashboard/Dashboard';
import Accounts from './pages/Accounts/Accounts';
import Transactions from './pages/Transactions/Transactions';
import Budget from './pages/Budget/Budget';
import Goals from './pages/Goals/Goals';
import Insights from './pages/Insights/Insights';
import Profile from './pages/Profile/Profile';
import Settings from './pages/Settings/Settings';
import ConnectBank from './pages/Banking/ConnectBank';

// Hooks
import { useAuth } from './hooks/useAuth';

// Styles
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

// Create a client for React Query
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

// Page transition variants
const pageVariants = {
  initial: {
    opacity: 0,
    x: -20,
  },
  animate: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.3,
      ease: 'easeOut',
    },
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: {
      duration: 0.2,
      ease: 'easeIn',
    },
  },
};

const AppRoutes: React.FC = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <Routes>
        {/* Public Routes */}
        <Route 
          path="/" 
          element={
            user ? <Navigate to="/dashboard" replace /> : 
            <motion.div
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <Landing />
            </motion.div>
          } 
        />
        
        <Route 
          path="/login" 
          element={
            user ? <Navigate to="/dashboard" replace /> :
            <motion.div
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <Login />
            </motion.div>
          } 
        />
        
        <Route 
          path="/register" 
          element={
            user ? <Navigate to="/dashboard" replace /> :
            <motion.div
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <Register />
            </motion.div>
          } 
        />
        
        <Route 
          path="/forgot-password" 
          element={
            user ? <Navigate to="/dashboard" replace /> :
            <motion.div
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <ForgotPassword />
            </motion.div>
          } 
        />

        {/* Protected Routes */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route 
              path="/dashboard" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Dashboard />
                </motion.div>
              } 
            />
            
            <Route 
              path="/accounts" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Accounts />
                </motion.div>
              } 
            />
            
            <Route 
              path="/transactions" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Transactions />
                </motion.div>
              } 
            />
            
            <Route 
              path="/budget" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Budget />
                </motion.div>
              } 
            />
            
            <Route 
              path="/goals" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Goals />
                </motion.div>
              } 
            />
            
            <Route 
              path="/insights" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Insights />
                </motion.div>
              } 
            />
            
            <Route 
              path="/connect-bank" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <ConnectBank />
                </motion.div>
              } 
            />
            
            <Route 
              path="/profile" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Profile />
                </motion.div>
              } 
            />
            
            <Route 
              path="/settings" 
              element={
                <motion.div
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Settings />
                </motion.div>
              } 
            />
          </Route>
        </Route>

        {/* Catch all route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
};

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <GlobalStyles />
          <Router>
            <div className="App">
              <AppRoutes />
              
              {/* Toast Notifications */}
              <ToastContainer
                position="top-right"
                autoClose={5000}
                hideProgressBar={false}
                newestOnTop={false}
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
                theme="light"
                toastClassName="toast-custom"
              />
            </div>
          </Router>
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
};

export default App;