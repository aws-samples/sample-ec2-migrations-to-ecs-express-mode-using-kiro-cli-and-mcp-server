# Deploy Script - Region Configuration

## Updated for Multi-Region Support

The `deploy.sh` script now supports deploying to any AWS region.

## Usage

### Deploy to eu-north-1 (default)
```bash
cd scripts/deployment
./deploy.sh
```

### Deploy to specific region
```bash
cd scripts/deployment
./deploy.sh us-west-2
./deploy.sh eu-west-1
./deploy.sh ap-southeast-1
```

## What the Script Does

1. **Accepts region parameter** (defaults to eu-north-1)
2. **Builds CDK project**
3. **Deploys infrastructure** to specified region:
   - Amazon Cognito User Pool
   - Amazon DynamoDB Table
   - Amazon S3 Bucket
   - Amazon EC2 Instance with ALB
4. **Auto-detects region** from stack outputs
5. **Configures application** with correct region settings
6. **Deploys application** to Amazon EC2 instance

## Changes Made

### deploy.sh
- Added `DEPLOY_REGION` parameter (line 15)
- Set environment variables for CDK (lines 27-28)
- Added `--region` flag to CDK deploy (line 29)
- Auto-detect region from User Pool ID (line 40)

### CDK (already configured)
- Uses `CDK_DEFAULT_REGION` environment variable
- Uses `AWS_REGION` environment variable

## Current Deployments

### eu-north-1 (Active)
- **User Pool:** <COGNITO_USER_POOL_ID>
- **Client ID:** 2jeg8fcbjubj36g2ndrk5bqjaa
- **Amazon S3 Bucket:** blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1
- **Amazon DynamoDB:** blog-posts
- **Amazon EC2 Instance:** i-027991bd8f7d81ce9
- **ALB:** CdkInf-BlogA-i1h5g03DNKXW-1062393157.eu-north-1.elb.amazonaws.com

### us-west-2 (Active)
- **User Pool:** us-west-2_vdR00IukT
- **Client ID:** 3481skh6ioml3k285jrpu6o054
- **Amazon S3 Bucket:** blog-images-private-<AWS_ACCOUNT_ID>-us-west-2
- **Amazon DynamoDB:** blog-posts
- **Amazon EC2 Instance:** i-03b01c4ade6558dd0
- **ALB:** CdkInf-BlogA-AtLCbiOgIq30-375679884.us-west-2.elb.amazonaws.com

## Verification

After deployment, verify the stack:
```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name CdkInfrastructureStack \
  --region eu-north-1 \
  --query 'Stacks[0].StackStatus'

# Get outputs
aws cloudformation describe-stacks \
  --stack-name CdkInfrastructureStack \
  --region eu-north-1 \
  --query 'Stacks[0].Outputs'
```

## Notes

- The script automatically detects the region from stack outputs
- All AWS CLI commands use the detected region
- The sample-application/.env file is updated with correct region settings
- Each region has its own isolated resources (Amazon Cognito, Amazon S3, Amazon DynamoDB)
