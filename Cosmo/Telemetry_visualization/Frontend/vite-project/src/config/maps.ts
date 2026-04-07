import { DashboardConfig, SensorConfig, SwitchConfig } from '../types/config';

// ========== UNIFIED SENSOR CONFIGURATION ==========
// All available sensors - filtered dynamically by view

export const ALL_SENSORS: SensorConfig[] = [
  // PRESSURE SENSORS (9 total) - IDs match wanda1 table columns
  { id: 'pt1', label: 'N2 Inlet', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 6000], showStats: true },
  { id: 'pt2', label: 'Nox Inlet', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 1500], showStats: true },
  { id: 'pt3', label: 'Dome', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 600], showStats: true },
  { id: 'pt4', label: 'Nox Tank', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 1500], showStats: true },
  { id: 'pt5', label: 'Fuel Tank', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 600], showStats: true },
  { id: 'pt6', label: 'Chamber', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 400], showStats: true },
  { id: 'pt7', label: 'Injector', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 480], showStats: true },
  { id: 'pt8', label: 'Fuel Inlet', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 560], showStats: true },
  { id: 'pt9', label: 'HPA', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 100], showStats: true },
  { id: 'pt25', label: 'COPV', unit: 'psi', color: '#06b6d4', group: 'pressure', domain: [0, 2500], showStats: true },

  // LOAD CELLS / THRUST (5 total) - IDs match wanda2 table columns
  { id: 'lc_net_force', label: 'NET FORCE', unit: 'lbs', color: '#ef4444', group: 'thrust', domain: [0, 130], showStats: true },
  { id: 'lc2', label: 'Thrust 2', unit: 'lbs', color: '#b91c1c', group: 'thrust', domain: [0, 130], showStats: true },
  { id: 'lc3', label: 'Thrust 3', unit: 'lbs', color: '#b91c1c', group: 'thrust', domain: [0, 130], showStats: true },
  { id: 'lc4', label: 'Nox Tank Wt', unit: 'lbs', color: '#f97316', group: 'thrust', domain: [0, 50], showStats: true },
  { id: 'lc1', label: 'Thrust 1', unit: 'lbs', color: '#b91c1c', group: 'thrust', domain: [0, 130], showStats: true },

  // TEMPERATURE SENSORS (2 total) - IDs match wanda2 table columns
  { id: 'tc1', label: 'Injector', unit: 'K', color: '#a855f7', group: 'temp', domain: [0, 320], showStats: true },
  { id: 'tc2', label: 'Fuel Inlet', unit: 'K', color: '#a855f7', group: 'temp', domain: [0, 290], showStats: true },
];

// All available switches - matches backend SwitchState interface
// Order: N2O group, Nitrogen group, Safety, then unused
const ALL_SWITCHES: SwitchConfig[] = [
  // Safety & Control (shown first)
  { id: 'continuity', label: 'CONTINUITY', group: 'safety', type: 'safety' },
  { id: 'launchKey', label: 'LAUNCH KEY', group: 'safety', type: 'safety' },
  { id: 'abort', label: 'ABORT', group: 'safety', type: 'safety' },

  // N2O System
  { id: 'switch1', label: 'N2O FILL', group: 'nox', type: 'valve' },
  { id: 'switch2', label: 'N2O VENT', group: 'nox', type: 'valve' },
  { id: 'switch3', label: 'N2O RELIEF', group: 'nox', type: 'valve' },

  // Nitrogen System
  { id: 'switch6', label: 'N2 FILL', group: 'n2', type: 'valve' },
  { id: 'switch7', label: 'N2 VENT', group: 'n2', type: 'valve' },

  // Fuel System
  { id: 'switch8', label: 'FUEL RELIEF', group: 'fuel', type: 'valve' },
  { id: 'switch9', label: 'FUEL PRESS', group: 'fuel', type: 'valve' },
  { id: 'switch10', label: 'FUEL MAIN', group: 'fuel', type: 'valve' },

  // Main Valves
  { id: 'switch5', label: 'NOX MAIN', group: 'nox', type: 'valve' },
  { id: 'switch4', label: 'DOME VENT', group: 'dome', type: 'valve' },

  // Unused (hidden in UI)
];

// Default dashboard config with all sensors
export const DASHBOARD_CONFIG: DashboardConfig = {
  sensors: ALL_SENSORS,
  switches: ALL_SWITCHES,
};