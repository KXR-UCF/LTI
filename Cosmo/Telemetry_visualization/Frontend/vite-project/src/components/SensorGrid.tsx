import { DashboardConfig } from '../types/config';
import { TelemetryChart, ChartHandle } from './TelemetryChart';
import { cn } from '@/lib/utils';

interface SensorGridProps {
  config: DashboardConfig;
  registry: (id: string, chart: ChartHandle | null) => void;
}

export function SensorGrid({ config, registry }: SensorGridProps) {
  // Determine grid layout based on number of sensors
  const sensorCount = config.sensors.length;

  // Detect if this is "all" view (17 sensors) for bento box layout
  const isBentoLayout = sensorCount === 17;

  // Section header component
  const SectionHeader = ({ title, row }: { title: string; row: number }) => (
    <div
      className="col-span-5 flex items-center px-2 py-1.5"
      style={{ gridRow: row, gridColumn: '1 / -1' }}
    >
      <div className="text-base font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
        {title}
      </div>
      <div className="flex-1 h-px bg-slate-200 dark:bg-slate-800 ml-3" />
    </div>
  );

  // Explicit grid positioning for bento box (all sensors view)
  // NEW LAYOUT: 5 cols × 9 rows with headers
  const getBentoPosition = (sensorId: string) => {
    const positions: Record<string, string> = {
      // === PRESSURE TRANSDUCERS (Rows 2-3) - 5 per row ===
      'pt1': 'col-start-1 row-start-2 col-span-1 row-span-1',
      'pt2': 'col-start-2 row-start-2 col-span-1 row-span-1',
      'pt3': 'col-start-3 row-start-2 col-span-1 row-span-1',
      'pt4': 'col-start-4 row-start-2 col-span-1 row-span-1',
      'pt5': 'col-start-5 row-start-2 col-span-1 row-span-1',

      'pt6': 'col-start-1 row-start-3 col-span-1 row-span-1',
      'pt7': 'col-start-2 row-start-3 col-span-1 row-span-1',
      'pt8': 'col-start-3 row-start-3 col-span-1 row-span-1',
      'pt9': 'col-start-4 row-start-3 col-span-1 row-span-1',
      'pt25': 'col-start-5 row-start-3 col-span-1 row-span-1',

      // === LOAD CELLS (Rows 5-6) - NET FORCE gets 2×2 hero spot ===
      'lc_net_force': 'col-start-1 row-start-5 col-span-2 row-span-2',  // 2×2 hero (left)
      'lc1': 'col-start-3 row-start-5 col-span-1 row-span-2',           // 1×2 (Nox Tank Wt)
      'lc2': 'col-start-4 row-start-5 col-span-1 row-span-1',           // 1×1 (Thrust 1)
      'lc3': 'col-start-5 row-start-5 col-span-1 row-span-1',           // 1×1 (Thrust 2)
      'lc4': 'col-start-4 row-start-6 col-span-2 row-span-1',           // 2×1 (Thrust 3)

      // === THERMOCOUPLES (Row 8) - span across bottom ===
      'tc1': 'col-start-1 row-start-8 col-span-2 row-span-1',        // 2×1 left
      'tc2': 'col-start-3 row-start-8 col-span-3 row-span-1',        // 3×1 right (larger)
    };

    return positions[sensorId] || 'col-span-1 row-span-1';
  };

  // Determine grid columns for filtered views
  const getGridColumns = () => {
    if (isBentoLayout) return 'grid-cols-5'; // NEW: 5 columns for bento (fits 10 PTs nicely)
    if (sensorCount === 10) return 'grid-cols-5'; // Pressure (5x2 with all 10 PTs)
    if (sensorCount === 5) return 'grid-cols-4'; // Load Cells (4 cols)
    if (sensorCount === 2) return 'grid-cols-2'; // Temperature (2 cols)
    return 'grid-cols-4'; // Default
  };

  // Determine grid rows for filtered views
  const getGridRows = () => {
    // Don't use fractional units - they cause inconsistent sizing on refresh
    return '';
  };

  // Get fixed row heights for filtered views
  const getFilteredRowsStyle = () => {
    if (isBentoLayout) return undefined;
    if (sensorCount === 10) return { gridTemplateRows: 'repeat(2, minmax(400px, 1fr))' }; // Pressure: 2 rows, min 400px, fill space
    if (sensorCount === 5) return { gridTemplateRows: 'repeat(2, minmax(400px, 1fr))' }; // Load Cells: 2 rows, min 400px, fill space
    if (sensorCount === 2) return { gridTemplateRows: 'minmax(400px, 1fr)' }; // Temperature: 1 row, min 400px, fill space
    return undefined;
  };

  // Get positioning for filtered views (simple grids)
  const getFilteredPosition = (sensorId: string) => {
    // Load cells view layout (4 cols x 2 rows)
    if (sensorCount === 5) {
      const positions: Record<string, string> = {
        'lc_net_force': 'col-start-1 row-start-1 col-span-2 row-span-2',      // 2×2 hero (left side)
        'lc1': 'col-start-3 row-start-1 col-span-1 row-span-1',        // Top right (Nox Tank Wt)
        'lc2': 'col-start-4 row-start-1 col-span-1 row-span-1',        // Top far right (Thrust 1)
        'lc3': 'col-start-3 row-start-2 col-span-1 row-span-1',        // Bottom right (Thrust 2)
        'lc4': 'col-start-4 row-start-2 col-span-1 row-span-1',        // Bottom far right (Thrust 3)
      };
      return positions[sensorId] || 'col-span-1 row-span-1';
    }
    // For temperature view, make them larger
    if (sensorCount === 2) {
      return 'col-span-1 row-span-1';
    }
    return 'col-span-1 row-span-1';
  };

  return (
    <div className="p-3 h-full">
      <div
        className={cn(
          "grid gap-3 min-h-full", // Allow all views to grow and scroll
          getGridColumns(),
          getGridRows()
        )}
        style={isBentoLayout ? {
          gridTemplateRows: 'auto 350px 350px auto 280px 280px auto 300px'
          // Row 1: header (auto ~30px)
          // Rows 2-3: PT chart rows (350px each - bigger for better visibility)
          // Row 4: header (auto ~30px)
          // Rows 5-6: Load cell chart rows (280px each - taller, total 560px for 2-row spans)
          // Row 7: header (auto ~30px)
          // Row 8: Thermocouple chart row (300px - taller)
        } : getFilteredRowsStyle()}
      >
        {/* Section Headers - only for All Sensors view */}
        {isBentoLayout && (
          <>
            <SectionHeader title="PRESSURE TRANSDUCERS" row={1} />
            <SectionHeader title="LOAD CELLS" row={4} />
            <SectionHeader title="THERMOCOUPLES" row={7} />
          </>
        )}

        {/* Render all sensor charts */}
        {config.sensors.map((sensor) => {
          const positioning = isBentoLayout
            ? getBentoPosition(sensor.id)
            : getFilteredPosition(sensor.id);

          return (
            <TelemetryChart
              key={sensor.id}
              config={sensor}
              ref={(r) => registry(sensor.id, r)}
              className={cn(positioning)}
            />
          );
        })}
      </div>
    </div>
  );
}
