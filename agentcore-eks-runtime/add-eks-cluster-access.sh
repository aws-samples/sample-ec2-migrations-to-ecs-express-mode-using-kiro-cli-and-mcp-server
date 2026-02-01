#!/bin/bash
# Add AgentCore execution role to EKS cluster access
# This allows the V2 agent to authenticate with the Kubernetes API
# Usage: ./add-eks-cluster-access.sh [CLUSTER_NAME] [REGION] [ROLE_NAME]

set -e

# Get cluster name from argument or prompt
if [ -n "$1" ]; then
    CLUSTER_NAME="$1"
else
    echo "❌ Error: Cluster name is required"
    echo "Usage: $0 CLUSTER_NAME [REGION] [ROLE_NAME]"
    echo "Example: $0 my-eks-cluster eu-north-1"
    echo "Example: $0 my-eks-cluster eu-north-1 AmazonBedrockAgentCoreSDKRuntime-us-west-2-976ef190c4"
    exit 1
fi

# Get region from argument or AWS CLI default
REGION="${2:-$(aws configure get region)}"
if [ -z "$REGION" ]; then
    echo "❌ Error: Region is required (not found in AWS CLI config)"
    echo "Usage: $0 CLUSTER_NAME [REGION] [ROLE_NAME]"
    exit 1
fi

# Get role name from argument or auto-detect
if [ -n "$3" ]; then
    AGENTCORE_ROLE_NAME="$3"
else
    # Auto-detect AgentCore role
    echo "🔍 Auto-detecting AgentCore execution role..."
    AGENTCORE_ROLE_NAME=$(aws iam list-roles --query "Roles[?starts_with(RoleName, 'AmazonBedrockAgentCoreSDKRuntime-')].RoleName" --output text | head -n 1)
    
    if [ -z "$AGENTCORE_ROLE_NAME" ]; then
        echo "❌ Error: Could not find AgentCore execution role"
        echo "Usage: $0 CLUSTER_NAME [REGION] [ROLE_NAME]"
        exit 1
    fi
    echo "✅ Found role: $AGENTCORE_ROLE_NAME"
fi

echo ""
echo "=========================================="
echo "Adding AgentCore Role to EKS Cluster"
echo "=========================================="
echo ""
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo "Role: $AGENTCORE_ROLE_NAME"
echo ""

# Get the role ARN
echo "🔍 Getting role ARN..."
ROLE_ARN=$(aws iam get-role --role-name "$AGENTCORE_ROLE_NAME" --query 'Role.Arn' --output text)
echo "Role ARN: $ROLE_ARN"
echo ""

# Check if access entry already exists
echo "Checking if access entry already exists..."
if aws eks describe-access-entry \
    --cluster-name "$CLUSTER_NAME" \
    --principal-arn "$ROLE_ARN" \
    --region "$REGION" 2>/dev/null; then
    echo "✅ Access entry already exists"
    echo ""
    echo "Updating access entry..."
    aws eks update-access-entry \
        --cluster-name "$CLUSTER_NAME" \
        --principal-arn "$ROLE_ARN" \
        --region "$REGION"
else
    echo "Creating new access entry..."
    aws eks create-access-entry \
        --cluster-name "$CLUSTER_NAME" \
        --principal-arn "$ROLE_ARN" \
        --region "$REGION" \
        --type STANDARD
fi

echo ""
echo "=========================================="
echo "Adding Cluster Admin Policy"
echo "=========================================="
echo ""

# Associate the cluster admin policy
# This gives full access to the cluster (you can restrict this later)
aws eks associate-access-policy \
    --cluster-name "$CLUSTER_NAME" \
    --principal-arn "$ROLE_ARN" \
    --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy \
    --access-scope type=cluster \
    --region "$REGION" 2>/dev/null || echo "Policy already associated or failed to associate"

echo ""
echo "=========================================="
echo "✅ SUCCESS!"
echo "=========================================="
echo ""
echo "The AgentCore role now has access to the EKS cluster."
echo "The V2 agent's kubernetes client should now work!"
echo ""
echo "Verify with:"
echo "  aws eks list-access-entries --cluster-name $CLUSTER_NAME --region $REGION"
echo ""
