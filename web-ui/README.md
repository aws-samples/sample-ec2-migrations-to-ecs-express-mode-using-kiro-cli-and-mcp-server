# AgentCore Deployment Dashboard

A conversational web-based UI for managing Amazon ECS and EKS deployments using AWS Bedrock AgentCore agents with **fully automated Docker build and deployment**.

## Features

### 💬 Conversational AI Interface
- **Natural language chat** with Amazon ECS and EKS agents
- **Fully automated deployments** - no manual Docker commands needed
- **Flexible parsing** - understands various message formats:
  - "Deploy blog-app to eu-north-1"
  - "Deploy the blog-v3-through-ui in ec2-eks-migration with 10 replicas"
  - "Deploy my-app to us-west-2 with 1024 CPU and 2048 memory"
- **Step-by-step guidance** through complex workflows
- **Context-aware** agents that handle all the details
- Press **Enter** to send messages, **Shift+Enter** for new lines

### 🚀 Automated Deployment Workflow

#### Amazon ECS Deployment (Fully Automated)
When you say: `"Deploy blog-app to eu-north-1"`

The system automatically:
1. ✅ Creates ECR repository
2. ✅ Builds Docker image (multi-platform: linux/amd64, linux/arm64)
3. ✅ Pushes image to ECR
4. ✅ Deploys to Amazon ECS Express Mode with all environment variables
5. ✅ Returns the service endpoint

#### EKS Deployment (Fully Automated)
When you say: `"Deploy blog-app-v5 to ec2-eks-migration"`

The system automatically:
1. ✅ Sets up OIDC provider (one-time per cluster)
2. ✅ Creates IRSA role with Amazon S3/Amazon DynamoDB permissions
3. ✅ Builds Docker image (multi-platform)
4. ✅ Pushes image to ECR
5. ✅ Deploys to EKS with Kubernetes manifests
6. ✅ Returns the LoadBalancer endpoint

### 🎯 Simple Operations
- **Deploy**: 
  - "Deploy blog-app to eu-north-1"
  - "Deploy blog-v3-through-ui in ec2-eks-migration with 10 replicas"
  - "Deploy my-app to us-west-2 with 1024 CPU and 2048 memory"
- **Check Status**: "What's the status of blog-app-v5?"
- **Delete**: "Delete blog-app-v4"
- **List**: "List all services in eu-north-1"

## Quick Start

### 1. Install Dependencies

```bash
cd web-ui
pip3 install -r requirements.txt
```

## Configuration

The `app.py` is pre-configured with your deployment settings. All values are centralized in the CONFIG dictionary for easy customization:

```python
CONFIG = {
    # Agent Configuration
    'ecs_agent_arn': 'arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/ecs_deployment_agent-Kq38Lc3cm5',
    'eks_agent_arn': 'arn:aws:bedrock-agentcore:us-west-2:<AWS_ACCOUNT_ID>:runtime/eks_deployment_agent-bJq2whDHLA',
    'agent_region': 'us-west-2',
    'account_id': '<AWS_ACCOUNT_ID>',
    'app_path': '$PROJECT_ROOT/sample-application',
    
    # Application Environment Variables
    'dynamodb_table': 'blog-posts',
    's3_bucket_prefix': 'blog-images-private',
    'cognito_user_pool_id': '<COGNITO_USER_POOL_ID>',
    'cognito_client_id': '<COGNITO_CLIENT_ID>',
    'app_port': '3000',
    
    # Default Resource Settings
    'default_cpu': '512',
    'default_memory': '1024',
    'default_replicas': 2
}
```

**To customize for your environment:**
1. Update agent ARNs if you have different agents
2. Change `account_id` to your AWS account
3. Update `app_path` to your application directory
4. Modify environment variables (Amazon DynamoDB table, Amazon S3 bucket, Amazon Cognito IDs)
5. Adjust default resource settings (CPU, memory, replicas)

### Environment Variables (Auto-Configured from CONFIG)

The agents automatically use these environment variables for deployments. All values come from the CONFIG dictionary and can be customized there:

