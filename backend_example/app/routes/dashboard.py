"""
Rotas de Dashboard
Endpoints para estatísticas e dados do dashboard
"""

from fastapi import APIRouter, HTTPException, Depends
import psycopg2.extras
from app.database import get_db_connection
from app.routes._auth_deps import get_current_user
from datetime import datetime, timedelta

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/stats")
def obter_estatisticas():
    """
    Retorna estatísticas gerais do sistema
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Contar prestadores ativos
        cur.execute("SELECT COUNT(*) as count FROM prestadores")
        prestadores_ativos = cur.fetchone()['count']
        
        # Contar montadores ativos
        cur.execute("SELECT COUNT(*) as count FROM montadores WHERE ativo = TRUE")
        montadores_ativos = cur.fetchone()['count']
        
        # Contar lotes do mês atual
        primeiro_dia_mes = datetime.now().replace(day=1)
        cur.execute(
            "SELECT COUNT(*) as count FROM lotes_servico WHERE data_envio >= %s",
            (primeiro_dia_mes,)
        )
        lotes_mes_atual = cur.fetchone()['count']
        
        # Contar lotes com NF pendente
        cur.execute(
            "SELECT COUNT(*) as count FROM lotes_servico WHERE status = 'Aguardando NF'"
        )
        nfs_aguardando = cur.fetchone()['count']
        
        # Mock de crescimento mensal (calcular baseado em dados reais)
        crescimento_mensal = 12.5
        
        # Mock de pagamentos pendentes (implementar cálculo real)
        pagamentos_pendentes = 45280.50
        
        return {
            "prestadores_ativos": prestadores_ativos,
            "montadores_ativos": montadores_ativos,
            "pagamentos_pendentes": pagamentos_pendentes,
            "nfs_aguardando": nfs_aguardando,
            "lotes_mes_atual": lotes_mes_atual,
            "crescimento_mensal": crescimento_mensal
        }

@router.get("/pendencias")
def obter_pendencias():
    """
    Retorna pendências do dia
    """
    # Mock de pendências (implementar lógica real baseada em regras de envio)
    pendencias = [
        {
            "id": 1,
            "tipo": "prestador",
            "nome": "Prestadora ABC Ltda",
            "acao": "Envio de relatório semanal",
            "data_vencimento": datetime.now().date().isoformat(),
            "status": "urgent"
        }
    ]
    
    return {"pendencias": pendencias}

@router.get("/atividades-recentes")
def obter_atividades_recentes():
    """
    Retorna atividades recentes do sistema
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar últimos lotes criados
        cur.execute("""
            SELECT 
                l.id,
                l.prestador_nome as entidade,
                l.created_at,
                'Lote de serviço criado' as acao,
                'info' as tipo
            FROM lotes_servico l
            ORDER BY l.created_at DESC
            LIMIT 10
        """)
        
        atividades = cur.fetchall()
        
        # Formatar tempo relativo
        for atividade in atividades:
            diff = datetime.now() - atividade['created_at']
            
            if diff.seconds < 3600:
                minutos = diff.seconds // 60
                tempo = f"Há {minutos} minuto{'s' if minutos != 1 else ''}"
            elif diff.seconds < 86400:
                horas = diff.seconds // 3600
                tempo = f"Há {horas} hora{'s' if horas != 1 else ''}"
            else:
                dias = diff.days
                tempo = f"Há {dias} dia{'s' if dias != 1 else ''}"
            
            atividade['tempo'] = tempo
            del atividade['created_at']
        
        return atividades


