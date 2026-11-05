# NoticeSaathi — Staging Infrastructure & Controlled Pilot Deployment Runbook

**Environment:** Staging / Pre-Pilot Production  
**Target Architecture:** Linux (Ubuntu 24.04 LTS), Docker Compose, PostgreSQL 16 Alpine, FastAPI Backend, Next.js 15 Frontend  
**Audience:** Site Reliability Engineers, DevOps, System Administrators  
**Core Principle:** *Private by default. Isolated credentials. Immutable data minimization.*

---

## 1. Pre-Deployment Configuration & Secrets

### 1.1 Environment Template (`.env.production`)
Create `.env.production` on the target staging host with secure random values:

```bash
# General
ENVIRONMENT=staging
DEBUG=false
SECRET_KEY=<generate_secure_random_64_char_hex>
PROJECT_NAME="NoticeSaathi"
VERSION="1.0.0"

# Database (PostgreSQL 16)
DATABASE_URL=postgresql://noticesaathi_user:<secure_db_password>@postgres:5432/noticesaathi_db
POSTGRES_USER=noticesaathi_user
POSTGRES_PASSWORD=<secure_db_password>
POSTGRES_DB=noticesaathi_db

# Storage
STORAGE_LOCAL_DIR=/var/noticesaathi/data/storage
MAX_UPLOAD_SIZE_BYTES=15728640
MAX_PAGES_PER_DOC=20
RETENTION_HOURS=48

# Gnani AI (Live Credentials)
GNANI_API_KEY=<official_gnani_api_key_when_issued>
GNANI_BASE_URL=https://api.vachana.ai
GNANI_STT_ENDPOINT=/stt/v3
GNANI_TTS_ENDPOINT=/api/v1/tts/inference
GNANI_TTS_MODEL=timbre-v2.5

# Cloud Translation (Optional with explicit consent)
TRANSLATION_PROVIDER=auto
REQUIRE_CONSENT_FOR_CLOUD_TRANSLATION=true
GOOGLE_TRANSLATE_API_KEY=
AZURE_TRANSLATOR_KEY=
AZURE_TRANSLATOR_REGION=centralindia
```

### 1.2 Storage Permissions
On the host filesystem, isolate private document storage:
```bash
sudo mkdir -p /var/noticesaathi/data/storage
sudo mkdir -p /var/noticesaathi/backups
sudo chmod 700 /var/noticesaathi/data/storage
sudo chown -R 10001:10001 /var/noticesaathi/data/storage
```

---

## 2. PostgreSQL Migrations & Database Initialization

Run database migrations via Alembic inside the API container:
```bash
# Verify current migration head
docker compose run --rm api alembic current

# Upgrade to latest revision (8b29da7753ab)
docker compose run --rm api alembic upgrade head
```

---

## 3. Application Health Probe & Verification

The staging server exposes a comprehensive readiness probe:
```bash
curl -f -s https://staging.noticesaathi.org/api/v1/health | jq .
```

Expected JSON response for a fully operational staging deployment:
```json
{
  "status": "healthy",
  "service": "NoticeSaathi",
  "version": "1.0.0",
  "environment": "staging",
  "checks": {
    "database": "connected",
    "storage": "writable",
    "ocr_engine": "ready"
  },
  "gnani_integration": {
    "configured": true,
    "mode": "live",
    "stt_endpoint": "/stt/v3",
    "tts_endpoint": "/api/v1/tts/inference"
  },
  "translation_engine": {
    "default_provider": "auto",
    "grounded_local_engine": "ready",
    "cloud_consent_required": true
  }
}
```

---

## 4. Background Data Retention & TTL Cleanup

Schedule the 48-hour document retention cleanup script via crontab:
```bash
# /etc/cron.d/noticesaathi-retention
# Runs hourly to purge documents older than 48 hours
0 * * * * noticesaathi /opt/noticesaathi/venv/bin/python /opt/noticesaathi/scripts/cleanup_expired_documents.py >> /var/log/noticesaathi/retention.log 2>&1
```

---

## 5. Automated Disaster Recovery & Backups

Execute automated daily snapshots of database state and storage archives:
```bash
# Run backup utility
python scripts/backup_restore.py --action backup --dir /var/noticesaathi/backups

# Restoration procedure (Disaster recovery)
python scripts/backup_restore.py --action restore \
  --db-file /var/noticesaathi/backups/notice_saathi_db_20261030_120000Z.sqlite \
  --storage-file /var/noticesaathi/backups/notice_saathi_storage_20261030_120000Z.tar.gz
```

---

## 6. HTTPS & Reverse Proxy Configuration (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name staging.noticesaathi.org;

    ssl_certificate /etc/letsencrypt/live/staging.noticesaathi.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging.noticesaathi.org/privkey.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend Next.js Web App
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

