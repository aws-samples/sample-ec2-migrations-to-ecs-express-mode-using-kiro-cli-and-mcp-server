# Demo Workflow: Amazon EC2 to Amazon ECS/EKS Migration with MCP

This guide provides a complete demo workflow for showcasing the Amazon EC2 to Amazon ECS/EKS migration solution using Model Context Protocol (MCP) and AI agents.

---

## 🎯 Demo Overview

**Duration**: 30-45 minutes  
**Audience Level**: L100 (Overview) to L300 (Deep Dive)  
**Key Message**: Simplify container deployments to AWS using AI-powered agents and natural language

---

## 📋 Prerequisites

### Required AWS Services
- ✅ **Amazon Amazon ECS** - Elastic Container Service (Express Mode)
- ✅ **Amazon EKS** - Elastic Kubernetes Service
- ✅ **Amazon ECR** - Elastic Container Registry
- ✅ **Amazon Bedrock** - For Claude 3.5 Sonnet LLM
- ✅ **AWS AWS CloudFormation** - Infrastructure as Code
- ✅ **IAM** - Identity and Access Management

### Local Setup
- Docker Desktop installed and running
- AWS CLI configured with credentials
- Python 3.9+ installed
- Node.js 18+ (for sample application)
- Maven/Java 21 (for Java demo)

### IAM Permissions Required
```
- bedrock:InvokeModel
- bedrock-agentcore:*
- ecs:*
- eks:*
- ecr:*
- cloudformation:*
- iam:CreateRole, iam:AttachRolePolicy
- ec2:DescribeVpcs, ec2:DescribeSubnets
```

---

## 🚀 Part 1: L100 - High-Level Overview (10 minutes)

### What Problem Are We Solving?

**Traditional Amazon EC2 Migration Challenges:**
- Manual Docker image building and pushing
- Complex AWS CloudFormation/CDK templates
- Multiple CLI commands to remember
- Error-prone configuration management
- Steep learning curve for Kubernetes

**Our Solution:**
- Natural language deployment commands
- Automated Docker build and push
- Intelligent resource detection
- AI-powered routing to appropriate tools
- Single web UI for both Amazon ECS and EKS

### Architecture Overview

```
┌─────────────────┐
│   Web UI        │ ← User types natural language
│   (Flask)       │
└────────┬────────┘
         │
         ├─→ LLM Router (Claude 3.5 Sonnet)
         │   ├─→ Parse intent
         │   ├─→ Extract parameters
         │   └─→ Route to agent
         │
         ├─→ Amazon ECS Agent (Bedrock AgentCore)
         │   ├─→ Create ECR repository
         │   ├─→ Deploy to Amazon ECS Express Mode
         │   └─→ Monitor CloudFormation
         │
         └─→ EKS Agent (Bedrock AgentCore)
             ├─→ Setup OIDC provider
             ├─→ Create IRSA roles
             ├─→ Deploy to Kubernetes
             └─→ Expose via LoadBalancer
```

### Key Services Explained

| Service | Role | Why It Matters |
|---------|------|----------------|
| **Amazon Bedrock** | LLM for natural language understanding | Converts "deploy my app with 5 replicas" into structured commands |
| **Bedrock AgentCore** | Hosts MCP agents with tools | Provides serverless runtime for deployment agents |
| **Amazon ECS Express Mode** | Simplified container orchestration | No cluster management, automatic infrastructure |
| **Amazon EKS** | Kubernetes service | Full Kubernetes compatibility for complex workloads |
| **Amazon ECR** | Container registry | Stores Docker images securely |

---

## 🎬 Part 2: L200 - Live Demo (15 minutes)

### Demo Script

#### 1. Start the Web UI (2 minutes)

```bash
# Terminal 1: Start Flask app
cd web-ui
python3 app.py

# Open browser: http://localhost:5001
```

**Show the UI:**
- Two tabs: Amazon ECS and EKS
- Chat interface for natural language
- Configuration options (region, cluster)

#### 2. Deploy Node.js App to Amazon ECS (5 minutes)

**Natural Language Command:**
```
Deploy the sample-application with 3 tasks in eu-north-1
```

**What Happens Behind the Scenes:**
1. ✅ LLM parses: app=sample-application, tasks=3, region=eu-north-1
2. ✅ Creates ECR repository
3. ✅ Builds Docker image from `sample-application/`
4. ✅ Pushes to ECR
5. ✅ Deploys to Amazon ECS Express Mode via CloudFormation
6. ✅ Provisions ALB, security groups, VPC automatically

**Show in Console:**
- AWS CloudFormation stack creation
- Amazon ECS service with 3 running tasks
- ALB endpoint URL

**Test the Endpoint:**
```bash
curl http://<alb-endpoint>
# Should return the blog application
```

#### 3. Deploy Java API to Amazon ECS (4 minutes)

**Natural Language Command:**
```
Deploy simple-java-api with 2 tasks and 1024 CPU and 2048 memory
```

