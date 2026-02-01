#!/usr/bin/env python3
"""
Test script to delete ECS Express Mode service using AgentCore
"""

import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

# Configuration
AGENT_ARN = "arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/ecs_deployment_agent-Kq38Lc3cm5"
AGENT_REGION = "us-west-2"  # Region where the agent is deployed
TARGET_REGION = "eu-north-1"  # Region where ECS services are running
SERVICE_NAME = "blog-app-1768574307"  # Change this to your actual service name

def invoke_strands_agent(agent_arn: str, prompt: str, agent_region: str = "us-west-2"):
    """Invoke AgentCore agent using Strands protocol"""
    
    # URL encode the ARN
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    
    # Construct endpoint URL with qualifier
    url = f"https://bedrock-agentcore.{agent_region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    # Prepare request payload
    payload = {
        "prompt": prompt
    }
    
    # Create AWS request for signing
    request = AWSRequest(
        method='POST',
        url=url,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json'
        }
    )
    
    # Sign the request
    session = boto3.Session()
    credentials = session.get_credentials()
    SigV4Auth(credentials, "bedrock-agentcore", agent_region).add_auth(request)
    
    # Send the request
    response = requests.post(
        url,
        data=request.body,
        headers=dict(request.headers)
    )
    
    return response

def list_ecs_services():
    """List all ECS services first"""
    print("\n" + "="*60)
    print("Step 1: Listing ECS Services")
    print("="*60)
    
    prompt = f"List all ECS services in {TARGET_REGION}"
    
    print(f"\n📤 Sending request to agent...")
    print(f"Prompt: {prompt}")
    
    response = invoke_strands_agent(AGENT_ARN, prompt, AGENT_REGION)
    
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Response:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"\n❌ Error: {response.text}")
        return None

def delete_ecs_service(service_name: str):
    """Delete ECS service"""
    print("\n" + "="*60)
    print(f"Step 2: Deleting ECS Service: {service_name}")
    print("="*60)
    
    prompt = f"Delete the ECS service named {service_name} in region {TARGET_REGION}"
    
    print(f"\n📤 Sending delete request to agent...")
    print(f"Prompt: {prompt}")
    
    response = invoke_strands_agent(AGENT_ARN, prompt, AGENT_REGION)
    
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Delete Response:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"\n❌ Error: {response.text}")
        return None

def check_cloudformation_stacks():
    """Check CloudFormation stacks to see what exists"""
    print("\n" + "="*60)
    print("Step 0: Checking CloudFormation Stacks")
    print("="*60)
    
    cfn = boto3.client('cloudformation', region_name=TARGET_REGION)
    
    try:
        response = cfn.list_stacks(
            StackStatusFilter=[
                'CREATE_COMPLETE',
                'UPDATE_COMPLETE',
                'DELETE_IN_PROGRESS'
            ]
        )
        
        ecs_stacks = [
            stack for stack in response['StackSummaries']
            if 'ecs-express' in stack['StackName']
        ]
        
        if ecs_stacks:
            print(f"\n✅ Found {len(ecs_stacks)} ECS Express stack(s):")
            for stack in ecs_stacks:
                print(f"  - {stack['StackName']} ({stack['StackStatus']})")
            return ecs_stacks
        else:
            print("\n⚠️  No ECS Express stacks found")
            return []
            
    except Exception as e:
        print(f"\n❌ Error checking stacks: {str(e)}")
        return []

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("ECS Service Deletion Test")
    print("="*60)
    print(f"\nAgent ARN: {AGENT_ARN}")
    print(f"Agent Region: {AGENT_REGION}")
    print(f"Target Region: {TARGET_REGION}")
    print(f"Target Service: {SERVICE_NAME}")
    
    # Step 0: Check what stacks exist
    stacks = check_cloudformation_stacks()
    
    if not stacks:
        print("\n⚠️  No ECS Express stacks found to delete")
        print("\nYou can still test the delete tool with a service name:")
        print(f"  Service Name: {SERVICE_NAME}")
        
        # Ask user if they want to proceed
        proceed = input("\nProceed with deletion attempt? (y/n): ")
        if proceed.lower() != 'y':
            print("\n❌ Deletion cancelled")
            return
    
    # Step 1: List services
    list_result = list_ecs_services()
    
    # Step 2: Delete service
    if list_result:
        print(f"\n⚠️  About to delete service: {SERVICE_NAME}")
        confirm = input("Confirm deletion? (y/n): ")
        
        if confirm.lower() == 'y':
            delete_result = delete_ecs_service(SERVICE_NAME)
            
            if delete_result:
                print("\n" + "="*60)
                print("✅ Deletion Summary")
                print("="*60)
                print(f"\nService: {SERVICE_NAME}")
                print(f"Region: {TARGET_REGION}")
                print("\nThe CloudFormation stack deletion has been initiated.")
                print("This will delete:")
                print("  - ECS Express Gateway Service")
                print("  - Application Load Balancer")
                print("  - Target Groups")
                print("  - Security Groups")
                print("  - CloudWatch Log Groups")
                print("\nCheck CloudFormation console for deletion progress:")
                print(f"https://console.aws.amazon.com/cloudformation/home?region={TARGET_REGION}")
        else:
            print("\n❌ Deletion cancelled by user")
    else:
        print("\n⚠️  Skipping deletion due to list failure")

if __name__ == "__main__":
    main()
