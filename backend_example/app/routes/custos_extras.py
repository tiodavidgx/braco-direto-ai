"""
Rotas de Custos Extras
Endpoints para gestão de custos extras de montadores
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import psycopg2.extras
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user

router = APIRouter()


class CustoExtraCreate(BaseModel):
    identificador_montador: str
    identificador_boletim: Optional[str] = None
    valor: float
    motivo: str
    observacao: Optional[str] = None
    gerar_boletim: bool = False  # Novo campo para gerar boletim fictício


class CustoExtraUpdate(BaseModel):
    identificador_montador: Optional[str] = None
    identificador_boletim: Optional[str] = None
    valor: Optional[float] = None
    motivo: Optional[str] = None
    observacao: Optional[str] = None
    status: Optional[str] = None


class CustoExtraResponse(BaseModel):
    id: int
    montador_id: Optional[int]
    identificador_montador: str
    identificador_boletim: str
    valor: float
    motivo: str
    observacao: Optional[str]
    status: str
    cadastrado_por: Optional[int]
    cadastrado_por_nome: Optional[str]
    montador_nome: Optional[str]
    processado_em: Optional[datetime]
    created_at: datetime


@router.get("")
def listar_custos_extras(
    status: Optional[str] = None,
    identificador_montador: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """
    Lista custos extras com filtros opcionais
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                ce.id,
                ce.montador_id,
                ce.identificador_montador,
                ce.identificador_boletim,
                ce.valor,
                ce.motivo,
                ce.observacao,
                ce.status,
                ce.cadastrado_por,
                u.nome as cadastrado_por_nome,
                m.nome as montador_nome,
                ce.processado_em,
                ce.created_at
            FROM custos_extras ce
            LEFT JOIN users u ON ce.cadastrado_por = u.id
            LEFT JOIN montadores m ON ce.montador_id = m.id
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND ce.status = %s"
            params.append(status)
        
        if identificador_montador:
            query += " AND ce.identificador_montador = %s"
            params.append(identificador_montador)
        
        query += " ORDER BY ce.created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        custos = cur.fetchall()
        
        return {
            "data": [dict(c) for c in custos],
            "total": len(custos)
        }


def gerar_proximo_boletim_ajuste(cur) -> str:
    """
    Gera o próximo número de boletim de ajuste no formato A-YYYY-NNNN
    Exemplo: A-2026-0001, A-2026-0002, etc.
    """
    ano_atual = datetime.now().year
    prefixo = f"A-{ano_atual}-"
    
    # Buscar o maior número de boletim de ajuste do ano atual
    cur.execute("""
        SELECT identificador_boletim 
        FROM custos_extras 
        WHERE identificador_boletim LIKE %s
        ORDER BY identificador_boletim DESC 
        LIMIT 1
    """, (f"{prefixo}%",))
    
    ultimo = cur.fetchone()
    
    if ultimo:
        # Extrair o número sequencial
        try:
            ultimo_num = int(ultimo['identificador_boletim'].replace(prefixo, ""))
            proximo_num = ultimo_num + 1
        except ValueError:
            proximo_num = 1
    else:
        proximo_num = 1
    
    return f"{prefixo}{proximo_num:04d}"


@router.get("/proximo-boletim-ajuste")
def obter_proximo_boletim_ajuste(
    current_user: dict = Depends(get_current_user)
):
    """
    Retorna o próximo número de boletim de ajuste disponível
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        proximo = gerar_proximo_boletim_ajuste(cur)
        return {"proximo_boletim": proximo}


@router.get("/pendentes")
def listar_custos_pendentes(
    identificador_montador: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Lista apenas custos extras pendentes (não processados)
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                ce.id,
                ce.montador_id,
                ce.identificador_montador,
                ce.identificador_boletim,
                ce.valor,
                ce.motivo,
                ce.status,
                m.nome as montador_nome,
                ce.created_at
            FROM custos_extras ce
            LEFT JOIN montadores m ON ce.montador_id = m.id
            WHERE ce.status = 'pendente'
        """
        params = []
        
        if identificador_montador:
            query += " AND ce.identificador_montador = %s"
            params.append(identificador_montador)
        
        query += " ORDER BY ce.created_at DESC"
        
        cur.execute(query, params)
        custos = cur.fetchall()
        
        return [dict(c) for c in custos]


