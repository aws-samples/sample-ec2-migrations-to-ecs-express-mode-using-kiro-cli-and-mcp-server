# Blog App CDK Infrastructure

This CDK stack deploys the blog application on Amazon EC2 with Amazon DynamoDB and Amazon S3 backend.

## Architecture

```
Internet → ALB → Amazon EC2 Instance → Amazon DynamoDB + S3
```

## Resources Created

- **Amazon EC2 Instance**: t3.micro running the Node.js application
- **Amazon DynamoDB Table**: `blog-posts` for storing post metadata
- **Amazon S3 Bucket**: For storing uploaded images
- **VPC**: Custom VPC with public/private subnets
- **Security Groups**: HTTP (80) and SSH (22) access
- **IAM Role**: Amazon EC2 permissions for Amazon DynamoDB and S3

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **CDK installed**: `npm install -g aws-cdk`
3. **Key Pair**: Create `blog-app-key` in Amazon EC2 console for SSH access

## Deployment

```bash
# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy the stack
cdk deploy

# View outputs
cdk deploy --outputs-file outputs.json
```

## Accessing the Application

After deployment:
1. Note the `ApplicationURL` from CDK outputs
2. Access the blog at `http://<public-ip>`
3. SSH access: Use the key pair or SSM Session Manager

## Environment Variables

The Amazon EC2 instance automatically configures:
- `AWS_REGION`: Current deployment region
- `DYNAMODB_TABLE`: blog-posts
- `Amazon S3_BUCKET`: Generated bucket name
- `PORT`: 80

## Monitoring

- **CloudWatch Logs**: Application logs available in CloudWatch
- **Health Check**: `/health` endpoint for monitoring
- **SSM**: Session Manager access without SSH keys

## Cleanup

```bash
cdk destroy
```

## Migration to ECS

This Amazon EC2 deployment serves as the baseline for migration to Amazon ECS Express Mode, demonstrating:
- Containerization readiness
- AWS service integrations
- Health check endpoints
- Environment-based configuration
