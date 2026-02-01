"""
AgentCore EKS Deployment Agent V2 - Pure Python SDK Implementation
===================================================================

This version uses:
- boto3 instead of AWS CLI
- kubernetes Python client instead of kubectl
- AWS CodeBuild for Docker builds (no Docker daemon needed)
- File content as parameters (no filesystem dependencies)

Dependencies:
    boto3>=1.34.0
    kubernetes>=28.1.0
    mcp

Author: AgentCore EKS Migration Team
Date: January 2026
"""

import json
import tempfile
import base64
from pathlib import Path
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP
import boto3
from botocore.signers import RequestSigner
from kubernetes import client as k8s_client

# Initialize FastMCP server
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_eks_token(cluster_name: str, region: str) -> str:
    """
    Generate EKS authentication token using AWS STS
    Replicates aws-iam-authenticator logic
    """
    session = boto3.Session()
    sts_client = session.client('sts', region_name=region)
    
    # Create a presigned URL for sts:GetCallerIdentity
    service_id = sts_client.meta.service_model.service_id
    signer = RequestSigner(
        service_id,
        region,
        'sts',
        'v4',
        session.get_credentials(),
        session.events
    )
    
    # Generate presigned URL with cluster name header
    params = {
        'method': 'GET',
        'url': f'https://sts.{region}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15',
        'body': {},
        'headers': {
            'x-k8s-aws-id': cluster_name
        },
        'context': {}
    }
    
    signed_url = signer.generate_presigned_url(
        params,
        region_name=region,
        expires_in=60,
        operation_name=''
    )
    
    # Encode as base64 (EKS token format)
    token = base64.urlsafe_b64encode(
        signed_url.encode('utf-8')
    ).decode('utf-8').rstrip('=')
    
    return f'k8s-aws-v1.{token}'

def get_k8s_client(cluster_name: str, region: str):
    """
    Get authenticated Kubernetes API client for EKS cluster
    """
    eks = boto3.client('eks', region_name=region)
    
    # Get cluster details
    cluster_info = eks.describe_cluster(name=cluster_name)
    cluster_endpoint = cluster_info['cluster']['endpoint']
    cluster_ca_data = cluster_info['cluster']['certificateAuthority']['data']
    
    # Generate authentication token
    token = generate_eks_token(cluster_name, region)
    
    # Write CA cert to temp file
    ca_cert_file = tempfile.NamedTemporaryFile(delete=False, suffix='.crt')
    ca_cert_file.write(base64.b64decode(cluster_ca_data))
    ca_cert_file.close()
    
    # Configure kubernetes client
    configuration = k8s_client.Configuration()
    configuration.host = cluster_endpoint
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.api_key['authorization'] = token
    configuration.ssl_ca_cert = ca_cert_file.name
    
    return k8s_client.ApiClient(configuration), ca_cert_file.name

# ============================================================================
# MCP TOOLS
# ============================================================================

@mcp.tool()
def setup_oidc_provider(cluster_name: str, region: str) -> dict:
    """
    Setup OIDC identity provider for EKS cluster using boto3
    
    Args:
        cluster_name: Name of the EKS cluster
        region: AWS region
        
    Returns:
        Dictionary with OIDC provider details
    """
    try:
        eks = boto3.client('eks', region_name=region)
        iam = boto3.client('iam')
        
        # Get OIDC issuer from cluster
        cluster = eks.describe_cluster(name=cluster_name)
        oidc_issuer = cluster['cluster']['identity']['oidc']['issuer']
        oidc_id = oidc_issuer.split('/')[-1]
        
        # Check if OIDC provider exists
        providers = iam.list_open_id_connect_providers()
        for provider in providers['OpenIDConnectProviderList']:
            if oidc_id in provider['Arn']:
                return {
                    "status": "exists",
                    "oidc_issuer": oidc_issuer,
                    "oidc_id": oidc_id,
                    "provider_arn": provider['Arn'],
                    "message": "OIDC provider already exists"
                }
        
        # Create OIDC provider
        thumbprint = "9e99a48a9960b14926bb7f3b02e22da2b0ab7280"  # EKS default
        response = iam.create_open_id_connect_provider(
            Url=oidc_issuer,
            ClientIDList=['sts.amazonaws.com'],
            ThumbprintList=[thumbprint]
        )
        
        return {
            "status": "created",
            "oidc_issuer": oidc_issuer,
            "oidc_id": oidc_id,
            "provider_arn": response['OpenIDConnectProviderArn'],
            "message": "OIDC provider created successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error setting up OIDC provider: {str(e)}"
        }

