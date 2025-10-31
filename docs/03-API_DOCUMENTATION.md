# API Documentation - Credify Backend

## Complete API Reference Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL & Headers](#base-url--headers)
4. [API Endpoints](#api-endpoints)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Examples](#examples)

---

## Overview

**Credify API** provides comprehensive endpoints for certificate management, verification, and fraud detection. All endpoints follow RESTful principles and return JSON responses.

### API Statistics
- **Total Endpoints:** 25+
- **Authentication:** JWT Bearer tokens
- **Rate Limits:** 100 requests/hour (configurable per role)
- **Response Format:** JSON
- **Content-Type:** `application/json`
- **Protocol:** HTTPS (production), HTTP (development)

---

## Authentication

### Token Types

#### Access Token (JWT)
- **Expiry:** 15 minutes
- **Use:** API requests in Authorization header
- **Format:** `Bearer {access_token}`
- **Payload:**
  ```json
  {
    "sub": "user_uuid",
    "email": "user@example.com",
    "org_id": "organization_uuid",
    "role": "admin|staff|limited",
    "account_type": "university|enterprise|public|admin",
    "permissions": ["read:certs", "write:certs"],
    "exp": 1234567890,
    "iat": 1234567500,
    "jti": "unique_token_id"
  }
  ```

#### Refresh Token
- **Expiry:** 7 days
- **Use:** Obtain new access token
- **Storage:** HttpOnly cookie or secure local storage
- **Endpoint:** `POST /api/v1/auth/refresh`

### Authorization Header

All protected endpoints require:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Base URL & Headers

### Base URL
```
Production:  https://api.credify.app/api/v1
Development: http://localhost:8000/api/v1
```

### Standard Headers

```http
Content-Type: application/json
Authorization: Bearer {access_token}
X-Request-ID: unique-request-identifier  (optional, for tracing)
X-Correlation-ID: batch-operation-id     (optional, for bulk operations)
User-Agent: Credify-Client/1.0
```

### Response Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
X-Request-ID: unique-request-identifier
Content-Type: application/json
Cache-Control: no-cache, no-store, must-revalidate
```

---

## API Endpoints

### 1. AUTHENTICATION ROUTES (`/auth`)

#### 1.1 User Signup
```http
POST /auth/signup
Content-Type: application/json

{
  "email": "student@university.edu",
  "password": "SecurePass@123",
  "first_name": "John",
  "last_name": "Doe",
  "role": "student",
  "organization_id": "org_uuid_here"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "user_id": "user_uuid",
    "email": "student@university.edu",
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

**Error Responses:**
```json
{
  "success": false,
  "error": "EMAIL_EXISTS",
  "message": "Email already registered",
  "status_code": 409
}
```

**Validation Rules:**
- Email: Valid format, unique, max 255 characters
- Password: Min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char
- First/Last Name: 2-50 characters
- Organization: Must exist in system

---

#### 1.2 User Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "student@university.edu",
  "password": "SecurePass@123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user_id": "user_uuid",
    "email": "student@university.edu",
    "organization_id": "org_uuid",
    "organization_name": "Sample University",
    "role": "student",
    "account_type": "university",
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer",
    "expires_in": 900,
    "last_login": "2024-10-31T10:00:00Z"
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid email or password
- `403 Forbidden` - Account inactive
- `404 Not Found` - User not found

---

#### 1.3 Refresh Access Token
```http
POST /auth/refresh
Authorization: Bearer {refresh_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGc...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or expired refresh token
- `401 Unauthorized` - Token blacklisted (logged out)

---

#### 1.4 Logout User
```http
POST /auth/logout
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully logged out",
  "data": {
    "user_id": "user_uuid",
    "logout_time": "2024-10-31T10:30:00Z"
  }
}
```

**Side Effects:**
- Access token added to Redis blacklist (TTL: 15 minutes)
- Refresh token added to Redis blacklist (TTL: 7 days)
- User session invalidated

---

#### 1.5 2FA Setup
```http
POST /auth/2fa/setup
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS...",
    "secret": "JBSWY3DPEBLW64TMMQQ",
    "backup_codes": [
      "ABC123DEF456",
      "GHI789JKL012",
      "MNO345PQR678",
      "STU901VWX234",
      "YZA567BCD890",
      "EFG123HIJ456",
      "KLM789NOP012",
      "QRS345TUV678",
      "WXY901ZAB234",
      "CDE567FGH890"
    ]
  }
}
```

---

### 2. CERTIFICATE ROUTES (`/certificates`)

#### 2.1 Upload Single Certificate
```http
POST /certificates/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

