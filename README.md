# Credify Backend API

AI-powered fraud detection system for academic certificates. Built with FastAPI, MongoDB, and 6-layer fraud detection pipeline.

## Quick Start

### Prerequisites
- Python 3.10+
- MongoDB 7.0+
- Redis 7.0+
- Docker & Docker Compose (optional)

### Installation

1. **Clone repository and navigate to backend**
```bash
cd Credify-backend
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run with Docker Compose**
```bash
docker-compose up
```

## 6-Layer Fraud Detection Pipeline

1. **EXIF Metadata** (0-20 pts) - Analyze image metadata
2. **Error Level Analysis** (0-20 pts) - Detect compression artifacts
3. **AI Vision (Gemini)** (0-20 pts) - Seal/text/layout analysis
4. **Database Cross-Check** (0-20 pts) - Fuzzy match against DB
5. **Blockchain** (0-10 pts) - Verify on Polygon Mumbai
6. **Geo-Fraud Patterns** (0-10 pts) - Detect fraud rings

## API Endpoints

- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/verification/verify` - Verify certificate
- `POST /api/certificates/upload` - Upload certificate
- `GET /api/health` - Health check

See OpenAPI docs at `/docs` when running.