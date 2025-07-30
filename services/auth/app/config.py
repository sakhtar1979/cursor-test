"""
Authentication Service Configuration
Handles all configuration settings with proper environment variable management.
"""

import os
from typing import Optional
from pydantic import BaseSettings, validator
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    """Application settings with validation and encryption."""
    
    # Database settings
    database_url: str = "postgresql://mintflow:password@postgres:5432/mintflow"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis settings
    redis_url: str = "redis://redis:6379/1"
    redis_pool_size: int = 10
    
    # JWT settings
    jwt_secret_key: str = "your-super-secret-jwt-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # Encryption settings
    encryption_key: Optional[str] = None
    
    # Email settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    
    # Security settings
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    # AWS settings
    aws_region: str = "us-east-1"
    aws_kms_key_id: Optional[str] = None
    aws_secrets_manager_enabled: bool = False
    
    # Application settings
    debug: bool = False
    service_name: str = "auth-service"
    service_version: str = "1.0.0"
    port: int = 8001
    
    @validator('encryption_key', pre=True, always=True)
    def generate_encryption_key(cls, v):
        if v is None:
            return Fernet.generate_key().decode()
        return v
    
    @validator('jwt_secret_key', pre=True, always=True)
    def validate_jwt_secret(cls, v):
        if v == "your-super-secret-jwt-key":
            raise ValueError("JWT secret key must be changed from default")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Create Fernet instance for encryption
fernet = Fernet(settings.encryption_key.encode())