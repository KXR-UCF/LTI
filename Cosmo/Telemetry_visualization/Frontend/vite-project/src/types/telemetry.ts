/**
 * Represents a single sensor reading from the backend.
 */
export interface TelemetryDataPoint {
    id: string;   // e.g. "PT-01", "LC-Net"
    value: number;
  }
  
  /**
   * Represents the state of switches (key-value pair).
   */

  export interface SwitchState {
    switch1: boolean;
    switch2: boolean;
    switch3: boolean;
    switch4: boolean;
    switch5: boolean;
    switch6: boolean;
    switch7: boolean;
    switch8: boolean;
    switch9: boolean;
    switch10: boolean;
    continuity: boolean;
    launchKey: boolean;
    abort: boolean;
    [key: string]: boolean; // Keep index signature for dynamic access if needed e.g. { switch1: true, launchKey: false }
  }
  
  /**
   * The Full Packet coming from WebSocket.
   */
  export interface TelemetryPacket {
    timestamp: number; // Unix Timestamp (ms) from QuestDB
    telemetry: TelemetryDataPoint[];
    switches: SwitchState;
  }