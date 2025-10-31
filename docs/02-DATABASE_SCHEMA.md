# PostgreSQL Database Schema

## Database Diagram

```
┌─────────────────────┐
│      users          │
├─────────────────────┤
│ id (UUID) [PK]      │
│ email (VARCHAR)     │
│ password_hash       │
│ phone (VARCHAR)     │
│ name (VARCHAR)      │
│ account_type        │
│ organization_id [FK]│
│ role (VARCHAR)      │
│ is_active           │
│ created_at          │
│ updated_at          │
└─────────────────────┘
        │
        ├──────────────┬──────────────┐
        │              │              │
        ↓              ↓              ↓
┌──────────────────┐┌─────────────────┐┌─────────────────┐
│  organizations   ││  certificates   ││  verifications  │
├──────────────────┤├─────────────────┤├─────────────────┤
│ id (UUID) [PK]   ││ id (UUID) [PK]  ││ id (UUID) [PK]  │
│ name             ││ issuer_id [FK]  ││ cert_id [FK]    │
│ type             ││ holder_email    ││ verifier_id [FK]│
│ email            ││ title           ││ fraud_score     │
│ phone            ││ issue_date      ││ verdict         │
│ is_verified      ││ image_url       ││ created_at      │
│ metadata (JSON)  ││ blockchain_hash ││ breakdown (JSON)│
│ created_at       ││ created_at      ││ details (JSON)  │
│ updated_at       ││ updated_at      ││                 │
└──────────────────┘└─────────────────┘└─────────────────┘
```

## Core Tables

### users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,

    -- Account & Organization
    account_type VARCHAR(50) NOT NULL, -- 'university', 'enterprise', 'public', 'admin'
    organization_id UUID NOT NULL REFERENCES organizations(id),
    role VARCHAR(50) NOT NULL,         -- 'admin', 'staff', 'officer', 'limited'

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,

    -- Sharding
    shard_key BIGINT DEFAULT 0,

    -- Indexes
    CONSTRAINT email_unique UNIQUE (email),
    CONSTRAINT phone_unique UNIQUE (phone)
) WITH (FILLFACTOR=90);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_org_id ON users(organization_id);
CREATE INDEX idx_users_shard_key ON users(shard_key);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### organizations Table

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('university', 'enterprise')),

    -- Contact
    email VARCHAR(255),
    phone VARCHAR(15),
    website VARCHAR(255),

    -- Address
    country VARCHAR(50) DEFAULT 'IN',
    state VARCHAR(50),
    city VARCHAR(100),
    address TEXT,

    -- Metadata
    logo_url TEXT,
    metadata JSONB DEFAULT '{}',

    -- Verification
    is_verified BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    verification_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'

    -- University-specific
    ugc_affiliation_number VARCHAR(100),
    aicte_code VARCHAR(100),

    -- Enterprise-specific
    gst_number VARCHAR(15),
    pan_number VARCHAR(10),
    cin_number VARCHAR(21),

    -- Settings
    subscription_tier VARCHAR(50) DEFAULT 'free', -- 'free', 'pro', 'enterprise'
    api_rate_limit INTEGER DEFAULT 100,
    bulk_upload_limit INTEGER DEFAULT 100,

    -- Status
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'suspended', 'inactive'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) WITH (FILLFACTOR=90);

CREATE INDEX idx_org_name ON organizations(name);
CREATE INDEX idx_org_type ON organizations(type);
CREATE INDEX idx_org_created_at ON organizations(created_at);
```

### certificates Table

```sql
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_id VARCHAR(255) UNIQUE NOT NULL, -- External ID

    -- Relationships
    issuer_organization_id UUID NOT NULL REFERENCES organizations(id),
    holder_email VARCHAR(255),
    holder_name VARCHAR(255),

    -- Certificate Details
    title VARCHAR(255) NOT NULL,
    certificate_type VARCHAR(50), -- 'bachelor', 'master', 'diploma', etc.
    issue_date DATE NOT NULL,
    expiry_date DATE,

    -- Files
    image_url VARCHAR(255),
    image_hash VARCHAR(255), -- SHA-256 for integrity
    document_hash VARCHAR(255),

    -- Blockchain
    blockchain_hash VARCHAR(255),
    blockchain_tx VARCHAR(255),

    -- Status
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'revoked', 'expired'
    is_revoked BOOLEAN DEFAULT false,
    revocation_reason VARCHAR(255),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Tracking
    verification_count INTEGER DEFAULT 0,
    last_verified_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Sharding
    shard_key BIGINT DEFAULT 0
) WITH (FILLFACTOR=90);

