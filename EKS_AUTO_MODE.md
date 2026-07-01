# EC2 to EKS Auto Mode Migration

This branch contains the companion code for the blog post: **[Migrate Amazon EC2 to EKS Auto Mode using Kiro CLI and MCP Servers](#)**.

## Quick Start

```bash
git clone -b eks-auto-mode https://github.com/aws-samples/sample-ec2-migrations-to-ecs-express-mode-using-kiro-cli-and-mcp-server
cd sample-ec2-migrations-to-ecs-express-mode-using-kiro-cli-and-mcp-server
```

Then follow the blog post walkthrough for the full migration steps.

## What's in this branch

| Directory | Purpose |
|-----------|---------|
| `sample-application/` | Node.js blog app (the workload to migrate) |
| `infrastructure/cdk/` | CDK stack for the initial EC2 deployment |
| `infrastructure/eks-auto-mode/` | CDK stack for EKS Auto Mode cluster |
| `.kiro/skills/ec2-to-eks-auto-mode/` | Kiro CLI migration skill (7-phase workflow) |
| `.kiro/agents/eks-migration.json` | Agent configuration for Kiro CLI |
| `scripts/deployment/` | Deployment scripts |
| `scripts/cleanup/` | Cleanup scripts |

## Related Blog Posts

- [Migrate Amazon EC2 to ECS Express Mode using Kiro CLI and MCP Servers](https://aws.amazon.com/blogs/containers/migrate-amazon-ec2-to-ecs-express-mode-using-kiro-cli-and-mcp-servers/) — uses the `main` branch
- **EC2 to EKS Auto Mode** (this blog) — uses this `eks-auto-mode` branch
