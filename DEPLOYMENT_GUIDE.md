# Container Provisioning Enhancement - Deployment Guide

## 🎉 Implementation Complete!

The container provisioning API enhancement has been successfully implemented. The orchestrator now integrates with the auth-gateway to validate API keys and provision containers with proper authentication.

## 📋 What Was Implemented

### Core Changes
1. **Auth-Gateway Integration** - Orchestrator validates API keys via `GET /auth` endpoint
2. **API Key Storage** - User API keys stored in DynamoDB for containers to use
3. **Named Configs** - Support for multiple named configurations per user
4. **Container Boot** - Containers fetch all config from DynamoDB at startup
5. **Plaintext Storage** - Secrets stored in plaintext (encryption in Phase 2)

### Auth-Gateway Configuration

**Production Auth-Gateway:** `https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com`

**Authentication Endpoint:** `GET /auth`
- Request: `Authorization: Bearer {api_key}`
- Response: `{"user_id": "string"}`
- Already deployed and working! ✅

**Other Endpoints Available:**
- `POST /auth/login` - User login with email/password
- `POST /users` - Create new user account
- `GET /users/{identifier}` - Get user details
- `POST /users/{identifier}/apikey/rotate` - Rotate API key

## 🚀 Deployment Steps

### 1. Update Environment Configuration

The `.env` file has been updated with the correct auth-gateway URL:
```bash
AUTH_GATEWAY_URL=https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com
```

**Required Environment Variables:**
- `AUTH_GATEWAY_URL` - ✅ Already set
- `ECS_CLUSTER_NAME` - ✅ Already set (clawtalk-dev)
- `ECS_TASK_DEFINITION` - ✅ Already set (openclaw-agent-dev)
- `CONTAINERS_TABLE` - ✅ Already set (openclaw-containers)
- `MASTER_API_KEY` - ✅ Already set (for admin access)

**Missing (Required for ECS):**
- `ECS_SUBNETS` - Comma-separated subnet IDs for ECS tasks
- `ECS_SECURITY_GROUPS` - Comma-separated security group IDs

Add these to `.env`:
```bash
# Example - replace with your actual VPC subnets/security groups
ECS_SUBNETS=subnet-xxxxx,subnet-yyyyy
ECS_SECURITY_GROUPS=sg-xxxxx
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Verify httpx is installed:
```bash
pip show httpx
# Should show: Version: 0.24.0 or higher
```

### 3. Run Tests

```bash
# Run auth middleware tests
python -m pytest tests/unit/test_auth_middleware.py -v

# Run all tests
python -m pytest tests/ -v
```

### 4. Start the Orchestrator

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production (with gunicorn)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 5. Run Integration Tests

```bash
# Test auth-gateway integration
./test_auth_gateway_integration.sh

# Or manually test the health endpoint
curl http://localhost:8000/health
```

## ✅ Verification Steps

### Step 1: Create Test User in Auth-Gateway

```bash
# Create a new user account
curl -X POST https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/users \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "display_name": "Test User",
    "password": "SecurePassword123!"
  }'

# Response will include api_key:
# {
#   "email": "test@example.com",
#   "uuid": "user-123",
#   "api_key": "sk-clawtalk-abc123...",
#   "created_at": "2026-04-07T10:00:00Z"
# }
```

**Save the `api_key` from the response!**

### Step 2: Test API Key Validation

```bash
# Test auth-gateway directly
curl -X GET https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/auth \
  -H 'Authorization: Bearer YOUR_API_KEY'

# Should return:
# {"user_id": "user-123"}
```

### Step 3: Create Container via Orchestrator

```bash
# Create a container with your API key
curl -X POST http://localhost:8000/containers \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"config_name": "default"}'

# Expected response:
# {
#   "container_id": "oc-abc12345",
#   "status": "PENDING",
#   "ip_address": null,
#   "health_status": "UNKNOWN",
#   "created_at": "2026-04-07T10:00:00Z",
#   "updated_at": "2026-04-07T10:00:00Z"
# }
```

### Step 4: Verify Config in DynamoDB

```bash
# Check that config was stored (replace with your user_id)
aws dynamodb get-item \
  --table-name openclaw-containers \
  --key '{"pk":{"S":"USER#user-123"},"sk":{"S":"CONFIG#default"}}' \
  --region ap-southeast-2

