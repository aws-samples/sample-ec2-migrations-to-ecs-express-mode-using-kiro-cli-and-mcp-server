#!/usr/bin/env python3
"""
Test script for delete tools in both ECS and EKS AgentCore agents
"""

import json

def test_ecs_delete_tool():
    """Test ECS delete_ecs_service tool"""
    print("\n" + "="*60)
    print("Testing ECS delete_ecs_service Tool")
    print("="*60)
    
    # Example tool call structure
    tool_call = {
        "tool": "delete_ecs_service",
        "parameters": {
            "service_name": "my-blog-app",
            "region": "us-west-2"
        }
    }
    
    print("\n📋 Tool Call Structure:")
    print(json.dumps(tool_call, indent=2))
    
    print("\n✅ Expected Behavior:")
    print("  - Constructs stack name as 'ecs-express-my-blog-app'")
    print("  - Checks if CloudFormation stack exists")
    print("  - Deletes the stack (which deletes ECS service)")
    print("  - Deletes associated resources:")
    print("    • ECS Express Gateway Service")
    print("    • Application Load Balancer")
    print("    • Target Groups")
    print("    • Security Groups")
    print("    • CloudWatch Log Groups")
    
    print("\n📤 Expected Response:")
    expected_response = {
        "status": "success",
        "stack_name": "ecs-express-my-blog-app",
        "service_name": "my-blog-app",
        "message": "Stack ecs-express-my-blog-app deletion initiated. This will delete the ECS service and all associated resources (ALB, target groups, security groups)."
    }
    print(json.dumps(expected_response, indent=2))
    
    print("\n⚠️  Alternative Parameters:")
    print("  You can also use 'stack_name' directly:")
    alt_call = {
        "tool": "delete_ecs_service",
        "parameters": {
            "stack_name": "ecs-express-my-blog-app",
            "region": "us-west-2"
        }
    }
    print(json.dumps(alt_call, indent=2))

def test_eks_delete_tool():
    """Test EKS delete_eks_deployment tool"""
    print("\n" + "="*60)
    print("Testing EKS delete_eks_deployment Tool")
    print("="*60)
    
    # Example tool call structure
    tool_call = {
        "tool": "delete_eks_deployment",
        "parameters": {
            "cluster_name": "ec2-eks-migration",
            "app_name": "blog-app-eks-v3",
            "region": "eu-north-1",
            "delete_service": True,
            "delete_service_account": True
        }
    }
    
    print("\n📋 Tool Call Structure:")
    print(json.dumps(tool_call, indent=2))
    
    print("\n✅ Expected Behavior:")
    print("  - Authenticates to EKS cluster using boto3")
    print("  - Deletes Kubernetes Deployment")
    print("  - Deletes Kubernetes Service (LoadBalancer)")
    print("  - Deletes Kubernetes ServiceAccount (IRSA)")
    print("  - Uses graceful deletion (30s grace period)")
    print("  - Handles 404 errors gracefully")
    
    print("\n📤 Expected Response:")
    expected_response = {
        "status": "success",
        "app_name": "blog-app-eks-v3",
        "deleted_resources": [
            "Deployment: blog-app-eks-v3",
            "Service: blog-app-eks-v3",
            "ServiceAccount: blog-app-eks-v3-sa"
        ],
        "message": "Successfully deleted 3 resource(s)"
    }
    print(json.dumps(expected_response, indent=2))
    
    print("\n⚠️  Optional Parameters:")
    print("  - delete_service: Set to False to keep the Service")
    print("  - delete_service_account: Set to False to keep the ServiceAccount")
    
    minimal_call = {
        "tool": "delete_eks_deployment",
        "parameters": {
            "cluster_name": "ec2-eks-migration",
            "app_name": "blog-app-eks-v3",
            "region": "eu-north-1",
            "delete_service": False,
            "delete_service_account": False
        }
    }
    print("\n  Minimal deletion (Deployment only):")
    print(json.dumps(minimal_call, indent=2))

def test_chatbot_integration():
    """Show how to use delete tools in chatbots"""
    print("\n" + "="*60)
    print("Chatbot Integration Examples")
    print("="*60)
    
    print("\n🤖 Simple Interactive Chatbot:")
    print("  Menu option: '6. Delete ECS Service'")
    print("  Menu option: '7. Delete EKS Deployment'")
    print("  User provides: service_name/app_name, region")
    
    print("\n🤖 AI-Powered Chatbot:")
    print("  User: 'Delete my ECS service called my-blog-app'")
    print("  Agent: Calls delete_ecs_service tool")
    print("  User: 'Remove the blog-app-eks-v3 deployment from EKS'")
    print("  Agent: Calls delete_eks_deployment tool")
    
    print("\n📝 Conversation Example:")
    conversation = [
        {"role": "user", "content": "I want to delete my ECS service"},
        {"role": "assistant", "content": "I can help you delete an ECS service. What's the service name?"},
        {"role": "user", "content": "my-blog-app in us-west-2"},
        {"role": "assistant", "content": "Calling delete_ecs_service..."},
        {"role": "tool", "content": "Stack deletion initiated successfully"},
        {"role": "assistant", "content": "✅ Your ECS service 'my-blog-app' has been deleted. The CloudFormation stack and all associated resources (ALB, target groups, security groups) are being removed."}
    ]
    
    for msg in conversation:
        print(f"  {msg['role'].upper()}: {msg['content']}")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AgentCore Delete Tools - Test Documentation")
    print("="*60)
    print("\nThis script demonstrates the new delete tools added to both")
    print("ECS and EKS AgentCore agents.")
    
    test_ecs_delete_tool()
    test_eks_delete_tool()
    test_chatbot_integration()
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("\n✅ ECS Delete Tool:")
    print("  - Deletes CloudFormation stack")
    print("  - Removes ECS service and all infrastructure")
    print("  - Accepts service_name or stack_name")
    
    print("\n✅ EKS Delete Tool:")
    print("  - Deletes Kubernetes resources")
    print("  - Removes Deployment, Service, ServiceAccount")
    print("  - Configurable deletion scope")
    
    print("\n✅ Both Tools:")
    print("  - Graceful error handling")
    print("  - Detailed status messages")
    print("  - Chatbot-ready")
    
    print("\n📚 Next Steps:")
    print("  1. Update chatbots to include delete options")
    print("  2. Test with real deployments")
    print("  3. Add to documentation")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
