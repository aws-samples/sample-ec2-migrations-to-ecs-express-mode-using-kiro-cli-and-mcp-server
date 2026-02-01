# Chat Interface Guide - AgentCore Dashboard

## Overview

The dashboard now includes **conversational chat interfaces** for both Amazon ECS and EKS agents. Instead of clicking buttons, you can have natural conversations with the agents to deploy, manage, and troubleshoot your applications.

## How to Use

### Amazon ECS Chat Examples

**Deploy a new application:**
```
Deploy blog-app to eu-north-1 with 512 CPU and 1024 memory
```

**Create ECR repository:**
```
Create an ECR repository named blog-app in eu-north-1
```

**Check service status:**
```
What's the status of blog-app-1768518733 in eu-north-1?
```

**Delete a service:**
```
Delete the Amazon ECS service blog-app-1768518733 in eu-north-1
```

**Full deployment workflow:**
```
I want to deploy blog-app to eu-north-1. First create the ECR repository, 
then I'll build and push the image, then deploy it with 512 CPU and 1024 memory.
```

### EKS Chat Examples

**Deploy a new application:**
```
Deploy blog-app-eks-v4 to ec2-eks-migration cluster in eu-north-1 with 2 replicas
```

**Setup OIDC:**
```
Setup OIDC provider for ec2-eks-migration cluster in eu-north-1
```

**Create IRSA role:**
```
Create an IRSA role for blog-app-eks-v4 in ec2-eks-migration cluster with access to 
S3 bucket blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1 and Amazon DynamoDB table blog-posts
```

**Check deployment status:**
```
What's the status of blog-app-eks-v3 in ec2-eks-migration cluster?
```

**Delete deployment:**
```
Delete blog-app-eks-v3 deployment from ec2-eks-migration cluster in eu-north-1
```

**Full deployment workflow:**
```
I want to deploy blog-app-eks-v4 to ec2-eks-migration in eu-north-1. 
Guide me through the complete process step by step.
```

## Conversational Deployment Workflow

### Amazon ECS Deployment (Step-by-Step)

**Step 1: Create ECR Repository**
```
You: Create ECR repository named blog-app in eu-north-1

Agent: ✅ Created ECR repository: blog-app
        Repository URI: <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app
```

**Step 2: Build and Push Image (You do this locally)**
```bash
cd /path/to/sample-application
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com
docker buildx build --platform linux/amd64,linux/arm64 -t <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app:latest --push .
```

**Step 3: Deploy to Amazon ECS**
```
You: Deploy the image <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app:latest 
     to Amazon ECS Express Mode in eu-north-1 with service name blog-app-prod, 
     512 CPU, 1024 memory, port 3000, and these environment variables:
     {"AWS_REGION": "eu-north-1", "DYNAMODB_TABLE": "blog-posts", 
      "Amazon S3_BUCKET": "blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1", 
      "COGNITO_USER_POOL_ID": "<COGNITO_USER_POOL_ID>", 
      "COGNITO_CLIENT_ID": "<COGNITO_CLIENT_ID>", "PORT": "3000"}

Agent: ✅ Deploying to Amazon ECS Express Mode...
       Service: blog-app-prod
       AWS CloudFormation stack: ecs-express-blog-app-prod-1768520000
       Status: CREATE_IN_PROGRESS
```

**Step 4: Check Status**
```
You: What's the status of blog-app-prod?

Agent: Service: blog-app-prod
       Status: ACTIVE
       Running tasks: 1
       Endpoint: http://ecs-express-blog-app-prod-alb-123456789.eu-north-1.elb.amazonaws.com
```

### EKS Deployment (Step-by-Step)

**Step 1: Setup OIDC**
```
You: Setup OIDC provider for ec2-eks-migration cluster in eu-north-1

Agent: ✅ OIDC provider already exists
       Provider ARN: arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/oidc.eks.eu-north-1.amazonaws.com/id/ABC123
```

**Step 2: Create IRSA Role**
```
You: Create IRSA role for blog-app-eks-v4 in ec2-eks-migration cluster with access to 
     Amazon S3 bucket blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1 and Amazon DynamoDB table blog-posts

Agent: ✅ Created IRSA role
       Role ARN: arn:aws:iam::<AWS_ACCOUNT_ID>:role/blog-app-eks-v4-irsa-role
       Service Account: blog-app-eks-v4-sa
```

**Step 3: Build and Push Image (You do this locally)**
```bash
cd /path/to/sample-application
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com
docker buildx build --platform linux/amd64,linux/arm64 -t <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app-eks-v4:latest --push .
```

