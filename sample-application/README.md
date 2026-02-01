# Sample Application

A secure blog application demonstrating the migration from Amazon EC2 to container orchestration platforms (Amazon ECS Express Mode and EKS).

## Application Overview

**Technology Stack:**
- **Backend**: Node.js with Express
- **Frontend**: HTML/CSS/JavaScript with Bootstrap
- **Authentication**: AWS Cognito
- **Database**: DynamoDB
- **Storage**: Amazon S3 for image uploads
- **Logging**: CloudWatch

## Features

### Core Functionality
- **User Authentication**: Amazon Cognito-based login/logout
- **Blog Management**: Create, read, and delete posts
- **Image Upload**: Amazon S3 integration for post images
- **Post Deletion**: Delete posts with confirmation dialog and automatic Amazon S3 cleanup
- **Responsive Design**: Mobile-friendly Bootstrap interface
- **Health Checks**: Built-in health endpoint for monitoring

### Security Features
- **JWT Token Validation**: Secure API endpoints
- **CORS Configuration**: Proper cross-origin handling
- **Input Validation**: Sanitized user inputs
- **Secure Headers**: Security recommended practices
- **Non-root Container**: Security-hardened Dockerfile

## File Structure

```
sample-application/
├── src/
│   └── server.js              # Main application server
├── public/
│   ├── index.html             # Frontend interface
│   ├── style.css              # Application styling
│   └── script.js              # Frontend JavaScript
├── Dockerfile                 # Container configuration
├── package.json               # Node.js dependencies
└── README.md                  # Application documentation
```

## Configuration

### Environment Variables
The application requires these environment variables:
- `AWS_REGION`: AWS region for services
- `DYNAMODB_TABLE`: Amazon DynamoDB table name
- `Amazon S3_BUCKET`: Amazon S3 bucket for image storage
- `COGNITO_USER_POOL_ID`: Amazon Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Amazon Cognito App Client ID
- `PORT`: Application port (default: 3000)

### AWS Services Integration
- **Amazon DynamoDB**: Stores blog posts and metadata
- **Amazon S3**: Stores uploaded images with proper permissions
- **Amazon Cognito**: Handles user authentication and authorization
- **CloudWatch**: Application logging and monitoring

## Container Configuration

### Dockerfile Features
- **Multi-stage ready**: Optimized for production
- **Non-root user**: Security recommended practices
- **Health checks**: Container health monitoring
- **Production dependencies**: Only required packages
- **Proper ownership**: Secure file permissions

### Health Check
The application provides a health endpoint at `/health` that:
- Validates AWS service connectivity
- Checks database accessibility
- Returns comprehensive status information
- Used by load balancers and container orchestrators

## Development

### Local Development
```bash
npm install
npm start
```

### Container Development
```bash
docker build -t blog-app .
docker run -p 3000:3000 \
  -e AWS_REGION=us-west-2 \
  -e DYNAMODB_TABLE=blog-posts \
  -e Amazon S3_BUCKET=your-bucket \
  -e COGNITO_USER_POOL_ID=your-pool-id \
  -e COGNITO_CLIENT_ID=your-client-id \
  blog-app
```

## API Endpoints

### Posts Management

#### Get All Posts
```http
GET /api/posts
```
Returns all blog posts from Amazon DynamoDB.

**Response:**
```json
[
  {
    "id": "post-123",
    "title": "My Blog Post",
    "content": "Post content...",
    "author": "John Doe",
    "createdAt": "2026-01-16T10:00:00Z",
    "imageUrl": "https://s3.amazonaws.com/bucket/image.jpg"
  }
]
```

#### Create Post
```http
POST /api/posts
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Request Body:**
- `title` (string, required): Post title
- `content` (string, required): Post content
- `author` (string, required): Author name
- `image` (file, optional): Image file to upload

**Response:**
```json
{
  "id": "post-123",
  "title": "My Blog Post",
  "content": "Post content...",
  "author": "John Doe",
  "createdAt": "2026-01-16T10:00:00Z",
  "imageUrl": "https://s3.amazonaws.com/bucket/image.jpg"
}
```

#### Delete Post
```http
DELETE /api/posts/:id
Authorization: Bearer <token>
```

**Parameters:**
- `id` (string, required): Post ID to delete

**Response (Success):**
```json
{
  "message": "Post deleted successfully"
}
```

**Response (Not Found):**
```json
{
  "error": "Post not found"
}
```

**Features:**
- Requires authentication (Bearer token)
- Deletes post from DynamoDB
- Automatically removes associated image from S3
- Returns 404 if post doesn't exist
- Includes confirmation dialog in UI

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-16T10:00:00Z",
  "services": {
    "dynamodb": "connected",
    "s3": "connected"
  }
}
```

## User Interface Features

### Delete Post Functionality

The delete feature provides a safe and user-friendly way to remove posts:

**User Flow:**
1. Click the 🗑️ Delete button on any post
2. Confirm deletion in the dialog prompt
3. Post fades out smoothly (300ms animation)
4. Success message appears
5. Post is removed from database and S3

