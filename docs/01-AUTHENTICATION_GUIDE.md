# Authentication & Authorization Guide

## Authentication System

### JWT-Based Token System

```
User Credentials → Verify → Argon2id Hash Check
        ↓
   JWT Token Generation
        ↓
┌──────────────────────────────────┐
│      Access Token (15 min)       │
├──────────────────────────────────┤
│ • sub: user_id                   │
│ • email: user@example.com        │
│ • org_id: organization_id        │
│ • role: admin|staff|limited      │
│ • permissions: [list]            │
│ • exp: 15 minutes                │
│ • iat: issued_at                 │
│ • jti: unique_id                 │
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│    Refresh Token (7 days)        │
├──────────────────────────────────┤
│ • sub: user_id                   │
│ • type: refresh                  │
│ • exp: 7 days                    │
│ • jti: unique_id                 │
│ • Stored in secure HttpOnly      │
│   cookie / local storage         │
└──────────────────────────────────┘
```

## Account Types & RBAC

### Account Type Hierarchy

```
┌─────────────────────────────────────────┐
│            Account Types                │
├─────────────────────────────────────────┤
│                                         │
│  1. Universities (Issuers)              │
│     ├── Admin - Full control            │
│     ├── Staff - Upload certificates     │
│     └── Limited - View only             │
│                                         │
│  2. Enterprises (Verifiers)             │
│     ├── Admin - Full control            │
│     ├── Officer - Verify certificates   │
│     └── Limited - View only             │
│                                         │
│  3. Public (No-login)                   │
│     └── Guest - Free basic verification │
│                                         │
│  4. Admins (System)                     │
│     ├── Super Admin - Everything        │
│     ├── Fraud Analyst - Fraud review    │
│     └── Support - User support          │
│                                         │
└─────────────────────────────────────────┘
```

### Permission Matrix

```
Resource                 | Univ Admin | Univ Staff | Enterprise | Public
─────────────────────────┼───────────┼───────────┼──────────┼────────
View own certs          | ✓         | ✓         | -        | -
Create certificates     | ✓         | ✓         | -        | -
Upload bulk certificates| ✓         | ✓         | -        | -
Verify any certificate  | -         | -         | ✓        | ✓ (5/day)
Access API keys         | ✓         | -         | ✓        | -
Access webhooks         | ✓         | -         | ✓        | -
View analytics          | ✓         | -         | ✓        | -
Admin panel             | -         | -         | -        | ✓ (Admin only)
```

## Implementation Example

### Login Endpoint (CORRECTED)

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.schemas.user import LoginRequest, TokenResponse
from app.core.security import verify_password, create_tokens
from app.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse, status_code=200)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user with email and password.

    Returns access token and refresh token.
    """
    # Find user by email
    user = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account disabled")

    # Generate tokens
    access_token, refresh_token = create_tokens(
        user_id=str(user.id),
        email=user.email,
        org_id=str(user.organization_id),
        role=user.role
    )

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=900  # 15 minutes
    )
```

### Protected Route Example

```python
from fastapi import Depends
from app.core.security import get_current_user

@router.get("/certificates")
async def list_certificates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List certificates for current user.
    Only sees certificates for their organization.
    """
    # Get organization
    org = await db.execute(
        select(Organization).where(
            Organization.id == current_user.organization_id
        )
    )
    org = org.scalar_one()

    # Get certificates based on organization
    certs = await db.execute(
        select(Certificate).where(
            Certificate.organization_id == org.id
        )
    )

    return certs.scalars().all()
```

## Password Security

### Requirements

```python
PASSWORD_REQUIREMENTS = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digits": True,
    "require_special": True
}

# Valid: "Secure@Pass123"
# Invalid: "Password"  (no special char, no digit)
```

### Hashing

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1
)

def hash_password(password: str) -> str:
    """Hash password with Argon2id."""
    return hasher.hash(password)

def verify_password(password: str, hash: str) -> bool:
    """Verify password against hash."""
    try:
        hasher.verify(hash, password)
        return True
    except VerifyMismatchError:
        return False
```

## Token Validation

### JWT Verification

```python
from jose import JWTError, jwt

def verify_token(token: str) -> dict:
    """Verify JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Token Blacklist

Revoked tokens stored in Redis:

```python
# When user logs out
await redis.setex(
    f"token_blacklist:{token_jti}",
    token_expiry_seconds,
    "revoked"
)

# When verifying token
blacklisted = await redis.exists(f"token_blacklist:{token_jti}")
if blacklisted:
    raise HTTPException(status_code=401, detail="Token revoked")
```

## Multi-Stakeholder Access Control

### Organization Isolation

```python
@router.get("/certificates")
async def get_certificates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    University can only see own certificates.
    Enterprise can only see verifications.
    """
    if current_user.account_type == "university":
        # Only show certificates issued by their org
        certs = await db.execute(
            select(Certificate).where(
                Certificate.issuer_organization_id == current_user.organization_id
            )
        )
    elif current_user.account_type == "enterprise":
        # Only show verifications they performed
        certs = await db.execute(
            select(Verification).where(
                Verification.verifier_organization_id == current_user.organization_id
            )
        )
    else:
        raise HTTPException(status_code=403, detail="Access denied")

    return certs.scalars().all()
```

## Security Best Practices

✅ **DO:**
- Always verify JWT signature
- Check token expiration
- Hash passwords with Argon2id
- Store refresh tokens in secure cookies
- Use HTTPS only
- Validate all inputs
- Log authentication events
- Check user is_active status

❌ **DON'T:**
- Store passwords in plain text
- Use weak JWT secrets
- Expose sensitive info in errors
- Allow token reuse
- Trust client-side validation
- Log sensitive data
- Skip permission checks

---

## Related Documentation

- [02-DATABASE_SCHEMA.md](02-DATABASE_SCHEMA.md) - Database models
- [03-API_DOCUMENTATION.md](03-API_DOCUMENTATION.md) - API endpoints

