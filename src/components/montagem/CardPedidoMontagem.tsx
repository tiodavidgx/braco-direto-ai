import { useEffect, useState } from "react";
import {
  Building2,
  Package,
  PlayCircle,
  CheckCircle2,
  RotateCcw,
  AlertCircle,
  MessageSquare,
  CalendarClock,
  PhoneOff,
  PauseCircle,
  FileText,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { SLABadge } from "./SLABadge";
import type { MontagemItem } from "@/types/montagem";
import {
  formatarCountdown,
  formatarHora,
  minutosAte,
} from "@/lib/slaMontagem";

interface CardPedidoMontagemProps {
  item: MontagemItem;
  onAbrir?: (item: MontagemItem) => void;
  onIniciar?: (item: MontagemItem) => void;
  onConcluir?: (item: MontagemItem) => void;
  onDesfazer?: (item: MontagemItem) => void;
  onAdiar?: (item: MontagemItem) => void;
  onRetomar?: (item: MontagemItem) => void;
  busy?: boolean;
}

export function CardPedidoMontagem({
  item,
  onAbrir,
  onIniciar,
  onConcluir,
  onDesfazer,
  onAdiar,
  onRetomar,
  busy,
}: CardPedidoMontagemProps) {
  const [, force] = useState(0);

  useEffect(() => {
    if (!item.sla || item.coluna === "finalizado") return;
    const id = setInterval(() => force((n) => n + 1), 30_000);
    return () => clearInterval(id);
  }, [item.sla, item.coluna]);

  const minRest = item.sla ? minutosAte(item.sla.prazo_limite) : null;
  const foraPrazo = minRest !== null && minRest < 0;
  const isFinalizado = item.coluna === "finalizado";
  const isStandby = item.coluna === "standby";
  const qtdComent = item.comentarios?.length ?? 0;

  const stop = (e: React.MouseEvent) => e.stopPropagation();

  // Formatadores leves para standby
  const formatarDataCurta = (iso: string) =>
    new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });

  const identificacaoNF =
    [item.filial_saida, item.nota_fiscal, item.serie_nota_fiscal]
      .filter((v) => v != null && v !== "")
      .join("-") || `#${item.numero_pedido}`;

  return (
    <Card
      onClick={() => onAbrir?.(item)}
      className={cn(
        "group relative cursor-pointer overflow-hidden border p-2.5 pl-3 transition-all hover:-translate-y-px hover:shadow-md",
        foraPrazo && !isFinalizado && !isStandby && "border-red-200 dark:border-red-900",
        isFinalizado && "opacity-90",
        isStandby && "border-violet-200 dark:border-violet-900"
      )}
    >
      {/* faixa lateral de urgência */}
      <div
        className={cn(
          "absolute left-0 top-0 h-full w-1",
          isStandby
            ? "bg-violet-500"
            : isFinalizado
            ? "bg-emerald-500"
            : foraPrazo
            ? "bg-red-500"
            : item.sla?.status_sla === "proximo_corte"
            ? "bg-amber-500"
            : item.sla?.status_sla === "recem_entregue"
            ? "bg-sky-500"
            : "bg-muted"
        )}
      />

      {/* Linha 1: identificação NF (filial-nota-serie) + SLA */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5 text-[13px] font-semibold">
          <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
          <span className="truncate font-mono">{identificacaoNF}</span>
        </div>
        {isStandby ? (
          <span className="flex items-center gap-1 rounded-md bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-800 dark:bg-violet-950 dark:text-violet-300">
            <PauseCircle className="h-3 w-3" />
            Stand by
          </span>
        ) : (
          <SLABadge
            sla={item.sla}
            coluna={item.coluna}
            className="shrink-0 text-[10px]"
          />
        )}
      </div>

      {/* Linha 2: cliente */}
      {item.cliente_nome && (
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {item.cliente_nome}
        </p>
      )}

      {/* Linha 3: filial + countdown */}
      <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
        {item.filial_venda ? (
          <span className="flex min-w-0 items-center gap-1">
            <Building2 className="h-3 w-3 shrink-0" />
            <span className="truncate">{item.filial_venda}</span>
          </span>
        ) : (
          <span />
        )}
        {!isFinalizado && !isStandby && item.sla && minRest !== null && (
          <span
            className={cn(
              "shrink-0 font-mono",
              foraPrazo && "font-medium text-red-600 dark:text-red-400"
            )}
            title={`Prazo ${formatarHora(item.sla.prazo_limite)}`}
          >
            {foraPrazo ? "-" : ""}
            {formatarCountdown(minRest)}
          </span>
        )}
      </div>

      {/* Info do adiamento (standby) */}
      {isStandby && item.adiamento && (
        <div className="mt-1.5 space-y-0.5 text-[11px]">
          {item.adiamento.motivo === "cliente_outra_data" && (
            <div className="flex items-center gap-1 text-violet-700 dark:text-violet-300">
              <CalendarClock className="h-3 w-3" />
              <span>
                Remarcado:{" "}
                {item.adiamento.nova_data
                  ? formatarDataCurta(item.adiamento.nova_data)
                  : "sem data"}
              </span>
            </div>
          )}
          {item.adiamento.motivo === "telefone_invalido" && (
            <div className="flex items-center gap-1 text-amber-700 dark:text-amber-400">
              <PhoneOff className="h-3 w-3" />
              <span>
                Telefone inválido · retorna{" "}
                {item.adiamento.retorno_em
                  ? formatarDataCurta(item.adiamento.retorno_em)
                  : "em 7 dias"}
              </span>
            </div>
          )}
        </div>
      )}

      {isFinalizado &&
        item.marcacao_local?.concluido_em &&
        item.conclusao_pendente_erp && (
          <div className="mt-1.5 flex items-center gap-1 text-[11px] text-amber-700 dark:text-amber-400">
            <AlertCircle className="h-3 w-3" />
            <span>Aguardando ERP</span>
          </div>
        )}

      {/* Linha 4: ações compactas + comentários */}
      <div className="mt-2 flex items-center gap-1" onClick={stop}>
        {item.coluna === "pendente" && !item.travado_pelo_erp && (
          <>
            <Button
              size="sm"
              variant="outline"
              className="h-7 flex-1 px-2 text-[11px]"
              disabled={busy}
              onClick={() => onIniciar?.(item)}
            >
              <PlayCircle className="mr-1 h-3 w-3" />
              Iniciar
            </Button>
            <Button
              size="sm"
              className="h-7 flex-1 px-2 text-[11px]"
              disabled={busy}
              onClick={() => onConcluir?.(item)}
            >
              <CheckCircle2 className="mr-1 h-3 w-3" />
              Concluir
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-1.5 text-muted-foreground"
              disabled={busy}
              onClick={() => onAdiar?.(item)}
              title="Adiar montagem"
            >
              <PauseCircle className="h-3 w-3" />
            </Button>
          </>
        )}

        {item.coluna === "em_andamento" && !item.travado_pelo_erp && (
          <>
            <Button
              size="sm"
              className="h-7 flex-1 px-2 text-[11px]"
              disabled={busy}
              onClick={() => onConcluir?.(item)}
            >
              <CheckCircle2 className="mr-1 h-3 w-3" />
              Concluir
            </Button>
            {item.marcacao_local?.iniciado_em && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-1.5"
                disabled={busy}
                onClick={() => onDesfazer?.(item)}
                title="Desfazer início"
              >
                <RotateCcw className="h-3 w-3" />
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-1.5 text-muted-foreground"
              disabled={busy}
              onClick={() => onAdiar?.(item)}
              title="Adiar montagem"
            >
              <PauseCircle className="h-3 w-3" />
            </Button>
          </>
        )}

        {isStandby && !item.travado_pelo_erp && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 flex-1 px-2 text-[11px]"
            disabled={busy}
            onClick={() => onRetomar?.(item)}
          >
            <PlayCircle className="mr-1 h-3 w-3" />
            Retomar
          </Button>
        )}

        {isFinalizado &&
          !item.travado_pelo_erp &&
          item.marcacao_local?.concluido_em && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 flex-1 px-2 text-[11px] text-muted-foreground"
              disabled={busy}
              onClick={() => onDesfazer?.(item)}
            >
              <RotateCcw className="mr-1 h-3 w-3" />
              Desfazer
            </Button>
          )}

        {item.travado_pelo_erp && isFinalizado && (
          <span className="flex-1 text-[10px] italic text-muted-foreground">
            Confirmado pelo ERP
          </span>
        )}

        <Button
          size="sm"
          variant="ghost"
          className="h-7 shrink-0 gap-1 px-1.5 text-[11px] text-muted-foreground"
          onClick={() => onAbrir?.(item)}
          title="Abrir detalhes e comentários"
        >
          <MessageSquare className="h-3 w-3" />
          {qtdComent > 0 && <span>{qtdComent}</span>}
        </Button>
      </div>
    </Card>
  );
}