**Amazon ECS Environment Variables:**
```json
{
  "AWS_REGION": "<deployment-region>",
  "DYNAMODB_TABLE": "blog-posts",  // from CONFIG['dynamodb_table']
  "Amazon S3_BUCKET": "blog-images-private-<AWS_ACCOUNT_ID>-<region>",  // from CONFIG['s3_bucket_prefix'] + account_id + region
  "COGNITO_USER_POOL_ID": "<COGNITO_USER_POOL_ID>",  // from CONFIG['cognito_user_pool_id']
  "COGNITO_CLIENT_ID": "<COGNITO_CLIENT_ID>",  // from CONFIG['cognito_client_id']
  "PORT": "3000"  // from CONFIG['app_port']
}
```

**EKS Environment Variables:**
```json
{
  "DYNAMODB_TABLE": "blog-posts",  // from CONFIG['dynamodb_table']
  "Amazon S3_BUCKET": "blog-images-private-<AWS_ACCOUNT_ID>-<region>",  // from CONFIG['s3_bucket_prefix'] + account_id + region
  "COGNITO_USER_POOL_ID": "<COGNITO_USER_POOL_ID>",  // from CONFIG['cognito_user_pool_id']
  "COGNITO_CLIENT_ID": "<COGNITO_CLIENT_ID>",  // from CONFIG['cognito_client_id']
  "PORT": "3000",  // from CONFIG['app_port']
  "NODE_ENV": "production"
}
```

**Default Resource Settings (from CONFIG):**
- **Amazon ECS**: CPU: 512, Memory: 1024 MB, Port: 3000
- **EKS**: Replicas: 2, Port: 3000
- **Docker**: Multi-platform builds (linux/amd64, linux/arm64)

**Note:** You can override these defaults in your chat messages:
- "Deploy my-app with 1024 CPU and 2048 memory" (Amazon ECS)
- "Deploy my-app with 10 replicas" (EKS)

### 3. Run the Server

```bash
python3 app.py
```

The dashboard will be available at: **http://localhost:5001**

## Usage Examples

### 💬 Amazon ECS Deployments

**Deploy a new application:**
```
You: Deploy blog-app to eu-north-1

Agent: 🚀 Amazon ECS Deployment Workflow for blog-app
       CPU: 512, Memory: 1024 MB
       
       Step 1: Create ECR Repository
       ✅ Created ECR repository: blog-app
       
       Step 2: Build and Push Docker Image
       🔨 Building Docker image from /path/to/sample-application...
       ✅ Image built and pushed: <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app:latest
       
       Step 3: Deploy to Amazon ECS Express Mode
       🚀 Deploying service blog-app-1768525000...
       
       ✅ Deployment Complete!
       Service: blog-app-1768525000
       Region: eu-north-1
       CPU: 512, Memory: 1024 MB
       Image: <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app:latest
```

**Deploy with custom resources:**
```
You: Deploy my-app to us-west-2 with 1024 CPU and 2048 memory

Agent: 🚀 Amazon ECS Deployment Workflow for my-app
       CPU: 1024, Memory: 2048 MB
       ...
```

**Other Amazon ECS commands:**
- "List all services in eu-north-1"
- "What's the status of blog-app-1768525000?"
- "Delete blog-app-1768525000"
- "Show me AWS CloudFormation stacks in eu-north-1"

### 💬 EKS Deployments

**Deploy a new application:**
```
You: Deploy blog-app-v5 to ec2-eks-migration

Agent: 🚀 EKS Deployment Workflow for blog-app-v5
       
       Starting automated deployment to ec2-eks-migration in eu-north-1...
       Replicas: 2
       
       Step 1: Setup OIDC Provider
       ✅ OIDC Provider: exists
       
       Step 2: Create IRSA Role
       ✅ IRSA Role: arn:aws:iam::<AWS_ACCOUNT_ID>:role/blog-app-v5-irsa-role
       
       Step 3: Build and Push Docker Image
       🔨 Building Docker image from /path/to/sample-application...
       ✅ Image built and pushed: <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/blog-app-v5:latest
       
       Step 4: Deploy to EKS
       🚀 Deploying to Kubernetes...
       
       ✅ Deployment Complete!
       🌐 Endpoint: http://a1234567890.eu-north-1.elb.amazonaws.com
       � Appl: blog-app-v5
       🔢 Replicas: 2
       
       💡 Access your app at the endpoint above (may take 2-3 minutes for LoadBalancer to be ready)
```

