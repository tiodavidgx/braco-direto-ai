import { useState, useEffect, useCallback, useRef } from "react";
import * as XLSX from "xlsx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  useDroppable,
  useDraggable,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { 
  Upload, 
  Download,
  DollarSign, 
  Calendar, 
  Clock, 
  Users, 
  Plus,
  Trash2,
  RefreshCw,
  Zap,
  GripVertical,
  X,
  Check,
  ArrowRight,
  Ban,
  AlertTriangle,
  ArrowUpDown,
  Scissors,
  SplitSquareHorizontal,
  Lock,
  Unlock,
  Building2,
  Undo2
} from "lucide-react";

// Função para determinar a URL da API baseado no ambiente
const getApiBaseUrl = (): string => {
  // Em produção, usa a mesma origem da página
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return `${window.location.origin}/api/v1`;
  }
  return 'http://localhost:14001/api/v1';
};

const API_URL = getApiBaseUrl();

// Tipos
interface Titulo {
  id: number;
  numero_titulo?: string;
  numero_documento?: string;
  nome_fornecedor: string;
  cod_fornecedor?: string;
  cnpj_cpf?: string;
  valor: number;
  data_vencimento: string;
  data_emissao?: string;
  descricao?: string;
  categoria?: string;
  status: string;
  tier: number;
  data_agendamento?: string;
  lote_importacao?: string;
  // Dados bancários
  banco?: string;
  agencia?: string;
  conta?: string;
  pix?: string;
  // Campos de parcelamento
  titulo_original_id?: number;
  parcela_numero?: number;
  parcela_total?: number;
  // Campos completos do ERP
  id_titulo_pagar?: string;
  num_orcom?: string;
  filial?: string;
  empresa?: string;
  data_pagamento?: string;
  tipo?: string;
  tipo_movimento?: string;
  situacao?: string;
  documento_dev?: string;
  liberacao?: string;
  empenho?: string;
  carne?: string;
  valor_titulo?: number;
  valor_antecipado?: number;
  valor_desconto?: number;
  valor_desconto_tributacao?: number;
  instrucao_pagamento?: string;
  grupo_conta?: string;
  seu_numero?: string;
  vinculado_lote?: string;
  lote_erp?: string;
}

interface Fornecedor {
  id: number;
  nome_fornecedor: string;
  cnpj_cpf?: string;
  tier: number;
  max_dias_atraso: number;
  notas?: string;
}

interface Excecao {
  id: number;
  nome_fornecedor: string;
  valor_solicitado: number;
  data_necessidade: string;
  motivo: string;
  status: string;
}

interface DiaRoteiro {
  data: string;
  dia_semana: string;
  titulos: Titulo[];
}

// Formatação
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
};

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-';
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('pt-BR');
};

const formatDateShort = (dateStr: string) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
};

const getTierConfig = (tier: number) => {
  const configs: Record<number, { emoji: string; label: string; color: string; bgColor: string }> = {
    1: { emoji: "🔴", label: "Crítico", color: "text-red-600", bgColor: "bg-red-50/80 border-red-100 hover:bg-red-50" },
    2: { emoji: "🟠", label: "Alta", color: "text-orange-600", bgColor: "bg-orange-50/80 border-orange-100 hover:bg-orange-50" },
    3: { emoji: "🟡", label: "Média", color: "text-yellow-600", bgColor: "bg-amber-50/80 border-amber-100 hover:bg-amber-50" },
    4: { emoji: "🟢", label: "Baixa", color: "text-green-600", bgColor: "bg-emerald-50/80 border-emerald-100 hover:bg-emerald-50" },
  };
  return configs[tier] || configs[3];
};

// Componente Card de Título Arrastável
interface TituloCardProps {
  titulo: Titulo;
  onRemove?: () => void;
  onDelete?: () => void;
  onMerge?: () => void;
  onSplit?: (tipo: 'iguais' | 'residual' | 'customizado', config?: { numParcelas?: number; valorPrimeira?: number; valoresParcelas?: number[] }) => void;
  isDragging?: boolean;
  showDelete?: boolean;
  showSplit?: boolean;
}

