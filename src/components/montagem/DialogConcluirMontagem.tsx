import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import type { MontagemItem } from "@/types/montagem";
import { minutosAte } from "@/lib/slaMontagem";

interface DialogConcluirMontagemProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  item: MontagemItem | null;
  onConfirm: (obs: string | undefined, motivo: string | undefined) => Promise<void>;
}

export function DialogConcluirMontagem({
  open,
  onOpenChange,
  item,
  onConfirm,
}: DialogConcluirMontagemProps) {
  const [observacao, setObservacao] = useState("");
  const [motivo, setMotivo] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setObservacao("");
      setMotivo("");
    }
  }, [open]);

  if (!item) return null;

  const foraPrazo =
    item.sla && minutosAte(item.sla.prazo_limite) < 0;

  const handle = async () => {
    setSaving(true);
    try {
      await onConfirm(
        observacao.trim() || undefined,
        foraPrazo ? motivo.trim() || undefined : undefined
      );
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  };

  const motivoObrigatorio = !!foraPrazo;
  const podeSalvar = !motivoObrigatorio || motivo.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            Concluir montagem
          </DialogTitle>
          <DialogDescription>
            Pedido <span className="font-medium">#{item.numero_pedido}</span>
            {item.cliente_nome ? ` — ${item.cliente_nome}` : ""}
          </DialogDescription>
        </DialogHeader>

        {foraPrazo && (
          <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Esta montagem está fora do prazo. Informe o motivo do atraso
              para concluir.
            </span>
          </div>
        )}

        <div className="space-y-3">
          {foraPrazo && (
            <div className="space-y-1.5">
              <Label htmlFor="motivo">
                Motivo do atraso <span className="text-red-600">*</span>
              </Label>
              <Textarea
                id="motivo"
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                placeholder="Ex.: cliente não estava no local; produto avariado na entrega; reagendamento..."
                rows={3}
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="observacao">Observação (opcional)</Label>
            <Textarea
              id="observacao"
              value={observacao}
              onChange={(e) => setObservacao(e.target.value)}
              placeholder="Notas adicionais sobre a montagem"
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={saving}
          >
            Cancelar
          </Button>
          <Button onClick={handle} disabled={saving || !podeSalvar}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Salvando
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Confirmar conclusão
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