**Deploy with custom replicas:**
```
You: Deploy blog-v3-through-ui in ec2-eks-migration with 10 replicas

Agent: 🚀 EKS Deployment Workflow for blog-v3-through-ui
       
       Starting automated deployment to ec2-eks-migration in eu-north-1...
       Replicas: 10
       ...
       
       ✅ Deployment Complete!
       📦 App: blog-v3-through-ui
       🔢 Replicas: 10
```

**Other EKS commands:**
- "Check status of blog-app-v5"
- "What's the status of blog-app-v4 in ec2-eks-migration?"
- "Delete blog-app-v4"
- "Setup OIDC for ec2-eks-migration"
- "Create IRSA role for blog-app-v6"

## How It Works

### Automated Docker Build & Push

The dashboard includes a `build_and_push_docker_image()` function that:
1. Creates ECR repository if it doesn't exist
2. Authenticates with ECR using AWS credentials
3. Builds multi-platform Docker image (linux/amd64, linux/arm64)
4. Falls back to single platform if buildx is not available
5. Pushes image to ECR
6. Returns the image URI for deployment

### Amazon ECS Deployment Flow

```
User: "Deploy blog-app to eu-north-1"
  ↓
1. Create ECR repository
  ↓
2. Build & push Docker image (automated)
  ↓
3. Deploy to Amazon ECS Express Mode via agent
  ↓
4. Return service endpoint
```

### EKS Deployment Flow

```
User: "Deploy blog-app-v5 to ec2-eks-migration"
  ↓
1. Setup OIDC provider (one-time)
  ↓
2. Create IRSA role with Amazon S3/Amazon DynamoDB permissions
  ↓
3. Build & push Docker image (automated)
  ↓
4. Deploy to EKS via agent (Deployment, Service, ServiceAccount)
  ↓
5. Return LoadBalancer endpoint
```

## Architecture

```
┌─────────────────────────────────┐
│   Web Browser (Dashboard UI)   │
│  • Chat Interface               │
│  • Button Operations            │
│  • Real-time Logs               │
└────────┬────────────────────────┘
         │ HTTP / WebSocket
         ▼
┌─────────────────────────────────┐
│  Flask Server (app.py)          │
│  • Chat endpoints               │
│  • Button endpoints             │
│  • AWS SigV4 signing            │
└────────┬────────────────────────┘
         │ AWS SigV4 Signed Requests
         ▼
┌─────────────────────────────────┐
│  AWS Bedrock AgentCore          │
│  ┌─────────────┐ ┌────────────┐ │
│  │ Amazon ECS Agent   │ │ EKS Agent  │ │
│  │  (Strands)  │ │   (MCP)    │ │
│  │  6 tools    │ │  6 tools   │ │
│  └─────────────┘ └────────────┘ │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  AWS Services                   │
│  • Amazon ECS Express Mode             │
│  • EKS Kubernetes               │
│  • AWS CloudFormation               │
│  • ECR                          │
│  • IAM (IRSA)                   │
└─────────────────────────────────┘
```

## API Endpoints

### Chat Endpoints (New!)

- `POST /api/ecs/chat` - Chat with Amazon ECS agent
  ```json
  {
    "message": "Deploy blog-app to eu-north-1 with 512 CPU",
    "region": "eu-north-1"
  }
  ```

- `POST /api/eks/chat` - Chat with EKS agent
  ```json
  {
    "message": "Deploy blog-app-eks-v4 to ec2-eks-migration",
    "cluster": "ec2-eks-migration",
    "region": "eu-north-1"
  }
  ```

### Amazon ECS Endpoints

- `POST /api/ecs/list` - List Amazon ECS services
- `POST /api/ecs/deploy` - Start deployment workflow (creates ECR)
- `POST /api/ecs/continue-deploy` - Continue deployment after image push
- `POST /api/ecs/delete` - Delete Amazon ECS service

