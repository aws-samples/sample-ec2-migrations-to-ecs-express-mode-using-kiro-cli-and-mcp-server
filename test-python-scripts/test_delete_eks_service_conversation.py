#!/usr/bin/env python3
"""
Test script to delete EKS deployment using AgentCore MCP
"""

import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

# Configuration
AGENT_ARN = "arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/eks_deployment_agent-bJq2whDHLA"
REGION = "us-west-2"
CLUSTER_NAME = "ec2-eks-migration"
CLUSTER_REGION = "eu-north-1"
APP_NAME = "blog-app-eks-v3"

def invoke_mcp_tool(agent_arn: str, tool_name: str, arguments: dict, region: str = "us-west-2"):
    """Invoke AgentCore MCP tool"""
    
    # URL encode the ARN
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    
    # Construct endpoint URL with qualifier
    url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    # Prepare MCP request payload
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    # Create AWS request for signing
    request = AWSRequest(
        method='POST',
        url=url,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
    )
    
    # Sign the request
    session = boto3.Session()
    credentials = session.get_credentials()
    SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)
    
    # Send the request
    response = requests.post(
        url,
        data=request.body,
        headers=dict(request.headers)
    )
    
    # Parse SSE response
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
    
    return response

def check_eks_deployment():
    """Check if EKS deployment exists"""
    print("\n" + "="*60)
    print("Step 1: Checking EKS Deployment Status")
    print("="*60)
    
    arguments = {
        "cluster_name": CLUSTER_NAME,
        "app_name": APP_NAME,
        "region": CLUSTER_REGION
    }
    
    print(f"\n📤 Calling get_deployment_status tool...")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    result = invoke_mcp_tool(AGENT_ARN, "get_deployment_status", arguments, REGION)
    
    print(f"\n📥 Response:")
    print(json.dumps(result, indent=2))
    
    # Check if deployment exists
    if isinstance(result, dict):
        status = result.get('status', 'unknown')
        if status == 'not_found':
            print(f"\n⚠️  Deployment '{APP_NAME}' not found in cluster '{CLUSTER_NAME}'")
            return False
        elif status == 'error':
            print(f"\n❌ Error: {result.get('message', 'Unknown error')}")
            return False
        else:
            print(f"\n✅ Deployment found with status: {status}")
            return True
    return False

def delete_eks_deployment():
    """Delete EKS deployment"""
    print("\n" + "="*60)
    print(f"Step 2: Deleting EKS Deployment: {APP_NAME}")
    print("="*60)
    
    arguments = {
        "cluster_name": CLUSTER_NAME,
        "app_name": APP_NAME,
        "region": CLUSTER_REGION,
        "delete_service": True,
        "delete_service_account": True
    }
    
    print(f"\n📤 Calling delete_eks_deployment tool...")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    result = invoke_mcp_tool(AGENT_ARN, "delete_eks_deployment", arguments, REGION)
    
    print(f"\n📥 Delete Response:")
    print(json.dumps(result, indent=2))
    
    return result

def check_kubernetes_resources():
    """Check Kubernetes resources using kubectl"""
    print("\n" + "="*60)
    print("Step 0: Checking Kubernetes Resources")
    print("="*60)
    
    try:
        import subprocess
        
        # Update kubeconfig
        print(f"\n📋 Updating kubeconfig for cluster: {CLUSTER_NAME}")
        subprocess.run([
            "aws", "eks", "update-kubeconfig",
            "--name", CLUSTER_NAME,
            "--region", CLUSTER_REGION
        ], check=True, capture_output=True)
        
        # Check deployments
        print(f"\n📋 Checking deployments...")
        result = subprocess.run([
            "kubectl", "get", "deployments",
            "-l", f"app={APP_NAME}",
            "-o", "json"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            deployments = json.loads(result.stdout)
            if deployments.get('items'):
                print(f"\n✅ Found deployment: {APP_NAME}")
                for item in deployments['items']:
                    print(f"  - Name: {item['metadata']['name']}")
                    print(f"  - Replicas: {item['spec']['replicas']}")
                    print(f"  - Available: {item['status'].get('availableReplicas', 0)}")
                return True
            else:
                print(f"\n⚠️  No deployment found with label app={APP_NAME}")
                return False
        else:
            print(f"\n⚠️  kubectl command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"\n⚠️  Could not check Kubernetes resources: {str(e)}")
        print("This is optional - proceeding with MCP tool call")
        return None

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("EKS Deployment Deletion Test")
    print("="*60)
    print(f"\nAgent ARN: {AGENT_ARN}")
    print(f"Region: {REGION}")
    print(f"Cluster: {CLUSTER_NAME} ({CLUSTER_REGION})")
    print(f"App Name: {APP_NAME}")
    
    # Step 0: Check Kubernetes resources (optional)
    k8s_exists = check_kubernetes_resources()
    
    # Step 1: Check deployment status via MCP
    deployment_exists = check_eks_deployment()
    
    if not deployment_exists and k8s_exists is False:
        print("\n⚠️  No deployment found to delete")
        print("\nYou can still test the delete tool:")
        
        # Ask user if they want to proceed
        proceed = input("\nProceed with deletion attempt? (y/n): ")
        if proceed.lower() != 'y':
            print("\n❌ Deletion cancelled")
            return
    
    # Step 2: Delete deployment
    print(f"\n⚠️  About to delete deployment: {APP_NAME}")
    print(f"This will delete:")
    print(f"  - Deployment: {APP_NAME}")
    print(f"  - Service: {APP_NAME}")
    print(f"  - ServiceAccount: {APP_NAME}-sa")
    
    confirm = input("\nConfirm deletion? (y/n): ")
    
    if confirm.lower() == 'y':
        delete_result = delete_eks_deployment()
        
        if delete_result:
            print("\n" + "="*60)
            print("✅ Deletion Summary")
            print("="*60)
            print(f"\nCluster: {CLUSTER_NAME}")
            print(f"App Name: {APP_NAME}")
            print(f"Region: {CLUSTER_REGION}")
            
            # Parse result
            if 'result' in delete_result:
                tool_result = delete_result['result']
                if isinstance(tool_result, dict):
                    deleted_resources = tool_result.get('deleted_resources', [])
                    print(f"\nDeleted Resources:")
                    for resource in deleted_resources:
                        print(f"  ✅ {resource}")
                    
                    print(f"\nMessage: {tool_result.get('message', 'N/A')}")
            
            print("\nVerify deletion with:")
            print(f"  kubectl get deployments,services,serviceaccounts -l app={APP_NAME}")
    else:
        print("\n❌ Deletion cancelled by user")

if __name__ == "__main__":
    main()
