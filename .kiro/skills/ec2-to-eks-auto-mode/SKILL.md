---
name: ec2-to-eks-auto-mode-migration
description: >
  Migrates any application running on EC2 to Amazon EKS Auto Mode using the EKS
  MCP server. Supports any language/runtime (Node.js, Python, Java, Go, .NET, etc.).
  Use when user says "migrate to EKS", "move from EC2 to Kubernetes",
  "containerize for EKS", "deploy to EKS Auto Mode", "set up EKS cluster",
  "convert EC2 app to containers", or "migrate my app to Kubernetes".
  Do NOT use for ECS migrations, Lambda migrations, or general Kubernetes questions
  without migration intent.
metadata:
  author: aws-samples
  version: 1.1.0
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
- This skill is runtime-agnostic. Adapt Dockerfile patterns to the application's language.

## Critical: Region Consistency

ALL resources MUST be created in the SAME region as the user's existing application stack.

### Region Discovery (execute before Phase 1)

1. Find the `BlogAppStack` CloudFormation stack by checking all AWS regions:
   ```bash
   for region in us-east-1 us-east-2 us-west-1 us-west-2 ca-central-1 ca-west-1 eu-west-1 eu-west-2 eu-west-3 eu-central-1 eu-central-2 eu-north-1 eu-south-1 eu-south-2 ap-east-1 ap-south-1 ap-south-2 ap-southeast-1 ap-southeast-2 ap-southeast-3 ap-southeast-4 ap-southeast-5 ap-northeast-1 ap-northeast-2 ap-northeast-3 sa-east-1 af-south-1 me-south-1 me-central-1 il-central-1; do
     aws cloudformation describe-stacks --stack-name BlogAppStack --region $region --query 'Stacks[0].StackStatus' --output text 2>/dev/null && echo "Found in: $region" && break
   done
   ```
2. Store the region where `BlogAppStack` exists as `<TARGET_REGION>`.
3. Extract stack outputs **LIVE from CloudFormation** (do NOT use cached JSON files — they may be stale):
   ```bash
   aws cloudformation describe-stacks --stack-name BlogAppStack --region <TARGET_REGION> --query 'Stacks[0].Outputs' --output json
   ```
   Required outputs to capture:
   - `S3BucketName` → use in env var `S3_BUCKET` and IAM policy S3 resource ARN
   - `DynamoDBTableName` → use in env var `DYNAMODB_TABLE` and IAM policy DynamoDB resource ARN
   - `UserPoolId` → use in env var `COGNITO_USER_POOL_ID` and IAM policy Cognito resource ARN
   - `UserPoolClientId` → use in env var `COGNITO_CLIENT_ID`
4. Use `<TARGET_REGION>` for ALL subsequent operations: ECR, EKS cluster, IAM policy ARNs, Pod Identity associations, and `aws eks update-kubeconfig`.
5. NEVER default to `us-east-1` or any hardcoded region. Always derive from `BlogAppStack`.
6. If `BlogAppStack` is not found in any region, ASK the user for the correct region.

### Critical: IAM Policy Resource ARNs

When creating the Pod IAM policy (Phase 4), ALL resource ARNs MUST use `<TARGET_REGION>`.
A common failure is region mismatch in ARNs (e.g., policy says `ap-southeast-1` but
resources are in `ap-southeast-2`), which causes `AccessDeniedException` at runtime.

**Always verify**: the region in every ARN in the policy matches `<TARGET_REGION>`:
- `arn:aws:dynamodb:<TARGET_REGION>:<ACCOUNT>:table/<TABLE>`
- `arn:aws:s3:::<BUCKET>` (S3 is global but bucket name includes region)
- `arn:aws:cognito-idp:<TARGET_REGION>:<ACCOUNT>:userpool/<POOL_ID>`

## Critical: MCP Tool Usage

When this skill specifies an MCP tool (e.g., `manage_eks_stacks`, `generate_app_manifest`,
`apply_yaml`, `list_k8s_resources`, `get_pod_logs`, `get_k8s_events`), you MUST use that
MCP tool. Do NOT substitute with AWS CLI commands, kubectl commands, or any other fallback.

If an MCP tool is unavailable or fails:
1. Report the exact error to the user.
2. Ask the user to verify the MCP server is connected.
3. Do NOT proceed by substituting a CLI equivalent.

