import fs from 'fs';
import { execSync } from 'child_process';
import { fetchLatestTelemetry } from './telemetryProvider';
import { SwitchStateManager } from './switchState';
import { TelemetryPacket } from '../types/telemetry';

const PIPE_PATH = '/tmp/switch_pipe';
// Continuity voltage threshold - if voltage drops below this, circuit is complete
const CONTINUITY_THRESHOLD = 1.0; // Volts

export class PollingEngine {
  private isRunning: boolean = false;
  private timer: NodeJS.Timeout | null = null;
  private switchManager: SwitchStateManager;
  private pipeFd: number | null = null;

  // Callback function to send data
  private onDataCallback: (packet: TelemetryPacket) => void;

  // Deduplication state tracking
  private lastBroadcastTimestamp: number = 0;
  private lastSwitchStateHash: string = '';
  private totalDuplicatesSkipped: number = 0;
  private totalBroadcasts: number = 0;

  // DEBUG: Poll rate tracking
  private lastPollTime: number = 0;
  private pollCount: number = 0;

  constructor(onData: (packet: TelemetryPacket) => void) {
    this.onDataCallback = onData;
    this.switchManager = new SwitchStateManager();
    this.tryOpenPipe();
  }

  /**
   * Creates the named pipe if needed and opens it for reading.
   * Pipe is created here so it's ready before socket_client.py starts.
   */
  private tryOpenPipe() {
    try {
      if (!fs.existsSync(PIPE_PATH)) {
        execSync(`mkfifo ${PIPE_PATH}`);
        console.log('Created Switch Pipe:', PIPE_PATH);
      }
      // O_RDONLY | O_NONBLOCK is critical for NFR-P2
      this.pipeFd = fs.openSync(PIPE_PATH, fs.constants.O_RDONLY | fs.constants.O_NONBLOCK);
      console.log('Connected to Switch Pipe');
    } catch (err) {
      console.warn('Failed to open pipe (will retry):', err);
    }
  }

  /**
   * Read switch messages without blocking the loop.
   */
  private readPipe() {
    if (this.pipeFd === null) {
      // Try to reconnect periodically if pipe was missing
      this.tryOpenPipe();
      return;
    }

    try {
      const buffer = Buffer.alloc(1024); // Small buffer for speed
      const bytesRead = fs.readSync(this.pipeFd, buffer, 0, 1024, null);
      
      if (bytesRead > 0) {
        const data = buffer.toString('utf8', 0, bytesRead);
        // Pipe might send multiple messages separated by newline
        const messages = data.split('\n');
        messages.forEach(msg => this.switchManager.parseAndUpdate(msg));
      }
    } catch (err: any) {
      // Handle EAGAIN (Resource temporarily unavailable) - means no data waiting
      if (err.code === 'EAGAIN' || err.code === 'EWOULDBLOCK') {
        return; 
      }
      console.error('Pipe Read Error:', err.message);
      // If pipe broke, close fd so we try to reopen next time
      try { fs.closeSync(this.pipeFd!); } catch {}
      this.pipeFd = null;
    }
  }

  /**
   * The Self-Correcting 60Hz Loop
   */
  public start() {
    if (this.isRunning) return;
    this.isRunning = true;
    console.log('Polling Engine Started (60Hz Target)');
    this.tick();
  }

  public stop() {
    this.isRunning = false;
    if (this.timer) clearTimeout(this.timer);
    if (this.pipeFd) fs.closeSync(this.pipeFd);
  }

  /**
   * Get deduplication statistics for monitoring
   */
  public getStats() {
    return {
      broadcastCount: this.totalBroadcasts,
      duplicateCount: this.totalDuplicatesSkipped,
      lastTimestamp: this.lastBroadcastTimestamp,
    };
  }

