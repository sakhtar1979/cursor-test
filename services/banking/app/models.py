"""
Banking Service Database Models
Defines all database schemas for financial institutions, accounts, and transactions.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, Index, Numeric, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ENUM
import uuid
import enum
from .config import fernet, settings

Base = declarative_base()


class AccountType(enum.Enum):
    """Account type enumeration."""
    DEPOSITORY = "depository"
    CREDIT = "credit"
    LOAN = "loan"
    INVESTMENT = "investment"
    OTHER = "other"


class AccountSubtype(enum.Enum):
    """Account subtype enumeration."""
    # Depository
    CHECKING = "checking"
    SAVINGS = "savings"
    HSA = "hsa"
    CD = "cd"
    MONEY_MARKET = "money_market"
    PAYPAL = "paypal"
    PREPAID = "prepaid"
    
    # Credit
    CREDIT_CARD = "credit_card"
    
    # Loan
    AUTO = "auto"
    BUSINESS = "business"
    COMMERCIAL = "commercial"
    CONSTRUCTION = "construction"
    CONSUMER = "consumer"
    HOME_EQUITY = "home_equity"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OVERDRAFT = "overdraft"
    STUDENT = "student"
    
    # Investment
    INVESTMENT_401A = "401a"
    INVESTMENT_401K = "401k"
    INVESTMENT_403B = "403b"
    INVESTMENT_457B = "457b"
    INVESTMENT_529 = "529"
    BROKERAGE = "brokerage"
    CASH_ISA = "cash_isa"
    EDUCATION_SAVINGS_ACCOUNT = "education_savings_account"
    FIXED_ANNUITY = "fixed_annuity"
    GIC = "gic"
    HEALTH_REIMBURSEMENT_ARRANGEMENT = "health_reimbursement_arrangement"
    IRA = "ira"
    ISA = "isa"
    KEOGH = "keogh"
    LIF = "lif"
    LIRA = "lira"
    LRIF = "lrif"
    LRSP = "lrsp"
    NON_CUSTODIAL_WALLET = "non_custodial_wallet"
    NON_TAXABLE_BROKERAGE_ACCOUNT = "non_taxable_brokerage_account"
    PENSION = "pension"
    PLAN = "plan"
    PRIF = "prif"
    PROFIT_SHARING_PLAN = "profit_sharing_plan"
    RDSP = "rdsp"
    RESP = "resp"
    RETIREMENT = "retirement"
    RLIF = "rlif"
    ROTH = "roth"
    ROTH_401K = "roth_401k"
    RRIF = "rrif"
    RRSP = "rrsp"
    SARSEP = "sarsep"
    SEP_IRA = "sep_ira"
    SIMPLE_IRA = "simple_ira"
    SIPP = "sipp"
    STOCK_PLAN = "stock_plan"
    TFSA = "tfsa"
    TRUST = "trust"
    UGMA = "ugma"
    UTMA = "utma"
    VARIABLE_ANNUITY = "variable_annuity"


class TransactionCategory(enum.Enum):
    """Transaction category enumeration."""
    AIRLINE = "airline"
    AMUSEMENT = "amusement"
    ATM = "atm"
    BANK_FEES = "bank_fees"
    BILLS = "bills"
    CASH_ADVANCE = "cash_advance"
    ENTERTAINMENT = "entertainment"
    FAST_FOOD = "fast_food"
    FINANCE = "finance"
    FOOD_AND_DRINK = "food_and_drink"
    GAS_STATION = "gas_station"
    GROCERIES = "groceries"
    HEALTH = "health"
    HOTEL = "hotel"
    INTEREST = "interest"
    OVERDRAFT = "overdraft"
    PAYROLL = "payroll"
    PROFESSIONAL_SERVICES = "professional_services"
    PURCHASE = "purchase"
    RECREATION = "recreation"
    RENT = "rent"
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    SUBSCRIPTION = "subscription"
    TAX = "tax"
    TRANSFER = "transfer"
    TRANSPORTATION = "transportation"
    TRAVEL = "travel"


class Institution(Base):
    """Financial institution model."""
    
    __tablename__ = "institutions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plaid_institution_id = Column(String(255), unique=True, nullable=True, index=True)
    yodlee_provider_id = Column(String(255), unique=True, nullable=True, index=True)
    
    name = Column(String(255), nullable=False, index=True)
    url = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    
    # Institution metadata
    country_codes = Column(JSON, nullable=True)  # List of supported countries
    products = Column(JSON, nullable=True)  # List of supported products
    routing_numbers = Column(JSON, nullable=True)  # List of routing numbers
    
    # Status
    is_active = Column(Boolean, default=True)
    health_status = Column(String(50), default="healthy")  # healthy, degraded, down
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = relationship("Item", back_populates="institution")
    
    __table_args__ = (
        Index('idx_institution_name', 'name'),
        Index('idx_institution_plaid_id', 'plaid_institution_id'),
    )


class Item(Base):
    """Banking connection item model."""
    
    __tablename__ = "items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    
    # Provider-specific IDs
    plaid_item_id = Column(String(255), unique=True, nullable=True, index=True)
    plaid_access_token = Column(String(255), nullable=True)  # Encrypted
    yodlee_item_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Connection metadata
    webhook_url = Column(String(500), nullable=True)
    connection_status = Column(String(50), default="connected")  # connected, error, requires_update
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Sync status
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    sync_in_progress = Column(Boolean, default=False)
    
    # Security
    consent_expiration_time = Column(DateTime, nullable=True)
    update_type = Column(String(50), nullable=True)  # background, user_present_required
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    institution = relationship("Institution", back_populates="items")
    accounts = relationship("Account", back_populates="item")
    
    def set_access_token(self, token: str) -> None:
        """Set encrypted access token."""
        self.plaid_access_token = fernet.encrypt(token.encode()).decode()
    
    def get_access_token(self) -> Optional[str]:
        """Get decrypted access token."""
        if self.plaid_access_token:
            return fernet.decrypt(self.plaid_access_token.encode()).decode()
        return None
    
    __table_args__ = (
        Index('idx_item_user_id', 'user_id'),
        Index('idx_item_institution', 'institution_id'),
        Index('idx_item_plaid_id', 'plaid_item_id'),
    )


class Account(Base):
    """Bank account model."""
    
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Provider-specific IDs
    plaid_account_id = Column(String(255), nullable=True, index=True)
    yodlee_account_id = Column(String(255), nullable=True, index=True)
    
    # Account information
    name = Column(String(255), nullable=False)
    official_name = Column(String(255), nullable=True)
    type = Column(ENUM(AccountType), nullable=False)
    subtype = Column(ENUM(AccountSubtype), nullable=True)
    
    # Account numbers (encrypted)
    account_number = Column(String(255), nullable=True)  # Encrypted
    routing_number = Column(String(255), nullable=True)  # Encrypted
    mask = Column(String(10), nullable=True)  # Last 4 digits
    
    # Balances
    current_balance = Column(Numeric(15, 2), nullable=True)
    available_balance = Column(Numeric(15, 2), nullable=True)
    credit_limit = Column(Numeric(15, 2), nullable=True)
    
    # Currency
    iso_currency_code = Column(String(3), nullable=True)
    unofficial_currency_code = Column(String(10), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)
    verification_status = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_balance_update = Column(DateTime, nullable=True)
    
    # Relationships
    item = relationship("Item", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    
    def set_account_number(self, number: str) -> None:
        """Set encrypted account number."""
        self.account_number = fernet.encrypt(number.encode()).decode()
    
    def get_account_number(self) -> Optional[str]:
        """Get decrypted account number."""
        if self.account_number:
            return fernet.decrypt(self.account_number.encode()).decode()
        return None
    
    def set_routing_number(self, number: str) -> None:
        """Set encrypted routing number."""
        self.routing_number = fernet.encrypt(number.encode()).decode()
    
    def get_routing_number(self) -> Optional[str]:
        """Get decrypted routing number."""
        if self.routing_number:
            return fernet.decrypt(self.routing_number.encode()).decode()
        return None
    
    __table_args__ = (
        Index('idx_account_user_id', 'user_id'),
        Index('idx_account_item_id', 'item_id'),
        Index('idx_account_type', 'type'),
        Index('idx_account_plaid_id', 'plaid_account_id'),
    )


class Transaction(Base):
    """Transaction model."""
    
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Provider-specific IDs
    plaid_transaction_id = Column(String(255), unique=True, nullable=True, index=True)
    yodlee_transaction_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Transaction details
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=False)
    merchant_name = Column(String(255), nullable=True)
    
    # Dates
    transaction_date = Column(Date, nullable=False)
    authorized_date = Column(Date, nullable=True)
    posted_date = Column(Date, nullable=True)
    
    # Categories
    category = Column(JSON, nullable=True)  # Array of category hierarchy
    category_id = Column(String(100), nullable=True)
    primary_category = Column(ENUM(TransactionCategory), nullable=True)
    
    # Currency
    iso_currency_code = Column(String(3), nullable=True)
    unofficial_currency_code = Column(String(10), nullable=True)
    
    # Transaction metadata
    transaction_type = Column(String(50), nullable=True)  # digital, place, special, unresolved
    pending = Column(Boolean, default=False)
    transaction_code = Column(String(50), nullable=True)
    
    # Location data
    location_data = Column(JSON, nullable=True)
    
    # Payment metadata
    payment_channel = Column(String(50), nullable=True)  # online, in_store, atm, other
    payment_meta = Column(JSON, nullable=True)
    
    # Personal finance data
    personal_finance_category = Column(JSON, nullable=True)
    
    # Custom fields
    user_category = Column(String(100), nullable=True)
    user_notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    
    __table_args__ = (
        Index('idx_transaction_user_id', 'user_id'),
        Index('idx_transaction_account_id', 'account_id'),
        Index('idx_transaction_date', 'transaction_date'),
        Index('idx_transaction_amount', 'amount'),
        Index('idx_transaction_category', 'primary_category'),
        Index('idx_transaction_pending', 'pending'),
        Index('idx_transaction_user_date', 'user_id', 'transaction_date'),
    )


class Balance(Base):
    """Account balance history model."""
    
    __tablename__ = "balances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Balance data
    current_balance = Column(Numeric(15, 2), nullable=True)
    available_balance = Column(Numeric(15, 2), nullable=True)
    credit_limit = Column(Numeric(15, 2), nullable=True)
    
    # Currency
    iso_currency_code = Column(String(3), nullable=True)
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_balance_account_time', 'account_id', 'recorded_at'),
        Index('idx_balance_user_time', 'user_id', 'recorded_at'),
    )


class SyncLog(Base):
    """Data synchronization log model."""
    
    __tablename__ = "sync_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Sync details
    sync_type = Column(String(50), nullable=False)  # transactions, accounts, balances
    status = Column(String(50), nullable=False)  # started, completed, failed
    
    # Counts
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Error information
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    __table_args__ = (
        Index('idx_sync_log_item_id', 'item_id'),
        Index('idx_sync_log_user_type', 'user_id', 'sync_type'),
        Index('idx_sync_log_status', 'status'),
        Index('idx_sync_log_started', 'started_at'),
    )


class WebhookEvent(Base):
    """Webhook event log model."""
    
    __tablename__ = "webhook_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Webhook details
    webhook_type = Column(String(100), nullable=False)  # TRANSACTIONS, ACCOUNTS, etc.
    webhook_code = Column(String(100), nullable=False)  # DEFAULT_UPDATE, etc.
    error_code = Column(String(100), nullable=True)
    
    # Payload
    payload = Column(JSON, nullable=False)
    
    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_webhook_type_code', 'webhook_type', 'webhook_code'),
        Index('idx_webhook_processed', 'processed'),
        Index('idx_webhook_received', 'received_at'),
    )