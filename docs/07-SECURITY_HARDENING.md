# Security Hardening - Production-Ready Implementation

## Complete Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: Network Security                                  │
│  ├─ HTTPS/TLS 1.3+                                         │
│  ├─ CORS Policy                                            │
│  ├─ Security Headers                                       │
│  └─ Rate Limiting                                          │
│                                                              │
│  Layer 2: Authentication                                    │
│  ├─ JWT with HS256/RS256                                   │
│  ├─ Argon2id Password Hashing                              │
│  ├─ Token Blacklist (Redis)                                │
│  └─ 2FA/MFA Support                                        │
│                                                              │
│  Layer 3: Authorization                                     │
│  ├─ Role-Based Access Control (RBAC)                       │
│  ├─ Resource-Level Permissions                             │
│  ├─ Organization Isolation                                 │
│  └─ Audit Logging                                          │
│                                                              │
│  Layer 4: Data Protection                                   │
│  ├─ Input Validation (Pydantic)                            │
│  ├─ SQL Injection Prevention                               │
│  ├─ XSS Protection                                         │
│  ├─ CSRF Tokens                                            │
│  └─ Encryption at Rest (optional)                          │
│                                                              │
│  Layer 5: Output Security                                   │
│  ├─ Error Message Sanitization                             │
│  ├─ No Sensitive Data in Logs                              │
│  ├─ Response Validation                                    │
│  └─ API Rate Limiting                                      │
│                                                              │
│  Layer 6: Infrastructure Security                           │
│  ├─ Database Credentials Rotation                          │
│  ├─ API Key Management                                     │
│  ├─ Network Segmentation                                   │
│  └─ Secrets Management (.env)                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. HTTPS & TLS Configuration

### FastAPI HTTPS Setup

**Location:** `app/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings with security configuration."""

    # HTTPS
    HTTPS_ONLY: bool = True
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    SSL_PROTOCOLS: list = ["TLSv1.2", "TLSv1.3"]
    SSL_CIPHERS: str = "HIGH:!aNULL:!MD5"

    # Security Headers
    CORS_ORIGINS: list = ["https://credify.app", "https://www.credify.app"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    CORS_ALLOW_HEADERS: list = ["*"]
    CORS_MAX_AGE: int = 3600

    # CSP Headers
    CONTENT_SECURITY_POLICY: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### ASGI Server Configuration

**Location:** `Dockerfile` (uvicorn launch)

```bash
# Use with SSL certificates
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--ssl-keyfile=/etc/ssl/private/key.pem", \
     "--ssl-certfile=/etc/ssl/certs/cert.pem", \
     "--ssl-keyfile-password-provider", "env:SSL_PASSWORD"]
```

---

## 2. Authentication Security

### Password Hashing with Argon2id

**Location:** `app/core/security.py`

```python
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from typing import Optional

# Argon2id password hashing (best for password storage)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=2,          # t_cost
    argon2__memory_cost=65536,    # m_cost (64MB)
    argon2__parallelism=4,        # p_cost
    argon2__hash_len=32,
    argon2__salt_len=16,
)

def hash_password(password: str) -> str:
    """Hash password with Argon2id."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def validate_password(password: str) -> None:
    """Validate password strength."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain uppercase letter")

    if not any(c.islower() for c in password):
        raise ValueError("Password must contain lowercase letter")

    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain digit")

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        raise ValueError("Password must contain special character")

# JWT Token Management
SECRET_KEY = "your-secret-key-min-32-chars-long-and-random"
ALGORITHM = "HS256"

def create_tokens(user_data: dict) -> dict:
    """Create access and refresh tokens."""
    # Access token (15 minutes)
    access_payload = {
        **user_data,
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iat": datetime.utcnow(),
        "type": "access"
    }

    # Refresh token (7 days)
    refresh_payload = {
        **user_data,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900  # 15 minutes in seconds
    }

def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
```

---

## 3. Authorization & RBAC

### Role-Based Access Control

**Location:** `app/middleware/auth.py`

```python
from fastapi import HTTPException, Depends, status
from functools import wraps
from app.core.security import decode_token

