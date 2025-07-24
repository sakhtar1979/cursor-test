"""
MintFlow Authentication Service
Handles user authentication, registration, and security features.
"""

import os
import hashlib
import secrets
import pyotp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
import jwt
import redis
from passlib.context import CryptContext
import structlog
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="MintFlow Authentication Service",
    description="Authentication and security service for MintFlow",
    version="1.0.0"
)

# Security configuration
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mintflow:password@postgres:5432/mintflow")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/1"))

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
REFRESH_TOKEN_EXPIRATION_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRATION_DAYS", "30"))

# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_2fa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, index=True)
    ip_address = Column(String)
    user_agent = Column(String)
    success = Column(Boolean)
    attempted_at = Column(DateTime, default=datetime.utcnow)

class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class TwoFactorSetup(BaseModel):
    totp_code: str

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def generate_user_id() -> str:
    """Generate a unique user ID"""
    return f"user_{secrets.token_urlsafe(16)}"

def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    payload = verify_token(credentials.credentials)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    return user

def is_account_locked(user: User) -> bool:
    """Check if user account is locked due to failed login attempts"""
    if user.locked_until and user.locked_until > datetime.utcnow():
        return True
    return False

def lock_account(user: User, db: Session):
    """Lock user account for 30 minutes after 5 failed attempts"""
    user.failed_login_attempts += 1
    
    if user.failed_login_attempts >= 5:
        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        logger.warning("Account locked due to failed login attempts", user_id=user.id)
    
    db.commit()

def reset_failed_attempts(user: User, db: Session):
    """Reset failed login attempts counter"""
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

async def send_email(to_email: str, subject: str, body: str):
    """Send email using SMTP"""
    try:
        smtp_server = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("EMAIL_PORT", "587"))
        from_email = os.getenv("EMAIL_HOST_USER")
        password = os.getenv("EMAIL_HOST_PASSWORD")
        
        if not from_email or not password:
            logger.error("Email configuration missing")
            return
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        
        logger.info("Email sent successfully", to_email=to_email)
    except Exception as e:
        logger.error("Failed to send email", error=str(e))

# Routes
@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        id=generate_user_id(),
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send verification email
    verification_token = generate_token()
    redis_client.setex(f"verify:{verification_token}", 3600, user.id)  # 1 hour expiry
    
    verification_link = f"{os.getenv('FRONTEND_URL')}/verify-email?token={verification_token}"
    email_body = f"""
    <h2>Welcome to MintFlow!</h2>
    <p>Please verify your email address by clicking the link below:</p>
    <a href="{verification_link}">Verify Email</a>
    <p>This link will expire in 1 hour.</p>
    """
    
    background_tasks.add_task(
        send_email,
        user_data.email,
        "Verify Your MintFlow Account",
        email_body
    )
    
    logger.info("User registered successfully", user_id=user.id, email=user.email)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_2fa_enabled=user.is_2fa_enabled,
        created_at=user.created_at,
        last_login=user.last_login
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """User login with optional 2FA"""
    
    # Get user
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is locked
    if is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to failed login attempts"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        lock_account(user, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check 2FA if enabled
    if user.is_2fa_enabled:
        if not login_data.totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA code required"
            )
        
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(login_data.totp_code):
            lock_account(user, db)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
    
    # Successful login
    reset_failed_attempts(user, db)
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Store refresh token in Redis
    redis_client.setex(f"refresh:{user.id}", 30 * 24 * 3600, refresh_token)  # 30 days
    
    logger.info("User logged in successfully", user_id=user.id, email=user.email)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )

@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    
    payload = verify_token(credentials.credentials)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    stored_token = redis_client.get(f"refresh:{user_id}")
    
    if not stored_token or stored_token.decode() != credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    # Update refresh token in Redis
    redis_client.setex(f"refresh:{user.id}", 30 * 24 * 3600, new_refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )

