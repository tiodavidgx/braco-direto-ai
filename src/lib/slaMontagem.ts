/**
 * Helpers de SLA para atualização em tempo real dos cards.
 * Regra equivalente à do backend (backend_example/app/utils/sla_montagem.py),
 * usada apenas para recomputar o countdown no client sem refetch.
 */

import type { MontagemSLA, MontagemStatusSLA } from "@/types/montagem";

const PROXIMO_CORTE_MIN = 120;

export function minutosAte(iso: string, agora: Date = new Date()): number {
  const d = new Date(iso).getTime();
  return Math.floor((d - agora.getTime()) / 60000);
}

export function recomputarStatus(
  sla: MontagemSLA,
  agora: Date = new Date()
): MontagemStatusSLA {
  const rest = minutosAte(sla.prazo_limite, agora);
  if (rest < 0) return "fora_do_prazo";
  if (sla.status_sla === "recem_entregue") return "recem_entregue"; // preservado
  if (sla.status_sla === "fds") {
    // só "sai" do FDS quando for dia útil; simplificação client-side:
    const dow = agora.getDay();
    if (dow === 0 || dow === 6) return "fds";
  }
  if (rest <= PROXIMO_CORTE_MIN) return "proximo_corte";
  return "no_prazo";
}

export function formatarCountdown(minutos: number): string {
  const abs = Math.abs(minutos);
  const h = Math.floor(abs / 60);
  const m = abs % 60;
  const sign = minutos < 0 ? "-" : "";
  if (h > 0) return `${sign}${h}h${m.toString().padStart(2, "0")}`;
  return `${sign}${m}min`;
}

export function formatarHora(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function formatarData(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

export function formatarDataHora(iso: string): string {
  return `${formatarData(iso)} ${formatarHora(iso)}`;
}
