import React from 'react';
import { View, ViewStyle, StyleSheet } from 'react-native';
import { moderateScale } from 'react-native-size-matters';
import { theme } from '../styles/theme';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  padding?: number;
  margin?: number;
  elevation?: number;
  borderRadius?: number;
}

const Card: React.FC<CardProps> = ({
  children,
  style,
  padding = moderateScale(16),
  margin = 0,
  elevation = 2,
  borderRadius = moderateScale(12),
}) => {
  return (
    <View
      style={[
        styles.card,
        {
          padding,
          margin,
          elevation,
          borderRadius,
          shadowOffset: {
            width: 0,
            height: elevation,
          },
          shadowOpacity: elevation * 0.1,
          shadowRadius: elevation * 2,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    shadowColor: theme.colors.shadow,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
});

export default Card;