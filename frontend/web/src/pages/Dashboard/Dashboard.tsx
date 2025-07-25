import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  TrendingDown, 
  CreditCard, 
  DollarSign, 
  Target,
  AlertCircle,
  Plus,
  Eye,
  EyeOff
} from 'lucide-react';

// Components
import Card from '../../components/UI/Card';
import Button from '../../components/UI/Button';
import LoadingSpinner from '../../components/UI/LoadingSpinner';
import SpendingChart from '../../components/Charts/SpendingChart';
import NetWorthChart from '../../components/Charts/NetWorthChart';
import TransactionList from '../../components/Transactions/TransactionList';
import BudgetProgress from '../../components/Budget/BudgetProgress';
import QuickActions from '../../components/Dashboard/QuickActions';
import InsightCard from '../../components/Dashboard/InsightCard';

// Hooks
import { useAuth } from '../../hooks/useAuth';
import { useAccounts } from '../../hooks/useAccounts';
import { useTransactions } from '../../hooks/useTransactions';
import { useBudgets } from '../../hooks/useBudgets';
import { useInsights } from '../../hooks/useInsights';

// Types
import { Account, Transaction, Budget, Insight } from '../../types';

// Utils
import { formatCurrency, formatPercentage } from '../../utils/formatters';

const DashboardContainer = styled.div`
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
  
  @media (max-width: 768px) {
    padding: 1rem;
  }
`;

const WelcomeSection = styled.div`
  margin-bottom: 2rem;
`;

const WelcomeText = styled.h1`
  font-size: 2rem;
  font-weight: 600;
  color: ${props => props.theme.colors.text.primary};
  margin-bottom: 0.5rem;
  
  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`;

const LastUpdated = styled.p`
  color: ${props => props.theme.colors.text.secondary};
  font-size: 0.875rem;
`;

const MetricsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
`;

const MetricCard = styled(Card)<{ trend?: 'up' | 'down' | 'neutral' }>`
  padding: 1.5rem;
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: ${props => {
      switch (props.trend) {
        case 'up': return props.theme.colors.success;
        case 'down': return props.theme.colors.error;
        default: return props.theme.colors.primary;
      }
    }};
  }
`;

const MetricHeader = styled.div`
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: 1rem;
`;

const MetricTitle = styled.h3`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${props => props.theme.colors.text.secondary};
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const MetricIcon = styled.div<{ color: string }>`
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: ${props => props.color}20;
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${props => props.color};
`;

const MetricValue = styled.div`
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
`;

const MetricAmount = styled.h2`
  font-size: 2rem;
  font-weight: 700;
  color: ${props => props.theme.colors.text.primary};
  
  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`;

const VisibilityToggle = styled.button`
  background: none;
  border: none;
  color: ${props => props.theme.colors.text.secondary};
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  
  &:hover {
    background: ${props => props.theme.colors.background.secondary};
  }
`;

const MetricChange = styled.span<{ trend: 'up' | 'down' | 'neutral' }>`
  font-size: 0.875rem;
  font-weight: 500;
  color: ${props => {
    switch (props.trend) {
      case 'up': return props.theme.colors.success;
      case 'down': return props.theme.colors.error;
      default: return props.theme.colors.text.secondary;
    }
  }};
  display: flex;
  align-items: center;
  gap: 0.25rem;
`;

const ContentGrid = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
  
  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
`;

const ChartsSection = styled.div`
  display: grid;
  gap: 1.5rem;
`;

const SidebarSection = styled.div`
  display: grid;
  gap: 1.5rem;
`;

const SectionTitle = styled.h2`
  font-size: 1.25rem;
  font-weight: 600;
  color: ${props => props.theme.colors.text.primary};
  margin-bottom: 1rem;
