import { WebSocket, WebSocketServer } from 'ws';
import { TelemetryPacket } from '../types/telemetry';

export class WebSocketManager {
  private wss: WebSocketServer;

  constructor(port: number) {
    // Bind to localhost only for security
    this.wss = new WebSocketServer({ port, host: '127.0.0.1' });

    console.log(`WebSocket Server started on ws://127.0.0.1:${port}`);

    this.setupListeners();
  }

  private setupListeners() {
    this.wss.on('connection', (ws: WebSocket) => {
      console.log('Client Connected');

      ws.on('error', (err) => {
        console.error('Client Socket Error:', err.message);
      });

      ws.on('close', () => {
        console.log('Client Disconnected');
      });
    });

    this.wss.on('error', (err) => {
      console.error('WebSocket Server Error:', err.message);
    });
  }

  /**
   * Broadcast telemetry packet to all connected clients.
   * This operation is fire-and-forget.
   */
  public broadcast(packet: TelemetryPacket): void {
    const payload = JSON.stringify(packet);

    this.wss.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(payload);
        } catch (err) {
          console.error('Failed to send to client:', err);
        }
      }
    });
  }

  public close(): void {
    this.wss.close(() => {
      console.log('WebSocket Server Closed');
    });
  }
}