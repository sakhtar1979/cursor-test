"""
Authentication Service Business Logic
Contains all business logic for authentication operations.
"""

import secrets
import smtplib
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import redis
import structlog

from .models import User, UserSession, EmailVerification, PasswordReset, SecurityEvent
from .schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from .security import (
    JWTManager, EncryptionManager, MFAManager, SecurityMonitor, 
    DeviceFingerprinting
)
from .config import settings

logger = structlog.get_logger()


class AuthService:
    """Core authentication service."""
    
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.security_monitor = SecurityMonitor(redis_client)
        self.jwt_manager = JWTManager()
        self.mfa_manager = MFAManager()
    
    async def register_user(
        self, 
        request: UserRegisterRequest,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """Register a new user."""
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == request.email).first()
        if existing_user:
            await self.security_monitor.log_security_event(
                event_type="registration_attempt_duplicate_email",
                description=f"Registration attempt with existing email: {request.email}",
                ip_address=ip_address,
                user_agent=user_agent,
                risk_level="medium"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Check username uniqueness if provided
        if request.username:
            existing_username = self.db.query(User).filter(User.username == request.username).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken"
                )
        
        # Create new user
        user = User(
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            phone_number=request.phone_number,
            consent_given=request.consent_given,
            privacy_policy_accepted=datetime.utcnow()
        )
        user.set_password(request.password)
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Send verification email
        verification_token = await self.create_email_verification(user.id, user.email)
        
        # Log security event
        await self.security_monitor.log_security_event(
            event_type="user_registered",
            description=f"User registered: {user.email}",
            user_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
            risk_level="low"
        )
        
        return {
            "user_id": str(user.id),
            "email": user.email,
            "verification_token": verification_token,
            "message": "User registered successfully. Please verify your email."
        }
    
    async def login_user(
        self,
        request: UserLoginRequest,
        ip_address: str,
        user_agent: str
    ) -> TokenResponse:
        """Authenticate user and return tokens."""
        
        # Check rate limiting
        if not await self.security_monitor.check_rate_limit(f"login:{ip_address}"):
            await self.security_monitor.log_security_event(
                event_type="rate_limit_exceeded",
                description=f"Login rate limit exceeded for IP: {ip_address}",
                ip_address=ip_address,
                user_agent=user_agent,
                risk_level="high"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later."
            )
        
        # Check if IP is blocked
        if await self.security_monitor.is_ip_blocked(ip_address):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Find user
        user = self.db.query(User).filter(User.email == request.email).first()
        if not user:
            await self.security_monitor.log_security_event(
                event_type="login_attempt_invalid_email",
                description=f"Login attempt with invalid email: {request.email}",
                ip_address=ip_address,
                user_agent=user_agent,
                risk_level="medium"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is locked
        if user.is_locked_out():
            await self.security_monitor.log_security_event(
                event_type="login_attempt_locked_user",
                description=f"Login attempt for locked user: {user.email}",
                user_id=str(user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                risk_level="high"
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked until {user.locked_until}"
            )
        
        # Verify password
        if not user.verify_password(request.password):
            user.increment_failed_login()
            self.db.commit()
            
            await self.security_monitor.log_security_event(
                event_type="login_attempt_invalid_password",
                description=f"Invalid password for user: {user.email}",
                user_id=str(user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                risk_level="medium"
            )
            
            if user.is_locked_out():
                await self.security_monitor.block_ip(ip_address, 3600)  # Block IP for 1 hour
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            await self.security_monitor.log_security_event(
                event_type="login_attempt_inactive_user",
                description=f"Login attempt for inactive user: {user.email}",
                user_id=str(user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                risk_level="medium"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Detect suspicious activity
        risk_assessment = await self.security_monitor.detect_suspicious_activity(
            str(user.id), ip_address, user_agent
        )
        
        # Handle MFA
        if user.mfa_enabled:
            if not request.totp_code:
                return TokenResponse(
                    access_token="",
                    refresh_token="",
                    token_type="bearer",
                    expires_in=0,
                    user_id=user.id,
                    requires_mfa=True
                )
            
            totp_secret = user.get_totp_secret()
            if not totp_secret or not self.mfa_manager.verify_totp(totp_secret, request.totp_code):
                await self.security_monitor.log_security_event(
                    event_type="mfa_verification_failed",
                    description=f"MFA verification failed for user: {user.email}",
                    user_id=str(user.id),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    risk_level="high"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code"
                )
        
        # Reset failed login attempts
        user.reset_failed_login()
        self.db.commit()
        
        # Create session
        device_fingerprint = DeviceFingerprinting.generate_fingerprint(request)
        session = await self.create_user_session(
            user.id, ip_address, user_agent, device_fingerprint, request.remember_me
        )
        
        # Generate tokens
        access_token = self.jwt_manager.create_access_token(
            str(user.id), 
            user.email,
            {"session_id": str(session.id)}
        )
        refresh_token = self.jwt_manager.create_refresh_token(str(user.id))
        
        # Log successful login
        await self.security_monitor.log_security_event(
            event_type="user_login_success",
            description=f"Successful login for user: {user.email}",
            user_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=str(session.id),
            risk_level=risk_assessment["risk_level"],
            metadata=risk_assessment
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user_id=user.id,
            requires_mfa=False
        )
    
    async def create_user_session(
        self,
        user_id: int,
        ip_address: str,
        user_agent: str,
        device_fingerprint: str,
        remember_me: bool = False
    ) -> UserSession:
        """Create a new user session."""
        
        # Determine session duration
        if remember_me:
            expires_at = datetime.utcnow() + timedelta(days=30)
        else:
            expires_at = datetime.utcnow() + timedelta(hours=24)
        
        session = UserSession(
            user_id=user_id,
            session_token=secrets.token_urlsafe(32),
            refresh_token=secrets.token_urlsafe(32),
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            expires_at=expires_at
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        # Clean up old sessions (keep last 5)
        old_sessions = self.db.query(UserSession)\
            .filter(UserSession.user_id == user_id)\
            .filter(UserSession.id != session.id)\
            .order_by(UserSession.created_at.desc())\
            .offset(5)\
            .all()
        
        for old_session in old_sessions:
            old_session.is_active = False
            old_session.revoked_at = datetime.utcnow()
            old_session.revoked_reason = "session_limit_exceeded"
        
        self.db.commit()
        
        return session
    
    async def create_email_verification(self, user_id: int, email: str) -> str:
        """Create email verification token."""
        token = secrets.token_urlsafe(32)
        
        verification = EmailVerification(
            user_id=user_id,
            email=email,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.db.add(verification)
        self.db.commit()
        
        # Send verification email (implement email service)
        await self._send_verification_email(email, token)
        
        return token
    
    async def verify_email(self, token: str) -> Dict[str, Any]:
        """Verify email address."""
        verification = self.db.query(EmailVerification)\
            .filter(EmailVerification.token == token)\
            .filter(EmailVerification.is_used == False)\
            .first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid verification token"
            )
        
        if verification.is_expired():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Verification token has expired"
            )
        
        # Update user verification status
        user = self.db.query(User).filter(User.id == verification.user_id).first()
        if user:
            user.is_verified = True
            verification.is_used = True
            verification.verified_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "message": "Email verified successfully",
                "user_id": str(user.id)
            }
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    async def setup_mfa(self, user_id: str, password: str) -> Dict[str, Any]:
        """Setup multi-factor authentication."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        # Generate TOTP secret
        secret = self.mfa_manager.generate_totp_secret()
        qr_code = self.mfa_manager.generate_qr_code(user.email, secret)
        backup_codes = self.mfa_manager.generate_backup_codes()
        
        # Encrypt and store
        user.set_totp_secret(secret)
        encrypted_backup_codes = [
            EncryptionManager.encrypt_data(code) for code in backup_codes
        ]
        user.backup_codes = encrypted_backup_codes
        
        self.db.commit()
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code}",
            "backup_codes": backup_codes
        }
    
    async def _send_verification_email(self, email: str, token: str):
        """Send email verification email."""
        # Implement email sending logic
        pass


class UserService:
    """User management service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            return UserResponse.from_orm(user)
        return None
    
    def update_user_profile(
        self, 
        user_id: str, 
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        username: Optional[str] = None
    ) -> UserResponse:
        """Update user profile."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if full_name is not None:
            user.full_name = full_name
        if phone_number is not None:
            user.phone_number = phone_number
        if username is not None:
            # Check if username is available
            existing = self.db.query(User)\
                .filter(User.username == username)\
                .filter(User.id != user_id)\
                .first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken"
                )
            user.username = username
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        return UserResponse.from_orm(user)
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's active sessions."""
        sessions = self.db.query(UserSession)\
            .filter(UserSession.user_id == user_id)\
            .filter(UserSession.is_active == True)\
            .order_by(UserSession.last_activity.desc())\
            .all()
        
        return [
            {
                "id": str(session.id),
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent
            }
            for session in sessions
        ]
    
    def revoke_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Revoke a user session."""
        session = self.db.query(UserSession)\
            .filter(UserSession.id == session_id)\
            .filter(UserSession.user_id == user_id)\
            .first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        session.revoked_reason = "user_revoked"
        
        self.db.commit()
        
        return {"message": "Session revoked successfully"}


class SecurityService:
    """Security and audit service."""
    
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.security_monitor = SecurityMonitor(redis_client)
    
    def get_security_events(
        self, 
        user_id: str, 
        limit: int = 50,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's security events."""
        query = self.db.query(SecurityEvent)\
            .filter(SecurityEvent.user_id == user_id)
        
        if event_type:
            query = query.filter(SecurityEvent.event_type == event_type)
        
        events = query.order_by(SecurityEvent.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "description": event.event_description,
                "ip_address": event.ip_address,
                "risk_level": event.risk_level,
                "created_at": event.created_at
            }
            for event in events
        ]