import { useMemo, useState } from "react";
import { Check, ChevronsUpDown, Building2, X, Plus } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface FiltroFiliaisProps {
  filiais: string[];
  selecionadas: string[];
  onChange: (sel: string[]) => void;
  className?: string;
  /** Quando verdadeiro, adicionar uma filial à seleção exige confirmação. */
  confirmarAdicionar?: boolean;
  /** Ao digitar um código novo e confirmar, adiciona à lista de conhecidas. */
  onAdicionarConhecida?: (codigo: string) => void;
}

export function FiltroFiliais({
  filiais,
  selecionadas,
  onChange,
  className,
  confirmarAdicionar,
  onAdicionarConhecida,
}: FiltroFiliaisProps) {
  const [open, setOpen] = useState(false);
  const [pendente, setPendente] = useState<string | null>(null);
  const [novo, setNovo] = useState("");

  const ordenadas = useMemo(
    () =>
      [...filiais].sort((a, b) =>
        a.localeCompare(b, "pt-BR", { numeric: true })
      ),
    [filiais]
  );

  const aplicarAdicao = (f: string) => {
    if (selecionadas.includes(f)) return;
    onChange([...selecionadas, f]);
  };

  const toggle = (f: string) => {
    if (selecionadas.includes(f)) {
      // remover é livre (filtra mais, sem risco)
      onChange(selecionadas.filter((x) => x !== f));
      return;
    }
    if (confirmarAdicionar && selecionadas.length > 0) {
      setPendente(f);
      return;
    }
    aplicarAdicao(f);
  };

  const limpar = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange([]);
  };

  const adicionarNova = () => {
    const v = novo.trim();
    if (!v) return;
    if (!filiais.includes(v)) {
      onAdicionarConhecida?.(v);
    }
    if (!selecionadas.includes(v)) {
      if (confirmarAdicionar && selecionadas.length > 0) {
        setPendente(v);
      } else {
        aplicarAdicao(v);
      }
    }
    setNovo("");
  };

  const label =
    selecionadas.length === 0
      ? "Todas as filiais"
      : selecionadas.length === 1
      ? selecionadas[0]
      : `${selecionadas.length} filiais`;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="h-9 min-w-[200px] justify-between"
          >
            <span className="flex items-center gap-2 truncate">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <span className="truncate">{label}</span>
            </span>
            <ChevronsUpDown className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[300px] p-0" align="start">
          <Command>
            <CommandInput placeholder="Buscar filial..." />
            <CommandList>
              <CommandEmpty>Nenhuma filial encontrada.</CommandEmpty>
              <CommandGroup>
                {ordenadas.map((f) => {
                  const checked = selecionadas.includes(f);
                  return (
                    <CommandItem
                      key={f}
                      value={f}
                      onSelect={() => toggle(f)}
                      className="cursor-pointer"
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          checked ? "opacity-100" : "opacity-0"
                        )}
                      />
                      {f}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
          {onAdicionarConhecida && (
            <div className="flex items-center gap-1 border-t p-2">
              <Input
                value={novo}
                onChange={(e) => setNovo(e.target.value)}
                placeholder="Adicionar filial..."
                className="h-8 text-sm"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    adicionarNova();
                  }
                }}
              />
              <Button
                type="button"
                size="icon"
                variant="secondary"
                className="h-8 w-8 shrink-0"
                onClick={adicionarNova}
                disabled={!novo.trim()}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </PopoverContent>
      </Popover>

      {selecionadas.length > 0 && (
        <Badge
          variant="secondary"
          className="cursor-pointer gap-1"
          onClick={limpar}
        >
          Limpar
          <X className="h-3 w-3" />
        </Badge>
      )}

      <AlertDialog
        open={pendente !== null}
        onOpenChange={(o) => {
          if (!o) setPendente(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Adicionar filial ao filtro?</AlertDialogTitle>
            <AlertDialogDescription>
              Novos cards serão carregados devido à marcação da filial{" "}
              <strong>{pendente}</strong>. Deseja continuar?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (pendente) aplicarAdicao(pendente);
                setPendente(null);
              }}
            >
              Continuar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