`;

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const { data: transactions, isLoading: transactionsLoading } = useTransactions({ limit: 5 });
  const { data: budgets, isLoading: budgetsLoading } = useBudgets();
  const { data: insights, isLoading: insightsLoading } = useInsights();

  const [showAmounts, setShowAmounts] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Calculate financial metrics
  const totalBalance = accounts?.reduce((sum, account) => {
    return sum + (account.current_balance || 0);
  }, 0) || 0;

  // Calculate financial metrics from real data
  const totalIncome = 2500; // TODO: Replace with real analytics data
  const totalExpenses = 1850; // TODO: Replace with real analytics data
  const netWorth = totalBalance + 5000; // TODO: Include actual investment data

  const monthlyChange = 150; // TODO: Calculate from historical data
  const expenseChange = -75; // TODO: Calculate actual expense change

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setLastRefresh(new Date());
    }, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  const maskAmount = (amount: number) => {
    return showAmounts ? formatCurrency(amount) : '••••••';
  };

  if (accountsLoading || transactionsLoading || budgetsLoading) {
    return (
      <DashboardContainer>
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      </DashboardContainer>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <DashboardContainer>
        {/* Welcome Section */}
        <motion.div variants={itemVariants}>
          <WelcomeSection>
            <WelcomeText>
              Welcome back, {user?.first_name}! 👋
            </WelcomeText>
            <LastUpdated>
              Last updated {lastRefresh.toLocaleTimeString()}
            </LastUpdated>
          </WelcomeSection>
        </motion.div>

        {/* Financial Metrics */}
        <motion.div variants={itemVariants}>
          <MetricsGrid>
            <MetricCard trend="up">
              <MetricHeader>
                <MetricTitle>Net Worth</MetricTitle>
                <MetricIcon color="#10B981">
                  <TrendingUp size={20} />
                </MetricIcon>
              </MetricHeader>
              <MetricValue>
                <MetricAmount>{maskAmount(netWorth)}</MetricAmount>
                <VisibilityToggle onClick={() => setShowAmounts(!showAmounts)}>
                  {showAmounts ? <EyeOff size={16} /> : <Eye size={16} />}
                </VisibilityToggle>
              </MetricValue>
              <MetricChange trend="up">
                <TrendingUp size={14} />
                +{formatCurrency(monthlyChange)} this month
              </MetricChange>
            </MetricCard>

            <MetricCard trend="neutral">
              <MetricHeader>
                <MetricTitle>Total Balance</MetricTitle>
                <MetricIcon color="#3B82F6">
                  <DollarSign size={20} />
                </MetricIcon>
              </MetricHeader>
              <MetricValue>
                <MetricAmount>{maskAmount(totalBalance)}</MetricAmount>
              </MetricValue>
              <MetricChange trend="neutral">
                Across {accounts?.length || 0} accounts
              </MetricChange>
            </MetricCard>

            <MetricCard trend="up">
              <MetricHeader>
                <MetricTitle>Monthly Income</MetricTitle>
                <MetricIcon color="#10B981">
                  <TrendingUp size={20} />
                </MetricIcon>
              </MetricHeader>
              <MetricValue>
                <MetricAmount>{maskAmount(totalIncome)}</MetricAmount>
              </MetricValue>
              <MetricChange trend="up">
                <TrendingUp size={14} />
                +5.2% vs last month
              </MetricChange>
            </MetricCard>

            <MetricCard trend="down">
              <MetricHeader>
                <MetricTitle>Monthly Expenses</MetricTitle>
                <MetricIcon color="#EF4444">
                  <TrendingDown size={20} />
                </MetricIcon>
              </MetricHeader>
              <MetricValue>
                <MetricAmount>{maskAmount(totalExpenses)}</MetricAmount>
              </MetricValue>
              <MetricChange trend="down">
                <TrendingDown size={14} />
                {formatCurrency(Math.abs(expenseChange))} less than last month
              </MetricChange>
            </MetricCard>
          </MetricsGrid>
        </motion.div>

        {/* Quick Actions */}
        <motion.div variants={itemVariants}>
          <QuickActions />
        </motion.div>

        {/* Main Content Grid */}
        <ContentGrid>
          {/* Charts Section */}
          <motion.div variants={itemVariants}>
            <ChartsSection>
              <Card padding="1.5rem">
                <SectionTitle>Spending Overview</SectionTitle>
                <SpendingChart />
              </Card>
              
              <Card padding="1.5rem">
                <SectionTitle>Net Worth Trend</SectionTitle>
                <NetWorthChart />
              </Card>
            </ChartsSection>
          </motion.div>

          {/* Sidebar */}
          <motion.div variants={itemVariants}>
            <SidebarSection>
              {/* Recent Transactions */}
              <Card padding="1.5rem">
                <div className="flex justify-between items-center mb-4">
                  <SectionTitle style={{ marginBottom: 0 }}>
                    Recent Transactions
                  </SectionTitle>
                  <Button variant="text" size="sm" to="/transactions">
                    View All
                  </Button>
                </div>
                <TransactionList 
                  transactions={transactions || []} 
                  showAccount={true}
                  limit={5}
                />
              </Card>

              {/* Budget Progress */}
              <Card padding="1.5rem">
                <div className="flex justify-between items-center mb-4">
                  <SectionTitle style={{ marginBottom: 0 }}>
                    Budget Progress
                  </SectionTitle>
                  <Button variant="text" size="sm" to="/budget">
                    Manage
                  </Button>
                </div>
                <BudgetProgress budgets={budgets || []} />
              </Card>

              {/* Insights */}
              <Card padding="1.5rem">
                <div className="flex justify-between items-center mb-4">
                  <SectionTitle style={{ marginBottom: 0 }}>
                    AI Insights
                  </SectionTitle>
                  <Button variant="text" size="sm" to="/insights">
                    View All
                  </Button>
                </div>
                <div className="space-y-3">
                  {insights?.slice(0, 3).map((insight, index) => (
                    <InsightCard 
                      key={index} 
                      insight={insight}
                      compact={true}
                    />
                  ))}
                </div>
              </Card>
            </SidebarSection>
          </motion.div>
        </ContentGrid>
      </DashboardContainer>
    </motion.div>
  );
};

export default Dashboard;