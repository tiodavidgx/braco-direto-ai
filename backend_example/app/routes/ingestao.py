"""
Rotas de Ingestão de Boletins de Montadores
Recebe dados via API no mesmo formato da aba "Importar Excel" do /envio-montadores
Autenticação via X-Bot-Key (mesmo padrão do dados_bot)
"""

import os
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from pydantic import BaseModel
import csv
import io
import psycopg2.extras
from app.database import get_db_connection

router = APIRouter()


# ============================================================
# Helpers
# ============================================================

def verificar_api_key(api_key: str):
    """Verifica se a API key do bot é válida (mesma tabela do dados_bot)"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM bot_config WHERE api_key = %s AND ativo = TRUE", 
            (api_key,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=401, detail="API key inválida ou inativa")


def parse_date(value):
    """Converte diversos formatos de data para date object"""
    if value is None or value == '' or value == 'None':
        return None
    
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    
    s = str(value).strip()
    
    # Formatos comuns
    formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
        '%d.%m.%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    
    # Se for número serial do Excel
    try:
        from datetime import timedelta
        excel_epoch = datetime(1899, 12, 30)
        dt = excel_epoch + timedelta(days=float(s))
        return dt.date()
    except (ValueError, TypeError):
        pass
    
    return None


def verificar_blacklist(boletim: str, identificador_montador: str) -> bool:
    """Retorna True se o boletim está na blacklist"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM boletins_blacklist WHERE boletim = %s LIMIT 1",
            (str(boletim).strip(),)
        )
        return cur.fetchone() is not None


