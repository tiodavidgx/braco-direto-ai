"""
Serviço de Envio Automático de Relatórios
Job que processa boletins pendentes e envia via endpoint HTTP interno
"""

import os
import requests
from datetime import datetime, date
from typing import Dict, List, Any, Tuple, Optional
import psycopg2.extras
from app.database import get_db_connection


API_INTERNAL_URL = os.getenv("API_INTERNAL_URL", "http://localhost:8000")
API_INTERNAL_TOKEN = os.getenv("API_INTERNAL_TOKEN", "")


def _calcular_periodo_ciclo(dias_envio: List[int], hoje: date) -> Tuple[date, date]:
    """
    Calcula o período do ciclo: envia tudo pendente até hoje.
    Data de corte = hoje. Boletins com data > hoje ficam pro próximo ciclo.
    """
    data_inicio = date(2020, 1, 1)  # Pega tudo pendente
    data_fim = hoje
    return data_inicio, data_fim


def _get_internal_auth_header() -> Dict[str, str]:
    """Obtém header de autenticação para chamadas internas"""
    headers = {"Content-Type": "application/json"}
    if API_INTERNAL_TOKEN:
        headers["Authorization"] = f"Bearer {API_INTERNAL_TOKEN}"
    return headers


def _buscar_email_config(tipo: str = "montador", template_id: int = None) -> Dict[str, str]:
    """Busca configuração de email do banco. Se template_id informado, usa ele; senão usa o default do tipo."""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if template_id:
            cur.execute(
                "SELECT assunto, corpo, cc FROM email_config WHERE id = %s AND ativo = TRUE",
                (template_id,)
            )
            config = cur.fetchone()
            if config:
                return {
                    "cc": config.get("cc", ""),
                    "assunto": config.get("assunto", ""),
                    "corpo": config.get("corpo", ""),
                    "template_id": template_id,
                }
        
        # Fallback: template default do tipo
        cur.execute(
            "SELECT assunto, corpo, cc, id FROM email_config WHERE tipo = %s AND is_default = TRUE AND ativo = TRUE LIMIT 1",
            (tipo,)
        )
        config = cur.fetchone()
        if not config:
            cur.execute(
                "SELECT assunto, corpo, cc, id FROM email_config WHERE tipo = %s AND ativo = TRUE ORDER BY id LIMIT 1",
                (tipo,)
            )
            config = cur.fetchone()
        
        if config:
            return {
                "cc": config.get("cc", ""),
                "assunto": config.get("assunto", ""),
                "corpo": config.get("corpo", ""),
                "template_id": config.get("id"),
            }
        return {
            "cc": "",
            "assunto": "Relatório de Pagamento de Montagem - Período: {{periodo_relatorio}}",
            "corpo": "Segue em anexo o relatório de pagamento de montagens.",
            "template_id": None,
        }


def processar_envios_pre_aprovados() -> Dict[str, Any]:
    """
    Job scheduler: verifica montadores pré-aprovados cujo dia de envio é hoje.
    Se encontrar, dispara o envio automático.
    """
    hoje = date.today()
    dia_hoje = hoje.day
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar montadores pré-aprovados com hoje no dias_envio_mes
        cur.execute("""
            SELECT id, nome FROM montadores 
            WHERE envio_automatico = TRUE 
              AND ativo = TRUE
              AND pre_aprovado_em IS NOT NULL
              AND %s = ANY(dias_envio_mes)
        """, (dia_hoje,))
        
        montadores = cur.fetchall()
        
        if not montadores:
            return {"status": "ok", "mensagem": f"Nenhum montador pré-aprovado para hoje (dia {dia_hoje})"}
        
        resultado = {"processados": 0, "erros": 0, "detalhes": []}
        
        for m in montadores:
            try:
                resp = processar_envios_automaticos_montadores(
                    dry_run=False, montador_id=m['id']
                )
                # Limpar pré-aprovação após envio
                cur.execute(
                    "UPDATE montadores SET pre_aprovado_em = NULL WHERE id = %s",
                    (m['id'],)
                )
                conn.commit()
                resultado["processados"] += 1
                resultado["detalhes"].append({"montador": m['nome'], "status": "enviado", "resumo": resp})
            except Exception as e:
                resultado["erros"] += 1
                resultado["detalhes"].append({"montador": m['nome'], "status": "erro", "erro": str(e)})
                conn.rollback()
        
        return resultado