@mcp.tool()
def create_irsa_role(cluster_name: str, app_name: str, region: str, 
                     s3_bucket: str, dynamodb_table: str) -> dict:
    """
    Create IAM role for service account with S3 and DynamoDB permissions using boto3
    
    Args:
        cluster_name: Name of the EKS cluster
        app_name: Name of the application
        region: AWS region
        s3_bucket: S3 bucket name for permissions
        dynamodb_table: DynamoDB table name for permissions
        
    Returns:
        Dictionary with role details
    """
    try:
        sts = boto3.client('sts')
        eks = boto3.client('eks', region_name=region)
        iam = boto3.client('iam')
        
        # Get account ID
        account_id = sts.get_caller_identity()['Account']
        
        # Get OIDC ID
        cluster = eks.describe_cluster(name=cluster_name)
        oidc_issuer = cluster['cluster']['identity']['oidc']['issuer']
        oidc_id = oidc_issuer.split('/')[-1]
        
        role_name = f"{app_name}-irsa-role"
        service_account_name = f"{app_name}-sa"
        
        # Create trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{account_id}:oidc-provider/oidc.eks.{region}.amazonaws.com/id/{oidc_id}"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"oidc.eks.{region}.amazonaws.com/id/{oidc_id}:sub": f"system:serviceaccount:default:{service_account_name}",
                        f"oidc.eks.{region}.amazonaws.com/id/{oidc_id}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        }
        
        # Create or update role
        try:
            response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"IRSA role for {app_name} EKS application"
            )
            role_created = True
        except iam.exceptions.EntityAlreadyExistsException:
            iam.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust_policy)
            )
            role_created = False
        
        # Create permissions policy
        permissions_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{s3_bucket}",
                        f"arn:aws:s3:::{s3_bucket}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan"
                    ],
                    "Resource": f"arn:aws:dynamodb:{region}:{account_id}:table/{dynamodb_table}"
                }
            ]
        }
        
        # Attach permissions policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{app_name}-permissions",
            PolicyDocument=json.dumps(permissions_policy)
        )
        
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        
        return {
            "status": "created" if role_created else "updated",
            "role_name": role_name,
            "role_arn": role_arn,
            "service_account_name": service_account_name,
            "s3_bucket": s3_bucket,
            "dynamodb_table": dynamodb_table,
            "message": f"IRSA role {'created' if role_created else 'updated'} successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating IRSA role: {str(e)}"
        }

