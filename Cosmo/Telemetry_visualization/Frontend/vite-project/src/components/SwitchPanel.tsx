import { SwitchConfig } from '../types/config';
import { SwitchState } from '../types/telemetry';
import { cn } from '@/lib/utils';

interface SwitchPanelProps {
  config: SwitchConfig[];
  values: SwitchState;
}

export function SwitchPanel({ config, values }: SwitchPanelProps) {
  // Group switches by their system
  const groups = {
    safety: config.filter(s => s.group === 'safety'),
    nox: config.filter(s => s.group === 'nox'),
    n2: config.filter(s => s.group === 'n2'),
    fuel: config.filter(s => s.group === 'fuel'),
    dome: config.filter(s => s.group === 'dome'),
    // Don't show unused switches
  };

  const renderGroup = (title: string, switches: SwitchConfig[]) => {
    if (switches.length === 0) return null;

    return (
      <div className="flex items-center gap-3">
        <span className="text-base font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          {title}
        </span>
        <div className="flex gap-2">
          {switches.map((s) => {
            const isActive = values[s.id];
            const isSafety = s.type === 'safety';

            return (
              <div
                key={s.id}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-300 text-xs font-medium uppercase tracking-wide",
                  // Base State
                  !isActive && "bg-slate-100 dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400",
                  // Active State - Normal
                  isActive && !isSafety && "bg-emerald-100 dark:bg-emerald-950/40 border-emerald-500/50 text-emerald-700 dark:text-emerald-400 shadow-[0_0_12px_-2px_rgba(16,185,129,0.6)]",
                  // Active State - Safety (RED + PULSE)
                  isActive && isSafety && "bg-red-100 dark:bg-red-950/40 border-red-500/50 text-red-700 dark:text-red-400 shadow-[0_0_12px_-2px_rgba(239,68,68,0.6)] animate-pulse"
                )}
              >
                {/* Indicator Dot */}
                <div
                  className={cn(
                    "w-2.5 h-2.5 rounded-full transition-all duration-300",
                    !isActive && "bg-slate-400 dark:bg-slate-600",
                    isActive && !isSafety && "bg-emerald-500 shadow-[0_0_8px_2px_rgba(16,185,129,0.8)]",
                    isActive && isSafety && "bg-red-500 shadow-[0_0_8px_2px_rgba(239,68,68,0.8)]"
                  )}
                />

                {/* Label */}
                <span className="leading-none whitespace-nowrap">
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="w-full bg-slate-100/80 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-800 px-4 py-3">
      <div className="flex items-center gap-6 flex-wrap">
        {renderGroup("SAFETY", groups.safety)}
        {renderGroup("N2O", groups.nox)}
        {renderGroup("NITROGEN", groups.n2)}
        {renderGroup("FUEL", groups.fuel)}
        {renderGroup("DOME", groups.dome)}
      </div>
    </div>
  );
}