# AgentCore Agent Runtime - IAM Permissions

## Required IAM Roles

### 1. AgentCore Execution Role
**Role:** `AmazonBedrockAgentCoreSDKRuntime-us-west-2-*`

This role is automatically created by `agentcore configure` and needs additional permissions for Amazon ECS deployment.

**Required Policy:** `ECSDeploymentAgentPolicy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRPermissions",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:DescribeRepositories",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSExpressPermissions",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateExpressGatewayService",
        "ecs:DescribeExpressGatewayService",
        "ecs:UpdateExpressGatewayService",
        "ecs:DeleteExpressGatewayService",
        "ecs:CreateCluster",
        "ecs:RegisterTaskDefinition",
        "ecs:DeregisterTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSListPermissions",
      "Effect": "Allow",
      "Action": [
        "ecs:ListClusters",
        "ecs:ListServices",
        "ecs:DescribeServices",
        "ecs:DescribeClusters",
        "ecs:ListTasks",
        "ecs:DescribeTasks",
        "ecs:DescribeServiceRevisions",
        "ecs:ListServiceDeployments"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationPermissions",
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ELBPermissions",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeRules"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassRolePermissions",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
        "arn:aws:iam::ACCOUNT_ID:role/ecsInfrastructureRoleForExpressServices"
      ]
    }
  ]
}
```

### 2. Amazon ECS Task Execution Role
**Role:** `ecsTaskExecutionRole`

Allows Amazon ECS tasks to pull images and write logs.

**Managed Policy:** `arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy`

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

### 3. Amazon ECS Infrastructure Role
**Role:** `ecsInfrastructureRoleForExpressServices`

Allows Amazon ECS Express Mode to provision ALB, target groups, security groups.

**Managed Policy:** `arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices`

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## Setup Instructions

### 1. Update AgentCore Execution Role
```bash
cd agentcore-agent-runtime
./update-permissions.sh
```

### 2. Create Amazon ECS Roles (if not exists)
```bash
# Task Execution Role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Infrastructure Role
aws iam create-role \
  --role-name ecsInfrastructureRoleForExpressServices \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name ecsInfrastructureRoleForExpressServices \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices
```

## Verification

```bash
# Check AgentCore role policies
aws iam list-role-policies --role-name AmazonBedrockAgentCoreSDKRuntime-us-west-2-*

# Check Amazon ECS roles exist
aws iam get-role --role-name ecsTaskExecutionRole
aws iam get-role --role-name ecsInfrastructureRoleForExpressServices
```
