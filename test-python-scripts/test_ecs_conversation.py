#!/usr/bin/env python3
"""
Test conversational invocation with AgentCore Runtime
Includes manual Docker build/push steps before deployment
"""

import boto3
import json
import uuid
import subprocess
import time
import sys

RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/ecs_deployment_agent-Kq38Lc3cm5"
AGENT_REGION = "us-west-2"  # AgentCore agent region
DEPLOY_REGION = "eu-north-1"  # ECS deployment region
ACCOUNT_ID = "<AWS_ACCOUNT_ID>"
APP_NAME = "sample-application"
APP_PATH = "$PROJECT_ROOT/sample-application"

client = boto3.client('bedrock-agentcore', region_name=AGENT_REGION)
session_id = str(uuid.uuid4())

def chat(message):
    """Send message and get response"""
    print(f"\n🧑 You: {message}")
    
    payload = json.dumps({"prompt": message}).encode()
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        payload=payload
    )
    
    response_body = response['response'].read()
    response_data = json.loads(response_body)
    
    # Extract text from response
    message_content = response_data.get('message', {})
    if isinstance(message_content, dict):
        content = message_content.get('content', [])
        if content and isinstance(content, list):
            text = content[0].get('text', str(response_data))
        else:
            text = str(response_data)
    else:
        text = str(message_content)
    
    print(f"🤖 Agent: {text}")
    return text

def run_command(cmd, description):
    """Run shell command and handle errors"""
    print(f"\n🔧 {description}")
    print(f"   Command: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    import shlex
    cmd_list = shlex.split(cmd) if isinstance(cmd, str) else cmd
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ❌ Error: {result.stderr}")
        return False
    print(f"   ✓ Success")
    return True

# Test conversation with Docker build/push
print(f"Session ID: {session_id}\n")
print("=" * 80)

# Step 1: Create ECR repository via agent
chat(f"Create an ECR repository named {APP_NAME} in {DEPLOY_REGION}")

# Step 2: Build and push Docker image (manual local steps)
print("\n" + "=" * 80)
print("MANUAL DOCKER BUILD/PUSH STEPS (running locally)")
print("=" * 80)

image_uri = f"{ACCOUNT_ID}.dkr.ecr.{DEPLOY_REGION}.amazonaws.com/{APP_NAME}:latest"

# ECR login first
run_command(
    f"aws ecr get-login-password --region {DEPLOY_REGION} | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{DEPLOY_REGION}.amazonaws.com",
    "Logging into ECR"
)

# Build multi-platform image and push directly
if not run_command(
    f"docker buildx build --platform linux/amd64,linux/arm64 -t {image_uri} --push {APP_PATH}",
    "Building and pushing multi-platform image to ECR"
):
    print("\n⚠️  Build/push failed. Trying single platform...")
    # Fallback: build for current platform and push
    run_command(f"cd {APP_PATH} && docker build -t {APP_NAME}:latest .", "Building single-platform image")
    run_command(f"docker tag {APP_NAME}:latest {image_uri}", "Tagging image")
    run_command(f"docker push {image_uri}", "Pushing to ECR")

print("\n" + "=" * 80)
print("RESUMING AGENT CONVERSATION")
print("=" * 80)

# Step 3: Deploy to ECS via agent with environment variables
service_name = f"blog-app-{int(time.time())}"

# Environment variables matching EC2 deployment
env_vars = {
    "AWS_REGION": "eu-north-1",
    "DYNAMODB_TABLE": "blog-posts",
    "S3_BUCKET": "blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1",
    "COGNITO_USER_POOL_ID": os.getenv("COGNITO_USER_POOL_ID", "your-user-pool-id"),
    "COGNITO_CLIENT_ID": os.getenv("COGNITO_CLIENT_ID", "your-client-id"),
    "PORT": "3000"
}

chat(f"""Deploy the image {image_uri} to ECS Express Mode in {DEPLOY_REGION}.
Use these parameters:
- service_name: {service_name}
- cpu: 512
- memory: 1024
- port: 3000
- region: {DEPLOY_REGION}
- environment_variables: {json.dumps(env_vars)}

Make sure to pass the environment_variables parameter to the deploy_ecs_express_service tool.
""")

# Step 4: Wait and check status
print("\n⏳ Waiting 90 seconds for CloudFormation stack to create...")
time.sleep(90)
chat(f"Show me the status of {service_name} including the endpoint URL")

print("\n" + "=" * 80)
print("✓ Complete ECS deployment test with Docker build/push")
print("=" * 80)