**Highlight:**
- Automatic port detection (8080 for Java vs 3000 for Node.js)
- Increased resources for Java apps
- Different source folder detection
- Health check endpoints

**Show:**
- Different Dockerfile being used
- Java Spring Boot startup logs
- Health check at `/health`

#### 4. Deploy to EKS with IRSA (4 minutes)

**Natural Language Command:**
```
Deploy blog-app in ec2-eks-migration with 5 replicas
```

**What's Different:**
1. ✅ OIDC provider setup (one-time)
2. ✅ IRSA role creation (IAM for service accounts)
3. ✅ Kubernetes deployment + service
4. ✅ LoadBalancer provisioning
5. ✅ AWS resource access via IRSA

**Show in Console:**
- EKS cluster
- Kubernetes deployments: `kubectl get deployments`
- Pods: `kubectl get pods`
- Service endpoint

---

## 🔬 Part 3: L300 - Deep Dive Topics (15 minutes)

### Topic 1: LLM-Based Routing Architecture

**How It Works:**

```python
# User message
"Deploy simple-java-api with 5 tasks"

# LLM Prompt
"""
Analyze this message and extract:
- app_name
- desired_count
- cpu, memory
- region
"""

# LLM Response
{
  "operation": "deploy",
  "arguments": {
    "app_name": "simple-java-api",
    "desired_count": 5,
    "cpu": "1024",
    "memory": "2048"
  },
  "reasoning": "User requested deployment with 5 tasks..."
}
```

**Benefits:**
- No rigid parsing rules
- Handles variations: "5 tasks", "5 replicas", "5 instances"
- Extracts implicit parameters
- Provides reasoning for transparency

**Code Deep Dive:**
```python
# web-ui/app.py
def llm_route_ecs_command(message: str, region: str) -> dict:
    # Constructs prompt with available tools
    # Calls Claude 3.5 Sonnet via Bedrock
    # Returns structured JSON with operation and arguments
```

### Topic 2: MCP (Model Context Protocol) Agents

**What is MCP?**
- Open protocol for connecting AI models to tools
- Standardized way to expose functions to LLMs
- Developed by Anthropic

**Our Implementation:**

```python
# agentcore-agent-runtime/agent.py
@tool
def deploy_ecs_express_service(
    service_name: str,
    image_uri: str,
    cpu: str = "256",
    memory: str = "512",
    desired_count: int = 1
) -> dict:
    # Creates AWS CloudFormation template
    # Deploys Amazon ECS Express Gateway Service
    # Returns deployment status
```

**Agent Architecture:**
- **Strands Agent** (Amazon ECS) - Conversational, multi-step workflows
- **MCP Tools** (EKS) - Direct tool invocation with structured I/O

**Why Two Approaches?**
- Amazon ECS: Simpler, conversational for Express Mode
- EKS: Complex, multi-step with OIDC, IRSA, K8s

### Topic 3: Amazon ECS Express Mode vs Traditional ECS

| Feature | Express Mode | Traditional Amazon ECS |
|---------|--------------|-----------------|
| Cluster Management | Automatic | Manual |
| VPC/Networking | Auto-provisioned | Manual setup |
| Load Balancer | Included | Separate resource |
| Scaling | Built-in | Manual ASG config |
| Use Case | Simple apps | Complex architectures |

**Express Mode Benefits:**
- 80% less configuration
- Faster time to production
- Lower operational overhead

**When to Use Traditional:**
- Custom networking requirements
- Existing VPC integration
- Advanced scaling policies

### Topic 4: IRSA (IAM Roles for Service Accounts)

**The Problem:**
- Pods need AWS permissions (Amazon S3, Amazon DynamoDB)
- Traditional: Instance roles (too broad)
- Better: Pod-level IAM roles

**How IRSA Works:**

```
1. OIDC Provider connects EKS to IAM
   ├─→ Trust relationship established
   └─→ Kubernetes can assume IAM roles

2. Service Account created in K8s
   ├─→ Annotated with IAM role ARN
   └─→ Pods use this service account

3. Pod assumes IAM role
   ├─→ Gets temporary credentials
   └─→ Accesses AWS services
```

**Our Automation:**
```python
# 1. Setup OIDC (one-time per cluster)
setup_oidc_provider(cluster_name, region)

# 2. Create IRSA role (per application)
create_irsa_role(
    cluster_name="ec2-eks-migration",
    app_name="blog-app",
    s3_bucket="blog-images-*",
    dynamodb_table="blog-posts"
)

# 3. Deploy with role
deploy_to_eks_with_irsa(
    role_arn="arn:aws:iam::...:role/blog-app-irsa-role",
    service_account_name="blog-app-sa"
)
```

### Topic 5: Intelligent Resource Detection

**Path Detection:**
```python
# Checks in order:
1. /workspace/{app_name}/          # Direct match
2. /workspace/sample-application/  # Default fallback

# Validates:
- Folder exists
- Dockerfile present
```

