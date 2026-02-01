#!/usr/bin/env python3
"""
Container Migration MCP Server
Automates containerization and ECS Express Mode deployment for EC2 to ECS migration
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("container-migration-mcp")

app = Server("container-migration-mcp")

@app.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available containerization and ECS deployment resources"""
    return [
        Resource(
            uri="container://dockerfile-template",
            name="Optimized Dockerfile Template",
            description="Production-ready Dockerfile template for Node.js applications",
            mimeType="text/plain"
        ),
        Resource(
            uri="container://docker-compose-template", 
            name="Docker Compose Template",
            description="Local development Docker Compose configuration",
            mimeType="text/yaml"
        ),
        Resource(
            uri="container://build-script",
            name="Container Build Script",
            description="Automated build and push script for ECR",
            mimeType="text/x-shellscript"
        ),
        Resource(
            uri="ecs://iam-roles-template",
            name="ECS Express Mode IAM Roles",
            description="Required IAM roles for ECS Express Mode deployment",
            mimeType="application/json"
        ),
        Resource(
            uri="ecs://deployment-guide",
            name="ECS Express Mode Deployment Guide",
            description="Step-by-step guide for ECS Express Mode deployment",
            mimeType="text/markdown"
        )
    ]

@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read containerization resource content"""
    
    if uri == "container://dockerfile-template":
        return """FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY public/ ./public/

# Create uploads directory
RUN mkdir -p uploads

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Change ownership of the app directory
RUN chown -R nodejs:nodejs /app
USER nodejs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD node -e "require('http').get('http://localhost:3000/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

# Start application
CMD ["npm", "start"]"""

    elif uri == "container://docker-compose-template":
        return """version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - AWS_REGION=us-west-2
      - DYNAMODB_TABLE=blog-posts
      - S3_BUCKET=blog-images-private-<AWS_ACCOUNT_ID>-us-west-2
      - COGNITO_USER_POOL_ID=<COGNITO_USER_POOL_ID>
      - COGNITO_CLIENT_ID=<COGNITO_CLIENT_ID>
      - PORT=3000
    volumes:
      - ~/.aws:/home/nodejs/.aws:ro
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s"""

    elif uri == "container://build-script":
        return """#!/bin/bash
set -e

# Configuration
APP_NAME="${1:-secure-blog}"
TAG="${2:-v1.0.0}"
REGION="${3:-us-west-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Starting container build and push process..."
echo "App: $APP_NAME, Tag: $TAG, Region: $REGION, Account: $ACCOUNT_ID"

# Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository..."
aws ecr create-repository --repository-name $APP_NAME --region $REGION 2>/dev/null || echo "Repository already exists"

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build image for linux/amd64 platform (required for ECS Fargate)
echo "🔨 Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t $APP_NAME:$TAG .

# Tag for ECR
echo "🏷️  Tagging image for ECR..."
docker tag $APP_NAME:$TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME:$TAG

# Push to ECR
echo "⬆️  Pushing to ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME:$TAG

echo "✅ Container successfully pushed to ECR!"
echo "Image URI: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME:$TAG"
"""
    
    elif uri == "ecs://iam-roles-template":
        return """# ECS Express Mode Required IAM Roles

## 1. Task Execution Role (ecsTaskExecutionRole)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## 2. Infrastructure Role (ecsInfrastructureRoleForExpressServices)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Creation Commands:
```bash
# Create task execution role
aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file://task-execution-trust-policy.json
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create infrastructure role
aws iam create-role --role-name ecsInfrastructureRoleForExpressServices --assume-role-policy-document file://ecs-trust-policy.json
aws iam attach-role-policy --role-name ecsInfrastructureRoleForExpressServices --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices
```
"""
    
    elif uri == "ecs://deployment-guide":
        return """# ECS Express Mode Deployment Guide

## Prerequisites ✅
1. **Container Image**: Built and pushed to ECR
2. **IAM Roles**: Task execution and infrastructure roles created
3. **AWS CLI**: Configured with appropriate permissions

