# Google Cloud Run Deployment Guide

## Current Issue
Your deployment is failing because the container can't start properly on Google Cloud Run. The error indicates the container failed to listen on port 8080 within the timeout.

## What I Fixed

### 1. **Dockerfile Updates**
- Added `gunicorn` to requirements.txt
- Increased timeout to 120 seconds
- Added proper worker configuration
- Created cache directory in the container

### 2. **Cache Directory Fix**
- Changed from `/tmp/cache` (Vercel) to `./cache` (Google Cloud Run)
- Added cache directory creation in Dockerfile

### 3. **Gunicorn Configuration**
- Added proper timeout settings
- Configured workers and threads for Cloud Run
- Set proper binding to 0.0.0.0:$PORT

## Deployment Steps

### Option 1: Using the Deployment Script
```bash
# Set your environment variable
export GEMINI_API_KEY="your_gemini_api_key_here"

# Run the deployment script
./deploy_gcp.sh
```

### Option 2: Manual Deployment
```bash
# Set your project ID
export PROJECT_ID="seventh-botany-471215-v7"

# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/psu-menu-analyzer

# Deploy to Cloud Run
gcloud run deploy psu-menu-analyzer \
  --image gcr.io/$PROJECT_ID/psu-menu-analyzer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY
```

### Option 3: Using Cloud Build (Recommended)
```bash
# Trigger build using cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml
```

## Environment Variables

Set these in Google Cloud Run:
1. Go to Cloud Run → Your Service → Edit & Deploy New Revision
2. Go to "Variables & Secrets" tab
3. Add: `GEMINI_API_KEY` with your Google Gemini API key

## Expected Results

After successful deployment:
- ✅ Container starts properly on port 8080
- ✅ All API endpoints work correctly
- ✅ Caching system functions properly
- ✅ AI analysis works with your API key

## Troubleshooting

### If deployment still fails:
1. **Check logs**: Go to Cloud Run → Your Service → Logs
2. **Verify environment variables**: Ensure GEMINI_API_KEY is set
3. **Check memory limits**: Increase if needed (current: 1Gi)
4. **Verify timeout**: Current timeout is 300 seconds

### Common Issues:
- **Port binding**: Make sure the app binds to 0.0.0.0:$PORT
- **Memory**: Increase memory if analysis fails
- **Timeout**: Increase timeout for long-running requests
- **Environment variables**: Ensure all required env vars are set

## Testing After Deployment

Once deployed, test with:
```bash
# Get your service URL
gcloud run services describe psu-menu-analyzer --platform managed --region us-central1 --format 'value(status.url)'

# Test the endpoints
curl https://your-service-url/health
curl -X POST https://your-service-url/api/analyze -H "Content-Type: application/json" -d '{"campus":"altoona-port-sky"}'
```

## Cost Optimization

- **CPU**: Set to 1 (current setting)
- **Memory**: 1Gi should be sufficient
- **Max Instances**: 10 (adjust based on traffic)
- **Min Instances**: 0 (to save costs when not in use)

Your PSU Menu Analyzer should now deploy successfully to Google Cloud Run! 🚀
