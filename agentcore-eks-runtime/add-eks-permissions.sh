#!/bin/bash
# Add EKS permissions to AgentCore execution role
# Usage: ./add-eks-permissions.sh [ROLE_NAME] [REGION]

set -e

# Get role name from argument or auto-detect
if [ -n "$1" ]; then
    ROLE_NAME="$1"
else
    # Auto-detect AgentCore role
    echo "🔍 Auto-detecting AgentCore execution role..."
    ROLE_NAME=$(aws iam list-roles --query "Roles[?starts_with(RoleName, 'AmazonBedrockAgentCoreSDKRuntime-')].RoleName" --output text | head -n 1)
    
    if [ -z "$ROLE_NAME" ]; then
        echo "❌ Error: Could not find AgentCore execution role"
        echo "Usage: $0 [ROLE_NAME] [REGION]"
        echo "Example: $0 AmazonBedrockAgentCoreSDKRuntime-us-west-2-976ef190c4 us-west-2"
        exit 1
    fi
    echo "✅ Found role: $ROLE_NAME"
fi

# Get region from argument or AWS CLI default
REGION="${2:-$(aws configure get region)}"
if [ -z "$REGION" ]; then
    REGION="us-west-2"
    echo "⚠️  No region specified, using default: $REGION"
fi

POLICY_NAME="EKSFullAccessPolicy"

echo ""
echo "🔧 Adding EKS permissions to role: $ROLE_NAME"
echo "   Region: $REGION"
echo ""

# Create policy document
cat > /tmp/eks-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateOpenIDConnectProvider",
        "iam:DeleteOpenIDConnectProvider",
        "iam:GetOpenIDConnectProvider",
        "iam:ListOpenIDConnectProviders",
        "iam:TagOpenIDConnectProvider",
        "iam:UntagOpenIDConnectProvider",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:UpdateRole",
        "iam:UpdateAssumeRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "codebuild:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bedrock-agentcore-codebuild-sources-*",
        "arn:aws:s3:::bedrock-agentcore-codebuild-sources-*/*"
      ]
    }
  ]
}
EOF

echo "📝 Policy document created"

# Attach policy to role
echo "🔗 Attaching policy to role..."
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document file:///tmp/eks-policy.json \
  --region "$REGION"

echo "✅ Successfully added EKS permissions to role: $ROLE_NAME"

# Verify policy was attached
echo ""
echo "📋 Verifying policy attachment..."
aws iam get-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --region "$REGION" \
  --query 'PolicyName' \
  --output text

echo ""
echo "✅ Policy verified: $POLICY_NAME"

# Clean up
rm /tmp/eks-policy.json

echo ""
echo "🎉 Done! The AgentCore execution role now has full EKS permissions."
echo ""
echo "Permissions added:"
echo "  ✅ EKS: Full access (eks:*)"
echo "  ✅ IAM: OIDC provider and role management"
echo "  ✅ ECR: Full access (ecr:*)"
echo "  ✅ CodeBuild: Full access (codebuild:*)"
echo "  ✅ STS: GetCallerIdentity"
echo "  ✅ S3: CodeBuild source bucket access"