@app.post("/api/v1/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user and invalidate refresh token"""
    
    # Remove refresh token from Redis
    redis_client.delete(f"refresh:{current_user.id}")
    
    logger.info("User logged out", user_id=current_user.id)
    
    return {"message": "Logged out successfully"}

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_2fa_enabled=current_user.is_2fa_enabled,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@app.get("/api/v1/auth/2fa/setup")
async def setup_2fa(current_user: User = Depends(get_current_user)):
    """Setup 2FA for user account"""
    
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )
    
    # Generate TOTP secret
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    
    # Generate QR code data
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="MintFlow"
    )
    
    # Store secret temporarily in Redis
    redis_client.setex(f"2fa_setup:{current_user.id}", 300, secret)  # 5 minutes
    
    return {
        "secret": secret,
        "qr_code_uri": provisioning_uri,
        "manual_entry_key": secret
    }

@app.post("/api/v1/auth/2fa/enable")
async def enable_2fa(setup_data: TwoFactorSetup, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Enable 2FA after verification"""
    
    # Get temporary secret from Redis
    secret = redis_client.get(f"2fa_setup:{current_user.id}")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup session expired"
        )
    
    # Verify TOTP code
    totp = pyotp.TOTP(secret.decode())
    if not totp.verify(setup_data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
    
    # Save secret and enable 2FA
    current_user.totp_secret = secret.decode()
    current_user.is_2fa_enabled = True
    db.commit()
    
    # Remove temporary secret
    redis_client.delete(f"2fa_setup:{current_user.id}")
    
    logger.info("2FA enabled for user", user_id=current_user.id)
    
    return {"message": "2FA enabled successfully"}

@app.delete("/api/v1/auth/2fa/disable")
async def disable_2fa(totp_data: TwoFactorSetup, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disable 2FA for user account"""
    
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    # Verify current TOTP code
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(totp_data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
    
    # Disable 2FA
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    db.commit()
    
    logger.info("2FA disabled for user", user_id=current_user.id)
    
    return {"message": "2FA disabled successfully"}

@app.post("/api/v1/auth/password-reset/request")
async def request_password_reset(reset_request: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Request password reset"""
    
    user = db.query(User).filter(User.email == reset_request.email).first()
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, you will receive a password reset link"}
    
    # Create password reset token
    reset_token = generate_token()
    
    password_reset = PasswordReset(
        id=generate_token(),
        user_id=user.id,
        token=reset_token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    
    db.add(password_reset)
    db.commit()
    
    # Send password reset email
    reset_link = f"{os.getenv('FRONTEND_URL')}/reset-password?token={reset_token}"
    email_body = f"""
    <h2>Password Reset Request</h2>
    <p>You requested a password reset for your MintFlow account.</p>
    <p>Click the link below to reset your password:</p>
    <a href="{reset_link}">Reset Password</a>
    <p>This link will expire in 1 hour.</p>
    <p>If you didn't request this, please ignore this email.</p>
    """
    
    background_tasks.add_task(
        send_email,
        user.email,
        "Reset Your MintFlow Password",
        email_body
    )
    
    logger.info("Password reset requested", user_id=user.id)
    
    return {"message": "If the email exists, you will receive a password reset link"}

@app.post("/api/v1/auth/password-reset/confirm")
async def confirm_password_reset(reset_data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Confirm password reset with token"""
    
    password_reset = db.query(PasswordReset).filter(
        PasswordReset.token == reset_data.token,
        PasswordReset.used == False,
        PasswordReset.expires_at > datetime.utcnow()
    ).first()
    
    if not password_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user = db.query(User).filter(User.id == password_reset.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Update password
    user.password_hash = hash_password(reset_data.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    
    # Mark reset token as used
    password_reset.used = True
    
    db.commit()
    
    # Invalidate all refresh tokens for this user
    redis_client.delete(f"refresh:{user.id}")
    
    logger.info("Password reset completed", user_id=user.id)
    
    return {"message": "Password reset successfully"}

@app.get("/api/v1/auth/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user email address"""
    
    user_id = redis_client.get(f"verify:{token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = db.query(User).filter(User.id == user_id.decode()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    user.is_verified = True
    db.commit()
    
    # Remove verification token
    redis_client.delete(f"verify:{token}")
    
    logger.info("Email verified", user_id=user.id)
    
    return {"message": "Email verified successfully"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "auth"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV") == "development"
    )