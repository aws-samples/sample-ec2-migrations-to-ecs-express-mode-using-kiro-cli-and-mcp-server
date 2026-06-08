# Scripts

Automation scripts for deployment and cleanup.

## Deployment (`deployment/`)

### `deploy.sh`
Deploys the initial EC2-based blog application:
- Builds and deploys CDK infrastructure
- Deploys sample application to EC2 via SSM
- Configures environment variables from CloudFormation outputs
- Validates deployment via health checks

```bash
./deploy.sh              # Default: eu-north-1
./deploy.sh us-west-2    # Specific region
./deploy.sh us-west-2 no_default_vpc  # Create new VPC
```

### `deploy_eks_cluster.sh`
Deploys EKS Auto Mode cluster (alternative to using the Kiro skill's Phase 3):

```bash
./deploy_eks_cluster.sh          # Default: eu-north-1
./deploy_eks_cluster.sh us-west-2
```

## Cleanup (`cleanup/`)

### `legacy_destroy.sh`
Removes the CDK-deployed EC2 infrastructure:

```bash
./legacy_destroy.sh              # Default region
./legacy_destroy.sh us-west-2    # Specific region
```
