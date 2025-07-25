import { ApiClient } from './api';
import { AnalyticsData } from '../hooks/useAnalytics';

class AnalyticsService {
  private api: ApiClient;

  constructor() {
    this.api = new ApiClient();
  }

  async getAnalytics(timeframe: 'month' | 'quarter' | 'year'): Promise<AnalyticsData> {
    try {
      const response = await this.api.get(`/api/v1/transactions/analysis?timeframe=${timeframe}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching analytics:', error);
      // Fallback to default values if API is unavailable
      return {
        monthlyIncome: 0,
        monthlyExpenses: 0,
        monthlyChange: 0,
        monthlyChangePercent: 0,
        expenseChange: 0,
        topCategories: [],
        incomeVsExpenses: [],
      };
    }
  }

  async getSpendingTrends(period: 'week' | 'month' | 'quarter') {
    try {
      const response = await this.api.get(`/api/v1/transactions/spending-trends?period=${period}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching spending trends:', error);
      return [];
    }
  }

  async getNetWorthHistory(period: 'month' | 'quarter' | 'year') {
    try {
      const response = await this.api.get(`/api/v1/accounts/net-worth-history?period=${period}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching net worth history:', error);
      return [];
    }
  }

  async getCategoryBreakdown(timeframe: 'month' | 'quarter' | 'year') {
    try {
      const response = await this.api.get(`/api/v1/transactions/category-breakdown?timeframe=${timeframe}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching category breakdown:', error);
      return [];
    }
  }

  async getBudgetPerformance() {
    try {
      const response = await this.api.get('/api/v1/budgets/performance');
      return response.data;
    } catch (error) {
      console.error('Error fetching budget performance:', error);
      return [];
    }
  }

  async getGoalProgress() {
    try {
      const response = await this.api.get('/api/v1/goals/progress');
      return response.data;
    } catch (error) {
      console.error('Error fetching goal progress:', error);
      return [];
    }
  }
}

export const analyticsService = new AnalyticsService();