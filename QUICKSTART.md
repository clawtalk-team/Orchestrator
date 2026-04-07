# Quick Start Guide - Get Orchestrator Working Now!

This guide will get your orchestrator working and launching containers in **5 minutes**.

## Prerequisites

- ✅ Auth-gateway is deployed and working
- ✅ DynamoDB table `openclaw-containers` exists
- ✅ Test API key available: `d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930`
- ⚠️ ECS cluster configured OR local Docker for testing

## Step 1: Install Dependencies

```bash
cd /Users/andrewsinclair/workspace/clawtalk/orchestrator
pip install -r requirements.txt
```

## Step 2: Verify Configuration

Check your `.env` file has these critical settings:

```bash
grep -E "(AUTH_GATEWAY_URL|CONTAINERS_TABLE|ECS_CLUSTER_NAME)" .env
```

Should show:
```
AUTH_GATEWAY_URL=https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com
CONTAINERS_TABLE=openclaw-containers
ECS_CLUSTER_NAME=clawtalk-dev
```

## Step 3: Set Up DynamoDB (One-time)

Run the setup script to configure system defaults and user config:

```bash
./setup_and_test.sh
```

This will:
1. ✅ Verify your API key with auth-gateway
2. ✅ Set up system defaults in DynamoDB
3. ✅ Create user config in DynamoDB
4. ✅ Test container creation

**Manual alternative (if script fails):**

```bash
# Get your user_id from auth-gateway
curl -X GET https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/auth \
  -H 'Authorization: Bearer d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930'

# Returns: {"user_id": "some-uuid"}
# Save this user_id for the next command
```

```python
# Create configs in DynamoDB using Python
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
table = dynamodb.Table('openclaw-containers')

# 1. System defaults
table.put_item(Item={
    'pk': 'SYSTEM',
    'sk': 'CONFIG#defaults',
    'config_type': 'system_config',
    'auth_gateway_url': 'https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com',
    'openclaw_url': 'http://localhost:18789',
    'openclaw_token': 'test-token-123',
    'voice_gateway_url': 'http://voice-gateway-dev-544339776.ap-southeast-2.elb.amazonaws.com',
    'updated_at': datetime.utcnow().isoformat()
})

# 2. User config (replace YOUR_USER_ID)
table.put_item(Item={
    'pk': 'USER#YOUR_USER_ID',  # Replace with actual user_id
    'sk': 'CONFIG#default',
    'config_type': 'user_config',
    'user_id': 'YOUR_USER_ID',  # Replace with actual user_id
    'llm_provider': 'anthropic',
    'openclaw_model': 'claude-3-haiku-20240307',
    'auth_gateway_api_key': 'd3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930',
    'anthropic_api_key': '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',
    'created_at': datetime.utcnow().isoformat(),
    'updated_at': datetime.utcnow().isoformat()
})

print("✓ Configuration created!")
```

## Step 4: Start the Orchestrator

```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Step 5: Test It!

In a new terminal:

```bash
# Test health endpoint (no auth required)
curl http://localhost:8000/health

# Create a container
curl -X POST http://localhost:8000/containers \
  -H 'Authorization: Bearer d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930' \
  -H 'Content-Type: application/json' \
  -d '{"config_name": "default"}'
```

**Expected response:**
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

## Step 6: Verify Container Launch

### If Using ECS:

```bash
# Check ECS tasks
aws ecs list-tasks --cluster clawtalk-dev --region ap-southeast-2

# Get task details
aws ecs describe-tasks --cluster clawtalk-dev --tasks <task-arn> --region ap-southeast-2

# Check container logs
aws logs tail /ecs/openclaw-agent-dev --follow --region ap-southeast-2
```

### If Testing Locally (without ECS):

The container creation will fail at the ECS launch step, but you can verify:

1. ✅ Auth-gateway validation works (user_id extracted)
2. ✅ Config stored in DynamoDB
3. ✅ API key accepted

Check the stored config:
```bash
# Get your user_id first
USER_ID=$(curl -s https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/auth \
  -H 'Authorization: Bearer d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['user_id'])")

# Check DynamoDB config
aws dynamodb get-item \
  --table-name openclaw-containers \
  --key "{\"pk\":{\"S\":\"USER#$USER_ID\"},\"sk\":{\"S\":\"CONFIG#default\"}}" \
  --region ap-southeast-2
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'httpx'"

**Solution:**
```bash
pip install httpx
```

### Issue: "Auth service timeout" (503)

**Solution:**
```bash
# Test auth-gateway directly
curl https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com/auth \
  -H 'Authorization: Bearer d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930'

# Should return: {"user_id": "..."}
```

### Issue: "Container not found" or ECS task fails

**Cause:** Missing ECS network configuration

**Solution:**

Add to `.env`:
```bash
# Get your VPC subnets
aws ec2 describe-subnets --region ap-southeast-2 \
  --filters "Name=vpc-id,Values=<your-vpc-id>" \
  --query 'Subnets[*].[SubnetId,AvailabilityZone]' --output table

# Add to .env
ECS_SUBNETS=subnet-xxxxx,subnet-yyyyy
ECS_SECURITY_GROUPS=sg-xxxxx
```

### Issue: "No user config found"

**Solution:** Run the setup script again:
```bash
./setup_and_test.sh
```

Or manually create the config in DynamoDB (see Step 3).

## What's Happening Behind the Scenes?

1. **You send request** with API key to orchestrator
2. **Orchestrator validates** API key with auth-gateway → gets user_id
3. **Orchestrator stores** your API key in DynamoDB config
4. **ECS task launches** with environment variables pointing to DynamoDB
5. **Container boots** and fetches config from DynamoDB
6. **Container uses** your API key to authenticate with auth-gateway
7. **Container connects** to voice-gateway and starts serving

## Next Steps

Once you see a container created successfully:

1. **Check container status:**
   ```bash
   curl http://localhost:8000/containers \
     -H 'Authorization: Bearer d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930'
   ```

2. **List all containers:**
   ```bash
   curl http://localhost:8000/containers \
     -H 'Authorization: Bearer d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930'
   ```

3. **Delete a container:**
   ```bash
   curl -X DELETE http://localhost:8000/containers/<container-id> \
     -H 'Authorization: Bearer d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930'
   ```

4. **Monitor ECS tasks:**
   - AWS Console: https://console.aws.amazon.com/ecs/v2/clusters/clawtalk-dev/tasks
   - CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=ap-southeast-2#logsV2:log-groups

## Success! 🎉

You now have:
- ✅ Working orchestrator with auth-gateway integration
- ✅ API key validation working
- ✅ Config management in DynamoDB
- ✅ Container provisioning ready

**Test API Key:** `d3559a7b1882bdf163885165895a048f566ac74d1639f4ef0b49bd698f714930`

**Auth-Gateway:** https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com

**Orchestrator API:** http://localhost:8000/docs

---

For more details, see:
- DEPLOYMENT_GUIDE.md - Complete deployment information
- IMPLEMENTATION_SUMMARY.md - Technical implementation details
- test_auth_gateway_integration.sh - Integration test script
