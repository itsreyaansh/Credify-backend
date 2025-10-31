# Deployment Guide - Railway.app & Docker

## Complete Deployment & DevOps Manual

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Docker Setup](#docker-setup)
4. [Railway.app Configuration](#railwayapp-configuration)
5. [Environment Variables](#environment-variables)
6. [Database Migrations](#database-migrations)
7. [Deployment Procedure](#deployment-procedure)
8. [Post-Deployment Verification](#post-deployment-verification)
9. [Monitoring & Logs](#monitoring--logs)
10. [Rollback Procedures](#rollback-procedures)
11. [Scaling & Performance](#scaling--performance)

---

## Overview

**Credify** is deployed on Railway.app using Docker containers for both backend and frontend. The system is designed for:

- **Single server MVP** (~500 concurrent users)
- **Auto-scaling ready** (horizontal scaling via sharding)
- **PostgreSQL** database with PgBouncer connection pooling
- **Redis** for caching and session management
- **CI/CD via GitHub Actions** for automated deployments

### Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│         Railway.app (Single Server)                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐        ┌──────────────┐          │
│  │   Backend    │        │   Frontend   │          │
│  │ (FastAPI)    │────────│   (React)    │          │
│  │ :8000        │        │   :3000      │          │
│  └──────────────┘        └──────────────┘          │
│        ↓                       ↓                     │
│  ┌──────────────────────────────────────┐          │
│  │  PgBouncer (Connection Pooling)      │          │
│  └──────────────────────────────────────┘          │
│        ↓                                            │
│  ┌──────────────────────────────────────┐          │
│  │  PostgreSQL 15 (Database)            │          │
│  │  - users                             │          │
│  │  - organizations                     │          │
│  │  - certificates                      │          │
│  │  - verifications                     │          │
│  │  - audit_logs                        │          │
│  └──────────────────────────────────────┘          │
│                                                      │
│  ┌──────────────────────────────────────┐          │
│  │  Redis (Cache & Sessions)            │          │
│  │  - Rate limiting                     │          │
│  │  - JWT blacklist                     │          │
│  │  - Geo clustering                    │          │
│  └──────────────────────────────────────┘          │
│                                                      │
│  External Integrations:                            │
│  - Google Gemini API                               │
│  - Polygon Mumbai (Blockchain)                     │
│  - SMTP (Email)                                    │
│  - S3 (File Storage - Optional)                    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

- **Docker:** 20.10+
- **Docker Compose:** 1.29+
- **Git:** 2.30+
- **Node.js:** 18+ (for frontend)
- **Python:** 3.10+ (for local development)
- **PostgreSQL CLI:** 13+ (for local testing)

### Railway.app Account

1. Create account at https://railway.app
2. Connect GitHub repository
3. Get Railway.app API token from settings
4. Set up project

### External Services

1. **Google Gemini API:** API key required
2. **Polygon Mumbai:** Wallet with test MATIC tokens
3. **SMTP:** Gmail, SendGrid, or similar
4. **S3/Cloud Storage:** AWS S3 or similar (optional)

---

## Docker Setup

### Backend Dockerfile

**Location:** `Credify-backend/Dockerfile`

```dockerfile
# Multi-stage build for FastAPI backend

# Stage 1: Builder
FROM python:3.10-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache /wheels/*

# Copy application code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY alembic.ini .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile

**Location:** `Credify-frontend/Dockerfile`

```dockerfile
# Multi-stage build for React frontend

# Stage 1: Build
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build


# Stage 2: Runtime (Nginx)
FROM nginx:alpine

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built app
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

**Location:** `Credify-frontend/nginx.conf`

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    server {
        listen 80;
        server_name _;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # SPA routing
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            expires 1h;
        }

        # Static assets
        location /static/ {
            alias /usr/share/nginx/html/static/;
            expires 365d;
        }

        # API proxy (if needed)
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

### Rate Limiting Configuration

**Location:** `app/middleware/rate_limit.py`

```python
from redis import Redis
from datetime import datetime, timedelta
import hashlib

class RateLimitMiddleware:
    """Distributed rate limiting middleware using Redis."""

    def __init__(self, redis_client: Redis, default_limit: int = 100):
        self.redis = redis_client
        self.default_limit = default_limit

    async def __call__(self, scope, receive, send):
        """Rate limit incoming requests."""
        if scope["type"] != "http":
            await send({"type": "http.response.start", "status": 200})
            return

        # Get client identifier
        client_ip = self._get_client_ip(scope)
        path = scope["path"]
        method = scope["method"]

        # Check rate limits
        key = f"rate_limit:{client_ip}:{path}"
        current_count = self.redis.incr(key)

        if current_count == 1:
            # First request in this window, set expiry to 1 hour
            self.redis.expire(key, 3600)

        # Get limit for this endpoint
        limit = self._get_limit(path, method)

        # Check if limit exceeded
        if current_count > limit:
            # Return 429 Too Many Requests
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [[b"retry-after", b"3600"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error":"rate_limit_exceeded","message":"Too many requests"}',
            })
            return

        # Add rate limit headers
        scope["rate_limit"] = {
            "limit": limit,
            "remaining": limit - current_count,
            "reset": self.redis.ttl(key)
        }

        await send(scope)

    def _get_client_ip(self, scope):
        """Extract client IP from request scope."""
        client_host, _ = scope["client"]
        x_forwarded_for = None

        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == b"x-forwarded-for":
                x_forwarded_for = header_value.decode().split(",")[0].strip()
                break

        return x_forwarded_for or client_host

    def _get_limit(self, path: str, method: str) -> int:
        """Get rate limit for endpoint."""
        limits = {
            ("/api/v1/auth/login", "POST"): 5,  # 5 per hour
            ("/api/v1/auth/signup", "POST"): 10,  # 10 per hour
            ("/api/v1/verification/verify", "POST"): 10,  # 10 per hour
            ("/api/v1/certificates/upload", "POST"): 20,  # 20 per hour
            ("/api/v1/certificates/bulk-upload", "POST"): 5,  # 5 per hour
            ("/health", "GET"): 1000,  # Unlimited
        }

        return limits.get((path, method), self.default_limit)
```

### WebSocket Connection Management

**Location:** `app/routes/websocket.py`

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manage WebSocket connections with reconnection support."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # verification_id -> set of client_ids

    async def connect(self, websocket: WebSocket, client_id: str):
        """Establish WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        """Handle WebSocket disconnection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        logger.info(f"WebSocket disconnected: {client_id}")

    async def subscribe(self, client_id: str, verification_id: str):
        """Subscribe client to verification updates."""
        if verification_id not in self.subscriptions:
            self.subscriptions[verification_id] = set()
        self.subscriptions[verification_id].add(client_id)
        logger.info(f"Client {client_id} subscribed to {verification_id}")

    async def unsubscribe(self, client_id: str, verification_id: str):
        """Unsubscribe client from verification updates."""
        if verification_id in self.subscriptions:
            self.subscriptions[verification_id].discard(client_id)

    async def broadcast(self, verification_id: str, message: dict):
        """Broadcast message to all subscribed clients."""
        if verification_id not in self.subscriptions:
            return

        dead_connections = []

        for client_id in self.subscriptions[verification_id]:
            if client_id not in self.active_connections:
                dead_connections.append(client_id)
                continue

            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {str(e)}")
                dead_connections.append(client_id)

        # Clean up dead connections
        for client_id in dead_connections:
            self.disconnect(client_id)
            await self.unsubscribe(client_id, verification_id)

    async def send_personal(self, client_id: str, message: dict):
        """Send message to specific client."""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {str(e)}")
                self.disconnect(client_id)

# WebSocket Router
ws_manager = WebSocketManager()

@router.websocket("/verification/stream")
async def verification_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time verification updates."""
    client_id = f"client_{uuid4()}"

    try:
        await ws_manager.connect(websocket, client_id)

        # Heartbeat to detect dead connections
        import asyncio
        async def heartbeat():
            while client_id in ws_manager.active_connections:
                try:
                    await websocket.send_json({"event": "ping"})
                    await asyncio.sleep(30)  # Every 30 seconds
                except:
                    break

        heartbeat_task = asyncio.create_task(heartbeat())

        while True:
            # Receive subscription messages
            data = await websocket.receive_json()

            if data.get("action") == "subscribe":
                verification_id = data.get("verification_id")
                if verification_id:
                    await ws_manager.subscribe(client_id, verification_id)

            elif data.get("action") == "unsubscribe":
                verification_id = data.get("verification_id")
                if verification_id:
                    await ws_manager.unsubscribe(client_id, verification_id)

            elif data.get("action") == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
        ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        ws_manager.disconnect(client_id)
```

**Client-side WebSocket Connection with Reconnection:**

```javascript
// frontend/src/services/websocket.ts

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000; // 3 seconds
  private messageHandlers: Map<string, Function> = new Map();
  private isManualClose = false;

  constructor(url: string) {
    this.url = url;
    this.clientId = `client_${Date.now()}_${Math.random()}`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log("WebSocket connected");
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          const data = JSON.parse(event.data);

          // Handle heartbeat
          if (data.event === "ping") {
            this.send({ event: "pong" });
            return;
          }

          // Dispatch to handlers
          if (data.event && this.messageHandlers.has(data.event)) {
            const handler = this.messageHandlers.get(data.event);
            handler?.(data);
          }
        };

        this.ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log("WebSocket closed");
          if (!this.isManualClose) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`Attempting to reconnect in ${delay}ms...`);

      setTimeout(() => {
        this.connect().catch((error) => {
          console.error("Reconnection failed:", error);
        });
      }, delay);
    }
  }

  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  subscribe(verificationId: string): void {
    this.send({
      action: "subscribe",
      verification_id: verificationId,
    });
  }

  on(event: string, handler: Function): void {
    this.messageHandlers.set(event, handler);
  }

  close(): void {
    this.isManualClose = true;
    if (this.ws) {
      this.ws.close();
    }
  }
}
```

### Docker Compose

**Location:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  # Backend - FastAPI
  backend:
    build:
      context: ./Credify-backend
      dockerfile: Dockerfile
    container_name: credify-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET=${JWT_SECRET}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - POLYGON_RPC_URL=${POLYGON_RPC_URL}
      - CONTRACT_ADDRESS=${CONTRACT_ADDRESS}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - ENVIRONMENT=${ENVIRONMENT:-development}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./Credify-backend/app:/app/app
    networks:
      - credify-network
    restart: unless-stopped

  # Frontend - React/Nginx
  frontend:
    build:
      context: ./Credify-frontend
      dockerfile: Dockerfile
    container_name: credify-frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=${VITE_API_URL:-http://backend:8000}
      - VITE_WS_URL=${VITE_WS_URL:-ws://backend:8000}
    depends_on:
      - backend
    networks:
      - credify-network
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: credify-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-credify}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB:-credify}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - credify-network
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: credify-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - credify-network
    restart: unless-stopped

  # PgBouncer - Connection Pooling
  pgbouncer:
    image: pgbouncer:latest
    container_name: credify-pgbouncer
    ports:
      - "6432:6432"
    environment:
      - DATABASES_HOST=postgres
      - DATABASES_PORT=5432
      - DATABASES_USER=${POSTGRES_USER:-credify}
      - DATABASES_PASSWORD=${POSTGRES_PASSWORD}
      - DATABASES_DBNAME=${POSTGRES_DB:-credify}
    volumes:
      - ./pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini
    depends_on:
      - postgres
    networks:
      - credify-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  credify-network:
    driver: bridge
```

### PgBouncer Configuration

**Location:** `pgbouncer.ini`

```ini
[databases]
credify = host=postgres port=5432 user=credify password=PASSWORD dbname=credify

[pgbouncer]
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = plain
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 10
reserve_pool_size = 5
reserve_pool_timeout = 3
```

---

## Railway.app Configuration

### 1. Create Project on Railway.app

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Create new project
railway init

# Choose Python backend
```

### 2. Configure Services in Railway.app

**Backend Service:**
```yaml
# railway.toml
[build]
builder = "dockerfile"
dockerfile = "./Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 100
```

**Frontend Service:**
```yaml
[build]
builder = "dockerfile"
dockerfile = "./Dockerfile"

[deploy]
healthcheckPath = "/"
```

**PostgreSQL Service:**
- Railway provides managed PostgreSQL
- Configuration via Railway dashboard
- Automatic backups included

**Redis Service:**
- Railway provides managed Redis
- Configuration via Railway dashboard

### 3. Environment Variables

Set in Railway dashboard for each service:

**Backend:**
```
DATABASE_URL=postgresql://user:pass@postgres:5432/credify
REDIS_URL=redis://redis:6379
JWT_SECRET=your-secret-min-32-chars
JWT_ALGORITHM=HS256
GEMINI_API_KEY=your-gemini-api-key
POLYGON_RPC_URL=https://rpc-mumbai.maticvigil.com
CONTRACT_ADDRESS=0x...
WEB3_PRIVATE_KEY=your-private-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
CORS_ORIGINS=https://credify.app,https://www.credify.app
ENVIRONMENT=production
```

---

## Environment Variables

### Complete .env.example

```bash
# Database
DATABASE_URL=postgresql://credify:password@localhost:5432/credify
POSTGRES_USER=credify
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=credify

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-secret-key-min-32-characters-long
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# External APIs
GEMINI_API_KEY=your-google-gemini-api-key
POLYGON_RPC_URL=https://rpc-mumbai.maticvigil.com
CONTRACT_ADDRESS=0x1234567890123456789012345678901234567890
WEB3_PRIVATE_KEY=your-ethereum-private-key

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=noreply@credify.app

# CORS
CORS_ORIGINS=http://localhost:3000,https://credify.app

# Storage
S3_BUCKET=credify-certificates
S3_REGION=us-east-1
S3_ACCESS_KEY=your-aws-access-key
S3_SECRET_KEY=your-aws-secret-key

# Environment
ENVIRONMENT=development|production
LOG_LEVEL=INFO
DEBUG=False

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=Credify
```

---

## Database Migrations

### Initial Setup

```bash
# 1. Create database
createdb -h localhost -U credify credify

# 2. Initialize Alembic
cd Credify-backend
alembic init migrations

# 3. Configure alembic.ini
# Set: sqlalchemy.url = postgresql://credify:password@localhost/credify

# 4. Create initial migration
alembic revision --autogenerate -m "Initial schema"

# 5. Apply migrations
alembic upgrade head
```

### Migration Scripts

**Location:** `Credify-backend/migrations/versions/`

```python
# Example: 001_initial_schema.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid()),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(15), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime()),
        sa.Column('shard_key', sa.BigInteger(), default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('phone')
    )

    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_org_id', 'users', ['organization_id'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])

    # ... more tables ...

def downgrade():
    op.drop_table('users')
```

### Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 001_initial_schema

# Check current revision
alembic current

# View migration history
alembic history
```

---

## Deployment Procedure

### Step 1: Prepare Code

```bash
# 1. Clone repository
git clone https://github.com/credify/credify.git
cd credify

# 2. Create feature branch
git checkout -b deploy/production

# 3. Verify all tests pass
cd Credify-backend
pytest tests/ -v
cd ../Credify-frontend
npm test

# 4. Build Docker images locally
docker-compose build

# 5. Test Docker images
docker-compose up
# Visit http://localhost:3000
```

### Step 2: Push to Repository

```bash
# 1. Commit changes
git add .
git commit -m "Prepare for production deployment"

# 2. Push to GitHub
git push origin deploy/production

# 3. Create pull request
gh pr create --title "Production Deployment" \
  --body "Ready for production deployment"
```

### Step 3: Deploy via Railway.app

**Option A: Automatic Deployment**
- Railway automatically deploys on push to main branch
- Verify deployment in Railway dashboard

**Option B: Manual Deployment via CLI**

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login to Railway
railway login

# 3. Select project
railway link <project-id>

# 4. Deploy
railway up
```

### Step 4: Run Database Migrations

```bash
# 1. Connect to Railway PostgreSQL
railway shell

# 2. Run migrations
alembic upgrade head

# 3. Seed initial data (optional)
python scripts/seed_admin.py
python scripts/seed_demo_data.py

# 4. Verify database
SELECT * FROM users LIMIT 1;
```

### Step 5: Verify Deployment

```bash
# 1. Check services status
railway status

# 2. View logs
railway logs

# 3. Test health endpoints
curl https://api-prod.railway.app/api/v1/health
curl https://api-prod.railway.app/api/v1/health/status

# 4. Test API endpoints
curl -X POST https://api-prod.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

---

## Post-Deployment Verification

### Checklist

```
[ ] All services running (backend, frontend, postgres, redis)
[ ] Database migrations applied successfully
[ ] API endpoints responding (200 OK)
[ ] Health checks passing
[ ] Frontend loading correctly
[ ] Login flow working
[ ] WebSocket connections establishing
[ ] Gemini API connected
[ ] Blockchain RPC connected
[ ] Email service working
[ ] Rate limiting active
[ ] Logging operational
[ ] Monitoring dashboards active
[ ] SSL certificates valid
[ ] CORS headers correct
```

### Monitoring & Logs

**Access Railway Dashboard:**
1. Go to https://railway.app
2. Select project
3. View logs in real-time
4. Check service metrics

**Local Log Inspection:**

```bash
# Backend logs
docker logs -f credify-backend

# Frontend logs
docker logs -f credify-frontend

# Database logs
docker logs -f credify-postgres
```

---

## Rollback Procedures

### Quick Rollback

```bash
# 1. Identify previous commit
git log --oneline -n 10

# 2. Revert to previous version
git revert <commit-hash>
git push origin main

# 3. Railway automatically deploys previous version
# Monitor deployment in dashboard

# 4. Verify rollback
curl https://api-prod.railway.app/api/v1/health/status
```

### Database Rollback

```bash
# 1. Connect to production database
railway shell

# 2. Rollback one migration
alembic downgrade -1

# 3. Verify data integrity
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM certificates;

# 4. If issues, contact database administrator
```

---

## Scaling & Performance

### Current Limits (Single Server)

- **Concurrent Users:** 500
- **Requests/second:** 100
- **Database Connections:** ~100 (via PgBouncer)
- **Memory:** 2GB
- **Storage:** 100GB

### Monitoring Metrics

```python
# Key metrics to monitor
- API response time (target: < 200ms)
- Fraud detection time (target: < 5s)
- Database query time (target: < 100ms)
- Error rate (target: < 0.1%)
- Cache hit rate (target: > 80%)
```

### Future Scaling

When approaching limits:

1. **Vertical Scaling:** Increase Railway instance size
2. **Horizontal Scaling:** Implement database sharding via shard_key
3. **CDN:** Add Cloudflare for frontend
4. **Load Balancer:** Add nginx reverse proxy
5. **Cache Layer:** Increase Redis memory and clusters

---

## Troubleshooting

### Issue: Containers Won't Start

```bash
# Check Docker daemon
docker ps

# Check logs
docker-compose logs -f

# Rebuild and restart
docker-compose build --no-cache
docker-compose up --force-recreate
```

### Issue: Database Connection Failed

```bash
# Verify DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check PgBouncer
docker logs credify-pgbouncer
```

### Issue: API Timeout

```bash
# Check API container
docker logs credify-backend

# Test local connectivity
curl http://localhost:8000/api/v1/health

# Check logs for Gemini/Blockchain delays
docker logs credify-backend | grep -i gemini
```

---

## Related Documentation

- [00-ARCHITECTURE_OVERVIEW.md](00-ARCHITECTURE_OVERVIEW.md) - System architecture
- [02-DATABASE_SCHEMA.md](02-DATABASE_SCHEMA.md) - Database design
- [03-API_DOCUMENTATION.md](03-API_DOCUMENTATION.md) - API reference

---

**Last Updated:** 2024-10-31
**Version:** 1.0
**Status:** Production Ready
