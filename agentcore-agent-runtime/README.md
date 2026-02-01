# AgentCore Agent Runtime for Amazon ECS Deployment

This directory contains the **Amazon Bedrock AgentCore Agent** that automates Amazon ECS Express Mode deployments using the Strands framework.

## 🔄 Protocol: Strands (AWS Proprietary)

This runtime uses the **Strands protocol**:
- **Transport:** HTTP with Strands-specific format
- **Format:** Strands conversation API
- **Authentication:** AWS SigV4 signing
- **Dependencies:** `strands`, `boto3`

**Key Difference:** Unlike the EKS runtime which uses MCP (Model Context Protocol), this runtime uses AWS's proprietary Strands protocol for conversation-based agent interactions.

## 🎯 What is AgentCore?

**Amazon Bedrock AgentCore** is an AWS-managed service that hosts AI agents with built-in tools. This agent uses the **Strands** framework to provide 5 MCP-compatible tools for deploying containerized applications to AWS Amazon ECS Express Mode.

## 🔧 Available Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `create_ecr_repository` | Create ECR repository | `app_name`, `region` |
| `deploy_ecs_express_service` | Deploy Amazon ECS Express Gateway Service | `service_name`, `image_uri`, `cpu`, `memory`, `port`, `region`, `environment_variables`, `desired_count` |
| `list_ecs_services` | List all Amazon ECS services | `region` |
| `check_service_status` | Check deployment status | `service_arn` or `stack_name`, `region` |
| `scale_service` | Scale service to N tasks | `service_name`, `desired_count`, `region` |
| `delete_ecs_service` | Delete Amazon ECS service and resources | `service_name` or `stack_name`, `region` |

## 📋 Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Python 3.10+** installed
3. **bedrock-agentcore-starter-toolkit** installed:
   ```bash
   pip install bedrock-agentcore-starter-toolkit
   ```

## 🚀 Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Deploy Agent to AWS

```bash
# Deploy the agent (one-time)
agentcore launch

# This can:
# - Package the agent code
# - Create AWS resources (AWS Lambda, IAM roles)
# - Deploy to Amazon Bedrock AgentCore
# - Return an Agent ARN
```

### 3. Verify Deployment

```bash
agentcore status
```

**Expected Output:**
```
✅ Agent Status: ecs_deployment_agent
Ready - Agent deployed and endpoint available

Agent ARN: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/ecs_deployment_agent-XXXXX
Region: us-west-2
```

### 4. Update Agent (After Code Changes)

```bash
# Redeploy with updated code
agentcore launch

# Or use the helper script
../redeploy_agent.sh
```

## 🔑 IAM Permissions Required

The agent's execution role needs these permissions:

### ECR Permissions
- `ecr:CreateRepository`
- `ecr:DescribeRepositories`
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecr:BatchGetImage`

### Amazon ECS Permissions
- `ecs:CreateExpressGatewayService`
- `ecs:DescribeExpressGatewayService`
- `ecs:UpdateExpressGatewayService`
- `ecs:DeleteExpressGatewayService`
- `ecs:ListClusters`
- `ecs:ListServices`
- `ecs:DescribeServices`
- `ecs:DescribeServiceDeployments`
- `ecs:UpdateService`

### AWS CloudFormation Permissions
- `cloudformation:CreateStack`
- `cloudformation:UpdateStack`
- `cloudformation:DeleteStack`
- `cloudformation:DescribeStacks`
- `cloudformation:DescribeStackEvents`

### IAM PassRole
- `iam:PassRole` for:
  - `ecsTaskExecutionRole`
  - `ecsInfrastructureRoleForExpressServices`

## 📝 Agent Code Structure

```python
# agent.py
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Define tools with @tool decorator
@tool
def create_ecr_repository(app_name: str, region: str = "us-west-2") -> dict:
    """Create ECR repository for container images"""
    # Implementation...

# Initialize agent with tools
agent = Agent(
    name="Amazon ECS Deployment Agent",
    description="Helps deploy applications to AWS Amazon ECS Express Mode",
    tools=[create_ecr_repository, deploy_ecs_express_service, ...]
)

# Create AgentCore app
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    """Process user requests"""
    user_message = payload.get("prompt", "")
    result = agent(user_message)
    return {"message": result.message}
```

## 🧪 Testing

Test the agent using the provided scripts:

```bash
# Single-task deployment
cd ..
python3 test_conversation.py

# Multi-task deployment (3 tasks)
python3 test_multi_task.py
```

## 🔍 Troubleshooting

### Agent Not Found
```bash
# Check agent status
agentcore status

# List all agents
agentcore list
```

### Permission Errors
Ensure the agent's execution role has all required permissions. Check:
```bash
aws iam get-role --role-name AmazonBedrockAgentCoreSDKRuntime-REGION-XXXXX
```

### Deployment Failures
Check CloudWatch Logs for the agent:
```bash
aws logs tail /aws/lambda/bedrock-agentcore-XXXXX --follow
```

## 📚 Learn More

- **AgentCore Documentation**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
- **Strands Framework**: https://github.com/awslabs/strands
- **Amazon ECS Express Mode**: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-gateway-service.html

## 🔄 Updating the Agent

When you modify `agent.py`:

1. Save your changes
2. Run `agentcore launch` to redeploy
3. Wait ~30 seconds for the update to propagate
4. Test with `python3 ../test_conversation.py`

## 🗑️ Cleanup

To remove the agent:

```bash
agentcore delete
```

This will delete:
- The agent runtime
- Associated AWS Lambda functions
- IAM roles (if not used by other agents)

---

**Note:** The agent runs in AWS-managed infrastructure. You don't need to manage servers, scaling, or availability.
