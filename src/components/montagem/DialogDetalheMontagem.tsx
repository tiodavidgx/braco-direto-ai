import { useEffect, useMemo, useRef, useState } from "react";
import {
  User as UserIcon,
  Building2,
  Hammer,
  CheckCircle2,
  PlayCircle,
  RotateCcw,
  AlertCircle,
  MessageSquare,
  Send,
  Info,
  FileText,
  Activity,
  Truck,
  Hash,
  CalendarClock,
  Undo2,
  Paperclip,
  X,
  Bell,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { toast } from "sonner";
import { montagemService } from "@/services/montagem.service";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { SLABadge } from "./SLABadge";
import type { MontagemComentario, MontagemItem } from "@/types/montagem";
import {
  formatarCountdown,
  formatarDataHora,
  minutosAte,
} from "@/lib/slaMontagem";
import { useAuth } from "@/contexts/AuthContext";
import {
  AttachmentPreview,
  LightboxPreview,
  type AnexoRef,
} from "@/components/shared/AttachmentPreview";

interface DialogDetalheMontagemProps {
  item: MontagemItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onIniciar?: (item: MontagemItem) => void | Promise<void>;
  onConcluir?: (item: MontagemItem) => void;
  onDesfazer?: (item: MontagemItem) => void | Promise<void>;
  onAdicionarComentario?: (pedidoId: string, texto: string, anexos?: File[]) => void;
  onAdiar?: (item: MontagemItem) => void;
  onRetomar?: (item: MontagemItem) => void;
  busy?: boolean;
}

export function DialogDetalheMontagem({
  item,
  open,
  onOpenChange,
  onIniciar,
  onConcluir,
  onDesfazer,
  onAdicionarComentario,
  onAdiar,
  onRetomar,
  busy,
}: DialogDetalheMontagemProps) {
  const { user } = useAuth();
  const [comentario, setComentario] = useState("");
  const [anexos, setAnexos] = useState<File[]>([]);
  const [preview, setPreview] = useState<AnexoRef | null>(null);
  const [lembretes, setLembretes] = useState<
    { id: number; agendar_para: string; enviado: boolean }[]
  >([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) {
      setComentario("");
      setAnexos([]);
      setPreview(null);
      setLembretes([]);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !item) return;
    montagemService
      .getLembretes(item.pedido_id)
      .then((data) =>
        setLembretes(Array.isArray(data) ? data.filter((l) => !l.enviado) : [])
      )
      .catch(() => setLembretes([]));
  }, [open, item?.pedido_id]);

  const minRest = useMemo(
    () => (item?.sla ? minutosAte(item.sla.prazo_limite) : null),
    [item]
  );

  if (!item) return null;

  const foraPrazo = minRest !== null && minRest < 0;
  const isFinalizado = item.coluna === "finalizado";
  const comentarios = item.comentarios ?? [];

  const identificacaoNF =
    [item.filial_saida, item.nota_fiscal, item.serie_nota_fiscal]
      .filter((v) => v != null && v !== "")
      .join("-") || `#${item.numero_pedido}`;

  const produtoLinha = [item.nome_produto, item.produto]
    .filter((v) => v != null && v !== "")
    .join(" · ");

  const montadorLinha = [item.identificador_montador, item.montador_nome]
    .filter((v) => v != null && v !== "")
    .join(" · ");

  const enviarComentario = () => {
    const texto = comentario.trim();
    if (!texto && anexos.length === 0) return;
    onAdicionarComentario?.(item.pedido_id, texto, anexos.length > 0 ? anexos : undefined);
    setComentario("");
    setAnexos([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[calc(100%-1rem)] max-w-2xl gap-0 overflow-hidden p-0 sm:w-full">
        <DialogHeader className="border-b px-3 py-3 sm:px-5 sm:py-4">
          <DialogTitle className="flex flex-wrap items-center gap-x-2 gap-y-1 pr-6 text-sm sm:text-base">
            <FileText className="h-4 w-4 text-primary" />
            <span className="font-mono">{identificacaoNF}</span>
            <span className="text-xs font-normal text-muted-foreground">
              · Pedido #{item.numero_pedido}
            </span>
            <SLABadge sla={item.sla} coluna={item.coluna} className="ml-2" />
          </DialogTitle>
          {!isFinalizado && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Select
                value=""
                onValueChange={async (tipo) => {
                  try {
                    await montagemService.criarLembrete(
                      item.pedido_id,
                      tipo as "1h" | "2h" | "6h" | "amanha"
                    );
                    toast.success(
                      tipo === "amanha"
                        ? "Lembrete agendado para amanhã às 9h"
                        : `Lembrete agendado para ${tipo}`
                    );
                    const data = await montagemService.getLembretes(
                      item.pedido_id
                    );
                    setLembretes(
                      Array.isArray(data)
                        ? data.filter((l) => !l.enviado)
                        : []
                    );
                  } catch {
                    toast.error("Erro ao agendar lembrete");
                  }
                }}
              >
                <SelectTrigger className="h-8 w-auto min-w-[140px] gap-1 text-xs">
                  <Bell className="h-3.5 w-3.5" />
                  <span>Lembre-me</span>
                  {lembretes.length > 0 && (
                    <span className="ml-1 rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold leading-none text-primary-foreground">
                      {lembretes.length}
                    </span>
                  )}
                </SelectTrigger>
                <SelectContent>
                  {lembretes.length > 0 && (
                    <>
                      <div className="px-2 py-1.5 text-[11px] font-medium text-muted-foreground">
                        Lembretes pendentes:
                      </div>
                      {lembretes.map((l) => (
                        <div
                          key={l.id}
                          className="flex items-center gap-1.5 px-2 py-1 text-[11px] text-muted-foreground"
                        >
                          <Bell className="h-3 w-3 text-orange-500" />
                          {new Date(l.agendar_para).toLocaleString("pt-BR", {
                            day: "2-digit",
                            month: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      ))}
                      <div className="my-1 border-t" />
                      <div className="px-2 py-1 text-[11px] font-medium text-muted-foreground">
                        Agendar novo:
                      </div>
                    </>
                  )}
                  <SelectItem value="1h">Em 1 hora</SelectItem>
                  <SelectItem value="2h">Em 2 horas</SelectItem>
                  <SelectItem value="6h">Em 6 horas</SelectItem>
                  <SelectItem value="amanha">Amanhã (9h)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </DialogHeader>

        <ScrollArea className="max-h-[calc(100dvh-9rem)] sm:max-h-[70vh]">
          <div className="space-y-5 px-3 py-4 sm:px-5">
            {/* Info cliente / filial / montador */}
            <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <InfoLinha
                icon={<UserIcon className="h-4 w-4" />}
                label="Cliente"
                value={item.cliente_nome ?? "—"}
              />
              <InfoLinha
                icon={<Building2 className="h-4 w-4" />}
                label="Filial Venda"
                value={item.filial_venda ?? "—"}
              />
              <InfoLinha
                icon={<Building2 className="h-4 w-4" />}
                label="Filial Saída"
                value={item.filial_saida ?? "—"}
              />
              <InfoLinha
                icon={<Hash className="h-4 w-4" />}
                label="Nota Fiscal / Série"
                value={
                  item.nota_fiscal
                    ? `${item.nota_fiscal}${
                        item.serie_nota_fiscal
                          ? " / " + item.serie_nota_fiscal
                          : ""
                      }`
                    : "—"
                }
              />
              <InfoLinha
                icon={<Truck className="h-4 w-4" />}
                label="Data da Entrega"
                value={
                  item.data_entrega ? formatarDataHora(item.data_entrega) : "—"
                }
              />
              <InfoLinha
                icon={<CalendarClock className="h-4 w-4" />}
                label="Previsão Montagem"
                value={
                  item.data_previsao_montagem
                    ? formatarDataHora(item.data_previsao_montagem)
                    : "—"
                }
              />
              <InfoLinha
                icon={<Hammer className="h-4 w-4" />}
                label="Montador"
                value={montadorLinha || "—"}
              />
              <InfoLinha
                icon={<Activity className="h-4 w-4" />}
                label="Situação Time Line"
                value={item.situacao_timeline ?? "—"}
              />
              <InfoLinha
                icon={<Activity className="h-4 w-4" />}
                label="Situação Boletim"
                value={item.situacao_boletim ?? "—"}
              />
              {item.data_montagem && (
                <InfoLinha
                  icon={<Hammer className="h-4 w-4" />}
                  label="Data da Montagem"
                  value={formatarDataHora(item.data_montagem)}
                />
              )}
            </section>

            {(produtoLinha || item.produtos_resumo) && (
              <section>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Produtos
                </p>
                <p className="rounded-md bg-muted/50 px-3 py-2 text-sm">
                  {produtoLinha || item.produtos_resumo}
                </p>
              </section>
            )}

            {/* SLA */}
            {item.sla && !isFinalizado && (
              <section
                className={cn(
                  "rounded-md border px-3 py-2.5 text-sm",
                  foraPrazo
                    ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200"
                    : "border-border bg-muted/30"
                )}
              >
                <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                  <span className="font-medium">
                    Prazo de montagem: {formatarDataHora(item.sla.prazo_limite)}
                  </span>
                  <span className="font-mono text-sm">
                    {foraPrazo ? "atrasado " : "em "}
                    {minRest !== null && formatarCountdown(minRest)}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {item.sla.badge_texto}
                </p>
              </section>
            )}

            {/* SLA — bloco para itens finalizados (compara data_montagem
                com prazo_limite calculado a partir da data_entrega) */}
            {isFinalizado && item.conclusao_sla && (() => {
              const c = item.conclusao_sla!;
              const dentro = c.dentro_do_prazo;
              const diff = c.diferenca_minutos;
              const tone =
                dentro === true
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200"
                  : dentro === false
                  ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200"
                  : "border-border bg-muted/30";
              const statusLabel =
                dentro === true
                  ? "Dentro do prazo"
                  : dentro === false
                  ? "Fora do prazo"
                  : "Sem data de montagem";
              const diffLabel =
                diff === null || diff === undefined
                  ? null
                  : diff <= 0
                  ? `${formatarCountdown(Math.abs(diff))} antes`
                  : `${formatarCountdown(diff)} de atraso`;
              return (
                <section className={cn("rounded-md border px-3 py-2.5 text-sm", tone)}>
                  <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                    <span className="font-medium">
                      Prazo de montagem: {formatarDataHora(c.prazo_limite)}
                    </span>
                    <span className="font-mono text-sm">{statusLabel}</span>
                  </div>
                  <div className="mt-1 grid gap-1 text-xs sm:grid-cols-2">
                    <p>
                      <span className="text-muted-foreground">Concluído em: </span>
                      {c.data_montagem
                        ? formatarDataHora(c.data_montagem)
                        : "—"}
                    </p>
                    {diffLabel && (
                      <p className="sm:text-right font-mono">{diffLabel}</p>
                    )}
                  </div>
                </section>
              );
            })()}

            {/* Marcações locais */}
            <section className="space-y-2">
              {item.marcacao_local?.iniciado_em && (
                <div className="flex items-start gap-2 text-sm">
                  <PlayCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <div>
                    <p className="font-medium">Montagem iniciada</p>
                    <p className="text-xs text-muted-foreground">
                      {formatarDataHora(item.marcacao_local.iniciado_em)}
                    </p>
                  </div>
                </div>
              )}
              {item.marcacao_local?.concluido_em && (
                <div className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                  <div>
                    <p className="font-medium">Montagem concluída</p>
                    <p className="text-xs text-muted-foreground">
                      {formatarDataHora(item.marcacao_local.concluido_em)}
                    </p>
                    {item.marcacao_local.motivo_atraso && (
                      <p className="mt-1 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
                        Motivo do atraso: {item.marcacao_local.motivo_atraso}
                      </p>
                    )}
                    {item.marcacao_local.observacao && (
                      <p className="mt-1 text-xs italic text-muted-foreground">
                        "{item.marcacao_local.observacao}"
                      </p>
                    )}
                  </div>
                </div>
              )}
              {isFinalizado && item.conclusao_pendente_erp && (
                <div className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">
                  <AlertCircle className="h-3.5 w-3.5" />
                  <span>Aguardando confirmação do ERP</span>
                </div>
              )}
              {item.travado_pelo_erp && (
                <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                  <Info className="h-3.5 w-3.5" />
                  <span>Status confirmado pelo ERP — ações travadas.</span>
                </div>
              )}
            </section>

            {/* Ações */}
            {!item.travado_pelo_erp && item.coluna === "em_andamento" &&
              item.marcacao_local?.iniciado_em && (
                <section className="flex flex-wrap gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={busy}
                    onClick={() => onDesfazer?.(item)}
                  >
                    <RotateCcw className="mr-1.5 h-4 w-4" />
                    Desfazer início
                  </Button>
                </section>
              )}

            <Separator />

            {/* Comentários */}
            <section>
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                Comentários
                <span className="rounded bg-muted px-1.5 text-xs text-muted-foreground">
                  {comentarios.length}
                </span>
              </div>

              {comentarios.length === 0 ? (
                <p className="rounded-md border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">
                  Nenhum comentário ainda. Registre abaixo informações da
                  montagem, atrasos, contato com cliente etc.
                </p>
              ) : (
                <ul className="space-y-3">
                  {comentarios.map((c) => (
                    <ComentarioItem key={c.id} comentario={c} onPreview={setPreview} />
                  ))}
                </ul>
              )}

              {/* Compor comentário */}
              <div className="mt-3 space-y-2">
                <Textarea
                  placeholder="Adicionar comentário..."
                  value={comentario}
                  onChange={(e) => setComentario(e.target.value)}
                  className="min-h-[70px] resize-none text-sm"
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                      e.preventDefault();
                      enviarComentario();
                    }
                  }}
                />

                {anexos.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {anexos.map((f, i) => (
                      <span
                        key={`${f.name}-${i}`}
                        className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px]"
                      >
                        <Paperclip className="h-3 w-3" />
                        <span className="max-w-[160px] truncate">{f.name}</span>
                        <button
                          type="button"
                          onClick={() => setAnexos((prev) => prev.filter((_, idx) => idx !== i))}
                          className="ml-0.5 hover:text-destructive"
                          aria-label="Remover anexo"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files) {
                          setAnexos((prev) => [...prev, ...Array.from(e.target.files!)]);
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={busy}
                      title="Anexar imagens ou arquivos"
                    >
                      <Paperclip className="h-4 w-4" />
                    </Button>
                    <span className="hidden truncate text-[11px] text-muted-foreground sm:inline">
                      {user?.nome ? `Como ${user.nome}` : "Seu comentário"} ·
                      Ctrl+Enter para enviar
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {!isFinalizado && item.coluna !== "standby" && onAdiar && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={busy || item.travado_pelo_erp}
                        onClick={() => onAdiar(item)}
                      >
                        <CalendarClock className="mr-1.5 h-3.5 w-3.5" />
                        Adiar montagem
                      </Button>
                    )}
                    {item.coluna === "standby" && onRetomar && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => onRetomar(item)}
                      >
                        <Undo2 className="mr-1.5 h-3.5 w-3.5" />
                        Retomar
                      </Button>
                    )}
                    <Button
                      size="sm"
                      disabled={(!comentario.trim() && anexos.length === 0) || busy}
                      onClick={enviarComentario}
                    >
                      <Send className="mr-1.5 h-3.5 w-3.5" />
                      Comentar
                    </Button>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </ScrollArea>
        <LightboxPreview anexo={preview} onClose={() => setPreview(null)} />
      </DialogContent>
    </Dialog>
  );
}

function InfoLinha({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <div className="min-w-0">
        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className="truncate font-medium">{value}</p>
      </div>
    </div>
  );
}

function ComentarioItem({
  comentario,
  onPreview,
}: {
  comentario: MontagemComentario;
  onPreview: (a: AnexoRef) => void;
}) {
  const iniciais = comentario.autor_nome
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  const anexos = comentario.anexos ?? [];
  const textoLimpo = comentario.texto === "(anexo)" && anexos.length > 0 ? "" : comentario.texto;

  return (
    <li className="flex gap-2.5">
      <Avatar className="h-7 w-7 shrink-0">
        <AvatarFallback className="text-[10px]">
          {iniciais || "?"}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1 rounded-md border bg-muted/30 px-3 py-2">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-xs font-medium">
            {comentario.autor_nome}
          </span>
          <span className="shrink-0 text-[10px] text-muted-foreground">
            {formatarDataHora(comentario.criado_em)}
          </span>
        </div>
        {textoLimpo && (
          <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">
            {textoLimpo}
          </p>
        )}
        {anexos.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {anexos.map((a, i) => (
              <AttachmentPreview key={`${a.url}-${i}`} anexo={a} onPreview={onPreview} />
            ))}
          </div>
        )}
      </div>
    </li>
  );
}
