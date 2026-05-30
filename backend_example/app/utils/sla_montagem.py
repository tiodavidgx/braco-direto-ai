"""
Regras de SLA para acompanhamento de montagem.

Regra de negócio:
- Entrega em dia útil antes das 13:00  -> etapa "manha";
  prazo = mesmo dia às 18:00.
- Entrega em dia útil a partir das 13:00 -> etapa "tarde";
  prazo = próximo dia útil às 13:00.
- Entrega em sábado ou domingo (qualquer hora) -> tratada como
  etapa "manha" de segunda-feira; prazo = segunda às 18:00.

Feriados: tratados como dia útil (fase 2).

Todas as datas são timezone-aware em America/Sao_Paulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional, Literal
from zoneinfo import ZoneInfo


TZ = ZoneInfo("America/Sao_Paulo")

CORTE_MANHA = time(13, 0)      # entregas < 13:00 = etapa manhã
FIM_TARDE = time(18, 0)        # prazo etapa manhã
FIM_MANHA = time(13, 0)        # prazo etapa tarde (no próximo dia útil)
PROXIMO_CORTE_HORAS = 2        # destaque visual de urgência
RECEM_ENTREGUE_MIN = 30        # primeiros 30 min após entrega

Etapa = Literal["manha", "tarde"]
StatusSLA = Literal[
    "fora_do_prazo",
    "proximo_corte",
    "no_prazo",
    "recem_entregue",
    "fds",
]


@dataclass(frozen=True)
class SLAResultado:
    etapa: Etapa
    prazo_limite: datetime             # timezone-aware
    status_sla: StatusSLA
    minutos_restantes: int             # negativo quando fora do prazo
    badge_texto: str                   # texto literal para o card
    entregue_fds: bool                 # entrega ocorreu em sábado/domingo


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _to_local(dt: datetime) -> datetime:
    """Converte timestamp para TZ local. Naive é assumido como já local."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def _is_dia_util(dt: datetime) -> bool:
    # Monday=0 ... Sunday=6
    return dt.weekday() < 5


def _proximo_dia_util(dt: datetime) -> datetime:
    """Retorna o mesmo horário no próximo dia útil (estritamente depois)."""
    nxt = dt + timedelta(days=1)
    while not _is_dia_util(nxt):
        nxt += timedelta(days=1)
    return nxt


def _com_hora(dt: datetime, t: time) -> datetime:
    return dt.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)


def _nome_dia_relativo(prazo: datetime, agora: datetime) -> str:
    """
    Devolve "hoje", "amanhã", "segunda", "terça", etc. em relação a `agora`,
    usando o dia do `prazo`.
    """
    dias = (prazo.date() - agora.date()).days
    if dias == 0:
        return "hoje"
    if dias == 1:
        return "amanhã"
    nomes = [
        "segunda", "terça", "quarta", "quinta",
        "sexta", "sábado", "domingo",
    ]
    return nomes[prazo.weekday()]


# ---------------------------------------------------------------------------
# função principal
# ---------------------------------------------------------------------------

def calcular_sla(
    data_entrega: datetime,
    agora: Optional[datetime] = None,
) -> SLAResultado:
    entrega = _to_local(data_entrega)
    now = _to_local(agora) if agora else datetime.now(TZ)

    entregue_fds = not _is_dia_util(entrega)

    # 1) Determinar etapa e prazo
    if entregue_fds:
        # Normaliza para "manhã de segunda" (ou próximo dia útil)
        base = entrega
        while not _is_dia_util(base):
            base += timedelta(days=1)
        etapa: Etapa = "manha"
        prazo = _com_hora(base, FIM_TARDE)
    elif entrega.time() < CORTE_MANHA:
        etapa = "manha"
        prazo = _com_hora(entrega, FIM_TARDE)
    else:
        etapa = "tarde"
        prazo = _com_hora(_proximo_dia_util(entrega), FIM_MANHA)

    # 2) Minutos restantes e status
    delta = prazo - now
    minutos_restantes = int(delta.total_seconds() // 60)

    if minutos_restantes < 0:
        status_sla: StatusSLA = "fora_do_prazo"
    elif (now - entrega).total_seconds() / 60 <= RECEM_ENTREGUE_MIN:
        status_sla = "recem_entregue"
    elif entregue_fds and not _is_dia_util(now):
        status_sla = "fds"
    elif minutos_restantes <= PROXIMO_CORTE_HORAS * 60:
        status_sla = "proximo_corte"
    else:
        status_sla = "no_prazo"

    # 3) Texto da badge
    badge_texto = _montar_texto_badge(
        status_sla=status_sla,
        etapa=etapa,
        prazo=prazo,
        agora=now,
        entregue_fds=entregue_fds,
    )

    return SLAResultado(
        etapa=etapa,
        prazo_limite=prazo,
        status_sla=status_sla,
        minutos_restantes=minutos_restantes,
        badge_texto=badge_texto,
        entregue_fds=entregue_fds,
    )


def _montar_texto_badge(
    *,
    status_sla: StatusSLA,
    etapa: Etapa,
    prazo: datetime,
    agora: datetime,
    entregue_fds: bool,
) -> str:
    if status_sla == "fora_do_prazo":
        return "Fora do prazo"

    if status_sla == "recem_entregue":
        return "Recém-entregue"

    if status_sla == "fds":
        # ainda é fim de semana; mensagem informativa
        return "Entregue FDS — montar segunda à tarde"

    # no_prazo / proximo_corte
    ref = _nome_dia_relativo(prazo, agora)
    if etapa == "manha":
        return f"Montar {ref} à tarde"
    # etapa == "tarde" -> prazo 13h
    if ref == "hoje":
        return "Montar hoje até 13h"
    if ref == "amanhã":
        return "Montar até amanhã 13h"
    return f"Montar {ref} até 13h"


# ---------------------------------------------------------------------------
# util para serialização
# ---------------------------------------------------------------------------

def sla_to_dict(r: SLAResultado) -> dict:
    return {
        "etapa": r.etapa,
        "prazo_limite": r.prazo_limite.isoformat(),
        "status_sla": r.status_sla,
        "minutos_restantes": r.minutos_restantes,
        "badge_texto": r.badge_texto,
        "entregue_fds": r.entregue_fds,
    }
