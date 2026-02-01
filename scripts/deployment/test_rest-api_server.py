#!/usr/bin/env python3
"""
Test script for Container Migration MCP Server
Tests all available endpoints and tools
"""

import requests
import json
import os

# Configuration
API_URL = os.getenv("MCP_API_URL", "https://d1lx8mfyu4.execute-api.us-west-2.amazonaws.com/Prod")
API_KEY = os.getenv("MCP_API_KEY", "AKIAIOSFODNN7EXAMPLE")  # AWS-approved example key

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

def test_endpoint(method, path, data=None):
    """Test an endpoint and return the result"""
    try:
        if method == "GET":
            response = requests.get(f"{API_URL}{path}", headers=HEADERS, timeout=30)
        else:
            response = requests.post(f"{API_URL}{path}", headers=HEADERS, json=data, timeout=30)
        
        print(f"  {method} {path}: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if 'status' in result:
                print(f"    Status: {result['status']}")
            if 'message' in result:
                print(f"    Message: {result['message']}")
        else:
            print(f"    Error: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"  {method} {path}: ERROR - {str(e)}")
        return False

def main():
    print("🧪 Testing Container Migration MCP Server")
    print("=" * 50)
    
    # Test containerization tools
    print("\n📦 Testing Containerization Tools:")
    
    # Test optimize_dockerfile
    test_endpoint("POST", "/tools/optimize_dockerfile", {
        "base_image": "node:18-alpine",
        "port": 3000
    })
    
    # Test build_and_push_container
    test_endpoint("POST", "/tools/build_and_push_container", {
        "app_name": "test-app",
        "tag": "test",
        "region": "us-west-2"
    })
    
    # Test validate_container_security
    test_endpoint("POST", "/tools/validate_container_security", {
        "dockerfile_path": "/tmp/Dockerfile"
    })
    
    # Test ECS tools
    print("\n🚀 Testing ECS Express Mode Tools:")
    
    # Test validate_ecs_prerequisites
    test_endpoint("POST", "/tools/validate_ecs_prerequisites", {
        "image_uri": "<AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0",
        "region": "us-west-2"
    })
    
    # Test deploy_ecs_express_service
    test_endpoint("POST", "/tools/deploy_ecs_express_service", {
        "service_name": "test-service",
        "image_uri": "<AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0",
        "environment_vars": {"NODE_ENV": "production"},
        "region": "us-west-2"
    })
    
    # Test check_ecs_service_status
    test_endpoint("POST", "/tools/check_ecs_service_status", {
        "service_arn": "arn:aws:ecs:us-west-2:<AWS_ACCOUNT_ID>:service/test-service",
        "region": "us-west-2"
    })
    
    # Test resource endpoints
    print("\n📋 Testing Resource Endpoints:")
    
    test_endpoint("GET", "/resources/dockerfile-template")
    test_endpoint("GET", "/resources/build-script")
    test_endpoint("GET", "/resources/iam-roles-template")
    test_endpoint("GET", "/resources/deployment-guide")
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    main()
