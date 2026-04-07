import os
from unittest.mock import MagicMock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

# Set up environment for testing to use local DynamoDB
os.environ["DYNAMODB_ENDPOINT"] = "http://localhost:8000"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["ECS_CLUSTER_NAME"] = "test-cluster"
os.environ["ECS_TASK_DEFINITION"] = "test-task"
os.environ["ECS_CONTAINER_NAME"] = "test-container"

# Clear the settings cache before tests
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session")
def dynamodb_setup():
    """Set up DynamoDB table once for the entire test session."""
    from app.services.dynamodb import ensure_table_exists
    from app.config import get_settings

    settings = get_settings()

    # Ensure table exists in local DynamoDB
    ensure_table_exists()

    yield

    # Optionally clean up table after all tests
    # (keeping it around can be useful for debugging)


@pytest.fixture
def clean_dynamodb(dynamodb_setup):
    """Clean DynamoDB table before each test."""
    from app.services.dynamodb import _get_table

    table = _get_table()

    # Delete all items from the table
    scan = table.scan()
    with table.batch_writer() as batch:
        for item in scan.get('Items', []):
            batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})

    yield

    # Clean up after test as well
    scan = table.scan()
    with table.batch_writer() as batch:
        for item in scan.get('Items', []):
            batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})


@pytest.fixture
def ecs_mocks():
    """Set up mocked ECS service (still using moto for ECS)."""
    with mock_aws():
        # Set up ECS cluster
        ecs = boto3.client("ecs", region_name="us-east-1")
        ecs.create_cluster(clusterName="test-cluster")

        # Register task definition
        ecs.register_task_definition(
            family="test-task",
            networkMode="awsvpc",
            requiresCompatibilities=["FARGATE"],
            cpu="256",
            memory="512",
            containerDefinitions=[
                {
                    "name": "test-container",
                    "image": "openclaw-agent:latest",
                    "portMappings": [
                        {
                            "containerPort": 8080,
                            "hostPort": 8080,
                            "protocol": "tcp",
                        }
                    ],
                }
            ],
        )

        yield


@pytest.fixture
def aws_mocks(clean_dynamodb, ecs_mocks):
    """Combined AWS mocks fixture for backward compatibility."""
    yield


@pytest.fixture
def client(clean_dynamodb):
    """Test client with clean DynamoDB."""
    from app.main import app

    return TestClient(app)


@pytest.fixture
def authenticated_client(clean_dynamodb):
    """Test client with authentication header."""
    from app.main import app

    client = TestClient(app)
    client.headers.update({"Authorization": "Bearer test-user:test-token-value"})
    return client
