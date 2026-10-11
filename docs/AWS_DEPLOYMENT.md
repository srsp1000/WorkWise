# WorkWise — AWS Serverless Architecture & Production Deployment Guide

**Target Environment:** AWS Serverless (AWS Lambda, API Gateway HTTP API v2, Amazon Bedrock, Amazon Polly, Amazon S3, AWS Amplify Hosting)  
**Primary Region:** `ap-south-1` (Mumbai, India)  
**IaC Tooling:** AWS Serverless Application Model (SAM) / CloudFormation  
**Status:** Hardened for production, zero-form Bedrock default, tested with Mangum ASGI runner.

---

## 1. Cloud Architecture Overview

```
                          ┌───────────────────────────┐
                          │    Mobile Supervisor      │
                          │ (React PWA / AWS Amplify) │
                          └─────────────┬─────────────┘
                                        │ HTTPS
                                        ▼
                          ┌───────────────────────────┐
                          │  API Gateway HTTP API v2  │
                          │ (Rate-Limited, CORS: *)   │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │    AWS Lambda Function    │
                          │    (Python 3.12 Mangum)   │
                          └──────┬─────────────┬──────┘
                                 │             │
        ┌────────────────────────┼─────────────┼────────────────────────┐
        │                        │             │                        │
        ▼                        ▼             ▼                        ▼
┌──────────────┐         ┌──────────────┐┌──────────────┐        ┌──────────────┐
│  Open-Meteo  │         │Amazon Bedrock││ Amazon Polly │        │  Amazon S3   │
│ Weather API  │         │ Nova / Claude││ Neural Speech│        │Audio Briefs &│
│ (Forecasts)  │         │ Converse API ││ (Kajal Voice)│        │ Print Reports│
└──────────────┘         └──────────────┘└──────────────┘        └──────────────┘
```

### Components & Roles:
1. **Frontend Hosting (AWS Amplify Hosting — "Deploy without Git"):**
   - Hosts the mobile-first Progressive Web App (`dist/` static bundle) with HTTPS.
   - Direct client-to-API Gateway calls (no CloudFront reverse proxy needed; CORS `*` is pre-configured).
2. **API Ingress (AWS API Gateway HTTP API v2):**
   - Routes to AWS Lambda via `$default` stage (no `/prod` subpath prefix to prevent routing mismatches).
   - Ingress protection via `DefaultRouteSettings`: `ThrottlingRateLimit: 20` req/sec, `ThrottlingBurstLimit: 50`.
3. **Compute (AWS Lambda with Mangum ASGI):**
   - Handler: `workwise_engine.lambda_handler.handler`.
   - Memory: 512 MB | Timeout: 30 seconds | Runtime: Python 3.12.
   - Built-in warmup ping handler prevents cold starts.
   - Reserves no protected environment variable names (reads `AWS_REGION` natively from runtime).
4. **Thermal Modeling & Weather (Open-Meteo):**
   - Hourly meteorological data with 15s timeout and exponential retry.
5. **AI Explanations (Amazon Bedrock Converse API):**
   - **Default Model:** `apac.amazon.nova-lite-v1:0` (Amazon Nova Lite APAC cross-region inference profile). Zero use-case forms required; immediately active in commercial accounts.
   - **Alternative Models:** `apac.anthropic.claude-haiku-4-5-20251001-v1:0` or Claude 3.5 Haiku (requires one-time Anthropic use-case form submission in console).
   - Guarded by deterministic safety regex and prohibited medical phrase filtering.
6. **Voice Briefings (Amazon Polly Neural Engine):**
   - Voice: `Kajal` (bilingual Indian English & Hindi neural voice).
   - Automatic fallback to browser Web Speech API if offline or AWS credentials unavailable.
7. **Storage (Amazon S3):**
   - S3 bucket (`workwise-briefs-${AWS::AccountId}-${AWS::Region}`) stores generated audio files with 7-day lifecycle purge rule.

---

## 2. Infrastructure as Code (`template.yaml` & `.samignore`)

Key properties in `template.yaml`:
- **No reserved `AWS_REGION` variable:** Clean Lambda environment that passes `cfn-lint`.
- **Default Stage `$default`:** Direct path mapping without `/prod/` prefix.
- **Throttling configured:** 20 req/s sustained, 50 burst to prevent runaway costs on unauthenticated demo endpoints.
- **`.samignore` included:** Excludes `frontend/`, `docs/`, `tests/`, and `.git` from the Lambda zip package, avoiding 250MB size limit blowups.

---

## 3. Step-by-Step Deployment Guide

### Why Use AWS CloudShell (Recommended)?
Building on Windows without Docker can fail due to symlinks, file permissions, or pulling `frontend/node_modules` into the Lambda zip. **AWS CloudShell** has:
- Pre-installed SAM CLI, Docker, and Git.
- Native Linux container build environment (`sam build --use-container`).
- Pre-authenticated AWS session (no need to create or store long-lived IAM access keys on local machines).

---

### Step 3.1: Deploy Backend via AWS CloudShell

