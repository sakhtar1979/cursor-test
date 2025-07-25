"""
MintFlow Banking Service
Handles banking integrations, account aggregation, and transaction syncing.
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer
from pydantic import BaseModel, validator
import httpx
import structlog
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, Numeric, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import redis
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.configuration import Configuration
from plaid.api_client import ApiClient

# Configure logging
logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="MintFlow Banking Service",
    description="Banking integrations and account management service",
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
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/4"))

# Plaid Configuration
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID", "your-plaid-client-id")
PLAID_SECRET = os.getenv("PLAID_SECRET", "your-plaid-secret")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")

configuration = Configuration(
    host=getattr(plaid_api, PLAID_ENV, plaid_api.Environment.sandbox),
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET
    }
)
api_client = ApiClient(configuration)
plaid_client = plaid_api.PlaidApi(api_client)

# Database Models
class BankConnection(Base):
    __tablename__ = "bank_connections"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    provider = Column(String, nullable=False)  # plaid, yodlee, etc.
    institution_id = Column(String, nullable=False)
    institution_name = Column(String, nullable=False)
    access_token = Column(String, nullable=False)  # Encrypted
    item_id = Column(String)  # Plaid specific
    cursor = Column(String)  # For incremental updates
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime)
    error_code = Column(String)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    accounts = relationship("BankAccount", back_populates="connection")

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    
    id = Column(String, primary_key=True, index=True)
    connection_id = Column(String, ForeignKey("bank_connections.id"), nullable=False)
    user_id = Column(String, index=True, nullable=False)
    account_id = Column(String, nullable=False)  # External account ID
    name = Column(String, nullable=False)
    official_name = Column(String)
    type = Column(String, nullable=False)  # checking, savings, credit, investment
    subtype = Column(String)
    mask = Column(String)  # Last 4 digits
    current_balance = Column(Numeric(15, 2))
    available_balance = Column(Numeric(15, 2))
    credit_limit = Column(Numeric(15, 2))
    currency_code = Column(String, default="USD")
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    connection = relationship("BankConnection", back_populates="accounts")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    account_id = Column(String, ForeignKey("bank_accounts.id"), nullable=False)
    user_id = Column(String, index=True, nullable=False)
    transaction_id = Column(String, nullable=False)  # External transaction ID
    amount = Column(Numeric(15, 2), nullable=False)
    date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    merchant_name = Column(String)
    category = Column(String)
    subcategory = Column(String)
    account_owner = Column(String)
    pending = Column(Boolean, default=False)
    transaction_type = Column(String)  # debit, credit
    location = Column(Text)  # JSON string
    metadata = Column(Text)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id = Column(String, primary_key=True, index=True)
    connection_id = Column(String, ForeignKey("bank_connections.id"), nullable=False)
    sync_type = Column(String, nullable=False)  # accounts, transactions
    status = Column(String, nullable=False)  # success, error, partial
    new_items = Column(Integer, default=0)
    updated_items = Column(Integer, default=0)
    error_message = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class LinkTokenRequest(BaseModel):
    user_id: str

class ExchangeTokenRequest(BaseModel):
    public_token: str

class SyncRequest(BaseModel):
    connection_id: Optional[str] = None
    force: bool = False

class BankConnectionResponse(BaseModel):
    id: str
    user_id: str
    provider: str
    institution_id: str
    institution_name: str
    is_active: bool
    last_sync: Optional[datetime]
    error_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime

class BankAccountResponse(BaseModel):
    id: str
    connection_id: str
    account_id: str
    name: str
    official_name: Optional[str]
    type: str
    subtype: Optional[str]
    mask: Optional[str]
    current_balance: Optional[float]
    available_balance: Optional[float]
    credit_limit: Optional[float]
    currency_code: str
    is_active: bool
    last_sync: Optional[datetime]

class TransactionResponse(BaseModel):
    id: str
    account_id: str
    transaction_id: str
    amount: float
    date: datetime
    description: str
    merchant_name: Optional[str]
    category: Optional[str]
    subcategory: Optional[str]
    pending: bool
    transaction_type: Optional[str]

# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(security)):
    """Extract user from JWT token with proper verification"""
    try:
        # Import the JWT verification function from auth service
        import jwt
        import os
        
        # Get the secret key from environment
        secret_key = os.getenv("JWT_SECRET", "your-secret-key")
        
        # Decode and verify the JWT token
        payload = jwt.decode(
            token.credentials, 
            secret_key, 
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
            
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Utility Functions
def generate_id(prefix: str) -> str:
    """Generate unique ID with prefix"""
    import secrets
    return f"{prefix}_{secrets.token_urlsafe(16)}"

def encrypt_token(token: str) -> str:
    """Encrypt sensitive tokens (simplified for demo)"""
    # In production, use proper encryption
    import base64
    return base64.b64encode(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt sensitive tokens (simplified for demo)"""
    # In production, use proper decryption
    import base64
    return base64.b64decode(encrypted_token.encode()).decode()