@mcp.tool()
def build_image_with_codebuild(source_location: str, image_name: str, 
                                region: str, buildspec_content: str = None) -> dict:
    """
    Build Docker image using AWS CodeBuild (no Docker daemon needed)
    
    Args:
        source_location: Source code location (GitHub, CodeCommit, S3)
        image_name: Name for the Docker image
        region: AWS region
        buildspec_content: Optional custom buildspec.yml content
        
    Returns:
        Dictionary with build status and image URI
    """
    try:
        sts = boto3.client('sts')
        codebuild = boto3.client('codebuild', region_name=region)
        
        account_id = sts.get_caller_identity()['Account']
        ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{image_name}"
        
        # Default buildspec if not provided
        if not buildspec_content:
            buildspec_content = f"""
version: 0.2
phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com
      - aws ecr create-repository --repository-name {image_name} --region {region} || true
  build:
    commands:
      - echo Building Docker image...
      - docker build --platform linux/amd64 -t {image_name} .
      - docker tag {image_name}:latest {ecr_uri}:latest
  post_build:
    commands:
      - echo Pushing Docker image...
      - docker push {ecr_uri}:latest
      - echo Build completed on `date`
"""
        
        # Start build
        response = codebuild.start_build(
            projectName='eks-image-builder',  # Must be pre-created
            sourceLocationOverride=source_location,
            buildspecOverride=buildspec_content,
            environmentVariablesOverride=[
                {'name': 'IMAGE_NAME', 'value': image_name, 'type': 'PLAINTEXT'},
                {'name': 'AWS_REGION', 'value': region, 'type': 'PLAINTEXT'},
                {'name': 'AWS_ACCOUNT_ID', 'value': account_id, 'type': 'PLAINTEXT'}
            ]
        )
        
        build_id = response['build']['id']
        
        # Wait for build to complete (with timeout)
        import time
        max_wait = 600  # 10 minutes
        elapsed = 0
        
        while elapsed < max_wait:
            build_info = codebuild.batch_get_builds(ids=[build_id])['builds'][0]
            status = build_info['buildStatus']
            
            if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                break
            
            # Intentional delay: Wait between deployment status checks to prevent API throttling
            # Intentional delay: Wait between deployment status checks to prevent API throttling

            time.sleep(10)
            elapsed += 10
        
        if status == 'SUCCEEDED':
            return {
                'status': 'success',
                'image_uri': f"{ecr_uri}:latest",
                'build_id': build_id,
                'message': 'Image built and pushed successfully'
            }
        else:
            return {
                'status': 'error',
                'message': f"Build {status.lower()}: {build_info.get('buildStatusReason', 'Unknown error')}",
                'build_id': build_id
            }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error building image: {str(e)}"
        }

