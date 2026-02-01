# Container Migration MCP Server - Deployment Guide

## Overview

The Container Migration MCP Server is a Model Context Protocol (MCP) server that automates the containerization and Amazon ECS Express Mode deployment process for migrating Amazon EC2 applications to AWS Amazon ECS. It provides both local and serverless deployment options.

## What It Does

This MCP server provides automated tools and resources for:

### 🛠️ Containerization Tools
- **optimize_dockerfile** - Generate production-ready Dockerfiles with security recommended practices
- **build_and_push_container** - Automated ECR repository creation, image build, and push workflow
- **test_container_locally** - Local container testing with environment variables
- **validate_container_security** - Security validation for Dockerfiles (checks for non-root users, health checks, etc.)

### 🚀 Amazon ECS Express Mode Tools
- **deploy_ecs_express_service** - Deploy containerized applications to Amazon ECS Express Mode
- **validate_ecs_prerequisites** - Check Amazon ECS deployment prerequisites (IAM roles, ECR images)
- **check_ecs_service_status** - Monitor Amazon ECS service deployment status and health

### 📚 Resources
- **dockerfile-template** - Optimized Dockerfile template for Node.js applications
- **docker-compose-template** - Local development configuration
- **build-script** - Automated build and push script for ECR
- **iam-roles-template** - Required IAM roles for Amazon ECS Express Mode
- **deployment-guide** - Step-by-step Amazon ECS deployment guide

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  MCP Client (Kiro/Claude)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ MCP Protocol (stdio/HTTP)
                     │
┌────────────────────▼────────────────────────────────────┐
│            Container Migration MCP Server                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Tools: optimize_dockerfile, build_and_push,    │  │
│  │         validate_security, deploy_ecs, etc.     │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Resources: Templates, Scripts, Guides          │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ AWS SDK/CLI
                     │
┌────────────────────▼────────────────────────────────────┐
│                    AWS Services                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   ECR    │  │   Amazon ECS    │  │   IAM    │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

## Deployment Options

### Option 1: Local Deployment (Recommended for Development)

Run the MCP server locally using stdio communication.

#### Prerequisites
- Python 3.8+
- Docker installed and running
- AWS CLI configured with credentials
- MCP SDK installed

#### Installation

```bash
cd mcp-servers/container-migration

# Install dependencies
pip install -r requirements.txt

# Make server executable
chmod +x server.py

# Test the server
./test.sh
```

#### Configuration