Parameters:
  certificate_image (file): JPG/PNG, max 5MB, required
  certificate_name (string): max 255 chars, required
  holder_name (string): max 255 chars, required
  issue_date (string): ISO-8601 date, required
  expiry_date (string): ISO-8601 date, optional
  metadata (json): custom metadata, optional
  degree_type (string): bachelor, master, diploma, etc.
  gpa (number): 0.0-4.0
  field_of_study (string): max 255 chars
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "certificate_id": "cert_uuid",
    "certificate_name": "Bachelor of Science",
    "holder_name": "John Doe",
    "issue_date": "2024-05-15",
    "expiry_date": "2026-05-15",
    "certificate_url": "https://storage.credify.app/certs/cert_uuid.jpg",
    "qr_code_url": "https://storage.credify.app/qr/cert_uuid.png",
    "pdf_url": "https://storage.credify.app/pdf/cert_uuid.pdf",
    "blockchain_hash": "0x1234567890abcdef...",
    "created_at": "2024-10-31T10:00:00Z"
  }
}
```

**Error Responses:**
```json
{
  "success": false,
  "error": "FILE_INVALID_FORMAT",
  "message": "Only JPG and PNG files are supported",
  "status_code": 400
}
```

**Validations:**
- File format: JPG, PNG only
- File size: Max 5MB
- Image dimensions: 640x480 to 4000x3000
- Date validation: Issue date ≤ today, expiry > issue date
- Organization match: Issuer's organization must match request user's organization

---

#### 2.2 Bulk Upload Certificates
```http
POST /certificates/bulk-upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
X-Correlation-ID: bulk_batch_uuid

Parameters:
  csv_file (file): CSV format, required
  certificates (files): Array of certificate images, required
```

**CSV Format:**
```csv
certificate_name,holder_name,issue_date,expiry_date,certificate_file,degree_type,gpa
Bachelor of Science,John Doe,2024-05-15,2026-05-15,cert_001.jpg,bachelor,3.8
Master of Technology,Jane Smith,2023-06-20,2025-06-20,cert_002.png,master,3.9
Diploma in Engineering,Bob Johnson,2022-07-10,,cert_003.jpg,diploma,3.5
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_uuid",
    "total_files": 3,
    "status": "processing",
    "message": "Bulk upload started. Check progress via WebSocket or batch status endpoint.",
    "websocket_url": "wss://api.credify.app/api/v1/certificates/bulk-upload/progress",
    "poll_endpoint": "/certificates/bulk-upload/status/batch_uuid"
  }
}
```

**WebSocket Progress Messages:**
```json
{
  "event": "progress",
  "data": {
    "batch_id": "batch_uuid",
    "processed": 1,
    "total": 3,
    "current_file": "cert_001.jpg",
    "status": "processing",
    "progress_percentage": 33
  }
}
```

**WebSocket Completion Message:**
```json
{
  "event": "complete",
  "data": {
    "batch_id": "batch_uuid",
    "total_uploaded": 3,
    "failed": 0,
    "error_report_url": null,
    "timestamp": "2024-10-31T10:15:00Z"
  }
}
```

---

#### 2.3 Get Certificate Details
```http
GET /certificates/{certificate_id}
Authorization: Bearer {access_token} [optional]
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "certificate_id": "cert_uuid",
    "certificate_name": "Bachelor of Science",
    "holder_name": "John Doe",
    "holder_email": "john@example.com",
    "issuer_id": "issuer_uuid",
    "issue_date": "2024-05-15",
    "expiry_date": "2026-05-15",
    "status": "active",
    "is_revoked": false,
    "certificate_url": "https://storage.credify.app/certs/cert_uuid.jpg",
    "qr_code_url": "https://storage.credify.app/qr/cert_uuid.png",
    "pdf_url": "https://storage.credify.app/pdf/cert_uuid.pdf",
    "blockchain_hash": "0x1234567890abcdef...",
    "blockchain_tx": "0xabcdef1234567890...",
    "verification_count": 5,
    "last_verified_at": "2024-10-30T15:30:00Z",
    "metadata": {
      "degree_type": "bachelor",
      "field_of_study": "Computer Science",
      "gpa": 3.8,
      "credits": 120
    },
    "created_at": "2024-05-20T10:00:00Z",
    "updated_at": "2024-10-31T08:00:00Z"
  }
}
```

---

#### 2.4 List User Certificates
```http
GET /certificates?page=1&limit=10&role=student&search=science
Authorization: Bearer {access_token}

