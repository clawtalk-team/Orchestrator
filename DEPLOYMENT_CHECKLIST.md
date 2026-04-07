# Deployment Checklist for Container Provisioning Enhancement

## Pre-Deployment Requirements

### 1. Auth-Gateway Service
- [ ] Auth-gateway service is deployed and running
- [ ] Auth-gateway implements `GET /auth` endpoint
- [ ] Endpoint accepts `Authorization: Bearer {api_key}` header
- [ ] Endpoint returns `{"user_id": "user-123"}` on success
- [ ] Endpoint returns 401 status code for invalid keys

### 2. Environment Configuration
- [ ] `AUTH_GATEWAY_URL` environment variable set (e.g., `http://auth-gateway:8001`)
- [ ] DynamoDB table exists (`DYNAMODB_TABLE` setting)
- [ ] AWS credentials configured (for production)
- [ ] Network connectivity between orchestrator and auth-gateway verified

### 3. Python Dependencies
- [ ] Install/update dependencies: `pip install -r requirements.txt`
- [ ] Verify httpx is installed: `pip show httpx`

## Deployment Steps

### 1. Deploy Orchestrator Updates
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations (if any)
# (Not needed for this change - DynamoDB schema unchanged)

# Restart orchestrator service
systemctl restart orchestrator  # or your deployment method
```

### 2. Update Container Image (if needed)
```bash
# If using custom container images, rebuild with updated fetch_config.py
docker build -t openclaw-agent:latest .
docker push openclaw-agent:latest

# Update ECS task definition to use new image
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### 3. Test in Staging Environment
```bash
# Create a test container
curl -X POST http://staging-orchestrator:8000/containers \
  -H 'Authorization: Bearer sk-clawtalk-staging-test-key' \
  -H 'Content-Type: application/json' \
  -d '{"config_name": "default"}'

# Verify response contains container_id
# Check container logs for successful config fetch
# Verify container connects to auth-gateway
```

### 4. Verify DynamoDB Config Storage
```bash
# Check config was stored correctly
aws dynamodb get-item \
  --table-name openclaw-containers \
  --key '{"pk":{"S":"USER#<user-id>"},"sk":{"S":"CONFIG#default"}}'

# Verify auth_gateway_api_key is present
```

### 5. Monitor Container Boot
```bash
# Get container ID from create response
CONTAINER_ID="<container-id>"

# Watch logs for config fetch
docker logs -f $CONTAINER_ID

# Expected output:
# === Fetching config for user_id=..., config_name=default ===
# [1/4] Fetching user config from DynamoDB...
# [2/4] Fetching system config from DynamoDB...
# [3/4] Building OpenClaw config...
# ✓ Config written to /root/.openclaw/openclaw.json
# [4/4] Building openclaw-agent config...
# ✓ Config written to /root/.clawtalk/clawtalk.json
# === Config fetch completed successfully ===
```

## Post-Deployment Verification

### 1. Functional Tests
- [ ] Container creation succeeds with valid API key
- [ ] Container creation fails with invalid API key (401)
- [ ] Auth-gateway is called for each request (check auth-gateway logs)
- [ ] User config is created/updated in DynamoDB
- [ ] Container boots successfully and fetches config
- [ ] openclaw-agent authenticates with auth-gateway
- [ ] Agents can be created and function correctly

### 2. Error Handling Tests
- [ ] Auth-gateway timeout handled gracefully (503 error)
- [ ] Auth-gateway connection error handled (503 error)
- [ ] Invalid auth-gateway response handled (500 error)
- [ ] Master API key still works for admin operations

### 3. Performance Tests
- [ ] Auth-gateway response time acceptable (<200ms)
- [ ] Container creation time unchanged
- [ ] No memory leaks in httpx connections
- [ ] Auth-gateway can handle concurrent requests

### 4. Security Tests
- [ ] API keys stored correctly in DynamoDB
- [ ] No API keys logged in application logs
- [ ] Master API key bypass only works with exact match
- [ ] Public endpoints still accessible without auth

## Rollback Plan

If issues are discovered after deployment:

### 1. Immediate Rollback (Previous Version)
```bash
# Revert to previous orchestrator version
git revert HEAD
pip install -r requirements.txt
systemctl restart orchestrator
```

### 2. Quick Fix (Auth-Gateway Bypass)
If auth-gateway is down, temporarily bypass by:
- Restore old middleware: `git show HEAD~1:app/middleware/auth.py > app/middleware/auth.py`
- Restart service
- Fix auth-gateway issue
- Redeploy enhancement

### 3. Data Cleanup (If Needed)
```bash
# Remove test configs created during deployment
aws dynamodb delete-item \
  --table-name openclaw-containers \
  --key '{"pk":{"S":"USER#<user-id>"},"sk":{"S":"CONFIG#default"}}'
```

## Monitoring & Alerts

### Key Metrics to Watch
1. **Auth-gateway response time** - Should be <200ms
2. **Auth-gateway error rate** - Should be <1%
3. **Container creation success rate** - Should be >99%
4. **Container boot time** - Should be unchanged

### CloudWatch Alarms (AWS)
```bash
# Auth-gateway timeout alarm
aws cloudwatch put-metric-alarm \
  --alarm-name orchestrator-auth-timeout \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --metric-name AuthGatewayTimeout \
  --namespace Orchestrator \
  --period 60 \
  --threshold 5

# Container creation failure alarm
aws cloudwatch put-metric-alarm \
  --alarm-name orchestrator-container-creation-failure \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --metric-name ContainerCreationError \
  --namespace Orchestrator \
  --period 60 \
  --threshold 3
```

## Common Issues & Solutions

### Issue 1: Auth-gateway connection timeout
**Symptoms:** Container creation returns 503 error, logs show "Auth service timeout"
**Solution:**
- Check auth-gateway is running: `curl http://auth-gateway:8001/health`
- Verify network connectivity from orchestrator to auth-gateway
- Check AUTH_GATEWAY_URL environment variable is correct

### Issue 2: Invalid user_id in response
**Symptoms:** Container creation returns 500 error, logs show "Invalid auth response"
**Solution:**
- Verify auth-gateway returns `{"user_id": "..."}` in response body
- Check auth-gateway API implementation matches expected format

### Issue 3: Container fails to boot
**Symptoms:** Container status stuck in PENDING or moves to FAILED
**Solution:**
- Check container logs: `docker logs <container-id>`
- Verify DynamoDB config exists for user
- Check CONFIG_NAME environment variable is set correctly
- Verify container has network access to DynamoDB

### Issue 4: httpx not found
**Symptoms:** Import error when starting orchestrator
**Solution:**
- Install dependencies: `pip install -r requirements.txt`
- Verify httpx is installed: `pip show httpx`
- Check Python environment is correct

## Success Criteria

Deployment is successful when:
- [x] All code changes deployed
- [ ] Tests pass in staging
- [ ] Container creation works with valid API key
- [ ] Container creation fails with invalid API key
- [ ] Auth-gateway integration working
- [ ] Containers boot successfully
- [ ] No errors in production logs
- [ ] Performance metrics within acceptable range

---
**Deployment Date:** _____________
**Deployed By:** _____________
**Environment:** _____________
**Rollback Required:** Yes / No
**Notes:** _____________