CREATE INDEX idx_cert_issuer_id ON certificates(issuer_organization_id);
CREATE INDEX idx_cert_holder_email ON certificates(holder_email);
CREATE INDEX idx_cert_shard_key ON certificates(shard_key);
CREATE INDEX idx_cert_created_at ON certificates(created_at);
CREATE INDEX idx_cert_status ON certificates(status);
```

### verifications Table

```sql
CREATE TABLE verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_id VARCHAR(255) UNIQUE NOT NULL,

    -- Relationships
    certificate_id UUID NOT NULL REFERENCES certificates(id),
    verifier_organization_id UUID REFERENCES organizations(id),
    verifier_user_id UUID REFERENCES users(id),

    -- Results
    fraud_score INTEGER CHECK (fraud_score >= 0 AND fraud_score <= 100),
    status VARCHAR(50), -- 'authentic', 'forged', 'suspicious'
    confidence DECIMAL(5, 2) CHECK (confidence >= 0 AND confidence <= 100),
    verdict VARCHAR(50),

    -- Details
    breakdown JSONB, -- Layer scores
    layer_details JSONB,
    model_version VARCHAR(20),

    -- Metadata
    ip_address INET,
    user_agent VARCHAR(255),

    -- Timestamps
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) WITH (FILLFACTOR=90);

CREATE INDEX idx_verif_cert_id ON verifications(certificate_id);
CREATE INDEX idx_verif_verifier_id ON verifications(verifier_organization_id);
CREATE INDEX idx_verif_created_at ON verifications(created_at);
CREATE INDEX idx_verif_status ON verifications(status);
```

### audit_logs Table

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Actor
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Action
    action VARCHAR(255), -- 'certificate_created', 'verification_completed', etc.
    resource_type VARCHAR(100), -- 'certificate', 'verification', 'user'
    resource_id UUID,

    -- Changes
    old_values JSONB,
    new_values JSONB,
    changes JSONB,

    -- Context
    ip_address INET,
    user_agent VARCHAR(255),

    -- GDPR
    gdpr_deletion_requested BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) WITH (FILLFACTOR=90);

CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_org_id ON audit_logs(organization_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_action ON audit_logs(action);
```

### webhooks Table

```sql
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Organization
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Webhook Configuration
    url VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL, -- 'verification.completed', 'certificate.created', etc.
    secret VARCHAR(255) NOT NULL, -- For HMAC-SHA256 signing

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Settings
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    retry_delay_seconds INTEGER DEFAULT 300,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP
) WITH (FILLFACTOR=90);

CREATE INDEX idx_webhook_org_id ON webhooks(organization_id);
CREATE INDEX idx_webhook_event ON webhooks(event_type);
CREATE INDEX idx_webhook_active ON webhooks(is_active);
CREATE INDEX idx_webhook_created_at ON webhooks(created_at);
```

### webhook_events Table

```sql
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Webhook Reference
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,

    -- Event Details
    event_type VARCHAR(100) NOT NULL,
    resource_id UUID NOT NULL,
    resource_type VARCHAR(100) NOT NULL, -- 'certificate', 'verification'

    -- Payload
    payload JSONB NOT NULL,

    -- Delivery Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'abandoned'
    response_status_code INTEGER,
    response_body TEXT,

    -- Retry Info
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    next_retry_at TIMESTAMP,

    -- Error Tracking
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) WITH (FILLFACTOR=90);

CREATE INDEX idx_webhook_event_webhook_id ON webhook_events(webhook_id);
CREATE INDEX idx_webhook_event_status ON webhook_events(status);
CREATE INDEX idx_webhook_event_created_at ON webhook_events(created_at);
CREATE INDEX idx_webhook_event_resource ON webhook_events(resource_type, resource_id);
```

### fraud_incidents Table

