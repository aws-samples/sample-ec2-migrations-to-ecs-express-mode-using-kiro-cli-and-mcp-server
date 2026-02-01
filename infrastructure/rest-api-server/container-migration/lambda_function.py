import json
import boto3
import subprocess
import os
import base64
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lightweight MCP server as Lambda function
    Handles containerization operations via API Gateway
    """
    
    try:
        # Parse the request
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '/')
        body = event.get('body', '{}')
        
        if body:
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(body).decode('utf-8')
            request_data = json.loads(body)
        else:
            request_data = {}
        
        # Route based on path
        if path == '/tools/optimize_dockerfile':
            return handle_optimize_dockerfile(request_data)
        elif path == '/tools/build_and_push_container':
            return handle_build_and_push_container(request_data)
        elif path == '/tools/validate_container_security':
            return handle_validate_container_security(request_data)
        elif path == '/tools/validate_ecs_prerequisites':
            return handle_validate_ecs_prerequisites(request_data)
        elif path == '/tools/deploy_ecs_express_service':
            return handle_deploy_ecs_express_service(request_data)
        elif path == '/tools/check_ecs_service_status':
            return handle_check_ecs_service_status(request_data)
        elif path == '/resources/dockerfile-template':
            return handle_dockerfile_template()
        elif path == '/resources/build-script':
            return handle_build_script()
        elif path == '/resources/iam-roles-template':
            return handle_iam_roles_template()
        elif path == '/resources/deployment-guide':
            return handle_deployment_guide()
        else:
            return create_response(404, {'error': 'Not found'})
            
    except Exception as e:
        return create_response(500, {'error': str(e)})

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }

def handle_optimize_dockerfile(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate optimized Dockerfile"""
    
    base_image = request_data.get('base_image', 'node:18-alpine')
    port = request_data.get('port', 3000)
    
    dockerfile_content = f"""FROM {base_image}

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY public/ ./public/

# Create uploads directory
RUN mkdir -p uploads

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Change ownership of the app directory
RUN chown -R nodejs:nodejs /app
USER nodejs

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD node -e "require('http').get('http://localhost:{port}/health', (res) => {{ process.exit(res.statusCode === 200 ? 0 : 1) }})"

# Start application
CMD ["npm", "start"]"""

    return create_response(200, {
        'status': 'success',
        'dockerfile': dockerfile_content,
        'message': 'Optimized Dockerfile generated with security best practices'
    })