# Should see:
# {
#   "Item": {
#     "pk": {"S": "USER#user-123"},
#     "sk": {"S": "CONFIG#default"},
#     "auth_gateway_api_key": {"S": "sk-clawtalk-abc123..."},
#     "llm_provider": {"S": "anthropic"},
#     "openclaw_model": {"S": "claude-3-haiku-20240307"},
#     "created_at": {"S": "2026-04-07T10:00:00Z"},
#     "updated_at": {"S": "2026-04-07T10:00:00Z"}
#   }
# }
```

### Step 5: Check Container Logs

```bash
# Get ECS task ARN from DynamoDB or ECS console
TASK_ARN="arn:aws:ecs:ap-southeast-2:826182175287:task/clawtalk-dev/abc123"

# Get container logs
aws logs tail /ecs/openclaw-agent-dev --follow --region ap-southeast-2

# Expected output:
# === Fetching config for user_id=user-123, config_name=default ===
# Container ID: oc-abc12345
# [1/4] Fetching user config from DynamoDB...
# [2/4] Fetching system config from DynamoDB...
# [3/4] Building OpenClaw config...
# ✓ Config written to /root/.openclaw/openclaw.json
# [4/4] Building openclaw-agent config...
# ✓ Config written to /root/.clawtalk/clawtalk.json
# === Config fetch completed successfully ===
```

## 🔍 Troubleshooting

### Issue: "Auth service timeout" (503 error)

**Cause:** Cannot reach auth-gateway

**Solution:**
```bash
# Test auth-gateway directly
curl https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/auth \
  -H 'Authorization: Bearer test'

# Check AUTH_GATEWAY_URL in .env
grep AUTH_GATEWAY_URL .env

# Verify network connectivity
ping z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com
```

### Issue: "Invalid API key" (401 error)

**Cause:** API key not recognized by auth-gateway

**Solution:**
1. Verify API key is correct (copy from user creation response)
2. Test API key directly with auth-gateway:
   ```bash
   curl https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/auth \
     -H 'Authorization: Bearer YOUR_API_KEY'
   ```
3. If expired/invalid, rotate the API key:
   ```bash
   curl -X POST https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/users/YOUR_USER_ID/apikey/rotate \
     -H 'Authorization: Bearer YOUR_OLD_API_KEY'
   ```

### Issue: Container fails to start

**Cause:** Missing ECS network configuration

**Solution:**
1. Check ECS_SUBNETS and ECS_SECURITY_GROUPS in `.env`
2. Get your VPC subnets:
   ```bash
   aws ec2 describe-subnets --region ap-southeast-2
   ```
3. Add to `.env`:
   ```bash
   ECS_SUBNETS=subnet-xxxxx,subnet-yyyyy
   ECS_SECURITY_GROUPS=sg-xxxxx
   ```

### Issue: Container can't fetch config from DynamoDB

**Cause:** Missing IAM permissions or wrong region

**Solution:**
1. Verify task execution role has DynamoDB permissions
2. Check DYNAMODB_REGION environment variable
3. Test DynamoDB access from container:
   ```bash
   docker exec CONTAINER_ID aws dynamodb list-tables --region ap-southeast-2
   ```

## 📊 Data Flow Diagram

```
┌─────────┐                 ┌──────────────┐                ┌──────────────┐
│  User   │                 │ Orchestrator │                │ Auth-Gateway │
└────┬────┘                 └──────┬───────┘                └──────┬───────┘
     │                             │                                │
     │ POST /containers            │                                │
     │ Authorization: Bearer key   │                                │
     ├────────────────────────────>│                                │
     │                             │                                │
     │                             │ GET /auth                      │
     │                             │ Authorization: Bearer key      │
     │                             ├───────────────────────────────>│
     │                             │                                │
     │                             │ {"user_id": "user-123"}        │
     │                             │<───────────────────────────────┤
     │                             │                                │
     │                             ▼                                │
     │                      ┌─────────────┐                         │
     │                      │  DynamoDB   │                         │
     │                      │             │                         │
     │                      │ Store:      │                         │
     │                      │ - api_key   │                         │
     │                      │ - user_id   │                         │
     │                      │ - config    │                         │
     │                      └─────────────┘                         │
     │                             │                                │
     │                             ▼                                │
     │                       Launch ECS Task                        │
     │                       - USER_ID                              │
     │                       - CONFIG_NAME                          │
     │                       - DYNAMODB_TABLE                       │
     │                             │                                │
     │ {"container_id": "oc-123"}  │                                │
     │<────────────────────────────┤                                │
     │                             │                                │
     │                             │                                │
     │                      ┌──────▼──────┐                         │
     │                      │  Container  │                         │
     │                      │   Startup   │                         │
     │                      └──────┬──────┘                         │
     │                             │                                │
     │                             │ Fetch config                   │
     │                             │ from DynamoDB                  │
     │                             ▼                                │
     │                      ┌─────────────┐                         │
     │                      │  DynamoDB   │                         │
     │                      │             │                         │
     │                      │ Return:     │                         │
     │                      │ - api_key   │                         │
     │                      │ - config    │                         │
     │                      └─────────────┘                         │
     │                             │                                │
     │                             ▼                                │
     │                    Write config files                        │
     │                    - clawtalk.json                           │
     │                    - openclaw.json                           │
     │                             │                                │
     │                             ▼                                │
     │                     Start openclaw-agent                     │
     │                             │                                │
     │                             │ Authenticate                   │
     │                             │ with api_key                   │
     │                             ├───────────────────────────────>│
     │                             │                                │
     │                             │ Success                        │
     │                             │<───────────────────────────────┤
     │                             │                                │
     │                             ▼                                │
     │                      Container RUNNING                       │