def processar_envios_automaticos_montadores(dry_run: bool = False, montador_id: int = None, ate_data: date = None) -> Dict[str, Any]:
    """
    Processa envios automáticos para montadores.
    
    Args:
        dry_run: Se True, apenas simula
        montador_id: Se informado, processa apenas este montador
        ate_data: Se informado, envia boletins até esta data (mescla ciclos vencidos)
    """
    hoje = date.today()
    dia_hoje = hoje.day
    forcando_vencido = ate_data is not None  # True quando é envio manual de ciclo vencido
    
    resultado = {
        "data_execucao": hoje.isoformat(),
        "dry_run": dry_run,
        "ate_data": ate_data.isoformat() if ate_data else None,
        "montadores_processados": 0,
        "montadores_sem_boletins": 0,
        "total_boletins_enviados": 0,
        "erros": 0,
        "detalhes": [],
    }
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar montadores
        if forcando_vencido:
            # Envio de ciclo vencido: não precisa checar dia de envio
            query = """
                SELECT * FROM montadores 
                WHERE envio_automatico = TRUE AND ativo = TRUE
            """
            params = []
        else:
            query = """
                SELECT * FROM montadores 
                WHERE envio_automatico = TRUE 
                  AND ativo = TRUE
                  AND %s = ANY(dias_envio_mes)
            """
            params = [dia_hoje]
        
        if montador_id:
            query += " AND id = %s"
            params.append(montador_id)
        
        cur.execute(query, params)
        
        montadores = cur.fetchall()
        
        if not montadores:
            resultado["mensagem"] = f"Nenhum montador encontrado"
            return resultado
        
        for montador in montadores:
            try:
                dias_envio = montador.get('dias_envio_mes') or []
                
                if ate_data:
                    data_inicio = date(2020, 1, 1)
                    data_fim = ate_data
                else:
                    data_inicio, data_fim = _calcular_periodo_ciclo(dias_envio, hoje)
                
                # Buscar boletins pendentes
                cur.execute("""
                    SELECT * FROM ingestao_boletins_montador
                    WHERE identificador_montador = %s
                      AND status = 'pendente'
                      AND data_montagem >= %s
                      AND data_montagem <= %s
                    ORDER BY data_montagem
                """, (montador['identificador'], data_inicio, data_fim))
                
                boletins = cur.fetchall()
                
                if not boletins:
                    resultado["montadores_sem_boletins"] += 1
                    resultado["detalhes"].append({
                        "montador": montador['nome'],
                        "status": "sem_boletins",
                        "periodo": f"{data_inicio} a {data_fim}",
                    })
                    continue
                
                # Preparar dados no formato do /relatorios/enviar-lote
                dados_envio = []
                for b in boletins:
                    dados_envio.append({
                        "identificador_do_montador": b['identificador_montador'],
                        "nome_do_montador": b['nome_montador'] or montador['nome'],
                        "identificador_boletim_montagem": b['boletim'],
                        "data_da_montagem": b['data_montagem'].isoformat() if b['data_montagem'] else None,
                        "media_de_valor_venda": float(b['valor_venda']),
                        "nome_do_cliente": b['nome_cliente'] or "",
                        "nome_produto": b['nome_produto'] or "",
                        "tipo_servico": b['tipo_servico'] or "MONTAGEM",
                        "adicional": float(b['valor_extra'] or 0),
                        "motivo_valor_extra": b['motivo_valor_extra'] or "",
                        "comissao": float(b['comissao_calculada'] or 0),
                    })
                
                # Buscar custos extras pendentes para este montador
                cur.execute("""
                    SELECT 
                        ce.identificador_boletim,
                        ce.valor,
                        ce.motivo
                    FROM custos_extras ce
                    WHERE ce.identificador_montador = %s
                      AND ce.identificador_boletim LIKE 'A-%%'
                      AND ce.status = 'pendente'
                """, (montador['identificador'],))
                
                custos_extras = cur.fetchall()
                for ce in custos_extras:
                    dados_envio.append({
                        "identificador_do_montador": montador['identificador'],
                        "nome_do_montador": montador['nome'],
                        "identificador_boletim_montagem": ce['identificador_boletim'],
                        "data_da_montagem": hoje.isoformat(),
                        "media_de_valor_venda": 0,
                        "nome_do_cliente": "-",
                        "nome_produto": "-",
                        "tipo_servico": "MONTAGEM",
                        "adicional": float(ce['valor']),
                        "motivo_valor_extra": ce['motivo'] or "",
                        "comissao": 0,
                        "is_ajuste": True,
                    })
                
                # Email config com CC do responsável NM e template do montador
                template_id = montador.get('email_template_id')
                email_config = _buscar_email_config("montador", template_id)
                if montador.get('email_responsavel_nm'):
                    cc_atual = email_config.get('cc', '')
                    if cc_atual:
                        email_config['cc'] = f"{cc_atual}, {montador['email_responsavel_nm']}"
                    else:
                        email_config['cc'] = montador['email_responsavel_nm']
                
                if dry_run:
                    resultado["detalhes"].append({
                        "montador": montador['nome'],
                        "status": "dry_run",
                        "qtd_boletins": len(boletins),
                        "valor_total": sum(float(b['valor_venda']) for b in boletins),
                        "comissao_total": sum(float(b['comissao_calculada'] or 0) for b in boletins),
                        "periodo": f"{data_inicio} a {data_fim}",
                    })
                    continue
                
                # Chamar endpoint de envio via HTTP interno
                payload = {
                    "tipo": "montador",
                    "dados": dados_envio,
                    "emailConfig": email_config,
                    "enviarWhatsApp": True,
                }
                
                response = requests.post(
                    f"{API_INTERNAL_URL}/api/v1/relatorios/enviar-lote",
                    json=payload,
                    headers=_get_internal_auth_header(),
                    timeout=120,
                )
                
                if response.status_code == 200:
                    resp_data = response.json()
                    
                    # Só marcar como processado se o envio realmente deu certo
                    sucessos = resp_data.get('sucesso', 0)
                    erros_envio = resp_data.get('erros', 0)
                    
                    if sucessos > 0:
                        for b in boletins:
                            cur.execute("""
                                UPDATE ingestao_boletins_montador
                                SET status = 'processado', lote_envio_id = %s, updated_at = NOW()
                                WHERE id = %s
                            """, (resp_data.get('lote_id'), b['id']))
                        
                        conn.commit()
                        
                        resultado["montadores_processados"] += 1
                        resultado["total_boletins_enviados"] += len(boletins)
                        resultado["detalhes"].append({
                            "montador": montador['nome'],
                            "status": "enviado",
                            "qtd_boletins": len(boletins),
                            "sucesso": sucessos,
                            "erros_envio": erros_envio,
                        })
                    else:
                        resultado["erros"] += 1
                        resultado["detalhes"].append({
                            "montador": montador['nome'],
                            "status": "erro",
                            "erro": f"Envio falhou: {sucessos} sucessos, {erros_envio} erros",
                        })
                else:
                    resultado["erros"] += 1
                    resultado["detalhes"].append({
                        "montador": montador['nome'],
                        "status": "erro",
                        "erro": f"HTTP {response.status_code}: {response.text[:200]}",
                    })
                    
            except Exception as e:
                resultado["erros"] += 1
                resultado["detalhes"].append({
                    "montador": montador.get('nome', 'N/A'),
                    "status": "erro",
                    "erro": str(e),
                })
                conn.rollback()
    
    return resultado


def processar_envios_dry_run() -> Dict[str, Any]:
    """Executa em modo simulação (dry-run) - não envia emails"""
    return processar_envios_automaticos_montadores(dry_run=True)
