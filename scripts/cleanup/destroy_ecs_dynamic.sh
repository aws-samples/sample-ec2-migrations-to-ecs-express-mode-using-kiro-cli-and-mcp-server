#!/bin/bash
set -e

# Default region, can be overridden
REGION="${AWS_REGION:-eu-north-1}"

# Allow region override via command line
if [ -n "$1" ]; then
    REGION="$1"
fi

echo "🗑️  Starting Complete ECS Infrastructure Cleanup"
echo "=============================================="
echo "🌍 Region: $REGION"
echo ""

# Step 1: Delete CloudFormation stacks first (they manage most resources)
echo "🚫 Step 1: Deleting CloudFormation stacks..."
STACKS=$(aws cloudformation list-stacks --region $REGION --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[?contains(StackName, `blog`) || contains(StackName, `secure`) || contains(StackName, `alb-stack`) || contains(StackName, `ecs-express`)].StackName' --output text)

if [ -n "$STACKS" ]; then
    for stack in $STACKS; do
        echo "🗑️  Deleting stack: $stack"
        aws cloudformation delete-stack --stack-name $stack --region $REGION
    done
    
    echo "⏳ Waiting for stacks to delete..."
    for stack in $STACKS; do
        echo "  Waiting for $stack..."
        aws cloudformation wait stack-delete-complete --stack-name $stack --region $REGION 2>/dev/null || echo "  Stack $stack deletion completed or failed"
    done
    echo "✅ CloudFormation stacks deleted"
else
    echo "ℹ️  No relevant CloudFormation stacks found"
fi

# Step 2: Clean up any remaining ECS services
echo ""
echo "🚫 Step 2: Cleaning up remaining ECS services..."
CLUSTERS=$(aws ecs list-clusters --region $REGION --query 'clusterArns[*]' --output text)

if [ -n "$CLUSTERS" ]; then
    for cluster_arn in $CLUSTERS; do
        cluster_name=$(basename $cluster_arn)
        
        if [[ $cluster_name == *"blog"* ]] || [[ $cluster_name == *"secure"* ]]; then
            echo "📋 Processing cluster: $cluster_name"
            
            services=$(aws ecs list-services --cluster $cluster_name --region $REGION --query 'serviceArns[*]' --output text 2>/dev/null || echo "")
            
            if [ -n "$services" ]; then
                for service_arn in $services; do
                    service_name=$(basename $service_arn)
                    echo "  ⏳ Scaling down service: $service_name"
                    aws ecs update-service --cluster $cluster_name --service $service_name --desired-count 0 --region $REGION >/dev/null
                    
                    echo "  🗑️  Deleting service: $service_name"
                    aws ecs delete-service --cluster $cluster_name --service $service_name --region $REGION >/dev/null
                done
            fi
            
            echo "  🗑️  Deleting cluster: $cluster_name"
            aws ecs delete-cluster --cluster $cluster_name --region $REGION >/dev/null
        fi
    done
    echo "✅ ECS services and clusters cleaned up"
else
    echo "ℹ️  No ECS clusters found"
fi

# Step 3: Delete task definitions
echo ""
echo "🚫 Step 3: Deregistering task definitions..."
TASK_FAMILIES=$(aws ecs list-task-definition-families --region $REGION --status ACTIVE --query 'families[?contains(@, `blog`) || contains(@, `secure`)]' --output text)

if [ -n "$TASK_FAMILIES" ]; then
    for family in $TASK_FAMILIES; do
        echo "📋 Processing task family: $family"
        
        # Get all revisions for this family
        REVISIONS=$(aws ecs list-task-definitions --family-prefix $family --region $REGION --query 'taskDefinitionArns[*]' --output text)
        
        for revision_arn in $REVISIONS; do
            echo "  🗑️  Deregistering: $(basename $revision_arn)"
            aws ecs deregister-task-definition --task-definition $revision_arn --region $REGION >/dev/null
        done
    done
    echo "✅ Task definitions deregistered"
else
    echo "ℹ️  No relevant task definitions found"
fi

# Step 4: Delete ECR repositories
echo ""
echo "🚫 Step 4: Deleting ECR repositories..."
ECR_REPOS=$(aws ecr describe-repositories --region $REGION --query 'repositories[?contains(repositoryName, `blog`) || contains(repositoryName, `secure`)].repositoryName' --output text 2>/dev/null || echo "")

if [ -n "$ECR_REPOS" ]; then
    for repo in $ECR_REPOS; do
        echo "🗑️  Deleting ECR repository: $repo"
        aws ecr delete-repository --repository-name $repo --force --region $REGION >/dev/null
    done
    echo "✅ ECR repositories deleted"
else
    echo "ℹ️  No blog/secure ECR repositories found"
fi

# Step 5: Delete CloudWatch Log Groups
echo ""
echo "🚫 Step 5: Deleting CloudWatch Log Groups..."
LOG_GROUPS=$(aws logs describe-log-groups --region $REGION --query 'logGroups[?contains(logGroupName, `/ecs/`) && (contains(logGroupName, `blog`) || contains(logGroupName, `secure`))].logGroupName' --output text 2>/dev/null || echo "")

if [ -n "$LOG_GROUPS" ]; then
    for log_group in $LOG_GROUPS; do
        echo "🗑️  Deleting log group: $log_group"
        aws logs delete-log-group --log-group-name $log_group --region $REGION >/dev/null
    done
    echo "✅ CloudWatch log groups deleted"
else
    echo "ℹ️  No relevant log groups found"
fi

# Step 6: Clean up any remaining load balancers and target groups
echo ""
echo "🚫 Step 6: Cleaning up load balancers..."
ALB_ARNS=$(aws elbv2 describe-load-balancers --region $REGION --query 'LoadBalancers[?contains(LoadBalancerName, `blog`) || contains(LoadBalancerName, `secure`)].LoadBalancerArn' --output text 2>/dev/null || echo "")

if [ -n "$ALB_ARNS" ]; then
    for alb_arn in $ALB_ARNS; do
        ALB_NAME=$(aws elbv2 describe-load-balancers --load-balancer-arns $alb_arn --query 'LoadBalancers[0].LoadBalancerName' --output text)
        echo "🗑️  Deleting ALB: $ALB_NAME"
        aws elbv2 delete-load-balancer --load-balancer-arn $alb_arn --region $REGION >/dev/null
    done
    echo "✅ Load balancers deleted"
else
    echo "ℹ️  No relevant load balancers found"
fi

# Step 7: Clean up target groups
echo ""
echo "🚫 Step 7: Cleaning up target groups..."
TG_ARNS=$(aws elbv2 describe-target-groups --region $REGION --query 'TargetGroups[?contains(TargetGroupName, `blog`) || contains(TargetGroupName, `secure`)].TargetGroupArn' --output text 2>/dev/null || echo "")

if [ -n "$TG_ARNS" ]; then
    for tg_arn in $TG_ARNS; do
        TG_NAME=$(aws elbv2 describe-target-groups --target-group-arns $tg_arn --query 'TargetGroups[0].TargetGroupName' --output text)
        echo "🗑️  Deleting target group: $TG_NAME"
        aws elbv2 delete-target-group --target-group-arn $tg_arn --region $REGION >/dev/null 2>&1 || echo "  Target group may already be deleted"
    done
    echo "✅ Target groups deleted"
else
    echo "ℹ️  No relevant target groups found"
fi

# Step 8: Clean up security groups (except default)
echo ""
echo "🚫 Step 8: Cleaning up security groups..."
SG_IDS=$(aws ec2 describe-security-groups --region $REGION --query 'SecurityGroups[?contains(GroupName, `blog`) || contains(GroupName, `secure`) || contains(GroupName, `ALB`) || contains(GroupName, `ECS`)].GroupId' --output text 2>/dev/null || echo "")

if [ -n "$SG_IDS" ]; then
    for sg_id in $SG_IDS; do
        SG_NAME=$(aws ec2 describe-security-groups --group-ids $sg_id --query 'SecurityGroups[0].GroupName' --output text)
        if [[ $SG_NAME != "default" ]]; then
            echo "🗑️  Deleting security group: $SG_NAME ($sg_id)"
            aws ec2 delete-security-group --group-id $sg_id --region $REGION >/dev/null 2>&1 || echo "  Security group may be in use or already deleted"
        fi
    done
    echo "✅ Security groups cleaned up"
else
    echo "ℹ️  No relevant security groups found"
fi

echo ""
echo "🎉 Complete ECS Infrastructure cleanup completed!"
echo "🔄 You can now redeploy the ECS setup multiple times"
echo ""