async def get_current_user(authorization: str = None) -> dict:
    """Extract and validate current user from JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )

    token = authorization.split(" ")[1]

    try:
        payload = decode_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

def require_role(*allowed_roles):
    """Check user has required role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: dict = Depends(get_current_user), **kwargs):
            user_role = current_user.get("role")

            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of roles: {allowed_roles}"
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def require_permission(permission: str):
    """Check user has specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: dict = Depends(get_current_user), **kwargs):
            user_permissions = current_user.get("permissions", [])

            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permission: {permission}"
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def organization_isolation(func):
    """Ensure users can only access their organization's data."""
    @wraps(func)
    async def wrapper(
        *args,
        organization_id: str,
        current_user: dict = Depends(get_current_user),
        **kwargs
    ):
        user_org_id = current_user.get("org_id")

        if user_org_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other organizations' data"
            )

        return await func(*args, organization_id=organization_id, current_user=current_user, **kwargs)
    return wrapper
```

---

## 4. Input Validation & SQL Injection Prevention

### Pydantic Input Schemas

**Location:** `app/schemas/user.py`

```python
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional

class LoginRequest(BaseModel):
    """Validated login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=255)

    @validator("email")
    def email_must_be_lowercase(cls, v):
        """Normalize email to lowercase."""
        return v.lower()

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserRegisterRequest(BaseModel):
    """Validated user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=255)
    organization_id: str = Field(..., pattern="^[a-f0-9-]{36}$")  # UUID format
    account_type: str = Field(..., regex="^(university|enterprise)$")

    class Config:
        """Pydantic config."""
        # Prevent extra fields
        extra = "forbid"
        # Use enum for account_type
        use_enum_values = True
```

### Parameterized Queries with SQLAlchemy

```python
# ✅ CORRECT - Parameterized query
from sqlalchemy import select

stmt = select(User).where(User.email == user_email)
result = await db.execute(stmt)
user = result.scalar_one_or_none()

# ❌ WRONG - String concatenation (VULNERABLE!)
# stmt = select(User).where(f"email = '{user_email}'")
```

---

## 5. Error Handling & Information Disclosure

### Secure Error Messages

**Location:** `app/middleware/error_handler.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
import logging

logger = logging.getLogger(__name__)

async def exception_handler(request: Request, exc: Exception):
    """Handle exceptions securely."""

    # Log full error internally (with all details)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Return generic error to client (no implementation details)
    if isinstance(exc, ValueError):
        # For known exceptions, return appropriate status
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "Invalid input provided"
                # Don't include: actual validation error details
            }
        )

    # For unknown exceptions, never expose details
    if isinstance(exc, Exception):
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": "An error occurred processing your request"
                # Don't include: stack trace, file names, line numbers, etc.
            }
        )
```

### Structured Logging Without Sensitive Data

**Location:** `app/middleware/logging.py`

```python
import json
import logging
from datetime import datetime

class SanitizedFormatter(logging.Formatter):
    """Log formatter that removes sensitive data."""

    SENSITIVE_KEYS = {
        "password", "token", "secret", "api_key", "private_key",
        "credit_card", "ssn", "email", "phone"
    }

    def format(self, record):
        """Format log record without sensitive data."""
        if hasattr(record, 'msg') and isinstance(record.msg, dict):
            record.msg = self._sanitize_dict(record.msg)

        # Also sanitize args if present
        if record.args and isinstance(record.args, dict):
            record.args = self._sanitize_dict(record.args)

        return super().format(record)

    def _sanitize_dict(self, data: dict) -> dict:
        """Remove sensitive fields from dictionary."""
        sanitized = {}

        for key, value in data.items():
            if key.lower() in self.SENSITIVE_KEYS:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            else:
                sanitized[key] = value

        return sanitized

# Setup logger with sanitized formatter
logger = logging.getLogger("credify")
handler = logging.StreamHandler()
formatter = SanitizedFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
```

---

## 6. API Security Best Practices

### CORS & Security Headers Middleware

**Location:** `app/middleware/security.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

def add_security_headers(app: FastAPI):
    """Add security headers to all responses."""

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response: Response = await call_next(request)

            # Prevent clickjacking
            response.headers["X-Frame-Options"] = "DENY"

            # Prevent MIME type sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"

            # Enable XSS protection
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Content Security Policy
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

            # Referrer Policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Permissions Policy
            response.headers["Permissions-Policy"] = (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )

            # HSTS (HTTP Strict Transport Security)
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            return response

    app.add_middleware(SecurityHeadersMiddleware)

