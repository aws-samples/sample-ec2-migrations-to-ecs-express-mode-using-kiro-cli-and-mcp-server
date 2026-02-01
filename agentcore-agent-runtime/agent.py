#!/usr/bin/env python3
"""
ECS Deployment Agent for AgentCore Runtime
Uses Strands Agent with ECS deployment tools
"""

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import boto3
import subprocess
import json

# Initialize app
app = BedrockAgentCoreApp()

# ECS deployment tools
@tool
def create_ecr_repository(app_name: str, region: str = "us-west-2") -> dict:
    """Create ECR repository for container images"""
    ecr = boto3.client('ecr', region_name=region)
    try:
        response = ecr.create_repository(repositoryName=app_name)
        return {
            "status": "success",
            "repository_uri": response['repository']['repositoryUri'],
            "repository_arn": response['repository']['repositoryArn']
        }
    except ecr.exceptions.RepositoryAlreadyExistsException:
        response = ecr.describe_repositories(repositoryNames=[app_name])
        return {
            "status": "exists",
            "repository_uri": response['repositories'][0]['repositoryUri']
        }

@tool
def deploy_ecs_express_service(
    service_name: str,
    image_uri: str,
    cpu: str = "256",
    memory: str = "512",
    port: int = 3000,
    region: str = "us-west-2",
    environment_variables: dict = None,
    desired_count: int = 1
) -> dict:
    """Deploy application to ECS Express Mode using CloudFormation with auto-scaling"""
    cfn = boto3.client('cloudformation', region_name=region)
    
    execution_role = "arn:aws:iam::<AWS_ACCOUNT_ID>:role/ecsTaskExecutionRole"
    task_role = "arn:aws:iam::<AWS_ACCOUNT_ID>:role/ecsTaskExecutionRole"
    infrastructure_role = "arn:aws:iam::<AWS_ACCOUNT_ID>:role/ecsInfrastructureRoleForExpressServices"
    stack_name = f"ecs-express-{service_name}"
    
    # Build container config
    container_config = {
        "Image": image_uri,
        "ContainerPort": port
    }
    
    # Add environment variables if provided
    if environment_variables:
        container_config["Environment"] = [
            {"Name": k, "Value": str(v)} for k, v in environment_variables.items()
        ]
    
    # Build service properties
    service_properties = {
        "ServiceName": service_name,
        "ExecutionRoleArn": execution_role,
        "TaskRoleArn": task_role,
        "InfrastructureRoleArn": infrastructure_role,
        "Cpu": cpu,
        "Memory": memory,
        "PrimaryContainer": container_config
    }
    
    # Add scaling configuration if multiple tasks requested
    if desired_count > 1:
        service_properties["ScalingTarget"] = {
            "MinTaskCount": desired_count,
            "MaxTaskCount": 50,
            "AutoScalingMetric": "AVERAGE_CPU",
            "AutoScalingTargetValue": 70
        }
    
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "ExpressService": {
                "Type": "AWS::ECS::ExpressGatewayService",
                "Properties": service_properties
            }
        },
        "Outputs": {
            "ServiceArn": {
                "Value": {"Ref": "ExpressService"}
            },
            "Endpoint": {
                "Value": {"Fn::GetAtt": ["ExpressService", "Endpoint"]}
            }
        }
    }
    
    try:
        import json
        response = cfn.create_stack(
            StackName=stack_name,
            TemplateBody=json.dumps(template),
            Capabilities=['CAPABILITY_IAM']
        )
        
        return {
            "status": "success",
            "stack_name": stack_name,
            "stack_id": response['StackId'],
            "desired_count": desired_count,
            "message": f"CloudFormation stack {stack_name} creation initiated with {desired_count} task(s)."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@tool
def list_ecs_services(region: str = "us-west-2") -> dict:
    """List all ECS services across all clusters"""
    ecs = boto3.client('ecs', region_name=region)
    
    try:
        # List all clusters
        clusters_response = ecs.list_clusters()
        all_services = []
        
        for cluster_arn in clusters_response.get('clusterArns', []):
            cluster_name = cluster_arn.split('/')[-1]
            
            # List services in this cluster
            services_response = ecs.list_services(cluster=cluster_arn)
            
            for service_arn in services_response.get('serviceArns', []):
                service_name = service_arn.split('/')[-1]
                all_services.append({
                    "cluster": cluster_name,
                    "service_name": service_name,
                    "service_arn": service_arn
                })
        
        return {"status": "success", "services": all_services, "count": len(all_services)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@tool
def check_service_status(service_arn: str = None, stack_name: str = None, region: str = "us-west-2") -> dict:
    """Check ECS service status via CloudFormation stack"""
    cfn = boto3.client('cloudformation', region_name=region)
    
    try:
        # If stack_name not provided, extract from service_arn
        if not stack_name and service_arn:
            service_name = service_arn.split('/')[-1]
            stack_name = f"ecs-express-{service_name}"
        
        if not stack_name:
            return {"status": "error", "message": "Either service_arn or stack_name required"}
        
        # Get stack status
        response = cfn.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]
        
        result = {
            "status": stack['StackStatus'],
            "stack_name": stack_name
        }
        
        # Get outputs if stack is complete
        if stack['StackStatus'] == 'CREATE_COMPLETE':
            outputs = {o['OutputKey']: o['OutputValue'] for o in stack.get('Outputs', [])}
            result['service_arn'] = outputs.get('ServiceArn', 'N/A')
            result['endpoint'] = outputs.get('Endpoint', 'N/A')
            result['alb_url'] = f"https://{outputs.get('Endpoint', 'N/A')}" if outputs.get('Endpoint') else 'N/A'
        
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@tool
def scale_service(service_name: str, desired_count: int, region: str = "us-west-2") -> dict:
    """Scale ECS service to desired task count"""
    ecs = boto3.client('ecs', region_name=region)
    
    try:
        response = ecs.update_service(
            cluster='default',
            service=service_name,
            desiredCount=desired_count
        )
        
        return {
            "status": "success",
            "service_name": service_name,
            "desired_count": desired_count,
            "message": f"Service {service_name} scaled to {desired_count} tasks"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@tool
def delete_ecs_service(service_name: str = None, stack_name: str = None, region: str = "us-west-2") -> dict:
    """
    Delete ECS Express Mode service by deleting its CloudFormation stack
    
    Args:
        service_name: Name of the ECS service (will construct stack name as ecs-express-{service_name})
        stack_name: Direct CloudFormation stack name (alternative to service_name)
        region: AWS region
        
    Returns:
        Dictionary with deletion status
    """
    cfn = boto3.client('cloudformation', region_name=region)
    
    try:
        # Determine stack name
        if not stack_name and service_name:
            stack_name = f"ecs-express-{service_name}"
        
        if not stack_name:
            return {
                "status": "error",
                "message": "Either service_name or stack_name is required"
            }
        
        # Check if stack exists
        try:
            cfn.describe_stacks(StackName=stack_name)
        except cfn.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                return {
                    "status": "not_found",
                    "stack_name": stack_name,
                    "message": f"Stack {stack_name} does not exist"
                }
            raise
        
        # Delete the stack
        cfn.delete_stack(StackName=stack_name)
        
        return {
            "status": "success",
            "stack_name": stack_name,
            "service_name": service_name,
            "message": f"Stack {stack_name} deletion initiated. This will delete the ECS service and all associated resources (ALB, target groups, security groups)."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting service: {str(e)}"
        }

# Initialize Strands agent with tools
agent = Agent(
    name="ECS Deployment Agent",
    description="Helps deploy applications to AWS ECS Express Mode",
    tools=[create_ecr_repository, deploy_ecs_express_service, list_ecs_services, check_service_status, scale_service, delete_ecs_service]
)

@app.entrypoint
def invoke(payload):
    """Process user requests for ECS deployment"""
    user_message = payload.get("prompt", "")
    
    if not user_message:
        return {
            "error": "No prompt provided",
            "message": "Please provide a 'prompt' key in your request"
        }
    
    # Run agent
    result = agent(user_message)
    
    return {
        "message": result.message,
        "tool_calls": len(result.tool_calls) if hasattr(result, 'tool_calls') else 0
    }

if __name__ == "__main__":
    app.run()
