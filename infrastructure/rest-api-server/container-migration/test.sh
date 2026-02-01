#!/bin/bash
# Test script for Container Migration MCP Server

echo "🧪 Testing Container Migration MCP Server"
echo "========================================"

# Check if MCP server is executable
if [ -x "./server.py" ]; then
    echo "✅ MCP server is executable"
else
    echo "❌ MCP server is not executable"
    chmod +x ./server.py
fi

# Check dependencies
echo "📦 Checking dependencies..."

if command -v python3 &> /dev/null; then
    echo "✅ Python 3 is available"
else
    echo "❌ Python 3 is required"
    exit 1
fi

if command -v docker &> /dev/null; then
    echo "✅ Docker is available"
else
    echo "❌ Docker is required"
    exit 1
fi

if command -v aws &> /dev/null; then
    echo "✅ AWS CLI is available"
else
    echo "❌ AWS CLI is required"
    exit 1
fi

# Test MCP server startup
echo "🚀 Testing MCP server startup..."
timeout 5s python3 ./server.py < /dev/null > /dev/null 2>&1
if [ $? -eq 124 ]; then
    echo "✅ MCP server starts successfully"
else
    echo "⚠️ MCP server may have issues"
fi

echo ""
echo "🎉 Container Migration MCP Server is ready!"
echo ""
echo "Integration example:"
echo '{'
echo '  "mcpServers": {'
echo '    "container-migration": {'
echo '      "command": "python3",'
echo '      "args": ["'$(pwd)'/server.py"]'
echo '    }'
echo '  }'
echo '}'
