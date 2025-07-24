"""
MintFlow API Gateway
Central entry point for all API requests with routing, authentication, and rate limiting.
"""

import os
import time
import asyncio
from typing import Dict, Optional
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import httpx
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, generate_latest
import structlog
import jwt
from datetime import datetime, timedelta

# Configure structured logging
logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('gateway_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('gateway_request_duration_seconds', 'Request duration')

app = FastAPI(
    title="MintFlow API Gateway",
    description="Central API Gateway for MintFlow Personal Finance System",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENV") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENV") != "production" else None
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if os.getenv("ENV") == "development" else ["yourdomain.com", "*.yourdomain.com"]
)

# Service Configuration
SERVICES = {
    "auth": {"url": "http://auth-service:8000", "health": "/health"},
    "user": {"url": "http://user-service:8000", "health": "/health"},
    "transaction": {"url": "http://transaction-service:8000", "health": "/health"},
    "banking": {"url": "http://banking-service:8000", "health": "/health"},
    "ai": {"url": "http://ai-service:8000", "health": "/health"},
}

# Redis connection for rate limiting and caching
redis_client = None

async def get_redis():
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    return redis_client

class RateLimiter:
    """Rate limiting implementation using Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
        self.per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
        self.per_day = int(os.getenv("RATE_LIMIT_PER_DAY", "10000"))
    
    async def check_rate_limit(self, identifier: str) -> bool:
        """Check if request is within rate limits"""
        now = datetime.utcnow()
        
        # Check minute limit
        minute_key = f"rate_limit:{identifier}:minute:{now.strftime('%Y-%m-%d-%H-%M')}"
        minute_count = await self.redis.incr(minute_key)
        if minute_count == 1:
            await self.redis.expire(minute_key, 60)
        if minute_count > self.per_minute:
            return False
        
        # Check hour limit
        hour_key = f"rate_limit:{identifier}:hour:{now.strftime('%Y-%m-%d-%H')}"
        hour_count = await self.redis.incr(hour_key)
        if hour_count == 1:
            await self.redis.expire(hour_key, 3600)
        if hour_count > self.per_hour:
            return False
        
        # Check day limit
        day_key = f"rate_limit:{identifier}:day:{now.strftime('%Y-%m-%d')}"
        day_count = await self.redis.incr(day_key)
        if day_count == 1:
            await self.redis.expire(day_key, 86400)
        if day_count > self.per_day:
            return False
        
        return True

async def verify_jwt_token(request: Request) -> Optional[Dict]:
    """Verify JWT token and extract user information"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET"),
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")]
        )
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

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Middleware for logging, metrics, and rate limiting"""
    start_time = time.time()
    
    # Get client IP for rate limiting
    client_ip = request.client.host
    
    # Rate limiting
    redis_conn = await get_redis()
    rate_limiter = RateLimiter(redis_conn)
    
    if not await rate_limiter.check_rate_limit(client_ip):
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status="429"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Process request
    response = await call_next(request)
    
    # Record metrics
    process_time = time.time() - start_time
    REQUEST_DURATION.observe(process_time)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=str(response.status_code)
    ).inc()
    
    # Add headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "unknown")
    
    return response

async def proxy_request(service_name: str, path: str, request: Request):
    """Proxy request to appropriate microservice"""
    if service_name not in SERVICES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found"
        )
    
    service_url = SERVICES[service_name]["url"]
    target_url = f"{service_url}{path}"
    
    # Prepare headers
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove host header
    
    # Get request body
    body = await request.body()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        except httpx.RequestError as e:
            logger.error("Service request failed", service=service_name, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} unavailable"
            )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for the API Gateway"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

# Service health checks
@app.get("/health/services")
async def service_health_check():
    """Check health of all downstream services"""
    health_status = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, config in SERVICES.items():
            try:
                response = await client.get(f"{config['url']}{config['health']}")
                health_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                health_status[service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
    
    return health_status

# Authentication routes
@app.api_route("/api/v1/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def auth_proxy(path: str, request: Request):
    """Proxy requests to authentication service"""
    return await proxy_request("auth", f"/api/v1/auth/{path}", request)

# User management routes (require authentication)
@app.api_route("/api/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def user_proxy(path: str, request: Request, user: Dict = Depends(verify_jwt_token)):
    """Proxy requests to user service"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return await proxy_request("user", f"/api/v1/users/{path}", request)

# Transaction routes (require authentication)
@app.api_route("/api/v1/transactions/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def transaction_proxy(path: str, request: Request, user: Dict = Depends(verify_jwt_token)):
    """Proxy requests to transaction service"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return await proxy_request("transaction", f"/api/v1/transactions/{path}", request)

# Banking routes (require authentication)
@app.api_route("/api/v1/banking/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def banking_proxy(path: str, request: Request, user: Dict = Depends(verify_jwt_token)):
    """Proxy requests to banking service"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return await proxy_request("banking", f"/api/v1/banking/{path}", request)

# AI/ML routes (require authentication)
@app.api_route("/api/v1/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def ai_proxy(path: str, request: Request, user: Dict = Depends(verify_jwt_token)):
    """Proxy requests to AI service"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return await proxy_request("ai", f"/api/v1/ai/{path}", request)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "MintFlow API Gateway",
        "version": "1.0.0",
        "description": "Personal Finance Management API",
        "documentation": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV") == "development",
        log_level="info"
    )