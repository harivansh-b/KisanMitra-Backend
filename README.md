# KisanMitra Backend

> **Agri Market Linkage Platform** — A three-sided marketplace connecting Farmers, FPOs (Farmer Producer Organizations), and Buyers.

Built with **FastAPI + Supabase PostgreSQL + PostGIS + SQLAlchemy + Alembic**.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Environment Variables](#3-environment-variables)
4. [Supabase Setup](#4-supabase-setup)
5. [Local Development Setup](#5-local-development-setup)
6. [Database Migrations (Alembic)](#6-database-migrations-alembic)
7. [Running the API Server](#7-running-the-api-server)
8. [API Documentation](#8-api-documentation)
9. [Authentication Flow](#9-authentication-flow)
10. [Role-Based Access Control (RBAC)](#10-role-based-access-control-rbac)
11. [Storage (Supabase Storage)](#11-storage-supabase-storage)
12. [Geographic Features (PostGIS)](#12-geographic-features-postgis)
13. [Running Tests](#13-running-tests)
14. [Project Structure](#14-project-structure)
15. [Future Services (Placeholders)](#15-future-services-placeholders)

---

## 1. Architecture Overview

KisanMitra follows a **clean, modular service-oriented architecture**. All business logic lives in `app/services/`, HTTP concerns in `app/api/v1/`, and data models in `app/models/`.

```
Client (Mobile/Web)
        |
        v
  FastAPI Application
  +-- Supabase Auth  ---------------> Supabase Auth (JWT verification)
  +-- API Routers (app/api/v1/)
  +-- Services (app/services/)
  |   +-- auth_service        --- Profile registration
  |   +-- farmer_service      --- Farmer CRUD, listings
  |   +-- fpo_service         --- FPO CRUD, members
  |   +-- buyer_service       --- Buyer CRUD, requirements
  |   +-- listing_service     --- Produce listings
  |   +-- marketplace_service --- Deterministic matching engine
  |   +-- order_service       --- Order state machine
  |   +-- transaction_service --- Payment records
  |   +-- storage_service     --- File upload/download
  |   +-- crop_service        --- Crop catalogue
  |
  +-- SQLAlchemy ORM -----------> Supabase PostgreSQL + PostGIS
  +-- Supabase Storage ---------> Supabase Storage Buckets
```

### User Roles

| Role | Description |
|------|-------------|
| **FARMER** | Individual farmers who create produce listings |
| **FPO** | Farmer Producer Organizations that aggregate produce and manage members |
| **BUYER** | Wholesalers, processors, exporters, retailers who post purchase requirements |

---

## 2. Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| PostgreSQL with PostGIS | (via Supabase - no local install needed) |
| Git | Any |

Supabase account with:
- A Supabase project (PostgreSQL + Auth + Storage)
- PostGIS extension enabled on the project

---

## 3. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Full Supabase PostgreSQL connection string | `postgresql+psycopg2://postgres.xyz:pw@aws-0-ap-south-1.pooler.supabase.com:5432/postgres` |
| `SUPABASE_URL` | Your Supabase project URL | `https://xyz.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase public anon key | `eyJh...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (admin) | `eyJh...` |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase dashboard -> Settings -> API | `your-jwt-secret` |
| `ENVIRONMENT` | `development` / `production` / `testing` | `development` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000,http://localhost:8081` |
| `MAX_UPLOAD_SIZE_MB` | Maximum file upload size in MB | `10` |
| `DOCUMENTS_BUCKET` | Supabase Storage bucket for documents | `documents` |
| `PRODUCE_IMAGES_BUCKET` | Bucket for produce listing images | `produce-images` |
| `PROFILE_IMAGES_BUCKET` | Bucket for user profile images | `profile-images` |

> WARNING: Never commit `.env` to version control. Use `.env.example` as the reference.

---

## 4. Supabase Setup

### 4.1 Enable PostGIS

In your Supabase dashboard -> **Database -> Extensions**, enable **PostGIS**. Alembic also runs `CREATE EXTENSION IF NOT EXISTS postgis` automatically during migrations.

### 4.2 Create Storage Buckets

In Supabase dashboard -> **Storage**, create three buckets:

| Bucket Name | Access | Purpose |
|-------------|--------|---------|
| `documents` | Private | KYC documents, certifications |
| `produce-images` | Public | Produce listing photos |
| `profile-images` | Public | User/organization profile photos |

### 4.3 Get Auth Keys

From **Project Settings -> API**:
- Copy **Project URL** -> `SUPABASE_URL`
- Copy **anon / public** key -> `SUPABASE_ANON_KEY`
- Copy **service_role** key -> `SUPABASE_SERVICE_ROLE_KEY`
- Copy **JWT Secret** -> `SUPABASE_JWT_SECRET`

### 4.4 Get Database URL

From **Project Settings -> Database -> Connection string** (Python/SQLAlchemy format):
```
postgresql+psycopg2://postgres.[project-ref]:[password]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

---

## 5. Local Development Setup

```bash
# Clone and enter directory
git clone <repo-url>
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 6. Database Migrations (Alembic)

All migrations live in `alembic/versions/`. The Alembic configuration reads `DATABASE_URL` from `.env` automatically.

```bash
# Apply all pending migrations
alembic upgrade head

# Check current migration status
alembic current

# View migration history
alembic history --verbose

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Rollback one migration
alembic downgrade -1
```

> NOTE: Alembic automatically runs `CREATE EXTENSION IF NOT EXISTS postgis` on PostgreSQL before applying migrations.

---

## 7. Running the API Server

```bash
# Development (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

On startup, the application:
1. Connects to the database
2. Seeds default crop catalogue (idempotent - safe to run multiple times)

---

## 8. API Documentation

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | **Swagger UI** - interactive API explorer |
| `http://localhost:8000/redoc` | **ReDoc** - clean API reference |
| `http://localhost:8000/openapi.json` | Raw OpenAPI schema |

### API Groups

| Prefix | Description |
|--------|-------------|
| `/api/v1/auth` | Profile registration, current user info |
| `/api/v1/farmers` | Farmer profile management, produce listings |
| `/api/v1/fpos` | FPO profile management, member management |
| `/api/v1/buyers` | Buyer profile management, purchase requirements |
| `/api/v1/crops` | Crop catalogue (browse, create, manage) |
| `/api/v1/listings` | Public produce listing search + matching |
| `/api/v1/marketplace` | Matching engine (listing<->requirement pairing) |
| `/api/v1/orders` | Order creation, state transitions, history |
| `/api/v1/transactions` | Payment/transaction records |
| `/api/v1/storage` | File upload/download/delete |
| `/api/v1/geo` | Geographic utilities |

---

## 9. Authentication Flow

KisanMitra uses **Supabase Auth** for identity management.

```
1. Client registers/logs in via Supabase Auth SDK
   (Mobile app / web frontend uses @supabase/supabase-js)

2. Supabase returns a JWT access_token

3. Client sends: Authorization: Bearer <access_token>

4. Backend verifies JWT:
   a. First tries local HMAC verification using SUPABASE_JWT_SECRET (fast, offline)
   b. Falls back to Supabase API GET /auth/v1/user (network call)

5. Verified auth_user_id is looked up in local `users` table

6. Role-based dependencies enforce FARMER / FPO / BUYER access
```

### Profile Registration

After Supabase Auth sign-up, users must register their profile:

```http
POST /api/v1/auth/register
Authorization: Bearer <supabase_jwt>

{
  "role": "FARMER",
  "phone": "9876543210"
}
```

This creates a `users` record. The user can then complete their role-specific profile (FarmerProfile, FPOProfile, BuyerProfile).

---

## 10. Role-Based Access Control (RBAC)

FastAPI dependencies in `app/core/dependencies.py` enforce role checks:

| Dependency | Allows |
|------------|--------|
| `get_current_user` | Any authenticated user |
| `get_current_farmer` | FARMER only |
| `get_current_fpo` | FPO only |
| `get_current_buyer` | BUYER only |
| `get_current_seller` | FARMER or FPO |

---

## 11. Storage (Supabase Storage)

Files are stored in Supabase Storage buckets. The `storage_service.py` handles:

- Upload with content-type detection
- Metadata persistence in PostgreSQL (`documents` table)
- Signed URL generation for private buckets
- Role-based access (users can only manage their own files)

### Upload a document

```
POST /api/v1/storage/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<binary>
owner_type=farmer
owner_id=<uuid>
```

### Get a signed download URL

```
GET /api/v1/storage/{document_id}/url?expires_in=3600
Authorization: Bearer <token>
```

### Required Storage Buckets

| Bucket | Used for |
|--------|----------|
| `documents` | KYC, certifications, agreements |
| `produce-images` | Listing photos |
| `profile-images` | Profile/org photos |

---

## 12. Geographic Features (PostGIS)

KisanMitra uses PostGIS for location-based queries (e.g., find buyers within 100 km of a farmer).

- Farmer, FPO, and Buyer profiles store `latitude`/`longitude` as floats.
- These are converted to PostGIS `Geography(POINT, 4326)` internally via the `PointGeography` TypeDecorator.
- `geo_service.apply_radius_filter()` uses `ST_DWithin` for efficient spatial queries.

### Example: listings near a location

```
GET /api/v1/listings?lat=18.52&lon=73.86&radius_km=50
```

---

## 13. Running Tests

Tests use **SQLite in-memory** database - no Supabase credentials needed.

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_auth.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Test Matrix

| File | Tests | Coverage |
|------|-------|----------|
| `test_auth.py` | 5 | Auth, profile registration, me endpoint |
| `test_farmers.py` | 4 | Farmer profile, produce listings, RBAC |
| `test_fpos.py` | 3 | FPO profile, member management |
| `test_buyers.py` | 4 | Buyer profile, requirements, RBAC |
| `test_marketplace.py` | 2 | Listing search, deterministic matching |
| `test_orders.py` | 2 | Full order workflow, seller rejection |
| `test_storage.py` | 1 | File upload, metadata, signed URL |
| **Total** | **21** | **21 passed** |

> In test mode (TESTING=1), actual Supabase Storage uploads are skipped. Only metadata is recorded in the test database.

---

## 14. Project Structure

```
backend/
+-- alembic/                    # Database migrations
|   +-- versions/               # Migration files
|   +-- env.py                  # Alembic config (reads from .env)
+-- app/
|   +-- main.py                 # FastAPI app, lifespan, CORS, router registration
|   +-- core/
|   |   +-- config.py           # Pydantic Settings (reads .env)
|   |   +-- database.py         # SQLAlchemy engine, PointGeography TypeDecorator
|   |   +-- dependencies.py     # Auth + role FastAPI dependencies
|   |   +-- exceptions.py       # Exception hierarchy + handlers
|   |   +-- security.py         # JWT verification, Supabase admin client
|   +-- api/
|   |   +-- deps.py             # Re-exports dependencies
|   |   +-- v1/                 # API routers (one per domain)
|   |       +-- auth.py, farmers.py, fpos.py, buyers.py,
|   |           crops.py, listings.py, marketplace.py,
|   |           orders.py, transactions.py, storage.py, geo.py
|   +-- models/                 # SQLAlchemy ORM models
|   |   +-- user.py, farmer.py, fpo.py, fpo_member.py
|   |   +-- buyer.py, buyer_requirement.py, crop.py
|   |   +-- produce_listing.py, order.py, transaction.py, document.py
|   +-- schemas/                # Pydantic request/response schemas
|   +-- services/               # Business logic layer
|   |   +-- auth_service.py, farmer_service.py, fpo_service.py
|   |   +-- buyer_service.py, crop_service.py, listing_service.py
|   |   +-- requirement_service.py, marketplace_service.py
|   |   +-- order_service.py, transaction_service.py
|   |   +-- storage_service.py, geo_service.py
|   |   +-- chatbot_service.py          # [Placeholder - next sprint]
|   |   +-- price_prediction_service.py # [Placeholder - next sprint]
|   |   +-- sales_window_service.py     # [Placeholder - next sprint]
|   +-- utils/
|       +-- enums.py            # All domain enums
|       +-- pagination.py       # PaginationParams, PaginatedResponse
|       +-- validators.py       # Phone, pincode, lat/lon validators
+-- tests/
|   +-- conftest.py             # SQLite test DB, shared fixtures
|   +-- test_auth.py, test_farmers.py, test_fpos.py
|   +-- test_buyers.py, test_marketplace.py
|   +-- test_orders.py, test_storage.py
+-- .env.example                # Environment variable template
+-- alembic.ini                 # Alembic configuration
+-- requirements.txt            # Python dependencies
+-- README.md
```

---

## 15. Future Services (Placeholders)

The following services are scaffolded with clean interfaces but contain **no business logic** - they will be implemented in the next sprint:

| Service | File | Planned Functionality |
|---------|------|-----------------------|
| Chatbot | `app/services/chatbot_service.py` | AI-powered farmer advisory |
| Price Prediction | `app/services/price_prediction_service.py` | ML-based crop price forecasting |
| Sales Window | `app/services/sales_window_service.py` | Optimal selling time prediction |

Each placeholder raises `NotImplementedError` to signal unimplemented state while providing the expected function signatures for seamless integration.

---

## License

Private - KisanMitra Agri-Tech Platform.