def verificar_duplicado(boletim: str, identificador_montador: str) -> bool:
    """Retorna True se o boletim já foi enviado em algum lote"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        # Verificar em envios_montagem (detalhes JSONB)
        cur.execute("""
            SELECT 1 FROM envios_montagem,
            jsonb_array_elements(detalhes->'items') as item
            WHERE item->>'identificador_boletim_montagem' = %s
            LIMIT 1
        """, (str(boletim).strip(),))
        return cur.fetchone() is not None


# ============================================================
# Modelos
# ============================================================

class BoletimMontadorEntry(BaseModel):
    """Formato exato do Excel de importação de montadores"""
    identificador_do_montador: str
    nome_do_montador: Optional[str] = None
    identificador_boletim_montagem: str
    data_da_montagem: Optional[str] = None
    media_de_valor_venda: float = 0.0
    nome_do_cliente: Optional[str] = None
    nome_produto: Optional[str] = None
    tipo_servico: str = "MONTAGEM"
    adicional: Optional[float] = 0.0
    motivo_valor_extra: Optional[str] = None


class IngestaoResponse(BaseModel):
    status: str
    inseridos: int = 0
    atualizados: int = 0
    bloqueados: int = 0
    duplicados: int = 0
    erros: int = 0
    detalhes_erros: List[dict] = []


# ============================================================
# Endpoints
# ============================================================

@router.post("/montadores")
def ingestar_boletins_montadores(
    dados: List[BoletimMontadorEntry],
    x_bot_key: str = Header(..., alias="X-Bot-Key"),
):
    """
    Recebe array JSON de boletins de montadores no formato do Excel.
    
    Exemplo de payload:
    [{
        "identificador_do_montador": "123",
        "nome_do_montador": "João",
        "identificador_boletim_montagem": "B001",
        "data_da_montagem": "2026-05-15",
        "media_de_valor_venda": 1500.00,
        "nome_do_cliente": "Cliente A",
        "nome_produto": "Produto X",
        "tipo_servico": "MONTAGEM",
        "adicional": 50.00,
        "motivo_valor_extra": "Deslocamento"
    }]
    """
    verificar_api_key(x_bot_key)
    
    resposta = IngestaoResponse(status="ok")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        for item in dados:
            try:
                identificador = str(item.identificador_do_montador).strip()
                boletim = str(item.identificador_boletim_montagem).strip()
                
                if not identificador or not boletim:
                    resposta.erros += 1
                    resposta.detalhes_erros.append({
                        "boletim": boletim,
                        "erro": "Identificador do montador e boletim são obrigatórios"
                    })
                    continue
                
                # Verificar blacklist
                if verificar_blacklist(boletim, identificador):
                    # UPSERT marcando como bloqueado
                    cur.execute("""
                        INSERT INTO ingestao_boletins_montador 
                            (identificador_montador, boletim, status, updated_at)
                        VALUES (%s, %s, 'bloqueado', NOW())
                        ON CONFLICT (identificador_montador, boletim) 
                        DO UPDATE SET status = 'bloqueado', updated_at = NOW()
                    """, (identificador, boletim))
                    resposta.bloqueados += 1
                    conn.commit()
                    continue
                
                # Verificar duplicado
                if verificar_duplicado(boletim, identificador):
                    cur.execute("""
                        INSERT INTO ingestao_boletins_montador 
                            (identificador_montador, boletim, status, updated_at)
                        VALUES (%s, %s, 'duplicado', NOW())
                        ON CONFLICT (identificador_montador, boletim) 
                        DO UPDATE SET status = 'duplicado', updated_at = NOW()
                    """, (identificador, boletim))
                    resposta.duplicados += 1
                    conn.commit()
                    continue
                
                # Buscar montador para calcular comissão
                cur.execute(
                    "SELECT * FROM montadores WHERE identificador = %s",
                    (identificador,)
                )
                montador = cur.fetchone()
                
                nome_montador = item.nome_do_montador or (montador['nome'] if montador else None)
                valor_venda = float(item.media_de_valor_venda or 0)
                valor_extra = float(item.adicional or 0)
                data_montagem = parse_date(item.data_da_montagem)
                
                # Determinar tipo de serviço
                tipo_raw = (item.tipo_servico or "MONTAGEM").upper()
                if "ASSIST" in tipo_raw or "TECNICA" in tipo_raw:
                    tipo_servico = "ASSISTENCIA_TECNICA"
                elif "DESMONT" in tipo_raw:
                    tipo_servico = "DESMONTAGEM"
                else:
                    tipo_servico = "MONTAGEM"
                
                # Calcular comissão
                percentual = 0.05
                if montador:
                    if tipo_servico == "MONTAGEM":
                        percentual = float(montador.get('percentual_montagem', 0.05))
                    elif tipo_servico == "ASSISTENCIA_TECNICA":
                        percentual = float(montador.get('percentual_assistencia', 0.05))
                    elif tipo_servico == "DESMONTAGEM":
                        percentual = float(montador.get('percentual_desmontagem', 0.05))
                
                comissao = valor_venda * percentual
                
                # UPSERT
                cur.execute("""
                    INSERT INTO ingestao_boletins_montador (
                        identificador_montador, nome_montador, boletim,
                        data_montagem, valor_venda, nome_cliente, nome_produto,
                        tipo_servico, valor_extra, motivo_valor_extra,
                        comissao_calculada, status, updated_at
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, 'pendente', NOW()
                    )
                    ON CONFLICT (identificador_montador, boletim) 
                    DO UPDATE SET
                        nome_montador = EXCLUDED.nome_montador,
                        data_montagem = EXCLUDED.data_montagem,
                        valor_venda = EXCLUDED.valor_venda,
                        nome_cliente = EXCLUDED.nome_cliente,
                        nome_produto = EXCLUDED.nome_produto,
                        tipo_servico = EXCLUDED.tipo_servico,
                        valor_extra = EXCLUDED.valor_extra,
                        motivo_valor_extra = EXCLUDED.motivo_valor_extra,
                        comissao_calculada = EXCLUDED.comissao_calculada,
                        status = CASE 
                            WHEN ingestao_boletins_montador.status = 'processado' 
                            THEN 'processado' 
                            ELSE 'pendente' 
                        END,
                        updated_at = NOW()
                """, (
                    identificador, nome_montador, boletim,
                    data_montagem, valor_venda, item.nome_do_cliente, item.nome_produto,
                    tipo_servico, valor_extra, item.motivo_valor_extra,
                    comissao,
                ))
                
                resposta.inseridos += 1
                conn.commit()
                
            except Exception as e:
                resposta.erros += 1
                resposta.detalhes_erros.append({
                    "boletim": item.identificador_boletim_montagem if hasattr(item, 'identificador_boletim_montagem') else 'N/A',
                    "erro": str(e)
                })
                conn.rollback()
    
    # Atualizar status final
    total = resposta.inseridos + resposta.atualizados + resposta.bloqueados + resposta.duplicados + resposta.erros
    if resposta.erros > 0:
        resposta.status = "concluido_com_erros"
    
    return {
        "status": resposta.status,
        "total_recebido": len(dados),
        "inseridos": resposta.inseridos,
        "atualizados": resposta.atualizados,
        "bloqueados": resposta.bloqueados,
        "duplicados": resposta.duplicados,
        "erros": resposta.erros,
        "detalhes_erros": resposta.detalhes_erros[:10],  # Limitar a 10 erros
    }


@router.post("/montadores/csv")
async def ingestar_boletins_csv(
    file: UploadFile = File(...),
    x_bot_key: str = Header(..., alias="X-Bot-Key"),
):
    """
    Recebe arquivo CSV/Excel com boletins de montadores.
    Mesmas colunas da aba 'Importar Excel'.
    """
    verificar_api_key(x_bot_key)
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    
    # Decodificar e processar CSV
    text_content = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text_content))
    
    # Normalizar nomes das colunas
    rows = []
    for row in reader:
        normalized = {}
        for key, value in row.items():
            normalized_key = key.strip().lower().replace(' ', '_')
            normalized[normalized_key] = value
        rows.append(normalized)
    
    # Mapear para o modelo
    dados = []
    erros_validacao = []
    
    for i, row in enumerate(rows):
        try:
            entry = BoletimMontadorEntry(
                identificador_do_montador=str(row.get('identificador_do_montador', '')),
                nome_do_montador=row.get('nome_do_montador'),
                identificador_boletim_montagem=str(row.get('identificador_boletim_montagem', '')),
                data_da_montagem=row.get('data_da_montagem'),
                media_de_valor_venda=float(row.get('media_de_valor_venda', 0)),
                nome_do_cliente=row.get('nome_do_cliente'),
                nome_produto=row.get('nome_produto'),
                tipo_servico=row.get('tipo_servico', 'MONTAGEM'),
                adicional=float(row.get('adicional', 0) or 0),
                motivo_valor_extra=row.get('motivo_valor_extra'),
            )
            dados.append(entry)
        except Exception as e:
            erros_validacao.append({"linha": i + 2, "erro": str(e)})
    
    # Processar via endpoint JSON
    return ingestar_boletins_montadores(dados=dados, x_bot_key=x_bot_key)
