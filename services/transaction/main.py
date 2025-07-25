"""
MintFlow Transaction Service
Handles transaction processing, categorization, analytics, and budgeting.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer
from pydantic import BaseModel, validator
import structlog
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, Numeric, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import redis
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import kafka
from kafka import KafkaProducer, KafkaConsumer
import pickle

# Configure logging
logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="MintFlow Transaction Service",
    description="Transaction processing and analytics service",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mintflow:password@postgres:5432/mintflow")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/3"))

# Kafka setup
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Database Models
class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    period = Column(String, nullable=False)  # monthly, weekly, yearly
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=0)
    target_date = Column(DateTime)
    category = Column(String)  # emergency, vacation, house, etc.
    is_achieved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TransactionCategory(Base):
    __tablename__ = "transaction_categories"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    parent_category = Column(String)
    description = Column(Text)
    keywords = Column(Text)  # JSON array of keywords
    is_income = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TransactionRule(Base):
    __tablename__ = "transaction_rules"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    conditions = Column(Text, nullable=False)  # JSON conditions
    actions = Column(Text, nullable=False)  # JSON actions
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class BudgetAlert(Base):
    __tablename__ = "budget_alerts"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    budget_id = Column(String, ForeignKey("budgets.id"), nullable=False)
    alert_type = Column(String, nullable=False)  # warning, exceeded
    threshold = Column(Numeric(5, 2), nullable=False)  # percentage
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class BudgetCreate(BaseModel):
    name: str
    category: str
    amount: Decimal
    period: str
    start_date: datetime
    end_date: Optional[datetime] = None
    
    @validator('period')
    def validate_period(cls, v):
        if v not in ['weekly', 'monthly', 'yearly']:
            raise ValueError('Period must be weekly, monthly, or yearly')
        return v

class GoalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_amount: Decimal
    target_date: Optional[datetime] = None
    category: Optional[str] = None

class TransactionCategoryUpdate(BaseModel):
    transaction_id: str
    category: str
    subcategory: Optional[str] = None

class BudgetResponse(BaseModel):
    id: str
    user_id: str
    name: str
    category: str
    amount: float
    period: str
    start_date: datetime
    end_date: Optional[datetime]
    is_active: bool
    spent_amount: Optional[float] = 0
    remaining_amount: Optional[float] = 0
    percentage_used: Optional[float] = 0

class GoalResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    target_amount: float
    current_amount: float
    target_date: Optional[datetime]
    category: Optional[str]
    is_achieved: bool
    progress_percentage: float

class SpendingAnalysis(BaseModel):
    period: str
    total_spent: float
    total_income: float
    net_amount: float
    top_categories: List[Dict[str, Any]]
    monthly_trend: List[Dict[str, Any]]

class TransactionInsight(BaseModel):
    type: str  # spending_pattern, unusual_transaction, budget_alert
    title: str
    description: str
    amount: Optional[float]
    category: Optional[str]
    confidence: float
    action_required: bool

# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(security)):
    """Extract user from JWT token (simplified for demo)"""
    try:
        import jwt
        payload = jwt.decode(token.credentials, options={"verify_signature": False})
        return payload.get("sub")
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Utility Functions
def generate_id(prefix: str) -> str:
    """Generate unique ID with prefix"""
    import secrets
    return f"{prefix}_{secrets.token_urlsafe(16)}"

class TransactionCategorizer:
    """AI-powered transaction categorization"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.categories = None
        self.load_or_train_model()
    
    def load_or_train_model(self):
        """Load existing model or train a new one"""
        try:
            # Try to load existing model
            with open('/app/models/categorizer_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            with open('/app/models/categorizer_vectorizer.pkl', 'rb') as f:
                self.vectorizer = pickle.load(f)
            with open('/app/models/categorizer_categories.pkl', 'rb') as f:
                self.categories = pickle.load(f)
            logger.info("Loaded existing categorization model")
        except:
            logger.info("Training new categorization model")
            self.train_model()
    
    def train_model(self):
        """Train categorization model with sample data"""
        # Sample training data - in production, use real transaction data
        training_data = [
            ("STARBUCKS COFFEE", "Food & Dining", "Coffee Shops"),
            ("AMAZON.COM", "Shopping", "Online"),
            ("SHELL GAS STATION", "Transportation", "Gas"),
            ("NETFLIX.COM", "Entertainment", "Streaming"),
            ("WHOLE FOODS", "Food & Dining", "Groceries"),
            ("UBER RIDE", "Transportation", "Rideshare"),
            ("ATM WITHDRAWAL", "Cash & ATM", "ATM"),
            ("PAYCHECK DEPOSIT", "Income", "Salary"),
            ("ELECTRIC COMPANY", "Bills & Utilities", "Electric"),
            ("RENT PAYMENT", "Bills & Utilities", "Rent"),
            # Add more training data...
        ]
        
        descriptions = [item[0] for item in training_data]
        categories = [item[1] for item in training_data]
        
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        X = self.vectorizer.fit_transform(descriptions)
        
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X, categories)
        
        self.categories = list(set(categories))
        
        # Save model
        os.makedirs('/app/models', exist_ok=True)
        with open('/app/models/categorizer_model.pkl', 'wb') as f:
            pickle.dump(self.model, f)
        with open('/app/models/categorizer_vectorizer.pkl', 'wb') as f:
            pickle.dump(self.vectorizer, f)
        with open('/app/models/categorizer_categories.pkl', 'wb') as f:
            pickle.dump(self.categories, f)
    
    def categorize(self, description: str, merchant_name: str = None) -> tuple:
        """Categorize a transaction"""
        if not self.model or not self.vectorizer:
            return "Other", None
        
        text = f"{description} {merchant_name or ''}".strip()
        X = self.vectorizer.transform([text])
        category = self.model.predict(X)[0]
        confidence = max(self.model.predict_proba(X)[0])
        
        return category, confidence