Query Parameters:
  page (number): Page number, default 1
  limit (number): Items per page, default 10, max 100
  role (string): student|issuer, required
  search (string): Search by certificate_name or holder_name
  status (string): active|revoked|expired
  sort_by (string): created_at|updated_at|holder_name
  order (string): asc|desc
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "certificates": [
      {
        "certificate_id": "cert_uuid",
        "certificate_name": "Bachelor of Science",
        "holder_name": "John Doe",
        "issue_date": "2024-05-15",
        "expiry_date": "2026-05-15",
        "status": "active",
        "verification_count": 5,
        "created_at": "2024-05-20T10:00:00Z"
      }
    ],
    "total": 42,
    "page": 1,
    "limit": 10,
    "total_pages": 5
  }
}
```

---

#### 2.5 Download Certificate PDF
```http
GET /certificates/{certificate_id}/download-pdf
Authorization: Bearer {access_token} [optional]
```

**Response (200 OK):**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="certificate.pdf"`
- Body: PDF file stream

**PDF Contents:**
1. Original certificate image
2. QR code linking to verification
3. Issue date and expiry date
4. Blockchain hash for audit
5. Verification URL
6. Credify branding and footer

---

#### 2.6 Revoke Certificate
```http
PATCH /certificates/{certificate_id}/revoke
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "reason": "Fraud detected - holder didn't complete course"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Certificate revoked successfully",
  "data": {
    "certificate_id": "cert_uuid",
    "is_revoked": true,
    "revocation_reason": "Fraud detected - holder didn't complete course",
    "revoked_at": "2024-10-31T10:45:00Z",
    "blockchain_revocation_tx": "0xabcdef1234567890..."
  }
}
```

**Side Effects:**
- Certificate marked as revoked in database
- Blockchain revocation call executed
- Fraud incident record created
- WebSocket notification sent to admin fraud feed

---

#### 2.7 Share Certificate
```http
POST /certificates/{certificate_id}/share
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "emails": [
    "employer@company.com",
    "recruiter@agency.com"
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Certificate shared successfully",
  "data": {
    "certificate_id": "cert_uuid",
    "shared_with": [
      "employer@company.com",
      "recruiter@agency.com"
    ],
    "shared_at": "2024-10-31T10:50:00Z",
    "verification_links": [
      "https://credify.app/verify/token_1",
      "https://credify.app/verify/token_2"
    ]
  }
}
```

---

### 3. VERIFICATION ROUTES (`/verification`)

#### 3.1 Verify Certificate
```http
POST /verification/verify
Authorization: Bearer {access_token} [optional]
Content-Type: multipart/form-data

Parameters:
  certificate_image (file): JPG/PNG, max 5MB, optional if certificate_id provided
  certificate_id (string): UUID, optional if certificate_image provided
  verifier_email (string): Verifier's email, optional
```

