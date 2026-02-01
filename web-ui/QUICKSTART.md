# Quick Start Guide - AgentCore Deployment Dashboard

## Overview

The web UI provides a beautiful dashboard to manage both Amazon ECS and EKS deployments using your AgentCore agents. It includes:

✅ **Amazon ECS Operations**: List, Deploy, Delete services
✅ **EKS Operations**: Check status, Deploy, Delete deployments
✅ **Real-time logs**: Color-coded output with timestamps
✅ **Deployment forms**: Full configuration options for both platforms

## Setup (One-time)

### 1. Install Dependencies

```bash
cd web-ui
pip3 install -r requirements.txt
```

### 2. Verify Configuration

The `app.py` file is already configured with your agent ARNs:
- **Amazon ECS Agent**: `ecs_deployment_agent-Kq38Lc3cm5`
- **EKS Agent**: `eks_deployment_agent-bJq2whDHLA`
- **Agent Region**: us-west-2
- **Account**: <AWS_ACCOUNT_ID>

## Running the Dashboard

```bash
cd web-ui
python3 app.py
```

Then open your browser to: **http://localhost:5001**

## Using the Dashboard

### Amazon ECS Deployment

1. Click **"➕ Deploy New Service"** button
2. Fill in the form:
   - **Service Name**: Optional (auto-generated if empty)
   - **Image URI**: Your ECR image (e.g., `<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app:latest`)
   - **CPU**: Select from 256-2048
   - **Memory**: Select from 512-4096 MB
   - **Port**: Default 3000
   - **Environment Variables**: JSON format (optional)
3. Click **"🚀 Deploy"**
4. Watch the real-time logs

### EKS Deployment

1. Click **"➕ Deploy New App"** button
2. **Prerequisites** (one-time setup):
   - Click **"🔐 Setup OIDC"** (if not already done)
   - Fill in Amazon S3 bucket and Amazon DynamoDB table
   - Click **"🔑 Create IRSA Role"** (copies ARN to form)
3. Fill in the deployment form:
   - **Image URI**: Your ECR image
   - **Replicas**: Number of pods (default 2)
   - **Port**: Default 3000
   - **IAM Role ARN**: Auto-filled from IRSA setup
   - **Environment Variables**: JSON format (optional)
4. Click **"🚀 Deploy"**
5. Watch the real-time logs

### Other Operations

**Amazon ECS:**
- **📋 List Services**: View all Amazon ECS services in selected region
- **🔍 Check Stacks**: View AWS CloudFormation stacks
- **🗑️ Delete Service**: Remove service and all resources

**EKS:**
- **📊 Check Status**: View deployment status, replicas, availability
- **🗑️ Delete Deployment**: Remove Deployment, Service, ServiceAccount

## Example: Deploy Sample Application

### To Amazon ECS (eu-north-1)

1. Select region: **eu-north-1**
2. Click **"➕ Deploy New Service"**
3. Enter image URI: `<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app:latest`
4. Set CPU: **512**, Memory: **1024**
5. Add environment variables:
   ```json
   {
     "AWS_REGION": "eu-north-1",
     "PORT": "3000",
     "NODE_ENV": "production"
   }
   ```
6. Click **"🚀 Deploy"**

### To EKS (eu-north-1)

1. Enter cluster: **ec2-eks-migration**
2. Enter app name: **blog-app-eks-v4**
3. Select region: **eu-north-1**
4. Click **"➕ Deploy New App"**
5. Setup prerequisites (if needed):
   - Click **"🔐 Setup OIDC"**
   - Enter Amazon S3 bucket: `blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1`
   - Enter Amazon DynamoDB table: `blog-posts`
   - Click **"🔑 Create IRSA Role"**
6. Enter image URI: `<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app:latest`
7. Set replicas: **2**
8. Add environment variables:
   ```json
   {
     "PORT": "3000",
     "NODE_ENV": "production",
     "AWS_REGION": "eu-north-1"
   }
   ```
9. Click **"🚀 Deploy"**

## Features

### Real-time Logs
- **Blue (Info)**: General information
- **Green (Success)**: Successful operations
- **Red (Error)**: Errors and failures
- **Orange (Warning)**: Warnings

### Auto-scroll
Logs automatically scroll to the latest entry

### Form Validation
- Required fields are validated
- JSON environment variables are parsed and validated
- Confirmation dialogs for destructive operations

## Troubleshooting

### "Connection refused"
- Ensure AWS credentials are configured: `aws sts get-caller-identity`
- Check agent ARNs are correct in `app.py`

### "Agent not found"
- Verify agents are deployed: Check agent directories
- Confirm agent region is us-west-2

### "Permission denied"
- Run permission setup scripts in agent directories
- Check IAM permissions for AgentCore, Amazon ECS, EKS

## Architecture

```
Browser (localhost:5001)
    ↓ HTTP
Flask Server (app.py)
    ↓ AWS SigV4 Signed Requests
AgentCore Agents (us-west-2)
    ├─ Amazon ECS Agent (Strands Protocol)
    └─ EKS Agent (MCP Protocol)
    ↓
AWS Services (any region)
    ├─ Amazon ECS Express Mode
    ├─ EKS Kubernetes
    └─ CloudFormation
```

## Next Steps

1. **Test the UI**: Deploy a sample application
2. **Monitor logs**: Watch real-time operation progress
3. **Clean up**: Use delete operations to remove test deployments
4. **Customize**: Modify `app.py` for additional operations

## Support

For issues or questions, refer to:
- `web-ui/README.md` - Full documentation
- `docs/` - Project documentation
- Agent README files for tool details

---

**Ready to deploy!** 🚀
