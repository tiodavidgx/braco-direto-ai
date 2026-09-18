"""
Rotas para processamento de dados MMS
Verifica duplicidade pelo Número do Pedido e gera relatórios limpos
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from psycopg2.extras import Json
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user, require_admin

router = APIRouter()
logger = logging.getLogger(__name__)


def _ensure_import_log_table(cursor):
    """Garante que a tabela de logs de importação exista (auto-migração)."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mms_importacoes (
            id SERIAL PRIMARY KEY,
            total_recebidos INTEGER NOT NULL DEFAULT 0,
            total_novos INTEGER NOT NULL DEFAULT 0,
            total_duplicados INTEGER NOT NULL DEFAULT 0,
            usuario_id INTEGER,
            usuario_nome VARCHAR(255),
            criado_em TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)


class MMSRecord(BaseModel):
    """Uma linha do relatório MMS. A chave de duplicidade é o Número do Pedido."""
    numero_pedido: str
    filial: Optional[str] = None
    canal_venda: Optional[str] = None
    origem_os: Optional[str] = None
    id_contrato: Optional[str] = None
    id_criticidade: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    complemento: Optional[str] = None
    referencia_endereco: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    nome_cliente: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    valor_total_pedido: Optional[str] = None
    data_recebimento: Optional[str] = None
    id_servico: Optional[str] = None
    valor_servico: Optional[str] = None
    data_agendamento: Optional[str] = None
    turno_agendamento: Optional[str] = None
    data_previsao_entrega: Optional[str] = None
    confirma_entrega: Optional[str] = None
    sku_produto: Optional[str] = None
    descricao_produto: Optional[str] = None
    valor_unitario_produto: Optional[str] = None
    quantidade_produto: Optional[str] = None
    quantidade_volumes: Optional[str] = None


class MMSProcessRequest(BaseModel):
    dados: List[MMSRecord]


class MMSProcessResponse(BaseModel):
    total_recebidos: int
    total_novos: int
    total_duplicados: int
    dados_novos: List[MMSRecord]


def _ensure_dados_column(cursor):
    """Garante a coluna JSONB com a linha completa do relatório (auto-migração)."""
    cursor.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mms_certificados' AND column_name = 'dados'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE mms_certificados ADD COLUMN IF NOT EXISTS dados JSONB")