**Response (202 Accepted - Async):**
```json
{
  "success": true,
  "status": "processing",
  "data": {
    "verification_id": "verif_uuid",
    "certificate_id": "cert_uuid",
    "status": "processing",
    "progress": 0,
    "current_layer": "exif_analysis",
    "estimated_time_seconds": 4,
    "message": "Verification started. Subscribe to WebSocket for real-time updates.",
    "websocket_url": "wss://api.credify.app/api/v1/verification/stream",
    "poll_endpoint": "/verification/verif_uuid"
  }
}
```

**Response (200 OK - Immediate for cached results):**
```json
{
  "success": true,
  "status": "complete",
  "data": {
    "verification_id": "verif_uuid",
    "certificate_id": "cert_uuid",
    "confidence_score": 87,
    "verdict": "verified",
    "processing_time_ms": 2150,
    "fraud_layers_result": {
      "exif_score": 18,
      "ela_score": 16,
      "gemini_score": 19,
      "database_score": 18,
      "blockchain_score": 10,
      "geo_fraud_score": 6,
      "total_score": 87
    },
    "layer_details": {
      "exif": {
        "score": 18,
        "has_exif": true,
        "camera_info": "Canon EOS 5D Mark IV",
        "software_used": null,
        "gps_present": false,
        "date_reasonable": true,
        "flags": []
      },
      "ela": {
        "score": 16,
        "consistency_percentage": 94.2,
        "cloning_detected": false,
        "splicing_detected": false,
        "heatmap_base64": "data:image/png;base64,iVBORw0KGgo..."
      },
      "gemini": {
        "score": 19,
        "seal_authentic": true,
        "seal_confidence": 0.96,
        "layout_professional": true,
        "detected_editing": false,
        "extracted_text": "Certificate of Achievement..."
      },
      "database": {
        "score": 18,
        "match_found": true,
        "matched_certificate_id": "original_cert_uuid",
        "match_quality": "exact",
        "is_revoked": false
      },
      "blockchain": {
        "score": 10,
        "blockchain_verified": true,
        "transaction_hash": "0xabcdef..."
      },
      "geo_fraud": {
        "score": 6,
        "ip_address": "203.0.113.42",
        "geolocation": {
          "country": "IN",
          "city": "Bangalore",
          "latitude": 12.9716,
          "longitude": 77.5946
        },
        "anomalies_detected": ["bulk_verification_pattern"]
      }
    },
    "report_url": "https://storage.credify.app/reports/verif_uuid.pdf",
    "verified_at": "2024-10-31T11:00:00Z",
    "created_at": "2024-10-31T11:00:00Z"
  }
}
```

---

#### 3.2 Get Verification Status
```http
GET /verification/{verification_id}
Authorization: Bearer {access_token} [optional]
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "verification_id": "verif_uuid",
    "status": "complete",
    "confidence_score": 87,
    "verdict": "verified",
    "processing_time_ms": 2150,
    "fraud_layers_result": {
      "total_score": 87,
      "exif_score": 18,
      "ela_score": 16,
      "gemini_score": 19,
      "database_score": 18,
      "blockchain_score": 10,
      "geo_fraud_score": 6
    },
    "created_at": "2024-10-31T11:00:00Z"
  }
}
```

---

#### 3.3 Verification History
```http
GET /verification/history?certificate_id={cert_id}&page=1&limit=10
Authorization: Bearer {access_token}

Query Parameters:
  certificate_id (string): Certificate UUID, required
  page (number): Page number, default 1
  limit (number): Items per page, max 100
  verdict (string): verified|suspicious|fraud
  sort_by (string): created_at (default) | confidence_score
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "verifications": [
      {
        "verification_id": "verif_uuid",
        "confidence_score": 87,
        "verdict": "verified",
        "processing_time_ms": 2150,
        "verified_at": "2024-10-31T11:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "limit": 10
  }
}
```

---

#### 3.4 WebSocket Verification Stream
```
WS /verification/stream
Authorization: Bearer {access_token} [optional]
```

