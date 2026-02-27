# Vertex AI Setup Guide

This guide walks you through setting up Google Cloud Vertex AI for Pikar AI, which provides **significantly higher rate limits** compared to the free Gemini API tier.

## Rate Limit Comparison

| Tier | Limit | Reset |
|------|-------|-------|
| **Gemini API (Free)** | 20 requests/day | Daily |
| **Vertex AI** | ~1,500 requests/minute | Per minute |

## Prerequisites

- Google Cloud Platform (GCP) account
- Billing enabled on your GCP project
- `gcloud` CLI installed (optional but recommended)

## Step-by-Step Setup

### Step 1: Create or Select a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing: `my-project-pk-484623`
3. Note your **Project ID** (not the project name)

### Step 2: Enable Billing

1. Go to **Billing** in the Cloud Console
2. Link a billing account to your project
3. Vertex AI has a generous free tier, but billing must be enabled

### Step 3: Enable Required APIs

Run these commands or enable via Cloud Console:

```bash
# Using gcloud CLI
gcloud services enable aiplatform.googleapis.com --project=my-project-pk-484623
gcloud services enable generativelanguage.googleapis.com --project=my-project-pk-484623
```

Or via Console:
1. Go to **APIs & Services** > **Enable APIs and Services**
2. Search for and enable:
   - "Vertex AI API"
   - "Generative Language API"

### Step 4: Create a Service Account

```bash
# Create service account
gcloud iam service-accounts create pikar-ai-vertex \
    --display-name="Pikar AI Vertex" \
    --project=my-project-pk-484623

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding my-project-pk-484623 \
    --member="serviceAccount:pikar-ai-vertex@my-project-pk-484623.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Download the key file
gcloud iam service-accounts keys create ./secrets/vertex-ai-service-account.json \
    --iam-account=pikar-ai-vertex@my-project-pk-484623.iam.gserviceaccount.com
```

Or via Console:
1. Go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Name: `pikar-ai-vertex`
4. Grant role: **Vertex AI User** (`roles/aiplatform.user`)
5. Click **Create Key** > **JSON**
6. Save the downloaded file to `secrets/vertex-ai-service-account.json`

### Step 5: Configure Environment Variables

Update your `app/.env` file:

```env
# Vertex AI Configuration
GOOGLE_CLOUD_PROJECT=my-project-pk-484623
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./secrets/vertex-ai-service-account.json

# Comment out or remove the API key (not needed with Vertex AI)
# GOOGLE_API_KEY=your-api-key
```

### Step 6: Verify Setup

Restart your backend server and check the logs:

```bash
cd app
python -m uvicorn fast_api_app:app --reload
```

You should see:
```
INFO: Vertex AI mode enabled. Project: my-project-pk-484623
INFO: Rate limits: ~1,500 requests/minute (varies by model)
```

If you see the API Key mode warning instead, check:
- The service account key file exists at the specified path
- The `GOOGLE_API_KEY` is commented out in your `.env`

## Supported Regions

Vertex AI is available in these regions. Choose the one closest to your users:

| Region | Location |
|--------|----------|
| `us-central1` | Iowa, USA (recommended) |
| `us-east1` | South Carolina, USA |
| `us-west1` | Oregon, USA |
| `europe-west1` | Belgium |
| `europe-west4` | Netherlands |
| `asia-northeast1` | Tokyo, Japan |
| `asia-southeast1` | Singapore |

## Troubleshooting

### Error: "Permission denied" or "403 Forbidden"

The service account lacks permissions. Run:

```bash
gcloud projects add-iam-policy-binding my-project-pk-484623 \
    --member="serviceAccount:pikar-ai-vertex@my-project-pk-484623.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### Error: "API not enabled"

Enable the Vertex AI API:

```bash
gcloud services enable aiplatform.googleapis.com --project=my-project-pk-484623
```

### Error: "Invalid credentials"

1. Verify the key file path is correct
2. Ensure the file is valid JSON
3. Check file permissions (should be readable by the app)

### Still getting rate limited?

Vertex AI quotas are project-wide. Check your quota usage:
1. Go to **IAM & Admin** > **Quotas**
2. Filter for "Vertex AI" or "Generative AI"
3. Request quota increase if needed

## Cost Considerations

Vertex AI pricing (as of 2025):

| Model | Input | Output |
|-------|-------|--------|
| Gemini 2.5 Flash | $0.075/1M tokens | $0.30/1M tokens |
| Gemini 2.5 Pro | $1.25/1M tokens | $5.00/1M tokens |

For typical usage:
- ~1,000 chat messages/day ≈ $1-5/month
- High-volume production ≈ $20-100/month

Monitor costs in **Billing** > **Cost Table**.

## Security Best Practices

1. **Never commit credentials**: The `secrets/` folder is gitignored
2. **Rotate keys regularly**: Create new keys every 90 days
3. **Use least privilege**: Only grant `aiplatform.user` role
4. **Enable audit logging**: Track API usage in Cloud Logging
