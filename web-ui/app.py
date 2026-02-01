#!/usr/bin/env python3
"""
Web UI for AgentCore ECS/EKS Deployment Tools
A simple Flask-based dashboard to execute deployment and deletion operations
Uses LLM-based routing instead of manual parsing for intelligent tool selection
"""

from flask import Flask, render_template, request, jsonify, Response
import boto3
import json
import subprocess
import threading
import queue
import time
from datetime import datetime
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
import requests

app = Flask(__name__)

# Configuration
CONFIG = {
    'ecs_agent_arn': 'arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/ecs_deployment_agent-Kq38Lc3cm5',
    'eks_agent_arn': 'arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/eks_deployment_agent-bJq2whDHLA',
    'agent_region': 'us-west-2',
    'account_id': '<AWS_ACCOUNT_ID>',
    'app_path': '$PROJECT_ROOT/sample-application',
    # Application environment variables
    'dynamodb_table': 'blog-posts',
    's3_bucket_prefix': 'blog-images-private',
    'cognito_user_pool_id': 'REPLACE_WITH_YOUR_USER_POOL_ID',
    'cognito_client_id': 'REPLACE_WITH_YOUR_CLIENT_ID',
    'app_port': '3000',
    # Default resource settings
    'default_cpu': '512',
    'default_memory': '1024',
    'default_replicas': 2
}

# Store operation logs
operation_logs = {}

# Initialize Bedrock Runtime client for LLM routing with custom retry config
bedrock_config = Config(
    retries={
        'max_attempts': 1,  # Disable boto3's internal retries, we'll handle it ourselves
        'mode': 'standard'
    },
    connect_timeout=10,
    read_timeout=60
)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=CONFIG['agent_region'], config=bedrock_config)

