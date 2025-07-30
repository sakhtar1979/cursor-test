/**
 * Card Component for MintFlow Mobile App
 * Reusable card component with elevation and styling
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { theme } from '../styles/theme';

export interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  contentStyle?: ViewStyle;
  onPress?: () => void;
  disabled?: boolean;
  elevation?: number;
  borderRadius?: number;
  padding?: number;
  margin?: number;
  backgroundColor?: string;
  shadowColor?: string;
  testID?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  style,
  contentStyle,
  onPress,
  disabled = false,
  elevation = 2,
  borderRadius = theme.borderRadius.medium,
  padding = theme.spacing.medium,
  margin = 0,
  backgroundColor = theme.colors.surface,
  shadowColor = theme.colors.shadow,
  testID,
}) => {
  const cardStyles = [
    styles.card,
    {
      borderRadius,
      padding,
      margin,
      backgroundColor,
      ...getShadowStyle(elevation, shadowColor),
    },
    style,
  ];

  const Component = onPress ? TouchableOpacity : View;

  return (
    <Component
      style={cardStyles}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={onPress ? 0.7 : 1}
      testID={testID}
    >
      <View style={[styles.content, contentStyle]}>
        {children}
      </View>
    </Component>
  );
};

// Helper function to generate shadow styles
function getShadowStyle(elevation: number, shadowColor: string): ViewStyle {
  if (elevation === 0) {
    return {};
  }

  return {
    shadowColor,
    shadowOffset: {
      width: 0,
      height: elevation / 2,
    },
    shadowOpacity: 0.1 + (elevation * 0.05),
    shadowRadius: elevation,
    elevation, // Android
  };
}

const styles = StyleSheet.create({
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: theme.colors.border,
  },
  content: {
    flex: 1,
  },
});

// Pre-configured card variants
export const CardVariants = {
  Primary: (props: Omit<CardProps, 'backgroundColor'>) => (
    <Card {...props} backgroundColor={theme.colors.primary} />
  ),
  
  Secondary: (props: Omit<CardProps, 'backgroundColor'>) => (
    <Card {...props} backgroundColor={theme.colors.secondary} />
  ),
  
  Surface: (props: Omit<CardProps, 'backgroundColor'>) => (
    <Card {...props} backgroundColor={theme.colors.surface} />
  ),
  
  Elevated: (props: Omit<CardProps, 'elevation'>) => (
    <Card {...props} elevation={4} />
  ),
  
  Flat: (props: Omit<CardProps, 'elevation'>) => (
    <Card {...props} elevation={0} />
  ),
};

// Account card specific component
export interface AccountCardProps extends Omit<CardProps, 'children'> {
  accountName: string;
  accountType: string;
  balance: number;
  currency?: string;
  isConnected?: boolean;
  lastUpdated?: Date;
}

export const AccountCard: React.FC<AccountCardProps> = ({
  accountName,
  accountType,
  balance,
  currency = 'USD',
  isConnected = true,
  lastUpdated,
  ...cardProps
}) => {
  const formatBalance = (amount: number, curr: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: curr,
    }).format(amount);
  };

  const formatLastUpdated = (date?: Date) => {
    if (!date) return '';
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Updated just now';
    if (diffInHours < 24) return `Updated ${diffInHours}h ago`;
    return `Updated ${Math.floor(diffInHours / 24)}d ago`;
  };

  return (
    <Card {...cardProps}>
      <View style={accountCardStyles.header}>
        <View style={accountCardStyles.titleContainer}>
          <Text style={accountCardStyles.accountName}>{accountName}</Text>
          <Text style={accountCardStyles.accountType}>{accountType}</Text>
        </View>
        <View style={[
          accountCardStyles.statusIndicator,
          { backgroundColor: isConnected ? theme.colors.success : theme.colors.error }
        ]} />
      </View>
      
      <View style={accountCardStyles.balanceContainer}>
        <Text style={accountCardStyles.balance}>
          {formatBalance(balance, currency)}
        </Text>
        {lastUpdated && (
          <Text style={accountCardStyles.lastUpdated}>
            {formatLastUpdated(lastUpdated)}
          </Text>
        )}
      </View>
    </Card>
  );
};

const accountCardStyles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: theme.spacing.small,
  },
  titleContainer: {
    flex: 1,
  },
  accountName: {
    fontSize: theme.typography.sizes.large,
    fontWeight: theme.typography.weights.semibold,
    color: theme.colors.text,
    marginBottom: theme.spacing.tiny,
  },
  accountType: {
    fontSize: theme.typography.sizes.small,
    color: theme.colors.textSecondary,
    textTransform: 'capitalize',
  },
  statusIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: theme.spacing.tiny,
  },
  balanceContainer: {
    alignItems: 'flex-start',
  },
  balance: {
    fontSize: theme.typography.sizes.extraLarge,
    fontWeight: theme.typography.weights.bold,
    color: theme.colors.text,
    marginBottom: theme.spacing.tiny,
  },
  lastUpdated: {
    fontSize: theme.typography.sizes.small,
    color: theme.colors.textSecondary,
  },
});

// Transaction card component
export interface TransactionCardProps extends Omit<CardProps, 'children'> {
  merchantName: string;
  category: string;
  amount: number;
  date: Date;
  currency?: string;
  isDebit?: boolean;
  isPending?: boolean;
}

export const TransactionCard: React.FC<TransactionCardProps> = ({
  merchantName,
  category,
  amount,
  date,
  currency = 'USD',
  isDebit = true,
  isPending = false,
  ...cardProps
}) => {
  const formatAmount = (amt: number, curr: string, debit: boolean) => {
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: curr,
    }).format(Math.abs(amt));
    
    return debit ? `-${formatted}` : `+${formatted}`;
  };

  const formatDate = (transactionDate: Date) => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (transactionDate.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (transactionDate.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return transactionDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
    }
  };

  return (
    <Card {...cardProps} padding={theme.spacing.medium}>
      <View style={transactionCardStyles.container}>
        <View style={transactionCardStyles.details}>
          <Text style={transactionCardStyles.merchant}>{merchantName}</Text>
          <View style={transactionCardStyles.metadata}>
            <Text style={transactionCardStyles.category}>{category}</Text>
            <Text style={transactionCardStyles.date}>{formatDate(date)}</Text>
          </View>
        </View>
        
        <View style={transactionCardStyles.amountContainer}>
          <Text style={[
            transactionCardStyles.amount,
            {
              color: isDebit ? theme.colors.error : theme.colors.success,
            }
          ]}>
            {formatAmount(amount, currency, isDebit)}
          </Text>
          {isPending && (
            <Text style={transactionCardStyles.pending}>Pending</Text>
          )}
        </View>
      </View>
    </Card>
  );
};

const transactionCardStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  details: {
    flex: 1,
    marginRight: theme.spacing.medium,
  },
  merchant: {
    fontSize: theme.typography.sizes.medium,
    fontWeight: theme.typography.weights.medium,
    color: theme.colors.text,
    marginBottom: theme.spacing.tiny,
  },
  metadata: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  category: {
    fontSize: theme.typography.sizes.small,
    color: theme.colors.textSecondary,
    marginRight: theme.spacing.small,
  },
  date: {
    fontSize: theme.typography.sizes.small,
    color: theme.colors.textSecondary,
  },
  amountContainer: {
    alignItems: 'flex-end',
  },
  amount: {
    fontSize: theme.typography.sizes.large,
    fontWeight: theme.typography.weights.semibold,
    marginBottom: theme.spacing.tiny,
  },
  pending: {
    fontSize: theme.typography.sizes.small,
    color: theme.colors.warning,
    fontStyle: 'italic',
  },
});

export default Card;