```sql
CREATE TABLE fraud_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    verification_id UUID NOT NULL REFERENCES verifications(id),
    certificate_id UUID NOT NULL REFERENCES certificates(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Fraud Classification
    fraud_type VARCHAR(100) NOT NULL, -- 'forged', 'template_match', 'metadata_mismatch', 'ai_detected'
    confidence_score DECIMAL(5, 2) CHECK (confidence_score >= 0 AND confidence_score <= 100),
    severity VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'

    -- Detection Details
    detection_layer VARCHAR(50), -- Which fraud layer detected it
    detection_reason TEXT,

    -- Geographic & Network
    ip_address INET,
    geolocation JSONB, -- {country, state, city, latitude, longitude}
    user_agent VARCHAR(255),

    -- Status
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'investigating', 'confirmed', 'dismissed'
    investigated_by UUID REFERENCES users(id),
    investigated_at TIMESTAMP,
    investigation_notes TEXT,

    -- Action Taken
    action_taken VARCHAR(100), -- 'none', 'certificate_revoked', 'user_suspended', 'reported'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) WITH (FILLFACTOR=90);

CREATE INDEX idx_fraud_verification_id ON fraud_incidents(verification_id);
CREATE INDEX idx_fraud_cert_id ON fraud_incidents(certificate_id);
CREATE INDEX idx_fraud_org_id ON fraud_incidents(organization_id);
CREATE INDEX idx_fraud_created_at ON fraud_incidents(created_at);
CREATE INDEX idx_fraud_status ON fraud_incidents(status);
CREATE INDEX idx_fraud_severity ON fraud_incidents(severity);
```

### rate_limit_keys Table (for distributed rate limiting)

```sql
CREATE TABLE rate_limit_keys (
    id BIGSERIAL PRIMARY KEY,

    -- Key identification
    key_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash of actual key
    key_type VARCHAR(50) NOT NULL, -- 'ip', 'user_id', 'api_key'
    identifier VARCHAR(255) NOT NULL,

    -- Rate limit config
    limit_per_hour INTEGER DEFAULT 100,
    limit_per_day INTEGER DEFAULT 1000,

    -- Current counts
    count_hour INTEGER DEFAULT 0,
    count_day INTEGER DEFAULT 0,

    -- Windows
    hour_window_start TIMESTAMP,
    day_window_start TIMESTAMP,

    -- Status
    is_blocked BOOLEAN DEFAULT false,
    block_reason VARCHAR(255),
    block_until TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) WITH (FILLFACTOR=90);

CREATE INDEX idx_rate_limit_key_hash ON rate_limit_keys(key_hash);
CREATE INDEX idx_rate_limit_blocked ON rate_limit_keys(is_blocked);
CREATE INDEX idx_rate_limit_type ON rate_limit_keys(key_type);
```

## Connection Pooling Configuration

```python
# PgBouncer configuration for Railway.app
DATABASE_URL = "postgresql://user:pass@pgbouncer:6432/credify"

# SQLAlchemy with connection pooling
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # Use PgBouncer for pooling
    connect_args={
        "timeout": 10,
        "command_timeout": 10,
    }
)

# Session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

## Migrations

Use Alembic for version control:

```bash
# Generate migration
alembic revision --autogenerate -m "Add organizations table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM certificates
WHERE issuer_organization_id = 'uuid'
AND created_at > NOW() - INTERVAL '7 days';

-- Vacuum for maintenance
VACUUM ANALYZE certificates;

-- Check index usage
SELECT * FROM pg_stat_user_indexes
WHERE idx_blks_read > 0;
```

## Data Retention Policies

```sql
-- Archive old verifications (> 2 years)
DELETE FROM verifications
WHERE created_at < NOW() - INTERVAL '2 years';

-- Archive old audit logs (> 1 year)
DELETE FROM audit_logs
WHERE created_at < NOW() - INTERVAL '1 year';
```

## Sharding Strategy (Future)

Sharding-ready columns already in place:

```python
def calculate_shard_key(user_id: str) -> int:
    """Calculate which shard this user belongs to."""
    # For MVP: always returns 0 (single shard)
    # For Phase 2: returns hash(user_id) % num_shards
    return 0

# Usage
shard_key = calculate_shard_key(user_id)
# Route to correct shard database
db = shards[shard_key]
```

---

## Related Documentation

- [01-AUTHENTICATION_GUIDE.md](01-AUTHENTICATION_GUIDE.md) - Auth system
- [03-API_DOCUMENTATION.md](03-API_DOCUMENTATION.md) - API endpoints