Add to your MCP client configuration (e.g., Kiro's `mcp.json`):

```json
{
  "mcpServers": {
    "container-migration": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp-servers/container-migration/server.py"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "default"
      }
    }
  }
}
```

#### Usage Example

Once configured, you can use the MCP server through your MCP client:

```
# In Kiro or Claude Desktop
"Optimize the Dockerfile for my application at /path/to/app"
"Build and push my container to ECR with name 'my-app' and tag 'v1.0.0'"
"Validate the security of my Dockerfile"
"Deploy my application to Amazon ECS Express Mode"
```

### Option 2: Serverless Deployment (AWS AWS Lambda)

Deploy the MCP server as a serverless API using AWS SAM.

#### Prerequisites
- AWS SAM CLI installed (`pip install aws-sam-cli`)
- AWS CLI configured
- Docker installed (for SAM build)

#### Deployment Steps

```bash
cd mcp-servers/container-migration

# Build the SAM application
sam build

# Deploy with guided prompts
sam deploy --guided

# Or use the deployment script
chmod +x deploy.sh
./deploy.sh
```

#### Deployment Configuration

During `sam deploy --guided`, you'll be prompted for:
- **Stack Name**: `container-migration-mcp` (or your choice)
- **AWS Region**: `us-west-2` (or your preferred region)
- **Environment**: `dev`, `staging`, or `prod`
- **Confirm changes**: Review AWS CloudFormation changeset
- **Allow SAM CLI IAM role creation**: Yes
- **Save arguments to samconfig.toml**: Yes

#### Post-Deployment

After deployment, SAM outputs:
- **ApiUrl**: The API Gateway endpoint URL
- **ApiKey**: API key for authentication
- **FunctionName**: AWS Lambda function name

Example output:
```
CloudFormation outputs from deployed stack
---------------------------------------------------------------------------
Outputs
---------------------------------------------------------------------------
Key                 ApiUrl
Description         API Gateway endpoint URL
Value               https://abc123xyz.execute-api.us-west-2.amazonaws.com/Prod

Key                 ApiKey
Description         API Key for authentication
Value               abc123def456ghi789

Key                 FunctionName
Description         AWS Lambda function name
Value               container-migration-mcp-dev
---------------------------------------------------------------------------
```

#### Testing the Serverless Deployment

```bash
# Test using the provided test script
python3 test_mcp_server.py https://abc123xyz.execute-api.us-west-2.amazonaws.com/Prod

# Or test individual endpoints
curl -X GET https://abc123xyz.execute-api.us-west-2.amazonaws.com/Prod/resources/dockerfile-template

curl -X POST https://abc123xyz.execute-api.us-west-2.amazonaws.com/Prod/tools/optimize_dockerfile \
  -H "Content-Type: application/json" \
  -d '{"base_image": "node:18-alpine", "port": 3000}'
```

#### Using the Serverless API

You can interact with the serverless deployment using:

1. **Python Client** (provided):
```bash
python3 client.py
# Enter API URL when prompted
```

2. **Direct HTTP Requests**:
```bash
# Get Dockerfile template
curl https://your-api-url/resources/dockerfile-template

# Optimize Dockerfile
curl -X POST https://your-api-url/tools/optimize_dockerfile \
  -H "Content-Type: application/json" \
  -d '{"base_image": "node:18-alpine", "port": 3000}'

# Validate security
curl -X POST https://your-api-url/tools/validate_container_security \
  -H "Content-Type: application/json" \
  -d '{"dockerfile_content": "FROM node:18-alpine\n..."}'
```

## Available Tools

### 1. optimize_dockerfile

Creates a production-ready Dockerfile with security recommended practices.

**Parameters:**
- `app_path` (string, required): Path to application directory
- `base_image` (string, optional): Base Docker image (default: "node:18-alpine")
- `port` (integer, optional): Application port (default: 3000)

**Example:**
```python
optimize_dockerfile(
    app_path="/path/to/app",
    base_image="node:18-alpine",
    port=3000
)
```

**Output:**
- Creates `Dockerfile` in the application directory
- Includes non-root user, health checks, production dependencies

### 2. build_and_push_container

Builds Docker image and pushes to Amazon ECR.

**Parameters:**
- `app_path` (string, required): Path to application directory with Dockerfile
- `app_name` (string, required): Application name for ECR repository
- `tag` (string, optional): Image tag (default: "v1.0.0")
- `region` (string, optional): AWS region (default: "us-west-2")

**Example:**
```python
build_and_push_container(
    app_path="/path/to/app",
    app_name="my-app",
    tag="v1.0.0",
    region="us-west-2"
)
```

**Output:**
- Creates ECR repository if it doesn't exist
- Builds Docker image for linux/amd64 platform
- Pushes image to ECR
- Returns full image URI

### 3. test_container_locally

Tests container locally with environment variables.

**Parameters:**
- `app_path` (string, required): Path to application directory
- `image_name` (string, required): Docker image name to test
- `env_vars` (object, optional): Environment variables for testing
- `port` (integer, optional): Port to expose (default: 3000)

**Example:**
```python
test_container_locally(
    app_path="/path/to/app",
    image_name="my-app:v1.0.0",
    env_vars={
        "AWS_REGION": "us-west-2",
        "DYNAMODB_TABLE": "my-table"
    },
    port=3000
)
```

### 4. validate_container_security

Validates Dockerfile security recommended practices.

**Parameters:**
- `dockerfile_path` (string, required): Path to Dockerfile to validate

**Example:**
```python
validate_container_security(
    dockerfile_path="/path/to/app/Dockerfile"
)
```

**Checks:**
- Non-root user execution
- Health check presence
- Production dependencies
- Selective file copying
- Security score calculation

### 5. deploy_ecs_express_service

Deploys containerized application to Amazon ECS Express Mode.

**Parameters:**
- `service_name` (string, required): Name for the Amazon ECS Express service
- `image_uri` (string, required): Full ECR image URI with tag
- `environment_vars` (object, optional): Environment variables for the container
- `cpu` (string, optional): CPU units (default: "256")
- `memory` (string, optional): Memory in MB (default: "512")
- `port` (integer, optional): Container port (default: 3000)
- `region` (string, optional): AWS region (default: "us-west-2")

**Example:**
```python
deploy_ecs_express_service(
    service_name="my-app-express",
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0.0",
    environment_vars={
        "AWS_REGION": "us-west-2",
        "DYNAMODB_TABLE": "my-table"
    },
    cpu="512",
    memory="1024",
    port=3000
)
```

### 6. validate_ecs_prerequisites

Validates Amazon ECS Express Mode prerequisites.

**Parameters:**
- `image_uri` (string, required): ECR image URI to validate
- `region` (string, optional): AWS region (default: "us-west-2")

**Example:**
```python
validate_ecs_prerequisites(
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0.0"
)
```

**Checks:**
- Container image exists in ECR
- ecsTaskExecutionRole exists
- ecsInfrastructureRoleForExpressServices exists

### 7. check_ecs_service_status

Monitors Amazon ECS Express service deployment status.

**Parameters:**
- `service_arn` (string, required): Amazon ECS Express service ARN
- `region` (string, optional): AWS region (default: "us-west-2")

**Example:**
```python
check_ecs_service_status(
    service_arn="arn:aws:ecs:us-west-2:123456789012:express-service/my-app-express"
)
```

## Complete Migration Workflow

### Phase 1: Containerization

```bash
# 1. Optimize Dockerfile
optimize_dockerfile(app_path="/path/to/app", port=3000)

# 2. Validate security
validate_container_security(dockerfile_path="/path/to/app/Dockerfile")

# 3. Test locally
test_container_locally(
    app_path="/path/to/app",
    image_name="my-app:test",
    env_vars={"PORT": "3000"}
)
```

### Phase 2: ECR Push

```bash
# Build and push to ECR
build_and_push_container(
    app_path="/path/to/app",
    app_name="my-app",
    tag="v1.0.0"
)
```

### Phase 3: Amazon ECS Deployment

```bash
# 1. Validate prerequisites
validate_ecs_prerequisites(
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0.0"
)

# 2. Deploy to Amazon ECS Express Mode
deploy_ecs_express_service(
    service_name="my-app-express",
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0.0",
    environment_vars={"AWS_REGION": "us-west-2"}
)

# 3. Monitor deployment
check_ecs_service_status(
    service_arn="arn:aws:ecs:us-west-2:123456789012:express-service/my-app-express"
)
```

## Troubleshooting

### Local Deployment Issues

**Server won't start:**
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Install dependencies
pip install -r requirements.txt

# Check for syntax errors
python3 -m py_compile server.py
```

**MCP client can't connect:**
- Verify the absolute path in mcp.json
- Check that server.py is executable: `chmod +x server.py`
- Test server manually: `python3 server.py`

### Serverless Deployment Issues

**SAM build fails:**
```bash
# Ensure Docker is running
docker ps

# Clean and rebuild
sam build --use-container
```

**Deployment fails:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify IAM permissions for AWS CloudFormation, AWS Lambda, API Gateway
```

**API returns errors:**
```bash
# Check AWS Lambda logs
aws logs tail /aws/lambda/container-migration-mcp-dev --follow

# Test AWS Lambda directly
aws lambda invoke --function-name container-migration-mcp-dev output.json
```

### Container Build Issues

**Docker build fails:**
- Ensure Docker daemon is running: `docker ps`
- Check Dockerfile syntax
- Verify base image is accessible

**ECR push fails:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check ECR permissions
- Ensure repository exists or can be created

### Amazon ECS Deployment Issues

**Prerequisites validation fails:**
```bash
# Create missing IAM roles
aws iam create-role --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

**Service deployment fails:**
- Check CloudWatch logs: `/ecs/[service-name]`
- Verify image URI is correct
- Ensure IAM roles have proper permissions
- Check VPC and subnet configuration

## Security Considerations

### IAM Permissions

The MCP server requires the following AWS permissions:

```json
<!-- Security: In production, replace Resource: "*" with specific ARN -->
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "ecs:*",
        "iam:GetRole",
        "iam:PassRole",
        "sts:GetCallerIdentity",
        "logs:*",
        "elasticloadbalancing:*",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

### Recommended Practices

1. **Use least privilege IAM roles** - Only grant necessary permissions
2. **Secure API keys** - For serverless deployment, rotate API keys regularly
3. **Environment variables** - Never commit sensitive data to version control
4. **Container security** - Always run containers as non-root users
5. **Network security** - Use VPC endpoints for ECR and Amazon ECS communication

## Cost Considerations

### Local Deployment
- **Free** - No AWS charges for running locally
- Only pay for AWS resources created (ECR storage, Amazon ECS tasks)

### Serverless Deployment
- **AWS Lambda**: Free tier includes 1M requests/month
- **API Gateway**: Free tier includes 1M API calls/month
- **CloudWatch Logs**: $0.50/GB ingested
- **Typical cost**: $5-20/month for moderate usage

## Support

For issues or questions:
- Check the troubleshooting section above
- Review CloudWatch logs for detailed error messages
- Consult AWS Amazon ECS and ECR documentation
- Open an issue in the project repository

## License

This MCP server is part of the Amazon EC2 to Amazon ECS migration project and is provided as-is for educational and demonstration purposes.
