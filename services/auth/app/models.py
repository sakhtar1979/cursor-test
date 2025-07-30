"""
Authentication Service Database Models
Defines all database schemas with proper security and encryption.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from passlib.context import CryptContext
from .config import fernet, settings

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """User model with enhanced security features."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Security fields
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    locked_until = Column(DateTime, nullable=True)
    
    # Two-Factor Authentication
    totp_secret = Column(String(255), nullable=True)  # Encrypted
    backup_codes = Column(JSON, nullable=True)  # Encrypted
    mfa_enabled = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_password_change = Column(DateTime, default=datetime.utcnow)
    
    # Privacy and compliance
    data_retention_date = Column(DateTime, nullable=True)
    consent_given = Column(Boolean, default=False)
    privacy_policy_accepted = Column(DateTime, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_created_at', 'created_at'),
    )
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hashed password."""
        return pwd_context.verify(password, self.hashed_password)
    
    def set_password(self, password: str) -> None:
        """Set hashed password."""
        self.hashed_password = pwd_context.hash(password)
        self.last_password_change = datetime.utcnow()
    
    def is_locked_out(self) -> bool:
        """Check if user is currently locked out."""
        if not self.is_locked:
            return False
        if self.locked_until and datetime.utcnow() > self.locked_until:
            self.is_locked = False
            self.failed_login_attempts = 0
            self.locked_until = None
            return False
        return True
    
    def increment_failed_login(self) -> None:
        """Increment failed login attempts and lock if necessary."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= settings.max_login_attempts:
            self.is_locked = True
            self.locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_duration_minutes)
    
    def reset_failed_login(self) -> None:
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.is_locked = False
        self.locked_until = None
        self.last_login = datetime.utcnow()
    
    def set_totp_secret(self, secret: str) -> None:
        """Set encrypted TOTP secret."""
        self.totp_secret = fernet.encrypt(secret.encode()).decode()
    
    def get_totp_secret(self) -> Optional[str]:
        """Get decrypted TOTP secret."""
        if self.totp_secret:
            return fernet.decrypt(self.totp_secret.encode()).decode()
        return None


class UserSession(Base):
    """User session tracking for security."""
    
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    refresh_token = Column(String(255), unique=True, index=True, nullable=False)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    
    # Session lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Security flags
    is_suspicious = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )


class SecurityEvent(Base):
    """Security event logging for audit trails."""
    
    __tablename__ = "security_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_description = Column(Text, nullable=False)
    
    # Context information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_path = Column(String(500), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Risk assessment
    risk_level = Column(String(20), default='low')  # low, medium, high, critical
    is_suspicious = Column(Boolean, default=False)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_security_event_type_time', 'event_type', 'created_at'),
        Index('idx_security_user_time', 'user_id', 'created_at'),
    )


class EmailVerification(Base):
    """Email verification tokens."""
    
    __tablename__ = "email_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False)
    
    def is_expired(self) -> bool:
        """Check if verification token is expired."""
        return datetime.utcnow() > self.expires_at


class PasswordReset(Base):
    """Password reset tokens."""
    
    __tablename__ = "password_resets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False)
    
    # Security
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    def is_expired(self) -> bool:
        """Check if reset token is expired."""
        return datetime.utcnow() > self.expires_at