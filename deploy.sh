#!/usr/bin/env bash
# Build on Cloud Build and deploy to Cloud Run. The Mistral key lives in Secret Manager; Gemini is
# reached through Vertex AI with the service's own identity (role aiplatform.user), billed to the project.
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
  --set-env-vars "MISTRAL_MODEL=ministral-14b-latest,VERTEX_PROJECT=$PROJECT,ESCALATION_MODEL=gemini-3.8-flash,DECISION_MODE=strong,RATE_GLOBAL_DAY=300" \
  --set-secrets MISTRAL_API_KEY=mistral-api-key:latest
