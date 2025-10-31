# Backend Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HTTP Requests                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         FastAPI Application (Port 8000)             │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │    Middleware Layer                           │ │   │
│  │  ├─────────────────────────────────────────────┤ │   │
│  │  │ • CORS & Security Headers                   │ │   │
│  │  │ • Authentication (JWT)                      │ │   │
│  │  │ • Rate Limiting (Redis)                     │ │   │
│  │  │ • Request/Response Logging                  │ │   │
│  │  │ • Error Handling                            │ │   │
│  │  └────────────────────────────────────────────┘ │   │
│  │          ↓                                        │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │    Router Layer (API Endpoints)              │ │   │
│  │  ├─────────────────────────────────────────────┤ │   │
│  │  │ • /api/v1/auth/       (Authentication)     │ │   │
│  │  │ • /api/v1/certificates/ (Certificate CRUD) │ │   │
│  │  │ • /api/v1/verification/ (Verify)           │ │   │
│  │  │ • /api/v1/admin/       (Admin)             │ │   │
│  │  │ • /health              (Health Checks)     │ │   │
│  │  └────────────────────────────────────────────┘ │   │
│  │          ↓                                        │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │    Service Layer (Business Logic)            │ │   │
│  │  ├─────────────────────────────────────────────┤ │   │
│  │  │ • AuthService                              │ │   │
│  │  │ • CertificateService                       │ │   │
│  │  │ • VerificationService                      │ │   │
│  │  │ • WebhookService                           │ │   │
│  │  └────────────────────────────────────────────┘ │   │
│  │          ↓                                        │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │    Fraud Detection Pipeline                   │ │   │
│  │  ├─────────────────────────────────────────────┤ │   │
│  │  │ Layer 1: EXIF Analysis (20 pts)            │ │   │
│  │  │ Layer 2: ELA (20 pts)                      │ │   │
│  │  │ Layer 3: Gemini Vision (20 pts)            │ │   │
│  │  │ Layer 4: Database Verification (20 pts)    │ │   │
│  │  │ Layer 5: Blockchain (10 pts)               │ │   │
│  │  │ Layer 6: Geo-Fraud (10 pts)                │ │   │
│  │  │ Total: 0-100 score                         │ │   │
│  │  └────────────────────────────────────────────┘ │   │
│  │                  ↓                               │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │    Data Access Layer (DAL)                    │ │   │
│  │  ├─────────────────────────────────────────────┤ │   │
│  │  │ • PostgreSQL Connection Pool               │ │   │
│  │  │ • Redis Cache                              │ │   │
│  │  │ • SQLAlchemy ORM                           │ │   │
│  │  └────────────────────────────────────────────┘ │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                       ↓                                  │
├─────────────────────────────────────────────────────────────┤
│                   External Services                        │
├─────────────────────────────────────────────────────────────┤
│  • PostgreSQL Database (Primary)                          │
│  • Redis Cache (Session/Rate-Limit)                       │
│  • Google Gemini Vision API                               │
│  • Polygon Mumbai Blockchain                              │
│  • AWS S3 (Certificate Images)                            │
│  • SMTP (Email Service)                                   │
│  • Razorpay (Payments)                                    │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI 0.109+ | High-performance async Python web framework |
| **Database** | PostgreSQL 15+ | Relational database with RBAC |
| **ORM** | SQLAlchemy Async | Async ORM for database operations |
| **Cache** | Redis 7.0+ | Session storage, rate limiting, caching |
| **Connection Pool** | PgBouncer | PostgreSQL connection pooling |
| **Language** | Python 3.10+ | Modern Python with type hints |
| **Async** | AsyncIO | Fully asynchronous operations |
| **Validation** | Pydantic v2 | Request/response validation |
| **Auth** | JWT + Argon2id | Token-based auth + password hashing |
| **Deployment** | Docker | Containerized deployment |
| **Hosting** | Railway.app | Cloud platform (India-optimized) |

## Project Structure

