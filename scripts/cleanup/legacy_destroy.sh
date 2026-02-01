#!/bin/bash

set -e

# Default region, can be overridden
REGION="${AWS_REGION:-eu-north-1}"

# Allow region override via command line
if [ -n "$1" ]; then
    REGION="$1"
fi

echo "🗑️  Starting CDK infrastructure destruction..."
echo "🌍 Region: $REGION"
echo ""

# Change to CDK directory
cd "$(dirname "$0")/../../infrastructure/cdk"

# Find CDK stack name dynamically
echo "🔍 Finding CDK stacks in region $REGION..."
CDK_STACKS=$(aws cloudformation list-stacks --region $REGION \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
    --query 'StackSummaries[?contains(StackName, `Cdk`) || contains(StackName, `CDK`)].StackName' \
    --output text)

if [ -z "$CDK_STACKS" ]; then
    echo "ℹ️  No CDK stacks found in region $REGION"
    exit 0
fi

for STACK_NAME in $CDK_STACKS; do
    echo "📋 Processing stack: $STACK_NAME"
    
    # Try to get stack outputs
    INSTANCE_ID=""
    S3_BUCKET=""
    
    STACK_INFO=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION 2>/dev/null || echo "")
    
    if [ -n "$STACK_INFO" ]; then
        INSTANCE_ID=$(echo "$STACK_INFO" | jq -r '.Stacks[0].Outputs[]? | select(.OutputKey=="SSMCommand") | .OutputValue' 2>/dev/null | grep -o 'i-[a-zA-Z0-9]*' || true)
        S3_BUCKET=$(echo "$STACK_INFO" | jq -r '.Stacks[0].Outputs[]? | select(.OutputKey=="S3BucketName") | .OutputValue' 2>/dev/null || true)
    fi
    
    echo "🔍 Found resources:"
    echo "  Instance ID: ${INSTANCE_ID:-'Not found'}"
    echo "  S3 Bucket: ${S3_BUCKET:-'Not found'}"
    
    # Stop application service if instance exists
    if [ -n "$INSTANCE_ID" ]; then
        echo "🛑 Stopping application service..."
        aws ssm send-command \
            --instance-ids "$INSTANCE_ID" \
            --document-name "AWS-RunShellScript" \
            --region "$REGION" \
            --parameters 'commands=[
                "sudo systemctl stop blog-app || true",
                "sudo systemctl disable blog-app || true",
                "rm -rf /home/ec2-user/blog-app*"
            ]' \
            --output text --query 'Command.CommandId' 2>/dev/null || true
        
        echo "⏳ Waiting for service cleanup..."
        sleep 10
    fi
    
    # Empty S3 bucket if it exists (required for deletion)
    if [ -n "$S3_BUCKET" ]; then
        echo "🗂️  Emptying S3 bucket..."
        aws s3 rm s3://$S3_BUCKET --recursive --region $REGION 2>/dev/null || true
    fi
    
    echo "🏗️  Destroying CDK stack: $STACK_NAME..."
    AWS_REGION=$REGION cdk destroy $STACK_NAME --force
done

echo "🧹 Cleaning up local files..."
cd ..
rm -f stack-outputs.json
rm -f app-deployment.tar.gz

echo "✅ CDK infrastructure destruction complete!"
echo "🔄 To redeploy, run: ./deploy.sh"