@router.get("/boletins-ajuste-pendentes")
def listar_boletins_ajuste_pendentes(
    identificador_montador: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Lista boletins de ajuste (A-YYYY-XXXX) pendentes para envio.
    Retorna no formato esperado pelo EnvioRelatoriosMontadores.
    Se identificador_montador for fornecido, filtra apenas os desse montador.
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                ce.id,
                ce.identificador_montador,
                ce.identificador_boletim,
                ce.valor,
                ce.motivo,
                ce.status,
                ce.created_at,
                m.nome as montador_nome
            FROM custos_extras ce
            LEFT JOIN montadores m ON ce.montador_id = m.id
            WHERE ce.identificador_boletim LIKE 'A-%%' 
              AND ce.status = 'pendente'
        """
        params = []
        
        if identificador_montador:
            query += " AND ce.identificador_montador = %s"
            params.append(identificador_montador)
        
        query += " ORDER BY ce.created_at DESC"
        
        cur.execute(query, params)
        custos = cur.fetchall()
        
        # Converter para formato esperado pelo frontend
        resultado = []
        for c in custos:
            resultado.append({
                "identificador_do_montador": c['identificador_montador'],
                "nome_do_montador": c['montador_nome'] or "",
                "identificador_boletim_montagem": c['identificador_boletim'],
                "data_da_montagem": c['created_at'].strftime('%Y-%m-%d') if c['created_at'] else "",
                "media_de_valor_venda": 0,  # Não tem venda
                "nome_do_cliente": "-",
                "nome_produto": "-",
                "comissao": 0,
                "adicional": float(c['valor']),
                "motivo_valor_extra": c['motivo'],
                "tipo_servico": "MONTAGEM",
                "is_ajuste": True  # Marca que é um boletim de ajuste
            })
        
        return resultado


@router.get("/por-boletim/{identificador_boletim}")
def buscar_custos_por_boletim(
    identificador_boletim: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Busca custos extras pendentes para um boletim específico
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                ce.id,
                ce.identificador_montador,
                ce.identificador_boletim,
                ce.valor,
                ce.motivo,
                ce.status,
                m.nome as montador_nome,
                ce.created_at
            FROM custos_extras ce
            LEFT JOIN montadores m ON ce.montador_id = m.id
            WHERE ce.identificador_boletim = %s AND ce.status = 'pendente'
            ORDER BY ce.created_at DESC
        """, (identificador_boletim,))
        
        custos = cur.fetchall()
        
        total_extra = sum(c['valor'] for c in custos)
        
        return {
            "custos": [dict(c) for c in custos],
            "total_extra": total_extra,
            "quantidade": len(custos)
        }