```
app/
├── __init__.py
├── main.py                              # FastAPI app initialization
│
├── core/
│   ├── __init__.py
│   ├── config.py                        # Environment configuration
│   ├── security.py                      # JWT, password hashing
│   ├── constants.py                     # Application constants
│   └── exceptions.py                    # Custom exceptions
│
├── models/
│   ├── __init__.py
│   ├── user.py                          # User SQLAlchemy model
│   ├── organization.py                  # Organization model
│   ├── certificate.py                   # Certificate model
│   ├── verification.py                  # Verification result model
│   ├── audit_log.py                     # Audit logging model
│   └── webhook.py                       # Webhook model
│
├── schemas/
│   ├── __init__.py
│   ├── user.py                          # User Pydantic schemas
│   ├── certificate.py                   # Certificate schemas
│   ├── verification.py                  # Verification schemas
│   ├── response.py                      # Standard response envelopes
│   └── error.py                         # Error schemas
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                          # /api/v1/auth endpoints
│   ├── certificates.py                  # /api/v1/certificates endpoints
│   ├── verification.py                  # /api/v1/verification endpoints
│   ├── webhooks.py                      # /api/v1/webhooks endpoints
│   ├── admin.py                         # /api/v1/admin endpoints
│   └── health.py                        # /health endpoints
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py                  # Authentication logic
│   ├── certificate_service.py           # Certificate management
│   ├── verification_service.py          # Verification orchestration
│   ├── webhook_service.py               # Webhook delivery & retry
│   ├── cache_service.py                 # Redis caching
│   └── email_service.py                 # Email sending
│
├── fraud_detection/
│   ├── __init__.py
│   ├── base.py                          # Base fraud detector class
│   ├── pipeline.py                      # Main fraud detection pipeline
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── layer_1_exif.py              # EXIF analysis (20 pts)
│   │   ├── layer_2_ela.py               # Error Level Analysis (20 pts)
│   │   ├── layer_3_gemini.py            # Gemini Vision (20 pts)
│   │   ├── layer_4_database.py          # Database verification (20 pts)
│   │   ├── layer_5_blockchain.py        # Blockchain verification (10 pts)
│   │   └── layer_6_geo_fraud.py         # Geo-fraud detection (10 pts)
│   └── utils/
│       ├── __init__.py
│       ├── image_processor.py           # Image processing utilities
│       ├── hashing.py                   # Hash computations
│       └── fuzzy_matcher.py             # Fuzzy string matching
│
├── middleware/
│   ├── __init__.py
│   ├── cors.py                          # CORS middleware
│   ├── auth.py                          # JWT authentication
│   ├── rate_limit.py                    # Rate limiting
│   ├── logging.py                       # Structured logging
│   └── error_handler.py                 # Error handling
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py                       # General utilities
│   ├── validators.py                    # Input validation
│   ├── decorators.py                    # Custom decorators
│   └── constants.py                     # Constants
│
└── external_apis/
    ├── __init__.py
    ├── gemini_client.py                 # Google Gemini integration
    ├── blockchain_client.py             # Blockchain integration
    └── s3_client.py                     # AWS S3 integration

migrations/
├── alembic.ini                          # Alembic configuration
├── env.py                               # Migration environment
└── versions/
    ├── 001_initial_schema.py            # Initial database setup
    ├── 002_add_rbac.py                  # RBAC implementation
    └── ...                              # Future migrations

tests/
├── __init__.py
├── conftest.py                          # pytest fixtures
├── unit/
│   ├── test_auth_service.py
│   ├── test_fraud_detection.py
│   └── ...
├── integration/
│   ├── test_certificate_flow.py
│   └── ...
└── fraud/
    └── test_fraud_accuracy.py

scripts/
├── seed_demo_data.py                    # Demo data seeding
├── backup_database.py                   # Backup automation
└── health_check.py                      # Health status check

docs/                                    # 30+ documentation files
├── 01-AUTHENTICATION.md
├── 02-DATABASE_SCHEMA.md
├── 03-API_DOCUMENTATION.md
└── ...
```

## Request Flow

```
HTTP Request
    ↓
CORS Middleware (validate origin)
    ↓
Rate Limit Middleware (check Redis)
    ↓
Authentication Middleware (validate JWT)
    ↓
Request Validation (Pydantic schemas)
    ↓
Route Handler (main logic)
    ↓
Service Layer (business logic)
    ↓
Data Access Layer (database/cache)
    ↓
External APIs (if needed)
    ↓
Response Generation
    ↓
Error Handler (if exception)
    ↓
Response Headers (rate limit, cache)
    ↓
HTTP Response
```

## Database Architecture

- **PostgreSQL 15+** - Primary relational database
- **Connection Pooling** - PgBouncer for efficient connections
- **RBAC Built-in** - organization_id, role-based access
- **Sharding-Ready** - shard_key column in critical tables
- **Full-Text Search** - PostgreSQL FTS for certificate search
- **JSON Support** - Metadata stored in JSON columns
- **Indexes** - Strategic indexes for performance
- **Migrations** - Alembic for version control

## Caching Strategy

```
Cache Layer (Redis)
├── User Sessions (TTL: 7 days)
├── JWT Blacklist (TTL: token expiry)
├── Certificate Metadata (TTL: 1 day)
├── Verification Results (TTL: 30 days)
├── Rate Limit Counters (TTL: 1 hour)
└── Webhook Retry Queue (TTL: 7 days)
```

## Security Layers

1. **Network Security** - HTTPS, CORS, security headers
2. **Authentication** - JWT tokens, Argon2id hashing
3. **Authorization** - RBAC with permission checks
4. **Input Validation** - Pydantic schemas, SQL injection prevention
5. **Rate Limiting** - Redis-based distributed rate limiting
6. **Error Handling** - No sensitive info in error messages
7. **Logging** - Structured logging without sensitive data
8. **Secrets** - Environment variables, never committed

## Performance Targets

- API Response Time: < 200ms (excluding fraud detection)
- Fraud Detection: < 5 seconds (parallel execution)
- Database Query: < 100ms
- Cache Hit Rate: > 80%
- Memory Usage: < 500MB
- CPU Usage: < 30% under normal load

## Related Documentation

- [01-AUTHENTICATION.md](01-AUTHENTICATION.md) - Auth system details
- [02-DATABASE_SCHEMA.md](02-DATABASE_SCHEMA.md) - Database design
- [03-API_DOCUMENTATION.md](03-API_DOCUMENTATION.md) - API endpoints
- [04-FRAUD_DETECTION_GUIDE.md](04-FRAUD_DETECTION_GUIDE.md) - Fraud pipeline
- [05-DEPLOYMENT.md](05-DEPLOYMENT.md) - Deployment procedures

---

**Next:** See [01-AUTHENTICATION.md](01-AUTHENTICATION.md) for authentication system details.