**Safety Features:**
- Confirmation dialog prevents accidental deletion
- Shows post title in confirmation message
- Graceful error handling with user feedback
- Automatic cleanup of Amazon S3 images

**UI Elements:**
```html
<!-- Each post includes action buttons -->
<div class="post-actions">
  <button class="edit-btn" onclick="editPost('post-id')">✏️ Edit</button>
  <button class="delete-btn" onclick="deletePost('post-id', 'Post Title')">🗑️ Delete</button>
</div>
```

**JavaScript Implementation:**
```javascript
async function deletePost(postId, postTitle) {
  if (!confirm(`Are you sure you want to delete "${postTitle}"?`)) {
    return;
  }
  
  const token = localStorage.getItem('token');
  const response = await fetch(`/api/posts/${postId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (response.ok) {
    // Fade out and remove post
    const postElement = document.getElementById(`post-${postId}`);
    postElement.style.transition = 'opacity 0.3s';
    postElement.style.opacity = '0';
    setTimeout(() => postElement.remove(), 300);
    alert('Post deleted successfully!');
  }
}
```

## Deployment Options

This application can be deployed to multiple container orchestration platforms:

### Amazon ECS Express Mode Deployment

**Features:**
- Simplified deployment with automatic infrastructure provisioning
- Integrated Application Load Balancer
- Auto-scaling capabilities
- Native AWS service integration

**Configuration:**
- Environment variables passed via Amazon ECS task definition
- IAM task role for AWS service access
- CloudWatch Logs for centralized logging
- VPC networking with security groups

**Deployment Steps:**
1. Build and push Docker image to ECR
2. Create Amazon ECS task definition with environment variables
3. Deploy using Amazon ECS Express Mode
4. Configure ALB health checks
5. Set up auto-scaling policies

### EKS (Kubernetes) Deployment

**Features:**
- Full Kubernetes orchestration capabilities
- Multi-cloud portability
- Advanced deployment strategies (blue/green, canary)
- Rich ecosystem of tools and operators

**Configuration:**
- Environment variables via Kubernetes ConfigMaps/Secrets
- IAM roles via IRSA (IAM Roles for Service Accounts)
- CloudWatch Container Insights for monitoring
- VPC CNI for native AWS networking

**Deployment Steps:**
1. Build and push Docker image to ECR
2. Create Kubernetes manifests (Deployment, Service, Ingress)
3. Configure IRSA for AWS service access
4. Deploy to EKS cluster using kubectl/Helm
5. Set up Horizontal Pod Autoscaler (HPA)

**Sample Kubernetes Manifest:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: blog-app
  template:
    metadata:
      labels:
        app: blog-app
    spec:
      serviceAccountName: blog-app-sa
      containers:
      - name: blog-app
        image: <account-id>.dkr.ecr.<region>.amazonaws.com/blog-app:latest
        ports:
        - containerPort: 3000
        env:
        - name: AWS_REGION
          value: "us-west-2"
        - name: DYNAMODB_TABLE
          valueFrom:
            configMapKeyRef:
              name: blog-config
              key: dynamodb-table
        - name: Amazon S3_BUCKET
          valueFrom:
            configMapKeyRef:
              name: blog-config
              key: s3-bucket
        - name: COGNITO_USER_POOL_ID
          valueFrom:
            secretKeyRef:
              name: blog-secrets
              key: cognito-pool-id
        - name: COGNITO_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: blog-secrets
              key: cognito-client-id
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: blog-app-service
spec:
  type: LoadBalancer
  selector:
    app: blog-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
```

## Migration Considerations

### Amazon EC2 to Container Orchestration Changes

#### Common Changes (Amazon ECS & EKS)
- **Environment Variables**: Moved from Amazon EC2 user data to container configuration
- **IAM Roles**: Changed from Amazon EC2 instance profile to container-specific roles
- **Health Checks**: Enhanced for container orchestration and load balancers
- **Logging**: Configured for CloudWatch Logs integration
- **Scalability**: Automatic scaling based on metrics

#### Amazon ECS-Specific Changes
- **Task Definitions**: Define container configuration and resources
- **Service Discovery**: Native AWS Cloud Map integration
- **Networking**: Amazon ECS-managed networking with awsvpc mode
- **IAM**: Task roles and execution roles

#### EKS-Specific Changes
- **Kubernetes Manifests**: Deployments, Services, ConfigMaps, Secrets
- **IRSA**: IAM Roles for Service Accounts for fine-grained permissions
- **Networking**: VPC CNI plugin for pod networking
- **Service Mesh**: Optional Istio/App Mesh integration
- **Helm Charts**: Package management for complex deployments

### Container Optimizations
- **Image Size**: Optimized with Alpine Linux base (~50MB)
- **Security**: Non-root user and minimal attack surface
- **Performance**: Production-only dependencies
- **Monitoring**: Built-in health checks and logging
- **Multi-platform**: Works on both Amazon ECS and EKS without changes
