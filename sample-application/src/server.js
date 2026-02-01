const express = require('express');
const AWS = require('aws-sdk');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const cors = require('cors');
const path = require('path');
const jwt = require('jsonwebtoken');
const jwkToPem = require('jwk-to-pem');
const axios = require('axios');
const fs = require('fs');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// AWS Configuration with IRSA support
// Check if running in EKS with IRSA
if (process.env.AWS_WEB_IDENTITY_TOKEN_FILE && process.env.AWS_ROLE_ARN) {
  console.log('Configuring AWS SDK with IRSA credentials');
  console.log('Token file:', process.env.AWS_WEB_IDENTITY_TOKEN_FILE);
  console.log('Role ARN:', process.env.AWS_ROLE_ARN);
  
  // Use TokenFileWebIdentityCredentials for automatic token refresh
  AWS.config.credentials = new AWS.TokenFileWebIdentityCredentials({
    roleArn: process.env.AWS_ROLE_ARN,
    tokenFile: process.env.AWS_WEB_IDENTITY_TOKEN_FILE,
    roleSessionName: process.env.AWS_ROLE_SESSION_NAME || 'eks-session'
  });
} else {
  console.log('Using default AWS credential chain');
}

AWS.config.update({
  region: process.env.AWS_REGION || 'eu-north-1',
  signatureVersion: 'v4'
});

const dynamodb = new AWS.DynamoDB.DocumentClient();
const s3 = new AWS.S3({
  region: process.env.AWS_REGION || 'eu-north-1',
  signatureVersion: 'v4'
});

const TABLE_NAME = process.env.DYNAMODB_TABLE || 'blog-posts';
const S3_BUCKET = process.env.S3_BUCKET || 'blog-images-bucket';
const USER_POOL_ID = process.env.COGNITO_USER_POOL_ID;
const CLIENT_ID = process.env.COGNITO_CLIENT_ID;

let jwks = null;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Multer configuration for file uploads
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Get JWKS for token verification
async function getJWKS() {
  if (!jwks && USER_POOL_ID) {
    try {
      const response = await axios.get(`https://cognito-idp.${process.env.AWS_REGION || 'eu-north-1'}.amazonaws.com/${USER_POOL_ID}/.well-known/jwks.json`);
      jwks = response.data;
    } catch (error) {
      console.error('Failed to get JWKS:', error.message);
    }
  }
  return jwks;
}

// Verify JWT token
async function verifyToken(token) {
  if (!USER_POOL_ID) return null;
  
  try {
    const jwksData = await getJWKS();
    if (!jwksData) return null;
    
    const decoded = jwt.decode(token, { complete: true });
    if (!decoded) return null;
    
    const kid = decoded.header.kid;
    const jwk = jwksData.keys.find(key => key.kid === kid);
    if (!jwk) return null;
    
    const pem = jwkToPem(jwk);
    const verified = jwt.verify(token, pem, { algorithms: ['RS256'] });
    return verified;
  } catch (error) {
    console.error('Token verification failed:', error.message);
    return null;
  }
}

// Authentication middleware
async function authenticateToken(req, res, next) {
  if (!USER_POOL_ID) {
    return res.status(500).json({ error: 'Authentication not configured' });
  }
  
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }
  
  const user = await verifyToken(token);
  if (!user) {
    return res.status(403).json({ error: 'Invalid token' });
  }
  
  req.user = user;
  next();
}

// Get presigned URL for S3 upload
app.post('/api/upload-url', authenticateToken, (req, res) => {
  const { fileName, fileType } = req.body;
  const key = `images/${uuidv4()}-${fileName}`;
  
  const params = {
    Bucket: S3_BUCKET,
    Key: key,
    Expires: 300,
    ContentType: fileType
  };
  
  const uploadUrl = s3.getSignedUrl('putObject', params);
  res.json({ uploadUrl, key });
});

// Get presigned URL for S3 download
app.get('/api/image/:key(*)', authenticateToken, (req, res) => {
  const { key } = req.params;
  const decodedKey = decodeURIComponent(key);
  
  const params = {
    Bucket: S3_BUCKET,
    Key: decodedKey,
    Expires: 300
  };
  
  const downloadUrl = s3.getSignedUrl('getObject', params);
  res.json({ downloadUrl });
});

// Get all posts
app.get('/api/posts', authenticateToken, async (req, res) => {
  try {
    const params = {
      TableName: TABLE_NAME
    };
    
    const result = await dynamodb.scan(params).promise();
    const posts = result.Items.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    res.json(posts);
  } catch (error) {
    console.error('Error fetching posts:', error);
    res.status(500).json({ error: 'Failed to fetch posts' });
  }
});

