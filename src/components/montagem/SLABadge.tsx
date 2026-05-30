import { cn } from "@/lib/utils";
import type { MontagemSLA, MontagemStatusSLA } from "@/types/montagem";
import { AlertTriangle, Clock, Sparkles, CheckCircle2, CalendarClock } from "lucide-react";

interface SLABadgeProps {
  sla: MontagemSLA | null;
  coluna?: string;
  className?: string;
  showIcon?: boolean;
}

const CLASSES: Record<MontagemStatusSLA, string> = {
  fora_do_prazo:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900",
  proximo_corte:
    "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900",
  no_prazo:
    "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900",
  recem_entregue:
    "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-900",
  fds:
    "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700",
};

const ICONS: Record<MontagemStatusSLA, React.ComponentType<{ className?: string }>> = {
  fora_do_prazo: AlertTriangle,
  proximo_corte: Clock,
  no_prazo: CalendarClock,
  recem_entregue: Sparkles,
  fds: CalendarClock,
};

export function SLABadge({ sla, coluna, className, showIcon = true }: SLABadgeProps) {
  if (coluna === "finalizado") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
          "bg-emerald-50 text-emerald-700 border-emerald-200",
          "dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900",
          className
        )}
      >
        {showIcon && <CheckCircle2 className="h-3 w-3" />}
        Finalizado
      </span>
    );
  }

  if (!sla) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
          "bg-muted text-muted-foreground border-border",
          className
        )}
      >
        Sem prazo
      </span>
    );
  }

  const Icon = ICONS[sla.status_sla];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        CLASSES[sla.status_sla],
        className
      )}
    >
      {showIcon && <Icon className="h-3 w-3" />}
      {sla.badge_texto}
    </span>
  );
}
