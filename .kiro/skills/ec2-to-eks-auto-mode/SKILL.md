---
name: ec2-to-eks-auto-mode-migration
description: >
  Migrates Node.js applications from EC2 to Amazon EKS Auto Mode using the EKS
  MCP server. Use when user says "migrate to EKS", "move from EC2 to Kubernetes",
  "containerize for EKS", "deploy to EKS Auto Mode", "set up EKS cluster", or
  "convert EC2 app to containers". Do NOT use for ECS migrations, Lambda migrations,
  or general Kubernetes questions without migration intent.
metadata:
  author: aws-samples
  version: 1.0.0
  mcp-server: awslabs.eks-mcp-server
  category: migration
  tags: [eks, ec2, kubernetes, auto-mode, containerization, migration]
---

# EC2 to EKS Auto Mode Migration

## Overview

This skill executes a deterministic 7-phase migration from EC2 to EKS Auto Mode.
Each phase has a validation gate. Do NOT proceed to the next phase until the gate passes.

EKS Auto Mode eliminates node group management — AWS provisions, scales, and patches
nodes automatically based on pod demand.

## Important

- Follow phases sequentially. Never skip a gate.
- If a gate fails, consult the Troubleshooting section before retrying.
- Never guess parameters. Read them from prior step outputs or ask the user.
- Use MCP tools when available instead of shell commands.

## Phase 1: Analyze and Containerize

### Step 1.1: Gather Application Facts

Identify these from the source code:
- Entry point (e.g., `server.js`, `app.js`)
- Port (`process.env.PORT` or hardcoded)
- Environment variables (grep for `process.env`)
- AWS services used (DynamoDB, S3, SQS, etc.)
- Health check endpoint path

### Step 1.2: Create Dockerfile

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
EXPOSE <PORT>
USER node
CMD ["node", "<entry-point>"]
```

Rules:
- Multi-stage build (smaller image)
- `npm ci` not `npm install` (reproducible)
- Non-root user (security)
- Alpine base (minimal attack surface)

### Step 1.3: Create .dockerignore

```
node_modules
.git
.env
*.md
tests/
coverage/
.dockerignore
Dockerfile
```

### Step 1.4: Build and Test Locally

```bash
docker build -t <app-name> .
docker run -p <PORT>:<PORT> -e AWS_REGION=<region> -e DYNAMODB_TABLE=<table> -e S3_BUCKET=<bucket> <app-name>
curl http://localhost:<PORT>/health
```

### GATE 1: Container health check returns 200. If not, fix before proceeding.

## Phase 2: Push to ECR

### Step 2.1: Create Repository and Push

```bash
aws ecr create-repository --repository-name <app-name> --region <region>
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker build --platform linux/amd64 -t <account-id>.dkr.ecr.<region>.amazonaws.com/<app-name>:latest .
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<app-name>:latest
```

### GATE 2: Image exists in ECR.
```bash
aws ecr describe-images --repository-name <app-name> --region <region> --query 'imageDetails[0].imageTags'
```

## Phase 3: Create EKS Cluster

### Step 3.1: Generate CloudFormation Template

Use `manage_eks_stacks` MCP tool:
- `operation`: `generate`
- `cluster_name`: `<app-name>-cluster`
- `template_file`: `/tmp/<app-name>-eks-template.yaml`

### Step 3.2: Deploy Cluster

Use `manage_eks_stacks` MCP tool:
- `operation`: `deploy`
- `cluster_name`: `<app-name>-cluster`
- `template_file`: `/tmp/<app-name>-eks-template.yaml`

This takes 15-20 minutes.

### Step 3.3: Update kubeconfig

```bash
aws eks update-kubeconfig --name <app-name>-cluster --region <region>
```

### GATE 3: Cluster is active.

Use `manage_eks_stacks` MCP tool:
- `operation`: `describe`
- `cluster_name`: `<app-name>-cluster`

Status must be `CREATE_COMPLETE`.

## Phase 4: Configure IAM Pod Identity

### Step 4.1: Create Pod IAM Policy

Create a policy with the same permissions the EC2 instance profile had.
See `references/iam-policy-template.md` for the template.

```bash
aws iam create-policy --policy-name <app-name>-pod-policy --policy-document file://policy.json
```

### Step 4.2: Create Pod Role with EKS Pod Identity Trust

```bash
aws iam create-role --role-name <app-name>-pod-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"]
  }]
}'
aws iam attach-role-policy --role-name <app-name>-pod-role --policy-arn arn:aws:iam::<account-id>:policy/<app-name>-pod-policy
```

### Step 4.3: Create Service Account and Pod Identity Association

```bash
kubectl create serviceaccount <app-name>-sa -n default
aws eks create-pod-identity-association \
  --cluster-name <app-name>-cluster \
  --namespace default \
  --service-account <app-name>-sa \
  --role-arn arn:aws:iam::<account-id>:role/<app-name>-pod-role