**Subscribe Message:**
```json
{
  "action": "subscribe",
  "verification_id": "verif_uuid"
}
```

**Progress Update:**
```json
{
  "event": "progress",
  "data": {
    "verification_id": "verif_uuid",
    "layer": "exif_analysis",
    "layer_number": 1,
    "progress": 15,
    "status": "processing"
  }
}
```

**Layer Complete:**
```json
{
  "event": "layer_complete",
  "data": {
    "verification_id": "verif_uuid",
    "layer": "exif_analysis",
    "score": 18,
    "progress": 20
  }
}
```

**Verification Complete:**
```json
{
  "event": "complete",
  "data": {
    "verification_id": "verif_uuid",
    "confidence_score": 87,
    "verdict": "verified",
    "fraud_layers_result": {...},
    "processing_time_ms": 2150
  }
}
```

---

### 4. ADMIN ROUTES (`/admin`)

#### 4.1 Fraud Feed
```http
GET /admin/fraud-feed?limit=50&verdict=fraud
Authorization: Bearer {access_token}

Query Parameters:
  limit (number): Items to return, default 50, max 500
  verdict (string): verified|suspicious|fraud
  min_confidence (number): Minimum confidence score, 0-100
  max_confidence (number): Maximum confidence score, 0-100
  start_date (string): ISO-8601 date
  end_date (string): ISO-8601 date
  sort_by (string): created_at (default) | confidence_score | location
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "incidents": [
      {
        "verification_id": "verif_uuid",
        "certificate_id": "cert_uuid",
        "verdict": "fraud",
        "confidence_score": 15,
        "issue_date": "2024-10-31T10:45:00Z",
        "ip_address": "203.0.113.99",
        "geolocation": {
          "country": "IN",
          "city": "Delhi",
          "latitude": 28.7041,
          "longitude": 77.1025
        },
        "fraud_type": "forged",
        "holder_name": "Unknown",
        "institution_name": "Fake University"
      }
    ],
    "total": 127,
    "processed_today": 450,
    "fraud_rate_today": 28.2
  }
}
```

---

#### 4.2 Analytics Dashboard
```http
GET /admin/analytics?start_date=2024-10-01&end_date=2024-10-31
Authorization: Bearer {access_token}

Query Parameters:
  start_date (string): ISO-8601 start date
  end_date (string): ISO-8601 end date
  group_by (string): day|week|month (default: day)
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "period": {
      "start_date": "2024-10-01",
      "end_date": "2024-10-31",
      "days": 31
    },
    "summary": {
      "total_verifications": 12450,
      "verified_count": 10120,
      "suspicious_count": 1980,
      "fraud_count": 350
    },
    "statistics": {
      "average_confidence_score": 82.4,
      "success_rate": 81.2,
      "fraud_rate": 2.8,
      "suspicious_rate": 15.9
    },
    "verification_rate_per_hour": 21.5,
    "top_fraud_types": {
      "forged": 180,
      "template": 95,
      "metadata": 45,
      "unknown": 30
    },
    "geographic_distribution": [
      {
        "country": "IN",
        "state": "Karnataka",
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "verifications": 2450,
        "fraud_count": 68
      }
    ],
    "layer_effectiveness": {
      "exif_layer": 92.1,
      "ela_layer": 88.5,
      "gemini_layer": 94.3,
      "database_layer": 96.2,
      "blockchain_layer": 85.6,
      "geo_fraud_layer": 76.4
    },
    "hourly_distribution": [
      {
        "hour": 0,
        "verifications": 420,
        "fraud_count": 12
      }
    ]
  }
}
```

---

#### 4.3 Manual Review Queue
```http
GET /admin/review-queue?confidence_min=40&confidence_max=80&page=1
Authorization: Bearer {access_token}

Query Parameters:
  confidence_min (number): Minimum confidence, default 40
  confidence_max (number): Maximum confidence, default 80
  page (number): Page number
  limit (number): Items per page, default 10
  priority (string): high|normal|low
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "reviews": [
      {
        "verification_id": "verif_uuid",
        "certificate_id": "cert_uuid",
        "confidence_score": 58,
        "verdict": "suspicious",
        "reason": "Multiple compression layers detected",
        "reviewed_by": null,
        "review_status": "pending",
        "created_at": "2024-10-31T10:00:00Z"
      }
    ],
    "total": 234,
    "page": 1,
    "high_priority_count": 45,
    "normal_priority_count": 145
  }
}
```