@mcp.tool()
def deploy_to_eks_with_irsa(cluster_name: str, app_name: str, image_uri: str, 
                             port: int, replicas: int, env_vars: dict, region: str,
                             role_arn: str, service_account_name: str) -> dict:
    """
    Deploy application to EKS with IRSA using Kubernetes Python client
    
    Args:
        cluster_name: Name of the EKS cluster
        app_name: Name of the application
        image_uri: Full URI of the Docker image
        port: Container port
        replicas: Number of replicas
        env_vars: Environment variables dictionary
        region: AWS region
        role_arn: IAM role ARN for IRSA
        service_account_name: Kubernetes service account name
        
    Returns:
        Dictionary with deployment status
    """
    try:
        # Get authenticated K8s client
        api_client, ca_cert_file = get_k8s_client(cluster_name, region)
        v1 = k8s_client.CoreV1Api(api_client)
        apps_v1 = k8s_client.AppsV1Api(api_client)
        
        # Prepare environment variables
        env_list = [k8s_client.V1EnvVar(name=k, value=v) for k, v in env_vars.items()]
        env_list.extend([
            k8s_client.V1EnvVar(name='AWS_REGION', value=region),
            k8s_client.V1EnvVar(name='AWS_SDK_LOAD_CONFIG', value='1')
        ])
        
        # Create ServiceAccount
        service_account = k8s_client.V1ServiceAccount(
            metadata=k8s_client.V1ObjectMeta(
                name=service_account_name,
                annotations={'eks.amazonaws.com/role-arn': role_arn}
            )
        )
        
        try:
            v1.create_namespaced_service_account('default', service_account)
        except k8s_client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                v1.patch_namespaced_service_account(
                    service_account_name, 'default', service_account
                )
        
        # Create Deployment
        deployment = k8s_client.V1Deployment(
            metadata=k8s_client.V1ObjectMeta(
                name=app_name,
                labels={'app': app_name}
            ),
            spec=k8s_client.V1DeploymentSpec(
                replicas=replicas,
                selector=k8s_client.V1LabelSelector(
                    match_labels={'app': app_name}
                ),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(labels={'app': app_name}),
                    spec=k8s_client.V1PodSpec(
                        service_account_name=service_account_name,
                        containers=[
                            k8s_client.V1Container(
                                name=app_name,
                                image=image_uri,
                                ports=[k8s_client.V1ContainerPort(container_port=port)],
                                env=env_list,
                                resources=k8s_client.V1ResourceRequirements(
                                    requests={'cpu': '250m', 'memory': '512Mi'},
                                    limits={'cpu': '500m', 'memory': '1Gi'}
                                )
                            )
                        ]
                    )
                )
            )
        )
        
        try:
            apps_v1.create_namespaced_deployment('default', deployment)
        except k8s_client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                apps_v1.patch_namespaced_deployment(
                    app_name, 'default', deployment
                )
        
        # Create Service
        service = k8s_client.V1Service(
            metadata=k8s_client.V1ObjectMeta(
                name=app_name,
                annotations={
                    'service.beta.kubernetes.io/aws-load-balancer-type': 'external',
                    'service.beta.kubernetes.io/aws-load-balancer-nlb-target-type': 'ip',
                    'service.beta.kubernetes.io/aws-load-balancer-scheme': 'internet-facing'
                }
            ),
            spec=k8s_client.V1ServiceSpec(
                type='LoadBalancer',
                selector={'app': app_name},
                ports=[k8s_client.V1ServicePort(port=80, target_port=port)]
            )
        )
        
        try:
            v1.create_namespaced_service('default', service)
        except k8s_client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                v1.patch_namespaced_service(app_name, 'default', service)
        
        # Wait for deployment to be ready
        import time
        for _ in range(60):  # Wait up to 5 minutes
            deployment_status = apps_v1.read_namespaced_deployment_status(
                app_name, 'default'
            )
            if deployment_status.status.available_replicas == replicas:
                break
            # Intentional delay: Wait between service readiness checks to prevent API rate limiting
            # Intentional delay: Wait between service readiness checks to prevent API rate limiting

            time.sleep(5)
        
        # Get service endpoint
        service_info = v1.read_namespaced_service(app_name, 'default')
        ingress = service_info.status.load_balancer.ingress
        
        endpoint = None
        if ingress and len(ingress) > 0:
            endpoint = ingress[0].hostname or ingress[0].ip
        
        # Cleanup temp CA cert file
        import os
        os.unlink(ca_cert_file)
        
        return {
            "status": "success",
            "endpoint": f"http://{endpoint}" if endpoint else None,
            "app_name": app_name,
            "replicas": replicas,
            "service_account": service_account_name,
            "role_arn": role_arn,
            "message": "Deployment successful with IRSA"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Deployment failed: {str(e)}"
        }