def llm_route_eks_command(message: str, cluster: str, region: str) -> dict:
    """
    Use LLM to intelligently route EKS commands to the appropriate MCP tool
    
    Args:
        message: User's natural language message
        cluster: EKS cluster name
        region: AWS region
        
    Returns:
        Dictionary with tool_name, arguments, and reasoning
    """
    
    # Define available tools for the LLM
    tools_description = """
Available EKS MCP Tools:

1. list_deployments
   - Purpose: List all deployments in the cluster
   - Arguments: cluster_name (string), region (string)
   - Use when: User wants to see, list, or count deployments

2. deploy_to_eks_with_irsa
   - Purpose: Deploy a new application to EKS
   - Arguments: cluster_name, app_name, image_uri, port (int), replicas (int), env_vars (dict), region, role_arn, service_account_name
   - Use when: User wants to deploy, create, or start a new application
   - Note: Requires OIDC and IRSA setup first
   - port: Application port (Java/Spring Boot: 8080, Node.js: 3000, Python/Flask: 5000)
   - env_vars: Only include if app needs AWS services (DynamoDB, S3, Cognito)

3. get_deployment_status
   - Purpose: Check status of a specific deployment
   - Arguments: cluster_name, app_name, region
   - Use when: User wants to check status, see if app is running, or get deployment info

4. delete_eks_deployment
   - Purpose: Delete a deployment and its resources
   - Arguments: cluster_name, app_name, region, delete_service (bool), delete_service_account (bool)
   - Use when: User wants to delete, remove, or clean up a deployment

5. setup_oidc_provider
   - Purpose: Setup OIDC provider for the cluster (one-time setup)
   - Arguments: cluster_name, region
   - Use when: User wants to setup OIDC or prepare cluster for IRSA

6. create_irsa_role
   - Purpose: Create IAM role for service account
   - Arguments: cluster_name, app_name, region, s3_bucket, dynamodb_table
   - Use when: User wants to create IRSA role or setup permissions
"""
    
    prompt = f"""You are an intelligent routing assistant for EKS deployment operations. Analyze the user's message and determine which MCP tool to call.

User Message: "{message}"
Context:
- Cluster: {cluster}
- Region: {region}
- Account ID: {CONFIG['account_id']}
- DynamoDB Table: {CONFIG['dynamodb_table']}
- S3 Bucket Prefix: {CONFIG['s3_bucket_prefix']}

{tools_description}

Analyze the message and respond with a JSON object containing:
1. "tool_name": The exact tool name to call (or "deploy_workflow" for full deployment)
2. "arguments": Dictionary of arguments for the tool
3. "reasoning": Brief explanation of why you chose this tool
4. "needs_build": true if deployment requires Docker build (for deploy operations)

For deployment requests:
- Extract app name from the message
- Extract replicas if mentioned (default: {CONFIG['default_replicas']})
- Determine port based on app type:
  * Java/Spring Boot apps: 8080
  * Node.js/Express apps: 3000
  * Python/Flask apps: 5000
  * If unclear, use 3000
- Determine env_vars based on app description:
  * If app mentions "blog", "cognito", "dynamodb", "s3": include DYNAMODB_TABLE, S3_BUCKET, COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, PORT, NODE_ENV
  * Otherwise: only include PORT, NODE_ENV
  * Format: {{"PORT": "8080", "NODE_ENV": "production"}}
  * Note: System will populate actual values from CONFIG
- Set needs_build to true
- Use tool_name "deploy_workflow" to trigger full deployment

IMPORTANT: 
- Infer port and env_vars from app name/type (java, node, python, spring, express, flask, blog, sample)
- For blog/sample apps, just indicate the env_vars structure - actual Cognito/DynamoDB values will be populated automatically

For list requests:
- Use list_deployments tool

For status checks:
- Extract app name and use get_deployment_status

For deletions:
- Extract app name and use delete_eks_deployment

Respond ONLY with valid JSON, no other text."""

    # Retry logic with exponential backoff for throttling
    max_retries = 5  # Increased from 3 to 5
    base_delay = 3  # Increased from 2 to 3 seconds
    
    for attempt in range(max_retries):
        try:
            response = bedrock_runtime.invoke_model(
                modelId='global.anthropic.claude-sonnet-4-20250514-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "temperature": 0.1
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            
            # Extract JSON from response (handle markdown code blocks)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            routing_decision = json.loads(content)
            return routing_decision
            
        except Exception as e:
            error_str = str(e)
            # Check if it's a throttling error
            if 'ServiceUnavailableException' in error_str or 'Too many connections' in error_str or 'ThrottlingException' in error_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 3s, 6s, 12s, 24s
                    print(f"Bedrock throttled, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    print(f"Bedrock throttled after {max_retries} attempts, giving up.")
            
            # Non-throttling error or final retry failed
            return {
                "tool_name": "error",
                "arguments": {},
                "reasoning": f"Failed to route command after {max_retries} attempts: {error_str}",
                "needs_build": False
            }
    
    # All retries exhausted
    return {
        "tool_name": "error",
        "arguments": {},
        "reasoning": "Failed to route command: Bedrock service unavailable after retries",
        "needs_build": False
    }

def llm_route_ecs_command(message: str, region: str) -> dict:
    """
    Use LLM to intelligently route ECS commands to the appropriate operation
    
    Args:
        message: User's natural language message
        region: AWS region
        
    Returns:
        Dictionary with operation type, arguments, and reasoning
    """
    
    tools_description = """
Available ECS Operations:

1. deploy
   - Purpose: Deploy a new service to ECS Express Mode
   - Arguments: app_name, region, cpu (string), memory (string), desired_count (int), port (int), env_vars (dict)
   - Use when: User wants to deploy, create, or start a new service
   - Note: Automatically builds and pushes Docker image
   - desired_count: Number of tasks to run (extract from "X tasks", "X replicas", "X instances")
   - port: Application port (Java/Spring Boot typically 8080, Node.js typically 3000, Python/Flask typically 5000)
   - cpu: CPU units (Java apps typically need 1024+, Node.js 512+)
   - memory: Memory in MB (Java apps typically need 2048+, Node.js 1024+)
   - env_vars: Only include if app needs specific AWS services (DynamoDB, S3, Cognito)

2. list
   - Purpose: List ECS services in a region
   - Arguments: region
   - Use when: User wants to see, list, or count services

3. delete
   - Purpose: Delete an ECS service
   - Arguments: service_name, region
   - Use when: User wants to delete, remove, or clean up a service

4. status
   - Purpose: Check CloudFormation stacks
   - Arguments: region
   - Use when: User wants to see stacks or infrastructure status
"""
    
    prompt = f"""You are an intelligent routing assistant for ECS deployment operations. Analyze the user's message and determine which operation to perform.

User Message: "{message}"
Context:
- Region: {region}
- Account ID: {CONFIG['account_id']}
- Default CPU: {CONFIG['default_cpu']}
- Default Memory: {CONFIG['default_memory']}

{tools_description}

Analyze the message and respond with a JSON object containing:
1. "operation": The operation type (deploy, list, delete, status)
2. "arguments": Dictionary of arguments
3. "reasoning": Brief explanation of why you chose this operation

For deployment requests:
- Extract app name from the message
- Determine port based on app type:
  * Java/Spring Boot apps: 8080
  * Node.js/Express apps: 3000
  * Python/Flask apps: 5000
  * If unclear, use 3000
- Determine CPU/memory based on app type:
  * Java apps: cpu=1024, memory=2048 (Java needs more resources)
  * Node.js apps: cpu=512, memory=1024
  * Python apps: cpu=512, memory=1024
  * If user specifies values, use those instead
- Extract desired_count if mentioned (look for "X tasks", "X replicas", "X instances", default: 1)
- Extract region if mentioned
- Determine env_vars based on app description:
  * If app mentions "blog", "cognito", "dynamodb", "s3": include AWS_REGION, DYNAMODB_TABLE, S3_BUCKET, COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, PORT
  * Otherwise: only include AWS_REGION, PORT
  * Format: {{"AWS_REGION": "{region}", "PORT": "8080"}}
  * Note: System will populate actual values from CONFIG

IMPORTANT: 
- If user mentions "5 tasks", "3 replicas", "10 instances", etc., extract the number as desired_count
- Infer port and resources from app name/type (java, node, python, spring, express, flask)
- For blog/sample apps, just indicate the env_vars structure - actual Cognito/DynamoDB values will be populated automatically

Respond ONLY with valid JSON, no other text."""

    # Retry logic with exponential backoff for throttling
    max_retries = 5  # Increased from 3 to 5
    base_delay = 3  # Increased from 2 to 3 seconds
    
    for attempt in range(max_retries):
        try:
            response = bedrock_runtime.invoke_model(
                modelId='global.anthropic.claude-sonnet-4-20250514-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "temperature": 0.1
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            
            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            routing_decision = json.loads(content)
            return routing_decision
            
        except Exception as e:
            error_str = str(e)
            # Check if it's a throttling error
            if 'ServiceUnavailableException' in error_str or 'Too many connections' in error_str or 'ThrottlingException' in error_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 3s, 6s, 12s, 24s
                    print(f"Bedrock throttled, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    print(f"Bedrock throttled after {max_retries} attempts, giving up.")
            
            # Non-throttling error or final retry failed
            return {
                "operation": "error",
                "arguments": {},
                "reasoning": f"Failed to route command after {max_retries} attempts: {error_str}"
            }
    
    # All retries exhausted
    return {
        "operation": "error",
        "arguments": {},
        "reasoning": "Failed to route command: Bedrock service unavailable after retries"
    }

def check_stack_status(stack_name, region):
    """Check CloudFormation stack status and return detailed info"""
    cfn = boto3.client('cloudformation', region_name=region)
    
    try:
        response = cfn.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]
        
        status = stack['StackStatus']
        status_reason = stack.get('StackStatusReason', '')
        
        result = {
            'status': status,
            'reason': status_reason,
            'stack_name': stack_name
        }
        
        # Get stack events for any non-complete status
        if status != 'CREATE_COMPLETE' and status != 'UPDATE_COMPLETE':
            events_response = cfn.describe_stack_events(StackName=stack_name)
            failed_events = []
            all_events = []
            
            for event in events_response['StackEvents'][:20]:  # Last 20 events
                event_info = {
                    'timestamp': event['Timestamp'].isoformat(),
                    'resource': event.get('LogicalResourceId'),
                    'type': event.get('ResourceType'),
                    'status': event.get('ResourceStatus'),
                    'reason': event.get('ResourceStatusReason', '')
                }
                all_events.append(event_info)
                
                if 'FAILED' in event.get('ResourceStatus', ''):
                    failed_events.append(event_info)
            
            result['failed_events'] = failed_events
            result['recent_events'] = all_events
        
        # Get outputs if stack is complete
        if status == 'CREATE_COMPLETE' or status == 'UPDATE_COMPLETE':
            outputs = {}
            for output in stack.get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']
            result['outputs'] = outputs
        
        return result
        
    except cfn.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            return {'status': 'NOT_FOUND', 'stack_name': stack_name}
        return {'status': 'ERROR', 'message': str(e)}

def log_message(operation_id, message, level='info'):
    """Add log message to operation"""
    if operation_id not in operation_logs:
        operation_logs[operation_id] = []
    
    operation_logs[operation_id].append({
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message
    })

def build_and_push_docker_image(app_name, region, app_path=None):
    """Build and push Docker image to ECR"""
    import subprocess
    import os
    
    account_id = CONFIG['account_id']
    
    # Determine app path
    if app_path is None:
        # Try to find the app folder in the workspace root
        workspace_root = '$PROJECT_ROOT'
        potential_paths = [
            f"{workspace_root}/{app_name}",  # Direct folder match
            f"{workspace_root}/sample-application",  # Default fallback
        ]
        
        print(f"DEBUG: Looking for app '{app_name}' in workspace")
        for path in potential_paths:
            dockerfile_path = f"{path}/Dockerfile"
            exists = os.path.exists(path)
            has_dockerfile = os.path.exists(dockerfile_path)
            print(f"DEBUG: Checking {path} - exists: {exists}, has Dockerfile: {has_dockerfile}")
            
            if exists and has_dockerfile:
                app_path = path
                print(f"DEBUG: Selected path: {app_path}")
                break
        
        if app_path is None:
            app_path = CONFIG['app_path']  # Ultimate fallback
            print(f"DEBUG: Using fallback path: {app_path}")
    
    image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{app_name}:latest"
    
    try:
        # Create ECR repository if it doesn't exist
        ecr = boto3.client('ecr', region_name=region)
        try:
            ecr.create_repository(repositoryName=app_name)
        except ecr.exceptions.RepositoryAlreadyExistsException:
            pass
        
        # Get ECR login
        import shlex
        login_cmd = ["aws", "ecr", "get-login-password", "--region", region]
        # Security: login_cmd constructed from static AWS CLI command
        # Security: subprocess.run() uses list arguments (no shell=True) - safe from injection
        login_result = subprocess.run(login_cmd, capture_output=True, text=True)
        if login_result.returncode != 0:
            return {'status': 'error', 'message': f'ECR login failed: {login_result.stderr}'}
        
        # Security: subprocess.run() uses list arguments (no shell=True) - safe from injection
        docker_login = subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", 
             f"{account_id}.dkr.ecr.{region}.amazonaws.com"],
            input=login_result.stdout,
            capture_output=True,
            text=True
        )
        
        if docker_login.returncode != 0:
            return {'status': 'error', 'message': f'Docker login failed: {docker_login.stderr}'}
        
        # Build and push multi-platform image
        # Security: subprocess.run() uses list arguments (no shell=True) - safe from injection
        result = subprocess.run(
            ["docker", "buildx", "build", "--platform", "linux/amd64,linux/arm64", 
             "-t", image_uri, "--push", app_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Fallback: try single platform
            # Security: subprocess.run() uses list arguments (no shell=True) - safe from injection
            result = subprocess.run(
                ["docker", "build", "-t", f"{app_name}:latest", app_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {'status': 'error', 'message': f'Docker build failed: {result.stderr}'}
            
            # Tag and push
            # Security: subprocess.run() uses list arguments (no shell=True) - safe from injection
            subprocess.run(["docker", "tag", f"{app_name}:latest", image_uri], check=True)
            # Security: subprocess.run() uses list arguments (no shell=True) - safe from injection
            result = subprocess.run(
                ["docker", "push", image_uri],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {'status': 'error', 'message': f'Docker push failed: {result.stderr}'}
        
        return {
            'status': 'success',
            'image_uri': image_uri,
            'app_path': app_path,
            'message': f'Successfully built and pushed {image_uri}'
        }
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def invoke_strands_agent(agent_arn, prompt, agent_region='us-west-2'):
    """Invoke ECS agent using Strands protocol"""
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    url = f"https://bedrock-agentcore.{agent_region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    payload = {"prompt": prompt}
    
    request_obj = AWSRequest(
        method='POST',
        url=url,
        data=json.dumps(payload),
        headers={'Content-Type': 'application/json'}
    )
    
    session = boto3.Session()
    credentials = session.get_credentials()
    SigV4Auth(credentials, "bedrock-agentcore", agent_region).add_auth(request_obj)
    
    response = requests.post(
        url,
        data=request_obj.body,
        headers=dict(request_obj.headers)
    )
    
    if response.status_code == 200:
        result = response.json()
        message = result.get('message', {})
        content = message.get('content', [])
        if content:
            return content[0].get('text', str(result))
    return f"Error: {response.text}"

def invoke_mcp_tool(agent_arn, tool_name, arguments, agent_region='us-west-2'):
    """Invoke EKS agent using MCP protocol"""
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    url = f"https://bedrock-agentcore.{agent_region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    request_obj = AWSRequest(
        method='POST',
        url=url,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
    )
    
    session = boto3.Session()
    credentials = session.get_credentials()
    SigV4Auth(credentials, "bedrock-agentcore", agent_region).add_auth(request_obj)
    
    response = requests.post(
        url,
        data=request_obj.body,
        headers=dict(request_obj.headers)
    )
    
    if response.status_code == 200:
        lines = response.text.strip().split('\n')
        for line in lines:
            if line.startswith('data: '):
                data = line[6:]
                try:
                    result = json.loads(data)
                    if 'result' in result and 'content' in result['result']:
                        content = result['result']['content']
                        if content and len(content) > 0:
                            text = content[0].get('text', '')
                            try:
                                return json.loads(text)
                            except json.JSONDecodeError:
                                return {"status": "success", "message": text}
                    return result
                except json.JSONDecodeError:
                    continue
        
        # If we got here, no valid data lines were found
        return {"status": "error", "message": f"No valid MCP response found. Raw response: {response.text[:500]}"}
    
    return {"status": "error", "message": f"HTTP {response.status_code}: {response.text[:500]}"}

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', config=CONFIG)

@app.route('/api/ecs/list', methods=['POST'])
def ecs_list_services():
    """List ECS services"""
    data = request.json
    region = data.get('region', 'us-west-2')
    
    try:
        prompt = f"List all ECS services in {region}"
        result = invoke_strands_agent(CONFIG['ecs_agent_arn'], prompt, CONFIG['agent_region'])
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/ecs/deploy', methods=['POST'])
def ecs_deploy():
    """Deploy to ECS with full workflow (ECR + build + deploy)"""
    data = request.json
    service_name = data.get('service_name', f"blog-app-{int(time.time())}")
    app_name = data.get('app_name', 'blog-app')
    region = data.get('region', 'us-west-2')
    cpu = data.get('cpu', CONFIG['default_cpu'])
    memory = data.get('memory', CONFIG['default_memory'])
    port = data.get('port', int(CONFIG['app_port']))
    env_vars = data.get('env_vars', {})
    
    try:
        # Step 1: Create ECR repository
        account_id = CONFIG['account_id']
        image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{app_name}:latest"
        
        prompt = f"""I need to deploy a containerized application to ECS Express Mode in {region}. Let's do this step by step:

Step 1: First, create an ECR repository named {app_name} in {region} if it doesn't exist.

Step 2: After the repository is ready, I will build and push the Docker image locally to {image_uri}.

Step 3: Then deploy the image {image_uri} to ECS Express Mode in {region} with these parameters:
- service_name: {service_name}
- cpu: {cpu}
- memory: {memory}
- port: {port}
- region: {region}
- environment_variables: {json.dumps(env_vars)}

Let's start with Step 1 - create the ECR repository."""
        
        result = invoke_strands_agent(CONFIG['ecs_agent_arn'], prompt, CONFIG['agent_region'])
        
        return jsonify({
            'status': 'success', 
            'result': result, 
            'service_name': service_name,
            'image_uri': image_uri,
            'next_steps': f"""
Next steps to complete deployment:

1. Build and push Docker image locally:
   cd {CONFIG['app_path']}
   aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com
   docker buildx build --platform linux/amd64,linux/arm64 -t {image_uri} --push .

2. After image is pushed, click "Continue Deployment" to deploy to ECS.
"""
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/ecs/delete', methods=['POST'])
def ecs_delete():
    """Delete ECS service"""
    data = request.json
    service_name = data.get('service_name')
    region = data.get('region', 'us-west-2')
    
    try:
        # Security: This is an LLM prompt, not a SQL query - no injection risk
        prompt = f"Delete the ECS service named {service_name} in region {region}"
        result = invoke_strands_agent(CONFIG['ecs_agent_arn'], prompt, CONFIG['agent_region'])
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/eks/status', methods=['POST'])
def eks_status():
    """Check EKS deployment status"""
    data = request.json
    cluster_name = data.get('cluster_name')
    app_name = data.get('app_name')
    region = data.get('region')
    
    try:
        result = invoke_mcp_tool(
            CONFIG['eks_agent_arn'],
            'get_deployment_status',
            {
                'cluster_name': cluster_name,
                'app_name': app_name,
                'region': region
            },
            CONFIG['agent_region']
        )
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/eks/delete', methods=['POST'])
def eks_delete():
    """Delete EKS deployment"""
    data = request.json
    cluster_name = data.get('cluster_name')
    app_name = data.get('app_name')
    region = data.get('region')
    
    try:
        result = invoke_mcp_tool(
            CONFIG['eks_agent_arn'],
            'delete_eks_deployment',
            {
                'cluster_name': cluster_name,
                'app_name': app_name,
                'region': region,
                'delete_service': True,
                'delete_service_account': True
            },
            CONFIG['agent_region']
        )
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/eks/deploy', methods=['POST'])
def eks_deploy():
    """Deploy to EKS with full workflow (ECR + build + deploy)"""
    data = request.json
    cluster_name = data.get('cluster_name')
    app_name = data.get('app_name')
    image_name = data.get('image_name', app_name)
    region = data.get('region')
    port = data.get('port', int(CONFIG['app_port']))
    replicas = data.get('replicas', CONFIG['default_replicas'])
    env_vars = data.get('env_vars', {})
    role_arn = data.get('role_arn')
    service_account_name = data.get('service_account_name', f"{app_name}-sa")
    s3_bucket = data.get('s3_bucket')
    dynamodb_table = data.get('dynamodb_table')
    
    try:
        account_id = CONFIG['account_id']
        image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{image_name}:latest"
        
        # Build conversational prompt for full workflow
        prompt_parts = [
            f"I need to deploy a containerized application to EKS cluster '{cluster_name}' in {region}. Let's do this step by step:",
            "",
            "Step 1: Setup OIDC provider for the cluster if not already done.",
            ""
        ]
        
        if not role_arn:
            prompt_parts.extend([
                f"Step 2: Create an IRSA role for app '{app_name}' with access to:",
                f"  - S3 bucket: {s3_bucket}",
                f"  - DynamoDB table: {dynamodb_table}",
                ""
            ])
            step_num = 3
        else:
            prompt_parts.append(f"Step 2: Use existing IRSA role: {role_arn}")
            prompt_parts.append("")
            step_num = 3
        
        prompt_parts.extend([
            f"Step {step_num}: After IRSA is ready, I will build and push the Docker image locally to {image_uri}.",
            "",
            f"Step {step_num + 1}: Then deploy to EKS with these parameters:",
            f"  - cluster: {cluster_name}",
            f"  - app_name: {app_name}",
            f"  - image_uri: {image_uri}",
            f"  - port: {port}",
            f"  - replicas: {replicas}",
            f"  - region: {region}",
            f"  - role_arn: {role_arn if role_arn else 'from Step 2'}",
            f"  - service_account_name: {service_account_name}",
            f"  - env_vars: {json.dumps(env_vars)}",
            "",
            "Let's start with Step 1 - setup OIDC provider."
        ])
        
        prompt = "\n".join(prompt_parts)
        
        result = invoke_mcp_tool(
            CONFIG['eks_agent_arn'],
            'setup_oidc_provider',
            {
                'cluster_name': cluster_name,
                'region': region
            },
            CONFIG['agent_region']
        )
        
        return jsonify({
            'status': 'success',
            'result': result,
            'image_uri': image_uri,
            'next_steps': f"""
Next steps to complete deployment:

1. {'Create IRSA role (click button below)' if not role_arn else 'IRSA role already provided'}

2. Build and push Docker image locally:
   cd {CONFIG['app_path']}
   aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com
   && docker buildx build --platform linux/amd64,linux/arm64 -t {image_uri} --push .

3. After image is pushed, click "Continue Deployment" to deploy to EKS.
"""
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/eks/continue-deploy', methods=['POST'])
def eks_continue_deploy():
    """Continue EKS deployment after image is pushed"""
    data = request.json
    cluster_name = data.get('cluster_name')
    app_name = data.get('app_name')
    image_uri = data.get('image_uri')
    region = data.get('region')
    port = data.get('port', int(CONFIG['app_port']))
    replicas = data.get('replicas', CONFIG['default_replicas'])
    env_vars = data.get('env_vars', {})
    role_arn = data.get('role_arn')
    service_account_name = data.get('service_account_name', f"{app_name}-sa")
    
    try:
        result = invoke_mcp_tool(
            CONFIG['eks_agent_arn'],
            'deploy_to_eks_with_irsa',
            {
                'cluster_name': cluster_name,
                'app_name': app_name,
                'image_uri': image_uri,
                'port': port,
                'replicas': replicas,
                'env_vars': env_vars,
                'region': region,
                'role_arn': role_arn,
                'service_account_name': service_account_name
            },
            CONFIG['agent_region']
        )
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/eks/setup-oidc', methods=['POST'])
def eks_setup_oidc():
    """Setup OIDC provider for EKS"""
    data = request.json
    cluster_name = data.get('cluster_name')
    region = data.get('region')
    
    try:
        result = invoke_mcp_tool(
            CONFIG['eks_agent_arn'],
            'setup_oidc_provider',
            {
                'cluster_name': cluster_name,
                'region': region
            },
            CONFIG['agent_region']
        )
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/eks/create-irsa', methods=['POST'])
def eks_create_irsa():
    """Create IRSA role for EKS"""
    data = request.json
    cluster_name = data.get('cluster_name')
    app_name = data.get('app_name')
    region = data.get('region')
    s3_bucket = data.get('s3_bucket')
    dynamodb_table = data.get('dynamodb_table')
    
    try:
        result = invoke_mcp_tool(
            CONFIG['eks_agent_arn'],
            'create_irsa_role',
            {
                'cluster_name': cluster_name,
                'app_name': app_name,
                'region': region,
                's3_bucket': s3_bucket,
                'dynamodb_table': dynamodb_table
            },
            CONFIG['agent_region']
        )
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/ecs/continue-deploy', methods=['POST'])
def ecs_continue_deploy():
    """Continue ECS deployment after image is pushed"""
    data = request.json
    service_name = data.get('service_name')
    image_uri = data.get('image_uri')
    region = data.get('region', 'us-west-2')
    cpu = data.get('cpu', CONFIG['default_cpu'])
    memory = data.get('memory', CONFIG['default_memory'])
    port = data.get('port', int(CONFIG['app_port']))
    env_vars = data.get('env_vars', {})
    
    try:
        prompt = f"""The Docker image has been built and pushed to {image_uri}.

Now deploy this image to ECS Express Mode in {region} with these parameters:
- service_name: {service_name}
- cpu: {cpu}
- memory: {memory}
- port: {port}
- region: {region}
- environment_variables: {json.dumps(env_vars)}

Make sure to pass the environment_variables parameter to the deploy_ecs_express_service tool."""
        
        result = invoke_strands_agent(CONFIG['ecs_agent_arn'], prompt, CONFIG['agent_region'])
        return jsonify({'status': 'success', 'result': result, 'service_name': service_name})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/logs/<operation_id>')
def get_logs(operation_id):
    """Get operation logs"""
    logs = operation_logs.get(operation_id, [])
    return jsonify({'logs': logs})

@app.route('/api/ecs/chat', methods=['POST'])
def ecs_chat():
    """Chat with ECS agent using LLM-based intelligent routing"""
    data = request.json
    message = data.get('message')
    region = data.get('region', 'us-west-2')
    
    try:
        # Use LLM to route the command
        routing = llm_route_ecs_command(message, region)
        
        # Debug: Log the routing decision
        print(f"ECS LLM Routing Decision: {json.dumps(routing, indent=2)}")
        
        operation = routing.get('operation')
        arguments = routing.get('arguments', {})
        reasoning = routing.get('reasoning', '')
        
        # Validate routing response
        if not operation:
            return jsonify({
                'status': 'error',
                'result': f'LLM failed to determine operation. Routing response: {json.dumps(routing, indent=2)}'
            })
        
        response_text = f"🤖 **Understanding your request...**\n\n"
        response_text += f"💡 {reasoning}\n\n"
        
        # Handle deployment
        if operation == 'deploy':
            app_name = arguments.get('app_name')
            cpu = arguments.get('cpu', CONFIG['default_cpu'])
            memory = arguments.get('memory', CONFIG['default_memory'])
            desired_count = arguments.get('desired_count', 1)
            deploy_region = arguments.get('region', region)
            app_port = arguments.get('port', CONFIG['app_port'])  # LLM determines port
            env_vars = arguments.get('env_vars', {
                "AWS_REGION": deploy_region,
                "PORT": str(app_port)
            })  # LLM determines env vars
            
            # Enrich env_vars with actual CONFIG values for blog apps
            if 'blog' in app_name.lower() or 'sample' in app_name.lower():
                env_vars.update({
                    'AWS_REGION': deploy_region,
                    'DYNAMODB_TABLE': CONFIG['dynamodb_table'],
                    'S3_BUCKET': f"{CONFIG['s3_bucket_prefix']}-{CONFIG['account_id']}-{deploy_region}",
                    'COGNITO_USER_POOL_ID': CONFIG['cognito_user_pool_id'],
                    'COGNITO_CLIENT_ID': CONFIG['cognito_client_id'],
                    'PORT': str(app_port)
                })
                print(f"ECS Enriched env_vars for {app_name}: {json.dumps(env_vars, indent=2)}")
            
            if not app_name:
                return jsonify({
                    'status': 'error',
                    'result': 'Could not determine app name from your message. Please specify the app name.'
                })
            
            service_name = f"{app_name}-{int(time.time())}"
            image_uri = f"{CONFIG['account_id']}.dkr.ecr.{deploy_region}.amazonaws.com/{app_name}:latest"
            
            response_text += f"🚀 **ECS Deployment Workflow for {app_name}**\n\n"
            response_text += f"Starting automated deployment to {deploy_region}...\n"
            response_text += f"CPU: {cpu}, Memory: {memory} MB, Tasks: {desired_count}, Port: {app_port}\n\n"
            
            # Step 1: Create ECR repository
            response_text += "**Step 1: Create ECR Repository**\n"
            ecr = boto3.client('ecr', region_name=deploy_region)
            try:
                ecr.create_repository(repositoryName=app_name)
                response_text += f"✅ Created ECR repository: {app_name}\n"
            except ecr.exceptions.RepositoryAlreadyExistsException:
                response_text += f"✅ ECR repository already exists: {app_name}\n"
            
            # Step 2: Build and push image
            response_text += f"\n**Step 2: Build and Push Docker Image**\n"
            
            build_result = build_and_push_docker_image(app_name, deploy_region)
            
            if build_result['status'] != 'success':
                response_text += f"❌ Build failed: {build_result['message']}\n"
                return jsonify({'status': 'error', 'result': response_text})
            
            response_text += f"🔨 Built from: {build_result.get('app_path', 'unknown')}\n"
            response_text += f"✅ Image built and pushed: {build_result['image_uri']}\n"
            
            # Step 3: Deploy to ECS
            response_text += f"\n**Step 3: Deploy to ECS Express Mode**\n"
            response_text += f"🚀 Deploying service {service_name} with {desired_count} task(s)...\n"
            
            # Use env_vars from LLM (already includes PORT)
            prompt = f"""Deploy the image {image_uri} to ECS Express Mode in {deploy_region}.
Use these parameters:
- service_name: {service_name}
- cpu: {cpu}
- memory: {memory}
- port: {app_port}
- region: {deploy_region}
- desired_count: {desired_count}
- environment_variables: {json.dumps(env_vars)}

Make sure to pass the environment_variables and desired_count parameters to the deploy_ecs_express_service tool."""
            
            result = invoke_strands_agent(CONFIG['ecs_agent_arn'], prompt, CONFIG['agent_region'])
            
            response_text += f"\n✅ **Deployment Initiated!**\n\n"
            response_text += f"Service: {service_name}\n"
            response_text += f"Region: {deploy_region}\n"
            response_text += f"CPU: {cpu}, Memory: {memory} MB\n"
            response_text += f"Desired Tasks: {desired_count}\n"
            response_text += f"Port: {app_port}\n"
            response_text += f"Image: {image_uri}\n\n"
            response_text += f"Agent response:\n{result}\n\n"
            
            # Check stack status
            stack_name = f"ecs-express-{service_name}"
            response_text += f"**Checking deployment status...**\n\n"
            
            # Intentional delay: Rate limiting for API calls
            time.sleep(5)  # Wait a bit for stack to be created
            
            stack_status = check_stack_status(stack_name, deploy_region)
            
            if stack_status['status'] == 'CREATE_IN_PROGRESS':
                response_text += f"⏳ Stack is being created: {stack_name}\n"
                response_text += f"Status: {stack_status['status']}\n"
                response_text += f"\n💡 Monitor progress in CloudFormation console or check back in a few minutes.\n"
            elif 'FAILED' in stack_status['status'] or 'ROLLBACK' in stack_status['status']:
                response_text += f"❌ Stack creation failed: {stack_status['status']}\n"
                if stack_status.get('reason'):
                    response_text += f"Reason: {stack_status['reason']}\n"
                
                if stack_status.get('failed_events'):
                    response_text += f"\n**Failed Resources:**\n"
                    for event in stack_status['failed_events']:
                        response_text += f"- {event['resource']} ({event['type']})\n"
                        response_text += f"  Status: {event['status']}\n"
                        response_text += f"  Reason: {event['reason']}\n\n"
                
                if stack_status.get('recent_events'):
                    response_text += f"\n**Recent Events:**\n"
                    for event in stack_status['recent_events'][:5]:
                        response_text += f"- [{event['timestamp']}] {event['resource']}: {event['status']}\n"
                        if event['reason']:
                            response_text += f"  {event['reason']}\n"
                
            elif stack_status['status'] == 'CREATE_COMPLETE':
                response_text += f"✅ Stack created successfully!\n"
                if stack_status.get('outputs'):
                    response_text += f"\n**Endpoints:**\n"
                    for key, value in stack_status['outputs'].items():
                        response_text += f"- {key}: {value}\n"
            
            return jsonify({'status': 'success', 'result': response_text})
        
        # Handle list operation
        elif operation == 'list':
            list_region = arguments.get('region', region)
            prompt = f"List all ECS services in {list_region}"
            result = invoke_strands_agent(CONFIG['ecs_agent_arn'], prompt, CONFIG['agent_region'])
            
            response_text += f"📋 **ECS Services in {list_region}**\n\n"
            response_text += result
            return jsonify({'status': 'success', 'result': response_text})
        
        # Handle delete operation
        elif operation == 'delete':
            service_name = arguments.get('service_name')
            delete_region = arguments.get('region', region)
            
            if not service_name:
                return jsonify({
                    'status': 'error',
                    'result': 'Could not determine service name from your message. Please specify the service name.'
                })
            
            # Security: This is an LLM prompt, not a SQL query - no injection risk
            prompt = f"Delete the ECS service named {service_name} in region {delete_region}"
            result = invoke_strands_agent(CONFIG['ecs_agent_arn'], prompt, CONFIG['agent_region'])
            
            response_text += f"🗑️ **Deleting Service {service_name}**\n\n"
            response_text += result
            return jsonify({'status': 'success', 'result': response_text})
        
        # Handle status operation
        elif operation == 'status':
            status_region = arguments.get('region', region)
            
            cfn = boto3.client('cloudformation', region_name=status_region)
            response = cfn.list_stacks(
                StackStatusFilter=[
                    'CREATE_COMPLETE',
                    'UPDATE_COMPLETE',
                    'DELETE_IN_PROGRESS'
                ]
            )
            
            ecs_stacks = [
                {
                    'name': stack['StackName'],
                    'status': stack['StackStatus'],
                    'created': stack['CreationTime'].isoformat()
                }
                for stack in response['StackSummaries']
                if 'ecs-express' in stack['StackName']
            ]
            
            response_text += f"📊 **CloudFormation Stacks in {status_region}**\n\n"
            response_text += f"Total ECS stacks: {len(ecs_stacks)}\n\n"
            
            if ecs_stacks:
                for stack in ecs_stacks:
                    response_text += f"• **{stack['name']}**\n"
                    response_text += f"  Status: {stack['status']}\n"
                    response_text += f"  Created: {stack['created']}\n\n"
            else:
                response_text += "No ECS stacks found.\n"
            
            return jsonify({'status': 'success', 'result': response_text})
        
        # Handle error
        elif operation == 'error':
            return jsonify({'status': 'error', 'result': reasoning})
        
        # Unknown operation
        else:
            return jsonify({
                'status': 'error',
                'result': f'Unknown operation: {operation}. The LLM suggested an operation that is not implemented.'
            })
        
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'message': f"{str(e)}\n\n{traceback.format_exc()}"})

@app.route('/api/eks/chat', methods=['POST'])
def eks_chat():
    """Chat with EKS agent using LLM-based intelligent routing"""
    data = request.json
    message = data.get('message')
    cluster = data.get('cluster', 'ec2-eks-migration')
    region = data.get('region', 'eu-north-1')
    
    try:
        # Use LLM to route the command
        routing = llm_route_eks_command(message, cluster, region)
        
        # Debug: Log the routing decision
        print(f"LLM Routing Decision: {json.dumps(routing, indent=2)}")
        
        tool_name = routing.get('tool_name')
        arguments = routing.get('arguments', {})
        reasoning = routing.get('reasoning', '')
        needs_build = routing.get('needs_build', False)
        
        # Validate routing response
        if not tool_name:
            return jsonify({
                'status': 'error',
                'result': f'LLM failed to determine tool. Routing response: {json.dumps(routing, indent=2)}'
            })
        
        response_text = f"🤖 **Understanding your request...**\n\n"
        response_text += f"💡 {reasoning}\n\n"
        
        # Handle deployment workflow
        if tool_name == 'deploy_workflow':
            app_name = arguments.get('app_name')
            replicas = arguments.get('replicas', CONFIG['default_replicas'])
            app_port = arguments.get('port', int(CONFIG['app_port']))  # LLM determines port
            env_vars = arguments.get('env_vars', {
                'PORT': str(app_port),
                'NODE_ENV': 'production'
            })  # LLM determines env vars
            
            # Enrich env_vars with actual CONFIG values for blog apps
            if 'blog' in app_name.lower() or 'sample' in app_name.lower():
                env_vars.update({
                    'AWS_REGION': region,
                    'DYNAMODB_TABLE': CONFIG['dynamodb_table'],
                    'S3_BUCKET': f"{CONFIG['s3_bucket_prefix']}-{CONFIG['account_id']}-{region}",
                    'COGNITO_USER_POOL_ID': CONFIG['cognito_user_pool_id'],
                    'COGNITO_CLIENT_ID': CONFIG['cognito_client_id'],
                    'PORT': str(app_port),
                    'NODE_ENV': 'production'
                })
                print(f"EKS Enriched env_vars for {app_name}: {json.dumps(env_vars, indent=2)}")
            
            # Ensure replicas is an integer
            if isinstance(replicas, str):
                try:
                    replicas = int(replicas)
                except ValueError:
                    replicas = CONFIG['default_replicas']
            
            # Ensure port is an integer
            if isinstance(app_port, str):
                try:
                    app_port = int(app_port)
                except ValueError:
                    app_port = int(CONFIG['app_port'])
            
            if not app_name:
                return jsonify({
                    'status': 'error',
                    'result': 'Could not determine app name from your message. Please specify the app name.'
                })
            
            image_uri = f"{CONFIG['account_id']}.dkr.ecr.{region}.amazonaws.com/{app_name}:latest"
            
            response_text += f"🚀 **EKS Deployment Workflow for {app_name}**\n\n"
            response_text += f"Starting automated deployment to {cluster} in {region}...\n"
            response_text += f"Replicas: {replicas}, Port: {app_port}\n\n"
            
            # Step 1: Setup OIDC
            response_text += "**Step 1: Setup OIDC Provider**\n"
            oidc_result = invoke_mcp_tool(
                CONFIG['eks_agent_arn'],
                'setup_oidc_provider',
                {'cluster_name': cluster, 'region': region},
                CONFIG['agent_region']
            )
            
            if isinstance(oidc_result, dict):
                if oidc_result.get('status') in ['exists', 'created']:
                    response_text += f"✅ OIDC Provider: {oidc_result.get('status')}\n"
                else:
                    response_text += f"⚠️ OIDC: {oidc_result.get('message', 'Unknown status')}\n"
            
            # Step 2: Create IRSA role
            response_text += f"\n**Step 2: Create IRSA Role**\n"
            irsa_result = invoke_mcp_tool(
                CONFIG['eks_agent_arn'],
                'create_irsa_role',
                {
                    'cluster_name': cluster,
                    'app_name': app_name,
                    'region': region,
                    's3_bucket': f"{CONFIG['s3_bucket_prefix']}-{CONFIG['account_id']}-{region}",
                    'dynamodb_table': CONFIG['dynamodb_table']
                },
                CONFIG['agent_region']
            )
            
            role_arn = None
            if isinstance(irsa_result, dict):
                if irsa_result.get('status') in ['created', 'updated']:
                    role_arn = irsa_result.get('role_arn')
                    response_text += f"✅ IRSA Role: {role_arn}\n"
                else:
                    response_text += f"⚠️ IRSA: {irsa_result.get('message', 'Unknown status')}\n"
                    return jsonify({'status': 'error', 'result': response_text})
            
            # Step 3: Build and push image
            response_text += f"\n**Step 3: Build and Push Docker Image**\n"
            
            build_result = build_and_push_docker_image(app_name, region)
            
            if build_result['status'] != 'success':
                response_text += f"❌ Build failed: {build_result['message']}\n"
                return jsonify({'status': 'error', 'result': response_text})
            
            response_text += f"🔨 Built from: {build_result.get('app_path', 'unknown')}\n"
            response_text += f"✅ Image built and pushed: {build_result['image_uri']}\n"
            
            # Step 4: Deploy to EKS
            response_text += f"\n**Step 4: Deploy to EKS**\n"
            response_text += f"🚀 Deploying to Kubernetes...\n"
            
            # Use env_vars from LLM
            deploy_result = invoke_mcp_tool(
                CONFIG['eks_agent_arn'],
                'deploy_to_eks_with_irsa',
                {
                    'cluster_name': cluster,
                    'app_name': app_name,
                    'image_uri': image_uri,
                    'port': app_port,
                    'replicas': replicas,
                    'env_vars': env_vars,
                    'region': region,
                    'role_arn': role_arn,
                    'service_account_name': f'{app_name}-sa'
                },
                CONFIG['agent_region']
            )
            
            # Debug: Log the deploy result
            print(f"Deploy Result: {json.dumps(deploy_result, indent=2)}")
            
            if isinstance(deploy_result, dict):
                if deploy_result.get('status') == 'success':
                    response_text += f"\n✅ **Deployment Complete!**\n\n"
                    if deploy_result.get('endpoint'):
                        response_text += f"🌐 Endpoint: {deploy_result['endpoint']}\n"
                    response_text += f"📦 App: {app_name}\n"
                    response_text += f"🔢 Replicas: {deploy_result.get('replicas', replicas)}\n"
                    response_text += f"\n💡 Access your app at the endpoint above (may take 2-3 minutes for LoadBalancer to be ready)\n"
                    return jsonify({'status': 'success', 'result': response_text})
                else:
                    error_msg = deploy_result.get('message', str(deploy_result))
                    response_text += f"❌ Deployment failed: {error_msg}\n"
                    return jsonify({'status': 'error', 'result': response_text})
            else:
                response_text += f"❌ Unexpected response type: {type(deploy_result).__name__}\n"
                response_text += f"Response: {str(deploy_result)[:500]}\n"
                return jsonify({'status': 'error', 'result': response_text})
        
        # Handle other tool calls
        elif tool_name == 'list_deployments':
            result = invoke_mcp_tool(
                CONFIG['eks_agent_arn'],
                tool_name,
                arguments,
                CONFIG['agent_region']
            )
            
            if isinstance(result, dict):
                if result.get('status') == 'success':
                    deployments = result.get('deployments', [])
                    count = result.get('count', 0)
                    response_text += f"📋 **Deployments in {cluster}**\n\n"
                    response_text += f"Total: {count} deployment(s)\n\n"
                    if deployments:
                        for dep in deployments:
                            response_text += f"• **{dep.get('name', 'unknown')}**\n"
                            response_text += f"  Replicas: {dep.get('replicas', 0)} (Ready: {dep.get('ready', 0)})\n"
                            if dep.get('created'):
                                response_text += f"  Created: {dep['created']}\n"
                            response_text += "\n"
                    else:
                        response_text += "No deployments found.\n"
                    return jsonify({'status': 'success', 'result': response_text})
                else:
                    return jsonify({'status': 'error', 'result': result.get('message', 'Failed to list deployments')})
            else:
                return jsonify({'status': 'error', 'result': f'Unexpected response: {str(result)}'})
        
        elif tool_name in ['get_deployment_status', 'delete_eks_deployment', 'setup_oidc_provider', 'create_irsa_role']:
            result = invoke_mcp_tool(
                CONFIG['eks_agent_arn'],
                tool_name,
                arguments,
                CONFIG['agent_region']
            )
            
            if isinstance(result, dict):
                response_text += f"**Result:**\n\n"
                response_text += json.dumps(result, indent=2)
                return jsonify({'status': 'success', 'result': response_text})
            else:
                return jsonify({'status': 'error', 'result': f'Unexpected response: {str(result)}'})
        
        elif tool_name == 'error':
            return jsonify({'status': 'error', 'result': reasoning})
        
        else:
            return jsonify({
                'status': 'error',
                'result': f'Unknown tool: {tool_name}. The LLM suggested a tool that is not implemented.'
            })
        
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'message': f"{str(e)}\n\n{traceback.format_exc()}"})

@app.route('/api/cloudformation/stacks', methods=['POST'])
def list_cfn_stacks():
    """List CloudFormation stacks"""
    data = request.json
    region = data.get('region', 'us-west-2')
    
    try:
        cfn = boto3.client('cloudformation', region_name=region)
        response = cfn.list_stacks(
            StackStatusFilter=[
                'CREATE_COMPLETE',
                'CREATE_IN_PROGRESS',
                'UPDATE_COMPLETE',
                'UPDATE_IN_PROGRESS',
                'ROLLBACK_COMPLETE',
                'ROLLBACK_IN_PROGRESS',
                'CREATE_FAILED',
                'DELETE_IN_PROGRESS'
            ]
        )
        
        ecs_stacks = [
            {
                'name': stack['StackName'],
                'status': stack['StackStatus'],
                'created': stack['CreationTime'].isoformat()
            }
            for stack in response['StackSummaries']
            if 'ecs-express' in stack['StackName']
        ]
        
        return jsonify({'status': 'success', 'stacks': ecs_stacks})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/cloudformation/stack-status', methods=['POST'])
def get_stack_status():
    """Get detailed status of a specific CloudFormation stack"""
    data = request.json
    stack_name = data.get('stack_name')
    region = data.get('region', 'us-west-2')
    
    if not stack_name:
        return jsonify({'status': 'error', 'message': 'stack_name is required'})
    
    try:
        result = check_stack_status(stack_name, region)
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='127.0.0.1', port=5001)
