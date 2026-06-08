const express = require('express');
const rateLimit = require('express-rate-limit');
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, ScanCommand, GetCommand, PutCommand, UpdateCommand, DeleteCommand } = require('@aws-sdk/lib-dynamodb');
const { S3Client, PutObjectCommand, DeleteObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');
const multer = require('multer');
const { randomUUID: uuidv4 } = require('crypto');
const crypto = require('crypto');
const cors = require('cors');
const path = require('path');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const REGION = process.env.AWS_REGION || 'ap-southeast-1';

// AWS SDK v3 clients (credential chain is automatic, supports Pod Identity natively)
const dynamoClient = new DynamoDBClient({ region: REGION });
const dynamodb = DynamoDBDocumentClient.from(dynamoClient);
const s3 = new S3Client({ region: REGION });

const TABLE_NAME = process.env.DYNAMODB_TABLE || 'blog-posts';
const S3_BUCKET = process.env.S3_BUCKET || 'blog-images-bucket';
const USER_POOL_ID = process.env.COGNITO_USER_POOL_ID;
const CLIENT_ID = process.env.COGNITO_CLIENT_ID;

let jwks = null;

// Middleware
const apiLimiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 100, standardHeaders: true, legacyHeaders: false });
app.use('/api/', apiLimiter);
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const storage = multer.memoryStorage();
const upload = multer({ storage });

// Get JWKS using native fetch (no axios needed)
async function getJWKS() {
  if (!jwks && USER_POOL_ID) {
    try {
      const res = await fetch(`https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}/.well-known/jwks.json`);
      jwks = await res.json();
    } catch (error) {
      console.error('Failed to get JWKS:', error.message);
    }
  }
  return jwks;
}

// Convert JWK to PEM using native crypto (no jwk-to-pem/elliptic needed)
function jwkToPem(jwk) {
  const keyObject = crypto.createPublicKey({ key: jwk, format: 'jwk' });
  return keyObject.export({ type: 'spki', format: 'pem' });
}

// Verify JWT token
async function verifyToken(token) {
  if (!USER_POOL_ID) return null;
  try {
    const jwksData = await getJWKS();
    if (!jwksData) return null;
    const decoded = jwt.decode(token, { complete: true });
    if (!decoded) return null;
    const jwk = jwksData.keys.find(key => key.kid === decoded.header.kid);
    if (!jwk) return null;
    return jwt.verify(token, jwkToPem(jwk), { algorithms: ['RS256'] });
  } catch (error) {
    console.error('Token verification failed:', error.message);
    return null;
  }
}

// Authentication middleware
async function authenticateToken(req, res, next) {
  if (!USER_POOL_ID) return res.status(500).json({ error: 'Authentication not configured' });
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Access token required' });
  const user = await verifyToken(token);
  if (!user) return res.status(403).json({ error: 'Invalid token' });
  req.user = user;
  next();
}

// Get presigned URL for S3 upload
app.post('/api/upload-url', authenticateToken, async (req, res) => {
  const { fileName, fileType } = req.body;
  const key = `images/${uuidv4()}-${fileName}`;
  const command = new PutObjectCommand({ Bucket: S3_BUCKET, Key: key, ContentType: fileType });
  const uploadUrl = await getSignedUrl(s3, command, { expiresIn: 300 });
  res.json({ uploadUrl, key });
});

// Get presigned URL for S3 download
app.get('/api/image/:key(*)', authenticateToken, async (req, res) => {
  const decodedKey = decodeURIComponent(req.params.key);
  const command = new GetObjectCommand({ Bucket: S3_BUCKET, Key: decodedKey });
  const downloadUrl = await getSignedUrl(s3, command, { expiresIn: 300 });
  res.json({ downloadUrl });
});

// Get all posts
app.get('/api/posts', authenticateToken, async (req, res) => {
  try {
    const result = await dynamodb.send(new ScanCommand({ TableName: TABLE_NAME }));
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
    const result = await dynamodb.send(new GetCommand({ TableName: TABLE_NAME, Key: { id: req.params.id } }));
    if (result.Item) res.json(result.Item);
    else res.status(404).json({ error: 'Post not found' });
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

    if (req.file && !imageKey) {
      const uploadKey = `images/${postId}-${Date.now()}.${req.file.originalname.split('.').pop()}`;
      await s3.send(new PutObjectCommand({ Bucket: S3_BUCKET, Key: uploadKey, Body: req.file.buffer, ContentType: req.file.mimetype }));
      finalImageKey = uploadKey;
    }

    const post = {
      id: postId, title, content, imageKey: finalImageKey,
      author: req.user.email || req.user.username || 'Anonymous',
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()
    };
    await dynamodb.send(new PutCommand({ TableName: TABLE_NAME, Item: post }));
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
    const existingPost = await dynamodb.send(new GetCommand({ TableName: TABLE_NAME, Key: { id: postId } }));
    if (!existingPost.Item) return res.status(404).json({ error: 'Post not found' });

    let finalImageKey = existingPost.Item.imageKey;
    if (req.file) {
      const uploadKey = `images/${postId}-${Date.now()}.${req.file.originalname.split('.').pop()}`;
      await s3.send(new PutObjectCommand({ Bucket: S3_BUCKET, Key: uploadKey, Body: req.file.buffer, ContentType: req.file.mimetype }));
      finalImageKey = uploadKey;
    } else if (imageKey) {
      finalImageKey = imageKey;
    }

    const result = await dynamodb.send(new UpdateCommand({
      TableName: TABLE_NAME, Key: { id: postId },
      UpdateExpression: 'SET title = :title, content = :content, imageKey = :imageKey, updatedAt = :updatedAt',
      ExpressionAttributeValues: { ':title': title, ':content': content, ':imageKey': finalImageKey, ':updatedAt': new Date().toISOString() },
      ReturnValues: 'ALL_NEW'
    }));
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
    const existingPost = await dynamodb.send(new GetCommand({ TableName: TABLE_NAME, Key: { id: postId } }));
    if (!existingPost.Item) return res.status(404).json({ error: 'Post not found' });

    if (existingPost.Item.imageKey) {
      try { await s3.send(new DeleteObjectCommand({ Bucket: S3_BUCKET, Key: existingPost.Item.imageKey })); }
      catch (s3Error) { console.error('Error deleting image from S3:', s3Error); }
    }

    await dynamodb.send(new DeleteCommand({ TableName: TABLE_NAME, Key: { id: postId } }));
    res.json({ message: 'Post deleted successfully' });
  } catch (error) {
    console.error('Error deleting post:', error);
    res.status(500).json({ error: 'Failed to delete post' });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy', timestamp: new Date().toISOString(),
    cognito: !!USER_POOL_ID, s3Bucket: S3_BUCKET, dynamoTable: TABLE_NAME,
    userPoolId: USER_POOL_ID, clientId: CLIENT_ID, region: REGION
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
