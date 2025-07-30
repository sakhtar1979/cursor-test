"""
Authentication Service Security Module
Handles JWT tokens, encryption, and security utilities.
"""

import secrets
import hashlib
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import structlog
from .config import settings, fernet
from .models import User, UserSession, SecurityEvent

logger = structlog.get_logger()
security = HTTPBearer()


class JWTManager:
    """JWT token management."""
    
    @staticmethod
    def create_access_token(user_id: str, email: str, additional_claims: Dict[str, Any] = None) -> str:
        """Create access token."""
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create refresh token."""
        to_encode = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days),
            "jti": secrets.token_urlsafe(32)  # JWT ID for token revocation
        }
        
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def extract_user_id(token: str) -> str:
        """Extract user ID from token."""
        payload = JWTManager.verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        return user_id


class EncryptionManager:
    """Data encryption and decryption utilities."""
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        """Encrypt sensitive data."""
        return fernet.encrypt(data.encode()).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return fernet.decrypt(encrypted_data.encode()).decode()
    
    @staticmethod
    def hash_data(data: str, salt: Optional[str] = None) -> str:
        """Hash data with optional salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex()
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)


class MFAManager:
    """Multi-Factor Authentication management."""
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate TOTP secret."""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(email: str, secret: str) -> str:
        """Generate QR code for TOTP setup."""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name="MintFlow"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return base64.b64encode(img_buffer.getvalue()).decode()
    
    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """Verify TOTP token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 30-second window
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate backup codes."""
        return [secrets.token_hex(4).upper() for _ in range(count)]


class SecurityMonitor:
    """Security monitoring and threat detection."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def log_security_event(
        self,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_path: Optional[str] = None,
        session_id: Optional[str] = None,
        risk_level: str = "low",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log security event for monitoring."""
        event_data = {
            "event_type": event_type,
            "description": description,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_path": request_path,
            "session_id": session_id,
            "risk_level": risk_level,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Security event logged", **event_data)
        
        # Store in Redis for real-time monitoring
        key = f"security_events:{datetime.utcnow().strftime('%Y%m%d')}"
        await self.redis.lpush(key, str(event_data))
        await self.redis.expire(key, 86400 * 7)  # Keep for 7 days
    
    async def check_rate_limit(self, identifier: str, limit: int = None, window: int = None) -> bool:
        """Check if request is within rate limits."""
        limit = limit or settings.rate_limit_requests
        window = window or settings.rate_limit_window_seconds
        
        key = f"rate_limit:{identifier}"
        current = await self.redis.get(key)
        
        if current is None:
            await self.redis.setex(key, window, 1)
            return True
        
        if int(current) >= limit:
            return False
        
        await self.redis.incr(key)
        return True
    
    async def detect_suspicious_activity(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """Detect suspicious login activity."""
        risk_score = 0
        flags = []
        
        # Check for multiple IPs
        ip_key = f"user_ips:{user_id}"
        recent_ips = await self.redis.smembers(ip_key)
        
        if ip_address.encode() not in recent_ips and len(recent_ips) > 0:
            risk_score += 30
            flags.append("new_ip_address")
        
        await self.redis.sadd(ip_key, ip_address)
        await self.redis.expire(ip_key, 86400 * 30)  # Keep for 30 days
        
        # Check for multiple user agents
        ua_key = f"user_agents:{user_id}"
        recent_uas = await self.redis.smembers(ua_key)
        
        if user_agent.encode() not in recent_uas and len(recent_uas) > 0:
            risk_score += 20
            flags.append("new_user_agent")
        
        await self.redis.sadd(ua_key, user_agent)
        await self.redis.expire(ua_key, 86400 * 30)
        
        # Check login frequency
        login_key = f"login_frequency:{user_id}"
        recent_logins = await self.redis.get(login_key)
        
        if recent_logins and int(recent_logins) > 5:
            risk_score += 40
            flags.append("high_login_frequency")
        
        await self.redis.incr(login_key)
        await self.redis.expire(login_key, 3600)  # 1 hour window
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "critical"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "flags": flags,
            "requires_additional_verification": risk_score >= 50
        }
    
    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked."""
        blocked = await self.redis.get(f"blocked_ip:{ip_address}")
        return blocked is not None
    
    async def block_ip(self, ip_address: str, duration: int = 3600):
        """Block IP address for specified duration."""
        await self.redis.setex(f"blocked_ip:{ip_address}", duration, "1")


class DeviceFingerprinting:
    """Device fingerprinting for enhanced security."""
    
    @staticmethod
    def generate_fingerprint(request: Request) -> str:
        """Generate device fingerprint from request."""
        components = [
            request.headers.get("user-agent", ""),
            request.headers.get("accept-language", ""),
            request.headers.get("accept-encoding", ""),
            request.headers.get("accept", ""),
            request.client.host if request.client else ""
        ]
        
        fingerprint_data = "|".join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    @staticmethod
    def is_known_device(user_id: str, fingerprint: str, redis_client: redis.Redis) -> bool:
        """Check if device fingerprint is known for user."""
        key = f"known_devices:{user_id}"
        return redis_client.sismember(key, fingerprint)
    
    @staticmethod
    def register_device(user_id: str, fingerprint: str, redis_client: redis.Redis):
        """Register device fingerprint for user."""
        key = f"known_devices:{user_id}"
        redis_client.sadd(key, fingerprint)
        redis_client.expire(key, 86400 * 90)  # Keep for 90 days