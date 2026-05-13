#!/usr/bin/env bash
# Deploy the ECR secret auto-refresher CronJob to the openclaw namespace.
# Run this once; the CronJob handles ongoing refreshes every 6 hours.
#
# Prerequisites:
#   - kubectl configured against the target cluster
#   - AWS profile 'ecr-dev' (or override with AWS_PROFILE) with permission
#     to assume arn:aws:iam::730335486558:role/ecr-dev-k8s-role
#
# Optional env overrides:
#   KUBECONFIG    path to kubeconfig file
#   KUBE_CONTEXT  kubectl context name
#   AWS_PROFILE   AWS profile to source base credentials from (default: ecr-dev)
set -euo pipefail

NAMESPACE="openclaw"
SECRET_NAME="aws-ecr-refresher-creds"
AWS_PROFILE="${AWS_PROFILE:-ecr-dev}"
MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Build kubectl flags if caller passed explicit kubeconfig/context
KUBECTL_FLAGS=()
[[ -n "${KUBECONFIG:-}" ]] && KUBECTL_FLAGS+=(--kubeconfig "$KUBECONFIG")
[[ -n "${KUBE_CONTEXT:-}" ]] && KUBECTL_FLAGS+=(--context "$KUBE_CONTEXT")
kubectl() { command kubectl "${KUBECTL_FLAGS[@]}" "$@"; }

# --------------------------------------------------------------------------
# 1. Read base (non-role) credentials from the source profile of ecr-dev
# --------------------------------------------------------------------------
SOURCE_PROFILE=$(aws configure get source_profile --profile "$AWS_PROFILE" 2>/dev/null || echo "default")
KEY_ID=$(aws configure get aws_access_key_id --profile "$SOURCE_PROFILE")
SECRET_KEY=$(aws configure get aws_secret_access_key --profile "$SOURCE_PROFILE")

if [[ -z "$KEY_ID" || -z "$SECRET_KEY" ]]; then
  echo "ERROR: Could not read credentials from AWS profile '$SOURCE_PROFILE'"
  exit 1
fi

echo "Using source profile: $SOURCE_PROFILE (key: ${KEY_ID:0:8}...)"

# --------------------------------------------------------------------------
# 2. Store credentials as a k8s Secret
# --------------------------------------------------------------------------
echo "Creating/updating k8s secret '$SECRET_NAME' in namespace '$NAMESPACE'..."
kubectl create secret generic "$SECRET_NAME" \
  --from-literal=aws_access_key_id="$KEY_ID" \
  --from-literal=aws_secret_access_key="$SECRET_KEY" \
  -n "$NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f -

# --------------------------------------------------------------------------
# 3. Apply RBAC + CronJob manifest
# --------------------------------------------------------------------------
echo "Applying ECR refresher manifests..."
kubectl apply -f "$MANIFEST_DIR/ecr-refresh-cronjob.yaml"

# --------------------------------------------------------------------------
# 4. Trigger an immediate run to verify everything works
# --------------------------------------------------------------------------
echo "Triggering immediate test run..."
JOB_NAME="ecr-refresh-manual-$(date +%s)"
kubectl create job "$JOB_NAME" \
  --from=cronjob/ecr-secret-refresher \
  -n "$NAMESPACE"

echo ""
echo "Watching job logs (Ctrl+C to stop watching; job continues running):"
sleep 3
kubectl logs -n "$NAMESPACE" -l "job-name=$JOB_NAME" --follow --ignore-errors || true

echo ""
echo "Done. CronJob 'ecr-secret-refresher' will refresh ECR credentials every 6 hours."
echo "Check status: kubectl get cronjob ecr-secret-refresher -n $NAMESPACE"
