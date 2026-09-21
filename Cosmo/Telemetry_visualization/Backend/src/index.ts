import 'dotenv/config';
import { checkConnection } from './db/client';
import { PollingEngine } from './services/pollingEngine';
import { TelemetryPacket } from './types/telemetry';
import { WebSocketManager } from './services/socketServer';

const WS_PORT = 3001;

async function main() {
  console.log('Starting Backend Service...');

  // 1. Verify DB Connection
  try {
    await checkConnection();
  } catch (err) {
    console.error('Fatal: Could not connect to Database. Exiting.');
    process.exit(1);
  }

  // 2. Initialize WebSocket Server
  const wsManager = new WebSocketManager(WS_PORT);

  // 3. Initialize Polling Engine with Broadcast Callback
  const engine = new PollingEngine((packet: TelemetryPacket) => {
    // Broadcast the packet to all connected Frontend clients
    wsManager.broadcast(packet);
  });

  // 3b. Heartbeat Monitor - Print status every 5 seconds
  setInterval(() => {
    const stats = engine.getStats();
    const efficiency = stats.broadcastCount > 0
      ? ((stats.broadcastCount / (stats.broadcastCount + stats.duplicateCount)) * 100).toFixed(1)
      : 100;
    console.log(
      `[${new Date().toISOString()}] 💓 Heartbeat | ` +
      `Broadcasts: ${stats.broadcastCount} | ` +
      `Skipped: ${stats.duplicateCount} | ` +
      `Efficiency: ${efficiency}%`
    );
  }, 5000);

  // 4. Start the Loop
  engine.start();

  // 5. Graceful Shutdown
  const shutdown = () => {
    console.log('\nShutting down...');
    engine.stop();
    wsManager.close();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

main().catch((err) => {
  console.error('Unhandled Exception:', err);
  process.exit(1);
});