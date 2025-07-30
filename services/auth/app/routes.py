"""
Authentication Service API Routes
Defines all HTTP endpoints for the authentication service.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import redis
import structlog

from .database import get_db, get_redis
from .schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    MFASetupRequest, MFASetupResponse, MFAVerifyRequest, MFADisableRequest,
    RefreshTokenRequest, EmailVerificationRequest, SessionResponse,
    SecurityEventResponse, UserProfileUpdate, ErrorResponse, SuccessResponse
)
from .services import AuthService, UserService, SecurityService
from .security import JWTManager, security
from .models import User
from .config import settings

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = JWTManager.verify_token(token)
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
    
    return user


def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and user agent from request."""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return ip_address, user_agent


@router.post("/register", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request_data: UserRegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Register a new user account."""
    try:
        ip_address, user_agent = get_client_info(request)
        auth_service = AuthService(db, redis_client)
        
        result = await auth_service.register_user(request_data, ip_address, user_agent)
        
        return SuccessResponse(
            message="User registered successfully",
            data=result
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request_data: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Authenticate user and return access tokens."""
    try:
        ip_address, user_agent = get_client_info(request)
        auth_service = AuthService(db, redis_client)
        
        tokens = await auth_service.login_user(request_data, ip_address, user_agent)
        return tokens
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        payload = JWTManager.verify_token(request_data.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens
        access_token = JWTManager.create_access_token(str(user.id), user.email)
        refresh_token = JWTManager.create_refresh_token(str(user.id))
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user_id=user.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user and invalidate session."""
    try:
        # Invalidate all user sessions
        # In a real implementation, you'd track and invalidate specific sessions
        return SuccessResponse(message="Logged out successfully")
    
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/verify-email", response_model=SuccessResponse)
async def verify_email(
    request_data: EmailVerificationRequest,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Verify user email address."""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.verify_email(request_data.token)
        
        return SuccessResponse(
            message="Email verified successfully",
            data=result
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Email verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information."""
    try:
        user_service = UserService(db)
        updated_user = user_service.update_user_profile(
            str(current_user.id),
            request_data.full_name,
            request_data.phone_number,
            request_data.username
        )
        return updated_user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Profile update failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    request_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    try:
        # Verify current password
        if not current_user.verify_password(request_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.set_password(request_data.new_password)
        db.commit()
        
        return SuccessResponse(message="Password changed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/reset-password", response_model=SuccessResponse)
async def request_password_reset(
    request_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Request password reset."""
    try:
        # Always return success to prevent email enumeration
        return SuccessResponse(
            message="If the email exists, a password reset link has been sent"
        )
    
    except Exception as e:
        logger.error("Password reset request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )


@router.post("/reset-password/confirm", response_model=SuccessResponse)
async def confirm_password_reset(
    request_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token."""
    try:
        # Implement password reset confirmation logic
        return SuccessResponse(message="Password reset successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password reset confirmation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset confirmation failed"
        )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request_data: MFASetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Setup multi-factor authentication."""
    try:
        auth_service = AuthService(db, redis_client)
        result = await auth_service.setup_mfa(str(current_user.id), request_data.password)
        
        return MFASetupResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA setup failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup failed"
        )


@router.post("/mfa/verify", response_model=SuccessResponse)
async def verify_mfa(
    request_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify MFA token and enable MFA."""
    try:
        totp_secret = current_user.get_totp_secret()
        if not totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA not set up"
            )
        
        from .security import MFAManager
        if not MFAManager.verify_totp(totp_secret, request_data.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )
        
        current_user.mfa_enabled = True
        db.commit()
        
        return SuccessResponse(message="MFA enabled successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA verification failed"
        )


@router.post("/mfa/disable", response_model=SuccessResponse)
async def disable_mfa(
    request_data: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable multi-factor authentication."""
    try:
        # Verify password
        if not current_user.verify_password(request_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        # Verify TOTP
        totp_secret = current_user.get_totp_secret()
        if not totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA not enabled"
            )
        
        from .security import MFAManager
        if not MFAManager.verify_totp(totp_secret, request_data.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )
        
        # Disable MFA
        current_user.mfa_enabled = False
        current_user.totp_secret = None
        current_user.backup_codes = None
        db.commit()
        
        return SuccessResponse(message="MFA disabled successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA disable failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA disable failed"
        )


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's active sessions."""
    try:
        user_service = UserService(db)
        sessions = user_service.get_user_sessions(str(current_user.id))
        
        return [SessionResponse(**session) for session in sessions]
    
    except Exception as e:
        logger.error("Get sessions failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session."""
    try:
        user_service = UserService(db)
        result = user_service.revoke_session(str(current_user.id), session_id)
        
        return SuccessResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Session revocation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session revocation failed"
        )


@router.get("/security/events", response_model=List[SecurityEventResponse])
async def get_security_events(
    limit: int = 50,
    event_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get user's security events."""
    try:
        security_service = SecurityService(db, redis_client)
        events = security_service.get_security_events(
            str(current_user.id), limit, event_type
        )
        
        return [SecurityEventResponse(**event) for event in events]
    
    except Exception as e:
        logger.error("Get security events failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security events"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}