function TituloCard({ titulo, onRemove, onDelete, onMerge, onSplit, isDragging, showDelete, showSplit }: TituloCardProps) {
  const [confirmDelete, setConfirmDelete] = useState<'confirm' | 'options' | null>(null);
  const [showSplitDialog, setShowSplitDialog] = useState<'iguais' | 'residual' | 'customizado' | null>(null);
  const [numParcelas, setNumParcelas] = useState(2);
  const [valorPrimeira, setValorPrimeira] = useState(40000);
  const [valoresParcelas, setValoresParcelas] = useState<number[]>([]);
  
  const tierConfig = getTierConfig(titulo.tier);
  const diasAtraso = Math.floor((new Date().getTime() - new Date(titulo.data_vencimento + 'T00:00:00').getTime()) / (1000 * 60 * 60 * 24));
  const isParcela = titulo.parcela_numero && titulo.parcela_total;

  const handleSplitConfirm = () => {
    if (!onSplit || !showSplitDialog) return;
    
    if (showSplitDialog === 'iguais') {
      onSplit('iguais', { numParcelas });
    } else if (showSplitDialog === 'residual') {
      onSplit('residual', { valorPrimeira });
    } else if (showSplitDialog === 'customizado') {
      // Verificar se a soma bate com o total
      const soma = valoresParcelas.reduce((a, b) => a + b, 0);
      if (Math.abs(soma - titulo.valor) > 0.01) {
        alert(`A soma das parcelas (${formatCurrency(soma)}) deve ser igual ao valor total (${formatCurrency(titulo.valor)})`);
        return;
      }
      onSplit('customizado', { valoresParcelas });
    }
    setShowSplitDialog(null);
  };

  // Inicializar parcelas customizadas quando abrir o dialog
  const initCustomParcelas = () => {
    // Começar com 2 parcelas: metade e metade
    const metade = Math.floor(titulo.valor / 2 * 100) / 100;
    setValoresParcelas([metade, titulo.valor - metade]);
    setShowSplitDialog('customizado');
  };

  const addParcela = () => {
    const novasParc = [...valoresParcelas, 0];
    setValoresParcelas(novasParc);
  };

  const removeParcela = (index: number) => {
    if (valoresParcelas.length <= 2) return;
    const novasParc = valoresParcelas.filter((_, i) => i !== index);
    setValoresParcelas(novasParc);
  };

  const updateParcela = (index: number, valor: number) => {
    const novasParc = [...valoresParcelas];
    novasParc[index] = valor;
    setValoresParcelas(novasParc);
  };

  const distribuirRestante = () => {
    const soma = valoresParcelas.reduce((a, b) => a + b, 0);
    const restante = titulo.valor - soma;
    if (valoresParcelas.length > 0) {
      const novasParc = [...valoresParcelas];
      novasParc[novasParc.length - 1] += restante;
      novasParc[novasParc.length - 1] = Math.round(novasParc[novasParc.length - 1] * 100) / 100;
      setValoresParcelas(novasParc);
    }
  };
  
  return (
    <>
      <div 
        className={`
          p-2 rounded-lg border mb-1.5 cursor-grab active:cursor-grabbing
          transition-all duration-200
          ${tierConfig.bgColor}
          ${isDragging ? 'opacity-50 scale-105 shadow-lg z-50' : 'hover:shadow-sm'}
        `}
      >
        {/* Linha 1: Nome + Valor + Ações */}
        <div className="flex items-center justify-between gap-1">
          <div className="flex items-center gap-1 min-w-0 flex-1">
            <GripVertical className="h-3 w-3 text-gray-400 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="font-medium text-[11px] truncate leading-tight" title={titulo.nome_fornecedor}>
                {titulo.nome_fornecedor}
              </div>
              <div className="flex items-center gap-1">
                <span className="text-xs font-bold text-gray-800">{formatCurrency(titulo.valor)}</span>
                {titulo.numero_titulo && (
                  <span className="text-[9px] text-muted-foreground truncate max-w-[60px]" title={titulo.numero_titulo}>
                    #{titulo.numero_titulo}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-0.5 flex-shrink-0">
            {showSplit && onSplit && titulo.valor > 1000 && !isParcela && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                  <Button variant="ghost" size="sm" className="h-4 w-4 p-0 hover:bg-blue-100" title="Dividir">
                    <Scissors className="h-2.5 w-2.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-44" onClick={(e) => e.stopPropagation()}>
                  <DropdownMenuItem onClick={() => setShowSplitDialog('iguais')}>
                    <SplitSquareHorizontal className="h-3 w-3 mr-2" />
                    Parcelas iguais
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setShowSplitDialog('residual')}>
                    <DollarSign className="h-3 w-3 mr-2" />
                    R$40k + Residual
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => initCustomParcelas()}>
                    <Scissors className="h-3 w-3 mr-2" />
                    Valores personalizados
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            {onRemove && (
              <Button variant="ghost" size="sm" className="h-4 w-4 p-0 hover:bg-gray-200"
                onClick={(e) => { e.stopPropagation(); onRemove(); }} title="Remover">
                <X className="h-2.5 w-2.5" />
              </Button>
            )}
            {showDelete && onDelete && (
              confirmDelete === 'options' && isParcela ? (
                <div className="flex gap-0.5" onClick={(e) => e.stopPropagation()}>
                  <Button variant="destructive" size="sm" className="h-4 px-1 text-[9px]"
                    onClick={(e) => { e.stopPropagation(); onDelete(); setConfirmDelete(null); }}>🗑️</Button>
                  {onMerge && (
                    <Button variant="outline" size="sm" className="h-4 px-1 text-[9px] bg-purple-50"
                      onClick={(e) => { e.stopPropagation(); onMerge(); setConfirmDelete(null); }}>🔄</Button>
                  )}
                  <Button variant="ghost" size="sm" className="h-4 px-1 text-[9px]"
                    onClick={(e) => { e.stopPropagation(); setConfirmDelete(null); }}>✕</Button>
                </div>
              ) : confirmDelete === 'confirm' ? (
                <div className="flex gap-0.5" onClick={(e) => e.stopPropagation()}>
                  <Button variant="destructive" size="sm" className="h-4 px-1 text-[9px]"
                    onClick={(e) => { e.stopPropagation(); onDelete(); setConfirmDelete(null); }}>Sim</Button>
                  <Button variant="outline" size="sm" className="h-4 px-1 text-[9px]"
                    onClick={(e) => { e.stopPropagation(); setConfirmDelete(null); }}>Não</Button>
                </div>
              ) : (
                <Button variant="ghost" size="sm" className="h-4 w-4 p-0 hover:bg-red-100 hover:text-red-600"
                  onClick={(e) => { e.stopPropagation(); setConfirmDelete(isParcela ? 'options' : 'confirm'); }}
                  title={isParcela ? "Opções" : "Excluir"}>
                  <Trash2 className="h-2.5 w-2.5" />
                </Button>
              )
            )}
          </div>
        </div>
        
        {/* Linha 2: Badges compactos */}
        <div className="flex items-center gap-1 mt-0.5 flex-wrap">
          <Badge variant="outline" className={`${tierConfig.color} text-[9px] px-1 py-0 h-3.5`}>
            {tierConfig.emoji} T{titulo.tier}
          </Badge>
          {isParcela && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant="secondary" className="text-[9px] px-1 py-0 h-3.5 bg-purple-100 text-purple-700 cursor-help">
                  ✂️ {titulo.parcela_numero}/{titulo.parcela_total}
                </Badge>
              </TooltipTrigger>
              <TooltipContent side="top" className="text-xs">
                <p>Parcela {titulo.parcela_numero} de {titulo.parcela_total}</p>
              </TooltipContent>
            </Tooltip>
          )}
          <span className="text-[9px] text-muted-foreground">
            {formatDateShort(titulo.data_vencimento)}
          </span>
          {diasAtraso > 0 && (
            <Badge variant="destructive" className="text-[9px] px-1 py-0 h-3.5">
              {diasAtraso}d
            </Badge>
          )}
        </div>
      </div>

      {/* Dialog de Split */}
      <Dialog open={showSplitDialog !== null} onOpenChange={(open) => !open && setShowSplitDialog(null)}>
        <DialogContent className="sm:max-w-md" onClick={(e) => e.stopPropagation()}>
          <DialogHeader>
            <DialogTitle>
              {showSplitDialog === 'iguais' && '✂️ Dividir em Parcelas Iguais'}
              {showSplitDialog === 'residual' && '💰 R$40k + Residual'}
              {showSplitDialog === 'customizado' && '🔧 Valor Customizado'}
            </DialogTitle>
            <DialogDescription>
              Valor total: <strong>{formatCurrency(titulo.valor)}</strong>
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {showSplitDialog === 'iguais' && (
              <>
                <div className="space-y-2">
                  <Label>Número de parcelas</Label>
                  <Input type="number" min={2} max={10} value={numParcelas}
                    onChange={(e) => setNumParcelas(parseInt(e.target.value) || 2)} />
                </div>
                <div className="bg-gray-50 p-3 rounded-lg text-sm">
                  <div className="font-medium mb-1">Prévia:</div>
                  {Array.from({ length: numParcelas }).map((_, i) => (
                    <div key={i} className="flex justify-between">
                      <span>Parcela {i + 1}:</span>
                      <span className="font-bold">{formatCurrency(titulo.valor / numParcelas)}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
            
            {showSplitDialog === 'residual' && (
              <div className="bg-gray-50 p-3 rounded-lg text-sm">
                <div className="font-medium mb-2">Prévia (R$40.000 + Residual):</div>
                {(() => {
                  const limite = 40000;
                  const numParcelas40k = Math.floor(titulo.valor / limite);
                  const residual = titulo.valor % limite;
                  const parcelas = [];
                  for (let i = 0; i < numParcelas40k; i++) {
                    parcelas.push({ label: `Parcela ${i + 1}`, valor: limite });
                  }
                  if (residual > 0) {
                    parcelas.push({ label: `Residual`, valor: residual });
                  }
                  return parcelas.map((p, i) => (
                    <div key={i} className="flex justify-between">
                      <span>{p.label}:</span>
                      <span className="font-bold">{formatCurrency(p.valor)}</span>
                    </div>
                  ));
                })()}
              </div>
            )}
            
            {showSplitDialog === 'customizado' && (
              <>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <Label>Parcelas personalizadas</Label>
                    <Button type="button" variant="outline" size="sm" onClick={addParcela} className="h-7 text-xs">
                      <Plus className="h-3 w-3 mr-1" /> Adicionar
                    </Button>
                  </div>
                  
                  {valoresParcelas.map((valor, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-sm text-gray-500 w-16">Parcela {index + 1}</span>
                      <Input 
                        type="number" 
                        min={0} 
                        step={100}
                        value={valor || ''}
                        onChange={(e) => updateParcela(index, parseFloat(e.target.value) || 0)} 
                        className="flex-1"
                      />
                      {valoresParcelas.length > 2 && (
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeParcela(index)} className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>

                <div className="bg-gray-50 p-3 rounded-lg text-sm space-y-2">
                  <div className="flex justify-between">
                    <span>Soma das parcelas:</span>
                    <span className={`font-bold ${Math.abs(valoresParcelas.reduce((a, b) => a + b, 0) - titulo.valor) > 0.01 ? 'text-red-600' : 'text-green-600'}`}>
                      {formatCurrency(valoresParcelas.reduce((a, b) => a + b, 0))}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Valor total:</span>
                    <span className="font-bold">{formatCurrency(titulo.valor)}</span>
                  </div>
                  {Math.abs(valoresParcelas.reduce((a, b) => a + b, 0) - titulo.valor) > 0.01 && (
                    <div className="flex justify-between items-center pt-1 border-t">
                      <span className="text-red-600">Diferença: {formatCurrency(titulo.valor - valoresParcelas.reduce((a, b) => a + b, 0))}</span>
                      <Button type="button" variant="outline" size="sm" onClick={distribuirRestante} className="h-6 text-xs">
                        Ajustar última
                      </Button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSplitDialog(null)}>Cancelar</Button>
            <Button 
              onClick={handleSplitConfirm}
              disabled={showSplitDialog === 'customizado' && Math.abs(valoresParcelas.reduce((a, b) => a + b, 0) - titulo.valor) > 0.01}
            >
              Confirmar Divisão
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Componente Draggable (para pendentes - apenas arrasta, não reordena)
function DraggableTituloCard({ titulo, onDelete, onMerge, onSplit }: { 
  titulo: Titulo; 
  onDelete?: () => void;
  onMerge?: () => void;
  onSplit?: (tipo: 'iguais' | 'residual' | 'customizado', config?: { numParcelas?: number; valorPrimeira?: number; valoresParcelas?: number[] }) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  } = useDraggable({ id: `titulo-${titulo.id}` });

  const style: React.CSSProperties = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    touchAction: 'none',
    cursor: isDragging ? 'grabbing' : 'grab',
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <TituloCard 
        titulo={titulo} 
        isDragging={isDragging} 
        showDelete={!!onDelete} 
        onDelete={onDelete}
        onMerge={onMerge}
        showSplit={!!onSplit}
        onSplit={onSplit}
      />
    </div>
  );
}

// Componente Sortable (para dias do roteiro - pode reordenar)
function SortableTituloCard({ titulo, onRemove, disabled }: { titulo: Titulo; onRemove: () => void; disabled?: boolean }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `titulo-${titulo.id}`, disabled });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    touchAction: 'none',
    cursor: disabled ? 'default' : isDragging ? 'grabbing' : 'grab',
    opacity: disabled ? 0.8 : 1,
  };

  // Quando disabled, não passa os listeners para impedir qualquer interação de drag
  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      {...attributes} 
      {...(disabled ? {} : listeners)}
    >
      <TituloCard titulo={titulo} onRemove={disabled ? undefined : onRemove} isDragging={isDragging} />
    </div>
  );
}

// Componente Coluna de Pendentes (Droppable)
interface PendentesColumnProps {
  titulos: Titulo[];
  total: number;
  filtroTier: number | null;
  setFiltroTier: (tier: number | null) => void;
  filtroFornecedor: string;
  setFiltroFornecedor: (fornecedor: string) => void;
  ordenacao: 'padrao' | 'valor_asc' | 'valor_desc';
  setOrdenacao: (ord: 'padrao' | 'valor_asc' | 'valor_desc') => void;
  onDeleteTitulo: (id: number) => void;
  onMergeTitulo: (id: number) => void;
  onSplitTitulo: (id: number, tipo: 'iguais' | 'residual' | 'customizado', config?: { numParcelas?: number; valorPrimeira?: number; valoresParcelas?: number[] }) => void;
}

function PendentesColumn({ titulos, total, filtroTier, setFiltroTier, filtroFornecedor, setFiltroFornecedor, ordenacao, setOrdenacao, onDeleteTitulo, onMergeTitulo, onSplitTitulo }: PendentesColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: 'pendentes',
  });

  // Aplicar filtros
  let titulosFiltrados = titulos.filter(t => {
    if (filtroTier !== null && t.tier !== filtroTier) return false;
    if (filtroFornecedor) {
      const busca = filtroFornecedor.toLowerCase();
      const matchFornecedor = t.nome_fornecedor.toLowerCase().includes(busca);
      const matchTitulo = String(t.numero_titulo || '').toLowerCase().includes(busca);
      const matchId = String(t.id).includes(busca);
      if (!matchFornecedor && !matchTitulo && !matchId) return false;
    }
    return true;
  });

  // Aplicar ordenação
  if (ordenacao === 'valor_asc') {
    titulosFiltrados = [...titulosFiltrados].sort((a, b) => a.valor - b.valor);
  } else if (ordenacao === 'valor_desc') {
    titulosFiltrados = [...titulosFiltrados].sort((a, b) => b.valor - a.valor);
  }

  const totalFiltrado = titulosFiltrados.reduce((sum, t) => sum + t.valor, 0);

  const toggleOrdenacao = () => {
    if (ordenacao === 'padrao') setOrdenacao('valor_asc');
    else if (ordenacao === 'valor_asc') setOrdenacao('valor_desc');
    else setOrdenacao('padrao');
  };

  return (
    <div 
      ref={setNodeRef}
      className={`
        flex-shrink-0 w-72 rounded-xl border transition-all flex flex-col bg-white overflow-hidden
        ${isOver ? 'ring-2 ring-emerald-400 border-emerald-400' : 'border-amber-200'}
      `}
      style={{ maxHeight: '520px' }}
    >
      <div className="p-3 bg-amber-50 border-b border-amber-100 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-amber-600" />
            <span className="font-semibold text-sm text-gray-800">Pendentes</span>
            <span className="text-xs text-gray-500 bg-white px-1.5 py-0.5 rounded-full">
              {titulosFiltrados.length}/{titulos.length}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={toggleOrdenacao}
              className={`p-1 rounded-lg hover:bg-amber-100 ${ordenacao !== 'padrao' ? 'bg-amber-100' : ''}`}
              title={ordenacao === 'padrao' ? 'Ordenar por valor' : ordenacao === 'valor_asc' ? 'Menor → Maior' : 'Maior → Menor'}
            >
              <ArrowUpDown className="h-3.5 w-3.5 text-gray-600" />
            </button>
            {[1, 2, 3, 4].map(t => (
              <button
                key={t}
                onClick={() => setFiltroTier(filtroTier === t ? null : t)}
                className={`w-5 h-5 rounded-full text-[10px] transition-all ${filtroTier === t ? 'ring-2 ring-offset-1 ring-gray-400 scale-110' : 'opacity-60 hover:opacity-100'}`}
              >
                {t === 1 ? '🔴' : t === 2 ? '🟠' : t === 3 ? '🟡' : '🟢'}
              </button>
            ))}
          </div>
        </div>
        <div className="text-sm font-bold text-amber-700 mt-1">{formatCurrency(totalFiltrado)}</div>
        <div className="relative mt-2">
          <Input
            placeholder="Buscar fornecedor ou título..."
            value={filtroFornecedor}
            onChange={(e) => setFiltroFornecedor(e.target.value)}
            className="h-8 text-xs bg-white border-amber-200 pl-8"
          />
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-1.5">
        {titulosFiltrados.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            <Check className="h-8 w-8 mx-auto mb-2 opacity-30" />
            {titulos.length === 0 ? 'Todos agendados!' : 'Nenhum título com este filtro'}
          </div>
        ) : (
          titulosFiltrados.map((titulo) => (
            <DraggableTituloCard
              key={titulo.id}
              titulo={titulo}
              onDelete={() => onDeleteTitulo(titulo.id)}
              onMerge={titulo.parcela_numero ? () => onMergeTitulo(titulo.id) : undefined}
              onSplit={(tipo, config) => onSplitTitulo(titulo.id, tipo, config)}
            />
          ))
        )}
      </div>
    </div>
  );
}

// Componente Coluna do Dia (Droppable)
interface DiaColumnProps {
  dia: DiaRoteiro;
  diaIndex: number;
  orcamento: number;
  onRemoveTitulo: (tituloId: number) => void;
  onCancelarDia: (data: string) => void;
  onCompletarOrcamento: (diaIndex: number, saldo: number) => void;
  onDownloadDia: (dia: DiaRoteiro) => void;
  isBloqueado: boolean;
  onToggleBloqueio: () => void;
  filtroGlobal?: string;
}

function DiaColumn({ dia, diaIndex, orcamento, onRemoveTitulo, onCancelarDia, onCompletarOrcamento, onDownloadDia, isBloqueado, onToggleBloqueio, filtroGlobal }: DiaColumnProps) {
  
  const total = dia.titulos.reduce((sum, t) => sum + t.valor, 0);
  const saldo = orcamento - total;
  const isOverBudget = saldo < 0;
  const hoje = new Date().toISOString().split('T')[0];
  const isToday = dia.data === hoje;
  const isPast = dia.data < hoje;

  // Contar matches do filtro global neste dia
  const busca = filtroGlobal?.toLowerCase();
  const matchCount = busca ? dia.titulos.filter(t => 
    t.nome_fornecedor.toLowerCase().includes(busca) ||
    String(t.numero_titulo || '').toLowerCase().includes(busca) ||
    String(t.id).includes(busca)
  ).length : 0;
  const hasMatches = busca && matchCount > 0;

  // Usar ID diferente baseado no estado de bloqueio para forçar re-registro do droppable
  const droppableId = isBloqueado ? `dia-${diaIndex}-blocked` : `dia-${diaIndex}`;
  
  const { setNodeRef, isOver } = useDroppable({
    id: droppableId,
    disabled: isBloqueado,
  });

  return (
    <div 
      ref={setNodeRef}
      className={`
        flex-shrink-0 w-64 rounded-xl border transition-all flex flex-col bg-white overflow-hidden
        ${hasMatches ? 'ring-2 ring-blue-500 border-blue-500' : ''}
        ${isBloqueado ? (isPast ? 'opacity-75 border-gray-300' : 'ring-2 ring-amber-400 border-amber-400') : isToday ? 'ring-2 ring-gray-400 ring-offset-2' : !hasMatches ? 'border-gray-200' : ''}
        ${isOver && !isBloqueado ? 'ring-2 ring-emerald-400 border-emerald-400' : ''}
        ${busca && !hasMatches && dia.titulos.length > 0 ? 'opacity-40' : ''}
      `}
      style={{ maxHeight: '520px' }}
    >
      {/* Header do dia */}
      <div className={`p-3 flex-shrink-0 ${isBloqueado ? (isPast ? 'bg-gray-400' : 'bg-amber-500') + ' text-white' : isPast ? 'bg-emerald-600 text-white' : isToday ? 'bg-gray-800 text-white' : 'bg-gray-50 border-b border-gray-100'}`}>
        <div className="flex justify-between items-center">
          <div>
            <div className={`font-semibold text-sm ${isBloqueado || isToday || isPast ? 'text-white' : 'text-gray-800'}`}>
              {dia.dia_semana}
              {hasMatches && (
                <span className="ml-1.5 inline-flex items-center justify-center bg-blue-500 text-white text-[9px] font-bold rounded-full w-4 h-4">
                  {matchCount}
                </span>
              )}
            </div>
            <div className={`text-xs ${isBloqueado ? (isPast ? 'text-gray-200' : 'text-amber-100') : isPast ? 'text-emerald-100' : isToday ? 'text-gray-300' : 'text-gray-500'}`}>{formatDate(dia.data)}</div>
          </div>
          <div className="flex items-center gap-1">
            {/* Botão de bloquear/desbloquear - aparece em todos os dias */}
            <Button 
              variant="ghost" 
              size="sm" 
              className={`h-6 w-6 p-0 ${isBloqueado ? 'text-white hover:text-amber-100 hover:bg-white/10' : isToday ? 'text-gray-300 hover:text-white hover:bg-white/10' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
              onClick={onToggleBloqueio}
              title={isBloqueado ? 'Desbloquear dia para edição' : 'Bloquear dia'}
            >
              {isBloqueado ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
            </Button>
            {isPast && !isBloqueado && <Badge className="bg-emerald-500/80 text-white border-0 text-[10px] px-1.5">�</Badge>}
            {isToday && !isBloqueado && <Badge className="bg-white/20 text-white border-0 text-[10px] px-1.5">Hoje</Badge>}
            {dia.titulos.length > 0 && (
              <Button 
                variant="ghost" 
                size="sm" 
                className={`h-6 w-6 p-0 ${isBloqueado || isToday ? 'text-emerald-300 hover:text-emerald-200 hover:bg-white/10' : 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50'}`}
                onClick={() => onDownloadDia(dia)}
                title="Baixar lista de pagamentos (XLSX)"
              >
                <Download className="h-3.5 w-3.5" />
              </Button>
            )}
            {saldo > 0 && !isBloqueado && (
              <Button 
                variant="ghost" 
                size="sm" 
                className={`h-6 w-6 p-0 ${isToday ? 'text-amber-300 hover:text-amber-200 hover:bg-white/10' : 'text-amber-600 hover:text-amber-700 hover:bg-amber-50'}`}
                onClick={() => onCompletarOrcamento(diaIndex, saldo)}
                title="Completar orçamento (puxar títulos que cabem no saldo)"
              >
                <Zap className="h-3.5 w-3.5" />
              </Button>
            )}
            {dia.titulos.length > 0 && !isBloqueado && (
              <Button 
                variant="ghost" 
                size="sm" 
                className={`h-6 w-6 p-0 ${isToday ? 'text-red-300 hover:text-red-200 hover:bg-white/10' : 'text-red-500 hover:text-red-700 hover:bg-red-50'}`}
                onClick={() => onCancelarDia(dia.data)}
                title="Cancelar pagamentos deste dia"
              >
                <Ban className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>
        <div className={`mt-2 pt-2 border-t text-xs ${isBloqueado && !isPast ? 'border-amber-400' : isToday || isPast ? 'border-white/20' : 'border-gray-200'}`}>
          <div className="flex justify-between">
            <span className={isBloqueado || isToday || isPast ? 'text-gray-300' : 'text-gray-500'}>Total:</span>
            <span className="font-bold">{formatCurrency(total)}</span>
          </div>
          <div className={`flex justify-between ${isOverBudget ? 'text-red-400' : isBloqueado || isToday || isPast ? 'text-emerald-300' : 'text-emerald-600'}`}>
            <span className={isBloqueado || isToday || isPast ? 'text-gray-300' : 'text-gray-500'}>Saldo:</span>
            <span className="font-bold">{formatCurrency(saldo)}</span>
          </div>
        </div>
      </div>

      {/* Lista de títulos */}
      <div className="flex-1 overflow-y-auto p-1.5">
        <SortableContext
          items={dia.titulos.map(t => `titulo-${t.id}`)}
          strategy={verticalListSortingStrategy}
        >
          {dia.titulos.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-xs">
              <Calendar className="h-6 w-6 mx-auto mb-2 opacity-30" />
              {isBloqueado ? 'Dia bloqueado' : 'Arraste títulos para cá'}
            </div>
          ) : (
            dia.titulos.map((titulo) => {
              const busca = filtroGlobal?.toLowerCase();
              const isMatch = !busca || 
                titulo.nome_fornecedor.toLowerCase().includes(busca) ||
                String(titulo.numero_titulo || '').toLowerCase().includes(busca) ||
                String(titulo.id).includes(busca);
              return (
                <div key={titulo.id} className={busca && !isMatch ? 'opacity-15' : busca && isMatch ? 'ring-2 ring-blue-400 rounded-lg' : ''}>
                  <SortableTituloCard
                    titulo={titulo}
                    onRemove={() => onRemoveTitulo(titulo.id)}
                    disabled={isBloqueado}
                  />
                </div>
              );
            })
          )}
        </SortableContext>
      </div>

      {/* Resumo por Fornecedor do dia */}
      {dia.titulos.length > 0 && (
        <div className="flex-shrink-0 border-t border-gray-100 bg-gray-50/80 p-2">
          <div className="text-[10px] font-medium text-gray-500 mb-1.5 flex items-center gap-1">
            <Building2 className="h-3 w-3" />
            Por fornecedor:
          </div>
          <div className="space-y-0.5 max-h-24 overflow-y-auto">
            {(() => {
              // Agrupar por fornecedor
              const fornMap = new Map<string, { count: number; valor: number }>();
              dia.titulos.forEach(t => {
                const nome = t.nome_fornecedor;
                const atual = fornMap.get(nome) || { count: 0, valor: 0 };
                fornMap.set(nome, { count: atual.count + 1, valor: atual.valor + t.valor });
              });
              
              // Ordenar por valor (menor para maior)
              const fornecedores = Array.from(fornMap.entries())
                .map(([nome, data]) => ({ nome, ...data }))
                .sort((a, b) => a.valor - b.valor);
              
              return fornecedores.map((f, i) => (
                <div key={i} className="flex items-center justify-between text-[10px] py-0.5 px-1 rounded hover:bg-gray-100">
                  <span className="truncate text-gray-600 max-w-[130px]" title={f.nome}>
                    {f.nome.length > 20 ? f.nome.substring(0, 20) + '...' : f.nome}
                  </span>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-gray-400">({f.count})</span>
                    <span className="font-medium text-gray-700">{formatCurrency(f.valor)}</span>
                  </div>
                </div>
              ));
            })()}
          </div>
        </div>
      )}
    </div>
  );
}

// Componente Principal
export default function GestaoPagamentos() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("roteiro");
  
  // Refs para scroll automático ao dia atual
  const diasScrollRef = useRef<HTMLDivElement>(null);
  const todayColumnRef = useRef<HTMLDivElement>(null);
  const hasScrolledToToday = useRef(false);
  
  // Estado centralizado de bloqueio manual por dia (data -> boolean)
  // Para dias passados: true = desbloqueado manualmente
  // Para dias futuros/hoje: true = bloqueado manualmente
  // Persistido no localStorage para manter entre reloads
  const [manualOverrides, setManualOverrides] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem('gestao-pagamentos-bloqueios');
      if (saved) {
        const parsed = JSON.parse(saved);
        console.log('Bloqueios carregados do localStorage:', parsed);
        return parsed;
      }
      return {};
    } catch (e) {
      console.error('Erro ao carregar bloqueios:', e);
      return {};
    }
  });
  
  // Flag para evitar salvar no primeiro render
  const [bloqueiosCarregados, setBloqueiosCarregados] = useState(false);
  
  // Marcar como carregado após o primeiro render
  useEffect(() => {
    setBloqueiosCarregados(true);
  }, []);
  
  // Salvar no localStorage quando mudar (após carregar)
  useEffect(() => {
    if (!bloqueiosCarregados) return; // Não salvar no primeiro render
    try {
      console.log('Salvando bloqueios no localStorage:', manualOverrides);
      localStorage.setItem('gestao-pagamentos-bloqueios', JSON.stringify(manualOverrides));
    } catch (e) {
      console.error('Erro ao salvar bloqueios:', e);
    }
  }, [manualOverrides, bloqueiosCarregados]);
  
  // Função para verificar se um dia está bloqueado
  const isDiaBloqueado = useCallback((data: string) => {
    const hoje = new Date().toISOString().split('T')[0];
    const isPast = data < hoje;
    const hasOverride = manualOverrides[data] || false;
    // Dias passados: bloqueados por padrão, override desbloqueia
    // Dias futuros/hoje: desbloqueados por padrão, override bloqueia
    return isPast ? !hasOverride : hasOverride;
  }, [manualOverrides]);
  
  // Função para toggle do bloqueio
  const toggleBloqueio = useCallback((data: string) => {
    setManualOverrides(prev => ({
      ...prev,
      [data]: !prev[data]
    }));
  }, []);
  
  // Quantidade de dias úteis passados a exibir
  const DIAS_PASSADOS = 10;

  // Função para gerar dias iniciais
  const gerarDiasIniciais = () => {
    const hoje = new Date();
    const dias: DiaRoteiro[] = [];
    const diasSemana = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];

    // Gerar dias passados (DIAS_PASSADOS dias úteis para trás)
    const diasPassadosArr: DiaRoteiro[] = [];
    let diasAdicionados = 0;
    let offset = 1; // começar em -1 (ontem)
    while (diasAdicionados < DIAS_PASSADOS) {
      const data = new Date(hoje);
      data.setDate(data.getDate() - offset);
      offset++;
      if (data.getDay() === 0) continue; // Pular domingo
      diasPassadosArr.unshift({
        data: data.toISOString().split('T')[0],
        dia_semana: diasSemana[data.getDay()],
        titulos: [],
      });
      diasAdicionados++;
    }

    // Gerar dias futuros (20 dias úteis para frente, incluindo hoje)
    diasAdicionados = 0;
    offset = 0;
    while (diasAdicionados < 20) {
      const data = new Date(hoje);
      data.setDate(data.getDate() + offset);
      offset++;
      if (data.getDay() === 0) continue; // Pular domingo
      dias.push({
        data: data.toISOString().split('T')[0],
        dia_semana: diasSemana[data.getDay()],
        titulos: [],
      });
      diasAdicionados++;
    }

    return [...diasPassadosArr, ...dias];
  };
  
  // Estados
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [excecoes, setExcecoes] = useState<Excecao[]>([]);
  const [titulosPendentes, setTitulosPendentes] = useState<Titulo[]>([]);
  const [roteiro, setRoteiro] = useState<DiaRoteiro[]>(gerarDiasIniciais);
  const [orcamentoDiario, setOrcamentoDiario] = useState(40000);
  const [diasRoteiro, setDiasRoteiro] = useState(20);
  
  // Drag and Drop
  const [activeTitulo, setActiveTitulo] = useState<Titulo | null>(null);
  
  // Dialogs
  const [dialogFornecedor, setDialogFornecedor] = useState(false);
  const [dialogExcecao, setDialogExcecao] = useState(false);
  const [dialogImport, setDialogImport] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<{ tipo: string; id: number } | null>(null);
  
  // Dialog Completar Orçamento (Raio)
  const [dialogCompletarOrcamento, setDialogCompletarOrcamento] = useState<{ diaIndex: number; saldo: number } | null>(null);
  const [fornecedorPriorizado, setFornecedorPriorizado] = useState<string>('');
  const [sugestoesFornecedorRaio, setSugestoesFornecedorRaio] = useState<{nome_fornecedor: string, total_titulos: number, valor_total: number}[]>([]);
  
  // Forms
  const [novoFornecedor, setNovoFornecedor] = useState<Partial<Fornecedor>>({ tier: 3, max_dias_atraso: 5 });
  const [novaExcecao, setNovaExcecao] = useState<Partial<Excecao>>({});
  const [arquivoImport, setArquivoImport] = useState<File | null>(null);
  
  // Filtros de pendentes
  const [filtroTier, setFiltroTier] = useState<number | null>(null);
  const [filtroFornecedor, setFiltroFornecedor] = useState('');
  const [ordenacaoPendentes, setOrdenacaoPendentes] = useState<'padrao' | 'valor_asc' | 'valor_desc'>('padrao');
  
  // Autocomplete fornecedores
  const [sugestoesFornecedor, setSugestoesFornecedor] = useState<{nome_fornecedor: string, cod_fornecedor: string | null}[]>([]);
  const [showSugestoes, setShowSugestoes] = useState(false);
  const [buscandoSugestoes, setBuscandoSugestoes] = useState(false);

  // Títulos excluídos (blacklist)
  const [titulosExcluidos, setTitulosExcluidos] = useState<any[]>([]);

  // Sensors para drag
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Buscar sugestões de fornecedores recentes
  const buscarSugestoesFornecedor = useCallback(async (termo: string) => {
    if (!termo || termo.length < 2) {
      setSugestoesFornecedor([]);
      setShowSugestoes(false);
      return;
    }
    
    setBuscandoSugestoes(true);
    try {
      const res = await fetch(`${API_URL}/gestao-pagamentos/fornecedores/recentes?q=${encodeURIComponent(termo)}`);
      if (res.ok) {
        const data = await res.json();
        setSugestoesFornecedor(data);
        setShowSugestoes(data.length > 0);
      }
    } catch (error) {
      console.error("Erro ao buscar sugestões:", error);
    } finally {
      setBuscandoSugestoes(false);
    }
  }, []);

  // Carregar dados
  const carregarOrcamento = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/gestao-pagamentos/orcamento`);
      if (res.ok) {
        const data = await res.json();
        setOrcamentoDiario(data.orcamento_diario);
      }
    } catch (error) {
      console.error("Erro ao carregar orçamento:", error);
    }
  }, []);

  const carregarFornecedores = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/gestao-pagamentos/fornecedores/prioridades`);
      if (res.ok) {
        setFornecedores(await res.json());
      }
    } catch (error) {
      console.error("Erro ao carregar fornecedores:", error);
    }
  }, []);

  const carregarExcecoes = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/gestao-pagamentos/excecoes`);
      if (res.ok) {
        setExcecoes(await res.json());
      }
    } catch (error) {
      console.error("Erro ao carregar exceções:", error);
    }
  }, []);

  const carregarTitulos = useCallback(async () => {
    try {
      // Carregar pendentes
      const resPendentes = await fetch(`${API_URL}/gestao-pagamentos/titulos?status=pendente`);
      if (resPendentes.ok) {
        const titulos = await resPendentes.json();
        setTitulosPendentes(titulos);
      }
      
      // Carregar agendados e organizar por dia
      const resAgendados = await fetch(`${API_URL}/gestao-pagamentos/titulos?status=agendado`);
      if (resAgendados.ok) {
        const titulosAgendados: Titulo[] = await resAgendados.json();
        
        // Agrupar por data_agendamento
        const porData: Record<string, Titulo[]> = {};
        titulosAgendados.forEach(t => {
          if (t.data_agendamento) {
            if (!porData[t.data_agendamento]) {
              porData[t.data_agendamento] = [];
            }
            porData[t.data_agendamento].push(t);
          }
        });
        
        // Atualizar roteiro com títulos agendados
        setRoteiro(prev => {
          const diasSemana = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];
          const datasExistentes = new Set(prev.map(d => d.data));
          
          // Adicionar dias passados que tenham títulos agendados
          const diasPassados: DiaRoteiro[] = [];
          Object.keys(porData).forEach(dataStr => {
            if (!datasExistentes.has(dataStr)) {
              const data = new Date(dataStr + 'T12:00:00');
              diasPassados.push({
                data: dataStr,
                dia_semana: diasSemana[data.getDay()],
                titulos: porData[dataStr] || []
              });
            }
          });
          
          // Ordenar dias passados por data
          diasPassados.sort((a, b) => a.data.localeCompare(b.data));
          
          // Atualizar dias existentes com seus títulos
          const diasAtualizados = prev.map(dia => ({
            ...dia,
            titulos: porData[dia.data] || []
          }));
          
          // Combinar: dias passados + dias existentes (já ordenados)
          return [...diasPassados, ...diasAtualizados];
        });
      }
    } catch (error) {
      console.error("Erro ao carregar títulos:", error);
    }
  }, []);

  const carregarTudo = useCallback(async () => {
    setLoading(true);
    await Promise.all([carregarOrcamento(), carregarFornecedores(), carregarExcecoes(), carregarTitulos()]);
    setLoading(false);
  }, [carregarOrcamento, carregarFornecedores, carregarExcecoes, carregarTitulos]);

  useEffect(() => {
    carregarTudo();
  }, [carregarTudo]);

  // Calcular dias necessários automaticamente
  const calcularDiasNecessarios = useCallback(() => {
    const totalPendente = titulosPendentes.reduce((sum, t) => sum + t.valor, 0);
    const totalNoRoteiro = roteiro.reduce((sum, dia) => 
      sum + dia.titulos.reduce((s, t) => s + t.valor, 0), 0
    );
    const totalGeral = totalPendente + totalNoRoteiro;
    
    if (totalGeral <= 0 || orcamentoDiario <= 0) return 20; // mínimo 20 dias úteis (~4 semanas)
    
    // Calcular dias necessários + margem de 30%
    const diasCalculados = Math.ceil((totalGeral / orcamentoDiario) * 1.3);
    return Math.max(20, Math.min(diasCalculados, 60)); // entre 20 e 60 dias
  }, [titulosPendentes, roteiro, orcamentoDiario]);

  // Inicializar/atualizar roteiro quando títulos mudam
  useEffect(() => {
    const diasNecessarios = calcularDiasNecessarios();
    
    const hoje = new Date();
    const dias: DiaRoteiro[] = [];
    const diasSemana = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];
    
    // Gerar dias passados (DIAS_PASSADOS dias úteis para trás)
    const diasPassadosArr: DiaRoteiro[] = [];
    let diasAdicionados = 0;
    let offset = 1;
    while (diasAdicionados < DIAS_PASSADOS) {
      const data = new Date(hoje);
      data.setDate(data.getDate() - offset);
      offset++;
      if (data.getDay() === 0) continue;
      const dataStr = data.toISOString().split('T')[0];
      const titulosExistentes = roteiro.find(d => d.data === dataStr)?.titulos || [];
      diasPassadosArr.unshift({
        data: dataStr,
        dia_semana: diasSemana[data.getDay()],
        titulos: titulosExistentes,
      });
      diasAdicionados++;
    }
    
    // Gerar dias futuros (incluindo hoje)
    diasAdicionados = 0;
    offset = 0;
    
    while (diasAdicionados < diasNecessarios) {
      const data = new Date(hoje);
      data.setDate(data.getDate() + offset);
      offset++;
      
      // Pular apenas domingo (0 = domingo)
      if (data.getDay() === 0) continue;
      
      const dataStr = data.toISOString().split('T')[0];
      
      // Manter títulos já agendados para este dia
      const titulosExistentes = roteiro.find(d => d.data === dataStr)?.titulos || [];
      
      dias.push({
        data: dataStr,
        dia_semana: diasSemana[data.getDay()],
        titulos: titulosExistentes,
      });
      diasAdicionados++;
    }
    
    const todosOsDias = [...diasPassadosArr, ...dias];
    
    // Atualizar se número de dias aumentou (nunca diminuir)
    if (todosOsDias.length > roteiro.length) {
      setRoteiro(todosOsDias);
    }
  }, [titulosPendentes, orcamentoDiario, calcularDiasNecessarios]);

  // Scroll automático para o dia atual quando o roteiro carrega
  useEffect(() => {
    if (roteiro.length > 0 && !hasScrolledToToday.current) {
      // Pequeno delay para garantir que o DOM renderizou
      const timer = setTimeout(() => {
        if (todayColumnRef.current && diasScrollRef.current) {
          const container = diasScrollRef.current;
          const todayEl = todayColumnRef.current;
          // Posicionar o dia de hoje no início do scroll (com um pequeno offset)
          const scrollLeft = todayEl.offsetLeft - container.offsetLeft - 12;
          container.scrollTo({ left: scrollLeft, behavior: 'smooth' });
          hasScrolledToToday.current = true;
        } else if (diasScrollRef.current) {
          // Se não encontrou "hoje", procurar o primeiro dia futuro
          const hoje = new Date().toISOString().split('T')[0];
          const primeiroFuturoIndex = roteiro.findIndex(d => d.data >= hoje);
          if (primeiroFuturoIndex > 0) {
            const container = diasScrollRef.current;
            // Cada coluna tem ~268px (w-64 + gap-3)
            const scrollLeft = primeiroFuturoIndex * 268 - 12;
            container.scrollTo({ left: scrollLeft, behavior: 'smooth' });
          }
          hasScrolledToToday.current = true;
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [roteiro]);

  // Gerar roteiro automático
  const gerarRoteiroAutomatico = async () => {
    setLoading(true);
    try {
      // Calcular dias necessários para cobrir tudo
      const totalPendente = titulosPendentes.reduce((sum, t) => sum + t.valor, 0);
      const diasNecessarios = Math.max(5, Math.ceil((totalPendente / orcamentoDiario) * 1.3) + 5);
      
      const res = await fetch(`${API_URL}/gestao-pagamentos/roteiro/gerar?dias=${diasNecessarios}`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        
        // Converter resposta para formato local
        const novoRoteiro: DiaRoteiro[] = data.roteiro.map((dia: any) => ({
          data: dia.data,
          dia_semana: dia.dia_semana,
          titulos: dia.itens
            .filter((item: any) => item.tipo === 'titulo')
            .map((item: any) => ({
              id: item.titulo_id,
              nome_fornecedor: item.nome_fornecedor,
              valor: item.valor,
              data_vencimento: item.data_vencimento,
              tier: item.tier,
              data_agendamento: dia.data,
            }))
        }));
        
        // Usar todos os dias gerados
        setRoteiro(novoRoteiro);
        
        // Atualizar títulos pendentes (remover os que foram agendados)
        const idsAgendados = new Set(
          novoRoteiro.flatMap(dia => dia.titulos.map(t => t.id))
        );
        setTitulosPendentes(prev => prev.filter(t => !idsAgendados.has(t.id)));
        
        toast({ title: "✅ Roteiro gerado automaticamente!" });
      }
    } catch (error) {
      toast({ title: "Erro ao gerar roteiro", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  // Drag handlers
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const id = String(active.id).replace('titulo-', '');
    
    // Procurar título em todos os lugares
    let titulo = titulosPendentes.find(t => t.id === parseInt(id));
    if (!titulo) {
      for (const dia of roteiro) {
        titulo = dia.titulos.find(t => t.id === parseInt(id));
        if (titulo) break;
      }
    }
    
    if (titulo) {
      setActiveTitulo(titulo);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTitulo(null);
    
    if (!over) return;
    
    const activeId = parseInt(String(active.id).replace('titulo-', ''));
    const overId = String(over.id);
    
    // Encontrar o título sendo arrastado
    let tituloArrastado: Titulo | undefined;
    let origemDiaIndex = -1;
    
    // Verificar se está nos pendentes
    const pendentesIndex = titulosPendentes.findIndex(t => t.id === activeId);
    if (pendentesIndex >= 0) {
      tituloArrastado = titulosPendentes[pendentesIndex];
    } else {
      // Procurar no roteiro
      for (let i = 0; i < roteiro.length; i++) {
        const idx = roteiro[i].titulos.findIndex(t => t.id === activeId);
        if (idx >= 0) {
          tituloArrastado = roteiro[i].titulos[idx];
          origemDiaIndex = i;
          break;
        }
      }
    }
    
    if (!tituloArrastado) return;
    
    // Verificar se a origem está bloqueada (não pode remover de dia bloqueado)
    if (origemDiaIndex >= 0 && isDiaBloqueado(roteiro[origemDiaIndex].data)) {
      return; // Não permitir mover de dia bloqueado
    }
    
    // Determinar destino
    let destinoDiaIndex = -1;
    
    // Se soltou em cima de outro título, encontrar o dia dele
    if (overId.startsWith('titulo-')) {
      const overTituloId = parseInt(overId.replace('titulo-', ''));
      for (let i = 0; i < roteiro.length; i++) {
        if (roteiro[i].titulos.some(t => t.id === overTituloId)) {
          destinoDiaIndex = i;
          break;
        }
      }
      // Verificar se o dia de destino está bloqueado
      if (destinoDiaIndex >= 0 && isDiaBloqueado(roteiro[destinoDiaIndex].data)) {
        return; // Não permitir mover para dia bloqueado
      }
      // Checar se está nos pendentes
      if (destinoDiaIndex < 0 && titulosPendentes.some(t => t.id === overTituloId)) {
        // Soltou em cima de um item pendente - volta para pendentes
        if (origemDiaIndex >= 0) {
          const novoRoteiro = [...roteiro];
          novoRoteiro[origemDiaIndex].titulos = novoRoteiro[origemDiaIndex].titulos.filter(t => t.id !== activeId);
          setRoteiro(novoRoteiro);
          setTitulosPendentes(prev => [...prev, { ...tituloArrastado!, data_agendamento: undefined }]);
          // Salvar no banco
          fetch(`${API_URL}/gestao-pagamentos/titulos/${activeId}/agendar`, { method: 'PUT' });
        }
        return;
      }
    } else if (overId.startsWith('dia-')) {
      // Ignorar se é um dia bloqueado (termina com -blocked)
      if (overId.endsWith('-blocked')) {
        return;
      }
      destinoDiaIndex = parseInt(overId.replace('dia-', '').replace('-blocked', ''));
      // Verificar se o dia de destino está bloqueado (usando estado centralizado)
      if (destinoDiaIndex >= 0 && destinoDiaIndex < roteiro.length && isDiaBloqueado(roteiro[destinoDiaIndex].data)) {
        return; // Não permitir mover para dia bloqueado
      }
    } else if (overId === 'pendentes') {
      // Remover do roteiro se estava lá
      if (origemDiaIndex >= 0) {
        const novoRoteiro = [...roteiro];
        novoRoteiro[origemDiaIndex].titulos = novoRoteiro[origemDiaIndex].titulos.filter(t => t.id !== activeId);
        setRoteiro(novoRoteiro);
        setTitulosPendentes(prev => [...prev, { ...tituloArrastado!, data_agendamento: undefined }]);
        // Salvar no banco
        fetch(`${API_URL}/gestao-pagamentos/titulos/${activeId}/agendar`, { method: 'PUT' });
      }
      return;
    }
    
    if (destinoDiaIndex < 0) return;
    
    // Mesmo dia? Não fazer nada
    if (origemDiaIndex === destinoDiaIndex) return;
    
    // Mover título
    const novoRoteiro = [...roteiro];
    
    // Remover da origem
    if (origemDiaIndex >= 0) {
      novoRoteiro[origemDiaIndex].titulos = novoRoteiro[origemDiaIndex].titulos.filter(t => t.id !== activeId);
    } else {
      setTitulosPendentes(prev => prev.filter(t => t.id !== activeId));
    }
    
    // Adicionar ao destino
    const dataDestino = novoRoteiro[destinoDiaIndex].data;
    novoRoteiro[destinoDiaIndex].titulos.push({
      ...tituloArrastado,
      data_agendamento: dataDestino
    });
    
    setRoteiro(novoRoteiro);
    
    // Salvar no banco de dados
    fetch(`${API_URL}/gestao-pagamentos/titulos/${activeId}/agendar?data_agendamento=${dataDestino}`, {
      method: 'PUT'
    }).catch(err => console.error('Erro ao salvar agendamento:', err));
  };

  // Remover título do dia (volta para pendentes)
  const removerTituloDoDia = (diaIndex: number, tituloId: number) => {
    const titulo = roteiro[diaIndex].titulos.find(t => t.id === tituloId);
    if (!titulo) return;
    
    const novoRoteiro = [...roteiro];
    novoRoteiro[diaIndex].titulos = novoRoteiro[diaIndex].titulos.filter(t => t.id !== tituloId);
    setRoteiro(novoRoteiro);
    
    setTitulosPendentes(prev => [...prev, { ...titulo, data_agendamento: undefined }]);
    
    // Salvar no banco de dados (voltar para pendente)
    fetch(`${API_URL}/gestao-pagamentos/titulos/${tituloId}/agendar`, {
      method: 'PUT'
    }).catch(err => console.error('Erro ao salvar:', err));
  };

  // Deletar título permanentemente (só de pendentes)
  const deletarTitulo = async (tituloId: number) => {
    try {
      const response = await fetch(`${API_URL}/gestao-pagamentos/titulos/${tituloId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setTitulosPendentes(prev => prev.filter(t => t.id !== tituloId));
        toast({ title: "Título excluído com sucesso" });
      } else {
        toast({ title: "Erro ao excluir título", variant: "destructive" });
      }
    } catch (error) {
      console.error('Erro ao deletar título:', error);
      toast({ title: "Erro ao excluir título", variant: "destructive" });
    }
  };

  // Juntar parcelas de volta ao título original
  const mergeTitulo = async (tituloId: number) => {
    const titulo = titulosPendentes.find(t => t.id === tituloId);
    if (!titulo) {
      toast({ title: "Título não encontrado", variant: "destructive" });
      return;
    }

    try {
      const response = await fetch(`${API_URL}/gestao-pagamentos/titulos/${tituloId}/merge`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        // Remover todas as parcelas do mesmo título original e adicionar o novo
        const tituloOriginalId = titulo.titulo_original_id;
        const removedIds: number[] = data.parcelas_ids || [];
        setTitulosPendentes(prev => {
          const semParcelas = prev.filter(t => {
            // Se temos IDs específicos removidos do backend, usar eles
            if (removedIds.length > 0) return !removedIds.includes(t.id);
            // Fallback: filtrar por titulo_original_id (parcelas criadas via split)
            if (tituloOriginalId) return t.titulo_original_id !== tituloOriginalId;
            // Parcelas de importação: filtrar por mesmo fornecedor + mesmo padrão de titulo
            return !(t.nome_fornecedor === titulo.nome_fornecedor && 
                     t.parcela_numero && t.parcela_total === titulo.parcela_total &&
                     t.data_vencimento === titulo.data_vencimento);
          });
          return [...semParcelas, data.titulo];
        });
        toast({ 
          title: `🔄 ${data.parcelas_removidas} parcelas reunificadas!`,
          description: `${titulo.nome_fornecedor} - ${formatCurrency(data.titulo.valor)}`
        });
      } else {
        const errorData = await response.json();
        toast({ title: errorData.detail || "Erro ao reunificar parcelas", variant: "destructive" });
      }
    } catch (error) {
      console.error('Erro ao reunificar parcelas:', error);
      toast({ title: "Erro ao reunificar parcelas", variant: "destructive" });
    }
  };

  // Dividir/Parcelar título
  const splitTitulo = async (tituloId: number, tipo: 'iguais' | 'residual' | 'customizado', config?: { numParcelas?: number; valorPrimeira?: number; valoresParcelas?: number[] }) => {
    const titulo = titulosPendentes.find(t => t.id === tituloId);
    if (!titulo) {
      toast({ title: "Título não encontrado", variant: "destructive" });
      return;
    }

    try {
      const response = await fetch(`${API_URL}/gestao-pagamentos/titulos/${tituloId}/split`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tipo, ...config })
      });

      if (response.ok) {
        const data = await response.json();
        // Remover título original e adicionar os novos
        setTitulosPendentes(prev => {
          const semOriginal = prev.filter(t => t.id !== tituloId);
          return [...semOriginal, ...data.titulos];
        });
        toast({ 
          title: `✂️ Título dividido em ${data.titulos.length} parcelas!`,
          description: `${titulo.nome_fornecedor}`
        });
      } else {
        const errorData = await response.json();
        toast({ title: errorData.detail || "Erro ao dividir título", variant: "destructive" });
      }
    } catch (error) {
      console.error('Erro ao dividir título:', error);
      toast({ title: "Erro ao dividir título", variant: "destructive" });
    }
  };

  // Cancelar dia de pagamento (todos os títulos vão para o próximo dia útil)
  const cancelarDiaPagamento = async (data: string) => {
    const diaIndex = roteiro.findIndex(d => d.data === data);
    if (diaIndex < 0) return;
    
    const dia = roteiro[diaIndex];
    if (dia.titulos.length === 0) {
      toast({ title: "Este dia não tem títulos agendados", variant: "destructive" });
      return;
    }
    
    // Confirmar ação
    if (!window.confirm(`⚠️ Cancelar pagamentos de ${dia.dia_semana} ${formatDate(data)}?\n\n${dia.titulos.length} títulos serão movidos para o próximo dia útil.`)) {
      return;
    }
    
    // Encontrar próximo dia útil (pula domingo)
    const proximoDiaIndex = diaIndex + 1;
    if (proximoDiaIndex >= roteiro.length) {
      toast({ title: "Não há próximo dia disponível no roteiro", variant: "destructive" });
      return;
    }
    
    const novoRoteiro = [...roteiro];
    const titulosMovidos = [...novoRoteiro[diaIndex].titulos];
    
    // Mover títulos para o próximo dia
    novoRoteiro[proximoDiaIndex].titulos = [
      ...titulosMovidos.map(t => ({ ...t, data_agendamento: novoRoteiro[proximoDiaIndex].data })),
      ...novoRoteiro[proximoDiaIndex].titulos
    ];
    novoRoteiro[diaIndex].titulos = [];
    
    setRoteiro(novoRoteiro);
    
    toast({ 
      title: `🚫 ${dia.dia_semana} cancelado!`,
      description: `${titulosMovidos.length} títulos movidos para ${novoRoteiro[proximoDiaIndex].dia_semana}`
    });
  };

  // Abrir dialog de completar orçamento
  const abrirDialogCompletarOrcamento = (diaIndex: number, saldo: number) => {
    // Listar fornecedores disponíveis nos pendentes que cabem no saldo
    const fornecedoresDisponiveis = new Map<string, { total_titulos: number, valor_total: number }>();
    
    for (const titulo of titulosPendentes) {
      if (titulo.valor <= saldo) {
        const forn = titulo.nome_fornecedor;
        const atual = fornecedoresDisponiveis.get(forn) || { total_titulos: 0, valor_total: 0 };
        fornecedoresDisponiveis.set(forn, {
          total_titulos: atual.total_titulos + 1,
          valor_total: atual.valor_total + titulo.valor
        });
      }
    }
    
    // Converter para array e ordenar por valor total
    const sugestoes = Array.from(fornecedoresDisponiveis.entries())
      .map(([nome, data]) => ({ nome_fornecedor: nome, ...data }))
      .sort((a, b) => b.valor_total - a.valor_total)
      .slice(0, 15); // Limitar a 15 fornecedores
    
    setSugestoesFornecedorRaio(sugestoes);
    setFornecedorPriorizado('');
    setDialogCompletarOrcamento({ diaIndex, saldo });
  };

  // Executar completar orçamento (com ou sem priorização de fornecedor)
  const executarCompletarOrcamento = (fornecedorPrioritario?: string) => {
    if (!dialogCompletarOrcamento) return;
    
    const { diaIndex } = dialogCompletarOrcamento;
    const novoRoteiro = [...roteiro];
    const dia = novoRoteiro[diaIndex];
    const totalAtual = dia.titulos.reduce((sum, t) => sum + t.valor, 0);
    let saldoDisponivel = orcamentoDiario - totalAtual;
    
    if (saldoDisponivel <= 0) {
      toast({ title: "Este dia já está completo ou acima do orçamento", variant: "destructive" });
      setDialogCompletarOrcamento(null);
      return;
    }

    const titulosAdicionados: Titulo[] = [];
    let novosPendentes = [...titulosPendentes];

    // Função para encontrar títulos que cabem no saldo
    const encontrarTitulosQueCabem = (titulos: Titulo[], saldo: number, priorizarFornecedor?: string): Titulo[] => {
      let ordenados = [...titulos];
      
      if (priorizarFornecedor) {
        // Primeiro os do fornecedor priorizado, depois os outros
        ordenados = ordenados.sort((a, b) => {
          const aIsPrioritario = a.nome_fornecedor.toLowerCase().includes(priorizarFornecedor.toLowerCase());
          const bIsPrioritario = b.nome_fornecedor.toLowerCase().includes(priorizarFornecedor.toLowerCase());
          
          if (aIsPrioritario && !bIsPrioritario) return -1;
          if (!aIsPrioritario && bIsPrioritario) return 1;
          
          // Dentro da mesma prioridade, ordenar por tier e valor
          if (a.tier !== b.tier) return a.tier - b.tier;
          return b.valor - a.valor;
        });
      } else {
        // Ordenar por tier (menor primeiro) e depois por valor (maior primeiro)
        ordenados = ordenados.sort((a, b) => {
          if (a.tier !== b.tier) return a.tier - b.tier;
          return b.valor - a.valor;
        });
      }
      
      const selecionados: Titulo[] = [];
      let saldoRestante = saldo;
      
      for (const titulo of ordenados) {
        if (titulo.valor <= saldoRestante) {
          selecionados.push(titulo);
          saldoRestante -= titulo.valor;
        }
      }
      
      return selecionados;
    };

    // 1. Primeiro, tentar pegar dos dias seguintes
    for (let i = diaIndex + 1; i < novoRoteiro.length && saldoDisponivel > 0; i++) {
      const titulosParaPegar = encontrarTitulosQueCabem(novoRoteiro[i].titulos, saldoDisponivel, fornecedorPrioritario);
      
      for (const titulo of titulosParaPegar) {
        novoRoteiro[i].titulos = novoRoteiro[i].titulos.filter(t => t.id !== titulo.id);
        titulosAdicionados.push({ ...titulo, data_agendamento: dia.data });
        saldoDisponivel -= titulo.valor;
        
        fetch(`${API_URL}/gestao-pagamentos/titulos/${titulo.id}/agendar?data_agendamento=${dia.data}`, {
          method: 'PUT'
        }).catch(err => console.error('Erro ao salvar:', err));
      }
    }

    // 2. Se ainda tiver saldo, pegar dos pendentes
    if (saldoDisponivel > 0) {
      const titulosDosPendentes = encontrarTitulosQueCabem(novosPendentes, saldoDisponivel, fornecedorPrioritario);
      
      for (const titulo of titulosDosPendentes) {
        novosPendentes = novosPendentes.filter(t => t.id !== titulo.id);
        titulosAdicionados.push({ ...titulo, data_agendamento: dia.data });
        saldoDisponivel -= titulo.valor;
        
        fetch(`${API_URL}/gestao-pagamentos/titulos/${titulo.id}/agendar?data_agendamento=${dia.data}`, {
          method: 'PUT'
        }).catch(err => console.error('Erro ao salvar:', err));
      }
    }

    if (titulosAdicionados.length === 0) {
      toast({ title: "Não há títulos que caibam no saldo disponível", variant: "destructive" });
      setDialogCompletarOrcamento(null);
      return;
    }

    novoRoteiro[diaIndex].titulos = [...dia.titulos, ...titulosAdicionados];
    
    setRoteiro(novoRoteiro);
    setTitulosPendentes(novosPendentes);
    setDialogCompletarOrcamento(null);
    
    const valorAdicionado = titulosAdicionados.reduce((sum, t) => sum + t.valor, 0);
    const descPrioridade = fornecedorPrioritario ? ` (priorizando ${fornecedorPrioritario})` : '';
    toast({ 
      title: `⚡ ${titulosAdicionados.length} títulos adicionados!`,
      description: `+${formatCurrency(valorAdicionado)} em ${dia.dia_semana}${descPrioridade}`
    });
  };

  // Salvar orçamento
  const salvarOrcamento = async () => {
    try {
      const res = await fetch(`${API_URL}/gestao-pagamentos/orcamento`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orcamento_diario: orcamentoDiario, dia_inicio_semana: 1, dias_uteis_semana: 5 })
      });
      if (res.ok) {
        toast({ title: "✅ Orçamento atualizado!" });
      }
    } catch (error) {
      toast({ title: "Erro ao salvar orçamento", variant: "destructive" });
    }
  };

  // Salvar fornecedor
  const salvarFornecedor = async () => {
    try {
      const res = await fetch(`${API_URL}/gestao-pagamentos/fornecedores/prioridades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(novoFornecedor)
      });
      if (res.ok) {
        toast({ title: "✅ Fornecedor cadastrado!" });
        setDialogFornecedor(false);
        setNovoFornecedor({ tier: 3, max_dias_atraso: 5 });
        carregarFornecedores();
      }
    } catch (error) {
      toast({ title: "Erro ao salvar fornecedor", variant: "destructive" });
    }
  };

  // Salvar exceção
  const salvarExcecao = async () => {
    try {
      const res = await fetch(`${API_URL}/gestao-pagamentos/excecoes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...novaExcecao,
          prioridade_especial: 1
        })
      });
      if (res.ok) {
        toast({ title: "✅ Exceção cadastrada!" });
        setDialogExcecao(false);
        setNovaExcecao({});
        carregarExcecoes();
      }
    } catch (error) {
      toast({ title: "Erro ao salvar exceção", variant: "destructive" });
    }
  };

  // Download títulos do dia como XLSX
  const downloadTitulosDia = (dia: DiaRoteiro) => {
    if (dia.titulos.length === 0) {
      toast({ title: "Nenhum título para exportar", variant: "destructive" });
      return;
    }

    // Função para formatar data no padrão brasileiro
    const formatDateBR = (dateStr?: string) => {
      if (!dateStr) return '';
      const date = new Date(dateStr + 'T00:00:00');
      return date.toLocaleDateString('pt-BR');
    };

    // Criar dados na MESMA ORDEM do arquivo de importação do ERP (TODAS AS COLUNAS)
    const dados = dia.titulos.map(titulo => ({
      'Cod. fornecedor': titulo.cod_fornecedor || '',
      'Nome fornecedor': titulo.nome_fornecedor,
      'CPF CNPJ': titulo.cnpj_cpf || '',
      'Num. Titulo': titulo.numero_titulo || titulo.numero_documento || '',
      'ID Titulo Pagar': titulo.id_titulo_pagar || '',
      'Num. Orcom': titulo.num_orcom || '',
      'Filial': titulo.filial || '',
      'Empresa': titulo.empresa || '',
      'Data lancamento': formatDateBR(titulo.data_emissao),
      'Data vencimento': formatDateBR(titulo.data_vencimento),
      'Data pagamento': formatDateBR(titulo.data_pagamento),
      'Tipo': titulo.tipo || '',
      'Tipo Mov.': titulo.tipo_movimento || '',
      'Situação': titulo.situacao || '',
      'Documento Dev.': titulo.documento_dev || '',
      'Liberação': titulo.liberacao || '',
      'Empenho': titulo.empenho || '',
      'Carnê': titulo.carne || '',
      'Valor do título': titulo.valor_titulo || titulo.valor,
      'Valor Antecipado': titulo.valor_antecipado || '',
      'Valor Desconto': titulo.valor_desconto || '',
      'Valor Desconto Tributação': titulo.valor_desconto_tributacao || '',
      'Parcela': titulo.parcela_numero && titulo.parcela_total 
        ? `${titulo.parcela_numero}/${titulo.parcela_total}` 
        : '',
      'Valor final': titulo.valor,
      'Valor original': (titulo.parcela_numero && titulo.parcela_total) 
        ? (titulo.valor_titulo || '') 
        : '',
      'Instrução pagamento': titulo.instrucao_pagamento || '',
      'Grupo de Conta': titulo.grupo_conta || '',
      'Conta': titulo.conta || '',
      'Descrição Conta': titulo.descricao || '',
      'Seu Número': titulo.seu_numero || '',
      'Vinculado a Lote': titulo.vinculado_lote || '',
      'Lote': titulo.lote_erp || '',
    }));

    // Criar workbook e worksheet
    const ws = XLSX.utils.json_to_sheet(dados);
    
    // Ajustar largura das colunas
    ws['!cols'] = [
      { wch: 15 }, // Cod. fornecedor
      { wch: 45 }, // Nome fornecedor
      { wch: 18 }, // CPF CNPJ
      { wch: 20 }, // Num. Titulo
      { wch: 15 }, // ID Titulo Pagar
      { wch: 12 }, // Num. Orcom
      { wch: 10 }, // Filial
      { wch: 15 }, // Empresa
      { wch: 15 }, // Data lancamento
      { wch: 15 }, // Data vencimento
      { wch: 15 }, // Data pagamento
      { wch: 10 }, // Tipo
      { wch: 12 }, // Tipo Mov.
      { wch: 12 }, // Situação
      { wch: 15 }, // Documento Dev.
      { wch: 12 }, // Liberação
      { wch: 12 }, // Empenho
      { wch: 10 }, // Carnê
      { wch: 15 }, // Valor do título
      { wch: 15 }, // Valor Antecipado
      { wch: 15 }, // Valor Desconto
      { wch: 20 }, // Valor Desconto Tributação
      { wch: 10 }, // Parcela
      { wch: 15 }, // Valor final
      { wch: 15 }, // Valor original
      { wch: 25 }, // Instrução pagamento
      { wch: 20 }, // Grupo de Conta
      { wch: 15 }, // Conta
      { wch: 40 }, // Descrição Conta
      { wch: 15 }, // Seu Número
      { wch: 15 }, // Vinculado a Lote
      { wch: 15 }, // Lote
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Pagamentos');

    // Formatar data para nome do arquivo
    const dataFormatada = new Date(dia.data + 'T00:00:00').toLocaleDateString('pt-BR').replace(/\//g, '-');
    const nomeArquivo = `pagamentos_${dataFormatada}.xlsx`;

    XLSX.writeFile(wb, nomeArquivo);
    
    toast({ 
      title: "✅ Download concluído!", 
      description: `${dia.titulos.length} títulos exportados para ${nomeArquivo}` 
    });
  };

  // Importar títulos
  const importarTitulos = async () => {
    if (!arquivoImport) return;
    
    try {
      const formData = new FormData();
      formData.append('file', arquivoImport);
      
      const res = await fetch(`${API_URL}/gestao-pagamentos/titulos/importar`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (res.ok) {
        toast({ 
          title: "✅ Importação concluída!", 
          description: `${data.importados} títulos importados` 
        });
        setDialogImport(false);
        setArquivoImport(null);
        carregarTitulos();
      } else {
        toast({ 
          title: "Erro na importação", 
          description: data.detail || "Verifique o formato do arquivo",
          variant: "destructive" 
        });
      }
    } catch (error) {
      toast({ title: "Erro ao importar", variant: "destructive" });
    }
  };

  // Deletar item
  const deletarItem = async () => {
    if (!confirmDelete) return;
    
    try {
      let url = '';
      if (confirmDelete.tipo === 'fornecedor') {
        url = `${API_URL}/gestao-pagamentos/fornecedores/prioridades/${confirmDelete.id}`;
      } else if (confirmDelete.tipo === 'excecao') {
        url = `${API_URL}/gestao-pagamentos/excecoes/${confirmDelete.id}`;
      }
      
      const res = await fetch(url, { method: 'DELETE' });
      if (res.ok) {
        toast({ title: "✅ Item removido!" });
        if (confirmDelete.tipo === 'fornecedor') carregarFornecedores();
        if (confirmDelete.tipo === 'excecao') carregarExcecoes();
      }
    } catch (error) {
      toast({ title: "Erro ao remover", variant: "destructive" });
    } finally {
      setConfirmDelete(null);
    }
  };

  // Calcular totais
  const totalRoteiro = roteiro.reduce((sum, dia) => 
    sum + dia.titulos.reduce((s, t) => s + t.valor, 0), 0
  );
  const totalPendentes = titulosPendentes.reduce((sum, t) => sum + t.valor, 0);

  return (
    <TooltipProvider>
    <div className="min-h-screen bg-gray-50/50 -m-4 md:-m-8 p-4 md:p-8 space-y-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-white rounded-xl border border-gray-200 shadow-sm">
            <DollarSign className="h-6 w-6 text-gray-700" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">
              Gestão de Pagamentos
            </h1>
            <p className="text-gray-500 text-sm">
              Arraste e solte para organizar o roteiro
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" onClick={carregarTudo} disabled={loading} className="border-gray-200 hover:bg-gray-100">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>
          <Dialog open={dialogImport} onOpenChange={setDialogImport}>
            <DialogTrigger asChild>
              <Button variant="outline" className="border-gray-200 hover:bg-gray-100">
                <Upload className="h-4 w-4 mr-2" />
                Importar
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Importar Títulos a Pagar</DialogTitle>
                <DialogDescription>
                  Upload de Excel/CSV. Colunas: fornecedor, valor, vencimento
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <Input 
                  type="file" 
                  accept=".xlsx,.xls,.csv"
                  onChange={(e) => setArquivoImport(e.target.files?.[0] || null)}
                />
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogImport(false)}>Cancelar</Button>
                <Button onClick={importarTitulos} disabled={!arquivoImport}>Importar</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button onClick={gerarRoteiroAutomatico} disabled={loading} className="bg-gray-800 hover:bg-gray-900 text-white">
            <Zap className="h-4 w-4 mr-2" />
            Gerar Roteiro Automático
          </Button>
        </div>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-white border-gray-200 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg">
                <Calendar className="h-5 w-5 text-gray-600" />
              </div>
              <div>
                <div className="text-xs text-gray-500 font-medium">Orçamento/dia</div>
                <div className="text-xl font-bold text-gray-800">{formatCurrency(orcamentoDiario)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-gray-200 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-50 rounded-lg">
                <Check className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <div className="text-xs text-gray-500 font-medium">Agendado</div>
                <div className="text-xl font-bold text-emerald-600">{formatCurrency(totalRoteiro)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-gray-200 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-50 rounded-lg">
                <Clock className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <div className="text-xs text-gray-500 font-medium">Pendentes</div>
                <div className="text-xl font-bold text-amber-600">{formatCurrency(totalPendentes)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-gray-200 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-violet-50 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-violet-600" />
              </div>
              <div>
                <div className="text-xs text-gray-500 font-medium">Exceções</div>
                <div className="text-xl font-bold text-violet-600">
                  {excecoes.length} <span className="text-sm font-normal">({formatCurrency(excecoes.reduce((s, e) => s + e.valor_solicitado, 0))})</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-white border border-gray-200">
          <TabsTrigger value="roteiro" className="data-[state=active]:bg-gray-100">📅 Roteiro</TabsTrigger>
          <TabsTrigger value="fornecedores" className="data-[state=active]:bg-gray-100">👥 Tiers</TabsTrigger>
          <TabsTrigger value="excecoes" className="data-[state=active]:bg-gray-100">⚡ Exceções</TabsTrigger>
          <TabsTrigger value="config" className="data-[state=active]:bg-gray-100">⚙️ Config</TabsTrigger>
          <TabsTrigger value="excluidos" className="data-[state=active]:bg-gray-100">🗑️ Excluídos</TabsTrigger>
        </TabsList>

        {/* Tab Roteiro - Drag and Drop */}
        <TabsContent value="roteiro" className="space-y-4">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <div className="flex gap-3" style={{ minHeight: '550px' }}>
              {/* Coluna de Pendentes - FIXA */}
              <div className="flex-shrink-0 sticky left-0 z-10 bg-background">
                <PendentesColumn 
                  titulos={titulosPendentes} 
                  total={totalPendentes}
                  filtroTier={filtroTier}
                  setFiltroTier={setFiltroTier}
                  filtroFornecedor={filtroFornecedor}
                  setFiltroFornecedor={setFiltroFornecedor}
                  ordenacao={ordenacaoPendentes}
                  setOrdenacao={setOrdenacaoPendentes}
                  onDeleteTitulo={deletarTitulo}
                  onMergeTitulo={mergeTitulo}
                  onSplitTitulo={splitTitulo}
                />
              </div>

              {/* Seta */}
              <div className="flex items-center flex-shrink-0 sticky left-[296px] z-10 bg-background">
                <ArrowRight className="h-5 w-5 text-gray-400" />
              </div>

              {/* Colunas dos dias - SCROLL HORIZONTAL */}
              <div ref={diasScrollRef} className="flex gap-3 overflow-x-auto overflow-y-hidden pb-4 flex-1">
                {roteiro.map((dia, index) => {
                  const hoje = new Date().toISOString().split('T')[0];
                  const isToday = dia.data === hoje;
                  return (
                    <div key={dia.data} ref={isToday ? todayColumnRef : undefined}>
                      <DiaColumn
                        dia={dia}
                        diaIndex={index}
                        orcamento={orcamentoDiario}
                        onRemoveTitulo={(tituloId) => removerTituloDoDia(index, tituloId)}
                        onCancelarDia={cancelarDiaPagamento}
                        onCompletarOrcamento={abrirDialogCompletarOrcamento}
                        onDownloadDia={downloadTitulosDia}
                        isBloqueado={isDiaBloqueado(dia.data)}
                        onToggleBloqueio={() => toggleBloqueio(dia.data)}
                        filtroGlobal={filtroFornecedor}
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Overlay do item sendo arrastado */}
            <DragOverlay>
              {activeTitulo && (
                <TituloCard titulo={activeTitulo} isDragging />
              )}
            </DragOverlay>
          </DndContext>
        </TabsContent>

        {/* Tab Fornecedores/Tiers */}
        <TabsContent value="fornecedores">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Configuração de Tiers</CardTitle>
                <CardDescription>
                  Define a prioridade e dias de espera por fornecedor
                </CardDescription>
              </div>
              <Dialog open={dialogFornecedor} onOpenChange={setDialogFornecedor}>
                <DialogTrigger asChild>
                  <Button><Plus className="h-4 w-4 mr-2" />Novo</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Cadastrar Fornecedor</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="relative">
                      <Label>Nome do Fornecedor *</Label>
                      <Input 
                        value={novoFornecedor.nome_fornecedor || ''}
                        onChange={(e) => {
                          const valor = e.target.value;
                          setNovoFornecedor({...novoFornecedor, nome_fornecedor: valor});
                          buscarSugestoesFornecedor(valor);
                        }}
                        onFocus={() => novoFornecedor.nome_fornecedor && novoFornecedor.nome_fornecedor.length >= 2 && buscarSugestoesFornecedor(novoFornecedor.nome_fornecedor)}
                        onBlur={() => setTimeout(() => setShowSugestoes(false), 200)}
                        placeholder="Digite para buscar..."
                        autoComplete="off"
                      />
                      {showSugestoes && sugestoesFornecedor.length > 0 && (
                        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                          {sugestoesFornecedor.map((sug, idx) => (
                            <div
                              key={idx}
                              className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                              onMouseDown={(e) => {
                                e.preventDefault();
                                setNovoFornecedor({...novoFornecedor, nome_fornecedor: sug.nome_fornecedor});
                                setShowSugestoes(false);
                              }}
                            >
                              <div className="font-medium">{sug.nome_fornecedor}</div>
                              {sug.cod_fornecedor && (
                                <div className="text-xs text-muted-foreground">Cód: {sug.cod_fornecedor}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {buscandoSugestoes && (
                        <div className="absolute right-3 top-8">
                          <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                        </div>
                      )}
                    </div>
                    <div>
                      <Label>Tier (Prioridade)</Label>
                      <Select 
                        value={String(novoFornecedor.tier || 3)}
                        onValueChange={(v) => setNovoFornecedor({...novoFornecedor, tier: Number(v)})}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">🔴 Tier 1 - Crítico</SelectItem>
                          <SelectItem value="2">🟠 Tier 2 - Alta</SelectItem>
                          <SelectItem value="3">🟡 Tier 3 - Média</SelectItem>
                          <SelectItem value="4">🟢 Tier 4 - Baixa</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Espera até X dias após vencimento</Label>
                      <Select 
                        value={String(novoFornecedor.max_dias_atraso || 0)}
                        onValueChange={(v) => setNovoFornecedor({...novoFornecedor, max_dias_atraso: Number(v)})}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="0">0 dias (pagar no vencimento)</SelectItem>
                          <SelectItem value="3">Espera até 3 dias</SelectItem>
                          <SelectItem value="5">Espera até 5 dias</SelectItem>
                          <SelectItem value="7">Espera até 7 dias</SelectItem>
                          <SelectItem value="10">Espera até 10 dias</SelectItem>
                          <SelectItem value="15">Espera até 15 dias</SelectItem>
                          <SelectItem value="30">Espera até 30 dias</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Observações</Label>
                      <Textarea 
                        value={novoFornecedor.notas || ''}
                        onChange={(e) => setNovoFornecedor({...novoFornecedor, notas: e.target.value})}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setDialogFornecedor(false)}>Cancelar</Button>
                    <Button onClick={salvarFornecedor}>Salvar</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {/* Legenda dos Tiers */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {[1, 2, 3, 4].map(tier => {
                  const config = getTierConfig(tier);
                  const diasPadrao = { 1: 0, 2: 3, 3: 5, 4: 10 }[tier];
                  return (
                    <div key={tier} className={`p-3 rounded-lg border ${config.bgColor}`}>
                      <div className="font-semibold">{config.emoji} Tier {tier}</div>
                      <div className="text-sm">{config.label}</div>
                      <div className="text-xs text-muted-foreground">Padrão: espera {diasPadrao} dias</div>
                    </div>
                  );
                })}
              </div>

              {fornecedores.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Nenhum fornecedor configurado</p>
                  <p className="text-sm">Fornecedores sem config usam Tier 3 (5 dias)</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fornecedor</TableHead>
                      <TableHead>Tier</TableHead>
                      <TableHead>Espera até</TableHead>
                      <TableHead>Observações</TableHead>
                      <TableHead className="w-[80px]">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fornecedores.map((f) => {
                      const config = getTierConfig(f.tier);
                      return (
                        <TableRow key={f.id}>
                          <TableCell className="font-medium">{f.nome_fornecedor}</TableCell>
                          <TableCell>
                            <Badge className={config.bgColor}>{config.emoji} Tier {f.tier}</Badge>
                          </TableCell>
                          <TableCell>{f.max_dias_atraso || 0} dias</TableCell>
                          <TableCell className="max-w-[200px] truncate">{f.notas || '-'}</TableCell>
                          <TableCell>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              onClick={() => setConfirmDelete({ tipo: 'fornecedor', id: f.id })}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Exceções */}
        <TabsContent value="excecoes">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>⚡ Exceções de Pagamento</CardTitle>
                <CardDescription>
                  Casos especiais que precisam de pagamento urgente
                </CardDescription>
              </div>
              <Dialog open={dialogExcecao} onOpenChange={setDialogExcecao}>
                <DialogTrigger asChild>
                  <Button><Plus className="h-4 w-4 mr-2" />Nova Exceção</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Criar Exceção</DialogTitle>
                    <DialogDescription>
                      Ex: "Prestador precisa de R$ 80k esta semana para impostos"
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label>Fornecedor *</Label>
                      <Input 
                        value={novaExcecao.nome_fornecedor || ''}
                        onChange={(e) => setNovaExcecao({...novaExcecao, nome_fornecedor: e.target.value})}
                      />
                    </div>
                    <div>
                      <Label>Valor (R$) *</Label>
                      <Input 
                        type="number"
                        value={novaExcecao.valor_solicitado || ''}
                        onChange={(e) => setNovaExcecao({...novaExcecao, valor_solicitado: Number(e.target.value)})}
                      />
                    </div>
                    <div>
                      <Label>Precisa até *</Label>
                      <Input 
                        type="date"
                        value={novaExcecao.data_necessidade || ''}
                        onChange={(e) => setNovaExcecao({...novaExcecao, data_necessidade: e.target.value})}
                      />
                    </div>
                    <div>
                      <Label>Motivo *</Label>
                      <Textarea 
                        value={novaExcecao.motivo || ''}
                        onChange={(e) => setNovaExcecao({...novaExcecao, motivo: e.target.value})}
                        placeholder="Ex: Pagar impostos, folha de funcionários..."
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setDialogExcecao(false)}>Cancelar</Button>
                    <Button onClick={salvarExcecao}>Salvar</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {excecoes.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Zap className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Nenhuma exceção ativa</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fornecedor</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                      <TableHead>Precisa até</TableHead>
                      <TableHead>Motivo</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-[80px]">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {excecoes.map((exc) => (
                      <TableRow key={exc.id}>
                        <TableCell className="font-medium">{exc.nome_fornecedor}</TableCell>
                        <TableCell className="text-right font-bold">{formatCurrency(exc.valor_solicitado)}</TableCell>
                        <TableCell>{formatDate(exc.data_necessidade)}</TableCell>
                        <TableCell className="max-w-[200px] truncate">{exc.motivo}</TableCell>
                        <TableCell>
                          <Badge variant={exc.status === 'pago' ? 'default' : 'secondary'}>
                            {exc.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => setConfirmDelete({ tipo: 'excecao', id: exc.id })}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Config */}
        <TabsContent value="config">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>💰 Orçamento Diário</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Valor (R$)</Label>
                  <Input 
                    type="number" 
                    value={orcamentoDiario}
                    onChange={(e) => setOrcamentoDiario(Number(e.target.value))}
                  />
                </div>
                <Button onClick={salvarOrcamento}>Salvar</Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>📅 Período do Roteiro</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Dias úteis necessários</Label>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-lg px-4 py-2">
                      {diasRoteiro} dias
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      (calculado automaticamente)
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Com orçamento de R$ {orcamentoDiario.toLocaleString('pt-BR')}/dia, 
                    são necessários {diasRoteiro} dias para pagar todos os títulos.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab Excluídos */}
        <TabsContent value="excluidos">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>🗑️ Títulos Excluídos (Blacklist)</CardTitle>
              <Button variant="outline" size="sm" onClick={async () => {
                const res = await fetch(`${API_URL}/gestao-pagamentos/titulos-excluidos`);
                if (res.ok) setTitulosExcluidos(await res.json());
              }}>
                <RefreshCw className="h-4 w-4 mr-2" /> Atualizar
              </Button>
            </CardHeader>
            <CardContent>
              {titulosExcluidos.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>Nenhum título excluído.</p>
                  <p className="text-sm mt-1">Clique em "Atualizar" para carregar a lista.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="p-2 text-left">Fornecedor</th>
                        <th className="p-2 text-left">Cód.</th>
                        <th className="p-2 text-left">Título</th>
                        <th className="p-2 text-right">Valor</th>
                        <th className="p-2 text-left">Vencimento</th>
                        <th className="p-2 text-left">Motivo</th>
                        <th className="p-2 text-left">Excluído em</th>
                        <th className="p-2 text-center">Ação</th>
                      </tr>
                    </thead>
                    <tbody>
                      {titulosExcluidos.map((t) => (
                        <tr key={t.id} className="border-b hover:bg-gray-50">
                          <td className="p-2">{t.nome_fornecedor}</td>
                          <td className="p-2">{t.cod_fornecedor}</td>
                          <td className="p-2 font-mono">{t.numero_titulo}</td>
                          <td className="p-2 text-right">{t.valor ? `R$ ${Number(t.valor).toLocaleString('pt-BR', {minimumFractionDigits: 2})}` : '-'}</td>
                          <td className="p-2">{t.data_vencimento ? new Date(t.data_vencimento + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}</td>
                          <td className="p-2">
                            <Badge variant={t.motivo === 'excluido_lote' ? 'secondary' : 'outline'}>
                              {t.motivo === 'excluido_lote' ? 'Lote' : 'Manual'}
                            </Badge>
                          </td>
                          <td className="p-2 text-xs text-gray-500">{t.excluido_em ? new Date(t.excluido_em).toLocaleString('pt-BR') : '-'}</td>
                          <td className="p-2 text-center">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-green-600 hover:text-green-800 hover:bg-green-50"
                              onClick={async () => {
                                if (!confirm(`Recuperar título "${t.numero_titulo}" de ${t.nome_fornecedor}?\n\nEle voltará para a lista de pendentes.`)) return;
                                const res = await fetch(`${API_URL}/gestao-pagamentos/titulos-excluidos/${t.id}`, { method: 'DELETE' });
                                if (res.ok) {
                                  setTitulosExcluidos(prev => prev.filter(x => x.id !== t.id));
                                  toast({ title: '✅ Título recuperado', description: 'Voltou para a lista de pendentes.' });
                                  carregarTitulos();
                                }
                              }}
                            >
                              <Undo2 className="h-4 w-4 mr-1" /> Recuperar
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialog de Completar Orçamento (Raio) */}
      <Dialog open={!!dialogCompletarOrcamento} onOpenChange={(open) => !open && setDialogCompletarOrcamento(null)}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-amber-500" />
              Completar Orçamento
            </DialogTitle>
            <DialogDescription>
              Saldo disponível: <strong className="text-emerald-600">{formatCurrency(dialogCompletarOrcamento?.saldo || 0)}</strong>
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-2">
            {/* Opção 1: Qualquer título */}
            <Button
              variant="outline"
              className="w-full h-auto py-3 px-4 flex flex-col items-start gap-1 hover:bg-gray-50 hover:border-gray-400"
              onClick={() => executarCompletarOrcamento()}
            >
              <div className="flex items-center gap-2 font-semibold text-sm">
                <Zap className="h-4 w-4 text-amber-500" />
                Preencher com qualquer título
              </div>
              <span className="text-xs text-gray-500 font-normal text-left">
                Seleciona os melhores títulos automaticamente
              </span>
            </Button>
            
            {/* Opção 2: Priorizar fornecedor */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Ou priorizar um fornecedor:</Label>
              <Select
                value={fornecedorPriorizado}
                onValueChange={setFornecedorPriorizado}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Selecione um fornecedor..." />
                </SelectTrigger>
                <SelectContent className="max-h-[250px]">
                  {sugestoesFornecedorRaio.map((forn) => (
                    <SelectItem key={forn.nome_fornecedor} value={forn.nome_fornecedor}>
                      <span className="truncate">{forn.nome_fornecedor.substring(0, 30)}{forn.nome_fornecedor.length > 30 ? '...' : ''}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {fornecedorPriorizado && (
                <div className="pt-1">
                  <p className="text-xs text-gray-600 mb-2">
                    Fornecedor selecionado terá prioridade no preenchimento
                  </p>
                  <Button
                    className="w-full bg-amber-500 hover:bg-amber-600 text-white"
                    onClick={() => executarCompletarOrcamento(fornecedorPriorizado)}
                  >
                    <Zap className="h-4 w-4 mr-2" />
                    Confirmar
                  </Button>
                </div>
              )}
              
              {sugestoesFornecedorRaio.length === 0 && (
                <p className="text-xs text-gray-500 italic">
                  Nenhum fornecedor com títulos disponíveis.
                </p>
              )}
            </div>
          </div>
          
          <DialogFooter className="mt-2">
            <Button variant="ghost" onClick={() => setDialogCompletarOrcamento(null)}>
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog de Confirmação */}
      <AlertDialog open={!!confirmDelete} onOpenChange={() => setConfirmDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar exclusão</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir este item?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={deletarItem} className="bg-red-600 hover:bg-red-700">
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    </TooltipProvider>
  );
}