def handle_build_and_push_container(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build and push container to ECR using CodeBuild"""
    
    app_name = request_data.get('app_name', 'secure-blog')
    app_path = request_data.get('app_path', '/tmp/app')
    tag = request_data.get('tag', 'v1.0.0')
    region = request_data.get('region')
    
    if not region:
        return create_response(400, {'error': 'region is required'})
    
    try:
        # Get AWS account ID
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
        
        # Create ECR repository
        ecr = boto3.client('ecr', region_name=region)
        try:
            ecr.create_repository(repositoryName=app_name)
            repository_created = True
        except ecr.exceptions.RepositoryAlreadyExistsException:
            repository_created = False
        
        # Generate ECR URI
        ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{app_name}:{tag}"
        
        # Check if image already exists
        try:
            ecr.describe_images(repositoryName=app_name, imageIds=[{'imageTag': tag}])
            image_exists = True
        except ecr.exceptions.ImageNotFoundException:
            image_exists = False
        
        if image_exists:
            return create_response(200, {
                'status': 'success',
                'image_uri': ecr_uri,
                'repository_created': repository_created,
                'message': f'Image already exists in ECR: {ecr_uri}',
                'build_required': False
            })
        
        # Since we can't execute Docker in Lambda, return instructions for client-side build
        return create_response(200, {
            'status': 'success',
            'image_uri': ecr_uri,
            'repository_created': repository_created,
            'message': f'ECR repository ready. Build and push required.',
            'build_required': True,
            'build_instructions': [
                f'cd {app_path}',
                f'aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com',
                f'docker build --platform linux/amd64 -t {app_name}:{tag} .',
                f'docker tag {app_name}:{tag} {ecr_uri}',
                f'docker push {ecr_uri}'
            ]
        })
        
    except Exception as e:
        return create_response(500, {'error': f'ECR setup failed: {str(e)}'})

def handle_validate_container_security(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate container security"""
    
    dockerfile_content = request_data.get('dockerfile_content', '')
    
    issues = []
    recommendations = []
    
    # Security checks
    if "USER root" in dockerfile_content or "USER 0" in dockerfile_content:
        issues.append("❌ Running as root user")
    elif "USER " not in dockerfile_content:
        issues.append("⚠️ No explicit user specified (may run as root)")
    else:
        recommendations.append("✅ Non-root user specified")
    
    if "HEALTHCHECK" not in dockerfile_content:
        issues.append("⚠️ No health check defined")
    else:
        recommendations.append("✅ Health check included")
    
    if "--only=production" in dockerfile_content or "--omit=dev" in dockerfile_content:
        recommendations.append("✅ Production dependencies only")
    else:
        issues.append("⚠️ Consider using production-only dependencies")
    
    if "COPY . ." in dockerfile_content:
        issues.append("⚠️ Copying entire directory (consider .dockerignore)")
    else:
        recommendations.append("✅ Selective file copying")
    
    return create_response(200, {
        'status': 'success',
        'recommendations': recommendations,
        'issues': issues,
        'security_score': len(recommendations) / (len(recommendations) + len(issues)) * 100 if (recommendations or issues) else 100
    })

def handle_dockerfile_template() -> Dict[str, Any]:
    """Return Dockerfile template"""
    
    template = """FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY public/ ./public/

# Create uploads directory
RUN mkdir -p uploads

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Change ownership of the app directory
RUN chown -R nodejs:nodejs /app
USER nodejs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD node -e "require('http').get('http://localhost:3000/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

# Start application
CMD ["npm", "start"]"""

    return create_response(200, {
        'status': 'success',
        'template': template,
        'description': 'Production-ready Dockerfile template with security best practices'
    })

def handle_build_script() -> Dict[str, Any]:
    """Return build script"""
    
    script = """#!/bin/bash
set -e

# Configuration
APP_NAME="${1:-secure-blog}"
TAG="${2:-v1.0.0}"
REGION="${3:-us-west-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Starting container build and push process..."
echo "App: $APP_NAME, Tag: $TAG, Region: $REGION, Account: $ACCOUNT_ID"

# Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository..."
aws ecr create-repository --repository-name $APP_NAME --region $REGION 2>/dev/null || echo "Repository already exists"

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build image for linux/amd64 platform (required for ECS Fargate)
echo "🔨 Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t $APP_NAME:$TAG .

# Tag for ECR
echo "🏷️  Tagging image for ECR..."
docker tag $APP_NAME:$TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME:$TAG

# Push to ECR
echo "⬆️  Pushing to ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME:$TAG

echo "✅ Container successfully pushed to ECR!"
echo "Image URI: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME:$TAG"
"""

    return create_response(200, {
        'status': 'success',
        'script': script,
        'description': 'Automated build and push script for ECR'
    })

def handle_validate_ecs_prerequisites(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate ECS Express Mode prerequisites"""
    
    image_uri = request_data.get('image_uri')
    region = request_data.get('region')
    
    if not image_uri:
        return create_response(400, {'error': 'image_uri is required'})
    
    if not region:
        return create_response(400, {'error': 'region is required'})
    
    validation_results = []
    
    try:
        # Check if image exists in ECR
        ecr = boto3.client('ecr', region_name=region)
        repo_name = image_uri.split('/')[-1].split(':')[0]
        
        try:
            ecr.describe_images(repositoryName=repo_name)
            validation_results.append("✅ Container image exists in ECR")
        except ecr.exceptions.ImageNotFoundException:
            validation_results.append("❌ Container image not found in ECR")
        except ecr.exceptions.RepositoryNotFoundException:
            validation_results.append("❌ ECR repository not found")
        
        # Check IAM roles
        iam = boto3.client('iam')
        
        # Check/Create ecsTaskExecutionRole
        try:
            iam.get_role(RoleName='ecsTaskExecutionRole')
            validation_results.append("✅ ecsTaskExecutionRole exists")
        except iam.exceptions.NoSuchEntityException:
            try:
                # Create ecsTaskExecutionRole
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                }
                
                iam.create_role(
                    RoleName='ecsTaskExecutionRole',
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description='ECS Task Execution Role for pulling images and writing logs'
                )
                
                # Attach managed policy
                iam.attach_role_policy(
                    RoleName='ecsTaskExecutionRole',
                    PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'
                )
                
                validation_results.append("✅ ecsTaskExecutionRole created")
            except Exception as e:
                validation_results.append(f"❌ Failed to create ecsTaskExecutionRole: {str(e)}")
        
        # Check/Create ecsInfrastructureRoleForExpressServices
        try:
            iam.get_role(RoleName='ecsInfrastructureRoleForExpressServices')
            validation_results.append("✅ ecsInfrastructureRoleForExpressServices exists")
        except iam.exceptions.NoSuchEntityException:
            try:
                # Create ecsInfrastructureRoleForExpressServices
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "ecs.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                }
                
                iam.create_role(
                    RoleName='ecsInfrastructureRoleForExpressServices',
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description='ECS Infrastructure Role for Express Gateway Services'
                )
                
                # Attach managed policy
                iam.attach_role_policy(
                    RoleName='ecsInfrastructureRoleForExpressServices',
                    PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices'
                )
                
                validation_results.append("✅ ecsInfrastructureRoleForExpressServices created")
            except Exception as e:
                validation_results.append(f"❌ Failed to create ecsInfrastructureRoleForExpressServices: {str(e)}")
        
        # Check BlogAppECSTaskRole
        try:
            iam.get_role(RoleName='BlogAppECSTaskRole')
            validation_results.append("✅ BlogAppECSTaskRole exists")
        except iam.exceptions.NoSuchEntityException:
            validation_results.append("❌ BlogAppECSTaskRole not found - required for task permissions")
        
        all_valid = all("✅" in result for result in validation_results)
        
        return create_response(200, {
            'status': 'success' if all_valid else 'validation_failed',
            'all_valid': all_valid,
            'results': validation_results,
            'message': 'All prerequisites met' if all_valid else 'Some prerequisites missing'
        })
        
    except Exception as e:
        return create_response(500, {'error': f'Validation failed: {str(e)}'})

def handle_deploy_ecs_express_service(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy ECS Express Gateway Service"""
    
    service_name = request_data.get('service_name')
    image_uri = request_data.get('image_uri')
    env_vars = request_data.get('environment_vars', {})
    cpu = request_data.get('cpu', '256')
    memory = request_data.get('memory', '512')
    port = request_data.get('port', 3000)
    region = request_data.get('region', 'us-west-2')
    vpc_id = request_data.get('vpc_id')
    subnet_ids = request_data.get('subnet_ids')
    
    if not service_name or not image_uri:
        return create_response(400, {'error': 'service_name and image_uri are required'})
    
    try:
        # Get AWS account ID
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
        
        # Auto-discover VPC and subnets if not provided
        if not vpc_id or not subnet_ids:
            ec2 = boto3.client('ec2', region_name=region)
            
            if not vpc_id:
                # Get default VPC
                vpcs = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
                if vpcs['Vpcs']:
                    vpc_id = vpcs['Vpcs'][0]['VpcId']
                else:
                    # Get first available VPC
                    vpcs = ec2.describe_vpcs()
                    if vpcs['Vpcs']:
                        vpc_id = vpcs['Vpcs'][0]['VpcId']
                    else:
                        return create_response(400, {'error': 'No VPC found in region'})
            
            if not subnet_ids:
                # Get public subnets in the VPC
                subnets = ec2.describe_subnets(
                    Filters=[
                        {'Name': 'vpc-id', 'Values': [vpc_id]},
                        {'Name': 'map-public-ip-on-launch', 'Values': ['true']}
                    ]
                )
                if subnets['Subnets']:
                    subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
                else:
                    # Fallback to any subnets in the VPC
                    subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                    subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
                
                if not subnet_ids:
                    return create_response(400, {'error': f'No subnets found in VPC {vpc_id}'})
        
        # Create ECS client
        ecs = boto3.client('ecs', region_name=region)
        
        # Create Express Gateway Service directly using ECS Express API
        try:
            # Use CreateExpressGatewayService API
            response = ecs.create_express_gateway_service(
                serviceName=service_name,
                taskDefinition={
                    'cpu': cpu,
                    'memory': memory,
                    'containerDefinitions': [{
                        'name': 'Main',
                        'image': image_uri,
                        'portMappings': [{
                            'containerPort': port,
                            'protocol': 'tcp'
                        }],
                        'environment': [{'name': k, 'value': str(v)} for k, v in env_vars.items()],
                        'logConfiguration': {
                            'logDriver': 'awslogs',
                            'options': {
                                'awslogs-create-group': 'true',
                                'awslogs-group': f'/ecs/{service_name}',
                                'awslogs-region': region,
                                'awslogs-stream-prefix': 'ecs'
                            }
                        }
                    }]
                },
                desiredCount=1,
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'assignPublicIp': 'ENABLED',
                        'subnets': subnet_ids
                    }
                },
                loadBalancerConfiguration={
                    'containerName': 'Main',
                    'containerPort': port
                },
                tags=[
                    {'key': 'Project', 'value': 'ECS-Express-Migration'},
                    {'key': 'ManagedBy', 'value': 'MCP-Server'},
                    {'key': 'ServiceName', 'value': service_name},
                    {'key': 'Environment', 'value': 'Demo'}
                ]
            )
            
            service_arn = response.get('serviceArn')
            
            return create_response(200, {
                'status': 'success',
                'service_arn': service_arn,
                'service_name': service_name,
                'container_port': port,
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'message': f'Express Gateway service {service_name} created successfully',
                'details': [
                    'ECS Express Gateway service deployed',
                    f'Service ARN: {service_arn}',
                    f'Container running on port {port}',
                    'Load balancer automatically provisioned',
                    'Service ready for traffic'
                ]
            })
            
        except Exception as express_error:
            print(f"Express Gateway API failed: {express_error}")
            
            # Create CloudFormation stack with ALB for fallback
            cloudformation = boto3.client('cloudformation', region_name=region)
            
            template = {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Resources": {
                    "ECSCluster": {
                        "Type": "AWS::ECS::Cluster",
                        "Properties": {
                            "ClusterName": f"{service_name}-cluster"
                        }
                    },
                    "ALBSecurityGroup": {
                        "Type": "AWS::EC2::SecurityGroup",
                        "Properties": {
                            "GroupDescription": "ALB Security Group",
                            "VpcId": vpc_id,
                            "SecurityGroupIngress": [{
                                "IpProtocol": "tcp",
                                "FromPort": 80,
                                "ToPort": 80,
                                "CidrIp": "0.0.0.0/0"
                            }]
                        }
                    },
                    "ECSTaskSecurityGroup": {
                        "Type": "AWS::EC2::SecurityGroup",
                        "Properties": {
                            "GroupDescription": "ECS Task Security Group",
                            "VpcId": vpc_id,
                            "SecurityGroupIngress": [{
                                "IpProtocol": "tcp",
                                "FromPort": port,
                                "ToPort": port,
                                "SourceSecurityGroupId": {"Ref": "ALBSecurityGroup"}
                            }]
                        }
                    },
                    "ApplicationLoadBalancer": {
                        "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                        "Properties": {
                            "Name": f"{service_name}-alb",
                            "Scheme": "internet-facing",
                            "Type": "application",
                            "SecurityGroups": [{"Ref": "ALBSecurityGroup"}],
                            "Subnets": subnet_ids
                        }
                    },
                    "TargetGroup": {
                        "Type": "AWS::ElasticLoadBalancingV2::TargetGroup",
                        "Properties": {
                            "Name": f"{service_name}-tg",
                            "Port": port,
                            "Protocol": "HTTP",
                            "TargetType": "ip",
                            "VpcId": vpc_id,
                            "HealthCheckPath": "/",
                            "HealthCheckPort": str(port),
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckIntervalSeconds": 30,
                            "HealthCheckTimeoutSeconds": 5,
                            "HealthyThresholdCount": 2,
                            "UnhealthyThresholdCount": 3
                        }
                    },
                    "ALBListener": {
                        "Type": "AWS::ElasticLoadBalancingV2::Listener",
                        "Properties": {
                            "DefaultActions": [{
                                "Type": "forward",
                                "TargetGroupArn": {"Ref": "TargetGroup"}
                            }],
                            "LoadBalancerArn": {"Ref": "ApplicationLoadBalancer"},
                            "Port": 80,
                            "Protocol": "HTTP"
                        }
                    },
                    "TaskDefinition": {
                        "Type": "AWS::ECS::TaskDefinition",
                        "Properties": {
                            "Family": service_name,
                            "Cpu": cpu,
                            "Memory": memory,
                            "NetworkMode": "awsvpc",
                            "RequiresCompatibilities": ["FARGATE"],
                            "ExecutionRoleArn": f"arn:aws:iam::{account_id}:role/ecsTaskExecutionRole",
                            "TaskRoleArn": f"arn:aws:iam::{account_id}:role/BlogAppECSTaskRole",
                            "ContainerDefinitions": [{
                                "Name": "Main",
                                "Image": image_uri,
                                "PortMappings": [{
                                    "ContainerPort": port,
                                    "Protocol": "tcp"
                                }],
                                "Environment": [{"Name": k, "Value": str(v)} for k, v in env_vars.items()],
                                "LogConfiguration": {
                                    "LogDriver": "awslogs",
                                    "Options": {
                                        "awslogs-create-group": "true",
                                        "awslogs-group": f"/ecs/{service_name}",
                                        "awslogs-region": region,
                                        "awslogs-stream-prefix": "ecs"
                                    }
                                }
                            }]
                        }
                    },
                    "ECSService": {
                        "Type": "AWS::ECS::Service",
                        "DependsOn": ["ALBListener"],
                        "Properties": {
                            "Cluster": {"Ref": "ECSCluster"},
                            "ServiceName": service_name,
                            "TaskDefinition": {"Ref": "TaskDefinition"},
                            "DesiredCount": 1,
                            "LaunchType": "FARGATE",
                            "NetworkConfiguration": {
                                "AwsvpcConfiguration": {
                                    "AssignPublicIp": "ENABLED",
                                    "SecurityGroups": [{"Ref": "ECSTaskSecurityGroup"}],
                                    "Subnets": subnet_ids
                                }
                            },
                            "LoadBalancers": [{
                                "TargetGroupArn": {"Ref": "TargetGroup"},
                                "ContainerName": "Main",
                                "ContainerPort": port
                            }]
                        }
                    }
                },
                "Outputs": {
                    "LoadBalancerURL": {
                        "Value": {"Fn::GetAtt": ["ApplicationLoadBalancer", "DNSName"]},
                        "Description": "Load Balancer URL"
                    },
                    "TargetGroupArn": {
                        "Value": {"Ref": "TargetGroup"},
                        "Description": "Target Group ARN"
                    },
                    "ECSTaskSecurityGroupId": {
                        "Value": {"Ref": "ECSTaskSecurityGroup"},
                        "Description": "ECS Task Security Group ID"
                    },
                    "ServiceArn": {
                        "Value": {"Ref": "ECSService"},
                        "Description": "ECS Service ARN"
                    }
                }
            }
            
            # Deploy ALB stack
            stack_name = f"{service_name}-alb-stack"
            cloudformation.create_stack(
                StackName=stack_name,
                TemplateBody=json.dumps(template),
                Capabilities=['CAPABILITY_IAM']
            )
            
            # Return immediately with deployment status - don't wait for completion
            return create_response(200, {
                'status': 'success',
                'deployment_status': 'in_progress',
                'stack_name': stack_name,
                'service_name': service_name,
                'container_port': port,
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'message': f'ECS service deployment started for {service_name}',
                'details': [
                    f'CloudFormation stack {stack_name} creation initiated',
                    'ALB and target group will be created automatically',
                    'ECS service will be deployed once infrastructure is ready',
                    f'Container will run on port {port}',
                    'Check deployment status using check_ecs_service_status tool'
                ],
                'next_steps': [
                    'Wait 3-5 minutes for infrastructure provisioning',
                    f'Use check_ecs_service_status with stack_name: {stack_name}',
                    'Service will be available at ALB DNS once ready'
                ]
            })
            
            # The following code would run if we waited, but we return early above
            # Get stack outputs (this won't execute due to early return)
            stack_info = cloudformation.describe_stacks(StackName=stack_name)
            outputs = {output['OutputKey']: output['OutputValue'] 
                      for output in stack_info['Stacks'][0].get('Outputs', [])}
            
            target_group_arn = outputs.get('TargetGroupArn')
            alb_dns = outputs.get('LoadBalancerURL')
            
            # Create task definition
            task_def = {
                'family': service_name,
                'cpu': cpu,
                'memory': memory,
                'networkMode': 'awsvpc',
                'requiresCompatibilities': ['FARGATE'],
                'executionRoleArn': f'arn:aws:iam::{account_id}:role/ecsTaskExecutionRole',
                'containerDefinitions': [{
                    'name': 'Main',
                    'image': image_uri,
                    'portMappings': [{
                        'containerPort': port,
                        'protocol': 'tcp'
                    }],
                    'environment': [{'name': k, 'value': str(v)} for k, v in env_vars.items()],
                    'logConfiguration': {
                        'logDriver': 'awslogs',
                        'options': {
                            'awslogs-create-group': 'true',
                            'awslogs-group': f'/ecs/{service_name}',
                            'awslogs-region': region,
                            'awslogs-stream-prefix': 'ecs'
                        }
                    }
                }]
            }
            
            # Register task definition
            task_response = ecs.register_task_definition(**task_def)
            task_arn = task_response['taskDefinition']['taskDefinitionArn']
            
            # Create service with load balancer
            service_response = ecs.create_service(
                cluster=f"{service_name}-cluster",
                serviceName=service_name,
                taskDefinition=task_arn,
                desiredCount=1,
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'assignPublicIp': 'ENABLED',
                        'subnets': [
                            'subnet-0c95da602730c1306',
                            'subnet-0acee65274920dede', 
                            'subnet-0e69cd15028078513',
                            'subnet-09f869cbb95232397'
                        ]
                    }
                },
                loadBalancers=[{
                    'targetGroupArn': target_group_arn,
                    'containerName': 'Main',
                    'containerPort': port
                }] if target_group_arn else []
            )
            
            service_arn = service_response['service']['serviceArn']
            
            return create_response(200, {
                'status': 'success',
                'service_arn': service_arn,
                'task_definition_arn': task_arn,
                'service_name': service_name,
                'cluster_name': f"{service_name}-cluster",
                'container_port': port,
                'load_balancer_url': f"http://{alb_dns}" if alb_dns else None,
                'message': f'ECS service {service_name} created with load balancer',
                'details': [
                    'ECS service deployed with Fargate',
                    f'Service ARN: {service_arn}',
                    f'Task definition: {task_arn}',
                    f'Container running on port {port}',
                    f'Load balancer URL: http://{alb_dns}' if alb_dns else 'Load balancer setup in progress'
                ]
            })
        
    except Exception as e:
        return create_response(500, {'error': f'Failed to deploy service: {str(e)}'})