**Port Detection:**
```python
if 'java' in app_name.lower():
    port = 8080  # Spring Boot default
else:
    port = 3000  # Node.js default
```

**Resource Sizing:**
```python
if 'java' in app_name.lower():
    cpu = '1024'    # 1 vCPU
    memory = '2048'  # 2 GB (Java needs more)
else:
    cpu = '512'     # 0.5 vCPU
    memory = '1024'  # 1 GB
```

**Environment Variables:**
```python
# Only add blog-specific vars for blog apps
if 'blog' in app_name or 'sample' in app_name:
    env_vars.update({
        'DYNAMODB_TABLE': 'blog-posts',
        'Amazon S3_BUCKET': 'blog-images-*',
        'COGNITO_*': '...'
    })
```

---

## 🎓 Key Takeaways

### For Developers
- ✅ Deploy containers with natural language
- ✅ No need to learn complex CLI commands
- ✅ Automatic resource optimization
- ✅ Built-in recommended practices

### For Architects
- ✅ Standardized deployment patterns
- ✅ Infrastructure as Code via CloudFormation
- ✅ Security recommended practices (IRSA, least privilege)
- ✅ Multi-environment support

### For DevOps
- ✅ Reduced operational overhead
- ✅ Automated health checks and monitoring
- ✅ Easy rollback via CloudFormation
- ✅ Audit trail through AWS CloudFormation events

---

## 🔧 Troubleshooting Common Issues

### Issue 1: Health Check Failures

**Symptom:** Stack rolls back with "No rollback candidate"

**Cause:** Container not responding on configured port

**Solution:**
```java
// Add root health check endpoint
@GetMapping("/")
public Map<String, String> root() {
    return Map.of("status", "ok");
}
```

### Issue 2: Java App Out of Memory

**Symptom:** Container crashes, OOMKilled

**Solution:** Increase memory
```
Deploy simple-java-api with 2048 memory
```

### Issue 3: Wrong Source Code Built

**Symptom:** Node.js app deployed instead of Java

**Check:** Flask console for debug output
```
DEBUG: Looking for app 'simple-java-api' in workspace
DEBUG: Checking /path/to/simple-java-api - exists: True, has Dockerfile: True
DEBUG: Selected path: /path/to/simple-java-api
```

---

## 📚 Additional Resources

### Documentation
- [Amazon ECS Express Mode Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-express.html)
- [EKS IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Model Context Protocol](https://modelcontextprotocol.io/)

### Sample Applications
- `sample-application/` - Node.js blog with Amazon DynamoDB and S3
- `simple-java-api/` - Spring Boot REST API

### Code Repositories
- Web UI: `web-ui/`
- Amazon ECS Agent: `agentcore-agent-runtime/`
- EKS Agent: `agentcore-eks-runtime/`

---

## 🎤 Demo Q&A Preparation

### Expected Questions

**Q: How much does this cost?**
A: 
- Bedrock: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- Amazon ECS Express: Standard Amazon ECS pricing (no additional cost)
- EKS: $0.10/hour per cluster + Amazon EC2/Fargate costs
- Typical demo: <$5 for full walkthrough

**Q: Can this work with existing applications?**
A: Yes! Just needs:
- Dockerfile in the app folder
- Health check endpoint (/, /health, /healthz)
- Port configuration

**Q: What about production deployments?**
A: This is a demo/prototype. For production:
- Add CI/CD integration
- Implement proper secret management
- Add monitoring and alerting
- Use infrastructure as code (CDK/Terraform)

**Q: How does this compare to AWS Copilot?**
A: 
- Copilot: CLI-based, opinionated workflows
- This solution: Natural language, flexible, AI-powered
- Both: Simplify container deployments

**Q: Can I customize the agents?**
A: Absolutely! The MCP tools are Python functions:
```python
@tool
def my_custom_deployment(params):
    # Your logic here
    pass
```

---

## 🎯 Success Metrics

After the demo, attendees should be able to:
- ✅ Explain the benefits of AI-powered deployments
- ✅ Understand Amazon ECS Express Mode vs traditional ECS
- ✅ Describe how IRSA works in EKS
- ✅ Deploy their own containerized applications
- ✅ Troubleshoot common deployment issues

---

## 📝 Demo Checklist

### Before Demo
- [ ] AWS credentials configured
- [ ] Docker Desktop running
- [ ] Flask app tested locally
- [ ] Sample apps built and tested
- [ ] EKS cluster accessible
- [ ] IAM roles created (ecsTaskExecutionRole, ecsInfrastructureRole)

### During Demo
- [ ] Show natural language commands
- [ ] Highlight automatic resource detection
- [ ] Display AWS CloudFormation/K8s console
- [ ] Test deployed endpoints
- [ ] Show error handling and debugging

### After Demo
- [ ] Clean up resources (delete stacks)
- [ ] Share GitHub repository
- [ ] Provide documentation links
- [ ] Collect feedback

---

**Happy Demoing! 🚀**
