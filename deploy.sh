#!/usr/bin/env bash
# Build on Cloud Build and deploy to Cloud Run. The Mistral key lives in Secret Manager.
set -euo pipefail
PROJECT="${1:-sinistres-cg-jose99}"
REGION=europe-west1

gcloud run deploy sinistres-cg \
  --project "$PROJECT" --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --memory 1Gi --cpu 1 --concurrency 20 \
  --min-instances 0 --max-instances 2 \
  --timeout 120 \
  --set-env-vars MISTRAL_MODEL=ministral-14b-latest \
  --set-secrets MISTRAL_API_KEY=mistral-api-key:latest