  private async tick() {
    if (!this.isRunning) return;

    const startTime = performance.now();

    // DEBUG: Track actual poll rate
    this.pollCount++;
    if (this.pollCount % 60 === 0) {
      const now = performance.now();
      if (this.lastPollTime > 0) {
        const actualHz = 60 / ((now - this.lastPollTime) / 1000);
        console.log(`[Poll Rate] Actual: ${actualHz.toFixed(1)} Hz (target: 60 Hz)`);
      }
      this.lastPollTime = now;
    }

    // 1. Read Switches (Fast, Synchronous, Non-blocking)
    this.readPipe();

    // 2. Fetch Telemetry (Async DB Query)
    const queryStart = performance.now();
    const telemetryRow = await fetchLatestTelemetry();
    const queryTime = performance.now() - queryStart;

    // DEBUG: Log query performance every 60 polls (~1 second)
    if (this.pollCount % 60 === 0) {
      console.log(`[Query Perf] Took ${queryTime.toFixed(2)}ms | Timestamp: ${telemetryRow?.timestamp || 'null'}`);
      console.log(`[Continuity] raw=${telemetryRow?.continuity_raw} type=${typeof telemetryRow?.continuity_raw} result=${telemetryRow?.continuity_raw != null ? telemetryRow.continuity_raw < CONTINUITY_THRESHOLD : 'skipped'}`);
      console.log(`[Dedup Stats] Broadcasts: ${this.totalBroadcasts} | Skipped: ${this.totalDuplicatesSkipped}`);
    }

    // 3. Get current switch state (always, even if no telemetry)
    const currentSwitches = this.switchManager.getState();

    // Override continuity based on telemetry voltage threshold (if available)
    if (telemetryRow && telemetryRow.continuity_raw != null) {
      currentSwitches.continuity = telemetryRow.continuity_raw < CONTINUITY_THRESHOLD;
    }

    // SAFETY: If abort is engaged, turn off all valves and launch key
    if (currentSwitches.abort === true) {
      // Check if this is the first time abort is engaged (to log once)
      const wasAbortEngaged = this.lastSwitchStateHash.includes('"abort":true');
      if (!wasAbortEngaged) {
        console.log('🚨 ABORT ENGAGED - Forcing all switches and launch key to OFF');
      }

      currentSwitches.switch1 = false;
      currentSwitches.switch2 = false;
      currentSwitches.switch3 = false;
      currentSwitches.switch4 = false;
      currentSwitches.switch5 = false;
      currentSwitches.switch6 = false;
      currentSwitches.switch7 = false;
      currentSwitches.switch8 = false;
      currentSwitches.switch9 = false;
      currentSwitches.switch10 = false;
      currentSwitches.launchKey = false;
    }

    const currentSwitchHash = JSON.stringify(currentSwitches);

    // 4. Check what changed
    const telemetryChanged = telemetryRow && (telemetryRow.timestamp.getTime() !== this.lastBroadcastTimestamp);
    const switchesChanged = currentSwitchHash !== this.lastSwitchStateHash;

    // 5. Broadcast if EITHER telemetry OR switches changed
    if (telemetryChanged || switchesChanged) {
      // Update tracking state
      if (telemetryRow) {
        this.lastBroadcastTimestamp = telemetryRow.timestamp.getTime();
      }
      this.lastSwitchStateHash = currentSwitchHash;

      // Build and broadcast packet
      const packet: TelemetryPacket = {
        timestamp: telemetryRow ? telemetryRow.timestamp.getTime() : this.lastBroadcastTimestamp,
        telemetry: telemetryRow ? [
          // IDs mirror database column names exactly
          { id: 'pt1', value: telemetryRow.pt1 },
          { id: 'pt2', value: telemetryRow.pt2 },
          { id: 'pt3', value: telemetryRow.pt3 },
          { id: 'pt4', value: telemetryRow.pt4 },
          { id: 'pt5', value: telemetryRow.pt5 },
          { id: 'pt6', value: telemetryRow.pt6 },
          { id: 'pt7', value: telemetryRow.pt7 },
          { id: 'pt8', value: telemetryRow.pt8 },
          { id: 'pt9', value: telemetryRow.pt9 },
          { id: 'pt25', value: telemetryRow.pt25 },
          { id: 'lc1', value: telemetryRow.lc1 },
          { id: 'lc2', value: telemetryRow.lc2 },
          { id: 'lc3', value: telemetryRow.lc3 },
          { id: 'lc4', value: telemetryRow.lc4 },
          { id: 'lc_net_force', value: telemetryRow.lc_net_force },
          { id: 'tc1', value: telemetryRow.tc1 },
          { id: 'tc2', value: telemetryRow.tc2 },
        ] : [],
        switches: currentSwitches,
      };

      this.onDataCallback(packet);
      this.totalBroadcasts++;
    } else {
      // Skip duplicate - neither telemetry nor switches changed
      this.totalDuplicatesSkipped++;
    }

    // 6. Calculate Drift & Schedule Next
    const endTime = performance.now();
    const executionTime = endTime - startTime;
    const targetInterval = 16.67; // 60Hz

    // If we took 5ms, wait 11.67ms. If we took 20ms, wait 0ms (run immediately).
    const nextDelay = Math.max(0, targetInterval - executionTime);

    this.timer = setTimeout(() => this.tick(), nextDelay);
  }
}