const express = require('express');
const cors = require('cors');
const axios = require('axios');
const multer = require('multer');
const path = require('path');
const config = require('./config');
const fs = require('fs');

const app = express();
const upload = multer({ dest: 'uploads/' });

app.use(cors());
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
    console.log(`[${new Date().toLocaleTimeString()}] ${req.method} ${req.url}`);
    next();
});

console.log('==================================================');
console.log('   MENDYGO NODE SERVER - INITIALIZING...         ');
console.log('==================================================');

// Proxy health check
app.get('/api/health', async (req, res) => {
    try {
        const response = await axios.get(`${config.PYTHON_BRIDGE_URL}/health`);
        res.json({ server: 'ok', bridge: response.data });
    } catch (error) {
        res.status(500).json({ server: 'ok', bridge: 'offline', error: error.message });
    }
});

// Proxy STT
app.post('/api/stt', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No audio file uploaded' });
        }

        const formData = new FormData();
        const fileContent = fs.readFileSync(req.file.path);
        formData.append('file', new Blob([fileContent]), req.file.originalname);

        const response = await axios.post(`${config.PYTHON_BRIDGE_URL}/stt`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        // Clean up temp file
        fs.unlinkSync(req.file.path);
        res.json(response.data);
    } catch (error) {
        console.error('STT Proxy Error:', error.message);
        res.status(500).json({ error: 'STT Transcription failed' });
    }
});

// Proxy TTS
app.post('/api/tts', async (req, res) => {
    try {
        const { prompt } = req.body;
        const response = await axios.post(`${config.PYTHON_BRIDGE_URL}/tts`, { prompt }, {
            responseType: 'arraybuffer'
        });

        res.set('Content-Type', 'audio/mpeg');
        res.send(response.data);
    } catch (error) {
        console.error('TTS Proxy Error:', error.message);
        res.status(500).json({ error: 'TTS Generation failed' });
    }
});

// Proxy stats
app.get('/api/stats', async (req, res) => {
    try {
        const response = await axios.get(`${config.PYTHON_BRIDGE_URL}/stats`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Proxy suggestions
app.get('/api/suggestions', async (req, res) => {
    try {
        const { user_id } = req.query;
        const response = await axios.get(`${config.PYTHON_BRIDGE_URL}/suggestions`, {
            params: { user_id: user_id || 'tester' }
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Proxy briefing
app.get('/api/briefing', async (req, res) => {
    try {
        const { user_id } = req.query;
        const response = await axios.get(`${config.PYTHON_BRIDGE_URL}/briefing`, {
            params: { user_id: user_id || 'tester' }
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Proxy KPIs
app.get('/api/kpis', async (req, res) => {
    try {
        const response = await axios.get(`${config.PYTHON_BRIDGE_URL}/kpis`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Proxy chat
app.post('/api/chat', async (req, res) => {
    try {
        const response = await axios.post(`${config.PYTHON_BRIDGE_URL}/chat`, req.body);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Ingest file
app.post('/api/ingest', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        const absolutePath = path.resolve(req.file.path);
        const response = await axios.post(`${config.PYTHON_BRIDGE_URL}/ingest`, {
            file_path: absolutePath
        });

        res.json(response.data);
    } catch (error) {
        res.status(500).json({
            error: error.response?.data?.detail || error.message,
            status: 'error'
        });
    }
});

app.post('/api/clear', async (req, res) => {
    try {
        const response = await axios.post(`${config.PYTHON_BRIDGE_URL}/clear`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(config.PORT, () => {
    console.log(`Server running on port ${config.PORT}`);
    console.log(`Proxying to Python Bridge at ${config.PYTHON_BRIDGE_URL}`);
});
