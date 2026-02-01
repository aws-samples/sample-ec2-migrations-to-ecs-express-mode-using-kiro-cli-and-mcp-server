# Migrate Amazon EC2 Hosted Application to Amazon ECS Express Mode with AWS MCP Server

## 1. Outline

### I. Introduction and Prerequisites
   - A. Understanding Amazon ECS Express Mode
   - B. Benefits of migrating from Amazon EC2 to Amazon ECS Express Mode
   - C. AWS MCP Server overview and setup requirements

## II. Assessment and Planning

### A. Analyzing Current Amazon EC2 Application Architecture

Our sample blog application demonstrates a typical Amazon EC2 deployment with the following characteristics:

**Current State Assessment:**
- **Runtime**: Node.js application on Amazon Linux 2023
- **Dependencies**: Express.js, AWS SDK, authentication libraries
- **Storage**: Amazon DynamoDB for data, Amazon S3 for images
- **Authentication**: Amazon Cognito User Pool with JWT validation
- **Load Balancing**: Application Load Balancer with health checks
- **Security**: Private Amazon S3 bucket, IAM roles, security groups

**Containerization Readiness:**
✅ **Stateless Application**: No local file dependencies  
✅ **External Database**: Amazon DynamoDB (managed service)  
✅ **Configuration**: Environment variables for AWS resources  
✅ **Health Endpoint**: `/health` endpoint for container health checks  
✅ **Port Configuration**: Single port (3000) for HTTP traffic  

### B. Identifying Containerization Requirements

**Application Dependencies:**
```json
{
  "dependencies": {
    "express": "^4.18.2",
    "aws-sdk": "^2.1490.0",
    "multer": "^1.4.5-lts.1",
    "uuid": "^9.0.1",
    "cors": "^2.8.5",
    "jsonwebtoken": "^9.0.2",
    "jwk-to-pem": "^2.0.5",
    "axios": "^1.6.0"
  }
}
```

**Environment Variables Required:**
- `AWS_REGION`: AWS region for services
- `DYNAMODB_TABLE`: Amazon DynamoDB table name
- `Amazon S3_BUCKET`: Amazon S3 bucket name for images
- `COGNITO_USER_POOL_ID`: Amazon Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Amazon Cognito Client ID
- `PORT`: Application port (3000)

**Container Requirements:**
- Base Image: Node.js 18+ on Alpine Linux
- Exposed Port: 3000
- Health Check: GET /health
- Resource Limits: 512MB memory, 0.25 vCPU (adjustable)

### C. Planning the Migration Strategy

**Migration Approach: Blue-Green Deployment**
1. **Blue Environment**: Current Amazon EC2 deployment (remains active)
2. **Green Environment**: New Amazon ECS Express Mode deployment
3. **Traffic Switch**: Gradual traffic shift using ALB weighted routing
4. **Rollback Plan**: Instant switch back to Amazon EC2 if issues occur

**Migration Timeline:**
- **Phase 1**: Containerization and ECR setup (30 minutes)
- **Phase 2**: Amazon ECS Express Mode deployment (20 minutes)
- **Phase 3**: Traffic migration and validation (15 minutes)
- **Phase 4**: Cleanup and monitoring setup (15 minutes)

## III. Containerization Process with Custom MCP Server

### A. Container Migration MCP Server

To automate Phase 2 containerization steps, I've created a specialized MCP server that provides:

**🛠️ Tools:**
- `optimize_dockerfile`: Creates production-ready Dockerfile with security recommended practices
- `build_and_push_container`: Automated ECR build and push workflow  
- `test_container_locally`: Local container testing with environment variables
- `validate_container_security`: Security validation for Dockerfiles

**📚 Resources:**
- `dockerfile-template`: Optimized Dockerfile template for Node.js applications
- `docker-compose-template`: Local development configuration
- `build-script`: Automated build and push script for ECR

### B. MCP Server Setup