async def sync_accounts(connection: BankConnection, db: Session):
    """Sync accounts for a bank connection"""
    try:
        access_token = decrypt_token(connection.access_token)
        
        if connection.provider == "plaid":
            request = AccountsGetRequest(access_token=access_token)
            response = plaid_client.accounts_get(request)
            
            for account in response['accounts']:
                # Check if account exists
                existing_account = db.query(BankAccount).filter(
                    BankAccount.connection_id == connection.id,
                    BankAccount.account_id == account['account_id']
                ).first()
                
                if existing_account:
                    # Update existing account
                    existing_account.current_balance = account['balances']['current']
                    existing_account.available_balance = account['balances']['available']
                    existing_account.credit_limit = account['balances'].get('limit')
                    existing_account.last_sync = datetime.utcnow()
                else:
                    # Create new account
                    new_account = BankAccount(
                        id=generate_id("acc"),
                        connection_id=connection.id,
                        user_id=connection.user_id,
                        account_id=account['account_id'],
                        name=account['name'],
                        official_name=account.get('official_name'),
                        type=account['type'],
                        subtype=account['subtype'],
                        mask=account['mask'],
                        current_balance=account['balances']['current'],
                        available_balance=account['balances']['available'],
                        credit_limit=account['balances'].get('limit'),
                        last_sync=datetime.utcnow()
                    )
                    db.add(new_account)
            
            connection.last_sync = datetime.utcnow()
            connection.error_code = None
            connection.error_message = None
            db.commit()
            
            logger.info("Accounts synced successfully", connection_id=connection.id)
            
    except Exception as e:
        logger.error("Failed to sync accounts", connection_id=connection.id, error=str(e))
        connection.error_code = "SYNC_ERROR"
        connection.error_message = str(e)
        db.commit()
        raise

