#!/bin/bash
# Redeploy AgentCore agent with environment variable support

cd agentcore-agent-runtime

echo "🔄 Redeploying AgentCore agent with updated code..."

# Launch updated agent
agentcore launch

echo "✅ Agent redeployed. Wait 30 seconds for it to be ready..."
sleep 30

echo "📋 Checking agent status..."
agentcore status

echo ""
echo "✅ Done! Now run: python3 test_conversation.py"
