#!/bin/bash
set -e

echo "🚀 Deploying Container Migration MCP Server to AWS Lambda"
echo "========================================================"

# Check prerequisites
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI is required. Install it first:"
    echo "   pip install aws-sam-cli"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is required"
    exit 1
fi

# Build and deploy
echo "📦 Building SAM application..."
sam build

echo "🚀 Deploying to AWS..."
sam deploy --guided --stack-name container-migration-mcp

echo "✅ Deployment complete!"
echo ""
echo "🔗 API endpoints will be available at:"
echo "   https://{api-id}.execute-api.{region}.amazonaws.com/dev"
echo ""
echo "📋 Available endpoints:"
echo "   POST /tools/optimize_dockerfile"
echo "   POST /tools/build_and_push_container" 
echo "   POST /tools/validate_container_security"
echo "   GET  /resources/dockerfile-template"
echo "   GET  /resources/Awes-script"