@router.post("/processar", response_model=MMSProcessResponse)
def processar_mms(
    request: MMSProcessRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Processa dados MMS:
    1. Verifica quais Números do Pedido já existem no banco
    2. Salva os novos pedidos (coluna certificado = Número do Pedido, linha completa em dados)
    3. Registra um log da importação (data/hora, quantidades e quem realizou)
    4. Retorna apenas os dados NÃO duplicados
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            _ensure_dados_column(cursor)

            dados_novos = []
            dados_duplicados = []

            for record in request.dados:
                # Verificar se o pedido já existe
                cursor.execute(
                    "SELECT id FROM mms_certificados WHERE certificado = %s",
                    (record.numero_pedido,)
                )

                if cursor.fetchone():
                    # Já existe - é duplicado
                    dados_duplicados.append(record)
                else:
                    # Não existe - é novo
                    dados_novos.append(record)
                    cursor.execute(
                        "INSERT INTO mms_certificados (certificado, dados) VALUES (%s, %s)",
                        (record.numero_pedido, Json(record.model_dump()))
                    )

            # Registrar log da importação (quem, quando e quantidades)
            _ensure_import_log_table(cursor)
            cursor.execute("""
                INSERT INTO mms_importacoes (
                    total_recebidos, total_novos, total_duplicados,
                    usuario_id, usuario_nome
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                len(request.dados),
                len(dados_novos),
                len(dados_duplicados),
                current_user.get("id"),
                current_user.get("nome"),
            ))

            conn.commit()

            return MMSProcessResponse(
                total_recebidos=len(request.dados),
                total_novos=len(dados_novos),
                total_duplicados=len(dados_duplicados),
                dados_novos=dados_novos
            )
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao processar dados: {str(e)}")
        finally:
            cursor.close()


@router.get("/importacoes")
def listar_importacoes(current_user: dict = Depends(get_current_user)):
    """Lista o histórico de importações (data/hora, quantidades e quem realizou)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        try:
            _ensure_import_log_table(cursor)
            conn.commit()

            cursor.execute("""
                SELECT id, criado_em, total_recebidos, total_novos,
                       total_duplicados, usuario_nome
                FROM mms_importacoes
                ORDER BY criado_em DESC
                LIMIT 200
            """)
            rows = cursor.fetchall()

            return [
                {
                    "id": r[0],
                    "criado_em": r[1].isoformat() if r[1] else None,
                    "total_recebidos": r[2],
                    "total_novos": r[3],
                    "total_duplicados": r[4],
                    "usuario_nome": r[5],
                }
                for r in rows
            ]

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao listar importações: {str(e)}")
        finally:
            cursor.close()


@router.delete("/importacoes/{importacao_id}")
def apagar_importacao(importacao_id: int, current_user: dict = Depends(require_admin)):
    """
    Apaga um lote de importação (só administrador): remove do banco os pedidos gravados
    nele e a linha do histórico. Os pedidos voltam a aparecer como novos na próxima colagem.
    O lote é identificado pelo horário: pedidos e log são gravados na mesma transação,
    então têm o mesmo criado_em.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT criado_em, total_novos, usuario_nome FROM mms_importacoes WHERE id = %s",
                (importacao_id,)
            )
            importacao = cursor.fetchone()
            if not importacao:
                raise HTTPException(status_code=404, detail="Importação não encontrada")
            criado_em, total_novos, usuario_nome = importacao

            cursor.execute("DELETE FROM mms_certificados WHERE criado_em = %s", (criado_em,))
            pedidos_removidos = cursor.rowcount
            if pedidos_removidos > total_novos:
                # Mais pedidos no mesmo horário do que o lote gravou: não dá para separar com segurança
                conn.rollback()
                raise HTTPException(
                    status_code=409,
                    detail=f"O lote tem {total_novos} pedidos novos, mas {pedidos_removidos} batem com o horário. Nada foi apagado."
                )

            cursor.execute("DELETE FROM mms_importacoes WHERE id = %s", (importacao_id,))
            conn.commit()

            logger.warning(
                "MMS: importação %s de %s (%s, %s novos) apagada por %s; %s pedidos removidos",
                importacao_id, usuario_nome, criado_em, total_novos, current_user.get("nome"), pedidos_removidos
            )
            return {"success": True, "pedidos_removidos": pedidos_removidos}

        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao apagar importação: {str(e)}")
        finally:
            cursor.close()


@router.get("/estatisticas")
def get_estatisticas():
    """Retorna estatísticas dos certificados armazenados"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM mms_certificados")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(criado_em), MAX(criado_em) FROM mms_certificados")
            row = cursor.fetchone()
            primeiro = row[0].isoformat() if row[0] else None
            ultimo = row[1].isoformat() if row[1] else None
            
            return {
                "total_certificados": total,
                "primeiro_registro": primeiro,
                "ultimo_registro": ultimo
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")
        finally:
            cursor.close()


@router.post("/verificar")
def verificar_duplicados(request: MMSProcessRequest):
    """
    Apenas verifica quais pedidos são duplicados SEM salvar no banco.
    Útil para preview antes de processar.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            dados_novos = []
            dados_duplicados = []
            # Pedidos já vistos neste relatório: uma linha por pedido, igual ao /processar
            vistos = set()

            for record in request.dados:
                if record.numero_pedido in vistos:
                    dados_duplicados.append(record)
                    continue
                vistos.add(record.numero_pedido)

                cursor.execute(
                    "SELECT id FROM mms_certificados WHERE certificado = %s",
                    (record.numero_pedido,)
                )

                if cursor.fetchone():
                    dados_duplicados.append(record)
                else:
                    dados_novos.append(record)
            
            return {
                "total_recebidos": len(request.dados),
                "total_novos": len(dados_novos),
                "total_duplicados": len(dados_duplicados),
                "dados_novos": dados_novos,
                "dados_duplicados": dados_duplicados
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao verificar dados: {str(e)}")
        finally:
            cursor.close()
