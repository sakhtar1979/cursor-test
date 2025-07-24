import React, { useState, useEffect, useCallback } from 'react';
import {
  ScrollView,
  RefreshControl,
  View,
  Text,
  TouchableOpacity,
  Dimensions,
  StyleSheet,
  StatusBar,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import LinearGradient from 'react-native-linear-gradient';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { moderateScale, scale, verticalScale } from 'react-native-size-matters';

// Components
import Card from '../components/Card';
import LoadingSpinner from '../components/LoadingSpinner';
import NetWorthChart from '../components/Charts/NetWorthChart';
import SpendingChart from '../components/Charts/SpendingChart';
import TransactionList from '../components/TransactionList';
import QuickActionButton from '../components/QuickActionButton';
import BalanceCard from '../components/BalanceCard';
import BudgetProgressCard from '../components/BudgetProgressCard';
import InsightCard from '../components/InsightCard';

// Hooks
import { useAuth } from '../hooks/useAuth';
import { useAccounts } from '../hooks/useAccounts';
import { useTransactions } from '../hooks/useTransactions';
import { useBudgets } from '../hooks/useBudgets';
import { useInsights } from '../hooks/useInsights';

// Utils
import { formatCurrency, formatTime } from '../utils/formatters';
import { theme } from '../styles/theme';

const { width } = Dimensions.get('window');

interface DashboardScreenProps {}

const DashboardScreen: React.FC<DashboardScreenProps> = () => {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();
  const { user } = useAuth();
  
  const { 
    data: accounts, 
    isLoading: accountsLoading, 
    refetch: refetchAccounts 
  } = useAccounts();
  
  const { 
    data: transactions, 
    isLoading: transactionsLoading,
    refetch: refetchTransactions 
  } = useTransactions({ limit: 5 });
  
  const { 
    data: budgets, 
    isLoading: budgetsLoading,
    refetch: refetchBudgets 
  } = useBudgets();
  
  const { 
    data: insights, 
    isLoading: insightsLoading,
    refetch: refetchInsights 
  } = useInsights();

  const [refreshing, setRefreshing] = useState(false);
  const [showAmounts, setShowAmounts] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Calculate financial metrics
  const totalBalance = accounts?.reduce((sum, account) => {
    return sum + (account.current_balance || 0);
  }, 0) || 0;

  const monthlyIncome = 4200; // This would come from analysis API
  const monthlyExpenses = 3150; // This would come from analysis API
  const netWorth = totalBalance + 15000; // Including investments, etc.

  const monthlyChange = 250;
  const monthlyChangePercent = 3.2;

  // Refresh handler
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        refetchAccounts(),
        refetchTransactions(),
        refetchBudgets(),
        refetchInsights(),
      ]);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error refreshing data:', error);
    } finally {
      setRefreshing(false);
    }
  }, [refetchAccounts, refetchTransactions, refetchBudgets, refetchInsights]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(() => {
      onRefresh();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [onRefresh]);

  const quickActions = [
    {
      title: 'Add Account',
      icon: 'account-balance',
      color: theme.colors.primary,
      onPress: () => navigation.navigate('ConnectBank' as never),
    },
    {
      title: 'Categorize',
      icon: 'category',
      color: theme.colors.secondary,
      onPress: () => navigation.navigate('Transactions' as never),
    },
    {
      title: 'Set Budget',
      icon: 'pie-chart',
      color: theme.colors.success,
      onPress: () => navigation.navigate('Budget' as never),
    },
    {
      title: 'Add Goal',
      icon: 'flag',
      color: theme.colors.warning,
      onPress: () => navigation.navigate('Goals' as never),
    },
  ];

  if (accountsLoading && !accounts) {
    return (
      <View style={styles.loadingContainer}>
        <LoadingSpinner size="large" />
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.primary} />
      
      {/* Header */}
      <LinearGradient
        colors={[theme.colors.primary, theme.colors.secondary]}
        style={styles.header}
      >
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.greeting}>Good morning,</Text>
            <Text style={styles.userName}>{user?.first_name} 👋</Text>
          </View>
          
          <TouchableOpacity
            style={styles.profileButton}
            onPress={() => navigation.navigate('Profile' as never)}
          >
            <Icon name="account-circle" size={moderateScale(32)} color="#fff" />
          </TouchableOpacity>
        </View>
        
        <Text style={styles.lastUpdated}>
          Last updated {formatTime(lastUpdated)}
        </Text>
      </LinearGradient>

      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={[theme.colors.primary]}
            tintColor={theme.colors.primary}
          />
        }
      >
        {/* Net Worth Card */}
        <View style={styles.section}>
          <BalanceCard
            title="Net Worth"
            amount={netWorth}
            change={monthlyChange}
            changePercent={monthlyChangePercent}
            showAmount={showAmounts}
            onToggleVisibility={() => setShowAmounts(!showAmounts)}
            trend="up"
          />
        </View>

        {/* Financial Summary */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Financial Summary</Text>
          <View style={styles.summaryRow}>
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>Total Balance</Text>
              <Text style={styles.summaryAmount}>
                {showAmounts ? formatCurrency(totalBalance) : '••••••'}
              </Text>
              <Text style={styles.summarySubtext}>
                {accounts?.length || 0} accounts
              </Text>
            </Card>
            
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>Monthly Income</Text>
              <Text style={[styles.summaryAmount, { color: theme.colors.success }]}>
                {showAmounts ? formatCurrency(monthlyIncome) : '••••••'}
              </Text>
              <View style={styles.changeRow}>
                <Icon name="trending-up" size={moderateScale(14)} color={theme.colors.success} />
                <Text style={[styles.summarySubtext, { color: theme.colors.success }]}>
                  +5.2%
                </Text>
              </View>
            </Card>
          </View>
          
          <View style={styles.summaryRow}>
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>Monthly Expenses</Text>
              <Text style={[styles.summaryAmount, { color: theme.colors.error }]}>
                {showAmounts ? formatCurrency(monthlyExpenses) : '••••••'}
              </Text>
              <View style={styles.changeRow}>
                <Icon name="trending-down" size={moderateScale(14)} color={theme.colors.success} />
                <Text style={[styles.summarySubtext, { color: theme.colors.success }]}>
                  -2.1%
                </Text>
              </View>
            </Card>
            
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>Net Income</Text>
              <Text style={styles.summaryAmount}>
                {showAmounts ? formatCurrency(monthlyIncome - monthlyExpenses) : '••••••'}
              </Text>
              <Text style={styles.summarySubtext}>This month</Text>
            </Card>
          </View>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.quickActionsGrid}>
            {quickActions.map((action, index) => (
              <QuickActionButton
                key={index}
                title={action.title}
                icon={action.icon}
                color={action.color}
                onPress={action.onPress}
              />
            ))}
          </View>
        </View>

        {/* Spending Chart */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Spending Overview</Text>
          <Card style={styles.chartCard}>
            <SpendingChart />
          </Card>
        </View>

        {/* Budget Progress */}
        {budgets && budgets.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Budget Progress</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Budget' as never)}>
                <Text style={styles.seeAllText}>See All</Text>
              </TouchableOpacity>
            </View>
            <BudgetProgressCard budgets={budgets.slice(0, 3)} />
          </View>
        )}

        {/* Recent Transactions */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Transactions</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Transactions' as never)}>
              <Text style={styles.seeAllText}>See All</Text>
            </TouchableOpacity>
          </View>
          <Card style={styles.transactionsCard}>
            <TransactionList
              transactions={transactions || []}
              showAccount={true}
              limit={5}
              showAmount={showAmounts}
            />
          </Card>
        </View>

        {/* AI Insights */}
        {insights && insights.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>AI Insights</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Insights' as never)}>
                <Text style={styles.seeAllText}>See All</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.insightsContainer}>
              {insights.slice(0, 2).map((insight, index) => (
                <InsightCard
                  key={index}
                  insight={insight}
                  compact={true}
                />
              ))}
            </View>
          </View>
        )}

        {/* Bottom spacing */}
        <View style={{ height: verticalScale(100) }} />
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background,
  },
  header: {
    paddingHorizontal: scale(20),
    paddingVertical: verticalScale(20),
    borderBottomLeftRadius: moderateScale(25),
    borderBottomRightRadius: moderateScale(25),
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: verticalScale(8),
  },
  greeting: {
    fontSize: moderateScale(16),
    color: '#fff',
    opacity: 0.9,
  },
  userName: {
    fontSize: moderateScale(24),
    fontWeight: 'bold',
    color: '#fff',
  },
  profileButton: {
    padding: moderateScale(4),
  },
  lastUpdated: {
    fontSize: moderateScale(12),
    color: '#fff',
    opacity: 0.8,
  },
  scrollView: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  section: {
    paddingHorizontal: scale(20),
    marginTop: verticalScale(20),
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: verticalScale(12),
  },
  sectionTitle: {
    fontSize: moderateScale(18),
    fontWeight: '600',
    color: theme.colors.text.primary,
  },
  seeAllText: {
    fontSize: moderateScale(14),
    color: theme.colors.primary,
    fontWeight: '500',
  },
  summaryRow: {
    flexDirection: 'row',
    gap: scale(12),
    marginBottom: verticalScale(12),
  },
  summaryCard: {
    flex: 1,
    padding: moderateScale(16),
  },
  summaryLabel: {
    fontSize: moderateScale(12),
    color: theme.colors.text.secondary,
    marginBottom: verticalScale(4),
  },
  summaryAmount: {
    fontSize: moderateScale(18),
    fontWeight: '600',
    color: theme.colors.text.primary,
    marginBottom: verticalScale(4),
  },
  summarySubtext: {
    fontSize: moderateScale(11),
    color: theme.colors.text.secondary,
  },
  changeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: scale(4),
  },
  quickActionsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: scale(12),
  },
  chartCard: {
    padding: moderateScale(16),
    height: verticalScale(200),
  },
  transactionsCard: {
    padding: moderateScale(16),
  },
  insightsContainer: {
    gap: verticalScale(12),
  },
});

export default DashboardScreen;