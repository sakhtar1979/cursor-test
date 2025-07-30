"""
Banking Service Configuration
Handles all configuration settings for banking integrations and financial data processing.
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, validator
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    """Banking service settings with validation and encryption."""
    
    # Database settings
    database_url: str = "postgresql://mintflow:password@postgres:5432/mintflow"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis settings
    redis_url: str = "redis://redis:6379/2"  # Different DB from auth
    redis_pool_size: int = 10
    
    # Encryption settings
    encryption_key: Optional[str] = None
    
    # Plaid configuration
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_environment: str = "sandbox"  # sandbox, development, production
    plaid_products: List[str] = ["transactions", "accounts", "identity"]
    plaid_country_codes: List[str] = ["US"]
    
    # Yodlee configuration
    yodlee_client_id: str = ""
    yodlee_secret: str = ""
    yodlee_environment: str = "sandbox"
    
    # Finicity configuration
    finicity_partner_id: str = ""
    finicity_app_key: str = ""
    finicity_secret: str = ""
    finicity_environment: str = "sandbox"
    
    # Banking data processing
    transaction_sync_interval_minutes: int = 30
    account_sync_interval_minutes: int = 60
    balance_sync_interval_minutes: int = 15
    
    # Data retention
    transaction_retention_days: int = 2555  # 7 years
    account_data_retention_days: int = 2555
    
    # Rate limiting
    plaid_rate_limit_requests: int = 100
    plaid_rate_limit_window_seconds: int = 60
    
    # AWS settings
    aws_region: str = "us-east-1"
    aws_kms_key_id: Optional[str] = None
    aws_secrets_manager_enabled: bool = False
    
    # Message queue settings
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_transactions: str = "transactions"
    kafka_topic_accounts: str = "accounts"
    kafka_topic_balances: str = "balances"
    
    # Application settings
    debug: bool = False
    service_name: str = "banking-service"
    service_version: str = "1.0.0"
    port: int = 8002
    
    # Security settings
    max_connection_attempts: int = 3
    connection_timeout_minutes: int = 10
    
    @validator('encryption_key', pre=True, always=True)
    def generate_encryption_key(cls, v):
        if v is None:
            return Fernet.generate_key().decode()
        return v
    
    @validator('plaid_environment')
    def validate_plaid_environment(cls, v):
        valid_envs = ["sandbox", "development", "production"]
        if v not in valid_envs:
            raise ValueError(f"Plaid environment must be one of {valid_envs}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Create Fernet instance for encryption
fernet = Fernet(settings.encryption_key.encode())