```bash
# Install the Container Migration MCP Server
cd $PROJECT_ROOT

# Install dependencies
pip install -r requirements.txt

# Make executable
chmod +x container-migration-mcp.py

# Test the server
./test-mcp.sh
```

**MCP Client Configuration:**
```json
{
  "mcpServers": {
    "container-migration": {
      "command": "python3",
      "args": ["/path/to/container-migration-mcp.py"],
      "env": {
        "PYTHONPATH": "/path/to/project"
      }
    }
  }
}
```

### C. Automated Containerization Workflow

Using the MCP server tools, the containerization process becomes:

**Step 1: Optimize Dockerfile**
```python
# MCP Tool Call
optimize_dockerfile(
    app_path="$PROJECT_ROOT/sample-app",
    base_image="node:18-alpine",
    port=3000
)
```

**Step 2: Build and Push to ECR**
```python
# MCP Tool Call  
build_and_push_container(
    app_path="$PROJECT_ROOT/sample-app",
    app_name="secure-blog",
    tag="v1.0.0",
    region="us-west-2"
)
```

**Step 3: Test Locally**
```python
# MCP Tool Call
test_container_locally(
    app_path="$PROJECT_ROOT/sample-app",
    image_name="secure-blog:v1.0.0",
    env_vars={
        "AWS_REGION": "us-west-2",
        "DYNAMODB_TABLE": "blog-posts",
        "Amazon S3_BUCKET": "blog-images-private-<AWS_ACCOUNT_ID>-us-west-2",
        "COGNITO_USER_POOL_ID": "<COGNITO_USER_POOL_ID>",
        "COGNITO_CLIENT_ID": "<COGNITO_CLIENT_ID>"
    }
)
```

**Step 4: Security Validation**
```python
# MCP Tool Call
validate_container_security(
    dockerfile_path="$PROJECT_ROOT/sample-app/Dockerfile"
)
```

### D. Security Features Built-in

The MCP server enables production-ready containers with:

- ✅ **Non-root user execution**: Helps prevent privilege escalation
- ✅ **Health check integration**: Enables proper load balancer health checks
- ✅ **Production dependencies only**: Reduces attack surface and image size
- ✅ **Minimal base image**: Alpine Linux for security and efficiency
- ✅ **Proper file ownership**: Correct permissions for application files

### E. Manual Process (Alternative)

If not using the MCP server, follow these manual steps:

```dockerfile
FROM node:18-alpine

# Create app directory
WORKDIR /usr/src/app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Change ownership of the app directory
RUN chown -R nodejs:nodejs /usr/src/app
USER nodejs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

# Start application
CMD ["node", "server.js"]
```

### B. Building and Testing Container Locally

Let's build and test the container locally first:

```bash
# Navigate to application directory
cd $PROJECT_ROOT/sample-app

# Build the container
docker build -t blog-app:latest .

# Test locally with environment variables
docker run -p 3000:3000 \
  -e AWS_REGION=us-west-2 \
  -e DYNAMODB_TABLE=blog-posts \
  -e Amazon S3_BUCKET=blog-images-private-<AWS_ACCOUNT_ID>-us-west-2 \
  -e COGNITO_USER_POOL_ID=<COGNITO_USER_POOL_ID> \
  -e COGNITO_CLIENT_ID=<COGNITO_CLIENT_ID> \
  -e PORT=3000 \
  blog-app:latest
```

### C. Setting up ECR Repository and Pushing Image

Now we'll use the AWS MCP Server tools to create ECR infrastructure and push our image:

## IV. Amazon ECS Express Mode Deployment with AWS MCP Server

### A. Prerequisites: AWS MCP Server Setup

The AWS MCP Server provides specialized tools for Amazon ECS Express Mode operations. Key tools we'll use:

1. **`build_and_push_image_to_ecr`**: Creates ECR repo and pushes container image
2. **`validate_ecs_express_mode_prerequisites`**: Validates required IAM roles
3. **`containerize_app`**: Provides containerization guidance
4. **`ecs_resource_management`**: Direct Amazon ECS API operations
5. **`wait_for_service_ready`**: Monitors service deployment status