def handle_check_ecs_service_status(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check ECS service status or CloudFormation stack status"""
    
    service_arn = request_data.get('service_arn')
    stack_name = request_data.get('stack_name')
    region = request_data.get('region')
    
    if not stack_name and not service_arn:
        return create_response(400, {'error': 'Either service_arn or stack_name is required'})
    
    if not region:
        return create_response(400, {'error': 'region is required'})
    
    try:
        # If stack_name is provided, check CloudFormation stack status first
        if stack_name:
            cf = boto3.client('cloudformation', region_name=region)
            
            try:
                stack_response = cf.describe_stacks(StackName=stack_name)
                stack = stack_response['Stacks'][0]
                stack_status = stack['StackStatus']
                
                if stack_status == 'CREATE_COMPLETE':
                    # Stack is ready, get outputs and check ECS service
                    outputs = {output['OutputKey']: output['OutputValue'] 
                              for output in stack.get('Outputs', [])}
                    
                    service_arn = outputs.get('ServiceArn')
                    load_balancer_url = outputs.get('LoadBalancerURL')
                    
                    if service_arn:
                        # Try to get service details
                        ecs = boto3.client('ecs', region_name=region)
                        service_name = stack_name.replace('-alb-stack', '')  # Derive service name
                        cluster_name = f"{service_name}-cluster"
                        
                        try:
                            service_response = ecs.describe_services(
                                cluster=cluster_name,
                                services=[service_name]
                            )
                            
                            if service_response['services']:
                                service = service_response['services'][0]
                                return create_response(200, {
                                    'status': 'success',
                                    'deployment_status': 'complete',
                                    'stack_status': stack_status,
                                    'service_status': service['status'],
                                    'service_arn': service_arn,
                                    'running_count': service['runningCount'],
                                    'desired_count': service['desiredCount'],
                                    'pending_count': service['pendingCount'],
                                    'load_balancer_url': f"http://{load_balancer_url}" if load_balancer_url else None,
                                    'message': f"Deployment complete. Service {service_name} is {service['status']}"
                                })
                        except Exception as e:
                            print(f"Error getting service details: {e}")
                    
                    return create_response(200, {
                        'status': 'success',
                        'deployment_status': 'complete',
                        'stack_status': stack_status,
                        'service_arn': service_arn,
                        'load_balancer_url': f"http://{load_balancer_url}" if load_balancer_url else None,
                        'message': 'Deployment complete, service details may still be loading'
                    })
                    
                elif 'FAILED' in stack_status or 'ROLLBACK' in stack_status:
                    return create_response(200, {
                        'status': 'error',
                        'deployment_status': 'failed',
                        'stack_status': stack_status,
                        'message': f'CloudFormation stack deployment failed: {stack_status}'
                    })
                else:
                    return create_response(200, {
                        'status': 'success',
                        'deployment_status': 'in_progress',
                        'stack_status': stack_status,
                        'message': f'Infrastructure deployment in progress: {stack_status}'
                    })
                    
            except cf.exceptions.ClientError as e:
                if 'does not exist' in str(e):
                    return create_response(404, {'error': f'CloudFormation stack {stack_name} not found'})
                raise
        
        # Original service ARN checking logic
        if service_arn:
            ecs = boto3.client('ecs', region_name=region)
            
            # Extract cluster and service name from ARN
            service_name = service_arn.split('/')[-1]
            cluster_name = service_arn.split('/')[-2] if 'cluster' in service_arn else 'default'
            
            response = ecs.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            if not response['services']:
                return create_response(404, {'error': 'Service not found'})
            
            service = response['services'][0]
            
            return create_response(200, {
                'status': 'success',
                'service_status': service['status'],
                'running_count': service['runningCount'],
                'desired_count': service['desiredCount'],
                'pending_count': service['pendingCount'],
                'task_definition': service['taskDefinition'],
                'message': f"Service {service_name} is {service['status']}"
            })
        
    except Exception as e:
        return create_response(500, {'error': f'Status check failed: {str(e)}'})

def handle_iam_roles_template() -> Dict[str, Any]:
    """Return IAM roles template"""
    
    template = {
        'task_execution_role': {
            'trust_policy': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': {'Service': 'ecs-tasks.amazonaws.com'},
                    'Action': 'sts:AssumeRole'
                }]
            },
            'managed_policies': ['arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy']
        },
        'infrastructure_role': {
            'trust_policy': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': {'Service': 'ecs.amazonaws.com'},
                    'Action': 'sts:AssumeRole'
                }]
            },
            'managed_policies': ['arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices']
        }
    }
    
    return create_response(200, {
        'status': 'success',
        'template': template,
        'description': 'Required IAM roles for ECS Express Mode'
    })

def handle_deployment_guide() -> Dict[str, Any]:
    """Return deployment guide"""
    
    guide = """# ECS Express Mode Deployment Guide

## Prerequisites
1. Container image built and pushed to ECR
2. Required IAM roles created
3. AWS CLI configured with appropriate permissions

## Deployment Steps
1. Validate prerequisites using validate_ecs_prerequisites
2. Deploy service using deploy_ecs_express_service  
3. Monitor deployment using check_ecs_service_status

## Benefits
- Zero infrastructure management
- Automatic scaling and load balancing
- Built-in health checks and monitoring
- Cost optimization through pay-per-use pricing
"""
    
    return create_response(200, {
        'status': 'success',
        'guide': guide,
        'description': 'Complete ECS Express Mode deployment guide'
    })
