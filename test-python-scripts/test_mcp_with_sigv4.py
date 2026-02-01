#!/usr/bin/env python3
"""
Test MCP server with AWS SigV4 authentication
This script uses boto3 to make signed requests to the MCP endpoint
"""

import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

# Configuration
AGENT_ARN = 'arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/eks_deployment_agent-bJq2whDHLA'
REGION = 'us-west-2'

def make_signed_request(url, method='POST', data=None):
    """Make a signed request to the MCP endpoint using SigV4"""
    
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Prepare request
    request = AWSRequest(
        method=method,
        url=url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
    )
    
    # Sign the request
    SigV4Auth(credentials, 'bedrock-agentcore', REGION).add_auth(request)
    
    # Make the request
    response = requests.request(
        method=request.method,
        url=request.url,
        headers=dict(request.headers),
        data=request.body
    )
    
    return response

def test_list_tools():
    """Test listing tools using MCP protocol"""
    
    # Encode ARN for URL
    encoded_arn = AGENT_ARN.replace(':', '%3A').replace('/', '%2F')
    
    # Construct MCP URL
    mcp_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    print(f"🔗 Testing MCP server with SigV4 authentication...")
    print(f"   URL: {mcp_url}")
    print(f"   Region: {REGION}")
    
    # MCP tools/list request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        print("\n📋 Sending tools/list request...")
        response = make_signed_request(mcp_url, data=json.dumps(mcp_request))
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # Check if it's a streaming response
            if 'text/event-stream' in response.headers.get('Content-Type', ''):
                print(f"\n✅ Streaming response received")
                
                # Parse SSE format
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        try:
                            result = json.loads(data)
                            
                            if 'result' in result and 'tools' in result['result']:
                                tools = result['result']['tools']
                                print(f"\n✅ Found {len(tools)} tools:")
                                for i, tool in enumerate(tools, 1):
                                    print(f"\n{i}. {tool['name']}")
                                    if 'description' in tool:
                                        print(f"   Description: {tool['description']}")
                                    if 'inputSchema' in tool:
                                        required = tool['inputSchema'].get('required', [])
                                        props = tool['inputSchema'].get('properties', {})
                                        print(f"   Required parameters: {', '.join(required)}")
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                result = response.json()
                print(f"\n✅ Response received:")
                print(json.dumps(result, indent=2))
                
                if 'result' in result and 'tools' in result['result']:
                    tools = result['result']['tools']
                    print(f"\n✅ Found {len(tools)} tools:")
                    for i, tool in enumerate(tools, 1):
                        print(f"\n{i}. {tool['name']}")
                        if 'description' in tool:
                            print(f"   Description: {tool['description']}")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_call_tool(tool_name, arguments):
    """Test calling a specific tool"""
    
    # Encode ARN for URL
    encoded_arn = AGENT_ARN.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    # MCP tools/call request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    try:
        print(f"\n🔧 Calling tool: {tool_name}")
        print(f"   Arguments: {json.dumps(arguments, indent=2)}")
        
        response = make_signed_request(mcp_url, data=json.dumps(mcp_request))
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Check if it's a streaming response
            if 'text/event-stream' in response.headers.get('Content-Type', ''):
                print(f"\n✅ Streaming response received")
                
                # Parse SSE format
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        try:
                            result = json.loads(data)
                            print(json.dumps(result, indent=2))
                            break
                        except json.JSONDecodeError:
                            continue
            else:
                result = response.json()
                print(f"\n✅ Tool result:")
                print(json.dumps(result, indent=2))
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test listing tools
    test_list_tools()
    
    # Test calling a tool
    print("\n" + "=" * 80)
    print("Testing tool invocation...")
    print("=" * 80)
    
    test_call_tool("setup_oidc_provider", {
        "cluster_name": "ec2-eks-migration",
        "region": "eu-north-1"
    })