async def sync_transactions(connection: BankConnection, db: Session, days_back: int = 30):
    """Sync transactions for a bank connection"""
    try:
        access_token = decrypt_token(connection.access_token)
        
        if connection.provider == "plaid":
            start_date = (datetime.utcnow() - timedelta(days=days_back)).date()
            end_date = datetime.utcnow().date()
            
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date
            )
            response = plaid_client.transactions_get(request)
            
            new_transactions = 0
            updated_transactions = 0
            
            for transaction in response['transactions']:
                # Find the account
                account = db.query(BankAccount).filter(
                    BankAccount.connection_id == connection.id,
                    BankAccount.account_id == transaction['account_id']
                ).first()
                
                if not account:
                    continue
                
                # Check if transaction exists
                existing_transaction = db.query(Transaction).filter(
                    Transaction.account_id == account.id,
                    Transaction.transaction_id == transaction['transaction_id']
                ).first()
                
                if existing_transaction:
                    # Update existing transaction
                    existing_transaction.amount = transaction['amount']
                    existing_transaction.description = transaction['name']
                    existing_transaction.merchant_name = transaction.get('merchant_name')
                    existing_transaction.pending = transaction['pending']
                    existing_transaction.updated_at = datetime.utcnow()
                    updated_transactions += 1
                else:
                    # Create new transaction
                    categories = transaction.get('category', [])
                    category = categories[0] if categories else None
                    subcategory = categories[1] if len(categories) > 1 else None
                    
                    new_transaction = Transaction(
                        id=generate_id("txn"),
                        account_id=account.id,
                        user_id=connection.user_id,
                        transaction_id=transaction['transaction_id'],
                        amount=transaction['amount'],
                        date=datetime.strptime(transaction['date'], '%Y-%m-%d'),
                        description=transaction['name'],
                        merchant_name=transaction.get('merchant_name'),
                        category=category,
                        subcategory=subcategory,
                        pending=transaction['pending'],
                        transaction_type='debit' if transaction['amount'] > 0 else 'credit',
                        location=json.dumps(transaction.get('location', {})),
                        metadata=json.dumps(transaction)
                    )
                    db.add(new_transaction)
                    new_transactions += 1
            
            # Log sync results
            sync_log = SyncLog(
                id=generate_id("sync"),
                connection_id=connection.id,
                sync_type="transactions",
                status="success",
                new_items=new_transactions,
                updated_items=updated_transactions,
                completed_at=datetime.utcnow()
            )
            db.add(sync_log)
            
            connection.last_sync = datetime.utcnow()
            db.commit()
            
            logger.info(
                "Transactions synced successfully",
                connection_id=connection.id,
                new=new_transactions,
                updated=updated_transactions
            )
            
    except Exception as e:
        logger.error("Failed to sync transactions", connection_id=connection.id, error=str(e))
        
        # Log sync error
        sync_log = SyncLog(
            id=generate_id("sync"),
            connection_id=connection.id,
            sync_type="transactions",
            status="error",
            error_message=str(e),
            completed_at=datetime.utcnow()
        )
        db.add(sync_log)
        db.commit()
        raise

# Routes
@app.post("/api/v1/banking/link-token")
async def create_link_token(
    request: LinkTokenRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Plaid link token for connecting bank accounts"""
    
    try:
        request_data = LinkTokenCreateRequest(
            products=[Products('transactions'), Products('accounts')],
            client_name="MintFlow",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(client_user_id=current_user)
        )
        
        response = plaid_client.link_token_create(request_data)
        
        return {
            "link_token": response['link_token'],
            "expiration": response['expiration']
        }
        
    except Exception as e:
        logger.error("Failed to create link token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create link token"
        )

@app.post("/api/v1/banking/exchange-token")
async def exchange_public_token(
    request: ExchangeTokenRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exchange public token for access token and create bank connection"""
    
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=request.public_token
        )
        exchange_response = plaid_client.item_public_token_exchange(exchange_request)
        
        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']
        
        # Get institution info
        accounts_request = AccountsGetRequest(access_token=access_token)
        accounts_response = plaid_client.accounts_get(accounts_request)
        
        institution_id = accounts_response['item']['institution_id']
        
        # Create bank connection
        connection = BankConnection(
            id=generate_id("conn"),
            user_id=current_user,
            provider="plaid",
            institution_id=institution_id,
            institution_name="Bank",  # Would fetch actual name from Plaid
            access_token=encrypt_token(access_token),
            item_id=item_id
        )
        
        db.add(connection)
        db.commit()
        
        # Schedule initial sync
        background_tasks.add_task(sync_accounts, connection, db)
        background_tasks.add_task(sync_transactions, connection, db)
        
        logger.info("Bank connection created", connection_id=connection.id, user_id=current_user)
        
        return BankConnectionResponse(
            id=connection.id,
            user_id=connection.user_id,
            provider=connection.provider,
            institution_id=connection.institution_id,
            institution_name=connection.institution_name,
            is_active=connection.is_active,
            last_sync=connection.last_sync,
            error_code=connection.error_code,
            error_message=connection.error_message,
            created_at=connection.created_at
        )
        
    except Exception as e:
        logger.error("Failed to exchange token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange token"
        )

