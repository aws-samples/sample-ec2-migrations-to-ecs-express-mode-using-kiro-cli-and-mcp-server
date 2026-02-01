# Container Migration & Amazon ECS Express Mode MCP Server

Automates containerization and Amazon ECS Express Mode deployment for Amazon EC2 to Amazon ECS migration.

## Features

### 🛠️ Containerization Tools
- **optimize_dockerfile**: Create production-ready Dockerfile with security recommended practices
- **build_and_push_container**: Automated ECR build and push workflow
- **test_container_locally**: Local container testing with environment variables
- **validate_container_security**: Security validation for Dockerfiles

### 🚀 Amazon ECS Express Mode Tools
- **deploy_ecs_express_service**: Deploy containerized app to Amazon ECS Express Mode
- **validate_ecs_prerequisites**: Check Amazon ECS deployment prerequisites
- **check_ecs_service_status**: Monitor Amazon ECS service deployment status

### 📚 Resources
- **dockerfile-template**: Optimized Dockerfile template for Node.js apps
- **docker-compose-template**: Local development configuration
- **build-script**: Automated build and push script
- **iam-roles-template**: Required IAM roles for Amazon ECS Express Mode
- **deployment-guide**: Step-by-step Amazon ECS deployment guide

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Make executable
chmod +x server.py

# Test
./test.sh
```

## MCP Client Configuration

```json
{
  "mcpServers": {
    "container-migration": {
      "command": "python3",
      "args": ["./mcp-servers/container-migration/server.py"]
    }
  }
}
```

## Usage

### Optimize Dockerfile
```python
optimize_dockerfile(
    app_path="/path/to/app",
    base_image="node:18-alpine",
    port=3000
)
```

### Build and Push to ECR
```python
build_and_push_container(
    app_path="/path/to/app",
    app_name="secure-blog",
    tag="v1.0.0",
    region="us-west-2"
)
```

### Test Locally
```python
test_container_locally(
    app_path="/path/to/app",
    image_name="secure-blog:v1.0.0",
    env_vars={
        "AWS_REGION": "us-west-2",
        "DYNAMODB_TABLE": "blog-posts"
    }
)
```

### Deploy to Amazon ECS Express Mode
```python
# Validate prerequisites
validate_ecs_prerequisites(
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0"
)

# Deploy service
deploy_ecs_express_service(
    service_name="secure-blog-express",
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0",
    environment_vars={
        "AWS_REGION": "us-west-2",
        "DYNAMODB_TABLE": "blog-posts",
        "Amazon S3_BUCKET": "my-bucket",
        "COGNITO_USER_POOL_ID": "us-west-2_abc123",
        "COGNITO_CLIENT_ID": "abc123def456"
    }
)

# Check deployment status
check_ecs_service_status(
    service_arn="arn:aws:ecs:us-west-2:123456789012:express-service/secure-blog-express"
)
```

## Security Features

- ✅ Non-root user execution
- ✅ Health check integration
- ✅ Production dependency optimization
- ✅ Minimal attack surface
- ✅ Proper file ownership

## Prerequisites

- Docker installed and running
- AWS CLI configured
- Python 3.8+ with MCP dependencies
