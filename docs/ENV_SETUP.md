# Environment Variables Setup

## Required Environment Variables

Before running the migration scripts, set the following environment variables:

```bash
# MCP Server Configuration
export MCP_API_URL="https://your-api-gateway-url.execute-api.region.amazonaws.com/Prod"
export MCP_API_KEY="your-actual-api-key-from-secrets-manager"
```

## Setting Environment Variables

### Option 1: Export in Terminal
```bash
export MCP_API_URL="https://d1lx8mfyu4.execute-api.us-west-2.amazonaws.com/Prod"
export MCP_API_KEY="$(aws secretsmanager get-secret-value --secret-id mcp-api-key --query SecretString --output text)"
```

### Option 2: Create .env file (add to .gitignore)
```bash
# Create .env file
cat > .env << EOF
MCP_API_URL=https://d1lx8mfyu4.execute-api.us-west-2.amazonaws.com/Prod
MCP_API_KEY=your-actual-api-key
EOF

# Load environment variables
source .env
```

### Option 3: Use AWS Secrets Manager
Store your API key in AWS Secrets Manager and retrieve it:

```bash
# Store the key in Secrets Manager
aws secretsmanager create-secret \
    --name "mcp-api-key" \
    --description "API key for MCP server" \
    --secret-string "your-actual-api-key"

# Retrieve and use the key
export MCP_API_KEY=$(aws secretsmanager get-secret-value \
    --secret-id mcp-api-key \
    --query SecretString \
    --output text)
```

## Running the Scripts

After setting the environment variables:

```bash
# Run migration
python3 migrate_to_ecs_express.py

# Run tests
python3 test_mcp_server.py
```

## Security Notes

- Never commit API keys to version control
- Use AWS Secrets Manager for production environments
- The example key `AKIAIOSFODNN7EXAMPLE` is AWS-approved for testing/documentation only
- Always rotate API keys regularly
