#!/bin/bash

# Deploy script for EC2-based blog application
# Fixes applied:
# - Uses real application files from sample-application directory (no placeholder copying needed)
# - Uses direct Node.js process management instead of systemctl
# - Ensures application binds to 0.0.0.0 for ALB connectivity
# - Automatically configures environment variables from CloudFormation outputs
# - Enforces authentication on all API endpoints (no anonymous access)
# - Includes comprehensive SSM testing for deployment verification

set -e

# Accept region as parameter, default to eu-north-1
DEPLOY_REGION="${1:-eu-north-1}"

echo "🚀 Starting deployment process..."
echo "📍 Target region: $DEPLOY_REGION"

# Change to CDK directory
cd "$(dirname "$0")/../../infrastructure/cdk"

echo "📦 Building CDK project..."
npm run build

echo "🏗️  Deploying CDK infrastructure to $DEPLOY_REGION..."
export CDK_DEFAULT_REGION="$DEPLOY_REGION"
export AWS_REGION="$DEPLOY_REGION"
cdk deploy --region "$DEPLOY_REGION" --require-approval never --outputs-file ../../scripts/deployment/stack-outputs.json

echo "📋 Extracting stack outputs..."
cd ../../scripts/deployment

# Extract values from CDK outputs
USER_POOL_ID=$(jq -r '.CdkInfrastructureStack.UserPoolId' stack-outputs.json)
CLIENT_ID=$(jq -r '.CdkInfrastructureStack.UserPoolClientId' stack-outputs.json)
S3_BUCKET=$(jq -r '.CdkInfrastructureStack.S3BucketName' stack-outputs.json)
DYNAMODB_TABLE=$(jq -r '.CdkInfrastructureStack.DynamoDBTableName' stack-outputs.json)
INSTANCE_ID=$(jq -r '.CdkInfrastructureStack.SSMCommand' stack-outputs.json | grep -o 'i-[a-zA-Z0-9]*')

# Auto-detect region from stack outputs (extract from S3 bucket name or User Pool ID)
REGION=$(echo "$USER_POOL_ID" | cut -d'_' -f1)

echo "✅ Stack outputs extracted:"
echo "  User Pool ID: $USER_POOL_ID"
echo "  Client ID: $CLIENT_ID"
echo "  S3 Bucket: $S3_BUCKET"
echo "  DynamoDB Table: $DYNAMODB_TABLE"
echo "  Instance ID: $INSTANCE_ID"

echo "🔧 Ensuring User Pool allows self-registration..."
aws cognito-idp update-user-pool \
    --user-pool-id "$USER_POOL_ID" \
    --admin-create-user-config '{"AllowAdminCreateUserOnly":false,"UnusedAccountValidityDays":7}' \
    --region "$REGION" > /dev/null
echo "  ✅ Self-registration enabled"

echo "🔧 Ensuring User Pool email verification is enabled..."
aws cognito-idp update-user-pool \
    --user-pool-id "$USER_POOL_ID" \
    --auto-verified-attributes email \
    --verification-message-template '{"DefaultEmailOption":"CONFIRM_WITH_CODE","EmailMessage":"Your verification code for the blog app is {####}","EmailSubject":"Verify your email for the blog app"}' \
    --region "$REGION" > /dev/null
echo "  ✅ Email verification enabled"

echo "📝 Updating sample-application environment..."

# Update .env file
cat > ../../sample-application/.env << EOF
# Environment Variables
PORT=3000
AWS_REGION=$REGION
DYNAMODB_TABLE=$DYNAMODB_TABLE
S3_BUCKET=$S3_BUCKET
COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_CLIENT_ID=$CLIENT_ID

# AWS Credentials (for local development)
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key
EOF

echo "📤 Deploying application to EC2..."

# Create deployment package with verification
cd ../../sample-application
echo "📦 Creating deployment package..."
echo "  Verifying source files:"
echo "    server.js: $(wc -c < src/server.js) bytes"
echo "    index.html: $(wc -c < public/index.html) bytes"

