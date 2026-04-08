# Orchestrator Service

Container orchestrator for managing openclaw-agent instances. Provides API for dynamic provisioning, lifecycle management, and health monitoring of containerized agents running on AWS ECS Fargate.

## Overview

The orchestrator enables users to spin up isolated openclaw-agent containers on-demand, each with their own configuration and resources. Built as a serverless FastAPI Lambda function with API Gateway frontend.

## Deployment Status

**✅ Deployed to AWS Dev Environment**

- **API Gateway URL:** `https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/`
- **Lambda Function:** `orchestrator-dev`
- **DynamoDB Table:** `openclaw-containers-dev`
- **Region:** ap-southeast-2

## Quick Start

### Production API (AWS Dev)
```bash
# Health check
curl https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/health

# Create a container
curl -X POST https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/containers \
  -H "Authorization: Bearer {USER_ID}:{YOUR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{}'

# List containers
curl https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/containers \
  -H "Authorization: Bearer {USER_ID}:{YOUR_TOKEN}"

# Get specific container
curl https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/containers/{CONTAINER_ID} \
  -H "Authorization: Bearer {USER_ID}:{YOUR_TOKEN}"

# Delete container
curl -X DELETE https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/containers/{CONTAINER_ID} \
  -H "Authorization: Bearer {USER_ID}:{YOUR_TOKEN}"
```

**Token Format:** `user_id:token_string` (minimum 20 characters total)
Example: `{USER_ID}:{YOUR_TOKEN}`

### Local Development
```bash
# Run locally with Docker Compose
make docker-up

# Test the API
curl http://localhost:8000/health

# Create a container
curl -X POST http://localhost:8000/containers \
  -H "Authorization: Bearer {USER_ID}:{YOUR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent"}'
```

## Getting Container Logs

### Quick Method (using container ID)

```bash
CONTAINER_ID="{CONTAINER_ID}"
USER_ID="{USER_ID}"

# 1. Get task ARN from DynamoDB
TASK_ARN=$(aws --profile personal dynamodb get-item \
  --table-name openclaw-containers-dev \
  --region ap-southeast-2 \
  --key "{\"pk\":{\"S\":\"USER#${USER_ID}\"},\"sk\":{\"S\":\"CONTAINER#${CONTAINER_ID}\"}}" \
  --query 'Item.task_arn.S' \
  --output text)

# 2. Extract task ID
TASK_ID=$(echo $TASK_ARN | rev | cut -d'/' -f1 | rev)

# 3. View logs
aws --profile personal logs tail /ecs/openclaw-agent-dev \
  --region ap-southeast-2 \
  --since 30m \
  --format short \
  --filter-pattern "$TASK_ID"

# 4. Follow logs in real-time
aws --profile personal logs tail /ecs/openclaw-agent-dev \
  --region ap-southeast-2 \
  --follow \
  --format short
```

### All Container Logs (recent)

```bash
# View all openclaw-agent logs from last 30 minutes
aws --profile personal logs tail /ecs/openclaw-agent-dev \
  --region ap-southeast-2 \
  --since 30m \
  --follow
```

See [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) for complete deployment and monitoring guide.

## API Endpoints

### Interactive API Documentation

- `GET /docs` - Swagger UI with built-in authentication (click "Authorize" button to enter your API key)
- `GET /redoc` - ReDoc API documentation

### Container Management

- `POST /containers` - Create new container
- `GET /containers` - List user's containers
- `GET /containers/{id}` - Get container details
- `DELETE /containers/{id}` - Stop and remove container
- `GET /containers/{id}/health` - Get container health status

### Configuration Management

- `GET /config` - List all user configurations
- `POST /config` - Create a new user configuration
- `GET /config/{config_name}` - Get a specific user configuration
- `PUT /config/{config_name}` - Update a user configuration (merge or overwrite)
- `DELETE /config/{config_name}` - Delete a user configuration
- `GET /config/system` - Get system-wide configuration (admin only)
- `PUT /config/system` - Update system-wide configuration (admin only)

### System

- `GET /health` - Service health check

## Authentication

Phase 1 uses simple token validation:
- Format: `Bearer user_id:token_hash`
- Minimum length: 20 characters
- Example: `Bearer {USER_ID}:{YOUR_TOKEN}`

Phase 2 will integrate with auth-gateway for full validation.

## Configuration System

