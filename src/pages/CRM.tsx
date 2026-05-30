import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";
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
} from "@dnd-kit/core";
import { useDraggable } from "@dnd-kit/core";
import {
  Plus,
  Search,
  Loader2,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Inbox,
  ArrowRight,
  MessageSquare,
  Send,
  Paperclip,
  User,
  Phone,
  Mail,
  Calendar,
  FileText,
  Tag,
  Building2,
  Hash,
  GripVertical,
  Filter,
  BarChart3,
  RefreshCw,
  ExternalLink,
  UserCheck,
  ChevronRight,
  FilePenLine,
  Trash2,
  Save,
  Wrench,
  X,
  Eye,
  Download,
  Play,
  FileAudio,
  FileVideo,
  FileImage,
  File as FileIcon,
  Bell,
  CalendarClock,
} from "lucide-react";
import { crmService } from "@/services/crm.service";
import { useAuth } from "@/contexts/AuthContext";
import type {
  CRMTicket,
  CRMTicketStatus,
  CRMTicketCreate,
  CRMStats,
  CRMArea,
  ProdutoVenda,
  ClientePedido,
  DadosMontagem,
  DadosNMResolve,
} from "@/types/crm";
import { CRM_AREAS, CRM_STATUS_DETALHE, CRM_RESOLUCOES } from "@/types/crm";

// ============================================================
// File preview helpers
// ============================================================

type FileCategory = "image" | "pdf" | "video" | "audio" | "other";

function getFileCategory(tipo: string, nome: string): FileCategory {
  const t = tipo.toLowerCase();
  const n = nome.toLowerCase();
  if (t.startsWith("image/") || /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(n)) return "image";
  if (t === "application/pdf" || n.endsWith(".pdf")) return "pdf";
  if (t.startsWith("video/") || /\.(mp4|webm|mov|avi|mkv)$/i.test(n)) return "video";
  if (t.startsWith("audio/") || /\.(mp3|wav|ogg|aac|m4a)$/i.test(n)) return "audio";
  return "other";
}

function resolveUrl(url: string): string {
  if (url.startsWith("http")) return url;
  const origin = window.location.origin;
  return `${origin}${url}`;
}

