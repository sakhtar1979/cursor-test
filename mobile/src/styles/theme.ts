import { DefaultTheme } from 'react-native-paper';

export const lightTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#3B82F6',
    secondary: '#8B5CF6',
    accent: '#F59E0B',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
    
    // Background colors
    background: '#FFFFFF',
    surface: '#FFFFFF',
    card: '#FFFFFF',
    
    // Text colors
    text: {
      primary: '#111827',
      secondary: '#6B7280',
      disabled: '#9CA3AF',
      inverse: '#FFFFFF',
    },
    
    // Border and shadow
    border: '#E5E7EB',
    shadow: '#000000',
    overlay: 'rgba(0, 0, 0, 0.5)',
    
    // Status colors
    online: '#10B981',
    offline: '#EF4444',
    idle: '#F59E0B',
  },
  
  // Typography
  fonts: {
    regular: {
      fontFamily: 'System',
      fontWeight: '400',
    },
    medium: {
      fontFamily: 'System',
      fontWeight: '500',
    },
    semibold: {
      fontFamily: 'System',
      fontWeight: '600',
    },
    bold: {
      fontFamily: 'System',
      fontWeight: '700',
    },
  },
  
  // Spacing
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  
  // Border radius
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    full: 9999,
  },
  
  // Elevation/Shadow
  elevation: {
    sm: 2,
    md: 4,
    lg: 8,
    xl: 16,
  },
};

export const darkTheme = {
  ...lightTheme,
  colors: {
    ...lightTheme.colors,
    
    // Background colors
    background: '#111827',
    surface: '#1F2937',
    card: '#1F2937',
    
    // Text colors
    text: {
      primary: '#F9FAFB',
      secondary: '#D1D5DB',
      disabled: '#6B7280',
      inverse: '#111827',
    },
    
    // Border and shadow
    border: '#374151',
    shadow: '#000000',
    overlay: 'rgba(0, 0, 0, 0.7)',
  },
};

export const theme = lightTheme;

// Type definitions
export type Theme = typeof lightTheme;
export type Colors = typeof lightTheme.colors;