/**
 * Represents a single row of raw telemetry data directly from QuestDB.
 * Data comes from two tables (wanda1 + wanda2) joined by ASOF JOIN.
 */
export interface RawTelemetryRow {
    timestamp: Date;
    // From wanda1 table
    pt1: number;
    pt2: number;
    pt3: number;
    pt4: number;
    pt5: number;
    pt6: number;
    pt7: number;
    pt8: number;
    pt9: number;
    pt25: number;
    continuity_raw: number;
    // From wanda2 table
    lc1: number;
    lc2: number;
    lc3: number;
    lc4: number;
    lc_net_force: number;
    tc1: number;
    tc2: number;
  }

/**
 * Single Source of Truth for Switch Definitions:
 * All states are booleans:
 * - True = Open / ENABLE / Active
 * - False = Close / DISABLE / Inactive
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
    launchKey: boolean;  // True = ENABLE FIRE
    abort: boolean;      // True = ABORT Open
    [key: string]: boolean; // Index signature for dynamic access
  }
  
  export interface TelemetryPacket {
    timestamp: number; // Unix seconds (or ms, frontend handles conversion)
    telemetry: Array<{ id: string; value: number }>;
    switches: SwitchState; // Now strictly typed
  }