@router.post("")
def criar_custo_extra(
    custo: CustoExtraCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Cria um novo custo extra
    Se gerar_boletim=True, cria um boletim fictício no formato A-YYYY-NNNN
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar montador pelo identificador
        cur.execute(
            "SELECT id, nome FROM montadores WHERE identificador = %s",
            (custo.identificador_montador,)
        )
        montador = cur.fetchone()
        
        # Não permite criar se o montador não existe
        if not montador:
            raise HTTPException(
                status_code=400, 
                detail=f"Montador com identificador '{custo.identificador_montador}' não encontrado. Verifique o código e tente novamente."
            )
        
        montador_id = montador['id']
        
        # Se gerar_boletim=True, criar boletim fictício
        if custo.gerar_boletim:
            identificador_boletim = gerar_proximo_boletim_ajuste(cur)
            is_boletim_gerado = True
        else:
            if not custo.identificador_boletim:
                raise HTTPException(
                    status_code=400,
                    detail="Identificador do boletim é obrigatório quando não está gerando boletim automático."
                )
            identificador_boletim = custo.identificador_boletim.strip()
            is_boletim_gerado = False
        
        # Inserir custo extra
        cur.execute("""
            INSERT INTO custos_extras (
                montador_id, identificador_montador, identificador_boletim,
                valor, motivo, observacao, status, cadastrado_por
            ) VALUES (%s, %s, %s, %s, %s, %s, 'pendente', %s)
            RETURNING id, montador_id, identificador_montador, identificador_boletim,
                      valor, motivo, observacao, status, created_at
        """, (
            montador_id,
            custo.identificador_montador,
            identificador_boletim,
            custo.valor,
            custo.motivo,
            custo.observacao,
            current_user['id']
        ))
        
        novo_custo = cur.fetchone()
        conn.commit()
        
        result = dict(novo_custo)
        result['montador_nome'] = montador['nome']
        result['boletim_gerado'] = is_boletim_gerado
        
        return result


@router.put("/{custo_id}")
def atualizar_custo_extra(
    custo_id: int,
    dados: CustoExtraUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza um custo extra existente
    Operadores só podem editar seus próprios custos, admins podem editar tudo
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se existe
        cur.execute("SELECT id, status, cadastrado_por FROM custos_extras WHERE id = %s", (custo_id,))
        custo = cur.fetchone()
        
        if not custo:
            raise HTTPException(status_code=404, detail="Custo extra não encontrado")
        
        # Verificar permissão: operadores só podem editar seus próprios custos
        is_admin = current_user.get('role') == 'admin'
        is_owner = custo['cadastrado_por'] == current_user['id']
        
        if not is_admin and not is_owner:
            raise HTTPException(
                status_code=403, 
                detail="Você não tem permissão para editar este custo extra. Apenas o criador ou administradores podem editar."
            )
        
        if custo['status'] == 'processado':
            raise HTTPException(status_code=400, detail="Não é possível editar um custo já processado")
        
        # Atualizar campos fornecidos
        updates = []
        params = []
        
        if dados.identificador_montador is not None:
            updates.append("identificador_montador = %s")
            params.append(dados.identificador_montador)
            # Atualizar montador_id também
            cur.execute(
                "SELECT id FROM montadores WHERE identificador = %s",
                (dados.identificador_montador,)
            )
            montador = cur.fetchone()
            updates.append("montador_id = %s")
            params.append(montador['id'] if montador else None)
        
        if dados.identificador_boletim is not None:
            updates.append("identificador_boletim = %s")
            params.append(dados.identificador_boletim)
        
        if dados.valor is not None:
            updates.append("valor = %s")
            params.append(dados.valor)
        
        if dados.motivo is not None:
            updates.append("motivo = %s")
            params.append(dados.motivo)
        
        if dados.observacao is not None:
            updates.append("observacao = %s")
            params.append(dados.observacao)
        
        if dados.status is not None:
            updates.append("status = %s")
            params.append(dados.status)
            if dados.status == 'processado':
                updates.append("processado_em = NOW()")
        
        updates.append("updated_at = NOW()")
        
        if updates:
            query = f"UPDATE custos_extras SET {', '.join(updates)} WHERE id = %s RETURNING *"
            params.append(custo_id)
            cur.execute(query, params)
            custo_atualizado = cur.fetchone()
            conn.commit()
            
            return dict(custo_atualizado)
        
        return {"message": "Nenhuma alteração realizada"}


@router.delete("/{custo_id}")
def excluir_custo_extra(
    custo_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Exclui um custo extra
    Operadores só podem excluir seus próprios custos, admins podem excluir tudo
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se existe e se pode ser excluído
        cur.execute("SELECT id, status, cadastrado_por FROM custos_extras WHERE id = %s", (custo_id,))
        custo = cur.fetchone()
        
        if not custo:
            raise HTTPException(status_code=404, detail="Custo extra não encontrado")
        
        # Verificar permissão: operadores só podem excluir seus próprios custos
        is_admin = current_user.get('role') == 'admin'
        is_owner = custo['cadastrado_por'] == current_user['id']
        
        if not is_admin and not is_owner:
            raise HTTPException(
                status_code=403, 
                detail="Você não tem permissão para excluir este custo extra. Apenas o criador ou administradores podem excluir."
            )
        
        if custo['status'] == 'processado':
            raise HTTPException(status_code=400, detail="Não é possível excluir um custo já processado")
        
        cur.execute("DELETE FROM custos_extras WHERE id = %s", (custo_id,))
        conn.commit()
        
        return {"success": True, "message": "Custo extra excluído com sucesso"}


@router.post("/marcar-processado")
def marcar_como_processado(
    ids: List[int],
    current_user: dict = Depends(get_current_user)
):
    """
    Marca múltiplos custos extras como processados
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            UPDATE custos_extras 
            SET status = 'processado', processado_em = NOW(), updated_at = NOW()
            WHERE id = ANY(%s) AND status = 'pendente'
            RETURNING id
        """, (ids,))
        
        processados = cur.fetchall()
        conn.commit()
        
        return {
            "success": True,
            "processados": len(processados),
            "ids": [p['id'] for p in processados]
        }
