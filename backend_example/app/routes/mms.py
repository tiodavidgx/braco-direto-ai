"""
Rotas para processamento de dados MMS
Verifica duplicidade de certificados e gera relatórios limpos
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.database import get_db_connection

router = APIRouter()


class MMSRecord(BaseModel):
    certificado: str
    filial_montadora: Optional[str] = None
    data_emissao: Optional[str] = None
    data_entrega: Optional[str] = None
    data_pre_agendamento: Optional[str] = None
    turno_agendamento: Optional[str] = None
    codigo_conjunto: Optional[str] = None
    codigo_mercadoria: Optional[str] = None
    qtde_unit_mercadoria: Optional[str] = None
    descricao_mercadoria: Optional[str] = None
    valor_mercadoria: Optional[str] = None
    valor_unitario_mercadoria: Optional[str] = None
    valor_servico: Optional[str] = None
    valor_custo: Optional[str] = None
    vigencia_inicial: Optional[str] = None
    nome_cliente: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    endereco: Optional[str] = None
    numero_endereco: Optional[str] = None
    complemento_endereco: Optional[str] = None
    referencia: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    bairro: Optional[str] = None
    cep: Optional[str] = None
    ddd: Optional[str] = None
    telefone_principal: Optional[str] = None
    ddd_tel_secundario: Optional[str] = None
    tel_secundario: Optional[str] = None
    email_segurado: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    entrega_realizada: Optional[str] = None
    id_plano: Optional[str] = None


class MMSProcessRequest(BaseModel):
    dados: List[MMSRecord]


class MMSProcessResponse(BaseModel):
    total_recebidos: int
    total_novos: int
    total_duplicados: int
    dados_novos: List[MMSRecord]


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Tenta converter string de data para formato SQL"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # Tentar diferentes formatos
        for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        return None
    except:
        return None


def parse_decimal(value_str: Optional[str]) -> Optional[float]:
    """Converte string para decimal"""
    if not value_str or value_str.strip() == '':
        return None
    try:
        # Remover R$, espaços e trocar vírgula por ponto
        cleaned = value_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(cleaned)
    except:
        return None


@router.post("/processar", response_model=MMSProcessResponse)
def processar_mms(request: MMSProcessRequest):
    """
    Processa dados MMS:
    1. Verifica quais certificados já existem no banco
    2. Salva os novos certificados
    3. Retorna apenas os dados NÃO duplicados
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            dados_novos = []
            dados_duplicados = []
            
            for record in request.dados:
                # Verificar se certificado já existe
                cursor.execute(
                    "SELECT id FROM mms_certificados WHERE certificado = %s",
                    (record.certificado,)
                )
                
                if cursor.fetchone():
                    # Já existe - é duplicado
                    dados_duplicados.append(record)
                else:
                    # Não existe - é novo
                    dados_novos.append(record)
                    
                    # Inserir no banco
                    cursor.execute("""
                        INSERT INTO mms_certificados (
                            certificado, filial_montadora, data_emissao, data_entrega,
                            data_pre_agendamento, turno_agendamento, codigo_conjunto,
                            codigo_mercadoria, qtde_unit_mercadoria, descricao_mercadoria,
                            valor_mercadoria, valor_unitario_mercadoria, valor_servico,
                            valor_custo, vigencia_inicial, nome_cliente, cpf_cnpj,
                            endereco, numero_endereco, complemento_endereco, referencia,
                            cidade, uf, bairro, cep, ddd, telefone_principal,
                            ddd_tel_secundario, tel_secundario, email_segurado,
                            tipo_pessoa, entrega_realizada, id_plano
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s
                        )
                    """, (
                        record.certificado,
                        record.filial_montadora,
                        parse_date(record.data_emissao),
                        parse_date(record.data_entrega),
                        parse_date(record.data_pre_agendamento),
                        record.turno_agendamento,
                        record.codigo_conjunto,
                        record.codigo_mercadoria,
                        parse_decimal(record.qtde_unit_mercadoria),
                        record.descricao_mercadoria,
                        parse_decimal(record.valor_mercadoria),
                        parse_decimal(record.valor_unitario_mercadoria),
                        parse_decimal(record.valor_servico),
                        parse_decimal(record.valor_custo),
                        parse_date(record.vigencia_inicial),
                        record.nome_cliente,
                        record.cpf_cnpj,
                        record.endereco,
                        record.numero_endereco,
                        record.complemento_endereco,
                        record.referencia,
                        record.cidade,
                        record.uf,
                        record.bairro,
                        record.cep,
                        record.ddd,
                        record.telefone_principal,
                        record.ddd_tel_secundario,
                        record.tel_secundario,
                        record.email_segurado,
                        record.tipo_pessoa,
                        record.entrega_realizada,
                        record.id_plano
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


@router.delete("/limpar")
def limpar_dados():
    """Limpa todos os certificados do banco (para reiniciar do zero)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM mms_certificados")
            deleted = cursor.rowcount
            conn.commit()
            
            return {
                "success": True,
                "message": f"{deleted} registros removidos",
                "registros_removidos": deleted
            }
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao limpar dados: {str(e)}")
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
    Apenas verifica quais certificados são duplicados SEM salvar no banco.
    Útil para preview antes de processar.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            dados_novos = []
            dados_duplicados = []
            
            for record in request.dados:
                cursor.execute(
                    "SELECT id FROM mms_certificados WHERE certificado = %s",
                    (record.certificado,)
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