function AttachmentPreview({
  anexo,
  onPreview,
}: {
  anexo: { nome: string; url: string; tipo: string };
  onPreview: (a: { nome: string; url: string; tipo: string }) => void;
}) {
  const cat = getFileCategory(anexo.tipo, anexo.nome);
  const fullUrl = resolveUrl(anexo.url);

  if (cat === "image") {
    return (
      <button
        onClick={() => onPreview(anexo)}
        className="group relative rounded-lg overflow-hidden border bg-muted/30 hover:ring-2 hover:ring-primary/50 transition-all"
      >
        <img
          src={fullUrl}
          alt={anexo.nome}
          className="h-32 w-auto max-w-[200px] object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
          <Eye className="h-5 w-5 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow" />
        </div>
        <p className="text-[10px] text-muted-foreground truncate px-1.5 py-1 bg-background/80 absolute bottom-0 left-0 right-0">
          {anexo.nome}
        </p>
      </button>
    );
  }

  if (cat === "video") {
    return (
      <button
        onClick={() => onPreview(anexo)}
        className="group relative rounded-lg overflow-hidden border bg-muted/30 hover:ring-2 hover:ring-primary/50 transition-all h-32 w-48 flex items-center justify-center"
      >
        <video src={fullUrl} className="h-full w-full object-cover" muted preload="metadata" />
        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-colors flex items-center justify-center">
          <div className="h-10 w-10 rounded-full bg-white/90 flex items-center justify-center shadow">
            <Play className="h-5 w-5 text-primary ml-0.5" />
          </div>
        </div>
        <p className="text-[10px] text-white truncate px-1.5 py-1 bg-black/50 absolute bottom-0 left-0 right-0">
          {anexo.nome}
        </p>
      </button>
    );
  }

  if (cat === "audio") {
    return (
      <div className="rounded-lg border bg-muted/30 p-2.5 w-64">
        <div className="flex items-center gap-2 mb-2">
          <FileAudio className="h-4 w-4 text-violet-500 shrink-0" />
          <span className="text-xs font-medium truncate">{anexo.nome}</span>
        </div>
        <audio controls className="w-full h-8" preload="metadata">
          <source src={fullUrl} type={anexo.tipo} />
        </audio>
      </div>
    );
  }

  if (cat === "pdf") {
    return (
      <button
        onClick={() => onPreview(anexo)}
        className="group rounded-lg border bg-muted/30 hover:ring-2 hover:ring-primary/50 transition-all p-3 flex items-center gap-3 w-64"
      >
        <div className="h-12 w-10 rounded bg-red-100 dark:bg-red-900/30 flex items-center justify-center shrink-0">
          <FileText className="h-6 w-6 text-red-600 dark:text-red-400" />
        </div>
        <div className="min-w-0 text-left">
          <p className="text-xs font-medium truncate">{anexo.nome}</p>
          <p className="text-[10px] text-muted-foreground">PDF · Clique para visualizar</p>
        </div>
        <Eye className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
      </button>
    );
  }

  // Fallback: other file types
  return (
    <a
      href={fullUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="rounded-lg border bg-muted/30 hover:bg-muted transition-colors p-3 flex items-center gap-3 w-64"
    >
      <div className="h-10 w-10 rounded bg-muted flex items-center justify-center shrink-0">
        <FileIcon className="h-5 w-5 text-muted-foreground" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium truncate">{anexo.nome}</p>
        <p className="text-[10px] text-muted-foreground">Clique para baixar</p>
      </div>
      <Download className="h-4 w-4 text-muted-foreground shrink-0" />
    </a>
  );
}

function LightboxPreview({
  anexo,
  onClose,
}: {
  anexo: { nome: string; url: string; tipo: string } | null;
  onClose: () => void;
}) {
  if (!anexo) return null;
  const cat = getFileCategory(anexo.tipo, anexo.nome);
  const fullUrl = resolveUrl(anexo.url);

  return (
    <div
      className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-4"
      onClick={(e) => { e.stopPropagation(); onClose(); }}
      onMouseDown={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
      onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } }}
      role="dialog"
      tabIndex={-1}
      ref={(el) => el?.focus()}
    >
      <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
        <a
          href={fullUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
          className="h-9 w-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
        >
          <Download className="h-4 w-4 text-white" />
        </a>
        <button
          onClick={(e) => { e.stopPropagation(); onClose(); }}
          onMouseDown={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
          className="h-9 w-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
        >
          <X className="h-5 w-5 text-white" />
        </button>
      </div>

      <div
        className="max-w-[90vw] max-h-[85vh] flex items-center justify-center"
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        {cat === "image" && (
          <img
            src={fullUrl}
            alt={anexo.nome}
            className="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
          />
        )}
        {cat === "pdf" && (
          <iframe
            src={fullUrl}
            className="w-[80vw] h-[85vh] rounded-lg bg-white"
            title={anexo.nome}
          />
        )}
        {cat === "video" && (
          <video
            src={fullUrl}
            controls
            autoPlay
            className="max-w-full max-h-[85vh] rounded-lg shadow-2xl"
          />
        )}
        {cat === "audio" && (
          <div className="bg-card rounded-xl p-8 shadow-2xl text-center space-y-4 min-w-[320px]">
            <FileAudio className="h-12 w-12 text-violet-500 mx-auto" />
            <p className="text-sm font-medium">{anexo.nome}</p>
            <audio controls autoPlay className="w-full">
              <source src={fullUrl} type={anexo.tipo} />
            </audio>
          </div>
        )}
      </div>

      <p className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-xs">
        {anexo.nome}
      </p>
    </div>
  );
}

// ============================================================
// Draft system (localStorage)
// ============================================================

interface CRMDraft {
  id: string;
  form: CRMTicketCreate;
  step: number;
  createdAt: string;
  updatedAt: string;
}

const DRAFTS_KEY = "crm_ticket_drafts";

function getDrafts(): CRMDraft[] {
  try {
    const raw = localStorage.getItem(DRAFTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveDraft(draft: CRMDraft) {
  const drafts = getDrafts().filter((d) => d.id !== draft.id);
  drafts.unshift({ ...draft, updatedAt: new Date().toISOString() });
  localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

function removeDraft(id: string) {
  const drafts = getDrafts().filter((d) => d.id !== id);
  localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

function isFormEmpty(form: CRMTicketCreate): boolean {
  return !form.id_pedido && !form.nome_cliente && !form.telefone && !form.email && !form.descricao;
}

// ============================================================
// Helpers
// ============================================================

const formatDate = (dateStr: string) => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("pt-BR");
};

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatTelefone = (value: string): string => {
  const numbers = value.replace(/\D/g, "");
  const limited = numbers.slice(0, 11);
  if (limited.length <= 2) return limited;
  if (limited.length <= 7) return `(${limited.slice(0, 2)}) ${limited.slice(2)}`;
  return `(${limited.slice(0, 2)}) ${limited.slice(2, 7)}-${limited.slice(7)}`;
};

const unformatTelefone = (value: string): string => value.replace(/\D/g, "");

// SLA status based on prazo
function getSlaStatus(prazo: string, status: CRMTicketStatus) {
  if (status === "resolvido") return { color: "text-emerald-600", bg: "bg-emerald-50", label: "Resolvido", icon: CheckCircle2 };
  const now = new Date();
  const deadline = new Date(prazo + "T23:59:59");
  const diffDays = Math.ceil((deadline.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return { color: "text-red-600", bg: "bg-red-50", label: `${Math.abs(diffDays)}d atrasado`, icon: AlertTriangle };
  if (diffDays <= 1) return { color: "text-amber-600", bg: "bg-amber-50", label: "Vence hoje/amanhã", icon: Clock };
  return { color: "text-emerald-600", bg: "bg-emerald-50", label: `${diffDays}d restantes`, icon: Clock };
}

const STATUS_CONFIG: Record<CRMTicketStatus, { title: string; color: string; bgCard: string; bgColumn: string; icon: React.ElementType; badgeVariant: "default" | "secondary" | "destructive" | "outline" }> = {
  novo: { title: "Novos", color: "text-blue-700", bgCard: "border-l-blue-500", bgColumn: "bg-blue-50/50", icon: Inbox, badgeVariant: "default" },
  em_andamento: { title: "Em Andamento", color: "text-amber-700", bgCard: "border-l-amber-500", bgColumn: "bg-amber-50/50", icon: ArrowRight, badgeVariant: "secondary" },
  retorno: { title: "Retorno", color: "text-purple-700", bgCard: "border-l-purple-500", bgColumn: "bg-purple-50/50", icon: Clock, badgeVariant: "secondary" },
  resolvido: { title: "Resolvidos", color: "text-emerald-700", bgCard: "border-l-emerald-500", bgColumn: "bg-emerald-50/50", icon: CheckCircle2, badgeVariant: "outline" },
};

const COLUMNS: CRMTicketStatus[] = ["novo", "em_andamento", "retorno", "resolvido"];

// ============================================================
// Draggable Ticket Card
// ============================================================

interface TicketCardProps {
  ticket: CRMTicket;
  onClick: (ticket: CRMTicket) => void;
  isDragOverlay?: boolean;
}

function TicketCard({ ticket, onClick, isDragOverlay }: TicketCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `ticket-${ticket.id}`,
    data: { ticket },
  });

  const sla = getSlaStatus(ticket.prazo, ticket.status);
  const SlaIcon = sla.icon;
  const config = STATUS_CONFIG[ticket.status];

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <div
      ref={!isDragOverlay ? setNodeRef : undefined}
      style={style}
      className={`
        group relative rounded-lg border bg-card p-3.5 shadow-sm transition-all cursor-pointer
        border-l-[3px] ${config.bgCard}
        ${isDragging ? "opacity-30 scale-95" : "hover:shadow-md hover:-translate-y-0.5"}
        ${isDragOverlay ? "shadow-xl ring-2 ring-primary/20 rotate-1" : ""}
      `}
      onClick={() => onClick(ticket)}
    >
      {/* Drag handle */}
      <div
        {...listeners}
        {...attributes}
        className="absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing hover:bg-muted"
        onClick={(e) => e.stopPropagation()}
      >
        <GripVertical className="h-3.5 w-3.5 text-muted-foreground" />
      </div>

      {/* Header: ID + Motivo */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-mono text-muted-foreground mb-0.5">{ticket.id_pedido}</p>
          <h4 className="text-sm font-semibold text-foreground truncate">{ticket.nome_cliente}</h4>
        </div>
      </div>

      {/* Info tags */}
      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        <Badge variant="outline" className={`text-xs font-normal ${
          ticket.status_detalhe === "Resolvido" ? "border-emerald-300 text-emerald-700 bg-emerald-50" :
          ticket.status_detalhe?.startsWith("Aguardando") ? "border-amber-300 text-amber-700 bg-amber-50" :
          ticket.status_detalhe === "Em Andamento" || ticket.status_detalhe === "Em Análise" ? "border-blue-300 text-blue-700 bg-blue-50" :
          ticket.status_detalhe?.startsWith("Pendente") ? "border-orange-300 text-orange-700 bg-orange-50" :
          ""
        }`}>
          {ticket.area ? (
            <>
              {ticket.area}
              {ticket.motivo && (
                <>
                  <span className="opacity-60 mx-1">|</span>
                  {ticket.motivo}
                </>
              )}
            </>
          ) : (ticket.status_detalhe || "Novo")}
        </Badge>
        {ticket.tipo_operacao_venda && (
          <Badge variant={/futura\s*(externa|interna)/i.test(ticket.tipo_operacao_venda) ? "destructive" : "secondary"} className="text-[10px]">
            {ticket.tipo_operacao_venda}
          </Badge>
        )}
        {ticket.situacao_timeline && (
          <Badge variant="secondary" className="text-[10px]">
            {ticket.situacao_timeline}
          </Badge>
        )}
        {(ticket.children_count || 0) > 0 && (
          <Badge variant="outline" className="text-[10px] gap-0.5">
            <Hash className="h-2.5 w-2.5" />
            {ticket.children_count} sub
          </Badge>
        )}
        {ticket.necessita_analise && (
          <Badge variant="destructive" className="text-[10px] gap-0.5 animate-pulse">
            <Bell className="h-2.5 w-2.5" />
            Necessita Análise
          </Badge>
        )}
        {ticket.data_nova_analise && !ticket.necessita_analise && ticket.status !== "resolvido" && (
          <Badge variant="outline" className="text-[10px] gap-0.5 border-blue-300 text-blue-700 bg-blue-50">
            <CalendarClock className="h-2.5 w-2.5" />
            Agendado {new Date(ticket.data_nova_analise + "T00:00:00").toLocaleDateString("pt-BR")}
          </Badge>
        )}
      </div>

      {/* Footer: SLA + Analista */}
      <div className="flex items-center justify-between gap-2">
        <div className={`flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded-md ${sla.bg} ${sla.color}`}>
          <SlaIcon className="h-3.5 w-3.5" />
          <span>{sla.label}</span>
        </div>
        {ticket.analista_nome && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1">
                  <div className="h-5 w-5 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-[10px] font-medium text-primary">
                      {ticket.analista_nome.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                    </span>
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{ticket.analista_nome}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      {/* Comment count indicator */}
      {ticket.comentarios.length > 0 && (
        <div className="absolute bottom-3 right-3 flex items-center gap-0.5 text-muted-foreground">
          <MessageSquare className="h-3 w-3" />
          <span className="text-[10px]">{ticket.comentarios.length}</span>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Droppable Kanban Column
// ============================================================

interface KanbanColumnProps {
  status: CRMTicketStatus;
  tickets: CRMTicket[];
  onTicketClick: (ticket: CRMTicket) => void;
}

function KanbanColumn({ status, tickets, onTicketClick }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `column-${status}`,
    data: { status },
  });

  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  return (
    <div
      ref={setNodeRef}
      className={`
        flex flex-col rounded-xl border transition-colors min-h-[500px]
        ${config.bgColumn}
        ${isOver ? "ring-2 ring-primary/30 bg-primary/5" : ""}
      `}
    >
      {/* Column Header */}
      <div className="flex items-center gap-2 p-4 pb-3">
        <Icon className={`h-4 w-4 ${config.color}`} />
        <h3 className={`text-sm font-semibold ${config.color}`}>{config.title}</h3>
        <Badge variant={config.badgeVariant} className="ml-auto text-xs h-5 min-w-[20px] justify-center">
          {tickets.length}
        </Badge>
      </div>

      {/* Cards */}
      <ScrollArea className="flex-1 px-3 pb-3">
        <div className="space-y-2.5">
          {tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="rounded-full bg-muted p-3 mb-2">
                <Icon className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="text-xs text-muted-foreground">Nenhum ticket</p>
            </div>
          ) : (
            tickets.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} onClick={onTicketClick} />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

// ============================================================
// Stat Card
// ============================================================

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  bgColor,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  color: string;
  bgColor: string;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={`rounded-lg p-2 ${bgColor}`}>
            <Icon className={`h-4 w-4 ${color}`} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================
// New Ticket Dialog
// ============================================================

interface NewTicketDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
  draftToLoad?: CRMDraft | null;
  onDraftChange?: () => void;
  areas?: string[];
  areasMap?: {id: number; nome: string}[];
  motivos?: {nome: string; area_id: number | null}[];
  plataformas?: string[];
  credenciadas?: string[];
}

function NewTicketDialog({ open, onOpenChange, onCreated, draftToLoad, onDraftChange, areas, areasMap = [], motivos, plataformas = [], credenciadas = [] }: NewTicketDialogProps) {
  // areas = crm_areas (UI: "Motivo"), motivos = crm_motivos (UI: "Área")
  const motivoList = areas && areas.length > 0 ? areas : [...CRM_AREAS];
  const areaObjectList = motivos && motivos.length > 0 ? motivos : [];
  const dynamicPlataformas = plataformas;
  const dynamicCredenciadas = credenciadas;
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [buscandoPedido, setBuscandoPedido] = useState(false);
  const [produtosEncontrados, setProdutosEncontrados] = useState<ProdutoVenda[]>([]);
  const [pedidoEncontrado, setPedidoEncontrado] = useState(false);
  const [pedidoNaoEncontrado, setPedidoNaoEncontrado] = useState(false);
  const [confirmacaoSemPedido, setConfirmacaoSemPedido] = useState("");
  const [semPedidoConfirmado, setSemPedidoConfirmado] = useState(false);
  const [clienteData, setClienteData] = useState<ClientePedido | null>(null);
  const [produtoSelecionado, setProdutoSelecionado] = useState<ProdutoVenda | null>(null);
  const [montagemData, setMontagemData] = useState<DadosMontagem[]>([]);
  const [nmresolveData, setNmresolveData] = useState<DadosNMResolve[]>([]);
  const [draftId, setDraftId] = useState<string | null>(null);
  const [form, setForm] = useState<CRMTicketCreate>({
    id_pedido: "",
    nome_cliente: "",
    telefone: "",
    email: "",
    area: "",
    motivo: "",
    descricao: "",
    glpi: "",
    id_processo: "",
    plataforma: "",
    credenciada: "",
    prazo: "",
    produto: "",
    nome_produto: "",
  });
  const [anexos, setAnexos] = useState<File[]>([]);

  const FRASE_CONFIRMACAO = "Sim, desejo criar sem id pedido";

  // Load draft when draftToLoad changes
  useEffect(() => {
    if (draftToLoad && open) {
      setForm(draftToLoad.form);
      setStep(draftToLoad.step || 1);
      setDraftId(draftToLoad.id);
      // Re-fetch pedido data to restore clienteData and products
      if (draftToLoad.form.id_pedido) {
        setBuscandoPedido(true);
        crmService.buscarDadosPedido(draftToLoad.form.id_pedido).then((dados) => {
          if (dados && dados.cliente) {
            setClienteData(dados.cliente);
            setPedidoEncontrado(true);
            setMontagemData(dados.montagem || []);
            setNmresolveData(dados.nmresolve || []);
            if (dados.produtos && dados.produtos.length > 0) {
              setProdutosEncontrados(dados.produtos);
              // Restore selected product from draft form
              if (draftToLoad.form.produto) {
                const p = dados.produtos.find((pr) => pr.produto === draftToLoad.form.produto);
                setProdutoSelecionado(p || null);
              } else if (dados.produtos.length === 1) {
                setProdutoSelecionado(dados.produtos[0]);
              }
            }
          } else {
            // Pedido not found anymore — allow manual
            setSemPedidoConfirmado(true);
          }
        }).catch(() => {
          setSemPedidoConfirmado(true);
        }).finally(() => {
          setBuscandoPedido(false);
        });
      } else {
        // Draft without pedido
        setSemPedidoConfirmado(true);
      }
    }
  }, [draftToLoad, open]);

  const emptyForm: CRMTicketCreate = {
    id_pedido: "",
    nome_cliente: "",
    telefone: "",
    email: "",
    area: "",
    motivo: "",
    descricao: "",
    glpi: "",
    id_processo: "",
    plataforma: "",
    credenciada: "",
    prazo: "",
    produto: "",
    nome_produto: "",
  };

  const resetForm = () => {
    setStep(1);
    setForm({ ...emptyForm });
    setAnexos([]);
    setProdutosEncontrados([]);
    setPedidoEncontrado(false);
    setPedidoNaoEncontrado(false);
    setConfirmacaoSemPedido("");
    setSemPedidoConfirmado(false);
    setClienteData(null);
    setProdutoSelecionado(null);
    setMontagemData([]);
    setNmresolveData([]);
    setDraftId(null);
  };

  // Auto-save as draft when closing with data
  const handleClose = (saveAsDraft: boolean) => {
    if (saveAsDraft && !isFormEmpty(form)) {
      const id = draftId || crypto.randomUUID();
      saveDraft({
        id,
        form,
        step,
        createdAt: draftId ? getDrafts().find((d) => d.id === draftId)?.createdAt || new Date().toISOString() : new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
      toast.info("Rascunho salvo!");
      onDraftChange?.();
    }
    resetForm();
    onOpenChange(false);
  };

  const handleDiscardDraft = () => {
    if (draftId) {
      removeDraft(draftId);
      onDraftChange?.();
    }
    resetForm();
    onOpenChange(false);
  };

  const buscarPedido = async () => {
    if (!form.id_pedido) return;
    setBuscandoPedido(true);
    setProdutosEncontrados([]);
    setPedidoEncontrado(false);
    setPedidoNaoEncontrado(false);
    setConfirmacaoSemPedido("");
    setSemPedidoConfirmado(false);
    setClienteData(null);
    setProdutoSelecionado(null);
    try {
      const dados = await crmService.buscarDadosPedido(form.id_pedido);
      if (dados && dados.cliente) {
        setClienteData(dados.cliente);
        setForm((f) => ({
          ...f,
          nome_cliente: dados.cliente!.nome_cliente || f.nome_cliente,
          telefone: dados.cliente!.telefone_cliente || f.telefone,
          plataforma: dados.cliente!.filial_venda || f.plataforma,
        }));
        setPedidoEncontrado(true);
        setMontagemData(dados.montagem || []);
        setNmresolveData(dados.nmresolve || []);
        if (dados.produtos && dados.produtos.length > 0) {
          setProdutosEncontrados(dados.produtos);
          if (dados.produtos.length === 1) {
            const p = dados.produtos[0];
            setProdutoSelecionado(p);
            setForm((f) => ({
              ...f,
              produto: p.produto,
              nome_produto: p.nome_produto,
            }));
          }
          toast.success(`Pedido encontrado! ${dados.produtos.length} produto(s).`);
        } else {
          toast.success("Pedido encontrado! Dados do cliente preenchidos.");
        }
      } else {
        setPedidoNaoEncontrado(true);
        toast.warning("ID do pedido não encontrado na base de dados.");
      }
    } catch {
      setPedidoNaoEncontrado(true);
      toast.error("Erro ao buscar dados do pedido");
    } finally {
      setBuscandoPedido(false);
    }
  };

  const confirmarSemPedido = () => {
    if (confirmacaoSemPedido.trim() === FRASE_CONFIRMACAO) {
      setSemPedidoConfirmado(true);
      setPedidoNaoEncontrado(false);
      toast.info("Prosseguindo sem ID do pedido.");
    } else {
      toast.error("Frase de confirmação incorreta. Digite exatamente como indicado.");
    }
  };

  const podeAvancar = () => {
    if (pedidoEncontrado) {
      if (produtosEncontrados.length > 1 && !form.produto) return false;
      return true;
    }
    if (semPedidoConfirmado) return true;
    return false;
  };

  const avancarEtapa = () => {
    if (!podeAvancar()) return;
    setStep(2);
  };

  const handleSubmit = async () => {
    if (!form.nome_cliente) return toast.error("Informe o nome do cliente");
    if (!form.telefone) return toast.error("Informe o telefone");
    if (!form.area) return toast.error("Selecione a área");
    if (!form.motivo) return toast.error("Selecione o motivo");
    if (!form.descricao) return toast.error("Informe a descrição");
    if (!form.glpi) return toast.error("Informe o ID GLPI");
    if (!form.id_processo) return toast.error("Informe o ID Processo");
    if (!form.plataforma) return toast.error("Selecione a plataforma");
    if (!form.credenciada) return toast.error("Informe a credenciada");
    if (!form.prazo) return toast.error("Defina o prazo");

    setSubmitting(true);
    try {
      await crmService.createTicket({
        ...form,
        anexos: anexos.length > 0 ? anexos : undefined,
        tipo_operacao_venda: clienteData?.tipo_operacao_venda || undefined,
        situacao_timeline: clienteData?.situacao_timeline || undefined,
      });
      toast.success("Ticket criado com sucesso! Atribuído automaticamente ao analista disponível.");
      // Remove draft if was loaded from one
      if (draftId) {
        removeDraft(draftId);
        onDraftChange?.();
      }
      resetForm();
      onOpenChange(false);
      onCreated();
    } catch (err: any) {
      toast.error(err.message || "Erro ao criar ticket");
    } finally {
      setSubmitting(false);
    }
  };

  // Step indicator
  const StepIndicator = () => (
    <div className="flex items-center justify-center gap-2 mb-4">
      <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${step === 1 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
        <span>1</span>
        <span>Identificação</span>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
      <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${step === 2 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
        <span>2</span>
        <span>Dados & Caso</span>
      </div>
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(true); }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            {draftId ? "Continuar Rascunho" : "Novo Ticket"}
          </DialogTitle>
          <DialogDescription>
            {step === 1
              ? "Identifique o pedido do cliente para preenchimento automático"
              : "Confira os dados e preencha as informações do caso"}
          </DialogDescription>
        </DialogHeader>

        <StepIndicator />

        {/* ============================================================ */}
        {/* ETAPA 1 - Identificação do Pedido                          */}
        {/* ============================================================ */}
        {step === 1 && (
          <div className="space-y-5 py-2">
            {/* ID Pedido + Buscar */}
            <div className="space-y-2">
              <Label htmlFor="id_pedido" className="text-sm font-medium">ID Pedido</Label>
              <div className="flex gap-2">
                <Input
                  id="id_pedido"
                  placeholder="Ex: 123456"
                  value={form.id_pedido}
                  onChange={(e) => {
                    setForm({ ...form, id_pedido: e.target.value });
                    setPedidoNaoEncontrado(false);
                    setPedidoEncontrado(false);
                    setConfirmacaoSemPedido("");
                    setSemPedidoConfirmado(false);
                    setProdutosEncontrados([]);
                    setProdutoSelecionado(null);
                    setClienteData(null);
                  }}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); buscarPedido(); } }}
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={buscarPedido}
                  disabled={buscandoPedido || !form.id_pedido}
                  className="shrink-0"
                >
                  {buscandoPedido ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-1" />
                      Buscar
                    </>
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Informe o ID e clique em Buscar para preenchimento automático
              </p>
            </div>

            {/* Alert: Pedido não encontrado */}
            {pedidoNaoEncontrado && !semPedidoConfirmado && (
              <div className="rounded-lg border border-orange-300 bg-orange-50 p-4 space-y-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-orange-800">Pedido não encontrado</p>
                    <p className="text-xs text-orange-700 mt-1">
                      O ID <span className="font-mono font-bold">{form.id_pedido}</span> não foi localizado na base de dados.
                      Para criar o ticket sem ID do pedido, digite a frase abaixo exatamente como indicado:
                    </p>
                  </div>
                </div>
                <div className="space-y-2 pl-7">
                  <p className="text-xs font-medium text-orange-800 bg-orange-100 rounded px-2 py-1 inline-block">
                    &quot;{FRASE_CONFIRMACAO}&quot;
                  </p>
                  <Input
                    placeholder="Digite a frase de confirmação..."
                    value={confirmacaoSemPedido}
                    onChange={(e) => setConfirmacaoSemPedido(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); confirmarSemPedido(); } }}
                    className="bg-white"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={confirmarSemPedido}
                    disabled={!confirmacaoSemPedido.trim()}
                    className="text-orange-700 border-orange-300 hover:bg-orange-100"
                  >
                    Criar ticket sem ID pedido
                  </Button>
                </div>
              </div>
            )}

            {/* Confirmação sem pedido aceita */}
            {semPedidoConfirmado && (
              <div className="rounded-lg border border-blue-300 bg-blue-50 p-3 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-blue-500 shrink-0" />
                <p className="text-sm text-blue-800">
                  Ticket será criado sem vínculo a um pedido. Preencha os dados manualmente na próxima etapa.
                </p>
              </div>
            )}

            {/* Pedido encontrado: mostra nome do cliente */}
            {pedidoEncontrado && clienteData && (
              <div className="rounded-lg border border-green-300 bg-green-50 p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-green-800">Pedido encontrado</p>
                    <p className="text-base font-medium text-green-900 mt-0.5">{clienteData.nome_cliente}</p>
                  </div>
                </div>

                {/* Seletor de Produto */}
                {produtosEncontrados.length > 0 && (
                  <div className="space-y-2 pl-7">
                    <Label className="text-sm font-medium text-green-800">
                      Selecione o produto {produtosEncontrados.length > 1 ? "*" : ""}
                    </Label>
                    {produtosEncontrados.length === 1 ? (
                      <div className="flex items-center gap-2 p-2 rounded-lg bg-white border border-green-200">
                        <Tag className="h-4 w-4 text-green-600" />
                        <span className="text-sm font-medium">{produtosEncontrados[0].nome_produto}</span>
                        {produtosEncontrados[0].numero_nf && (
                          <Badge variant="outline" className="ml-auto text-xs border-green-300 text-green-700">
                            NF {produtosEncontrados[0].numero_nf}
                          </Badge>
                        )}
                      </div>
                    ) : (
                      <Select
                        value={form.produto || ""}
                        onValueChange={(val) => {
                          const prod = produtosEncontrados.find((p) => p.produto === val);
                          setProdutoSelecionado(prod || null);
                          setForm((f) => ({
                            ...f,
                            produto: val,
                            nome_produto: prod?.nome_produto || "",
                          }));
                        }}
                      >
                        <SelectTrigger className="bg-white">
                          <SelectValue placeholder="Selecione o produto" />
                        </SelectTrigger>
                        <SelectContent>
                          {produtosEncontrados.map((p, i) => (
                            <SelectItem key={`${p.produto}-${i}`} value={p.produto}>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{p.nome_produto}</span>
                                {p.numero_nf && (
                                  <span className="text-muted-foreground text-xs">— NF {p.numero_nf}</span>
                                )}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                    <p className="text-xs text-green-700">
                      {produtosEncontrados.length} produto(s) encontrado(s) para este pedido
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Footer Etapa 1 */}
            <DialogFooter className="flex items-center justify-between pt-2">
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={handleDiscardDraft} className="text-muted-foreground">
                  <Trash2 className="h-3.5 w-3.5 mr-1" />
                  Descartar
                </Button>
                {!isFormEmpty(form) && (
                  <Button variant="ghost" size="sm" onClick={() => handleClose(true)} className="text-blue-600 hover:text-blue-700 hover:bg-blue-50">
                    <Save className="h-3.5 w-3.5 mr-1" />
                    Salvar rascunho
                  </Button>
                )}
              </div>
              <Button onClick={avancarEtapa} disabled={!podeAvancar()}>
                Próximo
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* ============================================================ */}
        {/* ETAPA 2 - Resumo dos Dados + Informações do Caso           */}
        {/* ============================================================ */}
        {step === 2 && (
          <div className="space-y-6 py-2">
            {/* Resumo dos dados do pedido */}
            {pedidoEncontrado && clienteData && (() => {
              const prod = produtoSelecionado || (produtosEncontrados.length === 1 ? produtosEncontrados[0] : null);
              const isVendaFutura = clienteData.tipo_operacao_venda
                ? /futura\s*(externa|interna)/i.test(clienteData.tipo_operacao_venda)
                : false;
              return (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <FileText className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">Dados do Pedido</h3>
                  </div>
                  <Separator className="mb-3" />
                  <div className="rounded-xl border bg-card p-5 shadow-sm space-y-3">
                    {/* Linha 1: ID Pedido + Cliente + Situação Nota */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-baseline gap-3">
                          <span className="text-xs text-muted-foreground uppercase tracking-wide">ID Pedido</span>
                          <span className="font-mono text-sm font-semibold">{form.id_pedido}</span>
                        </div>
                        <div className="flex items-baseline gap-3">
                          <span className="text-xs text-muted-foreground uppercase tracking-wide">Cliente</span>
                          <span className="text-sm font-semibold">{clienteData.nome_cliente}</span>
                        </div>
                        {clienteData.cpf_cnpj_cliente && (
                          <div className="flex items-baseline gap-3">
                            <span className="text-xs text-muted-foreground uppercase tracking-wide">CPF/CNPJ</span>
                            <span className="text-sm font-mono font-medium">{clienteData.cpf_cnpj_cliente}</span>
                          </div>
                        )}
                        {clienteData.data_emissao && (
                          <div className="flex items-baseline gap-3">
                            <span className="text-xs text-muted-foreground uppercase tracking-wide">Data Emissão</span>
                            <span className="text-sm font-medium">{formatDate(clienteData.data_emissao)}</span>
                          </div>
                        )}
                      </div>
                      {prod?.situacao_nota && (
                        <div className="text-right shrink-0">
                          <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Situação Nota</p>
                          <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-semibold ${
                            /emitida|faturado/i.test(prod.situacao_nota) ? "bg-green-50 text-green-700 ring-1 ring-green-200" :
                            /cancelada/i.test(prod.situacao_nota) ? "bg-red-50 text-red-700 ring-1 ring-red-200" :
                            "bg-slate-50 text-slate-700 ring-1 ring-slate-200"
                          }`}>
                            {prod.situacao_nota}
                          </span>
                        </div>
                      )}
                    </div>

                    <Separator className="my-1" />

                    {/* Linha 2: Filiais + NF */}
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Filial Saída</p>
                        <p className="text-sm font-medium">{clienteData.filial_saida || "—"}</p>
                      </div>
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Número NF</p>
                        <p className="text-sm font-mono font-medium">{prod?.numero_nf || "—"}</p>
                      </div>
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Série NF</p>
                        <p className="text-sm font-mono font-medium">{prod?.serie_nf || "—"}</p>
                      </div>
                    </div>

                    {/* Linha 3: Filial Venda + Produto + Nome Produto */}
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Filial Venda</p>
                        <p className="text-sm font-medium">{clienteData.filial_venda || "—"}</p>
                      </div>
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Produto</p>
                        <p className="text-sm font-mono font-medium">{prod?.produto || "—"}</p>
                      </div>
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Nome Produto</p>
                        <p className="text-sm font-medium leading-tight">{prod?.nome_produto || "—"}</p>
                      </div>
                    </div>

                    {/* Datas de Entrega (quando disponíveis) */}
                    {(clienteData.data_previsao_entrega || clienteData.data_entrega_efetiva) && (
                      <div className="grid grid-cols-3 gap-4">
                        {clienteData.data_previsao_entrega && (
                          <div>
                            <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Previsão Entrega</p>
                            <p className="text-sm font-medium">{formatDate(clienteData.data_previsao_entrega)}</p>
                          </div>
                        )}
                        {clienteData.data_entrega_efetiva && (
                          <div>
                            <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Entrega Efetiva</p>
                            <p className="text-sm font-medium text-green-600">{formatDate(clienteData.data_entrega_efetiva)}</p>
                          </div>
                        )}
                      </div>
                    )}

                    <Separator className="my-1" />

                    {/* Linha 4: Tipo Operação + Situação Timeline */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Tipo Operação</p>
                        <p className={`text-sm font-semibold ${isVendaFutura ? "text-red-600" : ""}`}>
                          {clienteData.tipo_operacao_venda || "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Situação Timeline</p>
                        {clienteData.situacao_timeline ? (
                          <Badge variant="secondary" className="text-xs mt-0.5">{clienteData.situacao_timeline}</Badge>
                        ) : (
                          <p className="text-sm">—</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Serviços (Montagem + NM Resolve) */}
            {pedidoEncontrado && (montagemData.length > 0 || nmresolveData.length > 0) && (() => {
              const selProd = produtoSelecionado || (produtosEncontrados.length === 1 ? produtosEncontrados[0] : null);
              const filteredMontagem = selProd
                ? montagemData.filter(m => m.identificador_nf === selProd.identificador_nf && m.produto === selProd.produto)
                : montagemData;
              const filteredNmresolve = selProd
                ? nmresolveData.filter(n => n.identificador_nf === selProd.identificador_nf && n.produto === selProd.produto)
                : nmresolveData;
              if (filteredMontagem.length === 0 && filteredNmresolve.length === 0) return null;
              return (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Wrench className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Serviços</h3>
                </div>
                <Separator className="mb-3" />
                <div className="space-y-3">
                  {/* Montagem */}
                  {filteredMontagem.length > 0 && (
                    <div className="rounded-xl border bg-card p-4 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Montagem</p>
                      <div className="space-y-2">
                        {filteredMontagem.map((m, i) => (
                          <div key={i} className={`grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm ${i > 0 ? "border-t pt-2" : ""}`}>
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Produto</p>
                              <p className="text-sm font-medium">{m.produto || "—"}</p>
                            </div>
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">ID Boletim Montagem</p>
                              <p className="text-sm font-medium">{m.identificador_boletim_montagem || "—"}</p>
                            </div>
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Previsão Montagem</p>
                              <p className="text-sm font-medium">{m.data_previsao_montagem ? formatDate(m.data_previsao_montagem) : "—"}</p>
                            </div>
                            {m.data_montagem && (
                              <div>
                                <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Data Montagem</p>
                                <p className="text-sm font-medium text-green-600">{formatDate(m.data_montagem)}</p>
                              </div>
                            )}
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Situação Boletim</p>
                              <Badge variant="secondary" className="text-xs">{m.situacao_boletim || "—"}</Badge>
                            </div>
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Montador</p>
                              <p className="text-sm font-medium">{m.nome_montador || "—"}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* NM Resolve */}
                  {filteredNmresolve.length > 0 && (
                    <div className="rounded-xl border bg-card p-4 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">NM Resolve</p>
                      <div className="space-y-2">
                        {filteredNmresolve.map((n, i) => (
                          <div key={i} className={`grid grid-cols-3 gap-x-4 gap-y-1.5 text-sm ${i > 0 ? "border-t pt-2" : ""}`}>
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Modalidade</p>
                              <p className="text-sm font-medium">{n.modalidade || "—"}</p>
                            </div>
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Situação Serviço</p>
                              <Badge variant="secondary" className="text-xs">{n.situacao_servico || "—"}</Badge>
                            </div>
                            <div>
                              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">Situação Boletim</p>
                              <Badge variant="outline" className="text-xs">{n.situacao_boletim || "—"}</Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              );
            })()}

            {/* Sem pedido */}
            {semPedidoConfirmado && (
              <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-blue-500 shrink-0" />
                <p className="text-sm text-blue-700">Ticket sem vínculo a pedido. Preencha todos os dados manualmente.</p>
              </div>
            )}

            {/* ---- Seção: Informações do Cliente (editáveis) ---- */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <User className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Informações do Cliente</h3>
              </div>
              <Separator className="mb-4" />
              <div className="grid gap-4">
                {/* Nome Cliente */}
                <div className="space-y-2">
                  <Label htmlFor="nome_cliente">Nome do Cliente *</Label>
                  <div className="relative">
                    <Input
                      id="nome_cliente"
                      placeholder="Nome completo do cliente"
                      value={form.nome_cliente}
                      onChange={(e) => setForm({ ...form, nome_cliente: e.target.value })}
                      className={pedidoEncontrado && form.nome_cliente ? "pr-8 border-green-300 bg-green-50/50" : ""}
                    />
                    {pedidoEncontrado && form.nome_cliente && (
                      <CheckCircle2 className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500" />
                    )}
                  </div>
                </div>

                {/* Telefone + Email */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="telefone">Telefone *</Label>
                    <Input
                      id="telefone"
                      type="tel"
                      placeholder="(11) 99999-9999"
                      value={formatTelefone(form.telefone)}
                      onChange={(e) => setForm({ ...form, telefone: unformatTelefone(e.target.value) })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="cliente@email.com"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                    />
                  </div>
                </div>

                {/* Anexos */}
                <div className="space-y-2">
                  <Label>Anexos</Label>
                  <div className="flex items-center gap-2">
                    <label
                      htmlFor="anexos"
                      className="flex items-center gap-2 px-4 py-2 border border-dashed rounded-lg cursor-pointer hover:bg-muted transition-colors flex-1"
                    >
                      <Paperclip className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        {anexos.length > 0 ? `${anexos.length} arquivo(s) selecionado(s)` : "Clique para selecionar arquivos"}
                      </span>
                    </label>
                    <input
                      id="anexos"
                      type="file"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files) setAnexos((prev) => [...prev, ...Array.from(e.target.files!)]);
                        e.target.value = "";
                      }}
                    />
                    {anexos.length > 0 && (
                      <Button variant="ghost" size="sm" onClick={() => setAnexos([])}>
                        Limpar
                      </Button>
                    )}
                  </div>
                  {anexos.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {anexos.map((f, i) => (
                        <Badge key={i} variant="secondary" className="text-[10px] gap-1 pr-1">
                          {f.name}
                          <button onClick={() => setAnexos((prev) => prev.filter((_, idx) => idx !== i))} className="ml-0.5 hover:text-destructive">
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">PDF, imagens ou documentos</p>
                </div>
              </div>
            </div>

            {/* ---- Seção: Informações do Caso ---- */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <FileText className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Informações do Caso</h3>
              </div>
              <Separator className="mb-4" />
              <div className="grid gap-4">
                {/* Área (top-level, from crm_areas) */}
                <div className="space-y-2">
                  <Label>Área *</Label>
                  <Select
                    value={form.area}
                    onValueChange={(v) => setForm({ ...form, area: v, motivo: "" })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione a área" />
                    </SelectTrigger>
                    <SelectContent>
                      {motivoList.map((a) => (
                        <SelectItem key={a} value={a}>
                          {a}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Motivo (mid-level, from crm_motivos, filtered by selected área) */}
                {(() => {
                  const selectedAreaObj = areasMap.find((am) => am.nome === form.area);
                  const filteredAreas = selectedAreaObj
                    ? areaObjectList.filter((m) => m.area_id === selectedAreaObj.id)
                    : [];
                  return (
                    <div className="space-y-2">
                      <Label>Motivo *</Label>
                      <Select
                        value={form.motivo || ""}
                        onValueChange={(v) => setForm({ ...form, motivo: v })}
                        disabled={!form.area || filteredAreas.length === 0}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder={!form.area ? "Selecione a área primeiro" : filteredAreas.length > 0 ? "Selecione o motivo" : "Nenhum motivo cadastrado para esta área"} />
                        </SelectTrigger>
                        <SelectContent>
                          {filteredAreas.map((m) => (
                            <SelectItem key={m.nome} value={m.nome}>
                              {m.nome}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {form.area && filteredAreas.length === 0 && (
                        <p className="text-xs text-amber-600">Cadastre um motivo para esta área em Parâmetros do CRM.</p>
                      )}
                    </div>
                  );
                })()}

                {/* Descrição */}
                <div className="space-y-2">
                  <Label htmlFor="descricao">Descrição *</Label>
                  <Textarea
                    id="descricao"
                    placeholder="Descreva o caso detalhadamente..."
                    rows={3}
                    value={form.descricao}
                    onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  />
                </div>

                {/* GLPI + ID Processo */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="glpi">GLPI *</Label>
                    <Input
                      id="glpi"
                      placeholder="Ex: GLI-44821"
                      value={form.glpi}
                      onChange={(e) => setForm({ ...form, glpi: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="id_processo">ID Processo *</Label>
                    <Input
                      id="id_processo"
                      placeholder="Ex: PROC-8821"
                      value={form.id_processo}
                      onChange={(e) => setForm({ ...form, id_processo: e.target.value })}
                    />
                  </div>
                </div>

                {/* Plataforma + Credenciada */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="plataforma">Plataforma *</Label>
                    <Select value={form.plataforma} onValueChange={(v) => setForm({ ...form, plataforma: v })}>
                      <SelectTrigger className="h-9">
                        <SelectValue placeholder="Selecione a plataforma" />
                      </SelectTrigger>
                      <SelectContent>
                        {dynamicPlataformas.map((p) => (
                          <SelectItem key={p} value={p}>{p}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="credenciada">Credenciada *</Label>
                    <Select value={form.credenciada} onValueChange={(v) => setForm({ ...form, credenciada: v })}>
                      <SelectTrigger className="h-9">
                        <SelectValue placeholder="Selecione a credenciada" />
                      </SelectTrigger>
                      <SelectContent>
                        {dynamicCredenciadas.length === 0 ? (
                          <div className="px-2 py-1.5 text-xs text-muted-foreground">Nenhuma credenciada cadastrada</div>
                        ) : (
                          dynamicCredenciadas.map((c) => (
                            <SelectItem key={c} value={c}>{c}</SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Prazo */}
                <div className="space-y-2">
                  <Label htmlFor="prazo">Prazo *</Label>
                  <Input
                    id="prazo"
                    type="date"
                    value={form.prazo}
                    onChange={(e) => setForm({ ...form, prazo: e.target.value })}
                    min={new Date().toISOString().split("T")[0]}
                  />
                  <p className="text-xs text-muted-foreground">
                    Data limite para resolução do caso
                  </p>
                </div>
              </div>
            </div>

            {/* Footer Etapa 2 */}
            <DialogFooter className="flex items-center justify-between pt-2">
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setStep(1)}>
                  Voltar
                </Button>
                {!isFormEmpty(form) && (
                  <Button variant="ghost" size="sm" onClick={() => handleClose(true)} className="text-blue-600 hover:text-blue-700 hover:bg-blue-50">
                    <Save className="h-3.5 w-3.5 mr-1" />
                    Salvar rascunho
                  </Button>
                )}
              </div>
              <Button onClick={handleSubmit} disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Criando...
                  </>
                ) : (
                  <>
                    <Plus className="mr-2 h-4 w-4" />
                    Criar Ticket
                  </>
                )}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ============================================================
// Ticket Detail — Full Screen Dialog
// ============================================================

interface TicketDetailSheetProps {
  ticket: CRMTicket | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onStatusChange: (id: number, status: CRMTicketStatus) => void;
  onCommentAdded: () => void;
  onDelete: (id: number) => void;
  statusOptions?: string[];
  analistas?: { id: number; nome: string }[];
  resolucaoOptions?: string[];
  areasMap?: { id: number; nome: string }[];
  motivos?: { nome: string; area_id: number | null }[];
}

function TicketDetailSheet({
  ticket,
  open,
  onOpenChange,
  onStatusChange,
  onCommentAdded,
  onDelete,
  statusOptions,
  analistas = [],
  resolucaoOptions = [],
  areasMap = [],
  motivos: motivosList = [],
}: TicketDetailSheetProps) {
  const dynamicResolucoes = resolucaoOptions;
  const { user } = useAuth();
  const statusList = statusOptions && statusOptions.length > 0 ? statusOptions : [...CRM_STATUS_DETALHE];
  const [comment, setComment] = useState("");
  const [commentAnexos, setCommentAnexos] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [statusAtual, setStatusAtual] = useState("");
  const [statusArea, setStatusArea] = useState("");
  const [resolucao, setResolucao] = useState("");
  const [descResolucao, setDescResolucao] = useState("");
  const [finalizando, setFinalizando] = useState(false);
  const [tipoInteracao, setTipoInteracao] = useState<"padrao" | "finalizacao">("padrao");
  const [dataNovaAnalise, setDataNovaAnalise] = useState("");

  // Approve/reject state
  const [retornoComentario, setRetornoComentario] = useState("");
  const [processandoRetorno, setProcessandoRetorno] = useState(false);

  // Bot data
  const [clienteData, setClienteData] = useState<ClientePedido | null>(null);
  const [produtosData, setProdutosData] = useState<ProdutoVenda[]>([]);
  const [montagemData, setMontagemData] = useState<DadosMontagem[]>([]);
  const [nmresolveData, setNmresolveData] = useState<DadosNMResolve[]>([]);
  const [loadingBot, setLoadingBot] = useState(false);
  const [now, setNow] = useState(() => new Date());

  // Lightbox
  const [lightboxAnexo, setLightboxAnexo] = useState<{ nome: string; url: string; tipo: string } | null>(null);

  // Child tickets
  const [viewingChild, setViewingChild] = useState<CRMTicket | null>(null);

  // Lembretes ativos
  const [lembretes, setLembretes] = useState<{ id: number; agendar_para: string; enviado: boolean }[]>([]);

  // Live countdown timer
  useEffect(() => {
    if (!open || ticket?.status === "resolvido") return;
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, [open, ticket?.status]);

  useEffect(() => {
    if (ticket && open) {
      setStatusAtual("");
      setStatusArea("");
      setDataNovaAnalise("");
      setResolucao(ticket.resolucao || "");
      setDescResolucao(ticket.descricao_resolucao || "");
      setComment("");
      setCommentAnexos([]);
      setViewingChild(null);
      // Fetch lembretes
      crmService.getLembretes(ticket.id)
        .then((data) => setLembretes(Array.isArray(data) ? data.filter(l => !l.enviado) : []))
        .catch(() => setLembretes([]));
      // Fetch bot data
      if (ticket.id_pedido) {
        setLoadingBot(true);
        crmService
          .buscarDadosPedido(ticket.id_pedido)
          .then((dados) => {
            if (dados) {
              setClienteData(dados.cliente);
              setProdutosData(dados.produtos || []);
              setMontagemData(dados.montagem || []);
              setNmresolveData(dados.nmresolve || []);
            }
          })
          .catch(() => {})
          .finally(() => setLoadingBot(false));
      } else {
        setClienteData(null);
        setProdutosData([]);
        setMontagemData([]);
        setNmresolveData([]);
      }
    }
  }, [ticket?.id, open]);

  if (!ticket) return null;

  // activeTicket is viewingChild (when viewing child) or ticket (parent)
  const displayTicket = viewingChild || ticket;
  const sla = getSlaStatus(displayTicket.prazo, displayTicket.status);
  const SlaIcon = sla.icon;

  const refreshAfterComment = async () => {
    onCommentAdded();
    if (viewingChild) {
      try {
        const updated = await crmService.getTicket(viewingChild.id);
        setViewingChild(updated);
      } catch { /* keep current data */ }
    }
  };

  const isCreatorOrAdmin = user?.role === "admin" || user?.id === displayTicket.solicitante_id;
  const isRetorno = displayTicket.status === "retorno";

  const handleAprovar = async () => {
    setProcessandoRetorno(true);
    try {
      await crmService.aprovarTicket(displayTicket.id, retornoComentario.trim());
      setRetornoComentario("");
      toast.success("Ticket aprovado e finalizado!");
      refreshAfterComment();
      onOpenChange(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao aprovar";
      toast.error(msg);
    } finally {
      setProcessandoRetorno(false);
    }
  };

  const handleRecusar = async () => {
    if (!retornoComentario.trim()) {
      toast.error("Informe o motivo da recusa");
      return;
    }
    setProcessandoRetorno(true);
    try {
      await crmService.recusarTicket(displayTicket.id, retornoComentario.trim());
      setRetornoComentario("");
      toast.success("Retorno recusado. Ticket voltou para Em Andamento.");
      refreshAfterComment();
      onOpenChange(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao recusar";
      toast.error(msg);
    } finally {
      setProcessandoRetorno(false);
    }
  };

  const handleAddComment = async () => {
    if (tipoInteracao === "finalizacao") {
      if (!resolucao) {
        toast.error("Selecione o tipo de resolução");
        return;
      }
      if (!descResolucao.trim()) {
        toast.error("Informe a descrição da resolução");
        return;
      }
      setFinalizando(true);
      try {
        if (comment.trim() || commentAnexos.length > 0) {
          await crmService.addComentario(
            displayTicket.id,
            comment.trim(),
            commentAnexos.length > 0 ? commentAnexos : undefined,
            "Resolvido"
          );
        }
        await crmService.finalizarTicket(displayTicket.id, {
          resolucao,
          descricao_resolucao: descResolucao.trim(),
        });
        setComment("");
        setCommentAnexos([]);
        setResolucao("");
        setDescResolucao("");
        setTipoInteracao("padrao");
        toast.success("Ticket finalizado com sucesso!");
        refreshAfterComment();
        onOpenChange(false);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("filho")) {
          toast.error(msg);
        } else {
          toast.error("Erro ao finalizar ticket");
        }
      } finally {
        setFinalizando(false);
      }
      return;
    }

    if (!comment.trim() && commentAnexos.length === 0) return;
    if (!statusAtual) {
      toast.error("Selecione a Área e o Motivo antes de enviar");
      return;
    }
    setSubmitting(true);
    try {
      await crmService.addComentario(
        displayTicket.id,
        comment.trim(),
        commentAnexos.length > 0 ? commentAnexos : undefined,
        statusAtual,
        dataNovaAnalise || undefined
      );
      setComment("");
      setCommentAnexos([]);
      setDataNovaAnalise("");
      setStatusAtual("");
      setStatusArea("");
      toast.success("Interação adicionada");
      refreshAfterComment();
    } catch {
      toast.error("Erro ao adicionar interação");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemoveAnexo = (index: number) => {
    setCommentAnexos((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAnexoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setCommentAnexos((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
    e.target.value = "";
  };



  const handleViewChild = async (child: CRMTicket) => {
    try {
      const full = await crmService.getTicket(child.id);
      setViewingChild(full);
      setComment("");
      setCommentAnexos([]);
      setStatusAtual("");
      setStatusArea("");
      setDataNovaAnalise("");
      setTipoInteracao("padrao");
    } catch {
      toast.error("Erro ao carregar sub-ticket");
    }
  };

  const openChildrenCount = ticket?.children?.filter(c => c.status !== "resolvido").length || 0;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!lightboxAnexo) onOpenChange(v); }}>
      <DialogContent
        className="max-w-[95vw] h-[92vh] flex flex-col overflow-hidden p-0 gap-0"
        onPointerDownOutside={(e) => { if (lightboxAnexo) e.preventDefault(); }}
        onInteractOutside={(e) => { if (lightboxAnexo) e.preventDefault(); }}
        onEscapeKeyDown={(e) => { if (lightboxAnexo) { e.preventDefault(); setLightboxAnexo(null); } }}
      >
        {/* Header */}
        <div className="shrink-0 border-b">
          {/* Top bar */}
          <div className="flex items-center justify-between px-5 py-3">
            <div className="flex items-center gap-2.5">
              <Badge
                variant={STATUS_CONFIG[displayTicket.status].badgeVariant}
                className="text-xs px-2.5 py-0.5"
              >
                {STATUS_CONFIG[displayTicket.status].title}
              </Badge>
              {viewingChild && (
                <Badge variant="outline" className="text-[10px] px-2 py-0.5 font-mono">
                  Filho #{viewingChild.id}
                </Badge>
              )}
              <div
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${sla.bg} ${sla.color}`}
              >
                <SlaIcon className="h-3 w-3" />
                {sla.label}
              </div>
            </div>

            {/* Center — Title */}
            <div className="absolute left-1/2 -translate-x-1/2 text-center pointer-events-none">
              <h2 className="text-base font-bold tracking-tight">{displayTicket.id_pedido}</h2>
              <p className="text-[11px] text-muted-foreground leading-tight">
                {displayTicket.nome_cliente} · {formatDate(displayTicket.created_at)}
                {displayTicket.id_processo && (
                  <> · <span className="font-mono font-medium text-foreground/70">ID {displayTicket.id_processo}</span></>
                )}
              </p>
            </div>

            <div className="flex items-center gap-1">
              {displayTicket.status !== "resolvido" && (
                <Select
                  value=""
                  onValueChange={async (tipo) => {
                    try {
                      await crmService.criarLembrete(displayTicket.id, tipo as "1h" | "2h" | "6h" | "amanha");
                      toast.success(
                        tipo === "amanha"
                          ? "Lembrete agendado para amanhã às 9h"
                          : `Lembrete agendado para ${tipo}`
                      );
                      // Recarregar lembretes
                      crmService.getLembretes(displayTicket.id)
                        .then((data) => setLembretes(Array.isArray(data) ? data.filter(l => !l.enviado) : []))
                        .catch(() => {});
                    } catch {
                      toast.error("Erro ao agendar lembrete");
                    }
                  }}
                >
                  <SelectTrigger className="h-8 w-auto min-w-[140px] text-xs gap-1">
                    <Bell className="h-3.5 w-3.5" />
                    <span>Lembre-me</span>
                    {lembretes.length > 0 && (
                      <span className="ml-1 bg-primary text-primary-foreground rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none">
                        {lembretes.length}
                      </span>
                    )}
                  </SelectTrigger>
                  <SelectContent>
                    {lembretes.length > 0 && (
                      <>
                        <div className="px-2 py-1.5 text-[11px] text-muted-foreground font-medium">
                          Lembretes pendentes:
                        </div>
                        {lembretes.map((l) => (
                          <div key={l.id} className="px-2 py-1 text-[11px] flex items-center gap-1.5 text-muted-foreground">
                            <Bell className="h-3 w-3 text-orange-500" />
                            {new Date(l.agendar_para).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                          </div>
                        ))}
                        <div className="my-1 border-t" />
                        <div className="px-2 py-1 text-[11px] text-muted-foreground font-medium">
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
              )}
              {displayTicket.status === "novo" && (
                <Button
                  size="sm"
                  variant="default"
                  className="h-8 text-xs gap-1.5"
                  onClick={() => onStatusChange(displayTicket.id, "em_andamento")}
                >
                  <ArrowRight className="h-3.5 w-3.5" />
                  Iniciar Atendimento
                </Button>
              )}
              {isCreatorOrAdmin && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  onClick={() => {
                    if (confirm("Tem certeza que deseja excluir este ticket?")) {
                      onDelete(displayTicket.id);
                    }
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>

          {/* Tabs — parent/children */}
          {(ticket.children?.length || 0) > 0 && (
            <div className="flex items-end gap-0 px-5 overflow-x-auto">
              <button
                onClick={() => { setViewingChild(null); setComment(""); setCommentAnexos([]); setStatusAtual(""); setStatusArea(""); setDataNovaAnalise(""); }}
                className={`relative px-4 py-2 text-xs font-medium transition-colors whitespace-nowrap border-b-2 ${
                  !viewingChild
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className="flex items-center gap-1.5">
                  <FileText className="h-3 w-3" />
                  Principal #{ticket.id}
                  {openChildrenCount > 0 && !viewingChild && (
                    <span className="ml-1 bg-amber-100 text-amber-700 text-[9px] px-1.5 py-0.5 rounded-full font-bold">
                      {openChildrenCount}
                    </span>
                  )}
                </span>
              </button>
              {ticket.children!.map((child) => {
                const isActive = viewingChild?.id === child.id;
                const childResolved = child.status === "resolvido";
                return (
                  <button
                    key={child.id}
                    onClick={() => handleViewChild(child)}
                    className={`relative px-4 py-2 text-xs font-medium transition-colors whitespace-nowrap border-b-2 ${
                      isActive
                        ? "border-primary text-primary"
                        : childResolved
                          ? "border-transparent text-emerald-600 hover:text-emerald-700"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <div className={`h-1.5 w-1.5 rounded-full ${
                        childResolved ? "bg-emerald-500" :
                        child.status === "em_andamento" ? "bg-blue-500" : "bg-gray-400"
                      }`} />
                      #{child.id} {child.motivo}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Body — two columns */}
        <div className="flex-1 overflow-hidden grid grid-cols-5 min-h-0">
          {/* ======== LEFT COLUMN — Interações (3/5) ======== */}
          <ScrollArea className="col-span-3 border-r h-full">
            <div className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold flex items-center gap-2 uppercase tracking-wide text-muted-foreground">
                  <MessageSquare className="h-3.5 w-3.5 text-primary" />
                  Interações ({displayTicket.comentarios.length})
                </h4>
              </div>

              {/* Interaction list — Timeline style */}
              {displayTicket.comentarios.length > 0 ? (
                <div className="relative space-y-0">
                  {/* Timeline line */}
                  <div className="absolute left-[15px] top-6 bottom-6 w-px bg-border" />

                  {displayTicket.comentarios.map((c, idx) => {
                    // Skip Aprovado/Recusado — they render as thread inside the Aguardando Aprovação bubble
                    if (c.status_detalhe === "Aprovado" || c.status_detalhe === "Recusado") return null;

                    // Find threaded replies (Aprovado/Recusado that follow this comment)
                    const threadReplies = c.status_detalhe === "Aguardando Aprovação"
                      ? displayTicket.comentarios.filter(
                          (r) => (r.status_detalhe === "Aprovado" || r.status_detalhe === "Recusado")
                            && new Date(r.created_at) >= new Date(c.created_at)
                        )
                      : [];

                    return (
                    <div key={c.id} className={`relative flex gap-3 ${idx > 0 ? "pt-4" : ""}`}>
                      {/* Avatar on timeline */}
                      <div className="relative z-10 shrink-0">
                        <div className={`h-8 w-8 rounded-full flex items-center justify-center text-[10px] font-bold ring-2 ring-background ${
                          c.status_detalhe === "Resolvido"
                            ? "bg-emerald-100 text-emerald-700"
                            : c.status_detalhe?.startsWith("Aguardando")
                              ? "bg-amber-100 text-amber-700"
                              : c.status_detalhe?.startsWith("Pendente")
                                ? "bg-orange-100 text-orange-700"
                                : "bg-primary/10 text-primary"
                        }`}>
                          {c.usuario_nome.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                        </div>
                      </div>

                      {/* Bubble */}
                      <div className="flex-1 min-w-0">
                        <div className="rounded-xl bg-card border shadow-sm overflow-hidden">
                          {/* Bubble header */}
                          <div className="flex items-center justify-between px-3.5 py-2 bg-muted/40 border-b">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-xs font-semibold truncate">{c.usuario_nome}</span>
                              {c.status_detalhe && (
                                <Badge variant="outline" className={`text-[10px] px-1.5 py-0 shrink-0 ${
                                  c.status_detalhe === "Resolvido" ? "border-emerald-300 text-emerald-700 bg-emerald-50" :
                                  c.status_detalhe?.startsWith("Aguardando") ? "border-amber-300 text-amber-700 bg-amber-50" :
                                  c.status_detalhe === "Em Andamento" || c.status_detalhe === "Em Análise" ? "border-blue-300 text-blue-700 bg-blue-50" :
                                  c.status_detalhe?.startsWith("Pendente") ? "border-orange-300 text-orange-700 bg-orange-50" :
                                  "border-slate-300 text-slate-600 bg-slate-50"
                                }`}>
                                  → {c.status_detalhe}
                                </Badge>
                              )}
                              {c.data_nova_analise && (
                                <Badge variant="outline" className="text-[10px] px-1.5 py-0 shrink-0 border-blue-300 text-blue-700 bg-blue-50 gap-0.5">
                                  <CalendarClock className="h-2.5 w-2.5" />
                                  Próx. análise: {new Date(c.data_nova_analise + "T00:00:00").toLocaleDateString("pt-BR")}
                                </Badge>
                              )}
                            </div>
                            <span className="text-[10px] text-muted-foreground shrink-0 ml-2">
                              {formatDateTime(c.created_at)}
                            </span>
                          </div>
                          {/* Bubble body */}
                          <div className="px-3.5 py-2.5">
                            {c.texto && (
                              <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
                                {c.texto}
                              </p>
                            )}
                            {c.anexos && c.anexos.length > 0 && (
                              <div className={`flex flex-wrap gap-2 ${c.texto ? "mt-2.5" : ""}`}>
                                {c.anexos.map((a, i) => (
                                  <AttachmentPreview
                                    key={i}
                                    anexo={a}
                                    onPreview={setLightboxAnexo}
                                  />
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Threaded replies (Aprovado/Recusado) */}
                          {threadReplies.map((reply) => (
                            <div key={reply.id} className={`border-t ${
                              reply.status_detalhe === "Aprovado"
                                ? "border-emerald-200 bg-emerald-50/50"
                                : "border-red-200 bg-red-50/50"
                            } px-3.5 py-2.5`}>
                              <div className="flex items-center justify-between mb-1.5">
                                <div className="flex items-center gap-2">
                                  <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[8px] font-bold ${
                                    reply.status_detalhe === "Aprovado"
                                      ? "bg-emerald-100 text-emerald-700"
                                      : "bg-red-100 text-red-700"
                                  }`}>
                                    {reply.usuario_nome.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                                  </div>
                                  <span className="text-xs font-semibold">{reply.usuario_nome}</span>
                                  <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${
                                    reply.status_detalhe === "Aprovado"
                                      ? "border-emerald-300 text-emerald-700 bg-emerald-100"
                                      : "border-red-300 text-red-700 bg-red-100"
                                  }`}>
                                    → {reply.status_detalhe}
                                  </Badge>
                                </div>
                                <span className="text-[10px] text-muted-foreground">{formatDateTime(reply.created_at)}</span>
                              </div>
                              {reply.texto && (
                                <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap ml-7">
                                  {reply.texto}
                                </p>
                              )}
                            </div>
                          ))}

                          {/* Thread: approve/reject inside finalization comment */}
                          {c.status_detalhe === "Aguardando Aprovação" && isRetorno && isCreatorOrAdmin && threadReplies.length === 0 && (
                            <div className="border-t border-purple-200 bg-purple-50/50 p-3.5 space-y-3">
                              <div className="flex items-center gap-2">
                                <Clock className="h-3.5 w-3.5 text-purple-600" />
                                <span className="text-xs font-semibold text-purple-800">Aprovar ou recusar esta finalização</span>
                              </div>
                              <Textarea
                                placeholder="Comentário (obrigatório para recusar)..."
                                value={retornoComentario}
                                onChange={(e) => setRetornoComentario(e.target.value)}
                                rows={2}
                                className="bg-white text-sm border-purple-200"
                              />
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                                  onClick={handleAprovar}
                                  disabled={processandoRetorno}
                                >
                                  {processandoRetorno ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1" />}
                                  Aprovar
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  className="flex-1"
                                  onClick={handleRecusar}
                                  disabled={processandoRetorno || !retornoComentario.trim()}
                                >
                                  {processandoRetorno ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <X className="h-3.5 w-3.5 mr-1" />}
                                  Recusar
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                    <MessageSquare className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <p className="text-sm text-muted-foreground">Nenhuma interação ainda</p>
                </div>
              )}

              {/* New Interaction - hidden for analysts when ticket is in retorno */}
              {!(isRetorno && !isCreatorOrAdmin) && (
              <div className="rounded-lg border bg-muted/20 p-3 space-y-3">
                {/* Interaction type toggle */}
                <div className="flex items-center gap-1 p-0.5 rounded-md bg-muted/50 w-fit">
                  <button
                    onClick={() => setTipoInteracao("padrao")}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      tipoInteracao === "padrao"
                        ? "bg-background shadow-sm text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <MessageSquare className="h-3 w-3 inline mr-1.5" />
                    Interação
                  </button>
                  {displayTicket.status !== "resolvido" && displayTicket.status !== "retorno" && (
                    <button
                      onClick={() => setTipoInteracao("finalizacao")}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoInteracao === "finalizacao"
                          ? "bg-emerald-100 shadow-sm text-emerald-800"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <CheckCircle2 className="h-3 w-3 inline mr-1.5" />
                      Finalização
                    </button>
                  )}
                </div>

                {/* Finalization fields */}
                {tipoInteracao === "finalizacao" && (
                  <div className="rounded-md border border-emerald-200 bg-emerald-50/30 p-3 space-y-2">
                    <div className="space-y-1.5">
                      <Label className="text-xs font-medium">Tipo de Resolução *</Label>
                      <Select value={resolucao} onValueChange={setResolucao}>
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Selecione a resolução" />
                        </SelectTrigger>
                        <SelectContent>
                          {(dynamicResolucoes.length > 0 ? dynamicResolucoes : CRM_RESOLUCOES as unknown as string[]).map((r) => (
                            <SelectItem key={r} value={r}>
                              {r}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs font-medium">Descrição da Resolução *</Label>
                      <Textarea
                        placeholder="Descreva como o caso foi resolvido..."
                        rows={2}
                        className="text-xs bg-background"
                        value={descResolucao}
                        onChange={(e) => setDescResolucao(e.target.value)}
                      />
                    </div>
                  </div>
                )}

                <Textarea
                  placeholder={tipoInteracao === "finalizacao" ? "Comentário adicional (opcional)..." : "Escreva uma interação..."}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={3}
                  className="bg-background"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey))
                      handleAddComment();
                  }}
                />

                {commentAnexos.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {commentAnexos.map((file, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-1.5 px-2 py-1 rounded-md border bg-background text-xs"
                      >
                        <Paperclip className="h-3 w-3 text-muted-foreground" />
                        <span className="truncate max-w-[120px]">
                          {file.name}
                        </span>
                        <button
                          onClick={() => handleRemoveAnexo(i)}
                          className="text-muted-foreground hover:text-red-500 ml-1"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0">
                      <Paperclip className="h-4 w-4" />
                      <span>Anexar</span>
                      <input
                        type="file"
                        multiple
                        className="hidden"
                        onChange={handleAnexoChange}
                      />
                    </label>
                    {tipoInteracao === "padrao" && (() => {
                      const selectedAreaObj = areasMap.find((am) => am.nome === statusArea);
                      const motivosFiltrados = selectedAreaObj
                        ? motivosList.filter((m) => m.area_id === selectedAreaObj.id)
                        : [];
                      return (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="text-xs text-muted-foreground font-medium">Status atual:</span>
                          <Select
                            value={statusArea}
                            onValueChange={(v) => { setStatusArea(v); setStatusAtual(""); }}
                          >
                            <SelectTrigger
                              className={`h-7 text-xs w-[150px] ${!statusArea ? "border-red-300 ring-1 ring-red-100" : ""}`}
                            >
                              <SelectValue placeholder="Área *" />
                            </SelectTrigger>
                            <SelectContent>
                              {areasMap.map((a) => (
                                <SelectItem key={a.id} value={a.nome}>
                                  {a.nome}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Select
                            value={statusAtual}
                            onValueChange={setStatusAtual}
                            disabled={!statusArea || motivosFiltrados.length === 0}
                          >
                            <SelectTrigger
                              className={`h-7 text-xs w-[170px] ${!statusAtual ? "border-red-300 ring-1 ring-red-100" : ""}`}
                            >
                              <SelectValue placeholder={!statusArea ? "Área primeiro" : motivosFiltrados.length === 0 ? "Sem motivos" : "Motivo *"} />
                            </SelectTrigger>
                            <SelectContent>
                              {motivosFiltrados.map((m) => (
                                <SelectItem key={m.nome} value={m.nome}>
                                  {m.nome}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      );
                    })()}
                    {tipoInteracao === "padrao" && (
                      <div className="flex items-center gap-1.5 shrink-0">
                        <CalendarClock className="h-3.5 w-3.5 text-muted-foreground" />
                        <input
                          type="date"
                          value={dataNovaAnalise}
                          onChange={(e) => setDataNovaAnalise(e.target.value)}
                          min={new Date(Date.now() + 86400000).toISOString().split("T")[0]}
                          className="h-7 text-xs border rounded-md px-2 bg-background w-[130px]"
                          title="Próxima análise (opcional — se vazio, cobra amanhã)"
                        />
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <p className="text-[11px] text-muted-foreground">
                      Ctrl+Enter
                    </p>
                    {tipoInteracao === "padrao" ? (
                      <Button
                        size="sm"
                        onClick={handleAddComment}
                        disabled={
                          submitting ||
                          (!comment.trim() && commentAnexos.length === 0) ||
                          !statusAtual
                        }
                      >
                        {submitting ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        className="bg-emerald-600 hover:bg-emerald-700"
                        onClick={handleAddComment}
                        disabled={
                          finalizando || !resolucao || !descResolucao.trim()
                        }
                      >
                        {finalizando ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <>
                            <CheckCircle2 className="h-4 w-4 mr-1" />
                            Finalizar
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
              )}
            </div>
          </ScrollArea>

          {/* ======== RIGHT COLUMN — Informações (2/5) ======== */}
          <ScrollArea className="col-span-2 h-full bg-muted/10">
            <div className="p-4 space-y-3">
              {/* Status + Countdown Card */}
              <div className={`rounded-xl p-4 ${
                displayTicket.status === "resolvido"
                  ? "bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900"
                  : "bg-card border shadow-sm"
              }`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Status Atual</p>
                    <div className="flex items-center gap-2">
                      <div className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                        displayTicket.status_detalhe === "Resolvido" ? "bg-emerald-500" :
                        displayTicket.status_detalhe?.startsWith("Aguardando") ? "bg-amber-500 animate-pulse" :
                        displayTicket.status_detalhe === "Em Andamento" || displayTicket.status_detalhe === "Em Análise" ? "bg-blue-500" :
                        displayTicket.status_detalhe?.startsWith("Pendente") ? "bg-orange-500" :
                        "bg-gray-400"
                      }`} />
                      <span className="text-sm font-bold">
                        {displayTicket.area || "—"}
                        {displayTicket.motivo && (
                          <>
                            <span className="text-muted-foreground font-normal mx-1.5">|</span>
                            {displayTicket.motivo}
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                  {/* Countdown */}
                  {(() => {
                    const deadline = new Date(displayTicket.prazo + "T23:59:59");
                    const diffMs = deadline.getTime() - now.getTime();
                    const isOverdue = diffMs < 0;
                    const absDiffMs = Math.abs(diffMs);
                    const days = Math.floor(absDiffMs / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((absDiffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((absDiffMs % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((absDiffMs % (1000 * 60)) / 1000);
                    const isResolved = displayTicket.status === "resolvido";
                    return (
                      <div className="text-right shrink-0">
                        {isResolved ? (
                          <div className="flex items-center gap-1.5 text-emerald-600">
                            <CheckCircle2 className="h-4 w-4" />
                            <span className="text-sm font-bold">Concluído</span>
                          </div>
                        ) : (
                          <div className={isOverdue ? "text-red-600" : days <= 1 ? "text-amber-600" : "text-foreground"}>
                            <div className="flex items-baseline gap-px justify-end font-mono leading-none">
                              <span className="text-lg font-black tabular-nums">{String(days).padStart(2, "0")}</span>
                              <span className="text-[8px] font-bold opacity-60">d</span>
                              <span className="text-lg font-black tabular-nums ml-0.5">{String(hours).padStart(2, "0")}</span>
                              <span className="text-[8px] font-bold opacity-60">h</span>
                              <span className="text-lg font-black tabular-nums ml-0.5">{String(minutes).padStart(2, "0")}</span>
                              <span className="text-[8px] font-bold opacity-60">m</span>
                              <span className="text-lg font-black tabular-nums ml-0.5">{String(seconds).padStart(2, "0")}</span>
                              <span className="text-[8px] font-bold opacity-60">s</span>
                            </div>
                            <p className="text-[9px] font-bold uppercase tracking-wider mt-0.5">
                              {isOverdue ? "ATRASADO" : "restantes"}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>

              {/* Informações do Cliente */}
              <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <div className="flex items-center gap-2 px-3.5 py-2 bg-muted/40 border-b">
                  <User className="h-3.5 w-3.5 text-primary" />
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Cliente</span>
                </div>
                <div className="p-3.5 space-y-2.5">
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                    <div className="min-w-0">
                      <p className="text-[10px] text-muted-foreground">Nome</p>
                      <p className="text-xs font-semibold truncate">{displayTicket.nome_cliente}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="text-[10px] text-muted-foreground">ID Pedido</p>
                      <p className="text-xs font-mono font-semibold">{displayTicket.id_pedido}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      <span>{formatTelefone(displayTicket.telefone)}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Mail className="h-3 w-3" />
                      <span className="truncate">{displayTicket.email}</span>
                    </div>
                  </div>
                  {displayTicket.anexo_nome && (
                    <button
                      onClick={() => setLightboxAnexo({
                        nome: displayTicket.anexo_nome || "",
                        url: displayTicket.anexo_url,
                        tipo: displayTicket.anexo_nome?.match(/\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i) ? "image/png" :
                              displayTicket.anexo_nome?.endsWith(".pdf") ? "application/pdf" : "",
                      })}
                      className="flex items-center gap-1.5 text-xs text-primary hover:underline"
                    >
                      <Paperclip className="h-3 w-3" />
                      {displayTicket.anexo_nome}
                      <Eye className="h-3 w-3 opacity-50" />
                    </button>
                  )}
                </div>
              </div>

              {/* Dados do Pedido (from bot) */}
              {loadingBot ? (
                <div className="flex items-center justify-center gap-2 py-6 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-xs">Carregando dados do pedido...</span>
                </div>
              ) : (
                clienteData && (
                  <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                    <div className="flex items-center gap-2 px-3.5 py-2 bg-muted/40 border-b">
                      <FileText className="h-3.5 w-3.5 text-primary" />
                      <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Dados do Pedido</span>
                    </div>
                    <div className="p-3.5 space-y-2.5">
                      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                        {clienteData.cpf_cnpj_cliente && (
                          <div>
                            <p className="text-[10px] text-muted-foreground">CPF/CNPJ</p>
                            <p className="text-xs font-mono font-semibold">{clienteData.cpf_cnpj_cliente}</p>
                          </div>
                        )}
                        {clienteData.data_emissao && (
                          <div>
                            <p className="text-[10px] text-muted-foreground">Emissão</p>
                            <p className="text-xs font-semibold">{formatDate(clienteData.data_emissao)}</p>
                          </div>
                        )}
                        {clienteData.uf_nf && (
                          <div className="min-w-0">
                            <p className="text-[10px] text-muted-foreground">UF / Cidade</p>
                            <p className="text-xs font-semibold truncate">
                              {clienteData.cidade_nf ? `${clienteData.cidade_nf} - ${clienteData.uf_nf}` : clienteData.uf_nf}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="h-px bg-border" />

                      <div className="grid grid-cols-3 gap-1.5">
                        <div>
                          <p className="text-[10px] text-muted-foreground">Fil. Saída</p>
                          <p className="text-xs font-semibold">{clienteData.filial_saida || "—"}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted-foreground">Fil. Venda</p>
                          <p className="text-xs font-semibold">{clienteData.filial_venda || "—"}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted-foreground">Entrega</p>
                          <p className="text-xs font-semibold">{clienteData.deseja_entrega || "—"}</p>
                        </div>
                      </div>

                      {/* Products */}
                      {produtosData.length > 0 && (
                        <>
                          <div className="h-px bg-border" />
                          <div>
                            <p className="text-[10px] text-muted-foreground mb-1.5">Produto(s)</p>
                            <div className="space-y-1">
                              {produtosData.map((p, i) => {
                                const isSelected = displayTicket.produto && String(p.produto) === String(displayTicket.produto);
                                return (
                                <div key={i} className={`rounded-lg border px-2.5 py-1.5 ${isSelected ? "bg-primary/10 border-primary ring-1 ring-primary/30" : "bg-muted/30"}`}>
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <span className="font-mono text-[10px] text-muted-foreground shrink-0">{p.produto}</span>
                                    <span className={`text-xs font-medium truncate ${isSelected ? "text-primary" : ""}`}>{p.nome_produto}</span>
                                    {isSelected && (
                                      <Badge variant="default" className="text-[8px] px-1 py-0 h-3.5 ml-auto shrink-0">Selecionado</Badge>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-1.5 mt-1">
                                    {p.numero_nf && (
                                      <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4">NF {p.numero_nf}</Badge>
                                    )}
                                    {p.situacao_nota && (
                                      <span className={`rounded-full px-2 py-0 text-[9px] font-bold ${
                                        /emitida|faturado/i.test(p.situacao_nota)
                                          ? "bg-emerald-100 text-emerald-700"
                                          : /cancelada/i.test(p.situacao_nota)
                                            ? "bg-red-100 text-red-700"
                                            : "bg-slate-100 text-slate-700"
                                      }`}>
                                        {p.situacao_nota}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                );
                              })}
                            </div>
                          </div>
                        </>
                      )}

                      {/* Dates */}
                      {(clienteData.data_previsao_entrega || clienteData.data_entrega_efetiva) && (
                        <>
                          <div className="h-px bg-border" />
                          <div className="grid grid-cols-2 gap-x-3">
                            {clienteData.data_previsao_entrega && (
                              <div>
                                <p className="text-[10px] text-muted-foreground">Prev. Entrega</p>
                                <p className="text-xs font-semibold">{formatDate(clienteData.data_previsao_entrega)}</p>
                              </div>
                            )}
                            {clienteData.data_entrega_efetiva && (
                              <div>
                                <p className="text-[10px] text-muted-foreground">Entrega Efetiva</p>
                                <p className="text-xs font-semibold text-emerald-600">{formatDate(clienteData.data_entrega_efetiva)}</p>
                              </div>
                            )}
                          </div>
                        </>
                      )}

                      {/* Tipo Operação + Timeline */}
                      <div className="h-px bg-border" />
                      <div className="grid grid-cols-2 gap-x-3">
                        <div className="min-w-0">
                          <p className="text-[10px] text-muted-foreground">Tipo Operação</p>
                          <p className={`text-xs font-bold ${
                            clienteData.tipo_operacao_venda && /futura/i.test(clienteData.tipo_operacao_venda) ? "text-red-600" : ""
                          }`}>
                            {clienteData.tipo_operacao_venda || "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted-foreground">Timeline</p>
                          {clienteData.situacao_timeline ? (
                            <Badge variant="secondary" className="text-[10px] h-4 px-1.5">{clienteData.situacao_timeline}</Badge>
                          ) : (
                            <p className="text-xs">—</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              )}

              {/* Serviços */}
              {(montagemData.length > 0 || nmresolveData.length > 0) && (
                <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                  <div className="flex items-center gap-2 px-3.5 py-2 bg-muted/40 border-b">
                    <Wrench className="h-3.5 w-3.5 text-primary" />
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Serviços</span>
                  </div>
                  <div className="p-3.5 space-y-3">
                    {montagemData.length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5">Montagem</p>
                        <div className="space-y-2">
                          {montagemData.map((m, i) => (
                            <div key={i} className={`grid grid-cols-2 gap-x-3 gap-y-1.5 ${i > 0 ? "border-t pt-2" : ""}`}>
                              <div>
                                <p className="text-[10px] text-muted-foreground">Produto</p>
                                <p className="text-xs font-semibold">{m.produto || "—"}</p>
                              </div>
                              <div>
                                <p className="text-[10px] text-muted-foreground">ID Boletim</p>
                                <p className="text-xs font-mono font-semibold">{m.identificador_boletim_montagem || "—"}</p>
                              </div>
                              <div>
                                <p className="text-[10px] text-muted-foreground">Situação</p>
                                <Badge variant="secondary" className="text-[10px] h-4 px-1.5">{m.situacao_boletim || "—"}</Badge>
                              </div>
                              <div>
                                <p className="text-[10px] text-muted-foreground">Previsão</p>
                                <p className="text-xs font-semibold">{m.data_previsao_montagem ? formatDate(m.data_previsao_montagem) : "—"}</p>
                              </div>
                              {m.data_montagem && (
                                <div>
                                  <p className="text-[10px] text-muted-foreground">Data Montagem</p>
                                  <p className="text-xs font-semibold text-emerald-600">{formatDate(m.data_montagem)}</p>
                                </div>
                              )}
                              <div>
                                <p className="text-[10px] text-muted-foreground">Montador</p>
                                <p className="text-xs font-semibold">{m.nome_montador || "—"}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {nmresolveData.length > 0 && (
                      <div>
                        {montagemData.length > 0 && <div className="h-px bg-border mb-2" />}
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5">NM Resolve</p>
                        <div className="space-y-2">
                          {nmresolveData.map((n, i) => (
                            <div key={i} className={`grid grid-cols-2 gap-x-3 gap-y-1.5 ${i > 0 ? "border-t pt-2" : ""}`}>
                              <div>
                                <p className="text-[10px] text-muted-foreground">Modalidade</p>
                                <p className="text-xs font-semibold">{n.modalidade || "—"}</p>
                              </div>
                              <div>
                                <p className="text-[10px] text-muted-foreground">Sit. Serviço</p>
                                <Badge variant="secondary" className="text-[10px] h-4 px-1.5">{n.situacao_servico || "—"}</Badge>
                              </div>
                              <div>
                                <p className="text-[10px] text-muted-foreground">Sit. Boletim</p>
                                <Badge variant="outline" className="text-[10px] h-4 px-1.5">{n.situacao_boletim || "—"}</Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Informações do Caso */}
              <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <div className="flex items-center gap-2 px-3.5 py-2 bg-muted/40 border-b">
                  <FileText className="h-3.5 w-3.5 text-primary" />
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Caso</span>
                </div>
                <div className="p-3.5 space-y-2.5">
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                    <div>
                      <p className="text-[10px] text-muted-foreground">Área</p>
                      <Badge variant="outline" className="text-[10px] h-5 px-2 font-semibold">{displayTicket.area}</Badge>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Prazo</p>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-muted-foreground" />
                        <p className="text-xs font-semibold">{formatDate(displayTicket.prazo)}</p>
                      </div>
                    </div>
                    {displayTicket.motivo && (
                      <div className="col-span-2">
                        <p className="text-[10px] text-muted-foreground">Motivo</p>
                        <p className="text-xs font-semibold">{displayTicket.motivo}</p>
                      </div>
                    )}
                  </div>

                  {/* Necessita Análise / Próxima análise */}
                  {displayTicket.status !== "resolvido" && (
                    <div className={`flex items-center gap-2 rounded-lg px-3 py-2 ${
                      displayTicket.necessita_analise
                        ? "bg-orange-50 border border-orange-200"
                        : displayTicket.data_nova_analise
                        ? "bg-blue-50 border border-blue-200"
                        : "bg-muted/30 border"
                    }`}>
                      {displayTicket.necessita_analise ? (
                        <>
                          <Bell className="h-3.5 w-3.5 text-orange-600 animate-pulse" />
                          <span className="text-xs font-semibold text-orange-700">Necessita análise hoje</span>
                        </>
                      ) : displayTicket.data_nova_analise ? (
                        <>
                          <CalendarClock className="h-3.5 w-3.5 text-blue-600" />
                          <span className="text-xs font-semibold text-blue-700">
                            Próxima análise: {new Date(displayTicket.data_nova_analise + "T00:00:00").toLocaleDateString("pt-BR")}
                          </span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                          <span className="text-xs font-semibold text-emerald-700">Analisado hoje</span>
                        </>
                      )}
                    </div>
                  )}

                  <div>
                    <p className="text-[10px] text-muted-foreground mb-0.5">Descrição</p>
                    <p className="text-xs leading-relaxed">{displayTicket.descricao}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                    {displayTicket.glpi && (
                      <div>
                        <p className="text-[10px] text-muted-foreground">GLPI</p>
                        <p className="text-xs font-mono font-semibold">{displayTicket.glpi}</p>
                      </div>
                    )}
                    {displayTicket.id_processo && (
                      <div>
                        <p className="text-[10px] text-muted-foreground">ID Processo</p>
                        <p className="text-xs font-mono font-semibold">{displayTicket.id_processo}</p>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
                    {displayTicket.plataforma && (
                      <div>
                        <p className="text-[10px] text-muted-foreground">Plataforma</p>
                        <div className="flex items-center gap-1">
                          <Building2 className="h-3 w-3 text-muted-foreground" />
                          <p className="text-xs font-semibold">{displayTicket.plataforma}</p>
                        </div>
                      </div>
                    )}
                    {displayTicket.credenciada && (
                      <div>
                        <p className="text-[10px] text-muted-foreground">Credenciada</p>
                        <p className="text-xs font-semibold">{displayTicket.credenciada}</p>
                      </div>
                    )}
                  </div>

                  <div className="h-px bg-border" />

                  <div className="grid grid-cols-2 gap-x-3">
                    <div>
                      <p className="text-[10px] text-muted-foreground">Solicitante</p>
                      <p className="text-xs font-semibold">{displayTicket.solicitante_nome}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Analista</p>
                      {isCreatorOrAdmin && analistas.length > 0 ? (
                        <Select
                          value={String(displayTicket.analista_id || "")}
                          onValueChange={async (val) => {
                            const a = analistas.find((x) => String(x.id) === val);
                            if (!a || !displayTicket) return;
                            try {
                              await crmService.reatribuir(displayTicket.id, a.id, a.nome);
                              toast.success(`Analista alterado para ${a.nome}`);
                              onCommentAdded();
                            } catch {
                              toast.error("Erro ao alterar analista");
                            }
                          }}
                        >
                          <SelectTrigger className="h-7 text-xs w-full mt-0.5">
                            <UserCheck className="h-3 w-3 text-muted-foreground mr-1" />
                            <SelectValue placeholder="Selecionar analista" />
                          </SelectTrigger>
                          <SelectContent>
                            {analistas.map((a) => (
                              <SelectItem key={a.id} value={String(a.id)}>{a.nome}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <div className="flex items-center gap-1">
                          <UserCheck className="h-3 w-3 text-muted-foreground" />
                          <p className="text-xs font-semibold">{displayTicket.analista_nome || "Não atribuído"}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Resolução */}
              {(displayTicket.status === "resolvido" || displayTicket.status === "retorno") && displayTicket.resolucao && (
                <div className="rounded-xl border border-emerald-200 dark:border-emerald-900 bg-emerald-50/50 dark:bg-emerald-950/20 overflow-hidden shadow-sm">
                  <div className="flex items-center gap-2 px-3.5 py-2 bg-emerald-100/50 dark:bg-emerald-900/30 border-b border-emerald-200 dark:border-emerald-900">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">Resolução</span>
                  </div>
                  <div className="p-3.5 space-y-2">
                    <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300 text-[10px] h-5 px-2 font-bold">
                      {displayTicket.resolucao}
                    </Badge>
                    {displayTicket.descricao_resolucao && (
                      <p className="text-xs leading-relaxed text-emerald-900 dark:text-emerald-200">{displayTicket.descricao_resolucao}</p>
                    )}
                  </div>
                </div>
              )}

            </div>
          </ScrollArea>
        </div>
        {lightboxAnexo && (
          <LightboxPreview anexo={lightboxAnexo} onClose={() => setLightboxAnexo(null)} />
        )}
      </DialogContent>
    </Dialog>
  );
}

// ============================================================
// Main CRM Page
// ============================================================

export default function CRM() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<CRMTicket[]>([]);
  const [stats, setStats] = useState<CRMStats>({ total: 0, novos: 0, em_andamento: 0, retorno: 0, resolvidos: 0, atrasados: 0, necessita_analise: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterMotivo, setFilterMotivo] = useState<string>("all");
  const [filterArea, setFilterArea] = useState<string>("all");
  const [filterAnalista, setFilterAnalista] = useState<string>("all");
  const [analistas, setAnalistas] = useState<{ id: number; nome: string }[]>([]);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<Record<string, string | null>>({});

  // Dialog / Sheet state
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<CRMTicket | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Dynamic parameters
  const [dynamicAreas, setDynamicAreas] = useState<string[]>([]);
  const [dynamicAreasMap, setDynamicAreasMap] = useState<{id: number; nome: string}[]>([]);
  const [dynamicMotivos, setDynamicMotivos] = useState<{nome: string; area_id: number | null}[]>([]);
  const [dynamicStatus, setDynamicStatus] = useState<string[]>([]);
  const [dynamicResolucoes, setDynamicResolucoes] = useState<string[]>([]);
  const [dynamicPlataformas, setDynamicPlataformas] = useState<string[]>([]);
  const [dynamicCredenciadas, setDynamicCredenciadas] = useState<string[]>([]);

  // Drafts
  const [drafts, setDrafts] = useState<CRMDraft[]>(getDrafts());
  const [activeDraft, setActiveDraft] = useState<CRMDraft | null>(null);

  const refreshDrafts = () => setDrafts(getDrafts());

  const handleOpenNewTicket = () => {
    setActiveDraft(null);
    setNewDialogOpen(true);
  };

  const handleOpenDraft = (draft: CRMDraft) => {
    setActiveDraft(draft);
    setNewDialogOpen(true);
  };

  const handleDeleteDraft = (id: string) => {
    removeDraft(id);
    refreshDrafts();
    toast.success("Rascunho excluído");
  };

  // DnD state
  const [activeTicket, setActiveTicket] = useState<CRMTicket | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  // Load data
  const loadData = useCallback(async () => {
    try {
      const [ticketsData, statsData, analistasData, atualizacaoData] = await Promise.all([
        crmService.getTickets(),
        crmService.getStats(),
        crmService.getAnalistas(),
        crmService.buscarUltimaAtualizacao(),
      ]);
      setTickets(ticketsData);
      setStats(statsData);
      setAnalistas(analistasData);
      setUltimaAtualizacao(atualizacaoData);
    } catch (err) {
      toast.error("Erro ao carregar dados do CRM");
    } finally {
      setLoading(false);
    }
  }, []);

  // Load parametros (areas + motivos + status + resolucoes)
  const loadParametros = useCallback(async () => {
    try {
      const [a, m, s, r, p, c] = await Promise.all([crmService.getAreas(), crmService.getMotivos(), crmService.getStatusDetalhe(), crmService.getResolucoes(), crmService.getPlataformas(), crmService.getCredenciadas()]);
      setDynamicAreas(a.filter((x) => x.ativo).map((x) => x.nome));
      setDynamicAreasMap(a.filter((x) => x.ativo).map((x) => ({ id: x.id, nome: x.nome })));
      setDynamicMotivos(m.filter((x) => x.ativo).map((x) => ({ nome: x.nome, area_id: x.area_id })));
      setDynamicStatus(s.filter((x) => x.ativo).map((x) => x.nome));
      setDynamicResolucoes(r.filter((x) => x.ativo).map((x) => x.nome));
      setDynamicPlataformas(p.filter((x) => x.ativo).map((x) => x.nome));
      setDynamicCredenciadas(c.filter((x) => x.ativo).map((x) => x.nome));
    } catch {
      // fallback to hardcoded
      setDynamicAreas([...CRM_AREAS]);
      setDynamicStatus([...CRM_STATUS_DETALHE]);
      setDynamicResolucoes([...CRM_RESOLUCOES]);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadParametros();
  }, [loadData, loadParametros]);

  // Filter tickets
  const filteredTickets = tickets.filter((t) => {
    if (search) {
      const s = search.toLowerCase();
      if (
        !t.id_pedido.toLowerCase().includes(s) &&
        !t.nome_cliente.toLowerCase().includes(s) &&
        !(t.area || "").toLowerCase().includes(s) &&
        !(t.motivo || "").toLowerCase().includes(s)
      )
        return false;
    }
    if (filterArea !== "all" && t.area !== filterArea) return false;
    if (filterMotivo !== "all" && t.motivo !== filterMotivo) return false;
    if (filterAnalista !== "all" && String(t.analista_id) !== filterAnalista) return false;
    return true;
  });

  const ticketsByStatus = (status: CRMTicketStatus) =>
    filteredTickets.filter((t) => t.status === status);

  // DnD handlers
  const handleDragStart = (event: DragStartEvent) => {
    const ticket = event.active.data.current?.ticket as CRMTicket;
    setActiveTicket(ticket || null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveTicket(null);
    const { active, over } = event;
    if (!over) return;

    const ticket = active.data.current?.ticket as CRMTicket;
    if (!ticket) return;

    // Extract target status from column id
    const targetColumnId = over.id as string;
    const targetStatus = targetColumnId.replace("column-", "") as CRMTicketStatus;

    if (ticket.status === targetStatus) return;

    // Optimistic update
    setTickets((prev) =>
      prev.map((t) =>
        t.id === ticket.id ? { ...t, status: targetStatus, updated_at: new Date().toISOString() } : t
      )
    );

    try {
      await crmService.updateStatus(ticket.id, targetStatus);
      const newStats = await crmService.getStats();
      setStats(newStats);

      const label = STATUS_CONFIG[targetStatus].title;
      toast.success(`Ticket movido para "${label}"`);
    } catch {
      // Revert
      setTickets((prev) =>
        prev.map((t) =>
          t.id === ticket.id ? { ...t, status: ticket.status } : t
        )
      );
      toast.error("Erro ao mover ticket");
    }
  };

  const handleStatusChange = async (id: number, status: CRMTicketStatus) => {
    try {
      await crmService.updateStatus(id, status);
      await loadData();
      // Reload ticket detail
      const updated = await crmService.getTicket(id);
      setSelectedTicket(updated);
      toast.success(`Ticket movido para "${STATUS_CONFIG[status].title}"`);
    } catch {
      toast.error("Erro ao alterar status");
    }
  };

  const handleTicketClick = async (ticket: CRMTicket) => {
    setSelectedTicket(ticket);
    setDetailOpen(true);
    // Fetch full ticket with children
    try {
      const full = await crmService.getTicket(ticket.id);
      setSelectedTicket(full);
    } catch {
      // keep the partial ticket if fetch fails
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">CRM</h1>
          <p className="text-muted-foreground">Gestão de atendimento ao cliente</p>
          {Object.keys(ultimaAtualizacao).length > 0 && (() => {
            const labels: Record<string, string> = { bot_vendas: "Vendas", bot_montagem: "Montagem", bot_nmresolve: "NM Resolve", atualizacoes_pedido: "Atualiz. Pedidos" };
            return (
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                {Object.entries(ultimaAtualizacao).map(([tabela, data]) => (
                  <span key={tabela} className="text-[11px] text-muted-foreground">
                    <span className="font-medium">{labels[tabela] || tabela}:</span>{" "}
                    {data ? formatDateTime(data) : "sem dados"}
                  </span>
                ))}
              </div>
            );
          })()}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Atualizar
          </Button>
          {(user?.crm_solicitante || user?.role === "admin") && (
            <Button onClick={handleOpenNewTicket}>
              <Plus className="h-4 w-4 mr-2" />
              Novo Ticket
            </Button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatCard title="Total" value={stats.total} icon={BarChart3} color="text-slate-600" bgColor="bg-slate-100" />
        <StatCard title="Novos" value={stats.novos} icon={Inbox} color="text-blue-600" bgColor="bg-blue-100" />
        <StatCard title="Em Andamento" value={stats.em_andamento} icon={ArrowRight} color="text-amber-600" bgColor="bg-amber-100" />
        <StatCard title="Retorno" value={stats.retorno} icon={Clock} color="text-purple-600" bgColor="bg-purple-100" />
        <StatCard title="Resolvidos" value={stats.resolvidos} icon={CheckCircle2} color="text-emerald-600" bgColor="bg-emerald-100" />
        <StatCard title="Atrasados" value={stats.atrasados} icon={AlertTriangle} color="text-red-600" bgColor="bg-red-100" />
        <StatCard title="Necessita Análise" value={stats.necessita_analise} icon={Bell} color="text-orange-600" bgColor="bg-orange-100" />
      </div>

      {/* Drafts */}
      {drafts.length > 0 && (
        <div className="rounded-xl border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <FilePenLine className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-semibold">Rascunhos</h3>
            <Badge variant="secondary" className="text-xs">{drafts.length}</Badge>
          </div>
          <div className="grid gap-2">
            {drafts.map((draft) => (
              <div
                key={draft.id}
                className="flex items-center justify-between gap-3 rounded-lg border bg-muted/30 px-4 py-2.5 hover:bg-muted/60 transition-colors group"
              >
                <div
                  className="flex-1 min-w-0 cursor-pointer"
                  onClick={() => handleOpenDraft(draft)}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">
                      {draft.form.nome_cliente || draft.form.id_pedido || "Sem identificação"}
                    </span>
                    {draft.form.id_pedido && (
                      <span className="text-xs font-mono text-muted-foreground">#{draft.form.id_pedido}</span>
                    )}
                    <Badge variant="outline" className="text-[10px] shrink-0">
                      Etapa {draft.step}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {draft.form.motivo}
                    {draft.form.descricao && ` — ${draft.form.descricao.slice(0, 60)}${draft.form.descricao.length > 60 ? "..." : ""}`}
                    {" · "}Salvo {formatDateTime(draft.updatedAt)}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" onClick={() => handleOpenDraft(draft)} className="h-8 px-2">
                    <FilePenLine className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDeleteDraft(draft.id)} className="h-8 px-2 text-muted-foreground hover:text-red-600">
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por ID, cliente, área ou motivo..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={filterArea} onValueChange={setFilterArea}>
          <SelectTrigger className="w-[180px]">
            <Filter className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
            <SelectValue placeholder="Motivo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os motivos</SelectItem>
            {(dynamicAreas.length > 0 ? dynamicAreas : CRM_AREAS as unknown as string[]).map((a) => (
              <SelectItem key={a} value={a}>{a}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {dynamicMotivos.length > 0 && (
          <Select value={filterMotivo} onValueChange={setFilterMotivo}>
            <SelectTrigger className="w-[180px]">
              <Tag className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
              <SelectValue placeholder="Área" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas as áreas</SelectItem>
              {dynamicMotivos.map((m) => (
                <SelectItem key={m.nome} value={m.nome}>{m.nome}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Select value={filterAnalista} onValueChange={setFilterAnalista}>
          <SelectTrigger className="w-[180px]">
            <UserCheck className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
            <SelectValue placeholder="Analista" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os analistas</SelectItem>
            {analistas.map((a) => (
              <SelectItem key={a.id} value={String(a.id)}>{a.nome}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Kanban Board */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {COLUMNS.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              tickets={ticketsByStatus(status)}
              onTicketClick={handleTicketClick}
            />
          ))}
        </div>

        <DragOverlay>
          {activeTicket ? (
            <div className="w-[300px]">
              <TicketCard ticket={activeTicket} onClick={() => {}} isDragOverlay />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* New Ticket Dialog */}
      <NewTicketDialog
        open={newDialogOpen}
        onOpenChange={setNewDialogOpen}
        onCreated={loadData}
        draftToLoad={activeDraft}
        onDraftChange={refreshDrafts}
        areas={dynamicAreas}
        areasMap={dynamicAreasMap}
        motivos={dynamicMotivos}
        plataformas={dynamicPlataformas}
        credenciadas={dynamicCredenciadas}
      />

      {/* Ticket Detail */}
      <TicketDetailSheet
        ticket={selectedTicket}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        onStatusChange={handleStatusChange}
        statusOptions={dynamicStatus}
        analistas={analistas}
        resolucaoOptions={dynamicResolucoes}
        areasMap={dynamicAreasMap}
        motivos={dynamicMotivos}
        onCommentAdded={async () => {
          await loadData();
          if (selectedTicket) {
            const updated = await crmService.getTicket(selectedTicket.id);
            setSelectedTicket({ ...updated });
          }
        }}
        onDelete={async (id) => {
          try {
            await crmService.deleteTicket(id);
            toast.success("Ticket excluído");
            setDetailOpen(false);
            setSelectedTicket(null);
            await loadData();
          } catch {
            toast.error("Erro ao excluir ticket");
          }
        }}
      />

    </div>
  );
}