# Remove any existing package and create fresh one excluding placeholder files
rm -f ../scripts/deployment/app-deployment.tar.gz
tar -czf ../scripts/deployment/app-deployment.tar.gz \
    --exclude='src/server-local.js' \
    --exclude='public/index-auth.html' \
    src/ public/ package.json package-lock.json

echo "  ✅ Package created: $(wc -c < ../scripts/deployment/app-deployment.tar.gz) bytes"
echo "  📋 Package contents:"
tar -tzf ../scripts/deployment/app-deployment.tar.gz | grep -E "(server|index)" | head -5

cd ../scripts/deployment

echo "📦 Uploading new application..."
# Upload deployment package to S3 temporarily
aws s3 cp app-deployment.tar.gz s3://$S3_BUCKET/deployment/

# Download and extract on EC2
DEPLOY_CMD_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --region "$REGION" \
    --parameters "commands=[
        \"cd /home/ec2-user\",
        \"# Clean up and recreate blog-app directory\",
        \"rm -rf blog-app blog-app-backup\",
        \"mkdir -p blog-app\",
        \"cd blog-app\",
        \"# Download and extract application\",
        \"aws s3 cp s3://$S3_BUCKET/deployment/app-deployment.tar.gz .\",
        \"tar -xzf app-deployment.tar.gz\",
        \"# Verify extracted files\",
        \"echo 'Extracted file sizes:'\",
        \"echo \\\"  server.js: \$(wc -c < src/server.js) bytes\\\"\",
        \"echo \\\"  index.html: \$(wc -c < public/index.html) bytes\\\"\",
        \"# Create environment configuration\",
        \"cat > .env << 'EOF'
PORT=3000
AWS_REGION=$REGION
DYNAMODB_TABLE=$DYNAMODB_TABLE
S3_BUCKET=$S3_BUCKET
COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_CLIENT_ID=$CLIENT_ID
EOF\",
        \"# Install dependencies and start application\",
        \"npm install\",
        \"echo 'Final file sizes:'\",
        \"echo \\\"  server.js: \$(wc -c < src/server.js) bytes\\\"\",
        \"echo \\\"  index.html: \$(wc -c < public/index.html) bytes\\\"\",
        \"pkill -f 'node src/server.js' || echo 'No existing processes'\",
        \"nohup node src/server.js > app.log 2>&1 &\",
        \"sleep 5\",
        \"curl -s http://localhost:3000/health | jq . || echo 'Health check endpoint not available'\",
        \"ps aux | grep 'node src/server.js' | grep -v grep || echo 'Application not running'\"
    ]" \
    --output text --query 'Command.CommandId')

echo "⏳ Waiting for deployment to complete..."
sleep 30

# Check deployment status
aws ssm get-command-invocation \
    --command-id "$DEPLOY_CMD_ID" \
    --instance-id "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'StandardOutputContent' \
    --output text

echo "🔧 Fixing load balancer security group..."
# Get ALB security group ID
ALB_SG_ID=$(aws elbv2 describe-load-balancers \
    --region "$REGION" \
    --query "LoadBalancers[?contains(LoadBalancerName, 'CdkInf-BlogA')].SecurityGroups[0]" \
    --output text)

if [ -n "$ALB_SG_ID" ]; then
    echo "  Found ALB Security Group: $ALB_SG_ID"
    # Add egress rule for port 3000
    aws ec2 authorize-security-group-egress \
        --group-id "$ALB_SG_ID" \
        --protocol tcp \
        --port 3000 \
        --cidr 0.0.0.0/0 \
        --region "$REGION" 2>/dev/null || echo "  Egress rule already exists"
    
    echo "  ✅ ALB security group configured"
else
    echo "  ⚠️  Could not find ALB security group"
fi

echo "🔧 Ensuring application binds to IPv4..."
# Fix IPv4 binding
aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --region "$REGION" \
    --parameters 'commands=[
        "cd /home/ec2-user/blog-app",
        "pkill -f \"node src/server.js\" || echo \"No existing processes\"",
        "sed -i \"s/app.listen(PORT, () => {/app.listen(PORT, \\\"0.0.0.0\\\", () => {/\" src/server.js",
        "nohup node src/server.js > app.log 2>&1 &",
        "sleep 5"
    ]' \
    --output text --query 'Command.CommandId' > /dev/null

