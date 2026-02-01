# Infrastructure

This directory contains all Infrastructure as Code (IaC) components for the Amazon EC2 to Amazon ECS migration project.

## Structure

### CDK Infrastructure (`cdk/`)
Complete Amazon EC2 infrastructure deployment using AWS CDK:
- **Amazon EC2 Instance**: Application server with security groups
- **Application Load Balancer**: Public-facing load balancer
- **Amazon DynamoDB Table**: Blog posts storage
- **Amazon S3 Bucket**: Image storage with proper policies
- **Amazon Cognito**: User authentication and authorization
- **IAM Roles**: Proper permissions for Amazon EC2 instance

**Usage:**
```bash
cd cdk
npm install
cdk deploy
```

### MCP Server (`mcp-server/`)
Model Context Protocol server implementations:

#### AWS Lambda-based MCP Server (`container-migration/`)
- **Serverless deployment** using AWS SAM
- **API Gateway integration** with API key authentication
- **Complete Amazon ECS automation** including cluster creation
- **Proper resource tagging** for cleanup
- **IAM role management** with dynamic policy attachment

**Features:**
- Dockerfile optimization
- Container build and ECR push
- Amazon ECS Express Mode deployment
- Prerequisites validation
- Service status monitoring

**Usage:**
```bash
cd mcp-server/container-migration
sam build && sam deploy
```

#### Local MCP Server (`server.py`)
- **Development version** for local testing
- **Same functionality** as AWS Lambda version
- **Direct AWS CLI integration**

## Configuration

### Environment Variables
```bash
export MCP_API_URL="https://your-api-gateway-url/Prod"
export MCP_API_KEY="your-api-key"
export AWS_REGION="us-west-2"
```

### Resource Tagging
All resources are tagged with:
- `Project: Amazon ECS-Express-Migration`
- `ManagedBy: MCP-Server`
- `ServiceName: {service-name}`
- `Environment: Demo`
- `AutoCleanup: true`

## Deployment Flow

1. **Deploy CDK Infrastructure**: Creates Amazon EC2 environment
2. **Deploy MCP Server**: Enables automation capabilities
3. **Run Migration**: Uses MCP server to migrate to ECS
4. **Monitor & Validate**: Check deployment status
5. **Cleanup**: Tag-based resource cleanup