## Deployment Steps 🚀

### Step 1: Validate Prerequisites
```python
validate_ecs_prerequisites(
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0.0"
)
```

### Step 2: Deploy ECS Express Service
```python
deploy_ecs_express_service(
    service_name="my-app-express",
    image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:v1.0.0",
    environment_vars={
        "AWS_REGION": "us-west-2",
        "DYNAMODB_TABLE": "my-table",
        "S3_BUCKET": "my-bucket"
    },
    cpu="256",
    memory="512",
    port=3000
)
```

### Step 3: Monitor Deployment
```python
check_ecs_service_status(
    service_arn="arn:aws:ecs:us-west-2:123456789012:express-service/my-app-express"
)
```

## Benefits 📈
- **Zero Infrastructure Management**: No servers to patch or maintain
- **Automatic Scaling**: Scales based on demand
- **Built-in Load Balancing**: ALB provisioned automatically
- **Health Checks**: Container health monitoring included
- **Cost Optimization**: Pay only for actual usage

## Troubleshooting 🔧
- **Service not starting**: Check CloudWatch logs
- **Health checks failing**: Verify /health endpoint
- **Permission errors**: Validate IAM roles
- **Image pull errors**: Confirm ECR permissions
"""
    
    else:
        raise ValueError(f"Unknown resource: {uri}")

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available containerization tools"""
    return [
        Tool(
            name="optimize_dockerfile",
            description="Create or optimize Dockerfile for production deployment",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_path": {
                        "type": "string",
                        "description": "Path to application directory"
                    },
                    "base_image": {
                        "type": "string", 
                        "description": "Base Docker image (default: node:18-alpine)",
                        "default": "node:18-alpine"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Application port (default: 3000)",
                        "default": 3000
                    }
                },
                "required": ["app_path"]
            }
        ),
        Tool(
            name="build_and_push_container",
            description="Build Docker image and push to ECR repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_path": {
                        "type": "string",
                        "description": "Path to application directory with Dockerfile"
                    },
                    "app_name": {
                        "type": "string",
                        "description": "Application name for ECR repository"
                    },
                    "tag": {
                        "type": "string",
                        "description": "Image tag (default: v1.0.0)",
                        "default": "v1.0.0"
                    },
                    "region": {
                        "type": "string",
                        "description": "AWS region (default: us-west-2)",
                        "default": "us-west-2"
                    }
                },
                "required": ["app_path", "app_name"]
            }
        ),
        Tool(
            name="test_container_locally",
            description="Test container locally with environment variables",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_path": {
                        "type": "string",
                        "description": "Path to application directory"
                    },
                    "image_name": {
                        "type": "string",
                        "description": "Docker image name to test"
                    },
                    "env_vars": {
                        "type": "object",
                        "description": "Environment variables for testing",
                        "additionalProperties": {"type": "string"}
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port to expose (default: 3000)",
                        "default": 3000
                    }
                },
                "required": ["app_path", "image_name"]
            }
        ),
        Tool(
            name="validate_container_security",
            description="Validate container security best practices",
            inputSchema={
                "type": "object",
                "properties": {
                    "dockerfile_path": {
                        "type": "string",
                        "description": "Path to Dockerfile to validate"
                    }
                },
                "required": ["dockerfile_path"]
            }
        ),
        Tool(
            name="deploy_ecs_express_service",
            description="Deploy containerized application to ECS Express Mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Name for the ECS Express service"
                    },
                    "image_uri": {
                        "type": "string",
                        "description": "Full ECR image URI with tag"
                    },
                    "environment_vars": {
                        "type": "object",
                        "description": "Environment variables for the container"
                    },
                    "cpu": {
                        "type": "string",
                        "description": "CPU units (256, 512, 1024, etc.)",
                        "default": "256"
                    },
                    "memory": {
                        "type": "string", 
                        "description": "Memory in MB (512, 1024, 2048, etc.)",
                        "default": "512"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Container port",
                        "default": 3000
                    },
                    "region": {
                        "type": "string",
                        "description": "AWS region",
                        "default": "us-west-2"
                    }
                },
                "required": ["service_name", "image_uri"]
            }
        ),
        Tool(
            name="validate_ecs_prerequisites",
            description="Validate ECS Express Mode prerequisites",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_uri": {
                        "type": "string",
                        "description": "ECR image URI to validate"
                    },
                    "region": {
                        "type": "string",
                        "description": "AWS region",
                        "default": "us-west-2"
                    }
                },
                "required": ["image_uri"]
            }
        ),
        Tool(
            name="check_ecs_service_status",
            description="Check ECS Express service deployment status",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_arn": {
                        "type": "string",
                        "description": "ECS Express service ARN"
                    },
                    "region": {
                        "type": "string",
                        "description": "AWS region",
                        "default": "us-west-2"
                    }
                },
                "required": ["service_arn"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls for containerization operations"""
    
    if name == "optimize_dockerfile":
        app_path = arguments["app_path"]
        base_image = arguments.get("base_image", "node:18-alpine")
        port = arguments.get("port", 3000)
        
        dockerfile_content = f"""FROM {base_image}

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY public/ ./public/

# Create uploads directory
RUN mkdir -p uploads

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Change ownership of the app directory
RUN chown -R nodejs:nodejs /app
USER nodejs

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD node -e "require('http').get('http://localhost:{port}/health', (res) => {{ process.exit(res.statusCode === 200 ? 0 : 1) }})"

# Start application
CMD ["npm", "start"]"""

        dockerfile_path = Path(app_path) / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        return [TextContent(
            type="text",
            text=f"✅ Optimized Dockerfile created at {dockerfile_path}\n\nKey optimizations:\n- Non-root user for security\n- Multi-stage build ready\n- Health check included\n- Production dependencies only\n- Proper file ownership"
        )]
    
    elif name == "build_and_push_container":
        app_path = arguments["app_path"]
        app_name = arguments["app_name"]
        tag = arguments.get("tag", "v1.0.0")
        region = arguments.get("region", "us-west-2")
        
        try:
            # Get AWS account ID
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
                capture_output=True, text=True, check=True
            )
            account_id = result.stdout.strip()
            
            # Create ECR repository
            subprocess.run([
                "aws", "ecr", "create-repository", 
                "--repository-name", app_name,
                "--region", region
            ], capture_output=True)
            
            # Login to ECR
            login_result = subprocess.run([
                "aws", "ecr", "get-login-password", "--region", region
            ], capture_output=True, text=True, check=True)
            
            subprocess.run([
                "docker", "login", "--username", "AWS", "--password-stdin",
                f"{account_id}.dkr.ecr.{region}.amazonaws.com"
            ], input=login_result.stdout, text=True, check=True, cwd=app_path)
            
            # Build image
            subprocess.run([
                "docker", "build", "-t", f"{app_name}:{tag}", "."
            ], check=True, cwd=app_path)
            
            # Tag for ECR
            ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{app_name}:{tag}"
            subprocess.run([
                "docker", "tag", f"{app_name}:{tag}", ecr_uri
            ], check=True)
            
            # Push to ECR
            subprocess.run([
                "docker", "push", ecr_uri
            ], check=True)
            
            return [TextContent(
                type="text",
                text=f"✅ Container successfully built and pushed!\n\nImage URI: {ecr_uri}\nRepository: {app_name}\nTag: {tag}\nRegion: {region}"
            )]
            
        except subprocess.CalledProcessError as e:
            return [TextContent(
                type="text", 
                text=f"❌ Error during build/push: {e}\n\nEnsure Docker is running and AWS credentials are configured."
            )]
    
    elif name == "test_container_locally":
        app_path = arguments["app_path"]
        image_name = arguments["image_name"]
        env_vars = arguments.get("env_vars", {})
        port = arguments.get("port", 3000)
        
        # Build environment variables for docker run
        env_args = []
        for key, value in env_vars.items():
            env_args.extend(["-e", f"{key}={value}"])
        
        try:
            # Run container in detached mode
            cmd = [
                "docker", "run", "-d", 
                "-p", f"{port}:{port}",
                "--name", f"test-{image_name.replace(':', '-')}"
            ] + env_args + [image_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()
            
            # Wait a moment for startup
            await asyncio.sleep(3)
            
            # Test health endpoint
            health_result = subprocess.run([
                "curl", "-f", f"http://localhost:{port}/health"
            ], capture_output=True, text=True)
            
            if health_result.returncode == 0:
                status = "✅ Container is healthy and responding"
            else:
                status = "⚠️ Container started but health check failed"
            
            return [TextContent(
                type="text",
                text=f"{status}\n\nContainer ID: {container_id}\nPort: {port}\nTest URL: http://localhost:{port}\n\nTo stop: docker stop {container_id}"
            )]
            
        except subprocess.CalledProcessError as e:
            return [TextContent(
                type="text",
                text=f"❌ Error testing container: {e}\n\nCheck Docker daemon and image availability."
            )]
    
    elif name == "validate_container_security":
        dockerfile_path = arguments["dockerfile_path"]
        
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
            
            issues = []
            recommendations = []
            
            # Security checks
            if "USER root" in content or "USER 0" in content:
                issues.append("❌ Running as root user")
            elif "USER " not in content:
                issues.append("⚠️ No explicit user specified (may run as root)")
            else:
                recommendations.append("✅ Non-root user specified")
            
            if "HEALTHCHECK" not in content:
                issues.append("⚠️ No health check defined")
            else:
                recommendations.append("✅ Health check included")
            
            if "--only=production" in content or "--omit=dev" in content:
                recommendations.append("✅ Production dependencies only")
            else:
                issues.append("⚠️ Consider using production-only dependencies")
            
            if "COPY . ." in content:
                issues.append("⚠️ Copying entire directory (consider .dockerignore)")
            else:
                recommendations.append("✅ Selective file copying")
            
            result = "🔒 Container Security Validation\n\n"
            
            if recommendations:
                result += "Strengths:\n" + "\n".join(recommendations) + "\n\n"
            
            if issues:
                result += "Issues to address:\n" + "\n".join(issues)
            else:
                result += "✅ No security issues found!"
            
            return [TextContent(type="text", text=result)]
            
        except FileNotFoundError:
            return [TextContent(
                type="text",
                text=f"❌ Dockerfile not found at {dockerfile_path}"
            )]
    
    elif name == "deploy_ecs_express_service":
        service_name = arguments["service_name"]
        image_uri = arguments["image_uri"]
        env_vars = arguments.get("environment_vars", {})
        cpu = arguments.get("cpu", "256")
        memory = arguments.get("memory", "512")
        port = arguments.get("port", 3000)
        region = arguments.get("region", "us-west-2")
        
        try:
            # Get AWS account ID
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
                capture_output=True, text=True, check=True
            )
            account_id = result.stdout.strip()
            
            # Validate required IAM roles exist
            execution_role_arn = f"arn:aws:iam::{account_id}:role/ecsTaskExecutionRole"
            task_role_arn = f"arn:aws:iam::{account_id}:role/BlogAppECSTaskRole"
            
            # Check execution role
            try:
                subprocess.run(["aws", "iam", "get-role", "--role-name", "ecsTaskExecutionRole"], 
                             capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError:
                return [TextContent(
                    type="text",
                    text="❌ ecsTaskExecutionRole not found. Please create it first using validate_ecs_prerequisites."
                )]
            
            # Check task role
            try:
                subprocess.run(["aws", "iam", "get-role", "--role-name", "BlogAppECSTaskRole"], 
                             capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError:
                return [TextContent(
                    type="text",
                    text="❌ BlogAppECSTaskRole not found. Please create it first."
                )]
            
            # Create ECS Express Gateway Service
            cmd = [
                "aws", "ecs", "create-express-gateway-service",
                "--service-name", service_name,
                "--task-definition-family", service_name,
                "--desired-count", "1",
                "--region", region,
                "--task-definition", json.dumps({
                    "family": service_name,
                    "cpu": cpu,
                    "memory": memory,
                    "networkMode": "awsvpc",
                    "requiresCompatibilities": ["FARGATE"],
                    "executionRoleArn": execution_role_arn,
                    "taskRoleArn": task_role_arn,
                    "containerDefinitions": [{
                        "name": service_name,
                        "image": image_uri,
                        "portMappings": [{
                            "containerPort": port,
                            "protocol": "tcp"
                        }],
                        "environment": [{"name": k, "value": str(v)} for k, v in env_vars.items()],
                        "healthCheck": {
                            "command": ["CMD-SHELL", f"curl -f http://localhost:{port}/health || exit 1"],
                            "interval": 30,
                            "timeout": 5,
                            "retries": 3,
                            "startPeriod": 60
                        },
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": f"/ecs/{service_name}",
                                "awslogs-region": region,
                                "awslogs-stream-prefix": "ecs"
                            }
                        }
                    }]
                })
            ]
            
            # nosemgrep: dangerous-subprocess-use-audit
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            service_info = json.loads(result.stdout)
            
            return [TextContent(
                type="text",
                text=f"""✅ ECS Express Gateway Service Created Successfully!

🚀 Service Details:
- Service Name: {service_name}
- Service ARN: {service_info.get('serviceArn', 'N/A')}
- Image: {image_uri}
- CPU: {cpu} units
- Memory: {memory} MB
- Port: {port}

🔗 Endpoints:
- Load Balancer URL: {service_info.get('loadBalancerUrl', 'Provisioning...')}

⏳ Status: {service_info.get('status', 'PENDING')}

📝 Next Steps:
1. Wait 2-3 minutes for service to become healthy
2. Use check_ecs_service_status to monitor deployment
3. Test the application endpoint once healthy
"""
            )]
            
        except subprocess.CalledProcessError as e:
            return [TextContent(
                type="text",
                text=f"❌ ECS Express Service deployment failed:\n{e.stderr}"
            )]
    
    elif name == "validate_ecs_prerequisites":
        image_uri = arguments["image_uri"]
        region = arguments.get("region", "us-west-2")
        
        validation_results = []
        
        try:
            # Check if image exists in ECR
            repo_name = image_uri.split('/')[-1].split(':')[0]
            cmd = ["aws", "ecr", "describe-images", "--repository-name", repo_name, "--region", region]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            validation_results.append("✅ Container image exists in ECR")
            
        except subprocess.CalledProcessError:
            validation_results.append("❌ Container image not found in ECR")
        
        try:
            # Check task execution role
            cmd = ["aws", "iam", "get-role", "--role-name", "ecsTaskExecutionRole"]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            validation_results.append("✅ ecsTaskExecutionRole exists")
            
        except subprocess.CalledProcessError:
            try:
                # Create ecsTaskExecutionRole
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                }
                
                # Write trust policy to temp file
                with open("/tmp/task-execution-trust-policy.json", "w") as f:
                    json.dump(trust_policy, f)
                
                # Create role
                cmd = ["aws", "iam", "create-role", 
                       "--role-name", "ecsTaskExecutionRole",
                       "--assume-role-policy-document", "file:///tmp/task-execution-trust-policy.json",
                       "--description", "ECS Task Execution Role for pulling images and writing logs"]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Attach managed policy
                cmd = ["aws", "iam", "attach-role-policy",
                       "--role-name", "ecsTaskExecutionRole", 
                       "--policy-arn", "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                validation_results.append("✅ ecsTaskExecutionRole created")
            except subprocess.CalledProcessError as e:
                validation_results.append(f"❌ Failed to create ecsTaskExecutionRole: {e}")
        
        try:
            # Check infrastructure role
            cmd = ["aws", "iam", "get-role", "--role-name", "ecsInfrastructureRoleForExpressServices"]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            validation_results.append("✅ ecsInfrastructureRoleForExpressServices exists")
            
        except subprocess.CalledProcessError:
            try:
                # Create ecsInfrastructureRoleForExpressServices
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "ecs.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                }
                
                # Write trust policy to temp file
                with open("/tmp/ecs-trust-policy.json", "w") as f:
                    json.dump(trust_policy, f)
                
                # Create role
                cmd = ["aws", "iam", "create-role",
                       "--role-name", "ecsInfrastructureRoleForExpressServices",
                       "--assume-role-policy-document", "file:///tmp/ecs-trust-policy.json",
                       "--description", "ECS Infrastructure Role for Express Gateway Services"]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Attach managed policy
                cmd = ["aws", "iam", "attach-role-policy",
                       "--role-name", "ecsInfrastructureRoleForExpressServices",
                       "--policy-arn", "arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                validation_results.append("✅ ecsInfrastructureRoleForExpressServices created")
            except subprocess.CalledProcessError as e:
                validation_results.append(f"❌ Failed to create ecsInfrastructureRoleForExpressServices: {e}")
        
        # Check BlogAppECSTaskRole
        try:
            cmd = ["aws", "iam", "get-role", "--role-name", "BlogAppECSTaskRole"]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            validation_results.append("✅ BlogAppECSTaskRole exists")
        except subprocess.CalledProcessError:
            validation_results.append("❌ BlogAppECSTaskRole not found - required for task permissions")
        
        all_valid = all("✅" in result for result in validation_results)
        status = "✅ All prerequisites met" if all_valid else "❌ Prerequisites missing"
        
        return [TextContent(
            type="text",
            text=f"""🔍 ECS Express Mode Prerequisites Validation

{status}

📋 Validation Results:
{chr(10).join(validation_results)}

💡 To fix missing prerequisites:
- Create ecsTaskExecutionRole: aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file://trust-policy.json
- Create infrastructure role: aws iam create-role --role-name ecsInfrastructureRoleForExpressServices --assume-role-policy-document file://ecs-trust-policy.json
- Push image to ECR: Use build_and_push_container tool
"""
        )]
    
    elif name == "check_ecs_service_status":
        service_arn = arguments["service_arn"]
        region = arguments.get("region", "us-west-2")
        
        try:
            # Get service status
            cmd = ["aws", "ecs", "describe-express-gateway-service", "--service-arn", service_arn, "--region", region]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            service_info = json.loads(result.stdout)
            
            service = service_info.get('service', {})
            status = service.get('status', 'UNKNOWN')
            running_count = service.get('runningCount', 0)
            desired_count = service.get('desiredCount', 0)
            load_balancer_url = service.get('loadBalancerUrl', 'N/A')
            
            # Determine overall health
            if status == "ACTIVE" and running_count == desired_count:
                health_status = "✅ HEALTHY"
            elif status == "ACTIVE" and running_count < desired_count:
                health_status = "⏳ DEPLOYING"
            else:
                health_status = f"⚠️ {status}"
            
            return [TextContent(
                type="text",
                text=f"""📊 ECS Express Service Status

{health_status}

🔍 Service Details:
- Status: {status}
- Running Tasks: {running_count}/{desired_count}
- Load Balancer URL: {load_balancer_url}

📈 Deployment Progress:
- Service ARN: {service_arn}
- Last Updated: {service.get('updatedAt', 'N/A')}

💡 Next Steps:
{
'🎉 Service is ready! Test your application at the Load Balancer URL.' if health_status == '✅ HEALTHY'
else '⏳ Wait a few more minutes and check status again.' if 'DEPLOYING' in health_status
else '🔧 Check CloudWatch logs for deployment issues.'
}
"""
            )]
            
        except subprocess.CalledProcessError as e:
            return [TextContent(
                type="text",
                text=f"❌ Failed to get service status:\n{e.stderr}"
            )]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="container-migration-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