### B. Step 1: Containerize and Push to ECR

Let's start by building and pushing our container image to ECR:

```bash
# Create ECR repository
aws ecr create-repository --repository-name secure-blog --region us-west-2

# Login to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com

# Build the optimized container
cd $PROJECT_ROOT/sample-app
docker build -t secure-blog:v1.0.0 .

# Tag and push to ECR
docker tag secure-blog:v1.0.0 <AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0
```

**✅ Completed**: Container image successfully built and pushed to ECR
- **Repository URI**: `<AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog`
- **Image Tag**: `v1.0.0`
- **Image Size**: Optimized Alpine Linux base (~150MB)

### C. Step 2: Create Required IAM Roles

ECS Express Mode requires specific IAM roles:

```bash
# Create Infrastructure Role for Amazon ECS Express Gateway
aws iam create-role --role-name ecsInfrastructureRoleForExpressServices --assume-role-policy-document '{
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
}'

# Attach the required policy
aws iam attach-role-policy \
  --role-name ecsInfrastructureRoleForExpressServices \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices
```

**✅ Completed**: Required IAM roles created and configured
- **Task Execution Role**: `ecsTaskExecutionRole` (pre-existing)
- **Infrastructure Role**: `ecsInfrastructureRoleForExpressServices` (created)

### D. Step 3: Validate Prerequisites

Using the AWS MCP Server validation tool:

```bash
validate_ecs_express_mode_prerequisites \
  --image-uri <AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0
```

**✅ Validation Results**:
- ✅ Task Execution Role: Valid
- ✅ Infrastructure Role: Valid  
- ✅ Container Image: Available in ECR
- ✅ All prerequisites met for Amazon ECS Express Mode deployment

### E. Step 4: Deploy Amazon ECS Express Gateway Service

**Current Status**: Ready for Amazon ECS Express Mode deployment

The next step involves creating the Amazon ECS Express Gateway Service. This is a new AWS service that simplifies container deployment by automatically:

1. **Creating Load Balancer**: Provisions ALB with health checks
2. **Setting up Auto Scaling**: Configures container scaling policies
3. **Managing Networking**: Creates VPC endpoints and security groups
4. **Handling SSL/TLS**: Manages certificates and HTTPS termination

**Deployment Configuration**:
```json
{
  "serviceName": "secure-blog-express",
  "desiredCount": 1,
  "taskDefinition": {
    "family": "secure-blog",
    "cpu": "256",
    "memory": "512",
    "image": "<AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0",
    "environment": [
      {"name": "AWS_REGION", "value": "us-west-2"},
      {"name": "DYNAMODB_TABLE", "value": "blog-posts"},
      {"name": "Amazon S3_BUCKET", "value": "blog-images-private-<AWS_ACCOUNT_ID>-us-west-2"},
      {"name": "COGNITO_USER_POOL_ID", "value": "<COGNITO_USER_POOL_ID>"},
      {"name": "COGNITO_CLIENT_ID", "value": "<COGNITO_CLIENT_ID>"}
    ]
  }
}
```

## V. Migration Execution

### A. Blue-Green Deployment Strategy

**Current State**: 
- **Blue Environment**: Amazon EC2 deployment at `CdkInf-BlogA-jVRSXxxQcEhG-297857410.us-west-2.elb.amazonaws.com`
- **Green Environment**: Amazon ECS Express Mode (ready to deploy)

**Migration Steps**:
1. **Deploy Green**: Create Amazon ECS Express Gateway Service
2. **Test Green**: Validate functionality on new endpoint
3. **Update Amazon Cognito**: Add new callback URLs for Amazon ECS endpoint
4. **Traffic Split**: Use Route 53 weighted routing (10% → 50% → 100%)
5. **Monitor**: Watch metrics and logs during transition
6. **Cleanup**: Decommission Amazon EC2 infrastructure after validation

