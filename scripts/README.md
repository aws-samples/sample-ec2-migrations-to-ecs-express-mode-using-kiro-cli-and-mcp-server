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
- Supports multi-region deployment (see `REGION_CONFIG.md`)

#### `deploy_eks_cluster.sh`
EKS cluster deployment script:
- Provisions EKS cluster infrastructure
- Configures node groups and networking

#### `test_rest-api_server.py`
REST API server testing and validation:
- Tests REST API server endpoints
- Validates deployment capabilities

#### `REGION_CONFIG.md`
Multi-region deployment configuration guide:
- Region parameter usage for `deploy.sh`
- CDK deployment per region
- Current deployment details

#### `eks-outputs.json`
EKS deployment output configuration:
- Stores EKS cluster outputs for reference

### Cleanup Scripts (`cleanup/`)

#### `destroy_ecs_dynamic.sh`
Dynamic Amazon ECS resource cleanup:
- **Tag-based discovery**: Uses `ManagedBy=MCP-Server` tags
- **Safe execution**: Only deletes project resources
- **Comprehensive cleanup**: Amazon ECS, ALB, IAM, ECR, CloudWatch
- **Policy management**: Dynamically detaches all policies
- **Fallback patterns**: Name-based matching as backup

#### `legacy_destroy.sh`
Legacy resource cleanup:
- Cleans up older deployment resources
- Fallback for resources not tagged with current conventions

## Usage

### Deployment
```bash
# Deploy infrastructure (default: eu-north-1)
cd scripts/deployment
./deploy.sh

# Deploy to specific region
./deploy.sh us-west-2
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
