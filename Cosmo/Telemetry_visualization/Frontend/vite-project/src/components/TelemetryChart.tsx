// src/components/TelemetryChart.tsx
import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import { SensorConfig } from '../types/config';
import { cn } from '@/lib/utils';
import { useTheme } from 'next-themes';

interface TelemetryChartProps {
  config: SensorConfig;
  className?: string;
}

export interface ChartHandle {
  addDataPoint: (timestamp: number, value: number) => void;
  reset: () => void;
  setRecordingState: (state: 'idle' | 'armed' | 'recording' | 'stopped') => void;
}

export const TelemetryChart = forwardRef<ChartHandle, TelemetryChartProps>(
  ({ config, className }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const uplotRef = useRef<uPlot | null>(null);
    const statsRef = useRef<HTMLDivElement>(null);
    const { theme } = useTheme();
    const isDark = theme === 'dark';

    // Ring Buffer Configuration (power of 2 for efficient masking)
    const CAPACITY = 8192; // Must be power of 2
    const MASK = CAPACITY - 1; // 8191 - for fast modulo via bitwise AND
    const MAX_VISIBLE = 5000; // Keep last 5000 points visible

    // Ring Buffer Storage (fixed-size arrays, reused for entire lifecycle)
    const timesRingRef = useRef<number[]>(new Array(CAPACITY).fill(0));
    const valuesRingRef = useRef<number[]>(new Array(CAPACITY).fill(0));
    const readIndexRef = useRef<number>(0);   // Unmasked - grows forever
    const writeIndexRef = useRef<number>(0);  // Unmasked - grows forever

    // View arrays for uPlot (extracted from ring buffer)
    const dataRef = useRef<[number[], number[]]>([[], []]);
    const peakRef = useRef<number>(-Infinity);
    const recordingStateRef = useRef<'idle' | 'armed' | 'recording' | 'stopped'>('idle');

    // Performance tracking
    const perfCounterRef = useRef<number>(0);
    const perfTotalTimeRef = useRef<number>(0);

    // Refs for stats bar elements (performance optimization - avoid innerHTML)
    const statsLabelRef = useRef<HTMLSpanElement>(null);
    const statsValueRef = useRef<HTMLSpanElement>(null);
    const statsPeakRef = useRef<HTMLSpanElement>(null);

    // Initialize uPlot
    useEffect(() => {
      if (!containerRef.current) return;

      // Calculate proper dimensions
      const containerWidth = containerRef.current.clientWidth;
      const containerHeight = containerRef.current.clientHeight;

      const opts: uPlot.Options = {
        id: config.id,
        class: 'uplot-chart',
        width: containerWidth,
        height: containerHeight,
        padding: [25, 15, 0, 0], // [top, right, bottom, left] - increased top padding to prevent cutoff
        series: [
          {}, // X-Axis (Time)
          {
            // Y-Axis (Value)
            show: true,
            spanGaps: true,  // Interpolate over gaps to prevent jagged lines
            stroke: config.color,
            width: 2,
            points: { show: false },
          },
        ],
        axes: [
          {
            // X-Axis (Bottom)
            side: 2, // 0=top, 1=right, 2=bottom, 3=left
            stroke: isDark ? '#94a3b8' : '#475569',
            grid: {
              show: true,
              stroke: isDark ? '#64748b' : '#cbd5e1',
              width: 1
            },
            ticks: {
              show: true,
              stroke: isDark ? '#64748b' : '#94a3b8',
              width: 1,
              size: 4
            },
            splits: (u) => {
              const min = u.scales.x.min || 0;
              const max = u.scales.x.max || 30;
              const range = max - min;

              // Determine interval based on range
              let interval = 5;
              if (range > 100) interval = 20;
              else if (range > 50) interval = 10;
              else if (range > 20) interval = 5;
              else if (range > 10) interval = 2;
              else interval = 1;

              const splits = [];
              const start = Math.floor(min / interval) * interval;
              for (let i = start; i <= max; i += interval) {
                if (i >= min) splits.push(i);
              }
              return splits;
            },
            values: (_u, vals) => vals.map(v => Math.round(v) + 's'),
            font: '10px monospace',
            size: 30,
            gap: 5,
            space: 50,
          },
          {
            // Y-Axis (Left)
            side: 3,
            stroke: isDark ? '#94a3b8' : '#475569',
            grid: {
              show: true,
              stroke: isDark ? '#64748b' : '#cbd5e1',
              width: 1
            },
            ticks: {
              show: true,
              stroke: isDark ? '#64748b' : '#94a3b8',
              width: 1,
              size: 4
            },
            splits: (u) => {
              const min = u.scales.y.min || 0;
              const max = u.scales.y.max || 1000;
              const range = max - min;

              // Determine nice interval (now handles decimal values)
              let interval = 100;
              if (range > 5000) interval = 1000;
              else if (range > 2000) interval = 500;
              else if (range > 1000) interval = 200;
              else if (range > 500) interval = 100;
              else if (range > 200) interval = 50;
              else if (range > 100) interval = 25;
              else if (range > 10) interval = 10;
              else if (range > 5) interval = 5;
              else if (range > 2) interval = 1;
              else if (range > 1) interval = 0.5;
              else if (range > 0.5) interval = 0.1;
              else if (range > 0.1) interval = 0.05;
              else if (range > 0.05) interval = 0.01;
              else if (range > 0.01) interval = 0.005;
              else interval = 0.001;

              const splits = [];
              const start = Math.floor(min / interval) * interval;
              // Only include splits within the actual min/max range
              for (let i = start; i <= max; i += interval) {
                if (i >= min && i <= max) {
                  splits.push(Number(i.toFixed(10))); // Fix floating point precision
                }
              }
              return splits;
            },
            values: (_u, vals) => vals.map(v => {
              // Smart formatting based on value magnitude
              if (Math.abs(v) >= 100) return Math.round(v).toLocaleString();
              if (Math.abs(v) >= 1) return v.toFixed(1);
              if (Math.abs(v) >= 0.1) return v.toFixed(2);
              if (Math.abs(v) >= 0.01) return v.toFixed(3);
              // For very small values or zero, show as integer
              if (v === 0) return '0';
              return v.toFixed(4);
            }),
            font: '10px monospace',
            size: 50,
            gap: 5,
          },
        ],
        scales: {
          x: {
            time: false,
            range: (_u, min, max) => {
              // If stopped, allow free panning (no auto-range)
              if (recordingStateRef.current === 'stopped') {
                return [min, max];
              }

              // Show 0-30 seconds by default when no data
              if (max === undefined || max === null || max === min) {
                return [0, 30];
              }

              // 30-second rolling window during live monitoring
              if (max <= 30) {
                return [0, 30];
              } else {
                return [max - 30, max]; // Sliding window
              }
            }
          },
          y: config.domain
            ? {
                range: (_u, min, max) => {
                  const [domainMin, domainMax] = config.domain as [number, number];

                  // If no data yet, use configured domain
                  if (min === undefined || max === undefined || min === null || max === null || min === max) {
                    return [domainMin, domainMax];
                  }

                  // If data exceeds configured domain, auto-expand with padding
                  if (min < domainMin || max > domainMax) {
                    const range = max - min;
                    const padding = range * 0.3;
                    return [Math.min(min - padding, domainMin), Math.max(max + padding, domainMax)];
                  }

                  // Otherwise use configured domain
                  return [domainMin, domainMax];
                }
              }
            : {
                range: (_u, min, max) => {
                  // Show 0-1 by default when no data (better for small decimal values)
                  if (max === undefined || max === null || max === min) {
                    return [0, 1];
                  }

                  // Auto-scale with 30% padding for better visualization
                  const range = max - min;
                  const padding = range * 0.3;

                  // Ensure minimum range to avoid too-tight scaling
                  const minRange = Math.max(range * 0.3, 0.01);
                  const finalMin = min - Math.max(padding, minRange);
                  const finalMax = max + Math.max(padding, minRange);

                  return [finalMin, finalMax];
                }
              },
        },
        cursor: {
          drag: {
            x: true,
            y: true,
            uni: 50, // Minimum pixels to drag before panning
          },
          points: {
            show: true,
            size: 6,
            width: 2,
            stroke: config.color,
            fill: isDark ? '#1e293b' : '#ffffff',
          },
        },
        // Enable scroll wheel zoom
        plugins: [
          {
            hooks: {
              ready: [
                (u) => {
                  const over = u.over;
                  const wheelHandler = (e: WheelEvent) => {
                    e.preventDefault();

                    const { left, top } = u.cursor;
                    if (left === undefined || top === undefined) return;

                    const factor = e.deltaY < 0 ? 0.9 : 1.1;
                    const xVal = u.posToVal(left, 'x');
                    const yVal = u.posToVal(top, 'y');

                    const xMin = u.scales.x.min!;
                    const xMax = u.scales.x.max!;
                    const yMin = u.scales.y.min!;
                    const yMax = u.scales.y.max!;

                    const xRange = xMax - xMin;
                    const yRange = yMax - yMin;

                    const newXRange = xRange * factor;
                    const newYRange = yRange * factor;

                    const newXMin = xVal - (xVal - xMin) * (newXRange / xRange);
                    const newXMax = xVal + (xMax - xVal) * (newXRange / xRange);
                    const newYMin = yVal - (yVal - yMin) * (newYRange / yRange);
                    const newYMax = yVal + (yMax - yVal) * (newYRange / yRange);

                    u.batch(() => {
                      u.setScale('x', { min: newXMin, max: newXMax });
                      u.setScale('y', { min: newYMin, max: newYMax });
                    });
                  };

                  over.addEventListener('wheel', wheelHandler, { passive: false });

                  return () => {
                    over.removeEventListener('wheel', wheelHandler);
                  };
                }
              ]
            }
          }
        ],
        legend: { show: false }, // We use custom stats overlay instead
        hooks: {
          setCursor: [
            (u) => {
              // Update stats bottom bar on cursor hover
              if (!config.showStats || !statsValueRef.current) return;

              const idx = u.cursor.idx;

              // If cursor is active and hovering over data
              if (idx !== null && idx !== undefined) {
                const time = u.data[0][idx];
                const value = u.data[1][idx];

                if (time !== undefined && value !== undefined && value !== null) {
                  // Update only the value and peak text (fast textContent update)
                  statsValueRef.current.textContent = `${value.toFixed(1)} ${config.unit} @ ${time.toFixed(1)}s`;
                  statsPeakRef.current!.textContent = `PEAK: ${peakRef.current.toFixed(1)}`;
                }
              }
            }
          ],
          setSelect: [
            (_u) => {
              // When cursor leaves, show latest live value
              if (!config.showStats || !statsValueRef.current) return;

              const [times, values] = dataRef.current;
              if (times.length === 0) return;

              const latestValue = values[values.length - 1];

              if (latestValue !== null && latestValue !== undefined) {
                // Update only the value and peak text (fast textContent update)
                statsValueRef.current.textContent = `${latestValue.toFixed(1)} ${config.unit}`;
                statsPeakRef.current!.textContent = `PEAK: ${peakRef.current.toFixed(1)}`;
              }
            }
          ],
        },
      };

      const u = new uPlot(opts, dataRef.current, containerRef.current);
      uplotRef.current = u;

      // Handle Resize
      const observer = new ResizeObserver(() => {
        if (containerRef.current && uplotRef.current) {
          const width = containerRef.current.clientWidth;
          const height = containerRef.current.clientHeight;
          if (width > 0 && height > 0) {
            uplotRef.current.setSize({ width, height });
          }
        }
      });
      observer.observe(containerRef.current);

      return () => {
        observer.disconnect();
        u.destroy();
      };
    }, [config, isDark]);

    // Expose methods to parent
    useImperativeHandle(ref, () => ({
      addDataPoint: (time: number, value: number) => {
        if (!uplotRef.current) return;

        // Validate inputs
        if (time === undefined || time === null || value === undefined || value === null || isNaN(value)) {
          console.warn(`[${config.id}] Invalid data point: time=${time}, value=${value}`);
          return;
        }

        const perfStart = performance.now();

        // --- RING BUFFER OPERATIONS (O(1)) ---

        // Write to ring buffer at masked position
        timesRingRef.current[writeIndexRef.current & MASK] = time;
        valuesRingRef.current[writeIndexRef.current & MASK] = value;
        writeIndexRef.current++; // Unmasked - grows forever

        // If buffer exceeds max visible, advance read pointer
        if (writeIndexRef.current - readIndexRef.current > MAX_VISIBLE) {
          readIndexRef.current++;
        }

        // --- EXTRACT VIEW FOR UPLOT (O(n) but no shift overhead) ---

        const size = writeIndexRef.current - readIndexRef.current;
        const times = dataRef.current[0];
        const values = dataRef.current[1];

        // Resize view arrays if needed (reuse existing arrays when possible)
        if (times.length !== size) {
          times.length = size;
          values.length = size;
        }

        // Copy valid data from ring buffer to view arrays
        for (let i = 0; i < size; i++) {
          const ringIdx = (readIndexRef.current + i) & MASK;
          times[i] = timesRingRef.current[ringIdx];
          values[i] = valuesRingRef.current[ringIdx];
        }

        uplotRef.current.setData(dataRef.current);

        // Performance tracking
        const perfEnd = performance.now();
        const elapsed = perfEnd - perfStart;
        perfTotalTimeRef.current += elapsed;
        perfCounterRef.current++;

        // Log performance every 60 calls (~1 second at 60Hz)
        if (perfCounterRef.current % 60 === 0) {
          const avgTime = perfTotalTimeRef.current / 60;
          console.log(`[${config.id}] RING BUFFER PERF: avg=${avgTime.toFixed(3)}ms per addDataPoint (${size} points)`);
          perfTotalTimeRef.current = 0;
        }

        // Update Stats Bottom Bar
        if (config.showStats && statsValueRef.current) {
          if (value > peakRef.current) peakRef.current = value;

          // Fast textContent updates (no HTML parsing, 10-100x faster than innerHTML)
          statsValueRef.current.textContent = `${value.toFixed(1)} ${config.unit}`;
          statsPeakRef.current!.textContent = `PEAK: ${peakRef.current.toFixed(1)}`;
        }
      },

      reset: () => {
        // Reset ring buffer indices (O(1) - no array clearing needed)
        readIndexRef.current = 0;
        writeIndexRef.current = 0;

        // Clear view arrays
        dataRef.current = [[], []];
        peakRef.current = -Infinity;
        perfCounterRef.current = 0;
        perfTotalTimeRef.current = 0;

        uplotRef.current?.setData(dataRef.current);
        if (statsValueRef.current) {
          // Fast textContent updates (no HTML parsing)
          statsValueRef.current.textContent = 'WAITING FOR DATA...';
          statsPeakRef.current!.textContent = '';
        }
      },

      setRecordingState: (state: 'idle' | 'armed' | 'recording' | 'stopped') => {
        recordingStateRef.current = state;
        // Force chart to re-evaluate scales
        if (uplotRef.current) {
          uplotRef.current.redraw();
        }
      }
    }));

    return (
      <div className={cn("relative bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden flex flex-col", className)}>
        {/* uPlot Container - flex-1 to fill available space */}
        <div ref={containerRef} className="flex-1 min-h-0" />

        {/* Combined Title + Stats Bottom Bar */}
        {config.showStats && (
          <div
            ref={statsRef}
            className="border-t border-slate-200 dark:border-slate-800 px-2 py-1.5 flex justify-between items-center gap-3 bg-slate-50 dark:bg-slate-900/30"
          >
            <span
              ref={statsLabelRef}
              className="text-sm font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wide flex-shrink-0"
            >
              {config.label}
            </span>
            <span
              ref={statsValueRef}
              className="font-mono text-sm font-bold flex-1 text-center"
              style={{ color: config.color }}
            >
              WAITING FOR DATA...
            </span>
            <span
              ref={statsPeakRef}
              className="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0"
            >
            </span>
          </div>
        )}
      </div>
    );
  }
);

TelemetryChart.displayName = 'TelemetryChart';
