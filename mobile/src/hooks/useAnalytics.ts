/**
 * Analytics Hook for MintFlow Mobile App
 * Provides real-time financial analytics and insights
 */

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsService } from '../services/analytics';
import { apiService } from '../services/api';
import { errorHandler } from '../utils/errorHandler';

export interface SpendingData {
  category: string;
  amount: number;
  percentage: number;
  color: string;
  trend: 'up' | 'down' | 'stable';
  previousAmount: number;
}

export interface IncomeData {
  month: string;
  income: number;
  expenses: number;
  savings: number;
  net: number;
}

export interface BudgetStatus {
  budgetId: string;
  category: string;
  budgeted: number;
  spent: number;
  remaining: number;
  percentage: number;
  status: 'under_budget' | 'on_track' | 'over_budget' | 'warning';
  daysLeft: number;
}

export interface NetWorthData {
  date: string;
  assets: number;
  liabilities: number;
  netWorth: number;
}

export interface CashFlowData {
  date: string;
  income: number;
  expenses: number;
  net: number;
}

export interface AnalyticsData {
  totalBalance: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  savingsRate: number;
  spendingByCategory: SpendingData[];
  incomeVsExpenses: IncomeData[];
  budgetStatus: BudgetStatus[];
  netWorthTrend: NetWorthData[];
  cashFlowTrend: CashFlowData[];
  topExpenseCategories: string[];
  financialHealthScore: number;
  creditScore?: number;
  lastUpdated: string;
}

export interface AnalyticsFilters {
  dateRange: {
    start: Date;
    end: Date;
  };
  accountIds?: string[];
  categories?: string[];
  includeInvestments?: boolean;
  excludeTransfers?: boolean;
}

export const useAnalytics = (filters?: AnalyticsFilters) => {
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);

  // Default filters
  const defaultFilters: AnalyticsFilters = {
    dateRange: {
      start: new Date(new Date().getFullYear(), new Date().getMonth() - 5, 1),
      end: new Date(),
    },
    includeInvestments: true,
    excludeTransfers: true,
    ...filters,
  };

  // Fetch analytics data
  const {
    data: analyticsData,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['analytics', defaultFilters],
    queryFn: () => analyticsService.getAnalytics(defaultFilters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    onError: (error) => {
      errorHandler.handleError(error, 'Failed to load analytics data');
    },
  });

  // Fetch spending insights
  const {
    data: spendingInsights,
    isLoading: insightsLoading,
  } = useQuery({
    queryKey: ['spending-insights', defaultFilters],
    queryFn: () => analyticsService.getSpendingInsights(defaultFilters),
    enabled: !!analyticsData,
    staleTime: 10 * 60 * 1000,
  });

  // Fetch budget performance
  const {
    data: budgetPerformance,
    isLoading: budgetLoading,
  } = useQuery({
    queryKey: ['budget-performance', defaultFilters],
    queryFn: () => analyticsService.getBudgetPerformance(defaultFilters),
    staleTime: 15 * 60 * 1000,
  });

  // Fetch financial goals progress
  const {
    data: goalsProgress,
    isLoading: goalsLoading,
  } = useQuery({
    queryKey: ['goals-progress'],
    queryFn: () => analyticsService.getGoalsProgress(),
    staleTime: 30 * 60 * 1000,
  });

  // Refresh analytics data
  const refreshAnalytics = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        queryClient.invalidateQueries(['analytics']),
        queryClient.invalidateQueries(['spending-insights']),
        queryClient.invalidateQueries(['budget-performance']),
        queryClient.invalidateQueries(['goals-progress']),
      ]);
    } catch (error) {
      errorHandler.handleError(error, 'Failed to refresh analytics');
    } finally {
      setRefreshing(false);
    }
  }, [queryClient]);

  // Update analytics preferences
  const updatePreferences = useMutation({
    mutationFn: analyticsService.updatePreferences,
    onSuccess: () => {
      queryClient.invalidateQueries(['analytics']);
      errorHandler.showSuccess('Analytics preferences updated');
    },
    onError: (error) => {
      errorHandler.handleError(error, 'Failed to update preferences');
    },
  });

  // Export analytics data
  const exportData = useMutation({
    mutationFn: analyticsService.exportData,
    onSuccess: (data) => {
      errorHandler.showSuccess('Analytics data exported successfully');
      return data;
    },
    onError: (error) => {
      errorHandler.handleError(error, 'Failed to export data');
    },
  });

  // Calculate derived metrics
  const derivedMetrics = analyticsData ? {
    monthlySpending: analyticsData.monthlyExpenses,
    savingsRate: analyticsData.savingsRate,
    debtToIncomeRatio: analyticsData.liabilities / analyticsData.monthlyIncome,
    emergencyFundMonths: analyticsData.totalBalance / analyticsData.monthlyExpenses,
    financialHealthGrade: getFinancialHealthGrade(analyticsData.financialHealthScore),
    topSpendingCategory: analyticsData.spendingByCategory[0]?.category || 'Unknown',
    monthlyNetIncome: analyticsData.monthlyIncome - analyticsData.monthlyExpenses,
  } : null;

  // Real-time data sync
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isFetching && !refreshing) {
        refetch();
      }
    }, 5 * 60 * 1000); // Refresh every 5 minutes

    return () => clearInterval(interval);
  }, [refetch, isFetching, refreshing]);

  return {
    // Data
    analyticsData,
    spendingInsights,
    budgetPerformance,
    goalsProgress,
    derivedMetrics,

    // Loading states
    isLoading: isLoading || insightsLoading || budgetLoading || goalsLoading,
    isRefreshing: refreshing || isFetching,
    
    // Error handling
    error,
    
    // Actions
    refreshAnalytics,
    updatePreferences: updatePreferences.mutate,
    exportData: exportData.mutate,
    
    // Status
    isUpdatingPreferences: updatePreferences.isLoading,
    isExporting: exportData.isLoading,
  };
};

// Helper function to get financial health grade
function getFinancialHealthGrade(score: number): string {
  if (score >= 90) return 'A+';
  if (score >= 80) return 'A';
  if (score >= 70) return 'B';
  if (score >= 60) return 'C';
  if (score >= 50) return 'D';
  return 'F';
}

// Hook for specific analytics components
export const useSpendingAnalytics = (categoryId?: string) => {
  const filters = categoryId ? {
    dateRange: {
      start: new Date(new Date().getFullYear(), new Date().getMonth() - 2, 1),
      end: new Date(),
    },
    categories: [categoryId],
  } : undefined;

  return useAnalytics(filters);
};

export const useBudgetAnalytics = (budgetId: string) => {
  return useQuery({
    queryKey: ['budget-analytics', budgetId],
    queryFn: () => analyticsService.getBudgetAnalytics(budgetId),
    staleTime: 10 * 60 * 1000,
  });
};

export const useGoalAnalytics = (goalId: string) => {
  return useQuery({
    queryKey: ['goal-analytics', goalId],
    queryFn: () => analyticsService.getGoalAnalytics(goalId),
    staleTime: 15 * 60 * 1000,
  });
};