```

### GATE 4: Pod identity association exists.
```bash
aws eks list-pod-identity-associations --cluster-name <app-name>-cluster --query 'associations[0].associationId'
```

## Phase 5: Deploy Application

### Step 5.1: Generate Manifest

Use `generate_app_manifest` MCP tool:
- `app_name`: `<app-name>`
- `image_uri`: `<account-id>.dkr.ecr.<region>.amazonaws.com/<app-name>:latest`
- `port`: `<PORT>`
- `replicas`: `2`
- `namespace`: `default`
- `load_balancer_scheme`: `internet-facing`
- `output_dir`: `/tmp`

### Step 5.2: Patch Manifest

Add to the generated YAML:
- `spec.template.spec.serviceAccountName: <app-name>-sa`
- Environment variables under containers[0].env
- Liveness probe: `httpGet /health` port `<PORT>`, initialDelaySeconds 10
- Readiness probe: `httpGet /health` port `<PORT>`, initialDelaySeconds 5

See `references/manifest-patch.md` for the exact structure.

### Step 5.3: Apply

Use `apply_yaml` MCP tool:
- `yaml_path`: path to manifest
- `cluster_name`: `<app-name>-cluster`
- `namespace`: `default`
- `force`: true

### GATE 5: All pods Running and Ready.

Use `list_k8s_resources` MCP tool:
- `cluster_name`: `<app-name>-cluster`
- `kind`: `Pod`
- `api_version`: `v1`
- `namespace`: `default`
- `label_selector`: `app=<app-name>`

All pods must show Running status. With Auto Mode, first pod may take 2-3 minutes while nodes provision.

## Phase 6: Verify

### Step 6.1: Get Load Balancer URL

```bash
kubectl get svc <app-name> -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

Wait 2-3 minutes for ALB provisioning if empty.

### Step 6.2: Test

```bash
curl http://<lb-hostname>/health
```

### Step 6.3: If Failing, Check Logs

Use `get_pod_logs` MCP tool:
- `cluster_name`: `<app-name>-cluster`
- `namespace`: `default`
- `pod_name`: from pod list
- `tail_lines`: 50

### GATE 6: Health endpoint returns 200 from the load balancer URL.

## Phase 7: Decommission EC2

Only after Gate 6 passes and traffic is verified:
1. Update DNS/routing to point to EKS load balancer
2. Terminate EC2 instance
3. Delete EC2 security groups and IAM instance profile
4. Destroy CDK stack: `cdk destroy`

## Troubleshooting

| Symptom | Diagnosis Tool | Root Cause | Fix |
|---------|---------------|------------|-----|
| Pods stuck Pending | `get_k8s_events` for Pod | Auto Mode provisioning nodes | Wait 2-3 min. If >5 min, check resource requests |
| ImagePullBackOff | `get_k8s_events` for Pod | Wrong ECR URI or no access | Verify image URI matches ECR exactly |
| CrashLoopBackOff | `get_pod_logs` with `previous: true` | App crash on startup | Check env vars, port mismatch, missing deps |
| Health check fail | Pod events | Wrong path or port in probe | Match probe config to actual health endpoint |
| No LB hostname | Service events | ALB still provisioning | Wait 2-3 min. Check service type is LoadBalancer |
| DynamoDB AccessDenied | App logs | Pod identity misconfigured | Verify SA name in deployment matches pod identity association |
| Nodes never appear | `get_eks_insights` | No workload scheduled | Deploy a pod first — Auto Mode is demand-driven |

## Examples

### Example 1: Blog Application Migration

User says: "Migrate my blog app from EC2 to EKS"

Actions:
1. Read app source to identify port (80), entry point (server.js), env vars (DYNAMODB_TABLE, S3_BUCKET)
2. Create Dockerfile with port 80, node server.js
3. Build and push to ECR
4. Create EKS cluster with Auto Mode
5. Set up pod identity for DynamoDB + S3 access
6. Deploy with 2 replicas, internet-facing LB
7. Verify health check at LB URL

Result: Application running on EKS with automatic scaling, no node management.

### Example 2: API Service with Custom Domain

User says: "Move my API from EC2 to Kubernetes with auto-scaling"

Actions:
1. Analyze API (port 3000, uses Redis + DynamoDB)
2. Containerize, push to ECR
3. Create EKS cluster
4. Configure pod identity for DynamoDB
5. Deploy with readiness/liveness probes on /health
6. Verify via LB hostname

Result: API on EKS Auto Mode with pod-driven auto-scaling.