@mcp.tool()
def get_deployment_status(cluster_name: str, app_name: str, region: str) -> dict:
    """
    Check deployment status using Kubernetes Python client
    
    Args:
        cluster_name: Name of the EKS cluster
        app_name: Name of the application
        region: AWS region
        
    Returns:
        Dictionary with deployment status
    """
    try:
        # Get authenticated K8s client
        api_client, ca_cert_file = get_k8s_client(cluster_name, region)
        apps_v1 = k8s_client.AppsV1Api(api_client)
        
        # Get deployment status
        deployment = apps_v1.read_namespaced_deployment_status(app_name, 'default')
        
        # Cleanup temp CA cert file
        import os
        os.unlink(ca_cert_file)
        
        return {
            "status": "running" if deployment.status.available_replicas and deployment.status.available_replicas > 0 else "pending",
            "replicas": deployment.status.replicas or 0,
            "available": deployment.status.available_replicas or 0,
            "ready": deployment.status.ready_replicas or 0,
            "updated": deployment.status.updated_replicas or 0
        }
        
    except k8s_client.exceptions.ApiException as e:
        if e.status == 404:
            return {"status": "not_found", "message": "Deployment not found"}
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def delete_eks_deployment(cluster_name: str, app_name: str, region: str, 
                          delete_service: bool = True, delete_service_account: bool = True) -> dict:
    """
    Delete EKS deployment, service, and optionally service account using Kubernetes Python client
    
    Args:
        cluster_name: Name of the EKS cluster
        app_name: Name of the application
        region: AWS region
        delete_service: Whether to delete the Kubernetes Service (default: True)
        delete_service_account: Whether to delete the ServiceAccount (default: True)
        
    Returns:
        Dictionary with deletion status
    """
    try:
        # Get authenticated K8s client
        api_client, ca_cert_file = get_k8s_client(cluster_name, region)
        apps_v1 = k8s_client.AppsV1Api(api_client)
        v1 = k8s_client.CoreV1Api(api_client)
        
        results = {
            "status": "success",
            "app_name": app_name,
            "deleted_resources": []
        }
        
        # Delete Deployment
        try:
            apps_v1.delete_namespaced_deployment(
                name=app_name,
                namespace='default',
                body=k8s_client.V1DeleteOptions(
                    propagation_policy='Foreground',
                    grace_period_seconds=30
                )
            )
            results["deleted_resources"].append(f"Deployment: {app_name}")
        except k8s_client.exceptions.ApiException as e:
            if e.status == 404:
                results["deleted_resources"].append(f"Deployment: {app_name} (not found)")
            else:
                raise
        
        # Delete Service
        if delete_service:
            try:
                v1.delete_namespaced_service(
                    name=app_name,
                    namespace='default',
                    body=k8s_client.V1DeleteOptions(grace_period_seconds=30)
                )
                results["deleted_resources"].append(f"Service: {app_name}")
            except k8s_client.exceptions.ApiException as e:
                if e.status == 404:
                    results["deleted_resources"].append(f"Service: {app_name} (not found)")
                else:
                    raise
        
        # Delete ServiceAccount
        if delete_service_account:
            service_account_name = f"{app_name}-sa"
            try:
                v1.delete_namespaced_service_account(
                    name=service_account_name,
                    namespace='default',
                    body=k8s_client.V1DeleteOptions(grace_period_seconds=30)
                )
                results["deleted_resources"].append(f"ServiceAccount: {service_account_name}")
            except k8s_client.exceptions.ApiException as e:
                if e.status == 404:
                    results["deleted_resources"].append(f"ServiceAccount: {service_account_name} (not found)")
                else:
                    raise
        
        # Cleanup temp CA cert file
        import os
        os.unlink(ca_cert_file)
        
        results["message"] = f"Successfully deleted {len([r for r in results['deleted_resources'] if 'not found' not in r])} resource(s)"
        
        return results
        
    except k8s_client.exceptions.ApiException as e:
        return {
            "status": "error",
            "message": f"Kubernetes API error: {e.reason}",
            "details": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting deployment: {str(e)}"
        }

@mcp.tool()
def list_deployments(cluster_name: str, region: str, namespace: str = 'default') -> dict:
    """
    List all deployments in the EKS cluster using Kubernetes Python client
    
    Args:
        cluster_name: Name of the EKS cluster
        region: AWS region
        namespace: Kubernetes namespace (default: 'default')
        
    Returns:
        Dictionary with list of deployments
    """
    try:
        # Get authenticated K8s client
        api_client, ca_cert_file = get_k8s_client(cluster_name, region)
        apps_v1 = k8s_client.AppsV1Api(api_client)
        
        # List deployments
        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
        
        deployment_list = []
        for dep in deployments.items:
            deployment_list.append({
                "name": dep.metadata.name,
                "replicas": dep.status.replicas or 0,
                "ready": dep.status.ready_replicas or 0,
                "available": dep.status.available_replicas or 0,
                "updated": dep.status.updated_replicas or 0,
                "created": dep.metadata.creation_timestamp.isoformat() if dep.metadata.creation_timestamp else None,
                "labels": dep.metadata.labels or {}
            })
        
        # Cleanup temp CA cert file
        import os
        os.unlink(ca_cert_file)
        
        return {
            "status": "success",
            "cluster": cluster_name,
            "namespace": namespace,
            "count": len(deployment_list),
            "deployments": deployment_list
        }
        
    except k8s_client.exceptions.ApiException as e:
        return {
            "status": "error",
            "message": f"Kubernetes API error: {e.reason}",
            "details": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing deployments: {str(e)}"
        }

# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
