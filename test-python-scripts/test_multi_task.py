#!/usr/bin/env python3
"""
Test multi-task deployment with AgentCore Runtime
"""

import boto3
import json
import uuid
import time

RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/ecs_deployment_agent-Kq38Lc3cm5"
AGENT_REGION = "us-west-2"
DEPLOY_REGION = "eu-north-1"
ACCOUNT_ID = "<AWS_ACCOUNT_ID>"
IMAGE_URI = f"{ACCOUNT_ID}.dkr.ecr.{DEPLOY_REGION}.amazonaws.com/sample-application:latest"

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

print(f"Session ID: {session_id}\n")
print("=" * 80)
print("TESTING MULTI-TASK DEPLOYMENT")
print("=" * 80)

# Environment variables
env_vars = {
    "AWS_REGION": "eu-north-1",
    "DYNAMODB_TABLE": "blog-posts",
    "S3_BUCKET": "blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1",
    "COGNITO_USER_POOL_ID": os.getenv("COGNITO_USER_POOL_ID", "your-user-pool-id"),
    "COGNITO_CLIENT_ID": os.getenv("COGNITO_CLIENT_ID", "your-client-id"),
    "PORT": "3000"
}

# Deploy with 3 tasks using ExpressGatewayScalingTarget
service_name = f"blog-multi-{int(time.time())}"
chat(f"""Deploy the image {IMAGE_URI} to ECS Express Mode in {DEPLOY_REGION}.
Use these parameters:
- service_name: {service_name}
- cpu: 512
- memory: 1024
- port: 3000
- region: {DEPLOY_REGION}
- desired_count: 3
- environment_variables: {json.dumps(env_vars)}

Set desired_count to 3 for high availability.
""")

# Wait for deployment
print("\n⏳ Waiting 90 seconds for deployment...")
time.sleep(90)

# Check status
chat(f"Show me the status of {service_name} including task count and endpoint URL")

print("\n" + "=" * 80)
print("✓ Multi-task deployment test complete")
print("=" * 80)
