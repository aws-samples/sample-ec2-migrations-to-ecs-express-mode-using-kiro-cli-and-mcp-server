#!/bin/bash
set -e

# Deploy EKS Auto Mode cluster
# Usage: ./deploy_eks_cluster.sh [region]

REGION="${1:-eu-north-1}"

echo "🚀 Deploying EKS Auto Mode Cluster"
echo "=================================="
echo "📍 Region: $REGION"
echo ""

# Change to EKS CDK directory
cd "$(dirname "$0")/../../infrastructure/eks-auto-mode"

echo "📦 Installing dependencies..."
npm install

echo "🔨 Building CDK project..."
npm run build

echo "🏗️  Deploying EKS cluster to $REGION..."
export CDK_DEFAULT_REGION="$REGION"
export AWS_REGION="$REGION"

cdk deploy --region "$REGION" --require-approval never --outputs-file ../../scripts/deployment/eks-outputs.json

echo ""
echo "✅ EKS cluster deployed successfully!"
echo ""

# Extract cluster name from outputs
CLUSTER_NAME=$(jq -r '.EksAutoModeStack.ClusterName' ../../scripts/deployment/eks-outputs.json)
CONFIG_CMD=$(jq -r '.EksAutoModeStack.ConfigCommand' ../../scripts/deployment/eks-outputs.json)

echo "📋 Cluster Details:"
echo "  Name: $CLUSTER_NAME"
echo "  Region: $REGION"
echo ""

echo "🔧 Configure kubectl:"
echo "  $CONFIG_CMD"
echo ""

echo "⏳ Waiting 60 seconds for cluster to be ready..."
sleep 60

echo "🔍 Verifying cluster..."
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query 'cluster.status' --output text

echo ""
echo "✨ Next steps:"
echo "  1. Configure kubectl: $CONFIG_CMD"
echo "  2. Verify nodes: kubectl get nodes"
echo "  3. Deploy application: kubectl apply -f k8s-manifests/"
echo ""
