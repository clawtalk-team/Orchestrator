# Orchestrator Management Scripts

Python scripts for managing openclaw-agent containers.

## Prerequisites

```bash
# Install dependencies
make install-dev

# Or manually
pip install boto3 tabulate
```

## Scripts

### 1. List Containers (DynamoDB)

List all containers the orchestrator thinks it's managing.

```bash
# List all containers
python scripts/list_containers.py

# List containers for specific user
python scripts/list_containers.py --user-id USER_123

# Use different environment
python scripts/list_containers.py --env prod
```

**Options:**
- `--env` - Environment (dev/prod), default: dev
- `--user-id` - Filter by specific user ID
- `--profile` - AWS profile name, default: personal
- `--region` - AWS region, default: ap-southeast-2

### 2. List ECS Tasks

List all actual ECS tasks running for openclaw-agent.

```bash
# List all ECS tasks
python scripts/list_ecs_tasks.py

# Use different environment
python scripts/list_ecs_tasks.py --env prod
```

**Options:**
- `--env` - Environment (dev/prod), default: dev
- `--profile` - AWS profile name, default: personal
- `--region` - AWS region, default: ap-southeast-2
- `--cluster` - ECS cluster name, default: openclaw

### 3. Get Logs

Fetch CloudWatch logs for a specific container.

```bash
# Get logs by container ID
python scripts/get_logs.py oc-abc12345 --user-id USER_123

# Get logs by task ID
python scripts/get_logs.py --task-id abc123def456

# Follow logs in real-time
python scripts/get_logs.py oc-abc12345 --user-id USER_123 --follow

# Show logs from last hour
python scripts/get_logs.py oc-abc12345 --user-id USER_123 --since 60
```

**Options:**
- `--user-id` - User ID (required with container ID)
- `--task-id` - Task ID (alternative to container ID)
- `--env` - Environment (dev/prod), default: dev
- `--follow` / `-f` - Follow logs in real-time
- `--since` - Show logs from last N minutes, default: 30
- `--profile` - AWS profile name, default: personal
- `--region` - AWS region, default: ap-southeast-2

### 4. Execute Shell

Get an interactive shell on a running container.

```bash
# Connect by container ID
python scripts/exec_shell.py oc-abc12345 --user-id USER_123

# Connect by task ARN
python scripts/exec_shell.py --task-arn arn:aws:ecs:...

# Run custom command
python scripts/exec_shell.py oc-abc12345 --user-id USER_123 --command "ls -la"
```

**Options:**
- `--user-id` - User ID (required with container ID)
- `--task-arn` - Task ARN (alternative to container ID)
- `--env` - Environment (dev/prod), default: dev
- `--command` - Command to execute, default: /bin/bash
- `--profile` - AWS profile name, default: personal
- `--region` - AWS region, default: ap-southeast-2
- `--cluster` - ECS cluster name, default: openclaw
- `--container` - Container name, default: openclaw-agent

**Prerequisites:**
- ECS exec must be enabled on the task
- Session Manager plugin must be installed: [Installation Guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)

### 5. Delete Containers

Stop ECS tasks and remove DynamoDB records.

```bash
# Delete single container
python scripts/delete_containers.py oc-abc12345 --user-id USER_123

# Delete multiple containers
python scripts/delete_containers.py oc-abc12345 oc-def67890 --user-id USER_123

# Delete all containers for a user
python scripts/delete_containers.py --user-id USER_123 --all

# Delete all STOPPED containers
python scripts/delete_containers.py --user-id USER_123 --status STOPPED

# Dry run (show what would be deleted)
python scripts/delete_containers.py --user-id USER_123 --all --dry-run

# Skip confirmation
python scripts/delete_containers.py oc-abc12345 --user-id USER_123 --yes
```

**Options:**
- `--user-id` - User ID (required)
- `--all` - Delete all containers for the user
- `--status` - Delete containers with specific status
- `--env` - Environment (dev/prod), default: dev
- `--dry-run` - Show what would be deleted without deleting
- `--yes` / `-y` - Skip confirmation prompt
- `--profile` - AWS profile name, default: personal
- `--region` - AWS region, default: ap-southeast-2
- `--cluster` - ECS cluster name, default: openclaw

## Common Workflows

### Check container status

```bash
# 1. List all containers in DynamoDB
python scripts/list_containers.py

# 2. List actual running tasks in ECS
python scripts/list_ecs_tasks.py

# 3. Compare to find discrepancies
```

### Debug a container

```bash
# 1. Get the logs
python scripts/get_logs.py oc-abc12345 --user-id USER_123 --since 60

# 2. Get a shell if needed
python scripts/exec_shell.py oc-abc12345 --user-id USER_123

# 3. Check health status (from list output)
python scripts/list_containers.py --user-id USER_123
```

### Clean up stopped containers

```bash
# 1. Check what would be deleted
python scripts/delete_containers.py --user-id USER_123 --status STOPPED --dry-run

# 2. Delete them
python scripts/delete_containers.py --user-id USER_123 --status STOPPED
```

### Monitor logs in real-time

```bash
# Follow logs for a specific container
python scripts/get_logs.py oc-abc12345 --user-id USER_123 --follow
```
