# Scripts

Automation scripts for deployment, migration, and cleanup operations.

## Structure

### Deployment Scripts (`deployment/`)

#### `deploy.sh`
Main deployment script that:
- Builds and deploys CDK infrastructure
- Deploys sample application to EC2
- Configures load balancer and health checks
- Validates deployment

#### `deploy_complete_ecs_infrastructure.py`
Complete Amazon ECS deployment from scratch:
- Creates ECR repository and IAM roles
- Builds and pushes container image
- Deploys Amazon ECS Express Mode service
- Monitors deployment progress

#### `migrate_to_ecs_express.py`
EC2 to Amazon ECS migration orchestrator:
- Uses MCP server for automation
- Handles containerization process
- Manages Amazon ECS deployment
- Provides status updates

#### `test_mcp_server.py`
MCP server testing and validation:
- Tests all MCP server endpoints
- Validates prerequisites
- Checks deployment capabilities

#### `set_mcp_env.sh`
Environment setup script:
- Sets MCP server URL and API key
- Configures AWS region
- Validates environment variables

### Cleanup Scripts (`cleanup/`)

#### `destroy_ecs_dynamic.sh`
Dynamic Amazon ECS resource cleanup:
- **Tag-based discovery**: Uses `ManagedBy=MCP-Server` tags
- **Safe execution**: Only deletes project resources
- **Comprehensive cleanup**: Amazon ECS, ALB, IAM, ECR, CloudWatch
- **Policy management**: Dynamically detaches all policies
- **Fallback patterns**: Name-based matching as backup

**Features:**
- Discovers resources by tags first
- Falls back to name patterns for compatibility
- Handles all policy types (managed and inline)
- Provides detailed logging
- Skips non-project resources

## Usage

### Deployment
```bash
# Set environment
cd scripts/deployment
source set_mcp_env.sh

# Deploy infrastructure
./deploy.sh

# Or migrate existing EC2
python migrate_to_ecs_express.py
```

### Cleanup
```bash
cd scripts/cleanup
./destroy_ecs_dynamic.sh
```

## Safety Features

### Tag-Based Resource Management
All scripts use consistent tagging:
- Only manages resources with `ManagedBy=MCP-Server`
- Skips production or unrelated resources
- Provides clear logging of actions

### Error Handling
- Graceful failure handling
- Rollback capabilities where applicable
- Detailed error reporting
- Safe defaults

### Validation
- Prerequisites checking
- Resource existence validation
- Permission verification
- Status monitoring