The orchestrator uses a **two-tier configuration system** that separates infrastructure-wide settings from user-specific preferences.

### Configuration Hierarchy

```
User Config (highest priority)
  ↓
System Config (infrastructure defaults)
  ↓
Hardcoded Defaults (fallback)
```

### How It Works

When a container is created, the orchestrator:
1. Loads **system config** from DynamoDB (`SYSTEM#CONFIG#defaults`) - infrastructure URLs, shared tokens
2. Loads **user config** from DynamoDB (`USER#{user_id}#CONFIG#{config_name}`) - API keys, preferences
3. **Merges** them with user values overriding system values
4. Passes the merged config to the container as environment variables

This ensures:
- Admins can update infrastructure URLs globally
- Users maintain their own API keys and preferences
- No config duplication across users

### System Configuration (Admin-managed)

System configs define infrastructure shared by all users:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `auth_gateway_url` | string | Auth gateway endpoint URL | `https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com` |
| `openclaw_url` | string | OpenClaw gateway URL | `http://localhost:18789` |
| `openclaw_token` | string | Shared OpenClaw service token | `test-token-123` |
| `voice_gateway_url` | string | Voice gateway WebSocket URL | `ws://localhost:9090` |

**Storage location:** DynamoDB key `pk="SYSTEM"`, `sk="CONFIG#defaults"`

### User Configuration (User-specific)

User configs define personal settings and secrets:

| Parameter | Type | Description | Example | Required |
|-----------|------|-------------|---------|----------|
| `llm_provider` | string | LLM provider choice | `anthropic`, `openai`, `openrouter` | Yes |
| `openclaw_model` | string | Default model to use | `claude-3-haiku-20240307` | Yes |
| `auth_gateway_api_key` | string | User's auth gateway API key | `b13b7bb9cbe9ecfa112cf...` | Yes |
| `anthropic_api_key` | string | Anthropic API key (if provider=anthropic) | `sk-ant-api03-...` | Conditional |
| `openai_api_key` | string | OpenAI API key (if provider=openai) | `sk-...` | Conditional |
| `openrouter_api_key` | string | OpenRouter API key (if provider=openrouter) | `sk-or-...` | Conditional |

**Storage location:** DynamoDB key `pk="USER#{user_id}"`, `sk="CONFIG#{config_name}"`

**Note:** This parameter set will grow as new features are added (e.g., voice settings, agent preferences, custom models).

### Setting Up Default Configurations

#### Option 1: Using the Helper Script (Recommended)

```bash
# Load system + user defaults
python3 scripts/load_defaults.py \
  --system \
  --user-id "your-user-id" \
  --auth-gateway-url "https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com" \
  --openclaw-url "http://localhost:18789" \
  --openclaw-token "test-token-123" \
  --llm-provider "anthropic" \
  --openclaw-model "claude-3-haiku-20240307" \
  --auth-gateway-api-key "your-auth-key" \
  --anthropic-api-key "your-anthropic-key"

# Verify configs were loaded
python3 scripts/load_defaults.py --verify --user-id "your-user-id"
```

#### Option 2: Using the Config API

```bash
# Create/update system config (admin only)
curl -X PUT https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/config/system \
  -H "Authorization: Bearer {ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_gateway_url": "https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com",
    "openclaw_url": "http://localhost:18789",
    "openclaw_token": "test-token-123"
  }'

# Create/update user config
curl -X POST https://prz6mum7c7.execute-api.ap-southeast-2.amazonaws.com/config \
  -H "Authorization: Bearer {USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "config_name": "default",
    "llm_provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "openclaw_model": "claude-3-haiku-20240307"
  }'
```

#### Option 3: Manual DynamoDB Setup

```python
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
table = dynamodb.Table('openclaw-containers')

# System config
table.put_item(Item={
    'pk': 'SYSTEM',
    'sk': 'CONFIG#defaults',
    'config_type': 'system_config',
    'auth_gateway_url': 'https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com',
    'openclaw_url': 'http://localhost:18789',
    'openclaw_token': 'test-token-123',
    'voice_gateway_url': 'ws://localhost:9090',
    'updated_at': datetime.utcnow().isoformat()
})

# User config
table.put_item(Item={
    'pk': 'USER#your-user-id',
    'sk': 'CONFIG#default',
    'config_type': 'user_config',
    'user_id': 'your-user-id',
    'llm_provider': 'anthropic',
    'openclaw_model': 'claude-3-haiku-20240307',
    'auth_gateway_api_key': 'your-auth-key',
    'anthropic_api_key': 'sk-ant-...',
    'created_at': datetime.utcnow().isoformat(),
    'updated_at': datetime.utcnow().isoformat()
})
```

