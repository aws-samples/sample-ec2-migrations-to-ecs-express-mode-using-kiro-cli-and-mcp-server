#!/bin/bash
# Update AgentCore execution role with all ECS deployment permissions

ROLE_NAME="AmazonBedrockAgentCoreSDKRuntime-us-west-2-7524651f9d"
POLICY_NAME="ECSDeploymentAgentPolicy"
ACCOUNT_ID="861276113985"

cat > /tmp/ecs-agent-policy-complete.json << EOF
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
        "ecs:ListServiceDeployments",
        "ecs:DescribeServiceDeployments"
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
        "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
        "arn:aws:iam::${ACCOUNT_ID}:role/ecsInfrastructureRoleForExpressServices"
      ]
    }
  ]
}
EOF

echo "Updating IAM policy for role: $ROLE_NAME"
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document file:///tmp/ecs-agent-policy-complete.json

if [ $? -eq 0 ]; then
  echo "✓ Policy updated successfully"
else
  echo "✗ Failed to update policy"
  exit 1
fi

echo ""
echo "Current policies attached to role:"
aws iam list-role-policies --role-name "$ROLE_NAME"