---

#### 4.4 User Management
```http
GET /admin/users?role=issuer&page=1&limit=20
Authorization: Bearer {access_token}

Query Parameters:
  role (string): student|issuer|verifier|admin
  status (string): active|inactive|suspended
  page (number): Page number
  limit (number): Items per page
  search (string): Search by email or name
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "user_uuid",
        "email": "issuer@university.edu",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "account_type": "university",
        "organization_id": "org_uuid",
        "is_active": true,
        "last_login": "2024-10-31T08:30:00Z",
        "created_at": "2024-01-15T10:00:00Z"
      }
    ],
    "total": 145,
    "page": 1
  }
}
```

---

#### 4.5 Disable User
```http
PATCH /admin/users/{user_id}/disable
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "reason": "Fraudulent activity detected",
  "notify_user": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "User disabled successfully",
  "data": {
    "user_id": "user_uuid",
    "is_active": false,
    "disabled_at": "2024-10-31T11:00:00Z"
  }
}
```

---

#### 4.6 WebSocket Admin Fraud Feed
```
WS /admin/fraud-stream
Authorization: Bearer {access_token}
```

**Fraud Alert Message:**
```json
{
  "event": "fraud_detected",
  "data": {
    "verification_id": "verif_uuid",
    "certificate_id": "cert_uuid",
    "verdict": "fraud",
    "confidence_score": 18,
    "fraud_type": "forged",
    "location": {
      "country": "IN",
      "city": "Mumbai"
    },
    "timestamp": "2024-10-31T11:05:00Z"
  }
}
```

---

### 5. HEALTH ROUTES (`/health`)

#### 5.1 Health Check
```http
GET /health
```

**Response (200 OK):**
```json
{
  "success": true,
  "status": "ok",
  "timestamp": "2024-10-31T11:10:00Z"
}
```

---

#### 5.2 Service Status
```http
GET /health/status
```

**Response (200 OK):**
```json
{
  "success": true,
  "status": "healthy",
  "data": {
    "database": {
      "status": "connected",
      "response_time_ms": 45,
      "connections_active": 12
    },
    "redis": {
      "status": "connected",
      "response_time_ms": 8,
      "memory_used_mb": 125
    },
    "gemini_api": {
      "status": "available",
      "last_check": "2024-10-31T11:09:00Z",
      "response_time_ms": 320
    },
    "blockchain": {
      "status": "available",
      "network": "Polygon Mumbai",
      "last_block": 45632189,
      "last_check": "2024-10-31T11:08:00Z"
    },
    "uptime_seconds": 864000,
    "uptime_hours": 240,
    "version": "1.0.0",
    "environment": "production"
  }
}
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "User-friendly error message",
  "status_code": 400,
  "details": {
    "field": "email",
    "constraint": "unique",
    "value_provided": "existing@email.com"
  },
  "timestamp": "2024-10-31T11:15:00Z",
  "request_id": "req_uuid_12345"
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful request |
| 201 | Created | Certificate uploaded successfully |
| 202 | Accepted | Async verification started |
| 400 | Bad Request | Invalid input validation |
| 401 | Unauthorized | Missing or invalid JWT |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Certificate doesn't exist |
| 409 | Conflict | Email already registered |
| 413 | Payload Too Large | File exceeds 5MB |
| 429 | Too Many Requests | Rate limit exceeded |
| 503 | Service Unavailable | Gemini API down |
| 500 | Internal Error | Server error |

### Error Codes

```
VALIDATION_ERROR
- Invalid input format
- Missing required fields
- Constraint violations

