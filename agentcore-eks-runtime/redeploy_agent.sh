#!/bin/bash
# Redeploy AgentCore EKS agent with updated code

cd "$(dirname "$0")"

echo "🔄 Redeploying AgentCore EKS agent with updated code..."

# Launch updated agent
agentcore launch

echo "✅ Agent redeployed. Wait 30 seconds for it to be ready..."
sleep 30

echo "📋 Checking agent status..."
agentcore status

echo ""
echo "✅ Done! Now run: python3 ../test-python-scripts/test_eks_deployment.py"
