# NoticeSaathi — Google Cloud Production Deployment Guide

This guide describes the complete, step-by-step production deployment of **NoticeSaathi** onto **Google Cloud Platform (GCP)** using **Cloud Run**, **Cloud SQL for PostgreSQL**, **Google Cloud Storage (GCS)**, **Google Secret Manager**, and **Cloud Scheduler**.

---

## 1. Target Architecture Topology

The production deployment decouples the frontend user interface and backend document/AI processing engines into stateless containerized services running on fully-managed Google Cloud Run, supported by enterprise cloud data services.

```mermaid
graph TD
    User["Citizen / User Browser<br/>(Desktop / Mobile)"] -->|HTTPS (Port 443)| CloudRunWeb["Google Cloud Run: Frontend<br/>(Next.js 15 / React 19 / SSR)"]
    CloudRunWeb -->|REST / HTTPS| CloudRunAPI["Google Cloud Run: Backend<br/>(FastAPI / Python 3.12 / RapidOCR)"]
    
    subgraph Google Cloud Platform (Region: asia-south1)
        subgraph Serverless Compute
            CloudRunWeb
            CloudRunAPI
            CronJob["Cloud Run Job<br/>(Retention Sweep Worker)"]
        end

        subgraph Managed Data & Storage
            CloudSQL[("Google Cloud SQL<br/>PostgreSQL 16 (HA)")]
            GCS[("Google Cloud Storage<br/>Private Bucket (Encrypted)")]
        end

        subgraph Security & Governance
            SecretManager["Google Secret Manager<br/>(Keys, DB Passwords, Tokens)"]
            IAM["Cloud IAM<br/>(Least Privilege Service Accounts)"]
        end

        subgraph Automation & Observability
            Scheduler["Cloud Scheduler<br/>(Hourly Cron Trigger)"]
            CloudLogging["Cloud Logging & Monitoring"]
        end
    end

    subgraph External Voice AI
        GnaniVoice["Gnani AI Cloud<br/>(Prisma STT / Timbre TTS)"]
    end

    CloudRunAPI -->|Cloud SQL Connector| CloudSQL
    CloudRunAPI -->|Authenticated Storage API / FUSE| GCS
    CloudRunAPI -->|Secret Accessor| SecretManager
    CloudRunAPI -->|HTTPS / API Key| GnaniVoice
    Scheduler -->|Trigger via IAM| CronJob
    CronJob -->|Database Cleanup| CloudSQL
    CronJob -->|Delete Expired Files| GCS
    CloudRunAPI -->|Structured JSON Logs| CloudLogging
```

---

## 2. Infrastructure Sizing & Requirements

| Service | Component | Recommended Sizing | Notes |
| :--- | :--- | :--- | :--- |
| **Cloud Run Web** | Next.js Frontend | 1 vCPU, 512 MB RAM | Min instances: 0, Max: 10, Concurrency: 80 |
| **Cloud Run API** | FastAPI + RapidOCR | 2 vCPU, 2 GB RAM | CPU allocation: Request-based; Concurrency: 10–20 (due to OCR compute) |
| **Cloud SQL** | PostgreSQL 16 | `db-custom-2-7680` (2 vCPU, 7.5 GB RAM) | Storage: 50 GB SSD with automatic storage increase enabled |
| **Cloud Storage** | Private Document Bucket | Standard Storage (asia-south1) | Uniform bucket-level access enabled, public access prevented |
| **Cloud Run Job** | Retention Cleanup | 1 vCPU, 512 MB RAM | Runs hourly via Cloud Scheduler to prune records older than 48 hours |

---

## 3. Initial GCP Project Setup

Set up your shell environment and enable the required Google Cloud APIs:

```bash
# 1. Set environment variables
export PROJECT_ID="noticesaathi-prod"
export REGION="asia-south1"            # Mumbai region for Indian citizen data residency
export ARTIFACT_REPO="noticesaathi-repo"
export GCS_BUCKET_NAME="noticesaathi-documents-prod"
export CLOUD_SQL_INSTANCE="noticesaathi-db-prod"
export DB_NAME="notice_saathi"
export DB_USER="saathi_app"

# 2. Authenticate and set default project
gcloud auth login
gcloud config set project ${PROJECT_ID}
gcloud config set compute/region ${REGION}

# 3. Enable necessary Google Cloud APIs
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    storage.googleapis.com \
    vpcaccess.googleapis.com \
    compute.googleapis.com
```

