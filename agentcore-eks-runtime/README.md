# AgentCore EKS Auto Mode Runtime

AWS-managed MCP runtime for deploying containerized applications to EKS Auto Mode with IRSA support.

## 🔄 Protocol: Model Context Protocol (MCP)

This runtime uses the **Model Context Protocol (MCP)** with FastMCP:
- **Transport:** Streamable HTTP (SSE - Server-Sent Events)
- **Format:** JSON-RPC 2.0
- **Authentication:** AWS SigV4 signing
- **Dependencies:** `mcp`, `boto3`, `kubernetes`

**Key Difference:** Unlike the Amazon ECS runtime which uses Strands protocol, this runtime uses the open-standard MCP protocol for tool invocation.

## ⚠️ Current Issue: 406 Error?

**Quick fix:**
```bash
./fix-and-redeploy.sh
```

See **[START_HERE.md](START_HERE.md)** for details.

## 🚀 Quick Start

### Option 1: Standalone Mode (Recommended - No Setup)
```bash
cd ../test-python-scripts
python3 test_eks_conversation.py
```

### Option 2: AgentCore Runtime (One Command Setup)
```bash
./setup-and-test.sh
```

This single script creates IAM role, assumes it, and tests the connection automatically!

See **[QUICKSTART.md](QUICKSTART.md)** for details.

## Tools

1. **setup_oidc_provider** - Create OIDC identity provider for EKS
2. **create_irsa_role** - Create IAM role with Amazon S3/Amazon DynamoDB permissions
3. **build_image_with_codebuild** - Build Docker image using AWS CodeBuild
4. **deploy_to_eks_with_irsa** - Deploy to EKS with IRSA configuration
5. **get_deployment_status** - Check deployment status
6. **delete_eks_deployment** - Delete EKS deployment, service, and service account

## Deploy Agent

```bash
cd agentcore-eks-runtime

# Deploy agent
agentcore launch

# Add EKS permissions to AgentCore execution role (auto-detects role and region)
bash add-eks-permissions.sh

# Or specify role and region explicitly
bash add-eks-permissions.sh AmazonBedrockAgentCoreSDKRuntime-us-west-2-976ef190c4 us-west-2

# Add AgentCore role to EKS cluster access (auto-detects role)
bash add-eks-cluster-access.sh my-eks-cluster eu-north-1

# Or specify all parameters explicitly
bash add-eks-cluster-access.sh my-eks-cluster eu-north-1 AmazonBedrockAgentCoreSDKRuntime-us-west-2-976ef190c4

# Verify
agentcore status
```

**Important:** Both permission scripts must be run after deploying the agent for the first time.

## Setup IAM (for AgentCore mode)

**One command:**
```bash
./setup-and-test.sh
```

This creates IAM role, assumes it, exports credentials, and tests the connection.

**Manual steps:** See [AUTHORIZER_SETUP.md](AUTHORIZER_SETUP.md)

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - ⭐ Start here!
- **[SETUP_SUMMARY.md](SETUP_SUMMARY.md)** - Complete overview
- **[AUTHORIZER_SETUP.md](AUTHORIZER_SETUP.md)** - Detailed IAM setup
- **[README_AUTHORIZER.md](README_AUTHORIZER.md)** - Quick reference

## Files

- `agent.py` - V2 Agent with boto3 + kubernetes client
- `agent_v2_boto3.py` - V2 source implementation
- `requirements.txt` - Python dependencies (boto3, kubernetes, mcp)
- `.bedrock_agentcore.yaml` - Agent configuration
- `add-eks-permissions.sh` - ⭐ Add EKS/ECR/IAM/CodeBuild permissions to AgentCore role
- `add-eks-cluster-access.sh` - ⭐ Add AgentCore role to EKS cluster with admin access
- `redeploy_agent.sh` - Redeploy agent

## Permission Scripts

### add-eks-permissions.sh
Adds the following permissions to the AgentCore execution role:
- **EKS**: Full access (eks:*)
- **IAM**: OIDC provider and role management
- **ECR**: Full access (ecr:*)
- **CodeBuild**: Full access (codebuild:*)
- **STS**: GetCallerIdentity
- **Amazon S3**: CodeBuild source bucket access

**Usage:**
```bash
# Auto-detect role and use AWS CLI default region
./add-eks-permissions.sh

# Specify role name
./add-eks-permissions.sh AmazonBedrockAgentCoreSDKRuntime-us-west-2-976ef190c4

# Specify both role and region
./add-eks-permissions.sh AmazonBedrockAgentCoreSDKRuntime-us-west-2-976ef190c4 us-west-2
```

### add-eks-cluster-access.sh
Adds the AgentCore execution role to the EKS cluster using EKS Access Entries:
- Creates access entry for the role
- Associates `AmazonEKSClusterAdminPolicy`
- Enables kubernetes client authentication

**Usage:**
```bash
# Auto-detect role, specify cluster and region
./add-eks-cluster-access.sh my-eks-cluster eu-north-1

# Specify all parameters explicitly
./add-eks-cluster-access.sh my-eks-cluster eu-north-1 AmazonBedrockAgentCoreSDKRuntime-us-west-2-976ef190c4
```

**Note:** Both scripts must be run after deploying the agent for the first time.
