/**
 * Defines the structure for a single chart/sensor on the dashboard.
 * Used by the SensorGrid to generate layouts dynamically.
 */
export interface SensorConfig {
    id: string;          // Matches the backend ID (e.g., 'PT-01')
    label: string;       // Human readable name (e.g., 'N2 Inlet')
    unit: string;        // Display unit (e.g., 'psi')
    color: string;       // Hex color for the chart line
    group: 'pressure' | 'thrust' | 'tank' | 'temp'; // For layout grouping
    domain?: [number, number]; // Optional fixed Y-axis range (e.g., [0, 1500]). If not set, auto-scales based on data.
    showStats?: boolean; // Hey, don't just show a squiggly line chart, render a Big Number for the current value and a smaller number for the Max Peak value.
  }
  
  /**
   * Defines the structure for a physical switch/indicator.
   */
  export interface SwitchConfig {
    id: string;          // Matches backend ID (e.g., 'switch1')
    label: string;       // Human readable name (e.g., 'NOX FILL')
    group: 'nox' | 'n2' | 'fuel' | 'dome' | 'safety' | 'unused'; // For visual grouping in the panel
    type: 'valve' | 'safety'; // Determines icon/color logic
  }
  
  /**
   * The Master Config object that defines a complete View (e.g., Liquid vs Solid).
   */
  export interface DashboardConfig {
    sensors: SensorConfig[];
    switches: SwitchConfig[];
  }