import { useState, useRef, useCallback, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { TelemetryPacket, SwitchState } from '../types/telemetry';
import { ChartHandle } from '../components/TelemetryChart';
import { EMAFilter } from '../lib/filters';

const DEFAULT_SWITCHES: SwitchState = {
    switch1: false, switch2: false, switch3: false, switch4: false,
    switch5: false, switch6: false, switch7: false, switch8: false,
    switch9: false, switch10: false,
    continuity: false, launchKey: false, abort: false
  };

// Connect on load
const WS_URL = 'ws://localhost:3001';

export type RecordingState = 'idle' | 'armed' | 'recording' | 'stopped';

// Store telemetry data points with timestamps for freezing capability
export interface StoredDataPoint {
  timestamp: number;
  relativeTime: number;
  telemetryData: { id: string; value: number }[];
}

export function useTelemetry() {
  // --- STATE ---
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  // Stores the latest packet purely for the Switch UI (low frequency updates)
  const [latestPacket, setLatestPacket] = useState<TelemetryPacket | null>(null);
  const [runtimeStr, setRuntimeStr] = useState<string>('00:00:00.00');
  const [filterEnabled, setFilterEnabled] = useState<boolean>(false);
  // Data health state: null = healthy, number = ms since last packet
  const [dataLag, setDataLag] = useState<number | null>(null);
  // Countdown state: holds when countdown is paused
  const [isCountdownHeld, setIsCountdownHeld] = useState<boolean>(false);

  // --- REFS (Performance Critical - No Re-renders) ---
  const startTimeRef = useRef<number | null>(null);
  const recordingStartTimeRef = useRef<number | null>(null);
  const chartRegistry = useRef<Map<string, ChartHandle>>(new Map());
  // Only stores data when RECORDING (not during idle monitoring)
  const recordedDataRef = useRef<StoredDataPoint[]>([]);
  const recordingStateRef = useRef<RecordingState>('idle');
  const filtersRef = useRef<Map<string, EMAFilter>>(new Map());
  const filterEnabledRef = useRef<boolean>(false);
  // Smooth clock: track last packet time for lag detection
  const lastPacketTimeRef = useRef<number | null>(null);
  const clientStartTimeRef = useRef<number | null>(null);
  // Countdown tracking
  const countdownDurationRef = useRef<number>(0); // Total countdown duration in seconds
  const countdownStartTimeRef = useRef<number | null>(null); // When countdown started
  const countdownPausedTimeRef = useRef<number>(0); // Accumulated paused time in ms
  const countdownHeldAtRef = useRef<number | null>(null); // When HOLD was clicked

  // Batching: accumulate data points, flush on animation frame
  const pendingDataRef = useRef<Array<{ id: string; time: number; value: number }>>([]);
  const animationFrameRef = useRef<number | null>(null);

  // Flush pending data to charts (called once per animation frame)
  const flushPendingData = useCallback(() => {
    const batch = pendingDataRef.current;
    if (batch.length === 0) {
      animationFrameRef.current = null;
      return;
    }

    // Update all charts with batched data
    batch.forEach(({ id, time, value }) => {
      const chart = chartRegistry.current.get(id);
      if (chart) {
        chart.addDataPoint(time, value);
      }
    });

    // Clear buffer
    pendingDataRef.current = [];
    animationFrameRef.current = null;
  }, []);

  // --- WEBSOCKET ENGINE ---
  const { readyState } = useWebSocket(WS_URL, {
    shouldReconnect: () => true, // Auto-reconnect
    onMessage: (event) => {
      try {
        const packet: TelemetryPacket = JSON.parse(event.data);

        // DEBUG: Log packet arrival rate
        console.log('Received packet at:', new Date().toISOString(), 'timestamp:', packet.timestamp, 'telemetry points:', packet.telemetry.length);

        // 1. Always update switches
        setLatestPacket(packet);

        // 2. Initialize start time on first packet (for relative time calculation)
        if (startTimeRef.current === null) {
          startTimeRef.current = packet.timestamp;
        }

        // 3. Calculate relative runtime (T+ seconds from first packet)
        const runtime = (packet.timestamp - startTimeRef.current) / 1000;

        // 4. Track last packet time for lag detection
        lastPacketTimeRef.current = Date.now();

        // 5. Mission clock is now updated by smooth interval (see useEffect below)
        // We no longer update it here directly

        // 6. Store telemetry data ONLY when recording (for export/review later)
        if (recordingStateRef.current === 'recording') {
          const dataPoint: StoredDataPoint = {
            timestamp: packet.timestamp,
            relativeTime: runtime,
            telemetryData: packet.telemetry
          };
          recordedDataRef.current.push(dataPoint);
        }

        // 7. BATCH DATA FOR CHARTS - Only if NOT stopped (frozen)
        if (recordingStateRef.current !== 'stopped') {
          packet.telemetry.forEach((point) => {
            let valueToPlot = point.value;

            // Apply filter only if enabled
            if (filterEnabledRef.current) {
              // Get or create filter
              let filter = filtersRef.current.get(point.id);
              if (!filter) {
                filter = new EMAFilter(0.3);
                filtersRef.current.set(point.id, filter);
              }
              // Smooth the value
              valueToPlot = filter.process(point.value);
            }

            // Add to pending batch (don't update chart yet)
            pendingDataRef.current.push({
              id: point.id,
              time: runtime,
              value: valueToPlot
            });
          });

          // Schedule flush if not already scheduled
          if (animationFrameRef.current === null) {
            animationFrameRef.current = requestAnimationFrame(flushPendingData);
          }
        }
      } catch (err) {
        console.error('Telemetry Parse Error:', err);
      }
    }
  });

  // --- SMOOTH MISSION CLOCK + LAG DETECTION + COUNTDOWN ---
  useEffect(() => {
    // T+ Mode: Recording (counting UP)
    if (recordingState === 'recording') {
      // Start client-side timer when recording starts
      if (clientStartTimeRef.current === null) {
        clientStartTimeRef.current = Date.now();
      }

      // Update clock smoothly every 100ms
      const interval = setInterval(() => {
        if (clientStartTimeRef.current !== null) {
          const elapsedSeconds = (Date.now() - clientStartTimeRef.current) / 1000;

          // Format as HH:MM:SS.cs (industry standard)
          const hours = Math.floor(elapsedSeconds / 3600);
          const minutes = Math.floor((elapsedSeconds % 3600) / 60);
          const seconds = Math.floor(elapsedSeconds % 60);
          const centiseconds = Math.floor((elapsedSeconds % 1) * 100);

          const formatted = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(centiseconds).padStart(2, '0')}`;
          setRuntimeStr(formatted);

          // Calculate lag
          if (lastPacketTimeRef.current !== null) {
            const lagMs = Date.now() - lastPacketTimeRef.current;
            setDataLag(lagMs);
          }
        }
      }, 100);

      return () => clearInterval(interval);
    }

    // T- Mode: Armed countdown (counting DOWN)
    if (recordingState === 'armed' && !isCountdownHeld) {
      if (countdownStartTimeRef.current === null) {
        countdownStartTimeRef.current = Date.now();
      }

      const interval = setInterval(() => {
        if (countdownStartTimeRef.current === null) return;

        // Calculate elapsed time (accounting for pauses)
        const elapsed = (Date.now() - countdownStartTimeRef.current - countdownPausedTimeRef.current) / 1000;
        const remaining = Math.max(0, countdownDurationRef.current - elapsed);

        // Format as HH:MM:SS.cs
        const hours = Math.floor(remaining / 3600);
        const minutes = Math.floor((remaining % 3600) / 60);
        const seconds = Math.floor(remaining % 60);
        const centiseconds = Math.floor((remaining % 1) * 100);

        const formatted = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(centiseconds).padStart(2, '0')}`;
        setRuntimeStr(formatted);

        // Auto-switch to T+ recording when countdown reaches zero
        if (remaining <= 0) {
          // Automatically start recording
          startRecording();
        }
      }, 100);

      return () => clearInterval(interval);
    }
  }, [recordingState, isCountdownHeld]);

  // Notify charts when recording state changes
  const notifyChartsOfState = useCallback((state: RecordingState) => {
    chartRegistry.current.forEach((chart) => {
      if ('setRecordingState' in chart) {
        (chart as any).setRecordingState(state);
      }
    });
  }, []);

  // --- CONTROLS ---
  const startArming = useCallback((durationSeconds: number) => {
    // Start T- countdown mode
    countdownDurationRef.current = durationSeconds;
    countdownStartTimeRef.current = Date.now();
    countdownPausedTimeRef.current = 0;
    countdownHeldAtRef.current = null;
    setIsCountdownHeld(false);

    const newState = 'armed';
    recordingStateRef.current = newState;
    setRecordingState(newState);
    notifyChartsOfState(newState);
    console.log('[Countdown] 🎯 ARMED - Countdown started:', durationSeconds, 'seconds');
  }, []);

  const holdCountdown = useCallback(() => {
    if (recordingState !== 'armed' || isCountdownHeld) return;

    countdownHeldAtRef.current = Date.now();
    setIsCountdownHeld(true);
    console.log('[Countdown] ⏸️ HOLD - Countdown paused');
  }, [recordingState, isCountdownHeld]);

  const resumeCountdown = useCallback(() => {
    if (recordingState !== 'armed' || !isCountdownHeld) return;
    if (countdownHeldAtRef.current === null) return;

    // Accumulate the paused time
    const pausedDuration = Date.now() - countdownHeldAtRef.current;
    countdownPausedTimeRef.current += pausedDuration;
    countdownHeldAtRef.current = null;
    setIsCountdownHeld(false);
    console.log('[Countdown] ▶️ RESUME - Countdown resumed');
  }, [recordingState, isCountdownHeld]);

  const abortCountdown = useCallback(() => {
    if (recordingState !== 'armed') return;

    // Reset to idle
    const newState = 'idle';
    recordingStateRef.current = newState;
    setRecordingState(newState);
    setRuntimeStr('00:00:00.00');
    setIsCountdownHeld(false);
    countdownStartTimeRef.current = null;
    countdownPausedTimeRef.current = 0;
    countdownHeldAtRef.current = null;
    notifyChartsOfState(newState);
    console.log('[Countdown] ⏹️ ABORT - Countdown cancelled');
  }, [recordingState]);

  const startRecording = useCallback(() => {
    // Clear all charts and reset to T+0
    chartRegistry.current.forEach((chart) => chart.reset());
    recordedDataRef.current = [];

    // Clear filters
    filtersRef.current.forEach(f => f.reset());
    filtersRef.current.clear();

    // Reset time reference - next packet will be T+0
    startTimeRef.current = null;
    recordingStartTimeRef.current = null;
    clientStartTimeRef.current = null;
    lastPacketTimeRef.current = null;
    setRuntimeStr('00:00:00.00');
    setDataLag(null);

    const newState = 'recording';
    recordingStateRef.current = newState;
    setRecordingState(newState);
    notifyChartsOfState(newState);
    console.log('[Recording] 🔴 START - Recording started, charts reset to T+0');
  }, [notifyChartsOfState]);

  const stopRecording = useCallback(() => {
    const newState = 'stopped';
    recordingStateRef.current = newState;
    setRecordingState(newState);
    notifyChartsOfState(newState);
    console.log('[Recording] ⏹️ STOP - Recording stopped. Saved', recordedDataRef.current.length, 'data points');
  }, [notifyChartsOfState]);

  const resetRecording = useCallback(() => {
    const newState = 'idle';
    recordingStateRef.current = newState;
    setRecordingState(newState);
    setRuntimeStr('00:00:00.00');
    recordingStartTimeRef.current = null;
    startTimeRef.current = null;
    clientStartTimeRef.current = null;
    lastPacketTimeRef.current = null;
    setDataLag(null);
    recordedDataRef.current = [];

    // Clear all uPlot instances
    chartRegistry.current.forEach((chart) => chart.reset());

    // Clear filters
    filtersRef.current.forEach(f => f.reset());
    filtersRef.current.clear();

    // Notify charts to resume rolling window mode
    notifyChartsOfState(newState);
    console.log('[Recording] 🔄 RESET - Reset to idle mode with rolling window');
  }, [notifyChartsOfState]);

  // --- REGISTRY ---
  // This function is passed to SensorGrid -> TelemetryChart
  // It allows the Child Chart to register itself with this Parent Hook
  const registerChart = useCallback((id: string, chart: ChartHandle | null) => {
    if (chart) {
      chartRegistry.current.set(id, chart);
    } else {
      chartRegistry.current.delete(id);
    }
  }, []);

  // --- FILTER CONTROL ---
  const toggleFilter = useCallback((enabled: boolean) => {
    setFilterEnabled(enabled);
    filterEnabledRef.current = enabled;

    // Clear filter state when toggling to ensure clean transition
    if (!enabled) {
      filtersRef.current.forEach(f => f.reset());
    }

    console.log('[Filter]', enabled ? '✅ ENABLED - EMA filtering active' : '❌ DISABLED - Raw values');
  }, []);

  // Cleanup animation frame on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

 const switches: SwitchState = latestPacket ? latestPacket.switches : DEFAULT_SWITCHES;

  return {
    recordingState,
    connectionStatus: readyState === ReadyState.OPEN ? 'Connected' : 'Disconnected',
    switches,
    runtimeStr,
    dataLag,
    isCountdownHeld,
    controls: {
      startArming,
      holdCountdown,
      resumeCountdown,
      abortCountdown,
      startRecording,
      stopRecording,
      resetRecording
    },
    registerChart,
    filterEnabled,
    toggleFilter
  };
}