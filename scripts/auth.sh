#!/usr/bin/env bash
#
# auth.sh — Get a valid Cognito ID token for the GTM Accelerator API
#
# The API Gateway Cognito authorizer validates the ID token (not access token).
# This script handles user creation, confirmation, and token retrieval.
#
# Usage:
#   # First time — create user + get token:
#   ./scripts/auth.sh setup
#
#   # Subsequent — just get a fresh token:
#   ./scripts/auth.sh token
#
#   # Export as env var for curl:
#   export TOKEN=$(./scripts/auth.sh token)
#
# Prerequisites:
#   - AWS CLI configured
#   - jq installed (brew install jq / apt install jq)
#   - Stack deployed (sam deploy)

set -euo pipefail

STACK_NAME="${STACK_NAME:-gtm-accelerator-sprint}"
REGION="${AWS_REGION:-us-east-1}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@gtm-accelerator.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-SprintDemo2026!@}"

# ─── Fetch stack outputs ───────────────────────────────────────────────
get_output() {
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
        --output text
}

USER_POOL_ID=$(get_output "UserPoolId")
CLIENT_ID=$(get_output "UserPoolClientId")
API_URL=$(get_output "ApiEndpoint")

if [ -z "$USER_POOL_ID" ] || [ -z "$CLIENT_ID" ]; then
    echo "ERROR: Could not fetch stack outputs. Is '$STACK_NAME' deployed?" >&2
    exit 1
fi

# ─── Commands ──────────────────────────────────────────────────────────
cmd_setup() {
    echo "=== GTM Accelerator Sprint — Auth Setup ===" >&2
    echo "Stack:     $STACK_NAME" >&2
    echo "Pool:      $USER_POOL_ID" >&2
    echo "Client:    $CLIENT_ID" >&2
    echo "API:       $API_URL" >&2
    echo "" >&2

    # 1. Create user
    echo "[1/3] Creating admin user: $ADMIN_EMAIL" >&2
    aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$ADMIN_EMAIL" \
        --user-attributes Name=email,Value="$ADMIN_EMAIL" Name=email_verified,Value=true \
        --message-action SUPPRESS \
        --region "$REGION" 2>/dev/null || echo "  (user may already exist, continuing)" >&2

    # 2. Set permanent password (skip FORCE_CHANGE_PASSWORD state)
    echo "[2/3] Setting password..." >&2
    aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$ADMIN_EMAIL" \
        --password "$ADMIN_PASSWORD" \
        --permanent \
        --region "$REGION"

    # 3. Get token
    echo "[3/3] Authenticating..." >&2
    cmd_token
}

cmd_token() {
    # Initiate auth and extract the IdToken
    RESULT=$(aws cognito-idp initiate-auth \
        --auth-flow USER_PASSWORD_AUTH \
        --client-id "$CLIENT_ID" \
        --auth-parameters USERNAME="$ADMIN_EMAIL",PASSWORD="$ADMIN_PASSWORD" \
        --region "$REGION" \
        --output json 2>/dev/null)

    # Check for NEW_PASSWORD_REQUIRED challenge
    CHALLENGE=$(echo "$RESULT" | jq -r '.ChallengeName // empty')
    if [ "$CHALLENGE" = "NEW_PASSWORD_REQUIRED" ]; then
        echo "User requires password change. Running setup instead..." >&2
        SESSION=$(echo "$RESULT" | jq -r '.Session')
        RESULT=$(aws cognito-idp admin-respond-to-auth-challenge \
            --user-pool-id "$USER_POOL_ID" \
            --client-id "$CLIENT_ID" \
            --challenge-name NEW_PASSWORD_REQUIRED \
            --challenge-responses USERNAME="$ADMIN_EMAIL",NEW_PASSWORD="$ADMIN_PASSWORD" \
            --session "$SESSION" \
            --region "$REGION" \
            --output json)
    fi

    ID_TOKEN=$(echo "$RESULT" | jq -r '.AuthenticationResult.IdToken // empty')

    if [ -z "$ID_TOKEN" ]; then
        echo "ERROR: Failed to get token. Response:" >&2
        echo "$RESULT" | jq . >&2
        exit 1
    fi

    # Print just the token (stdout) so it can be captured via $()
    echo "$ID_TOKEN"

    # Helpful info to stderr (won't pollute variable capture)
    echo "" >&2
    echo "=== Token retrieved successfully ===" >&2
    echo "API URL: $API_URL" >&2
    echo "" >&2
    echo "Quick test (demo endpoint — no auth needed):" >&2
    echo "  curl -X POST $API_URL/demo/run" >&2
    echo "" >&2
    echo "Authenticated test:" >&2
    echo "  export TOKEN=\$(./scripts/auth.sh token)" >&2
    echo "  curl -X POST $API_URL/engagements \\" >&2
    echo "    -H \"Authorization: \$TOKEN\" \\" >&2
    echo "    -H \"Content-Type: application/json\" \\" >&2
    echo "    -d '{\"company_name\":\"Test\",\"contact_email\":\"t@t.co\"}'" >&2
}

cmd_info() {
    echo "Stack:     $STACK_NAME"
    echo "Region:    $REGION"
    echo "Pool ID:   $USER_POOL_ID"
    echo "Client ID: $CLIENT_ID"
    echo "API URL:   $API_URL"
    echo "Email:     $ADMIN_EMAIL"
}

# ─── Main ──────────────────────────────────────────────────────────────
case "${1:-help}" in
    setup)  cmd_setup ;;
    token)  cmd_token ;;
    info)   cmd_info ;;
    *)
        echo "Usage: $0 {setup|token|info}"
        echo ""
        echo "  setup  — Create admin user + get token (first time)"
        echo "  token  — Get a fresh ID token (subsequent calls)"
        echo "  info   — Show stack config"
        echo ""
        echo "Environment variables:"
        echo "  STACK_NAME      (default: gtm-accelerator-sprint)"
        echo "  AWS_REGION      (default: us-east-1)"
        echo "  ADMIN_EMAIL     (default: admin@gtm-accelerator.local)"
        echo "  ADMIN_PASSWORD  (default: SprintDemo2026!@)"
        ;;
esac
