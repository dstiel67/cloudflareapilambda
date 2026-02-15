/**
 * Atom Store API Server
 * 
 * Provides REST API and WebSocket endpoints for failover status updates.
 * Receives updates from Read Flags Service and broadcasts to connected clients.
 */

import express, { Request, Response } from 'express';
import { createServer } from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import cors from 'cors';

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

// Middleware
app.use(cors());
app.use(express.json());

// In-memory store for current failover status
let currentFailoverStatus: Record<string, any> = {};

// Connected WebSocket clients
const clients = new Set<WebSocket>();

/**
 * REST API Endpoints
 */

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    connectedClients: clients.size,
  });
});

// Get current failover status
app.get('/api/failover/status', (req: Request, res: Response) => {
  res.json(currentFailoverStatus);
});

// Update failover status (called by Read Flags Service)
app.post('/api/failover/update', (req: Request, res: Response) => {
  try {
    const updates = req.body;
    
    console.log('Received failover update:', updates);
    
    // Update current status
    currentFailoverStatus = {
      ...currentFailoverStatus,
      ...updates,
    };
    
    // Broadcast to all connected WebSocket clients
    broadcastToClients(currentFailoverStatus);
    
    res.json({
      success: true,
      message: 'Failover status updated',
      updatedApps: Object.keys(updates),
    });
    
  } catch (error) {
    console.error('Error updating failover status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update failover status',
    });
  }
});

// Get failover status for specific app
app.get('/api/failover/status/:appId', (req: Request, res: Response) => {
  const { appId } = req.params;
  const status = currentFailoverStatus[appId];
  
  if (status) {
    res.json(status);
  } else {
    res.status(404).json({
      error: 'App not found',
      appId,
    });
  }
});

/**
 * WebSocket Handling
 */

wss.on('connection', (ws: WebSocket) => {
  console.log('New WebSocket client connected');
  clients.add(ws);
  
  // Send current status to new client
  ws.send(JSON.stringify({
    type: 'initial',
    data: currentFailoverStatus,
  }));
  
  ws.on('close', () => {
    console.log('WebSocket client disconnected');
    clients.delete(ws);
  });
  
  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
    clients.delete(ws);
  });
});

/**
 * Broadcast updates to all connected WebSocket clients
 */
function broadcastToClients(data: any) {
  const message = JSON.stringify({
    type: 'update',
    data,
    timestamp: new Date().toISOString(),
  });
  
  clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
  
  console.log(`Broadcasted update to ${clients.size} clients`);
}

/**
 * Start server
 */
const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
  console.log(`Atom Store API server running on port ${PORT}`);
  console.log(`REST API: http://localhost:${PORT}/api/failover/status`);
  console.log(`WebSocket: ws://localhost:${PORT}/ws/failover`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