# Initialize categorizer
categorizer = TransactionCategorizer()

def analyze_spending_patterns(user_id: str, db: Session) -> List[TransactionInsight]:
    """Analyze user spending patterns and generate insights"""
    insights = []
    
    # Get recent transactions
    recent_transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= datetime.utcnow() - timedelta(days=30)
    ).all()
    
    if not recent_transactions:
        return insights
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame([{
        'amount': float(t.amount),
        'date': t.date,
        'category': t.category,
        'description': t.description
    } for t in recent_transactions])
    
    # Unusual spending analysis
    for category in df['category'].unique():
        if category is None:
            continue
            
        category_data = df[df['category'] == category]
        if len(category_data) < 3:
            continue
        
        mean_amount = category_data['amount'].mean()
        std_amount = category_data['amount'].std()
        
        # Find unusual transactions (more than 2 standard deviations)
        unusual = category_data[category_data['amount'] > mean_amount + 2 * std_amount]
        
        for _, transaction in unusual.iterrows():
            insights.append(TransactionInsight(
                type="unusual_transaction",
                title=f"Unusual {category} spending",
                description=f"${transaction['amount']:.2f} spent on {transaction['description']} is higher than usual",
                amount=transaction['amount'],
                category=category,
                confidence=0.8,
                action_required=False
            ))
    
    # Spending trend analysis
    daily_spending = df.groupby(df['date'].dt.date)['amount'].sum()
    if len(daily_spending) > 7:
        recent_avg = daily_spending.tail(7).mean()
        previous_avg = daily_spending.iloc[-14:-7].mean() if len(daily_spending) > 14 else recent_avg
        
        if recent_avg > previous_avg * 1.2:
            insights.append(TransactionInsight(
                type="spending_pattern",
                title="Increased spending detected",
                description=f"Your daily spending has increased by {((recent_avg/previous_avg - 1) * 100):.1f}% this week",
                amount=recent_avg - previous_avg,
                category=None,
                confidence=0.9,
                action_required=True
            ))
    
    return insights