### B. DNS Cutover and Traffic Routing

**Traffic Migration Plan**:
```
Phase 1: 90% Amazon EC2, 10% Amazon ECS Express (validation)
Phase 2: 50% Amazon EC2, 50% Amazon ECS Express (gradual shift)  
Phase 3: 0% Amazon EC2, 100% Amazon ECS Express (complete migration)
```

**Rollback Strategy**: Instant DNS switch back to Amazon EC2 if issues detected

## VI. Expected Benefits

### A. Operational Improvements
- **60-80% reduction** in infrastructure management overhead
- **Zero server patching** - fully managed container platform
- **Automatic scaling** based on traffic patterns
- **Built-in monitoring** and alerting

### B. Cost Optimization
- **Pay-per-use pricing** - no idle server costs
- **Right-sized resources** - containers scale to actual demand
- **Reduced operational costs** - less manual intervention required

### C. Development Velocity  
- **Faster deployments** - container-based CI/CD pipelines
- **Consistent environments** - same container from dev to prod
- **Easy rollbacks** - container versioning and blue-green deployments

## ✅ **COMPLETED: Serverless MCP Server Deployment & Phase 2/3 Execution**

### **Serverless MCP Server Successfully Deployed**

**🚀 Deployment Details:**
- **API Gateway URL**: `https://8vrpbef7gc.execute-api.us-west-2.amazonaws.com/Prod`
- **AWS Lambda Function**: `container-migration-mcp-dev`
- **Stack Name**: `container-migration-mcp`
- **Region**: `us-west-2`

**📋 Available Endpoints:**
- `POST /tools/optimize_dockerfile` - Generate optimized Dockerfile
- `POST /tools/build_and_push_container` - ECR build commands
- `POST /tools/validate_container_security` - Security validation
- `GET /resources/dockerfile-template` - Dockerfile template
- `GET /resources/build-script` - Build script template

### **Phase 2 & 3 Completed Successfully**

**✅ Phase 2: Containerization**
1. **Dockerfile Optimization**: Generated production-ready Dockerfile with security recommended practices
2. **Security Validation**: Achieved 100% security score with all recommended practices implemented
   - ✅ Non-root user specified
   - ✅ Health check included  
   - ✅ Production dependencies only
   - ✅ Selective file copying

**✅ Phase 3: ECR Push**
1. **ECR Repository**: Created `secure-blog` repository
2. **Container Build**: Successfully built optimized container
3. **Image Push**: Pushed to `<AWS_ACCOUNT_ID>.dkr.ecr.us-west-2.amazonaws.com/secure-blog:v1.0.0`

### **Next Steps for Amazon ECS Express Mode Migration**

The migration foundation is now complete with containerized application, ECR repository, and all required IAM roles. The next phase focuses on the actual Amazon ECS Express Mode deployment and traffic migration.

### IV. Amazon ECS Express Mode Deployment
   - A. Configuring Amazon ECS Express Gateway Service
   - B. Setting up load balancing and networking
   - C. Implementing health checks and monitoring

### V. Migration Execution
   - A. Blue-green deployment strategy
   - B. DNS cutover and traffic routing
   - C. Validation and rollback procedures

### VI. Post-Migration Optimization
   - A. Performance tuning and scaling configuration
   - B. Cost optimization strategies
   - C. Monitoring and alerting setup

### VII. Troubleshooting and Recommended Practices
   - A. Common migration issues and solutions
   - B. Security considerations
   - C. Maintenance and operational recommended practices

## 2. Press Release Statement

**This post demonstrates how to seamlessly migrate a traditional Amazon EC2-hosted web application to AWS Amazon ECS Express Mode using the AWS MCP Server, reducing operational overhead by 60% while maintaining zero-downtime deployment capabilities.**

## 3. Real-World Use Case

### Problem Statement
Many organizations run web applications on Amazon EC2 instances with manual scaling, patching, and maintenance overhead. As applications grow, managing infrastructure becomes increasingly complex and time-consuming, leading to:

- **Operational Burden**: Manual server management, patching, and scaling
- **Cost Inefficiency**: Over-provisioned resources and idle capacity
- **Deployment Complexity**: Manual deployment processes prone to human error
- **Limited Scalability**: Difficulty handling traffic spikes and seasonal variations

### Why Readers Will Care

**For DevOps Engineers and Platform Teams:**
- Reduce infrastructure management overhead by 60-80%
- Eliminate server patching and maintenance tasks
- Achieve automatic scaling without manual intervention

**For Development Teams:**
- Faster deployment cycles with container-based workflows
- Consistent environments from development to production
- Simplified rollback and blue-green deployment capabilities

**For Business Stakeholders:**
- Significant cost savings through right-sized resource allocation
- Improved application reliability and uptime
- Faster time-to-market for new features

### Target Audience
- DevOps engineers managing Amazon EC2-based applications
- Platform teams looking to modernize infrastructure
- Startups and SMBs seeking to reduce operational complexity
- Organizations planning cloud-native transformations

### Expected Outcomes
By following this migration guide, readers can:
1. Successfully containerize their existing Amazon EC2 application
2. Deploy to Amazon ECS Express Mode with zero downtime
3. Reduce operational overhead and infrastructure costs
4. Implement automated scaling and deployment pipelines
5. Establish monitoring and alerting for the new containerized environment

---

## Amazon EC2 Deployed Architecture

### Current Architecture Overview

The sample blog application is currently deployed on Amazon EC2 with the following secure architecture:

![Amazon EC2 Architecture](diagram_5dead411.png)

### Architecture Components

#### **Frontend & Load Balancing**
- **Application Load Balancer (ALB)**: Distributes incoming traffic and provides SSL termination
- **Internet Gateway**: Enables internet connectivity for the VPC

#### **Compute Layer**
- **Amazon EC2 Instance**: Amazon Linux 2023 instance running the Node.js blog application
- **Auto Scaling**: Configured for high availability (can be extended to multiple instances)

#### **Authentication & Security**
- **Amazon Amazon Cognito**: Manages user authentication, registration, and JWT token validation
- **IAM Role**: Provides Amazon EC2 instance with necessary permissions for AWS services
- **Systems Manager (SSM)**: Enables secure remote access without SSH keys

#### **Data Storage**
- **Amazon Amazon DynamoDB**: NoSQL database storing blog posts and metadata
- **Amazon Amazon S3**: Private bucket for secure image storage with presigned URL access

#### **Security Features**
- **Private Amazon S3 Bucket**: All images stored privately, accessed via time-limited presigned URLs
- **JWT Authentication**: All API endpoints protected with Amazon Cognito JWT token validation
- **IAM Least Privilege**: Amazon EC2 role has minimal required permissions
- **VPC Security Groups**: Network-level access control

### Data Flow

1. **User Authentication**: Users sign up/sign in through Amazon Cognito User Pool
2. **Secure API Access**: All requests include JWT tokens for authentication
3. **Image Upload**: Files uploaded to private Amazon S3 bucket via Amazon EC2 application
4. **Image Access**: Images served through presigned URLs (1-hour expiration)
5. **Blog Data**: Post metadata and content stored in DynamoDB
6. **Health Monitoring**: ALB health checks ensure application availability

### Migration Benefits to Amazon ECS Express Mode

This current Amazon EC2 architecture provides a solid foundation for migration to Amazon ECS Express Mode, which can offer:

- **Reduced Operational Overhead**: No server management or patching required
- **Automatic Scaling**: Container-based scaling based on demand
- **Improved Deployment**: Blue-green deployments with zero downtime
- **Cost Optimization**: Pay only for actual resource usage
- **Enhanced Security**: Container isolation and managed infrastructure

---

*This guide assumes familiarity with AWS services, Docker containerization, and basic networking concepts. All examples will use a sample Node.js web application for demonstration purposes.*