**Step 4: Deploy to EKS**
```
You: Deploy <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app-eks-v4:latest 
     to ec2-eks-migration cluster with app name blog-app-eks-v4, 2 replicas, 
     port 3000, role arn:aws:iam::<AWS_ACCOUNT_ID>:role/blog-app-eks-v4-irsa-role, 
     and environment variables:
     {"DYNAMODB_TABLE": "blog-posts", 
      "Amazon S3_BUCKET": "blog-images-private-<AWS_ACCOUNT_ID>-eu-north-1", 
      "COGNITO_USER_POOL_ID": "<COGNITO_USER_POOL_ID>", 
      "COGNITO_CLIENT_ID": "<COGNITO_CLIENT_ID>", 
      "PORT": "3000", "NODE_ENV": "production"}

Agent: ✅ Deployment successful!
       App: blog-app-eks-v4
       Replicas: 2/2 ready
       Endpoint: http://a1234567890abcdef.eu-north-1.elb.amazonaws.com
```

## Tips for Better Conversations

### Be Specific
✅ Good: "Deploy blog-app to eu-north-1 with 512 CPU and 1024 memory"
❌ Bad: "Deploy something"

### Include Region
✅ Good: "Create ECR repository in eu-north-1"
❌ Bad: "Create ECR repository" (will use default region)

### Use Full Names
✅ Good: "Delete blog-app-1768518733 in eu-north-1"
❌ Bad: "Delete that service"

### Ask for Guidance
✅ Good: "Guide me through deploying blog-app to EKS step by step"
✅ Good: "What do I need to do next?"
✅ Good: "Show me the Docker commands to build and push the image"

### Multi-Step Requests
You can ask the agent to guide you through complex workflows:
```
I want to deploy a new version of blog-app to both Amazon ECS and EKS in eu-north-1. 
Walk me through the process step by step, starting with creating the ECR repository.
```

## Keyboard Shortcuts

- **Enter**: Send message
- **Shift + Enter**: New line in message

## Context Awareness

The agents are aware of:
- Your account ID: <AWS_ACCOUNT_ID>
- Your app path: /path/to/sample-application
- Default regions: us-west-2, eu-north-1
- Default cluster: ec2-eks-migration
- Environment variables needed for the blog app
- Default resource configurations (CPU, memory, replicas)

So you don't need to specify everything every time!

## Example Conversations

### Quick Deploy
```
You: Deploy blog-app to eu-north-1
Agent: I'll help you deploy. First, let me create the ECR repository...
       ✅ Repository created: <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app
       
       Next steps:
       1. Build and push your image:
          cd /path/to/sample-application
          aws ecr get-login-password --region eu-north-1 | docker login ...
          docker buildx build --platform linux/amd64,linux/arm64 -t ... --push .
       
       2. Once pushed, tell me "continue deployment" and I'll deploy to Amazon ECS.
```

### Troubleshooting
```
You: My service blog-app-prod is not working
Agent: Let me check the status...
       Service: blog-app-prod
       Status: ACTIVE
       Running tasks: 0/1
       
       Issue: Tasks are failing to start. Checking recent events...
       Error: CannotPullContainerError - Image not found
       
       Solution: The Docker image hasn't been pushed to ECR yet. 
       Please build and push the image first.
```

### Cleanup
```
You: Delete everything related to blog-app in eu-north-1
Agent: I found these resources:
       - Amazon ECS service: blog-app-1768518733
       - AWS CloudFormation stack: ecs-express-blog-app-1768518733
       - ECR repository: blog-app
       
       Shall I delete all of them? (yes/no)
```

## Benefits of Chat Interface

1. **Natural Language**: No need to remember button names or form fields
2. **Guided Workflows**: Agent can walk you through complex processes
3. **Context Retention**: Agent remembers what you're working on
4. **Flexible**: Ask questions, get status, troubleshoot - all in one place
5. **Clear Instructions**: Agent provides exact commands to run locally
6. **Error Handling**: Agent can diagnose issues and suggest fixes

## When to Use Buttons vs Chat

**Use Buttons for:**
- Quick actions (list services, check stacks)
- When you know exactly what you want
- Repetitive tasks

**Use Chat for:**
- Complex deployments
- Step-by-step guidance
- Troubleshooting
- Learning the process
- When you're not sure what to do next

---

**Pro Tip**: Start with chat to learn the workflow, then use buttons for quick actions once you're familiar!