@app.get("/api/v1/banking/connections", response_model=List[BankConnectionResponse])
async def get_connections(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bank connections for the current user"""
    
    connections = db.query(BankConnection).filter(
        BankConnection.user_id == current_user
    ).all()
    
    return [
        BankConnectionResponse(
            id=conn.id,
            user_id=conn.user_id,
            provider=conn.provider,
            institution_id=conn.institution_id,
            institution_name=conn.institution_name,
            is_active=conn.is_active,
            last_sync=conn.last_sync,
            error_code=conn.error_code,
            error_message=conn.error_message,
            created_at=conn.created_at
        )
        for conn in connections
    ]

@app.get("/api/v1/banking/accounts", response_model=List[BankAccountResponse])
async def get_accounts(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bank accounts for the current user"""
    
    accounts = db.query(BankAccount).filter(
        BankAccount.user_id == current_user,
        BankAccount.is_active == True
    ).all()
    
    return [
        BankAccountResponse(
            id=account.id,
            connection_id=account.connection_id,
            account_id=account.account_id,
            name=account.name,
            official_name=account.official_name,
            type=account.type,
            subtype=account.subtype,
            mask=account.mask,
            current_balance=float(account.current_balance) if account.current_balance else None,
            available_balance=float(account.available_balance) if account.available_balance else None,
            credit_limit=float(account.credit_limit) if account.credit_limit else None,
            currency_code=account.currency_code,
            is_active=account.is_active,
            last_sync=account.last_sync
        )
        for account in accounts
    ]

@app.get("/api/v1/banking/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    account_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get transactions for the current user"""
    
    query = db.query(Transaction).filter(Transaction.user_id == current_user)
    
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()
    
    return [
        TransactionResponse(
            id=txn.id,
            account_id=txn.account_id,
            transaction_id=txn.transaction_id,
            amount=float(txn.amount),
            date=txn.date,
            description=txn.description,
            merchant_name=txn.merchant_name,
            category=txn.category,
            subcategory=txn.subcategory,
            pending=txn.pending,
            transaction_type=txn.transaction_type
        )
        for txn in transactions
    ]

@app.post("/api/v1/banking/sync")
async def sync_data(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync bank data for user connections"""
    
    query = db.query(BankConnection).filter(
        BankConnection.user_id == current_user,
        BankConnection.is_active == True
    )
    
    if request.connection_id:
        query = query.filter(BankConnection.id == request.connection_id)
    
    connections = query.all()
    
    if not connections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active connections found"
        )
    
    # Schedule sync tasks
    for connection in connections:
        # Check if sync is needed (avoid too frequent syncs unless forced)
        if not request.force and connection.last_sync:
            time_since_sync = datetime.utcnow() - connection.last_sync
            if time_since_sync < timedelta(hours=1):
                continue
        
        background_tasks.add_task(sync_accounts, connection, db)
        background_tasks.add_task(sync_transactions, connection, db)
    
    return {
        "message": f"Sync initiated for {len(connections)} connections",
        "connections": [conn.id for conn in connections]
    }

@app.delete("/api/v1/banking/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bank connection"""
    
    connection = db.query(BankConnection).filter(
        BankConnection.id == connection_id,
        BankConnection.user_id == current_user
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Soft delete - deactivate instead of deleting
    connection.is_active = False
    
    # Deactivate associated accounts
    db.query(BankAccount).filter(
        BankAccount.connection_id == connection_id
    ).update({"is_active": False})
    
    db.commit()
    
    logger.info("Bank connection deactivated", connection_id=connection_id, user_id=current_user)
    
    return {"message": "Connection deleted successfully"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "banking"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV") == "development"
    )