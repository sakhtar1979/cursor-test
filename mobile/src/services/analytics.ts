/**
 * Analytics Service for MintFlow Mobile App
 * Handles all analytics and insights API calls
 */

import { apiService } from './api';
import { AnalyticsData, AnalyticsFilters, SpendingData, BudgetStatus } from '../hooks/useAnalytics';

export interface SpendingInsight {
  type: 'trend' | 'anomaly' | 'recommendation';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  category: string;
  amount?: number;
  percentage?: number;
  actionable: boolean;
  suggestion?: string;
}

export interface BudgetPerformance {
  overallStatus: 'on_track' | 'warning' | 'over_budget';
  totalBudgeted: number;
  totalSpent: number;
  remainingBudget: number;
  categoriesOverBudget: number;
  averageSpendingRate: number;
  projectedMonthEnd: number;
  budgets: BudgetStatus[];
}

export interface GoalProgress {
  goalId: string;
  title: string;
  type: 'savings' | 'debt_payoff' | 'investment';
  targetAmount: number;
  currentAmount: number;
  percentage: number;
  targetDate: string;
  onTrack: boolean;
  monthlyContribution: number;
  requiredMonthlyContribution: number;
  estimatedCompletionDate: string;
}

export interface AnalyticsPreferences {
  excludeCategories: string[];
  includeInvestments: boolean;
  excludeTransfers: boolean;
  defaultTimeframe: 'month' | 'quarter' | 'year';
  currency: string;
  notifications: {
    budgetAlerts: boolean;
    spendingInsights: boolean;
    goalReminders: boolean;
  };
}

class AnalyticsService {
  private baseURL = '/api/v1/analytics';

  async getAnalytics(filters: AnalyticsFilters): Promise<AnalyticsData> {
    try {
      const response = await apiService.post(`${this.baseURL}/dashboard`, {
        dateRange: {
          start: filters.dateRange.start.toISOString(),
          end: filters.dateRange.end.toISOString(),
        },
        accountIds: filters.accountIds,
        categories: filters.categories,
        includeInvestments: filters.includeInvestments,
        excludeTransfers: filters.excludeTransfers,
      });

      return this.transformAnalyticsData(response.data);
    } catch (error) {
      console.error('Failed to fetch analytics data:', error);
      throw new Error('Failed to load analytics data');
    }
  }

  async getSpendingInsights(filters: AnalyticsFilters): Promise<SpendingInsight[]> {
    try {
      const response = await apiService.post(`${this.baseURL}/insights/spending`, {
        dateRange: {
          start: filters.dateRange.start.toISOString(),
          end: filters.dateRange.end.toISOString(),
        },
        categories: filters.categories,
      });

      return response.data.insights || [];
    } catch (error) {
      console.error('Failed to fetch spending insights:', error);
      return [];
    }
  }

  async getBudgetPerformance(filters: AnalyticsFilters): Promise<BudgetPerformance> {
    try {
      const response = await apiService.post(`${this.baseURL}/budgets/performance`, {
        dateRange: {
          start: filters.dateRange.start.toISOString(),
          end: filters.dateRange.end.toISOString(),
        },
      });

      return response.data;
    } catch (error) {
      console.error('Failed to fetch budget performance:', error);
      throw new Error('Failed to load budget performance');
    }
  }

  async getGoalsProgress(): Promise<GoalProgress[]> {
    try {
      const response = await apiService.get(`${this.baseURL}/goals/progress`);
      return response.data.goals || [];
    } catch (error) {
      console.error('Failed to fetch goals progress:', error);
      return [];
    }
  }

