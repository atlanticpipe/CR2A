import express from 'express';
import path from 'path';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static('public'));
app.use(express.static('frontend/dist')); // Adjust path to your built frontend

// CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});

// Security headers
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
});

// API routes (if you have any)
// import apiRoutes from './routes/api.js';
// app.use('/api', apiRoutes);

// SPA fallback - IMPORTANT: This sends index.html for all non-file routes
app.get('*', (req, res) => {
  // Check if the request is for a file (has an extension)
  if (path.extname(req.path) !== '') {
    res.status(404).send('Not found');
  } else {
    // Send index.html for all routes without file extensions
    res.sendFile(path.join(__dirname, 'frontend/dist/index.html'));
    // OR if your frontend is in a different location:
    // res.sendFile(path.join(__dirname, 'public/index.html'));
  }
});

app.listen(PORT, () => {
  console.log(`🚀 CR2A Server running on http://localhost:${PORT}`);
});