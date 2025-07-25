import { useQuery } from 'react-query';
import { analyticsService } from '../services/analytics';

export interface AnalyticsData {
  monthlyIncome: number;
  monthlyExpenses: number;
  monthlyChange: number;
  monthlyChangePercent: number;
  expenseChange: number;
  topCategories: Array<{
    category: string;
    amount: number;
    percentage: number;
  }>;
  incomeVsExpenses: Array<{
    month: string;
    income: number;
    expenses: number;
  }>;
}

export function useAnalytics(timeframe: 'month' | 'quarter' | 'year' = 'month') {
  return useQuery<AnalyticsData, Error>(
    ['analytics', timeframe],
    () => analyticsService.getAnalytics(timeframe),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 3,
    }
  );
}

export function useSpendingTrends(period: 'week' | 'month' | 'quarter' = 'month') {
  return useQuery(
    ['spending-trends', period],
    () => analyticsService.getSpendingTrends(period),
    {
      staleTime: 5 * 60 * 1000,
      cacheTime: 10 * 60 * 1000,
      refetchOnWindowFocus: false,
    }
  );
}

export function useNetWorthHistory(period: 'month' | 'quarter' | 'year' = 'year') {
  return useQuery(
    ['net-worth-history', period],
    () => analyticsService.getNetWorthHistory(period),
    {
      staleTime: 10 * 60 * 1000, // 10 minutes
      cacheTime: 30 * 60 * 1000, // 30 minutes
      refetchOnWindowFocus: false,
    }
  );
}