---

## 4. Identity & Access Management (IAM)

Create dedicated, least-privileged service accounts for the backend API and retention cleanup jobs.

```bash
# 1. Create API Service Account
gcloud iam service-accounts create saathi-backend-sa \
    --display-name="NoticeSaathi Backend Cloud Run Service Account"

# 2. Assign Cloud SQL Client role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:saathi-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# 3. Assign Cloud Storage Object Admin on private documents bucket
gcloud storage buckets add-iam-policy-binding gs://${GCS_BUCKET_NAME} \
    --member="serviceAccount:saathi-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectUser"

# 4. Assign Secret Manager Secret Accessor
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:saathi-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# 5. Create Cloud Scheduler Invoker Service Account
gcloud iam service-accounts create saathi-scheduler-sa \
    --display-name="NoticeSaathi Cloud Scheduler Invoker"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:saathi-scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

---

## 5. Secret Manager Configuration

Store all sensitive secrets in Google Secret Manager to eliminate hardcoded credentials:

```bash
# Generate high-entropy secret key for session signing
SECRET_KEY_VAL=$(openssl rand -hex 32)
echo -n "${SECRET_KEY_VAL}" | gcloud secrets create saathi-secret-key --data-file=-

# Generate database password
DB_PASS_VAL=$(openssl rand -hex 24)
echo -n "${DB_PASS_VAL}" | gcloud secrets create saathi-db-password --data-file=-

# Store Gnani AI API Key
echo -n "YOUR_GNANI_API_KEY" | gcloud secrets create saathi-gnani-api-key --data-file=-
```

---

## 6. Cloud SQL for PostgreSQL Setup

Provision a managed PostgreSQL 16 instance with automated daily backups:

```bash
# 1. Create Cloud SQL Instance (PostgreSQL 16)
gcloud sql instances create ${CLOUD_SQL_INSTANCE} \
    --database-version=POSTGRES_16 \
    --tier=db-custom-2-7680 \
    --region=${REGION} \
    --availability-type=REGIONAL \
    --backup-start-time=02:00 \
    --enable-point-in-time-recovery \
    --storage-auto-increase \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=03

# 2. Create application database
gcloud sql databases create ${DB_NAME} --instance=${CLOUD_SQL_INSTANCE}

# 3. Create application user with generated password
gcloud sql users create ${DB_USER} \
    --instance=${CLOUD_SQL_INSTANCE} \
    --password="${DB_PASS_VAL}"
```

The database connection string for Cloud Run using the built-in Cloud SQL Auth Proxy is:
```
postgresql+psycopg2://saathi_app:${DB_PASS_VAL}@/notice_saathi?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

---

## 7. Cloud Storage Private Bucket Setup

Create a secure private bucket in the same region (`asia-south1`):

```bash
# 1. Create standard storage bucket
gcloud storage buckets create gs://${GCS_BUCKET_NAME} \
    --location=${REGION} \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access

# 2. Block all public access
gcloud storage buckets update gs://${GCS_BUCKET_NAME} \
    --public-access-prevention
```

---

## 8. Artifact Registry & Container Builds

Create a Docker repository in Artifact Registry and build the containers:

```bash
# 1. Create Docker repository
gcloud artifacts repositories create ${ARTIFACT_REPO} \
    --repository-format=docker \
    --location=${REGION} \
    --description="NoticeSaathi Container Repository"

# 2. Build and push Backend Image
gcloud builds submit \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/api:latest \
    -f infra/Dockerfile.api .

# 3. Build and push Frontend Image
# Note: Provide the production API URL during build time for Next.js client bundling
gcloud builds submit \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/web:latest \
    --substitutions=_NEXT_PUBLIC_API_URL="https://api.noticesaathi.org/api/v1" \
    -f infra/Dockerfile.web .
```

---

## 9. Deploying Cloud Run Services

### 9.1 Deploy Backend API Service