```

## 🔐 Security Considerations

### Current Implementation (Phase 1)
- ✅ API keys validated via auth-gateway
- ✅ Master API key uses constant-time comparison
- ⚠️ **Secrets stored in plaintext in DynamoDB**
- ⚠️ **No encryption at rest** (to be added in Phase 2)

### Phase 2 Enhancements (TODO)
- [ ] Implement AWS KMS encryption for secrets
- [ ] Encrypt `auth_gateway_api_key` before storing
- [ ] Encrypt LLM provider API keys
- [ ] Add secret rotation support
- [ ] Audit logging for config access

### Best Practices
1. **Never log API keys** - Already implemented
2. **Use HTTPS** - Auth-gateway already uses HTTPS ✅
3. **Validate all inputs** - Already implemented ✅
4. **Use IAM roles** - Use for DynamoDB access ✅
5. **Rotate keys regularly** - Auth-gateway supports key rotation

## 📚 API Documentation

### Create Container
```http
POST /containers
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "config_name": "default"
}
```

**Response:**
```json
{
  "container_id": "oc-abc12345",
  "status": "PENDING",
  "ip_address": null,
  "health_status": "UNKNOWN",
  "created_at": "2026-04-07T10:00:00Z",
  "updated_at": "2026-04-07T10:00:00Z"
}
```

### List Containers
```http
GET /containers
Authorization: Bearer {api_key}
```

### Get Container Details
```http
GET /containers/{container_id}
Authorization: Bearer {api_key}
```

### Delete Container
```http
DELETE /containers/{container_id}
Authorization: Bearer {api_key}
```

## 🎯 Next Steps

### Immediate (Phase 1 Complete)
1. ✅ Update AUTH_GATEWAY_URL in .env
2. ✅ Test with real auth-gateway
3. ⏳ Add ECS_SUBNETS and ECS_SECURITY_GROUPS to .env
4. ⏳ Deploy to production
5. ⏳ Create test user and verify end-to-end flow

### Phase 2 (Encryption & Config API)
1. Implement AWS KMS encryption
2. Add config management endpoints:
   - `GET /config` - View user config
   - `POST /config` - Update user config
   - `GET /config/system` - View system defaults
3. Add config validation
4. Add secret rotation support
5. Add audit logging

### Phase 3 (Monitoring & Operations)
1. Add CloudWatch metrics
2. Set up alarms for auth failures
3. Add distributed tracing
4. Create operational runbooks
5. Performance optimization

## 📝 Summary

**Status:** ✅ Implementation Complete (Phase 1)

**What Works:**
- Auth-gateway integration with production endpoint
- API key validation and user_id extraction
- Config storage in DynamoDB (plaintext)
- Container provisioning with named configs
- Container boot script fetches config from DynamoDB

**What's Next:**
1. Add ECS network configuration (subnets/security groups)
2. Test with real user accounts
3. Deploy to production environment
4. Add encryption (Phase 2)

**Files Modified:**
- `app/middleware/auth.py` - Auth-gateway integration
- `app/models/container.py` - Added config_name field
- `app/routes/containers.py` - Pass api_key to ECS
- `app/services/ecs.py` - Store api_key, add CONFIG_NAME
- `app/services/user_config.py` - Remove encryption, support named configs
- `scripts/container/fetch_config.py` - Support CONFIG_NAME
- `tests/unit/test_auth_middleware.py` - Mock auth-gateway
- `.env` - Updated AUTH_GATEWAY_URL

---
**Implementation Date:** 2026-04-07
**Auth-Gateway:** https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com
**Documentation:** See IMPLEMENTATION_SUMMARY.md for detailed technical info