### EKS Endpoints

- `POST /api/eks/status` - Check deployment status
- `POST /api/eks/deploy` - Start deployment workflow (OIDC + IRSA)
- `POST /api/eks/continue-deploy` - Continue deployment after image push
- `POST /api/eks/setup-oidc` - Setup OIDC provider
- `POST /api/eks/create-irsa` - Create IRSA role
- `POST /api/eks/delete` - Delete deployment

### Utility Endpoints

- `POST /api/cloudformation/stacks` - List AWS CloudFormation stacks

## Security

- Uses AWS SigV4 authentication for all AgentCore requests
- Requires valid AWS credentials in your environment
- No credentials stored in the application

## Troubleshooting

### Connection Errors

If you see connection errors:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify agent ARNs are correct
3. Ensure agents are deployed and ready

### Agent Not Found

If agent is not found:
1. Run `agentcore status` in the agent directory
2. Verify the agent ARN in CONFIG
3. Check the agent region matches

### Permission Errors

If you see permission errors:
1. Check IAM permissions for AgentCore
2. Verify Amazon ECS/EKS permissions
3. Run permission setup scripts in agent directories

## Development

### Adding New Operations

1. Add API endpoint in `app.py`:
```python
@app.route('/api/new/operation', methods=['POST'])
def new_operation():
    # Implementation
    pass
```

2. Add UI button in `templates/index.html`:
```html
<button class="btn btn-primary" onclick="newOperation()">
    New Operation
</button>
```

3. Add JavaScript function:
```javascript
async function newOperation() {
    // Implementation
}
```

### Styling

The dashboard uses custom CSS with:
- Gradient background
- Card-based layout
- Responsive design
- Color-coded log levels
- Smooth animations

## Interface Overview

### Clean, Chat-Only Design
- **Amazon ECS Card**: Region selector + Chat interface + Output logs
- **EKS Card**: Cluster/Region inputs + Chat interface + Output logs
- **No buttons or forms** - everything through natural language
- **Real-time logs**: Color-coded output with timestamps
- **Conversation history**: See your chat with the agent

### Chat Interface Features
- **Natural language**: Just describe what you want to do
- **Context-aware**: Agents know your configuration
- **Fully automated**: No manual Docker commands needed
- **Clear feedback**: Step-by-step progress updates
- **Keyboard shortcuts**: Enter to send, Shift+Enter for new line

### Log Output
- **Timestamped entries**: Every message has a timestamp
- **Color-coded levels**: 
  - 🔵 Info (blue): General information
  - 🟢 Success (green): Successful operations
  - 🔴 Error (red): Errors and failures
  - 🟠 Warning (orange): Warnings and next steps
- **Auto-scroll**: Automatically scrolls to latest message
- **Monospace font**: Easy to read commands and technical output

## Documentation

- **[CHAT_GUIDE.md](CHAT_GUIDE.md)** - Complete guide to using the chat interface with examples
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide for getting up and running
- **[README.md](README.md)** - This file

## Key Features

### ✅ Implemented
- ✅ Conversational chat interface for both Amazon ECS and EKS
- ✅ **Fully automated Docker build and push**
- ✅ Natural language deployment workflows
- ✅ Context-aware agents with pre-configured settings
- ✅ Real-time log output with color coding
- ✅ Complete deployment workflows (ECR → Build → Deploy)
- ✅ OIDC and IRSA setup for EKS
- ✅ Delete operations for cleanup
- ✅ AWS CloudFormation stack management
- ✅ Multi-region support
- ✅ Multi-platform Docker builds (amd64, arm64)

### 🚀 Future Enhancements
- [ ] Multi-turn conversation memory
- [ ] Real-time log streaming with WebSockets
- [ ] Operation history and audit log
- [ ] Multi-region parallel operations
- [ ] Export logs to file
- [ ] Dark mode toggle
- [ ] Authentication/authorization
- [ ] Deployment templates
- [ ] Rollback functionality

## License

Same as parent project

## Support

For issues or questions, refer to the main project README or create an issue.
