import { Eye, Play, Download, X, FileText, FileAudio, File as FileIcon } from "lucide-react";

export type AnexoRef = { nome: string; url: string; tipo: string };

type FileCategory = "image" | "pdf" | "video" | "audio" | "other";

export function getFileCategory(tipo: string, nome: string): FileCategory {
  const t = (tipo || "").toLowerCase();
  const n = (nome || "").toLowerCase();
  if (t.startsWith("image/") || /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(n)) return "image";
  if (t === "application/pdf" || n.endsWith(".pdf")) return "pdf";
  if (t.startsWith("video/") || /\.(mp4|webm|mov|avi|mkv)$/i.test(n)) return "video";
  if (t.startsWith("audio/") || /\.(mp3|wav|ogg|aac|m4a)$/i.test(n)) return "audio";
  return "other";
}

export function resolveUrl(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  const origin = window.location.origin;
  return `${origin}${url}`;
}

export function AttachmentPreview({
  anexo,
  onPreview,
}: {
  anexo: AnexoRef;
  onPreview: (a: AnexoRef) => void;
}) {
  const cat = getFileCategory(anexo.tipo, anexo.nome);
  const fullUrl = resolveUrl(anexo.url);

  if (cat === "image") {
    return (
      <button
        type="button"
        onClick={() => onPreview(anexo)}
        className="group relative rounded-lg overflow-hidden border bg-muted/30 hover:ring-2 hover:ring-primary/50 transition-all"
      >
        <img
          src={fullUrl}
          alt={anexo.nome}
          className="h-28 w-auto max-w-[180px] object-cover"
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
        type="button"
        onClick={() => onPreview(anexo)}
        className="group relative rounded-lg overflow-hidden border bg-muted/30 hover:ring-2 hover:ring-primary/50 transition-all h-28 w-44 flex items-center justify-center"
      >
        <video src={fullUrl} className="h-full w-full object-cover" muted preload="metadata" />
        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-colors flex items-center justify-center">
          <div className="h-9 w-9 rounded-full bg-white/90 flex items-center justify-center shadow">
            <Play className="h-4 w-4 text-primary ml-0.5" />
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
        type="button"
        onClick={() => onPreview(anexo)}
        className="group rounded-lg border bg-muted/30 hover:ring-2 hover:ring-primary/50 transition-all p-3 flex items-center gap-3 w-64"
      >
        <div className="h-10 w-9 rounded bg-red-100 dark:bg-red-900/30 flex items-center justify-center shrink-0">
          <FileText className="h-5 w-5 text-red-600 dark:text-red-400" />
        </div>
        <div className="min-w-0 text-left">
          <p className="text-xs font-medium truncate">{anexo.nome}</p>
          <p className="text-[10px] text-muted-foreground">PDF · Clique para visualizar</p>
        </div>
        <Eye className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
      </button>
    );
  }

  return (
    <a
      href={fullUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="rounded-lg border bg-muted/30 hover:bg-muted transition-colors p-3 flex items-center gap-3 w-64"
    >
      <div className="h-9 w-9 rounded bg-muted flex items-center justify-center shrink-0">
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

export function LightboxPreview({
  anexo,
  onClose,
}: {
  anexo: AnexoRef | null;
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
          type="button"
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