async def check_budget_alerts(user_id: str, db: Session):
    """Check for budget alerts and send notifications"""
    current_date = datetime.utcnow()
    
    # Get active budgets
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.is_active == True
    ).all()
    
    for budget in budgets:
        # Calculate budget period
        if budget.period == 'monthly':
            period_start = current_date.replace(day=1)
        elif budget.period == 'weekly':
            period_start = current_date - timedelta(days=current_date.weekday())
        else:  # yearly
            period_start = current_date.replace(month=1, day=1)
        
        # Calculate spending in this period
        spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.category == budget.category,
            Transaction.date >= period_start,
            Transaction.amount > 0  # Only spending, not income
        ).scalar() or 0
        
        spent_percentage = (float(spent) / float(budget.amount)) * 100
        
        # Check for alerts
        alert_thresholds = [80, 100]  # 80% warning, 100% exceeded
        
        for threshold in alert_thresholds:
            if spent_percentage >= threshold:
                # Check if alert already sent
                existing_alert = db.query(BudgetAlert).filter(
                    BudgetAlert.budget_id == budget.id,
                    BudgetAlert.threshold == threshold,
                    BudgetAlert.created_at >= period_start,
                    BudgetAlert.is_sent == True
                ).first()
                
                if not existing_alert:
                    # Create and send alert
                    alert = BudgetAlert(
                        id=generate_id("alert"),
                        user_id=user_id,
                        budget_id=budget.id,
                        alert_type="warning" if threshold < 100 else "exceeded",
                        threshold=threshold,
                        is_sent=True,
                        sent_at=current_date
                    )
                    db.add(alert)
                    
                    # Send notification via Kafka
                    notification_data = {
                        "user_id": user_id,
                        "type": "budget_alert",
                        "title": f"Budget Alert: {budget.name}",
                        "message": f"You've spent {spent_percentage:.1f}% of your {budget.name} budget",
                        "data": {
                            "budget_id": budget.id,
                            "spent_amount": float(spent),
                            "budget_amount": float(budget.amount),
                            "category": budget.category
                        }
                    }
                    
                    producer.send('notifications', notification_data)
    
    db.commit()

# Routes
@app.post("/api/v1/transactions/budgets", response_model=BudgetResponse)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new budget"""
    
    budget = Budget(
        id=generate_id("budget"),
        user_id=current_user,
        name=budget_data.name,
        category=budget_data.category,
        amount=budget_data.amount,
        period=budget_data.period,
        start_date=budget_data.start_date,
        end_date=budget_data.end_date
    )
    
    db.add(budget)
    db.commit()
    db.refresh(budget)
    
    logger.info("Budget created", budget_id=budget.id, user_id=current_user)
    
    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        name=budget.name,
        category=budget.category,
        amount=float(budget.amount),
        period=budget.period,
        start_date=budget.start_date,
        end_date=budget.end_date,
        is_active=budget.is_active
    )

@app.get("/api/v1/transactions/budgets", response_model=List[BudgetResponse])
async def get_budgets(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user budgets with spending analysis"""
    
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user,
        Budget.is_active == True
    ).all()
    
    budget_responses = []
    current_date = datetime.utcnow()
    
    for budget in budgets:
        # Calculate period
        if budget.period == 'monthly':
            period_start = current_date.replace(day=1)
        elif budget.period == 'weekly':
            period_start = current_date - timedelta(days=current_date.weekday())
        else:  # yearly
            period_start = current_date.replace(month=1, day=1)
        
        # Calculate spending
        spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user,
            Transaction.category == budget.category,
            Transaction.date >= period_start,
            Transaction.amount > 0
        ).scalar() or 0
        
        spent_amount = float(spent)
        budget_amount = float(budget.amount)
        remaining = budget_amount - spent_amount
        percentage = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0
        
        budget_responses.append(BudgetResponse(
            id=budget.id,
            user_id=budget.user_id,
            name=budget.name,
            category=budget.category,
            amount=budget_amount,
            period=budget.period,
            start_date=budget.start_date,
            end_date=budget.end_date,
            is_active=budget.is_active,
            spent_amount=spent_amount,
            remaining_amount=remaining,
            percentage_used=percentage
        ))
    
    return budget_responses