  async getBudgetAnalytics(budgetId: string): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/budgets/${budgetId}/analytics`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch analytics for budget ${budgetId}:`, error);
      throw new Error('Failed to load budget analytics');
    }
  }

  async getGoalAnalytics(goalId: string): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/goals/${goalId}/analytics`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch analytics for goal ${goalId}:`, error);
      throw new Error('Failed to load goal analytics');
    }
  }

  async getCategoryTrends(categoryId: string, timeframe: string): Promise<any> {
    try {
      const response = await apiService.get(
        `${this.baseURL}/categories/${categoryId}/trends?timeframe=${timeframe}`
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch trends for category ${categoryId}:`, error);
      throw new Error('Failed to load category trends');
    }
  }

  async getNetWorthHistory(timeframe: string): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/net-worth?timeframe=${timeframe}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch net worth history:', error);
      throw new Error('Failed to load net worth history');
    }
  }

  async getCashFlowAnalysis(filters: AnalyticsFilters): Promise<any> {
    try {
      const response = await apiService.post(`${this.baseURL}/cash-flow`, {
        dateRange: {
          start: filters.dateRange.start.toISOString(),
          end: filters.dateRange.end.toISOString(),
        },
        accountIds: filters.accountIds,
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch cash flow analysis:', error);
      throw new Error('Failed to load cash flow analysis');
    }
  }

  async getFinancialHealthScore(): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/health-score`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch financial health score:', error);
      throw new Error('Failed to load financial health score');
    }
  }

  async updatePreferences(preferences: AnalyticsPreferences): Promise<void> {
    try {
      await apiService.put(`${this.baseURL}/preferences`, preferences);
    } catch (error) {
      console.error('Failed to update analytics preferences:', error);
      throw new Error('Failed to update preferences');
    }
  }

  async getPreferences(): Promise<AnalyticsPreferences> {
    try {
      const response = await apiService.get(`${this.baseURL}/preferences`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch analytics preferences:', error);
      throw new Error('Failed to load preferences');
    }
  }

  async exportData(format: 'csv' | 'pdf' | 'excel', filters: AnalyticsFilters): Promise<string> {
    try {
      const response = await apiService.post(`${this.baseURL}/export`, {
        format,
        dateRange: {
          start: filters.dateRange.start.toISOString(),
          end: filters.dateRange.end.toISOString(),
        },
        accountIds: filters.accountIds,
        categories: filters.categories,
      });
      
      return response.data.downloadUrl;
    } catch (error) {
      console.error('Failed to export analytics data:', error);
      throw new Error('Failed to export data');
    }
  }

  async getCustomReport(reportConfig: any): Promise<any> {
    try {
      const response = await apiService.post(`${this.baseURL}/reports/custom`, reportConfig);
      return response.data;
    } catch (error) {
      console.error('Failed to generate custom report:', error);
      throw new Error('Failed to generate custom report');
    }
  }

  async getRecurringTransactions(): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/recurring-transactions`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch recurring transactions:', error);
      throw new Error('Failed to load recurring transactions');
    }
  }

  async getPredictiveInsights(): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/insights/predictive`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch predictive insights:', error);
      return { insights: [] };
    }
  }

  async getSpendingForecast(months: number): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/forecast/spending?months=${months}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch spending forecast:', error);
      throw new Error('Failed to load spending forecast');
    }
  }

  async getBenchmarkComparison(): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseURL}/benchmark`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch benchmark comparison:', error);
      return { benchmarks: [] };
    }
  }

  private transformAnalyticsData(rawData: any): AnalyticsData {
    return {
      totalBalance: rawData.total_balance || 0,
      monthlyIncome: rawData.monthly_income || 0,
      monthlyExpenses: rawData.monthly_expenses || 0,
      savingsRate: rawData.savings_rate || 0,
      spendingByCategory: this.transformSpendingData(rawData.spending_by_category || []),
      incomeVsExpenses: rawData.income_vs_expenses || [],
      budgetStatus: rawData.budget_status || [],
      netWorthTrend: rawData.net_worth_trend || [],
      cashFlowTrend: rawData.cash_flow_trend || [],
      topExpenseCategories: rawData.top_expense_categories || [],
      financialHealthScore: rawData.financial_health_score || 0,
      creditScore: rawData.credit_score,
      lastUpdated: rawData.last_updated || new Date().toISOString(),
    };
  }

  private transformSpendingData(rawSpending: any[]): SpendingData[] {
    const colors = [
      '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
      '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
    ];

    return rawSpending.map((item, index) => ({
      category: item.category,
      amount: item.amount || 0,
      percentage: item.percentage || 0,
      color: colors[index % colors.length],
      trend: item.trend || 'stable',
      previousAmount: item.previous_amount || 0,
    }));
  }

  // Mock data fallback for development/testing
  private getMockAnalyticsData(): AnalyticsData {
    return {
      totalBalance: 15250.75,
      monthlyIncome: 6500.00,
      monthlyExpenses: 4200.50,
      savingsRate: 35.4,
      spendingByCategory: [
        { category: 'Food & Dining', amount: 850, percentage: 20.2, color: '#FF6B6B', trend: 'up', previousAmount: 750 },
        { category: 'Transportation', amount: 650, percentage: 15.5, color: '#4ECDC4', trend: 'down', previousAmount: 720 },
        { category: 'Entertainment', amount: 420, percentage: 10.0, color: '#45B7D1', trend: 'stable', previousAmount: 415 },
        { category: 'Shopping', amount: 380, percentage: 9.0, color: '#96CEB4', trend: 'up', previousAmount: 320 },
        { category: 'Bills & Utilities', amount: 1200, percentage: 28.6, color: '#FFEAA7', trend: 'stable', previousAmount: 1180 },
      ],
      incomeVsExpenses: [
        { month: 'Jan', income: 6500, expenses: 4100, savings: 2400, net: 2400 },
        { month: 'Feb', income: 6500, expenses: 4300, savings: 2200, net: 2200 },
        { month: 'Mar', income: 6800, expenses: 4200, savings: 2600, net: 2600 },
        { month: 'Apr', income: 6500, expenses: 4400, savings: 2100, net: 2100 },
        { month: 'May', income: 6500, expenses: 4200, savings: 2300, net: 2300 },
      ],
      budgetStatus: [],
      netWorthTrend: [],
      cashFlowTrend: [],
      topExpenseCategories: ['Food & Dining', 'Bills & Utilities', 'Transportation'],
      financialHealthScore: 78,
      creditScore: 742,
      lastUpdated: new Date().toISOString(),
    };
  }
}

export const analyticsService = new AnalyticsService();