1. Open the [AWS Management Console](https://console.aws.amazon.com/) in region **`ap-south-1` (Mumbai)**.
2. Click the **CloudShell** icon (>_) in the top navigation bar.
3. In CloudShell, run:

```bash
# Clone the repository
git clone https://github.com/srsp1000/WorkWise.git
cd WorkWise

# Ensure Python 3.12 is installed in CloudShell (Amazon Linux 2023)
sudo dnf install -y python3.12 python3.12-pip

# Build serverless artifacts natively (fast, no Docker container issues)
sam build

# Deploy with guided setup
sam deploy --guided \
  --stack-name workwise \
  --region ap-south-1 \
  --capabilities CAPABILITY_IAM
```

**Prompts during `sam deploy --guided`:**
- Stack Name: `workwise`
- AWS Region: `ap-south-1`
- Parameter BedrockModelId: `apac.amazon.nova-lite-v1:0` (press Enter for default)
- Confirm changes before deploy: `N`
- Allow SAM CLI to create IAM roles: `Y`
- Disable rollback: `N`
- WorkWiseFunction may not have authorization defined, Is this okay?: `Y` (public demo endpoints)
- Save arguments to configuration file: `Y`

4. Copy the **`WorkWiseApiEndpoint`** output from the terminal (e.g., `https://abcdef123.execute-api.ap-south-1.amazonaws.com`).

---

### Step 3.2: Verify Live Backend Endpoints (Smoke Tests)

Before building the frontend, test the live API endpoints directly using `curl`:

```bash
API_URL="https://<your-api-id>.execute-api.ap-south-1.amazonaws.com"

# 1. Health check
curl -s "${API_URL}/api/health"
# Expected: {"status":"healthy","service":"workwise-engine",...}

# 2. Tasks catalog
curl -s "${API_URL}/api/tasks" | head -c 200

# 3. Deterministic Safety Plan
curl -s -X POST "${API_URL}/api/plan" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-10-12","city":"Delhi","tasks":["concrete_slab_pour","rebar_installation"]}' | head -c 200

# 4. Amazon Bedrock AI reasoning
curl -s -X POST "${API_URL}/api/ai/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Why is concrete unschedulable during peak heat?","plan":{"status":"ACTIVE","matrix":[],"shifts":[],"summary":{"total_tasks":1,"scheduled_count":0,"unschedulable_count":1,"high_heat_count":0,"extreme_heat_count":0}}}'
# Expected: Returns grounded explanation citing OSHA / NIOSH continuous work screening criteria.

# 5. Amazon Polly Audio Synthesis (Kajal Neural Voice)
curl -s -X POST "${API_URL}/api/audio/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"Namaste supervisor. Today heat risk is moderate. Drink water every 20 minutes.","language":"hi"}'
# Expected: Returns {"audio_base64":"...","format":"mp3","voice":"Kajal"}
```

---

### Step 3.3: Build & Deploy Frontend to AWS Amplify (Manual Drag-and-Drop)

This is the fastest, zero-friction hosting method for production demo:

1. **Build Frontend on your local machine:**
   ```powershell
   cd frontend

   # Set VITE_API_BASE to your deployed API Gateway URL
   # Note: WorkWise api.ts automatically normalizes both with or without /api
   $env:VITE_API_BASE="https://<your-api-id>.execute-api.ap-south-1.amazonaws.com/api"

   npm run build
   ```
   *(On macOS/Linux bash: `VITE_API_BASE="https://<api-id>.execute-api.ap-south-1.amazonaws.com/api" npm run build`)*

2. **Deploy to AWS Amplify Hosting:**
   - Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/).
   - Click **Deploy an app** -> Select **Deploy without Git**.
   - App Name: `WorkWise`
   - Environment Name: `production`
   - Drag and drop the `frontend/dist` directory (or zip `dist` and upload `dist.zip`).
   - Click **Save and deploy**.
   - Amplify gives you an instant HTTPS URL (e.g. `https://production.d1234abcd.amplifyapp.com`).
   - Test the app in mobile view on your browser or phone!

---

## 4. Bedrock Model Access & Permissions Matrix

| Model | Profile ID | Access Requirements in `ap-south-1` | Recommended Use |
| :--- | :--- | :--- | :--- |
| **Amazon Nova Lite (Default)** | `apac.amazon.nova-lite-v1:0` | **Zero-form, instant access** on first invocation | **Recommended default for demos & zero latency setup** |
| **Amazon Nova Micro** | `apac.amazon.nova-micro-v1:0` | Zero-form, instant access | Fastest token generation |
| **Claude Haiku 4.5** | `apac.anthropic.claude-haiku-4-5-20251001-v1:0` | Requires submitting Anthropic use-case form | Once Anthropic approval clears |
| **Claude 3.5 Haiku (Legacy)** | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | US inference profile only, EOL June 19, 2026 | Avoid for Mumbai stack |

> [!TIP]
> To switch models at deploy time without editing code:
> ```bash
> sam deploy --parameter-overrides BedrockModelId=apac.amazon.nova-lite-v1:0
> ```

---

## 5. Cost Safeguards & Throttling

To prevent unexpected billing on public demo endpoints:
1. **API Gateway Throttling:** `template.yaml` enforces:
   - `ThrottlingRateLimit: 20` requests per second.
   - `ThrottlingBurstLimit: 50` burst requests.
2. **AWS Budget Alert:**
   - In AWS Console -> **AWS Billing & Cost Management** -> **Budgets**.
   - Create a Zero-Spend or $5.00/month Budget with email alerts.
3. **S3 Lifecycle:**
   - Audio files expire and are automatically deleted after 7 days.

---

## 6. Video Demonstration Evidence Checklist

When recording the project demonstration video, include the following AWS screens to prove live cloud infrastructure:
- [ ] **AWS Lambda Console (`ap-south-1`):** Show `workwise-WorkWiseFunction-*` function code, Python 3.12 runtime, and environment variables.
- [ ] **API Gateway Console:** Show HTTP API routes (`$default` catch-all) and CORS settings.
- [ ] **Amazon Bedrock Console:** Show inference profile usage and model activity.
- [ ] **CloudWatch Logs:** Live log streams proving actual Lambda executions, execution times (~300ms), and absence of errors.
- [ ] **Amplify PWA Live on Mobile:** Tap "Play Morning Audio Brief" to hear Polly's Kajal neural voice, and ask the Supervisor Copilot a question to see real-time Bedrock reasoning.
