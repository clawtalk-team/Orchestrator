#!/usr/bin/env python3
"""
List all containers that the orchestrator thinks it is managing.
Queries DynamoDB for all container records.

Usage: python scripts/list_containers.py [--env ENV] [--user-id USER_ID]
"""

import argparse
import boto3
from typing import Optional
from tabulate import tabulate


def list_containers(
    env: str = "dev",
    user_id: Optional[str] = None,
    profile: str = "personal",
    region: str = "ap-southeast-2"
):
    """List all containers from DynamoDB."""
    table_name = f"openclaw-containers-{env}"

    session = boto3.Session(profile_name=profile, region_name=region)
    dynamodb = session.client("dynamodb")

    print(f"==> Listing containers from DynamoDB table: {table_name}\n")

    if user_id:
        # Query specific user
        print(f"Filtering by user: {user_id}")
        response = dynamodb.query(
            TableName=table_name,
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={
                ":pk": {"S": f"USER#{user_id}"}
            }
        )
        items = response.get("Items", [])
    else:
        # Scan all containers
        response = dynamodb.scan(TableName=table_name)
        items = response.get("Items", [])

    if not items:
        print("No containers found.")
        return

    # Parse items into table format
    table_data = []
    for item in items:
        container_id = item.get("sk", {}).get("S", "").replace("CONTAINER#", "")
        user = item.get("user_id", {}).get("S", "")
        status = item.get("status", {}).get("S", "")
        task_arn = item.get("task_arn", {}).get("S", "")
        ip = item.get("ip_address", {}).get("S", "")
        created = item.get("created_at", {}).get("S", "")
        health = item.get("health_status", {}).get("S", "")

        table_data.append([
            container_id,
            user,
            status,
            health,
            ip,
            task_arn.split("/")[-1] if task_arn else "",
            created
        ])

    headers = ["Container ID", "User ID", "Status", "Health", "IP Address", "Task ID", "Created At"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal containers: {len(items)}")


def main():
    parser = argparse.ArgumentParser(description="List orchestrator-managed containers")
    parser.add_argument("--env", default="dev", help="Environment (dev/prod)")
    parser.add_argument("--user-id", help="Filter by specific user ID")
    parser.add_argument("--profile", default="personal", help="AWS profile name")
    parser.add_argument("--region", default="ap-southeast-2", help="AWS region")

    args = parser.parse_args()

    list_containers(
        env=args.env,
        user_id=args.user_id,
        profile=args.profile,
        region=args.region
    )


if __name__ == "__main__":
    main()
