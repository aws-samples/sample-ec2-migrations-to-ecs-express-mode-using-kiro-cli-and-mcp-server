#!/usr/bin/env python3
"""
Deploy sample-application to EKS using V2 Agent (boto3-based)
Hybrid approach: Use V2 agent for AWS operations, local tools for K8s
"""

import boto3
import json
import time
import subprocess as sp
from pathlib import Path
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

# Configuration
AGENT_ARN = 'arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/eks_deployment_agent-bJq2whDHLA'
AGENT_REGION = 'us-west-2'
CLUSTER_NAME = 'ec2-eks-migration'
REGION = 'eu-north-1'
APP_NAME = 'blog-app-eks-v3'
IMAGE_NAME = 'blog-app-eks-v3'
APP_PATH = '$PROJECT_ROOT/sample-application'
PORT = 3000
REPLICAS = 2
S3_BUCKET = 'blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1'
DYNAMODB_TABLE = 'blog-posts'
COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', 'your-user-pool-id')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', 'your-client-id')
NODE_ENV = 'production'

def make_signed_request(url, method='POST', data=None):
    """Make a signed request to the MCP endpoint using SigV4"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method=method,
        url=url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', AGENT_REGION).add_auth(request)
    
    response = requests.request(
        method=request.method,
        url=request.url,
        headers=dict(request.headers),
        data=request.body
    )
    
    return response

def call_mcp_tool(tool_name, arguments):
    """Call an MCP tool and return the result"""
    encoded_arn = AGENT_ARN.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.{AGENT_REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    print(f"\n🔧 Calling MCP tool: {tool_name}")
    
    try:
        response = make_signed_request(mcp_url, data=json.dumps(mcp_request))
        
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
                                    tool_result = json.loads(text)
                                    return tool_result
                                except json.JSONDecodeError:
                                    return {"status": "success", "message": text}
                        return result
                    except json.JSONDecodeError:
                        continue
            
            return {"status": "error", "message": "Could not parse response"}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def build_and_push_image_local(app_path, image_name, region, account_id):
    """Build and push Docker image locally (fallback)"""
    print(f"\n🔧 Building and pushing Docker image locally...")
    
    # Verify Dockerfile
    dockerfile_path = Path(app_path) / "Dockerfile"
    if not dockerfile_path.exists():
        print(f"   ❌ Dockerfile not found at {dockerfile_path}")
        return {'status': 'error', 'message': 'Dockerfile not found'}
    
    ecr = boto3.client('ecr', region_name=region)
    ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{image_name}"
    
    # Create ECR repository
    try:
        ecr.create_repository(repositoryName=image_name)
        print(f"   ✅ Created ECR repository: {image_name}")
    except ecr.exceptions.RepositoryAlreadyExistsException:
        print(f"   ✅ ECR repository already exists")
    
    # Get ECR login
    auth = ecr.get_authorization_token()
    token = auth['authorizationData'][0]['authorizationToken']
    endpoint = auth['authorizationData'][0]['proxyEndpoint']
    
    # Docker login
    import base64
    username, password = base64.b64decode(token).decode().split(':')
    sp.run(
        ['docker', 'login', '--username', username, '--password-stdin', endpoint],
        input=password.encode(),
        check=True,
        capture_output=True
    )
    print(f"   ✅ Logged in to ECR")
    
    # Build image
    print(f"   🔨 Building image...")
    sp.run(
        ['docker', 'build', '--platform', 'linux/amd64', '-t', image_name, app_path],
        check=True
    )
    print(f"   ✅ Built image")
    
    # Tag and push
    sp.run(['docker', 'tag', image_name, f"{ecr_uri}:latest"], check=True)
    print(f"   📤 Pushing image to ECR...")
    sp.run(['docker', 'push', f"{ecr_uri}:latest"], check=True)
    print(f"   ✅ Pushed image: {ecr_uri}:latest")
    
    return {
        'status': 'success',
        'image_uri': f"{ecr_uri}:latest"
    }

def deploy_to_eks_local(cluster_name, app_name, image_uri, port, replicas, env_vars, region, role_arn, service_account_name):
    """Deploy to EKS using local kubectl (fallback)"""
    print(f"\n🔧 Deploying to EKS using local kubectl...")
    
    # Update kubeconfig
    sp.run(
        ['aws', 'eks', 'update-kubeconfig', '--name', cluster_name, '--region', region],
        check=True,
        capture_output=True
    )
    print(f"   ✅ Updated kubeconfig")
    
    # Prepare environment variables
    env_list = [{"name": k, "value": v} for k, v in env_vars.items()]
    env_list.extend([
        {"name": "AWS_REGION", "value": region},
        {"name": "AWS_SDK_LOAD_CONFIG", "value": "1"}
    ])
    
    # Create manifests
    import yaml
    
    service_account = {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {
            "name": service_account_name,
            "annotations": {
                "eks.amazonaws.com/role-arn": role_arn
            }
        }
    }
    
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": app_name, "labels": {"app": app_name}},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": app_name}},
            "template": {
                "metadata": {"labels": {"app": app_name}},
                "spec": {
                    "serviceAccountName": service_account_name,
                    "containers": [{
                        "name": app_name,
                        "image": image_uri,
                        "ports": [{"containerPort": port}],
                        "env": env_list,
                        "resources": {
                            "requests": {"cpu": "250m", "memory": "512Mi"},
                            "limits": {"cpu": "500m", "memory": "1Gi"}
                        }
                    }]
                }
            }
        }
    }
    
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": app_name,
            "annotations": {
                "service.beta.kubernetes.io/aws-load-balancer-type": "external",
                "service.beta.kubernetes.io/aws-load-balancer-nlb-target-type": "ip",
                "service.beta.kubernetes.io/aws-load-balancer-scheme": "internet-facing"
            }
        },
        "spec": {
            "type": "LoadBalancer",
            "selector": {"app": app_name},
            "ports": [{"port": 80, "targetPort": port}]
        }
    }
    
    # Apply manifests
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump_all([service_account, deployment, service], f)
        deploy_file = f.name
    
    try:
        sp.run(['kubectl', 'apply', '-f', deploy_file], check=True, capture_output=True)
        print(f"   ✅ Applied Kubernetes manifests")
        
        # Wait for deployment
        print(f"   ⏳ Waiting for deployment to be ready...")
        sp.run(
            ['kubectl', 'wait', '--for=condition=available', '--timeout=300s', f'deployment/{app_name}'],
            check=True,
            capture_output=True
        )
        print(f"   ✅ Deployment is ready")
        
        # Get service endpoint
        print(f"   ⏳ Waiting for LoadBalancer endpoint...")
        for i in range(30):
            result = sp.run(
                ['kubectl', 'get', 'service', app_name, '-o', 'json'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                svc = json.loads(result.stdout)
                ingress = svc.get('status', {}).get('loadBalancer', {}).get('ingress', [])
                if ingress:
                    endpoint = ingress[0].get('hostname') or ingress[0].get('ip')
                    print(f"   ✅ LoadBalancer endpoint: {endpoint}")
                    return {
                        'status': 'success',
                        'endpoint': f"http://{endpoint}",
                        'app_name': app_name,
                        'replicas': replicas
                    }
            time.sleep(10)
        
        print(f"   ⚠️  LoadBalancer endpoint not ready yet")
        return {
            'status': 'pending',
            'message': 'Deployment created, waiting for LoadBalancer'
        }
    finally:
        import os
        os.unlink(deploy_file)

def main():
    """Main deployment workflow"""
    
    print("=" * 80)
    print("🚀 Deploying sample-application to EKS using V2 Agent")
    print("=" * 80)
    print("\nStrategy: Use V2 agent (boto3 + kubernetes client) for all operations")
    print("          with local fallback for Docker build and K8s deploy if needed")
    print("=" * 80)
    
    # Get account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    print(f"\nConfiguration:")
    print(f"  Account ID: {account_id}")
    print(f"  Cluster: {CLUSTER_NAME}")
    print(f"  Region: {REGION}")
    print(f"  App Name: {APP_NAME}")
    print(f"  Image: {IMAGE_NAME}")
    print(f"  Replicas: {REPLICAS}")
    
    # Step 1: Setup OIDC Provider (V2 Agent - boto3)
    print("\n" + "=" * 80)
    print("STEP 1: Setup OIDC Provider (V2 Agent - boto3)")
    print("=" * 80)
    
    oidc_result = call_mcp_tool("setup_oidc_provider", {
        "cluster_name": CLUSTER_NAME,
        "region": REGION
    })
    
    print(f"   Status: {oidc_result.get('status')}")
    if oidc_result.get('status') not in ['exists', 'created']:
        print(f"   ⚠️  Warning: {oidc_result.get('message')}")
    else:
        print(f"   ✅ OIDC Provider: {oidc_result.get('provider_arn')}")
    
    # Step 2: Create IRSA Role (V2 Agent - boto3)
    print("\n" + "=" * 80)
    print("STEP 2: Create IRSA Role (V2 Agent - boto3)")
    print("=" * 80)
    
    irsa_result = call_mcp_tool("create_irsa_role", {
        "cluster_name": CLUSTER_NAME,
        "app_name": APP_NAME,
        "region": REGION,
        "s3_bucket": S3_BUCKET,
        "dynamodb_table": DYNAMODB_TABLE
    })
    
    print(f"   Status: {irsa_result.get('status')}")
    if irsa_result.get('status') not in ['created', 'updated']:
        print(f"   ❌ Error: {irsa_result.get('message')}")
        return
    
    role_arn = irsa_result.get('role_arn')
    service_account_name = irsa_result.get('service_account_name')
    print(f"   ✅ Role ARN: {role_arn}")
    print(f"   ✅ Service Account: {service_account_name}")
    
    # Step 3: Build and Push Image (Local - Docker)
    print("\n" + "=" * 80)
    print("STEP 3: Build and Push Docker Image (Local - Docker)")
    print("=" * 80)
    print("   Note: Using local Docker because CodeBuild project not set up")
    
    build_result = build_and_push_image_local(APP_PATH, IMAGE_NAME, REGION, account_id)
    
    if build_result['status'] != 'success':
        print(f"   ❌ Error: {build_result.get('message')}")
        return
    
    image_uri = build_result['image_uri']
    print(f"   ✅ Image URI: {image_uri}")
    
    # Step 4: Deploy to EKS (V2 Agent - kubernetes client)
    print("\n" + "=" * 80)
    print("STEP 4: Deploy to EKS (V2 Agent - kubernetes client)")
    print("=" * 80)
    print("   Note: Testing V2 agent's deploy_to_eks_with_irsa tool")
    
    env_vars = {
        "DYNAMODB_TABLE": DYNAMODB_TABLE,
        "S3_BUCKET": S3_BUCKET,
        "COGNITO_USER_POOL_ID": COGNITO_USER_POOL_ID,
        "COGNITO_CLIENT_ID": COGNITO_CLIENT_ID,
        "PORT": str(PORT),
        "NODE_ENV": NODE_ENV
    }
    
    deploy_result = call_mcp_tool("deploy_to_eks_with_irsa", {
        "cluster_name": CLUSTER_NAME,
        "app_name": APP_NAME,
        "image_uri": image_uri,
        "port": PORT,
        "replicas": REPLICAS,
        "env_vars": env_vars,
        "region": REGION,
        "role_arn": role_arn,
        "service_account_name": service_account_name
    })
    
    print(f"   Status: {deploy_result.get('status')}")
    if deploy_result.get('status') == 'success':
        print(f"   ✅ Deployment successful!")
        if deploy_result.get('endpoint'):
            print(f"   ✅ Endpoint: {deploy_result.get('endpoint')}")
    else:
        print(f"   ⚠️  Message: {deploy_result.get('message')}")
        print(f"\n   Note: If authentication fails, falling back to local kubectl...")
        
        # Fallback to local kubectl if agent fails
        deploy_result = deploy_to_eks_local(
            CLUSTER_NAME, APP_NAME, image_uri, PORT, REPLICAS,
            env_vars, REGION, role_arn, service_account_name
        )
        
        if deploy_result['status'] != 'success':
            print(f"   ⚠️  Status: {deploy_result.get('status')}")
            print(f"   Message: {deploy_result.get('message')}")
    
    # Step 5: Verify Deployment
    print("\n" + "=" * 80)
    print("STEP 5: Verify Deployment")
    print("=" * 80)
    
    time.sleep(5)
    
    result = sp.run(
        ['kubectl', 'get', 'deployment', APP_NAME, '-o', 'json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        deployment = json.loads(result.stdout)
        status = deployment.get('status', {})
        
        print(f"   Replicas: {status.get('replicas', 0)}")
        print(f"   Available: {status.get('availableReplicas', 0)}")
        print(f"   Ready: {status.get('readyReplicas', 0)}")
    
    # Final Summary
    print("\n" + "=" * 80)
    print("✅ DEPLOYMENT COMPLETE!")
    print("=" * 80)
    
    print(f"\n📝 Deployment Summary:")
    print(f"   Cluster: {CLUSTER_NAME}")
    print(f"   App Name: {APP_NAME}")
    print(f"   Image: {image_uri}")
    print(f"   Replicas: {REPLICAS}")
    print(f"   Role ARN: {role_arn}")
    print(f"   Service Account: {service_account_name}")
    
    if deploy_result.get('endpoint'):
        print(f"\n🌐 Application Endpoint: {deploy_result['endpoint']}")
    
    print(f"\n📊 V2 Agent Usage:")
    print(f"   ✅ OIDC Setup: V2 Agent (boto3)")
    print(f"   ✅ IRSA Role: V2 Agent (boto3)")
    print(f"   ⚠️  Docker Build: Local (CodeBuild not set up)")
    print(f"   {'✅' if deploy_result.get('status') == 'success' else '⚠️'}  K8s Deploy: V2 Agent (kubernetes client) {'with local fallback' if deploy_result.get('status') != 'success' else ''}")
    
    print(f"\n📝 Useful commands:")
    print(f"   Get endpoint: kubectl get service {APP_NAME} -o jsonpath='{{.status.loadBalancer.ingress[0].hostname}}'")
    print(f"   Check logs: kubectl logs -l app={APP_NAME}")
    print(f"   Check pods: kubectl get pods -l app={APP_NAME}")
    print(f"   Scale: kubectl scale deployment/{APP_NAME} --replicas=3")
    print(f"   Delete: kubectl delete deployment,service,serviceaccount {APP_NAME} {service_account_name}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