AUTHENTICATION_ERRORS
- INVALID_CREDENTIALS
- TOKEN_EXPIRED
- TOKEN_INVALID
- USER_INACTIVE

AUTHORIZATION_ERRORS
- INSUFFICIENT_PERMISSIONS
- FORBIDDEN_RESOURCE

RESOURCE_ERRORS
- EMAIL_EXISTS
- USER_NOT_FOUND
- CERTIFICATE_NOT_FOUND
- VERIFICATION_NOT_FOUND
- INSTITUTION_NOT_FOUND

FILE_ERRORS
- FILE_INVALID_FORMAT
- FILE_TOO_LARGE
- IMAGE_DIMENSIONS_INVALID

RATE_LIMIT_ERRORS
- RATE_LIMIT_EXCEEDED

EXTERNAL_SERVICE_ERRORS
- GEMINI_API_ERROR
- BLOCKCHAIN_ERROR
- SMTP_ERROR

SYSTEM_ERRORS
- DATABASE_ERROR
- REDIS_ERROR
- INTERNAL_SERVER_ERROR
```

---

## Rate Limiting

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

### Rate Limit Rules

| Endpoint | Limit | Window |
|----------|-------|--------|
| General endpoints | 100 | 1 hour |
| Login attempts | 5 | 15 minutes |
| Verification | 10 | 1 hour |
| Certificate upload | 20 | 1 hour |
| Admin endpoints | 50 | 1 hour |
| Health check | Unlimited | - |
| Public verification | Unlimited | - |

### Rate Limit Error Response

```json
{
  "success": false,
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again in 3600 seconds.",
  "status_code": 429,
  "details": {
    "limit": 100,
    "remaining": 0,
    "reset_at": "2024-10-31T12:15:00Z"
  }
}
```

---

## Examples

### Example 1: Complete Verification Flow

**Step 1: Upload Certificate**
```bash
curl -X POST http://localhost:8000/api/v1/certificates/upload \
  -H "Authorization: Bearer {access_token}" \
  -F "certificate_image=@certificate.jpg" \
  -F "certificate_name=Bachelor of Science" \
  -F "holder_name=John Doe" \
  -F "issue_date=2024-05-15"
```

**Step 2: Verify Certificate**
```bash
curl -X POST http://localhost:8000/api/v1/verification/verify \
  -H "Authorization: Bearer {access_token}" \
  -F "certificate_id=cert_uuid"
```

**Step 3: Subscribe to WebSocket**
```javascript
const ws = new WebSocket('wss://localhost:8000/api/v1/verification/stream');
ws.send(JSON.stringify({
  action: 'subscribe',
  verification_id: 'verif_uuid'
}));
```

---

### Example 2: Bulk Upload with Progress

**Step 1: Prepare CSV and files**
```
certificates.csv
cert_001.jpg
cert_002.jpg
cert_003.jpg
```

**Step 2: Submit bulk upload**
```bash
curl -X POST http://localhost:8000/api/v1/certificates/bulk-upload \
  -H "Authorization: Bearer {access_token}" \
  -F "csv_file=@certificates.csv" \
  -F "certificates=@cert_001.jpg" \
  -F "certificates=@cert_002.jpg" \
  -F "certificates=@cert_003.jpg"
```

**Step 3: Monitor progress**
```javascript
const ws = new WebSocket('wss://localhost:8000/api/v1/certificates/bulk-upload/progress');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.processed}/${data.total}`);
};
```

---

## Related Documentation

- [01-AUTHENTICATION_GUIDE.md](01-AUTHENTICATION_GUIDE.md) - Authentication system details
- [02-DATABASE_SCHEMA.md](02-DATABASE_SCHEMA.md) - Database design
- [04-FRAUD_DETECTION_GUIDE.md](04-FRAUD_DETECTION_GUIDE.md) - Fraud detection pipeline
- [05-DEPLOYMENT.md](05-DEPLOYMENT.md) - Deployment procedures

---

**Last Updated:** 2024-10-31
**API Version:** 1.0
**Status:** Production Ready
