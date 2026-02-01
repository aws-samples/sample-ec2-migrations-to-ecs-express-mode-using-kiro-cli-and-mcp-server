# EKS Deployment Test Scripts

This directory contains test scripts for deploying applications to Amazon EKS with IRSA (IAM Roles for Service Accounts).

## Files

- `test_eks_deployment.py` - Main deployment script with IRSA configuration
- `.env.example` - Example configuration file with all available options
- `.env` - Actual configuration file (not committed to git)
- `requirements.txt` - Python dependencies

## Quick Start

### 1. Install Dependencies

```bash
pip install python-dotenv boto3
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example configuration and edit with your values:

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run Deployment

```bash
python test_eks_deployment.py
```

## Configuration

The script uses environment variables from the `.env` file. All configuration is dynamic with no hardcoded values.

### Required Configuration

```bash
# EKS Cluster
EKS_CLUSTER_NAME=your-cluster-name
EKS_REGION=us-west-2

# Application
APP_NAME=my-app
APP_PATH=/path/to/your/application
IMAGE_NAME=my-app-image

# AWS Resources
S3_BUCKET=your-s3-bucket
DYNAMODB_TABLE=your-dynamodb-table
```

### Optional Configuration

```bash
# Application Settings
PORT=3000
REPLICAS=2
NODE_ENV=production

# Amazon Cognito (if using authentication)
COGNITO_USER_POOL_ID=your-pool-id
COGNITO_CLIENT_ID=your-client-id

# IRSA (auto-generated if not provided)
IRSA_ROLE_NAME=custom-role-name
SERVICE_ACCOUNT_NAME=custom-sa-name
```

## What the Script Does

1. **Loads Configuration** - Reads from `.env` file or environment variables
2. **Updates kubeconfig** - Configures kubectl for your EKS cluster
3. **Creates ECR Repository** - If it doesn't exist
4. **Sets up OIDC Provider** - Creates IAM OIDC identity provider for the cluster
5. **Creates IRSA Role** - IAM role with Amazon S3 and Amazon DynamoDB permissions
6. **Builds Docker Image** - With `--platform linux/amd64` for EKS compatibility
7. **Pushes to ECR** - Uploads image to Amazon ECR
8. **Deploys to EKS** - Creates ServiceAccount, Deployment, and LoadBalancer Service
9. **Waits for Ready** - Monitors deployment until pods are running
10. **Gets Endpoint** - Retrieves LoadBalancer URL
11. **Verifies IRSA** - Checks that service account token is mounted correctly

## Features

- ✅ **No Hardcoded Values** - All configuration from environment variables
- ✅ **IRSA Support** - Secure AWS access without credentials
- ✅ **Platform Compatibility** - Builds for linux/amd64 (EKS nodes)
- ✅ **Automatic OIDC Setup** - Creates OIDC provider if missing
- ✅ **LoadBalancer Configuration** - Internet-facing NLB with proper annotations
- ✅ **Health Checks** - Verifies deployment and IRSA configuration
- ✅ **Idempotent** - Safe to run multiple times

## Example Output

```
🚀 Starting EKS deployment to cluster...
================================================================================
Configuration:
  Cluster: ec2-eks-migration
  Region: eu-north-1
  App Name: blog-app-eks
  Image: blog-app-eks
  Replicas: 2
  Amazon S3 Bucket: blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1
  Amazon DynamoDB Table: blog-posts
================================================================================

STEP 1: Create ECR Repository
✓ Repository created or already exists

STEP 2: Build and Push Docker Image (linux/amd64 for EKS)
✓ Image built and pushed successfully

STEP 3: Create IAM OIDC Identity Provider and Role for Service Account (IRSA)
✓ OIDC provider created
✓ IAM role created with Amazon S3 and Amazon DynamoDB permissions

STEP 4: Deploy to EKS with IRSA
✓ Deployment successful

STEP 5: Waiting for Deployment
✓ Pods are running

STEP 6: Get Service Endpoint
🎉 Deployment successful!
📊 Endpoint: http://k8s-default-blogappe-xxx.elb.eu-north-1.amazonaws.com
📊 Replicas: 2
```

## Useful Commands

```bash
# Check application logs
kubectl logs -l app=blog-app-eks

# Check service account
kubectl describe sa blog-app-eks-sa

# Verify IRSA token mount
kubectl exec -it $(kubectl get pod -l app=blog-app-eks -o jsonpath='{.items[0].metadata.name}') -- ls -la /var/run/secrets/eks.amazonaws.com/serviceaccount/

# Test AWS credentials
kubectl exec -it $(kubectl get pod -l app=blog-app-eks -o jsonpath='{.items[0].metadata.name}') -- env | grep AWS

# Scale deployment
kubectl scale deployment/blog-app-eks --replicas=3

# Delete deployment
kubectl delete deployment,service,serviceaccount blog-app-eks blog-app-eks-sa

# Port forward for local testing
kubectl port-forward service/blog-app-eks 8080:80
```

## Troubleshooting

### Image Pull Errors

If you see "no match for platform in manifest" errors:
- Ensure Docker image is built with `--platform linux/amd64`
- The script automatically handles this

### Credential Errors

If you see "Could not load credentials" errors:
- Check that OIDC provider exists: `aws iam list-open-id-connect-providers`
- Verify IAM role trust policy includes correct OIDC provider
- Check service account annotation: `kubectl describe sa blog-app-eks-sa`
- Verify environment variables in pod: `kubectl describe pod -l app=blog-app-eks`

### LoadBalancer Not Ready

If LoadBalancer endpoint is not available:
- Check service status: `kubectl describe svc blog-app-eks`
- Verify subnet tags for EKS Auto Mode
- Check AWS Load Balancer Controller logs

## Environment Variables Reference

See `.env.example` for complete list of available configuration options.

## Security Notes

- Never commit `.env` file to version control
- Use IAM roles with minimal required permissions
- IRSA provides secure, scoped access without credentials
- Service account tokens are automatically rotated