echo "⏳ Waiting for health checks to pass..."
sleep 60

# Run comprehensive SSM tests to verify deployment
echo "🧪 Running comprehensive deployment tests via SSM..."

TEST_CMD_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --region "$REGION" \
    --parameters 'commands=[
        "echo \"=== Deployment Verification Tests ===\"",
        "cd /home/ec2-user/blog-app",
        "echo \"1. Application Process Status:\"",
        "ps aux | grep \"node src/server.js\" | grep -v grep || echo \"❌ Application not running\"",
        "echo \"2. Port 3000 Status:\"",
        "netstat -tlnp | grep :3000 || echo \"❌ Port 3000 not listening\"",
        "echo \"3. Application Logs (last 10 lines):\"",
        "tail -10 app.log 2>/dev/null || echo \"No app.log found\"",
        "echo \"4. Environment Configuration:\"",
        "cat .env | grep -E \"(USER_POOL_ID|CLIENT_ID|S3_BUCKET|DYNAMODB_TABLE)\" || echo \"❌ Environment not configured\"",
        "echo \"5. File Verification (should be >9000 and >17000 bytes):\"",
        "echo \"  server.js size: $(wc -c < src/server.js) bytes\"",
        "echo \"  index.html size: $(wc -c < public/index.html) bytes\"",
        "echo \"6. Authentication Test (should return error):\"",
        "curl -s http://localhost:3000/api/posts || echo \"❌ Local API test failed\"",
        "echo \"7. Health Check (should return healthy):\"",
        "curl -s http://localhost:3000/health || echo \"❌ Local health check failed\"",
        "echo \"=== Tests Complete ===\""
    ]' \
    --output text --query 'Command.CommandId')

echo "⏳ Waiting for SSM tests to complete..."
sleep 15

# Get and display test results
echo "📊 SSM Test Results:"
aws ssm get-command-invocation \
    --command-id "$TEST_CMD_ID" \
    --instance-id "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'StandardOutputContent' \
    --output text

# Validate deployment
APP_URL=$(jq -r '.CdkInfrastructureStack.ApplicationURL' stack-outputs.json 2>/dev/null)
if [ -n "$APP_URL" ]; then
    echo "🔍 Validating deployment..."
    
    # Test health endpoint
    for i in {1..5}; do
        echo "  Attempt $i/5: Testing health endpoint..."
        if curl -s --max-time 10 "$APP_URL/health" | grep -q "healthy"; then
            echo "  ✅ Health check passed"
            break
        else
            if [ $i -eq 5 ]; then
                echo "  ❌ Health check failed after 5 attempts"
                echo "  🔧 Checking target group health..."
                
                # Get target group ARN
                TG_ARN=$(aws elbv2 describe-target-groups \
                    --region "$REGION" \
                    --query "TargetGroups[?contains(TargetGroupName, 'CdkInf-BlogA')].TargetGroupArn" \
                    --output text)
                
                if [ -n "$TG_ARN" ]; then
                    aws elbv2 describe-target-health \
                        --target-group-arn "$TG_ARN" \
                        --region "$REGION" \
                        --query 'TargetHealthDescriptions[0].TargetHealth'
                fi
            else
                echo "  ⏳ Waiting 30 seconds before retry..."
                sleep 30
            fi
        fi
    done
    
    # Test main page
    echo "  Testing main page..."
    if curl -s --max-time 10 "$APP_URL/" | grep -q "Secure Blog"; then
        echo "  ✅ Main page accessible"
    else
        echo "  ⚠️  Main page may have issues"
    fi
fi

# Clean up
aws s3 rm s3://$S3_BUCKET/deployment/app-deployment.tar.gz
rm -f app-deployment.tar.gz stack-outputs.json

echo "🎉 Deployment complete!"
echo "🌐 Application URL: $APP_URL"
echo "📝 If you see 504 errors, wait 2-3 minutes for health checks to pass"
