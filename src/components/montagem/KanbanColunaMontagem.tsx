import { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface KanbanColunaMontagemProps {
  titulo: string;
  descricao?: string;
  contador: number;
  destaque?: number; // ex: quantidade fora do prazo
  accent: "slate" | "amber" | "emerald";
  children: ReactNode;
  vazioLabel?: string;
}

const ACCENTS: Record<
  KanbanColunaMontagemProps["accent"],
  { title: string; badge: string; bar: string }
> = {
  slate: {
    title: "text-slate-700 dark:text-slate-200",
    badge: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
    bar: "bg-slate-400 dark:bg-slate-600",
  },
  amber: {
    title: "text-amber-700 dark:text-amber-300",
    badge: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
    bar: "bg-amber-500",
  },
  emerald: {
    title: "text-emerald-700 dark:text-emerald-300",
    badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
    bar: "bg-emerald-500",
  },
};

export function KanbanColunaMontagem({
  titulo,
  descricao,
  contador,
  destaque,
  accent,
  children,
  vazioLabel = "Nenhum pedido",
}: KanbanColunaMontagemProps) {
  const a = ACCENTS[accent];

  return (
    <div className="flex h-full min-h-[60vh] flex-col rounded-xl border bg-card/40">
      <div className="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn("h-2 w-2 rounded-full", a.bar)} />
            <h3 className={cn("text-sm font-semibold tracking-tight", a.title)}>
              {titulo}
            </h3>
          </div>
          {descricao && (
            <p className="mt-1 text-xs text-muted-foreground">{descricao}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {destaque !== undefined && destaque > 0 && (
            <Badge
              variant="outline"
              className="border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
            >
              {destaque} fora do prazo
            </Badge>
          )}
          <Badge className={cn("font-mono", a.badge)}>{contador}</Badge>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-3 p-3">
          {contador === 0 ? (
            <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
              {vazioLabel}
            </div>
          ) : (
            children
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