The MCP tools provide validated, consistent behavior. CLI fallbacks introduce the
trial-and-error approach this skill is designed to eliminate.

## Critical: AWS Knowledge MCP Server

Use the `aws-knowledge-mcp-server` to fetch EKS best practices, documentation, and
guidance at any phase. Specifically:
- Before creating the cluster, search for current EKS Auto Mode best practices.
- When configuring IAM Pod Identity, fetch latest documentation for correct trust policies.
- When the Troubleshooting table below doesn't resolve an issue, search for additional known issues.
- When making architecture decisions, consult AWS Well-Architected guidance for EKS.

Always prefer up-to-date documentation from the knowledge server over cached knowledge.

## Phase 1: Analyze and Containerize

### Step 1.1: Discover Application Profile

Inspect the EC2 application source and gather:

| Fact | How to Find |
|------|-------------|
| Language/Runtime | File extensions, package files (package.json, requirements.txt, pom.xml, go.mod, *.csproj) |
| Entry point | Start scripts, Procfile, main class, CMD in existing Dockerfile |
| Port | Config files, environment variables, code (listen/bind calls) |
| Environment variables | grep for env/os.environ/System.getenv/os.Getenv in source |
| AWS services used | SDK imports (DynamoDB, S3, SQS, SNS, etc.) |
| Health check endpoint | Routes like /health, /healthz, /status, /ping |
| Build steps | Makefile, build scripts, package manager commands |
| Static assets / volumes | Uploaded files, local storage paths |

If no health check endpoint exists, ask the user to add one before proceeding.

### Step 1.2: Create Dockerfile

Select the appropriate base image and build pattern for the runtime:

**Node.js:**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
USER node
```

**Python:**
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
USER nobody
```

**Java (Maven):**
```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn package -DskipTests
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
USER nobody
ENTRYPOINT ["java", "-jar", "app.jar"]
```

**Go:**
```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o server .
FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/server .
USER nobody
ENTRYPOINT ["./server"]
```

**.NET:**
```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS builder
WORKDIR /app
COPY *.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /out
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=builder /out .
USER app
ENTRYPOINT ["dotnet", "<AppName>.dll"]
```

Common rules for ALL runtimes:
- Multi-stage build (minimize image size)
- Non-root user (security)
- Copy dependency manifest first (layer caching)
- Use slim/alpine base where possible
- Add `EXPOSE <PORT>`

### Step 1.3: Create .dockerignore

Adapt to the runtime. Always exclude:
```
.git
.env
*.md
tests/
coverage/
.dockerignore
Dockerfile
```

Runtime-specific exclusions:
- Node.js: `node_modules`
- Python: `__pycache__`, `.venv`, `*.pyc`
- Java: `target/`
- Go: vendor/ (if not vendoring)
- .NET: `bin/`, `obj/`

### Step 1.4: Build and Test Locally

```bash
docker build -t <app-name> .
docker run -p <PORT>:<PORT> \
  -e <ENV_VAR_1>=<value> \
  -e <ENV_VAR_2>=<value> \
  <app-name>
curl http://localhost:<PORT>/<health-path>
```

### GATE 1: Container health check returns 200. If not, fix before proceeding.

## Phase 2: Push to ECR

### Step 2.1: Create Repository and Push

Create ECR in `<TARGET_REGION>` (the same region as the existing application stack).

```bash
aws ecr create-repository --repository-name <app-name> --region <TARGET_REGION>
aws ecr get-login-password --region <TARGET_REGION> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<TARGET_REGION>.amazonaws.com
docker build --platform linux/amd64 -t <account-id>.dkr.ecr.<TARGET_REGION>.amazonaws.com/<app-name>:latest .
docker push <account-id>.dkr.ecr.<TARGET_REGION>.amazonaws.com/<app-name>:latest
```

Note: Always build with `--platform linux/amd64` for EKS compatibility (even on ARM Macs).

### GATE 2: Image exists in ECR.
```bash
aws ecr describe-images --repository-name <app-name> --region <TARGET_REGION> --query 'imageDetails[0].imageTags'
```

## Phase 3: Create EKS Auto Mode Cluster

**Pre-condition (MUST pass before proceeding):**
- Determine the region of the existing CloudFormation stack (from Step 2 deployment output)
- Verify that `AWS_DEFAULT_REGION` or the `--region` parameter passed to `manage_eks_stacks` matches this region exactly
- If mismatched, STOP and prompt the user to correct the region before continuing

