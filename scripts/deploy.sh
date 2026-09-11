#!/bin/bash

SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id benchamrk/prod \
    --query SecretString \
    --output text)

export KEYCLOAK_ADMIN_PASSWORD=$(echo "$SECRET_JSON" | jq -r ".KEYCLOAK_ADMIN_PASSWORD")

export POSTGRES_PASSWORD=$(echo "$SECRET_JSON" | jq -r ".POSTGRES_PASSWORD")

export DATABASE_URL="postgresql+asyncpg://orchestrator:${POSTGRES_PASSWORD}@postgres:5432/orchestrator"
export DATABASE_URL_SYNC="postgresql+psycopg://orchestrator:${POSTGRES_PASSWORD}@postgres:5432/orchestrator"


docker compose up \
    -f docker-compose.prod.yml \
    --env-file .env \
    up -d