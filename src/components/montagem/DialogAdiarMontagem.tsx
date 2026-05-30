import { useEffect, useMemo, useState } from "react";
import { CalendarIcon, PhoneOff, CalendarClock, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type {
  MontagemAdiamentoMotivo,
  MontagemItem,
} from "@/types/montagem";

interface DialogAdiarMontagemProps {
  item: MontagemItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (payload: {
    motivo: MontagemAdiamentoMotivo;
    nova_data?: string; // ISO
    confirmou_vitrine?: boolean;
    observacao?: string;
  }) => Promise<void> | void;
}

export function DialogAdiarMontagem({
  item,
  open,
  onOpenChange,
  onConfirm,
}: DialogAdiarMontagemProps) {
  const [motivo, setMotivo] = useState<MontagemAdiamentoMotivo>("cliente_outra_data");
  const [data, setData] = useState<Date | undefined>();
  const [hora, setHora] = useState<string>("09:00");
  const [confirmouVitrine, setConfirmouVitrine] = useState(false);
  const [observacao, setObservacao] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (open) {
      setMotivo("cliente_outra_data");
      setData(undefined);
      setHora("09:00");
      setConfirmouVitrine(false);
      setObservacao("");
    }
  }, [open]);

  const novaDataISO = useMemo(() => {
    if (motivo !== "cliente_outra_data" || !data) return undefined;
    const [h, m] = hora.split(":").map((n) => parseInt(n, 10) || 0);
    const d = new Date(data);
    d.setHours(h, m, 0, 0);
    return d.toISOString();
  }, [motivo, data, hora]);

  const podeConfirmar = useMemo(() => {
    if (motivo === "cliente_outra_data") {
      return !!novaDataISO && new Date(novaDataISO).getTime() > Date.now();
    }
    if (motivo === "telefone_invalido") {
      return confirmouVitrine;
    }
    return false;
  }, [motivo, novaDataISO, confirmouVitrine]);

  const handleConfirmar = async () => {
    if (!podeConfirmar) return;
    try {
      setSalvando(true);
      await onConfirm({
        motivo,
        nova_data: novaDataISO,
        confirmou_vitrine:
          motivo === "telefone_invalido" ? confirmouVitrine : undefined,
        observacao: observacao.trim() || undefined,
      });
      onOpenChange(false);
    } finally {
      setSalvando(false);
    }
  };

  if (!item) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Adiar montagem do pedido #{item.numero_pedido}</DialogTitle>
          <DialogDescription>
            Selecione o motivo do adiamento. O pedido ficará em Stand by até
            que seja retomado.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-1">
          <RadioGroup
            value={motivo}
            onValueChange={(v) => setMotivo(v as MontagemAdiamentoMotivo)}
            className="gap-2"
          >
            <OpcaoMotivo
              value="cliente_outra_data"
              icon={<CalendarClock className="h-4 w-4 text-sky-600" />}
              titulo="Cliente deseja montagem em outro momento"
              descricao="Agende a nova data/horário combinado com o cliente."
              ativo={motivo === "cliente_outra_data"}
            />
            <OpcaoMotivo
              value="telefone_invalido"
              icon={<PhoneOff className="h-4 w-4 text-amber-600" />}
              titulo="Telefone do cliente incorreto ou não atende"
              descricao="O pedido retornará automaticamente para a fila em 7 dias."
              ativo={motivo === "telefone_invalido"}
            />
          </RadioGroup>

          {motivo === "cliente_outra_data" && (
            <div className="grid grid-cols-1 gap-3 rounded-md border bg-muted/30 p-3 sm:grid-cols-[1fr_120px]">
              <div className="space-y-1.5">
                <Label className="text-xs">Nova data</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !data && "text-muted-foreground"
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {data
                        ? data.toLocaleDateString("pt-BR")
                        : "Selecionar data"}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={data}
                      onSelect={setData}
                      initialFocus
                      disabled={(d) => {
                        const hoje = new Date();
                        hoje.setHours(0, 0, 0, 0);
                        return d < hoje;
                      }}
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Horário</Label>
                <Input
                  type="time"
                  value={hora}
                  onChange={(e) => setHora(e.target.value)}
                />
              </div>
            </div>
          )}

          {motivo === "telefone_invalido" && (
            <div className="space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/30">
              <div className="flex items-start gap-2 text-xs text-amber-900 dark:text-amber-200">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <p>
                  Antes de confirmar, registre a informação de telefone
                  incorreto na ocorrência do pedido dentro do sistema Vitrine.
                  O pedido retornará automaticamente em 7 dias.
                </p>
              </div>
              <label className="flex cursor-pointer items-start gap-2 rounded-md bg-background/60 p-2 text-sm">
                <Checkbox
                  checked={confirmouVitrine}
                  onCheckedChange={(c) => setConfirmouVitrine(c === true)}
                  className="mt-0.5"
                />
                <span>
                  Confirmo que registrei a ocorrência no sistema{" "}
                  <span className="font-medium">Vitrine</span>.
                </span>
              </label>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="obs-adiar" className="text-xs">
              Observação (opcional)
            </Label>
            <Textarea
              id="obs-adiar"
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
              placeholder="Anote detalhes da tratativa com o cliente..."
              className="min-h-[60px] text-sm"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={salvando}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleConfirmar}
            disabled={!podeConfirmar || salvando}
          >
            {salvando ? "Adiando..." : "Confirmar adiamento"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function OpcaoMotivo({
  value,
  icon,
  titulo,
  descricao,
  ativo,
}: {
  value: string;
  icon: React.ReactNode;
  titulo: string;
  descricao: string;
  ativo: boolean;
}) {
  return (
    <label
      htmlFor={`motivo-${value}`}
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors",
        ativo ? "border-primary bg-primary/5" : "hover:bg-muted/40"
      )}
    >
      <RadioGroupItem value={value} id={`motivo-${value}`} className="mt-0.5" />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium">{titulo}</span>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">{descricao}</p>
      </div>
    </label>
  );
}