def add_cors(app: FastAPI, origins: list):
    """Configure CORS with security."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        max_age=3600,
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"]
    )
```

---

## 7. Secrets Management

### Environment Variables Best Practices

**Location:** `.env.example`

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname
POSTGRES_PASSWORD=secure_random_password_min_32_chars

# Secrets (Never commit actual values!)
JWT_SECRET=your-super-secret-key-min-32-chars-random
API_SECRET_KEY=another-secret-min-32-chars

# API Keys
GEMINI_API_KEY=your-gemini-key-here
POLYGON_RPC_URL=https://rpc-mumbai.maticvigil.com
WEB3_PRIVATE_KEY=0x... (DO NOT COMMIT)

# Email
SMTP_PASSWORD=your-app-specific-password (NOT main password)

# Security
CORS_ORIGINS=https://credify.app,https://www.credify.app
ENVIRONMENT=production
```

### Secure Secrets Rotation

**Location:** `scripts/rotate_secrets.py`

```python
import os
import sys
from cryptography.fernet import Fernet
from datetime import datetime

def rotate_jwt_secret():
    """Rotate JWT secret securely."""
    old_secret = os.getenv("JWT_SECRET")
    new_secret = Fernet.generate_key().decode()

    # Store new secret
    with open(".env", "a") as f:
        f.write(f"\n# Rotated at {datetime.utcnow()}\n")
        f.write(f"JWT_SECRET={new_secret}\n")

    print("✓ JWT secret rotated")
    print("⚠️  Update all running instances to use new secret")

def rotate_db_password():
    """Rotate database password."""
    print("⚠️  Manual step required:")
    print("1. Change PostgreSQL user password")
    print("2. Update DATABASE_URL in .env")
    print("3. Restart all services")

if __name__ == "__main__":
    rotate_jwt_secret()
```

---

## 8. Audit Logging

### Comprehensive Audit Trail

**Location:** `app/services/audit_service.py`

```python
from app.models.audit_log import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json

class AuditService:
    """Manage audit logging for compliance."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        user_id: str,
        organization_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        old_values: dict = None,
        new_values: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success"
    ):
        """Log user action for audit trail."""

        audit_log = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values or {},
            new_values=new_values or {},
            changes=self._calculate_changes(old_values, new_values),
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            created_at=datetime.utcnow()
        )

        self.db.add(audit_log)
        await self.db.commit()

    def _calculate_changes(self, old: dict, new: dict) -> dict:
        """Calculate what changed between old and new values."""
        if not old or not new:
            return {}

        changes = {}
        for key in set(list(old.keys()) + list(new.keys())):
            if old.get(key) != new.get(key):
                changes[key] = {
                    "old": old.get(key),
                    "new": new.get(key)
                }

        return changes
```

---

## 9. Security Checklist

### Pre-Production Security Checklist

```
✓ HTTPS/TLS Configuration
  [ ] SSL certificates installed and valid
  [ ] TLS 1.2+ enforced
  [ ] HSTS headers configured
  [ ] Certificate auto-renewal configured

✓ Authentication
  [ ] JWT secrets strong (min 32 chars, random)
  [ ] Password hashing with Argon2id
  [ ] Token expiry configured (15min access, 7day refresh)
  [ ] Logout invalidates tokens

✓ Authorization
  [ ] RBAC implemented and tested
  [ ] Organization isolation enforced
  [ ] API endpoints protected
  [ ] Admin endpoints require authentication

✓ Input Validation
  [ ] All endpoints use Pydantic schemas
  [ ] Parameterized SQL queries used
  [ ] File uploads validated (type, size)
  [ ] No user input in SQL queries

✓ Error Handling
  [ ] No stack traces in responses
  [ ] No sensitive data in error messages
  [ ] Structured logging without PII
  [ ] 500 errors return generic message

✓ API Security
  [ ] CORS configured correctly
  [ ] Security headers added
  [ ] Rate limiting active
  [ ] CSRF protection for state-changing requests

✓ Data Protection
  [ ] Sensitive data not logged
  [ ] Database credentials not in code
  [ ] API keys in environment variables
  [ ] Secrets rotation configured

✓ Infrastructure
  [ ] Database user has minimal permissions
  [ ] Connections use SSL
  [ ] Backups encrypted and tested
  [ ] Monitoring and alerting configured

✓ Compliance
  [ ] Data retention policies documented
  [ ] GDPR right-to-delete implemented
  [ ] Audit logging for all sensitive actions
  [ ] Data classification completed
```

---

## Related Documentation

- [06-TESTING_STRATEGY.md](06-TESTING_STRATEGY.md) - Security testing
- [05-DEPLOYMENT.md](05-DEPLOYMENT.md) - Deployment security

---

**Last Updated:** 2024-10-31
**Version:** 1.0
**Status:** Production Ready