**Action:** Use `manage_eks_stacks` MCP tool to create the EKS Auto Mode cluster in the SAME region as the existing stack.

**Gate:** CloudFormation status is CREATE_COMPLETE AND cluster region matches existing stack region.

### Step 3.1: Determine Latest Kubernetes Version

**CRITICAL**: The `manage_eks_stacks` template may have outdated `AllowedValues` for
`KubernetesVersion`. You MUST look up the latest version before deploying.

Use `aws-knowledge-mcp-server` `read_documentation` tool:
- URL: `https://docs.aws.amazon.com/eks/latest/userguide/platform-versions.html`
- Find the highest Kubernetes minor version listed (e.g., `1.35`)

If the user requested "latest version", use this value. Never rely on the template's default.

### Step 3.2: Generate CloudFormation Template

Use `manage_eks_stacks` MCP tool:
- `operation`: `generate`
- `cluster_name`: `<app-name>-cluster`

### Step 3.3: Patch Template Version

Before deploying, modify the generated template content:
1. Add the latest version (from Step 3.1) to `Parameters.KubernetesVersion.AllowedValues`
2. Set `Parameters.KubernetesVersion.Default` to the latest version

This ensures the cluster is created with the latest supported Kubernetes version.

### Step 3.4: Deploy Cluster

Use `manage_eks_stacks` MCP tool:
- `operation`: `deploy`
- `cluster_name`: `<app-name>-cluster`
- `template_content`: the patched template from Step 3.3

This takes 15-20 minutes.

### Step 3.5: Update kubeconfig

```bash
aws eks update-kubeconfig --name <app-name>-cluster --region <TARGET_REGION>
```

### GATE 3: Cluster is active.

Use `manage_eks_stacks` MCP tool:
- `operation`: `describe`
- `cluster_name`: `<app-name>-cluster`

Status must be `CREATE_COMPLETE`.

## Phase 4: Configure IAM Pod Identity

### Step 4.1: Create Pod IAM Policy

Create a policy matching the EC2 instance profile permissions.
See `references/iam-policy-template.md` for common patterns.

Identify which AWS services the app uses and grant least-privilege access.

```bash
aws iam create-policy --policy-name <app-name>-pod-policy --policy-document file://policy.json
```

### Step 4.2: Create Pod Role

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
  --role-arn arn:aws:iam::<account-id>:role/<app-name>-pod-role \
  --region <TARGET_REGION>
```

### GATE 4: Pod identity association exists.
```bash
aws eks list-pod-identity-associations --cluster-name <app-name>-cluster --region <TARGET_REGION> --query 'associations[0].associationId'
```

## Phase 5: Deploy Application

### Step 5.1: Generate Manifest

Use `generate_app_manifest` MCP tool:
- `app_name`: `<app-name>`
- `image_uri`: `<account-id>.dkr.ecr.<TARGET_REGION>.amazonaws.com/<app-name>:latest`
- `port`: `<PORT>`
- `replicas`: `2`
- `namespace`: `default`
- `load_balancer_scheme`: `internet-facing`
- `output_dir`: `/tmp`

### Step 5.2: Patch Manifest

Add to the generated YAML:
- `spec.template.spec.serviceAccountName: <app-name>-sa`
- All environment variables the app needs under `containers[0].env`
- Liveness probe: `httpGet /<health-path>` port `<PORT>`, initialDelaySeconds appropriate for runtime (10s Node/Go/Python, 30s Java/.NET)
- Readiness probe: `httpGet /<health-path>` port `<PORT>`, initialDelaySeconds 5
- Resource requests/limits (see `references/manifest-patch.md`)

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

### Step 6.2: Test Health

```bash
curl http://<lb-hostname>/<health-path>
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
4. Destroy infrastructure stack (e.g., `cdk destroy`, `terraform destroy`, or CloudFormation delete)

## Cluster Deletion

To delete the EKS cluster and its underlying infrastructure:

### Using `manage_eks_stacks` (preferred)

Use the `manage_eks_stacks` MCP tool:
- `operation`: `delete`
- `cluster_name`: `<app-name>-cluster`

**Known limitation**: The `manage_eks_stacks` tool does NOT support a region parameter. It uses the default AWS region from your environment. If the cluster was created in a different region, the tool will fail with "Stack not found."