@app.post("/api/v1/transactions/goals", response_model=GoalResponse)
async def create_goal(
    goal_data: GoalCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new financial goal"""
    
    goal = Goal(
        id=generate_id("goal"),
        user_id=current_user,
        name=goal_data.name,
        description=goal_data.description,
        target_amount=goal_data.target_amount,
        target_date=goal_data.target_date,
        category=goal_data.category
    )
    
    db.add(goal)
    db.commit()
    db.refresh(goal)
    
    logger.info("Goal created", goal_id=goal.id, user_id=current_user)
    
    progress = (float(goal.current_amount) / float(goal.target_amount)) * 100
    
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        name=goal.name,
        description=goal.description,
        target_amount=float(goal.target_amount),
        current_amount=float(goal.current_amount),
        target_date=goal.target_date,
        category=goal.category,
        is_achieved=goal.is_achieved,
        progress_percentage=progress
    )

@app.put("/api/v1/transactions/categorize")
async def update_transaction_category(
    category_update: TransactionCategoryUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update transaction category"""
    
    # Update the transaction in the banking service and send to Kafka
    # This implementation sends updates via message queue for async processing
    
    update_data = {
        "user_id": current_user,
        "transaction_id": category_update.transaction_id,
        "category": category_update.category,
        "subcategory": category_update.subcategory,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    producer.send('transaction_updates', update_data)
    
    logger.info("Transaction category updated", 
                transaction_id=category_update.transaction_id,
                user_id=current_user)
    
    return {"message": "Category updated successfully"}

@app.get("/api/v1/transactions/analysis", response_model=SpendingAnalysis)
async def get_spending_analysis(
    period: str = "monthly",
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get spending analysis for the user"""
    
    # Calculate period
    current_date = datetime.utcnow()
    if period == "monthly":
        start_date = current_date.replace(day=1)
    elif period == "weekly":
        start_date = current_date - timedelta(days=current_date.weekday())
    else:  # yearly
        start_date = current_date.replace(month=1, day=1)
    
    # Get transactions for the period
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user,
        Transaction.date >= start_date
    ).all()
    
    if not transactions:
        return SpendingAnalysis(
            period=period,
            total_spent=0,
            total_income=0,
            net_amount=0,
            top_categories=[],
            monthly_trend=[]
        )
    
    # Calculate totals
    total_spent = sum(float(t.amount) for t in transactions if t.amount > 0)
    total_income = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
    net_amount = total_income - total_spent
    
    # Top categories
    category_spending = {}
    for t in transactions:
        if t.amount > 0 and t.category:  # Only spending
            category_spending[t.category] = category_spending.get(t.category, 0) + float(t.amount)
    
    top_categories = [
        {"category": cat, "amount": amount, "percentage": (amount/total_spent)*100 if total_spent > 0 else 0}
        for cat, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Monthly trend (last 6 months)
    monthly_trend = []
    for i in range(6):
        month_start = (current_date - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_transactions = [t for t in transactions 
                            if month_start <= t.date <= month_end]
        
        month_spent = sum(float(t.amount) for t in month_transactions if t.amount > 0)
        
        monthly_trend.append({
            "month": month_start.strftime("%Y-%m"),
            "amount": month_spent
        })
    
    monthly_trend.reverse()  # Oldest first
    
    return SpendingAnalysis(
        period=period,
        total_spent=total_spent,
        total_income=total_income,
        net_amount=net_amount,
        top_categories=top_categories,
        monthly_trend=monthly_trend
    )

@app.get("/api/v1/transactions/insights", response_model=List[TransactionInsight])
async def get_insights(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered transaction insights"""
    
    insights = analyze_spending_patterns(current_user, db)
    
    return insights

@app.post("/api/v1/transactions/check-budgets")
async def check_budgets(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check budget alerts for the user"""
    
    background_tasks.add_task(check_budget_alerts, current_user, db)
    
    return {"message": "Budget check initiated"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "transaction"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV") == "development"
    )