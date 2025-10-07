#!/bin/bash

# Google Cloud Run Deployment Script for PSU Menu Analyzer

echo "🚀 Deploying PSU Menu Analyzer to Google Cloud Run..."

# Set your project ID (replace with your actual project ID)
PROJECT_ID="seventh-botany-471215-v7"
SERVICE_NAME="psu-menu-analyzer"
REGION="us-central1"

# Build and push the container
echo "📦 Building and pushing container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY

echo "✅ Deployment complete!"
echo "🌐 Your app should be available at:"
gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)'
