"""
Authentication Service Pydantic Schemas
Defines request/response models with proper validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator, Field
from uuid import UUID
import re


class UserRegisterRequest(BaseModel):
    """User registration request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, regex=r'^\+?1?\d{9,15}$')
    consent_given: bool = True
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('consent_given')
    def validate_consent(cls, v):
        if not v:
            raise ValueError('Consent must be given to register')
        return v


class UserLoginRequest(BaseModel):
    """User login request schema."""
    email: EmailStr
    password: str
    remember_me: bool = False
    totp_code: Optional[str] = Field(None, regex=r'^\d{6}$')
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!",
                "remember_me": False,
                "totp_code": "123456"
            }
        }


class TokenResponse(BaseModel):
    """JWT token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    requires_mfa: bool = False


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    email: str
    username: Optional[str]
    full_name: Optional[str]
    phone_number: Optional[str]
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class MFASetupRequest(BaseModel):
    """MFA setup request schema."""
    password: str


class MFASetupResponse(BaseModel):
    """MFA setup response schema."""
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    """MFA verification request schema."""
    totp_code: str = Field(..., regex=r'^\d{6}$')


class MFADisableRequest(BaseModel):
    """MFA disable request schema."""
    password: str
    totp_code: str = Field(..., regex=r'^\d{6}$')


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""
    token: str


class SessionResponse(BaseModel):
    """User session response schema."""
    id: UUID
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_current: bool = False
    
    class Config:
        from_attributes = True


class SecurityEventResponse(BaseModel):
    """Security event response schema."""
    id: UUID
    event_type: str
    event_description: str
    ip_address: Optional[str]
    risk_level: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update schema."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, regex=r'^\+?1?\d{9,15}$')
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    
    @validator('username')
    def validate_username(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str
    message: str
    details: Optional[dict] = None


class SuccessResponse(BaseModel):
    """Standard success response schema."""
    success: bool = True
    message: str
    data: Optional[dict] = None