```bash
gcloud run deploy noticesaathi-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/api:latest \
    --region=${REGION} \
    --service-account=saathi-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --cpu=2 \
    --memory=2Gi \
    --concurrency=15 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=120s \
    --allow-unauthenticated \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${CLOUD_SQL_INSTANCE} \
    --set-env-vars="ENVIRONMENT=production,DEBUG=false,API_V1_STR=/api/v1,CORS_ALLOWED_ORIGINS=https://noticesaathi.org,https://www.noticesaathi.org,STORAGE_LOCAL_DIR=/mnt/storage,RETENTION_HOURS=48,DEFAULT_LANGUAGE=te-IN" \
    --set-secrets="SECRET_KEY=saathi-secret-key:latest,DATABASE_URL=saathi-database-url:latest,GNANI_API_KEY=saathi-gnani-api-key:latest"
```

### 9.2 Deploy Frontend Web Service

```bash
gcloud run deploy noticesaathi-web \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/web:latest \
    --region=${REGION} \
    --cpu=1 \
    --memory=512Mi \
    --concurrency=80 \
    --min-instances=1 \
    --max-instances=10 \
    --allow-unauthenticated \
    --set-env-vars="NODE_ENV=production,PORT=3000,NEXT_PUBLIC_API_URL=https://api.noticesaathi.org/api/v1,NEXT_PUBLIC_APP_URL=https://noticesaathi.org"
```

---

## 10. Automated Retention Worker (Cloud Run Job + Scheduler)

NoticeSaathi enforces a strict **48-Hour Data Retention Policy**. Documents and audio files older than 48 hours are permanently swept.

### 10.1 Create Cloud Run Job

```bash
gcloud run jobs create noticesaathi-retention-sweep \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/api:latest \
    --region=${REGION} \
    --service-account=saathi-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${CLOUD_SQL_INSTANCE} \
    --set-env-vars="ENVIRONMENT=production,RETENTION_HOURS=48,STORAGE_LOCAL_DIR=/mnt/storage" \
    --set-secrets="DATABASE_URL=saathi-database-url:latest" \
    --command="python" \
    --args="scripts/cleanup_expired_documents.py"
```

### 10.2 Schedule Hourly Job Execution

```bash
gcloud scheduler jobs create http noticesaathi-hourly-cleanup \
    --location=${REGION} \
    --schedule="0 * * * *" \
    --time-zone="Asia/Kolkata" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/noticesaathi-retention-sweep:run" \
    --http-method=POST \
    --oauth-service-account-email="saathi-scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

---

## 11. Custom Domains & SSL Certificates

Map custom domains to Cloud Run services:

```bash
# Map frontend domain
gcloud beta run domain-mappings create \
    --service=noticesaathi-web \
    --domain=noticesaathi.org \
    --region=${REGION}

# Map backend API domain
gcloud beta run domain-mappings create \
    --service=noticesaathi-api \
    --domain=api.noticesaathi.org \
    --region=${REGION}
```

Cloud Run automatically provisions and renews managed SSL certificates upon DNS verification of the generated CNAME records.

---

## 12. Monitoring, Observability & Health Checks

1. **Health Probes**:
   - Backend endpoint: `GET https://api.noticesaathi.org/api/v1/health`
   - Frontend endpoint: `GET https://noticesaathi.org/`
2. **Alert Policies in Cloud Monitoring**:
   - **HTTP 5xx Alert**: Trigger when 5xx errors exceed 1% over 5 minutes.
   - **Container Restart Alert**: Alert on container memory limit exceedance (OOM).
   - **Cloud SQL Utilization**: Alert when storage or CPU utilization exceeds 80%.

---

## 13. Rollback & Disaster Recovery Procedures

### Instant Service Rollback

If a bad release occurs, instantly rollback to the previous healthy revision:

```bash
# List previous revisions
gcloud run revisions list --service=noticesaathi-api --region=${REGION}

# Instantly route 100% traffic to previous stable revision
gcloud run services update-traffic noticesaathi-api \
    --to-revisions=noticesaathi-api-00012-abc=100 \
    --region=${REGION}
```

### Database Point-In-Time Recovery (PITR)

Cloud SQL point-in-time recovery allows restoring the database to any second within the retention window (7 days by default):

```bash
gcloud sql instances clone ${CLOUD_SQL_INSTANCE} ${CLOUD_SQL_INSTANCE}-restored \
    --point-in-time="2026-11-09T10:00:00.000000Z"
```