@router.get("/pendencias-envio")
def obter_pendencias_envio():
    """
    Retorna montadores ATIVOS com envios de relatório atrasados.
    
    Verifica se o montador tem dia_envio_1 e dia_envio_2 configurados,
    e se existe pelo menos um envio em cada período do mês atual.
    
    Períodos:
    - 1º período: dia 1 até dia_envio_1
    - 2º período: dia_envio_1+1 até dia_envio_2
    """
    from calendar import monthrange
    
    hoje = datetime.now()
    dia_atual = hoje.day
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Primeiro e último dia do mês
    primeiro_dia_mes = datetime(ano_atual, mes_atual, 1)
    ultimo_dia_mes = datetime(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1], 23, 59, 59)
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar montadores ATIVOS com dias de envio configurados
        cur.execute("""
            SELECT 
                id, nome, identificador, email, filial, localidade as cidade,
                dia_envio_1, dia_envio_2
            FROM montadores
            WHERE ativo = TRUE 
              AND dia_envio_1 IS NOT NULL 
              AND dia_envio_2 IS NOT NULL
            ORDER BY nome
        """)
        montadores = cur.fetchall()
        
        pendencias = []
        
        for m in montadores:
            dia1 = m['dia_envio_1']
            dia2 = m['dia_envio_2']
            montador_id = m['id']
            
            # Verificar 1º período (dia 1 até dia_envio_1)
            # Só verifica se já passou o dia_envio_1
            if dia_atual > dia1:
                # Verificar se existe envio no 1º período
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM envios_montagem
                    WHERE montador_id = %s
                      AND data_envio >= %s
                      AND data_envio < %s
                """, (
                    montador_id,
                    primeiro_dia_mes,
                    datetime(ano_atual, mes_atual, dia1, 23, 59, 59)
                ))
                envios_p1 = cur.fetchone()['count']
                
                if envios_p1 == 0:
                    dias_atraso = dia_atual - dia1
                    pendencias.append({
                        "montador_id": montador_id,
                        "nome": m['nome'],
                        "identificador": m['identificador'],
                        "email": m['email'],
                        "filial": m['filial'],
                        "cidade": m['cidade'],
                        "periodo": 1,
                        "dia_previsto": dia1,
                        "dias_atraso": dias_atraso,
                        "status": "overdue" if dias_atraso > 3 else "urgent",
                        "descricao": f"1º envio do mês (previsto dia {dia1})"
                    })
            
            # Verificar 2º período (dia_envio_1+1 até dia_envio_2)
            # Só verifica se já passou o dia_envio_2
            if dia_atual > dia2:
                # Verificar se existe envio no 2º período
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM envios_montagem
                    WHERE montador_id = %s
                      AND data_envio > %s
                      AND data_envio <= %s
                """, (
                    montador_id,
                    datetime(ano_atual, mes_atual, dia1, 23, 59, 59),
                    datetime(ano_atual, mes_atual, dia2, 23, 59, 59)
                ))
                envios_p2 = cur.fetchone()['count']
                
                if envios_p2 == 0:
                    dias_atraso = dia_atual - dia2
                    pendencias.append({
                        "montador_id": montador_id,
                        "nome": m['nome'],
                        "identificador": m['identificador'],
                        "email": m['email'],
                        "filial": m['filial'],
                        "cidade": m['cidade'],
                        "periodo": 2,
                        "dia_previsto": dia2,
                        "dias_atraso": dias_atraso,
                        "status": "overdue" if dias_atraso > 3 else "urgent",
                        "descricao": f"2º envio do mês (previsto dia {dia2})"
                    })
        
        # Ordenar por dias de atraso (mais atrasados primeiro)
        pendencias.sort(key=lambda x: x['dias_atraso'], reverse=True)
        
        # Filtrar pendências que foram ignoradas
        cur.execute("""
            SELECT montador_id, periodo FROM pendencias_ignoradas
            WHERE mes = %s AND ano = %s
        """, (mes_atual, ano_atual))
        ignoradas = {(r['montador_id'], r['periodo']) for r in cur.fetchall()}
        
        pendencias_filtradas = [
            p for p in pendencias 
            if (p['montador_id'], p['periodo']) not in ignoradas
        ]
        
        return {
            "total": len(pendencias_filtradas),
            "data_verificacao": hoje.isoformat(),
            "pendencias": pendencias_filtradas
        }


@router.post("/pendencias-envio/ignorar")
def ignorar_pendencia_envio(montador_id: int, periodo: int):
    """
    Ignora uma pendência de envio para o mês atual.
    
    Args:
        montador_id: ID do montador
        periodo: 1 para primeiro período, 2 para segundo período
    """
    from calendar import monthrange
    
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cur.execute("""
                INSERT INTO pendencias_ignoradas (montador_id, periodo, mes, ano)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (montador_id, periodo, mes, ano) DO NOTHING
            """, (montador_id, periodo, mes_atual, ano_atual))
            conn.commit()
            
            return {"success": True, "message": "Pendência ignorada com sucesso"}
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
