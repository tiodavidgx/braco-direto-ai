"""
Rotas de Dashboard
Endpoints para estatísticas e dados do dashboard
"""

from fastapi import APIRouter
import psycopg2.extras
from app.database import get_db_connection
from datetime import datetime, timedelta

router = APIRouter()

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
