import { useState, useMemo, useEffect } from 'react';
import { useTelemetry } from './hooks/useTelemetry';
import { DASHBOARD_CONFIG } from './config/maps';
import { SensorGrid } from './components/SensorGrid';
import { SwitchPanel } from './components/SwitchPanel';
import { ThemeToggle } from './components/theme-toggle';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Input } from './components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './components/ui/select';
import { Play, Square, RotateCcw, Filter, Target, Pause, PlayCircle } from 'lucide-react';
import { Toggle } from './components/ui/toggle';

type FilterMode = 'all' | 'pressure' | 'thrust' | 'temp';

const FILTER_MODE_KEY = 'cosmo-filter-mode';

export default function App() {
  const {
    recordingState,
    connectionStatus,
    switches,
    runtimeStr,
    dataLag,
    isCountdownHeld,
    controls,
    registerChart,
    filterEnabled,
    toggleFilter
  } = useTelemetry();

  // ARM dialog state
  const [armDialogOpen, setArmDialogOpen] = useState(false);
  const [hours, setHours] = useState(0);
  const [minutes, setMinutes] = useState(5);
  const [seconds, setSeconds] = useState(0);

  // Filter State (All, Pressure, Load Cells, Temperature) - Load from localStorage
  const [filterMode, setFilterMode] = useState<FilterMode>(() => {
    const saved = localStorage.getItem(FILTER_MODE_KEY);
    return (saved as FilterMode) || 'all';
  });

  // Persist filter mode to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(FILTER_MODE_KEY, filterMode);
  }, [filterMode]);

  // Filter sensors based on selected mode
  const filteredSensors = useMemo(() => {
    if (filterMode === 'all') {
      return DASHBOARD_CONFIG.sensors;
    }
    return DASHBOARD_CONFIG.sensors.filter(sensor => sensor.group === filterMode);
  }, [filterMode]);

  // Create filtered config
  const currentConfig = useMemo(() => ({
    sensors: filteredSensors,
    switches: DASHBOARD_CONFIG.switches,
  }), [filteredSensors]);

  // Determine if we should allow scrolling (for All Sensors view)
  const isAllSensorsView = filterMode === 'all';

  // Calculate data health status
  const getDataHealth = () => {
    if (recordingState !== 'recording' || dataLag === null) {
      return { status: 'idle', color: 'text-slate-400', label: '' };
    }

    if (dataLag < 500) {
      return { status: 'live', color: 'text-emerald-400', label: 'LIVE' };
    } else if (dataLag < 1000) {
      return { status: 'lag', color: 'text-amber-400', label: `LAG ${dataLag}ms` };
    } else {
      return { status: 'lost', color: 'text-red-400', label: 'SIGNAL LOST' };
    }
  };

  const dataHealth = getDataHealth();

  // ARM dialog handlers
  const handlePresetDuration = (seconds: number) => {
    controls.startArming(seconds);
    setArmDialogOpen(false);
  };

  const handleCustomDuration = () => {
    const totalSeconds = hours * 3600 + minutes * 60 + seconds;

    if (totalSeconds > 0) {
      controls.startArming(totalSeconds);
      setArmDialogOpen(false);
    }
  };

  return (
    <div className="h-screen w-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-50 flex flex-col overflow-hidden font-sans selection:bg-emerald-500/30">

      {/* --- HEADER --- */}
      <header className="min-h-14 flex-none border-b border-slate-200 dark:border-slate-800 bg-slate-100/80 dark:bg-slate-900/80 backdrop-blur-md px-4 py-2 z-50">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          {/* LEFT: Status & Title */}
          <div className="flex items-center gap-4 min-w-0">
            <div className="flex items-center gap-2">
              <img
                src="/logo.png"
                alt="COSMO Logo"
                className="w-8 h-8 rounded-full object-cover flex-shrink-0"
              />
              <h1 className="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100 whitespace-nowrap">
                COSMO WANDA <span className="text-slate-400 dark:text-slate-500 font-normal hidden sm:inline">TELEMETRY</span>
              </h1>
            </div>

            <Badge
              variant={connectionStatus === 'Connected' ? 'default' : 'destructive'}
              className={`text-[10px] px-2 h-5 uppercase tracking-wider flex-shrink-0 ${
                connectionStatus === 'Connected' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50' : ''
              }`}
            >
              {connectionStatus === 'Connected' ? 'Online' : 'Offline'}
            </Badge>
          </div>

          {/* CENTER: Mission Clock - Hide on very small screens */}
          <div className="hidden lg:flex flex-col items-center flex-shrink-0">
            <div className="text-[10px] text-slate-400 dark:text-slate-500 font-mono tracking-[0.2em] uppercase">
              Mission Clock
            </div>
            <div className="flex items-center gap-3">
              <div className={`font-mono text-2xl font-bold tabular-nums tracking-widest ${
                recordingState === 'recording' ? 'text-emerald-500 dark:text-emerald-400' :
                recordingState === 'armed' ? (
                  runtimeStr.startsWith('00:00:1') || runtimeStr.startsWith('00:00:0')
                    ? 'text-orange-500 dark:text-orange-400'
                    : 'text-amber-500 dark:text-amber-400'
                ) :
                recordingState === 'stopped' ? 'text-amber-500 dark:text-amber-400' :
                'text-slate-400 dark:text-slate-600'
              }`}>
                {recordingState === 'armed' ? 'T-' : 'T+'} {runtimeStr}
              </div>
              {recordingState === 'recording' && dataHealth.label && (
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    dataHealth.status === 'live' ? 'bg-emerald-400 animate-pulse' :
                    dataHealth.status === 'lag' ? 'bg-amber-400 animate-pulse' :
                    'bg-red-500 animate-ping'
                  }`} />
                  <span className={`text-xs font-mono font-semibold tracking-wider ${dataHealth.color}`}>
                    {dataHealth.label}
                  </span>
                </div>
              )}
              {recordingState === 'armed' && (
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    isCountdownHeld
                      ? 'bg-amber-400'
                      : (runtimeStr.startsWith('00:00:1') || runtimeStr.startsWith('00:00:0'))
                        ? 'bg-orange-400 animate-ping'
                        : 'bg-amber-400 animate-pulse'
                  }`} />
                  <span className={`text-xs font-mono font-semibold tracking-wider ${
                    isCountdownHeld
                      ? 'text-amber-400'
                      : (runtimeStr.startsWith('00:00:1') || runtimeStr.startsWith('00:00:0'))
                        ? 'text-orange-400'
                        : 'text-amber-400'
                  }`}>
                    {isCountdownHeld ? 'HELD' :
                     (runtimeStr.startsWith('00:00:1') || runtimeStr.startsWith('00:00:0')) ? 'FINAL COUNT' : 'ARMED'}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Controls */}
          <div className="flex items-center gap-2 md:gap-3 flex-shrink-0">
          {/* Filter Selector */}
          <Select
            value={filterMode}
            onValueChange={(v) => setFilterMode(v as FilterMode)}
          >
            <SelectTrigger className="w-[140px] md:w-[160px] h-8 bg-slate-50 dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-xs">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent className="bg-slate-50 dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-200">
              <SelectItem value="all">All Sensors (16)</SelectItem>
              <SelectItem value="pressure">Pressure (9)</SelectItem>
              <SelectItem value="thrust">Load Cells (5)</SelectItem>
              <SelectItem value="temp">Temperature (2)</SelectItem>
            </SelectContent>
          </Select>

          <div className="hidden md:block w-px h-6 bg-slate-300 dark:bg-slate-800 mx-2" />

          {/* Theme Toggle */}
          <ThemeToggle />

          {/* Median Filter Toggle */}
          <Toggle
            pressed={filterEnabled}
            onPressedChange={toggleFilter}
            aria-label="Toggle median filter"
            className="h-8 px-2 data-[state=on]:bg-emerald-500/20 data-[state=on]:text-emerald-500 data-[state=on]:border-emerald-500/50"
          >
            <Filter className="w-4 h-4" />
          </Toggle>

          <div className="hidden md:block w-px h-6 bg-slate-300 dark:bg-slate-800 mx-2" />

          {/* Flight Recorder */}
          <div className="flex items-center gap-0.5 md:gap-1 bg-slate-50 dark:bg-slate-900 p-1 rounded-md border border-slate-300 dark:border-slate-800">
            {/* IDLE State: ARM + REC */}
            {recordingState === 'idle' && (
              <>
                <Dialog open={armDialogOpen} onOpenChange={setArmDialogOpen}>
                  <DialogTrigger asChild>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 px-2 md:px-3 text-xs gap-1 md:gap-2 hover:bg-slate-200 dark:hover:bg-slate-800 text-amber-500 hover:text-amber-400"
                      disabled={connectionStatus !== 'Connected'}
                    >
                      <Target className="w-3 h-3" />
                      <span className="hidden sm:inline">ARM</span>
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-md bg-slate-50 dark:bg-slate-900 border-slate-300 dark:border-slate-800">
                    <DialogHeader>
                      <DialogTitle className="text-slate-900 dark:text-slate-100">Set Countdown Duration</DialogTitle>
                      <DialogDescription className="text-slate-600 dark:text-slate-400">
                        Select a preset or enter custom countdown time (HH:MM:SS)
                      </DialogDescription>
                    </DialogHeader>

                    <div className="grid grid-cols-4 gap-2 mb-4">
                      <Button
                        variant="outline"
                        onClick={() => handlePresetDuration(10)}
                        className="bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700"
                      >
                        10s
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handlePresetDuration(30)}
                        className="bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700"
                      >
                        30s
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handlePresetDuration(60)}
                        className="bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700"
                      >
                        1m
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handlePresetDuration(300)}
                        className="bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700"
                      >
                        5m
                      </Button>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-slate-900 dark:text-slate-200">Custom Duration</label>
                      <div className="flex items-center gap-2">
                        <div className="flex flex-col items-center">
                          <label className="text-xs text-slate-500 dark:text-slate-400 mb-1">HH</label>
                          <Input
                            type="number"
                            min="0"
                            max="99"
                            value={hours}
                            onChange={(e) => setHours(Math.max(0, Math.min(99, parseInt(e.target.value) || 0)))}
                            className="w-16 text-center bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 font-mono"
                          />
                        </div>
                        <span className="text-xl font-bold text-slate-400 dark:text-slate-500">:</span>
                        <div className="flex flex-col items-center">
                          <label className="text-xs text-slate-500 dark:text-slate-400 mb-1">MM</label>
                          <Input
                            type="number"
                            min="0"
                            max="59"
                            value={minutes}
                            onChange={(e) => setMinutes(Math.max(0, Math.min(59, parseInt(e.target.value) || 0)))}
                            className="w-16 text-center bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 font-mono"
                          />
                        </div>
                        <span className="text-xl font-bold text-slate-400 dark:text-slate-500">:</span>
                        <div className="flex flex-col items-center">
                          <label className="text-xs text-slate-500 dark:text-slate-400 mb-1">SS</label>
                          <Input
                            type="number"
                            min="0"
                            max="59"
                            value={seconds}
                            onChange={(e) => setSeconds(Math.max(0, Math.min(59, parseInt(e.target.value) || 0)))}
                            className="w-16 text-center bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 font-mono"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-end gap-2 mt-4">
                      <Button
                        variant="outline"
                        onClick={() => setArmDialogOpen(false)}
                        className="bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700"
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={handleCustomDuration}
                        className="bg-emerald-500 hover:bg-emerald-600 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white"
                      >
                        Start Countdown
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>

                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 md:px-3 text-xs gap-1 md:gap-2 hover:bg-slate-200 dark:hover:bg-slate-800"
                  onClick={controls.startRecording}
                  disabled={connectionStatus !== 'Connected'}
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span className="hidden sm:inline">REC</span>
                </Button>
              </>
            )}

            {/* ARMED State: HOLD/RESUME + ABORT */}
            {recordingState === 'armed' && (
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 md:px-3 text-xs gap-1 md:gap-2 hover:bg-slate-200 dark:hover:bg-slate-800 text-amber-500 hover:text-amber-400"
                  onClick={isCountdownHeld ? controls.resumeCountdown : controls.holdCountdown}
                >
                  {isCountdownHeld ? <PlayCircle className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
                  <span className="hidden sm:inline">{isCountdownHeld ? 'RESUME' : 'HOLD'}</span>
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 md:px-3 text-xs gap-1 md:gap-2 hover:bg-slate-200 dark:hover:bg-slate-800 text-red-500 hover:text-red-400"
                  onClick={controls.abortCountdown}
                >
                  <Square className="w-3 h-3 fill-current" />
                  <span className="hidden sm:inline">ABORT</span>
                </Button>
              </>
            )}

            {/* RECORDING State: STOP */}
            {recordingState === 'recording' && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 md:px-3 text-xs gap-1 md:gap-2 hover:bg-slate-200 dark:hover:bg-slate-800 text-amber-500 hover:text-amber-400"
                onClick={controls.stopRecording}
              >
                <Square className="w-3 h-3 fill-current" />
                <span className="hidden sm:inline">STOP</span>
              </Button>
            )}

            {/* STOPPED State: RST */}
            {recordingState === 'stopped' && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 md:px-3 text-xs gap-1 md:gap-2 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                onClick={controls.resetRecording}
              >
                <RotateCcw className="w-3 h-3" />
                <span className="hidden sm:inline">RST</span>
              </Button>
            )}
          </div>
          </div>
        </div>
      </header>

      {/* --- MAIN CONTENT (Charts) --- */}
      <main className="flex-1 relative bg-slate-50 dark:bg-slate-950/50 overflow-auto">
        <SensorGrid
          config={currentConfig}
          registry={registerChart}
        />
      </main>

      {/* --- FOOTER (Switches) --- */}
      <footer className="flex-none z-10">
        <SwitchPanel
          config={currentConfig.switches}
          values={switches}
        />
      </footer>
    </div>
  );
}