### Configuration API Endpoints

- `GET /config` - List all user configurations
- `POST /config` - Create a new user configuration
- `GET /config/{config_name}` - Get a specific user configuration
- `PUT /config/{config_name}` - Update a user configuration
- `DELETE /config/{config_name}` - Delete a user configuration
- `GET /config/system` - Get system configuration (admin only)
- `PUT /config/system` - Update system configuration (admin only)

See the [API Documentation](./docs/CONFIG_API.md) for detailed endpoint specs.

### Named Configurations

Users can maintain multiple named configurations:

```bash
# Create a "production" config
curl -X POST .../config \
  -d '{"config_name": "production", "llm_provider": "anthropic", ...}'

# Create a "testing" config
curl -X POST .../config \
  -d '{"config_name": "testing", "llm_provider": "openai", ...}'

# Use specific config when creating container
curl -X POST .../containers \
  -d '{"config_name": "production"}'
```

### How Configs Are Merged

When building container configs, the system merges system and user values:

**Example:**

```python
# System Config (from DynamoDB SYSTEM#CONFIG#defaults)
system_config = {
    "auth_gateway_url": "https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com",
    "openclaw_url": "http://localhost:18789",
    "openclaw_token": "test-token-123"
}

# User Config (from DynamoDB USER#{user_id}#CONFIG#default)
user_config = {
    "llm_provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "openclaw_model": "claude-3-haiku-20240307",
    "auth_gateway_api_key": "b13b7bb9..."
}

# Final Merged Config (passed to container)
final_config = {
    # System provides infrastructure
    "auth_gateway_url": "https://z1fm1cdkph.execute-api.ap-southeast-2.amazonaws.com",
    "openclaw_url": "http://localhost:18789",
    "openclaw_token": "test-token-123",

    # User provides secrets and preferences
    "llm_provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "openclaw_model": "claude-3-haiku-20240307",
    "auth_gateway_api_key": "b13b7bb9..."
}
```

**Key principle:** User values always override system values when both define the same field.

## Architecture

Built with:
- **FastAPI** - Modern Python API framework
- **AWS Lambda** - Serverless compute (ARM64)
- **API Gateway HTTP API** - HTTP endpoint
- **DynamoDB** - Container metadata and configuration storage
- **ECS Fargate** - Container runtime
- **CloudWatch Logs** - Logging

See [docs/IMPLEMENTATION_SUMMARY.md](./docs/IMPLEMENTATION_SUMMARY.md) for implementation details.

## Documentation

Comprehensive documentation is available in the [`docs/`](./docs/) directory:

- **[Getting Started](./docs/README.md)** - Documentation index
- **[Deployment Guide](./docs/DEPLOYMENT.md)** - Deploy to AWS infrastructure
- **[E2E Testing](./docs/E2E_TEST_GUIDE.md)** - Run end-to-end tests
- **[Implementation Summary](./docs/IMPLEMENTATION_SUMMARY.md)** - Technical implementation details
- **[Container Requirements](./docs/CONTAINER_REQUIREMENTS.md)** - Container configuration requirements

## Development

```bash
# Install dependencies
make install-dev

# Run tests
make test

# Run E2E tests
make test-e2e           # Local with DynamoDB Local
make test-e2e-aws       # Against real AWS DynamoDB

# Run locally
make docker-up

# Build Lambda image
make build-lambda

# Deploy to AWS
cd ../infrastructure/infra/environments/dev
terraform apply -var="orchestrator_image_tag=dev-latest"
```

## Project Structure

```
orchestrator/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings and configuration
│   ├── middleware/          # Authentication middleware
│   ├── models/              # Pydantic models
│   ├── routes/              # API endpoint handlers
│   └── services/            # Business logic (DynamoDB, ECS)
├── tests/                   # Unit and integration tests
├── lambda_handler.py        # AWS Lambda entry point
├── Dockerfile.lambda        # Lambda container image
└── docker-compose.yml       # Local development setup
```

## License

Proprietary - All rights reserved