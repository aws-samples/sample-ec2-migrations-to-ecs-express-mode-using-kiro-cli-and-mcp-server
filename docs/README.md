# Amazon EC2 to Amazon ECS Express Mode Migration Project

This project demonstrates migrating a secure blog application from Amazon EC2 to Amazon ECS Express Mode using AWS MCP Server tools.

## Project Structure

```
ec2-ecs-express-mode-using-mcp/
├── README.md                           # This file
├── migrate-ec2-to-ecs-express-mode.md  # Complete migration guide
├── diagram_5dead411.png               # Architecture diagram
├── sample-app/                        # Sample blog application
│   ├── src/server.js                  # Node.js application
│   ├── public/index.html              # Frontend with Amazon Cognito auth
│   ├── package.json                   # Dependencies
│   ├── Dockerfile                     # Optimized container config
│   └── README.md                      # Application documentation
├── cdk-infrastructure/                # CDK deployment code
│   ├── lib/cdk-infrastructure-stack.ts # Infrastructure as code
│   ├── bin/cdk-infrastructure.ts      # CDK app entry point
│   └── package.json                   # CDK dependencies
└── mcp-servers/                       # MCP server implementations
    └── container-migration/           # Phase 2 automation
        ├── server.py                  # MCP server implementation
        ├── requirements.txt           # Python dependencies
        ├── test.sh                    # Test script
        ├── package.json               # Metadata
        └── README.md                  # MCP server documentation
```

## Quick Start

### 1. Set up MCP Server Environment
```bash
source set_mcp_env.sh
```

### 2. Deploy Infrastructure Options

**Option A: Complete Amazon ECS Infrastructure from Scratch**
```bash
python deploy_complete_ecs_infrastructure.py
```

**Option B: Deploy Amazon EC2 First, Then Migrate**
```bash
cd cdk-infrastructure
npm install
cdk deploy
cd ..
python migrate_to_ecs_express.py
```

### 3. Clean Up Everything
```bash
./destroy_ecs_infrastructure.sh
```

## Complete Infrastructure Lifecycle

The project now supports end-to-end infrastructure management:

- **MCP Server**: Deployed at `https://d1lx8mfyu4.execute-api.us-west-2.amazonaws.com/Prod`
- **Auto-provisioning**: Creates ECR repositories and IAM roles automatically
- **Complete cleanup**: Removes all resources including custom IAM roles
- **Security**: Uses environment variables for API keys

## Key Features

- **Secure Authentication**: Amazon Cognito User Pool with JWT validation
- **Private Storage**: Amazon S3 bucket with presigned URLs
- **Production Ready**: Non-root containers, health checks, security recommended practices
- **Automated Migration**: MCP server tools for containerization
- **Zero Downtime**: Blue-green deployment strategy

## Architecture

![Current Amazon EC2 Architecture](diagram_5dead411.png)

## MCP Server Integration

Add to your MCP client configuration:

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

## Migration Benefits

- **60-80% reduction** in operational overhead
- **Zero server patching** with managed containers
- **Automatic scaling** based on demand
- **Cost optimization** through right-sizing
- **Faster deployments** with container workflows

## Environment Variables Setup

### Required Environment Variables

Before running the migration scripts, set the following environment variables:

```bash
# MCP Server Configuration
export MCP_API_URL="https://your-api-gateway-url.execute-api.region.amazonaws.com/Prod"
export MCP_API_KEY="your-actual-api-key-from-secrets-manager"
```

### Setting Environment Variables

#### Option 1: Export in Terminal
```bash
export MCP_API_URL="https://d1lx8mfyu4.execute-api.us-west-2.amazonaws.com/Prod"
export MCP_API_KEY="$(aws secretsmanager get-secret-value --secret-id mcp-api-key --query SecretString --output text)"
```

#### Option 2: Create .env file (add to .gitignore)
```bash
# Create .env file
cat > .env << EOF
MCP_API_URL=https://d1lx8mfyu4.execute-api.us-west-2.amazonaws.com/Prod
MCP_API_KEY=your-actual-api-key
EOF

# Load environment variables
source .env
```

#### Option 3: Use AWS Secrets Manager
Store your API key in AWS Secrets Manager and retrieve it:

```bash
# Store the key in Secrets Manager
aws secretsmanager create-secret \
    --name "mcp-api-key" \
    --description "API key for MCP server" \
    --secret-string "your-actual-api-key"

# Retrieve and use the key
export MCP_API_KEY=$(aws secretsmanager get-secret-value \
    --secret-id mcp-api-key \
    --query SecretString \
    --output text)
```

### Running the Scripts

After setting the environment variables:

```bash
# Run migration
python3 migrate_to_ecs_express.py

# Run tests
python3 test_mcp_server.py
```

### Security Notes

- Never commit API keys to version control
- Use AWS Secrets Manager for production environments
- The example key `AKIAIOSFODNN7EXAMPLE` is AWS-approved for testing/documentation only
- Always rotate API keys regularly

## Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed and running
- Node.js 18+ for local development
- Python 3.8+ for MCP server
- CDK CLI for infrastructure deployment

## Support

For questions or issues, refer to the detailed migration guide or check the individual component README files.