### Fallback: Direct CloudFormation deletion (cross-region)

If the MCP tool fails due to region mismatch, use the AWS CLI directly:

```bash
aws cloudformation delete-stack --stack-name eks-<app-name>-cluster-stack --region <TARGET_REGION>
```

Monitor deletion progress:
```bash
aws cloudformation describe-stacks --stack-name eks-<app-name>-cluster-stack --region <TARGET_REGION> --query 'Stacks[0].StackStatus'
```

Stack deletion typically takes 10–15 minutes and removes:
- The EKS cluster and all workloads
- The dedicated VPC (subnets, route tables, internet gateway)
- Security groups
- IAM roles created by the stack

### Pre-deletion cleanup

Before deleting the stack, remove any resources created outside CloudFormation to avoid `DELETE_FAILED`:
1. Delete Kubernetes LoadBalancer services (which create AWS ALBs/NLBs):
   ```bash
   kubectl delete svc --all -n default
   ```
2. Delete Pod Identity associations:
   ```bash
   aws eks delete-pod-identity-association --cluster-name <app-name>-cluster --association-id <id> --region <TARGET_REGION>
   ```
3. Delete the IAM pod role and policy:
   ```bash
   aws iam detach-role-policy --role-name <app-name>-pod-role --policy-arn arn:aws:iam::<account-id>:policy/<app-name>-pod-policy
   aws iam delete-role --role-name <app-name>-pod-role
   aws iam delete-policy --policy-arn arn:aws:iam::<account-id>:policy/<app-name>-pod-policy
   ```
4. Delete the ECR repository:
   ```bash
   aws ecr delete-repository --repository-name <app-name> --force --region <TARGET_REGION>
   ```

## Troubleshooting

| Symptom | Diagnosis Tool | Root Cause | Fix |
|---------|---------------|------------|-----|
| Pods stuck Pending | `get_k8s_events` for Pod | Auto Mode provisioning nodes | Wait 2-3 min. If >5 min, check resource requests |
| ImagePullBackOff | `get_k8s_events` for Pod | Wrong ECR URI or no access | Verify image URI matches ECR exactly |
| CrashLoopBackOff | `get_pod_logs` with `previous: true` | App crash on startup | Check env vars, port mismatch, missing deps |
| OOMKilled | Pod events | Memory limit too low | Increase resources.limits.memory |
| Health check fail | Pod events | Wrong path or port in probe | Match probe config to actual health endpoint |
| No LB hostname | Service events | ALB still provisioning | Wait 2-3 min. Check service type is LoadBalancer |
| AWS SDK AccessDenied | App logs | Pod identity misconfigured | Verify SA name matches pod identity association |
| AWS SDK AccessDenied (DynamoDB/S3/Cognito) | App logs show `AccessDeniedException` | IAM policy resource ARNs have wrong region | Check every ARN in the pod policy uses `<TARGET_REGION>`, not a different region. Update policy with `aws iam create-policy-version` |
| Cognito "User pool client does not exist" | App logs or UI error | Stale/incorrect Cognito Client ID | Re-extract `UserPoolClientId` LIVE from `BlogAppStack` outputs — do not trust cached JSON files |
| Nodes never appear | `get_eks_insights` | No workload scheduled | Deploy a pod first — Auto Mode is demand-driven |
| Slow startup (Java/.NET) | Probe failures | initialDelaySeconds too low | Increase to 30-60s for JVM/.NET cold start |

## Examples

### Example 1: Node.js Blog App

User says: "Migrate my blog app from EC2 to EKS"

Profile: Node.js, port 80, uses DynamoDB + S3, health at /health

### Example 2: Python Flask API

User says: "Move my Python API to Kubernetes"

Profile: Python 3.11, port 5000, uses SQS + DynamoDB, health at /healthz

### Example 3: Java Spring Boot Service

User says: "Containerize my Java service for EKS"

Profile: Java 21, port 8080, uses RDS (via Secrets Manager) + S3, health at /actuator/health
Note: Needs 30s initialDelaySeconds for JVM warmup, 512Mi+ memory.

### Example 4: Go Microservice

User says: "Deploy my Go service to EKS Auto Mode"

Profile: Go 1.22, port 8080, uses DynamoDB, health at /ping
Note: Tiny image (~15MB), fast startup, can use low resource requests.
