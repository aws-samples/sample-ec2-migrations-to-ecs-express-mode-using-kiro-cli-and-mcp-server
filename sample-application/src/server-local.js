const express = require('express');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// In-memory storage for local testing
let posts = [];

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));
app.use('/uploads', express.static('uploads'));

// Multer configuration for local file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    const uniqueName = `${Date.now()}-${Math.round(Math.random() * 1E9)}.${file.originalname.split('.').pop()}`;
    cb(null, uniqueName);
  }
});

const upload = multer({ storage: storage });

// Routes

// Get all posts
app.get('/api/posts', (req, res) => {
  res.json(posts.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)));
});

// Get single post
app.get('/api/posts/:id', (req, res) => {
  const post = posts.find(p => p.id === req.params.id);
  if (post) {
    res.json(post);
  } else {
    res.status(404).json({ error: 'Post not found' });
  }
});

// Create new post
app.post('/api/posts', upload.single('image'), (req, res) => {
  const { title, content } = req.body;
  const postId = uuidv4();
  
  let imageUrl = null;
  if (req.file) {
    imageUrl = `/uploads/${req.file.filename}`;
  }
  
  const post = {
    id: postId,
    title,
    content,
    imageUrl,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
  
  posts.push(post);
  res.status(201).json(post);
});

// Update post
app.put('/api/posts/:id', upload.single('image'), (req, res) => {
  const { title, content } = req.body;
  const postIndex = posts.findIndex(p => p.id === req.params.id);
  
  if (postIndex === -1) {
    return res.status(404).json({ error: 'Post not found' });
  }
  
  let imageUrl = posts[postIndex].imageUrl;
  
  // Handle new image upload
  if (req.file) {
    // Delete old image if exists
    if (imageUrl && imageUrl.startsWith('/uploads/')) {
      const oldImagePath = path.join(__dirname, '..', imageUrl);
      if (fs.existsSync(oldImagePath)) {
        fs.unlinkSync(oldImagePath);
      }
    }
    imageUrl = `/uploads/${req.file.filename}`;
  }
  
  posts[postIndex] = {
    ...posts[postIndex],
    title,
    content,
    imageUrl,
    updatedAt: new Date().toISOString()
  };
  
  res.json(posts[postIndex]);
});

// Delete post
app.delete('/api/posts/:id', (req, res) => {
  const postIndex = posts.findIndex(p => p.id === req.params.id);
  
  if (postIndex === -1) {
    return res.status(404).json({ error: 'Post not found' });
  }
  
  const post = posts[postIndex];
  
  // Delete image file if exists
  if (post.imageUrl && post.imageUrl.startsWith('/uploads/')) {
    const imagePath = path.join(__dirname, '..', post.imageUrl);
    if (fs.existsSync(imagePath)) {
      fs.unlinkSync(imagePath);
    }
  }
  
  posts.splice(postIndex, 1);
  res.json({ message: 'Post deleted successfully' });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    posts_count: posts.length 
  });
});

// Serve frontend
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
  console.log(`📝 Blog app ready for testing!`);
});