// Get single post
app.get('/api/posts/:id', authenticateToken, async (req, res) => {
  try {
    const params = {
      TableName: TABLE_NAME,
      Key: { id: req.params.id }
    };
    
    const result = await dynamodb.get(params).promise();
    if (result.Item) {
      res.json(result.Item);
    } else {
      res.status(404).json({ error: 'Post not found' });
    }
  } catch (error) {
    console.error('Error fetching post:', error);
    res.status(500).json({ error: 'Failed to fetch post' });
  }
});

// Create new post
app.post('/api/posts', authenticateToken, upload.single('image'), async (req, res) => {
  try {
    const { title, content, imageKey } = req.body;
    const postId = uuidv4();
    
    let finalImageKey = imageKey;
    
    // Handle direct file upload
    if (req.file && !imageKey) {
      const uploadKey = `images/${postId}-${Date.now()}.${req.file.originalname.split('.').pop()}`;
      
      const s3Params = {
        Bucket: S3_BUCKET,
        Key: uploadKey,
        Body: req.file.buffer,
        ContentType: req.file.mimetype
      };
      
      await s3.upload(s3Params).promise();
      finalImageKey = uploadKey;
    }
    
    // Save post to DynamoDB
    const post = {
      id: postId,
      title,
      content,
      imageKey: finalImageKey,
      author: req.user.email || req.user.username || 'Anonymous',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    const params = {
      TableName: TABLE_NAME,
      Item: post
    };
    
    await dynamodb.put(params).promise();
    res.status(201).json(post);
  } catch (error) {
    console.error('Error creating post:', error);
    res.status(500).json({ error: 'Failed to create post' });
  }
});

// Update post
app.put('/api/posts/:id', authenticateToken, upload.single('image'), async (req, res) => {
  try {
    const { title, content, imageKey } = req.body;
    const postId = req.params.id;
    
    // Get existing post
    const getParams = {
      TableName: TABLE_NAME,
      Key: { id: postId }
    };
    
    const existingPost = await dynamodb.get(getParams).promise();
    if (!existingPost.Item) {
      return res.status(404).json({ error: 'Post not found' });
    }
    
    let finalImageKey = existingPost.Item.imageKey;
    
    // Handle new image upload
    if (req.file) {
      const uploadKey = `images/${postId}-${Date.now()}.${req.file.originalname.split('.').pop()}`;
      
      const s3Params = {
        Bucket: S3_BUCKET,
        Key: uploadKey,
        Body: req.file.buffer,
        ContentType: req.file.mimetype
      };
      
      await s3.upload(s3Params).promise();
      finalImageKey = uploadKey;
    } else if (imageKey) {
      finalImageKey = imageKey;
    }
    
    // Update post in DynamoDB
    const updateParams = {
      TableName: TABLE_NAME,
      Key: { id: postId },
      UpdateExpression: 'SET title = :title, content = :content, imageKey = :imageKey, updatedAt = :updatedAt',
      ExpressionAttributeValues: {
        ':title': title,
        ':content': content,
        ':imageKey': finalImageKey,
        ':updatedAt': new Date().toISOString()
      },
      ReturnValues: 'ALL_NEW'
    };
    
    const result = await dynamodb.update(updateParams).promise();
    res.json(result.Attributes);
  } catch (error) {
    console.error('Error updating post:', error);
    res.status(500).json({ error: 'Failed to update post' });
  }
});

// Delete post
app.delete('/api/posts/:id', authenticateToken, async (req, res) => {
  try {
    const postId = req.params.id;
    
    // Get post to check if image exists
    const getParams = {
      TableName: TABLE_NAME,
      Key: { id: postId }
    };
    
    const existingPost = await dynamodb.get(getParams).promise();
    if (!existingPost.Item) {
      return res.status(404).json({ error: 'Post not found' });
    }
    
    // Delete image from S3 if exists
    if (existingPost.Item.imageKey) {
      const s3Params = {
        Bucket: S3_BUCKET,
        Key: existingPost.Item.imageKey
      };
      
      try {
        await s3.deleteObject(s3Params).promise();
      } catch (s3Error) {
        console.error('Error deleting image from S3:', s3Error);
      }
    }
    
    // Delete post from DynamoDB
    const deleteParams = {
      TableName: TABLE_NAME,
      Key: { id: postId }
    };
    
    await dynamodb.delete(deleteParams).promise();
    res.json({ message: 'Post deleted successfully' });
  } catch (error) {
    console.error('Error deleting post:', error);
    res.status(500).json({ error: 'Failed to delete post' });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    cognito: !!USER_POOL_ID,
    s3Bucket: S3_BUCKET,
    dynamoTable: TABLE_NAME,
    userPoolId: USER_POOL_ID,
    clientId: CLIENT_ID,
    region: process.env.AWS_REGION || 'eu-north-1'
  });
});

// Serve frontend
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Cognito User Pool: ${USER_POOL_ID || 'Not configured'}`);
  console.log(`S3 Bucket: ${S3_BUCKET}`);
  console.log(`DynamoDB Table: ${TABLE_NAME}`);
});
