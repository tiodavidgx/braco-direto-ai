"""
Rotas de Prestadores
Endpoints para CRUD de prestadores
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, EmailStr
import psycopg2.extras
from app.database import get_db_connection

router = APIRouter()

# Modelos Pydantic
class PrestadorBase(BaseModel):
    nome: str
    email: EmailStr
    fornecedor_id: str
    telefone: Optional[str] = None
    regra_envio: str = "Nenhuma"
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: int = 10
    emails_adicionais: Optional[str] = None

class PrestadorCreate(PrestadorBase):
    pass

class PrestadorUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    fornecedor_id: Optional[str] = None
    telefone: Optional[str] = None
    regra_envio: Optional[str] = None
    dias_envio: Optional[str] = None
    tempo_vencimento_dias: Optional[int] = None
    emails_adicionais: Optional[str] = None

@router.get("/")
def listar_prestadores(
    search: Optional[str] = None,
    ativo: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Lista todos os prestadores com paginação e filtros.
    
    - **search**: Busca por nome (opcional)
    - **ativo**: Filtrar por status ativo (opcional)
    - **page**: Número da página (padrão: 1)
    - **limit**: Itens por página (padrão: 10, máx: 100)
    """
    offset = (page - 1) * limit
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query base
        query = "SELECT * FROM prestadores WHERE 1=1"
        params = []
        
        # Filtros
        if search:
            query += " AND nome ILIKE %s"
            params.append(f"%{search}%")
        
        # Count total
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cur.execute(count_query, params)
        total = cur.fetchone()['count']
        
        # Query com paginação
        query += " ORDER BY nome ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        prestadores = cur.fetchall()
        
        return {
            "data": prestadores,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }

@router.get("/{prestador_id}")
def buscar_prestador(prestador_id: int):
    """Busca um prestador específico por ID"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM prestadores WHERE id = %s", (prestador_id,))
        prestador = cur.fetchone()
        
        if not prestador:
            raise HTTPException(status_code=404, detail="Prestador não encontrado")
        
        return prestador

@router.post("/", status_code=201)
def criar_prestador(prestador: PrestadorCreate):
    """Cria um novo prestador"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO prestadores 
                (nome, email, fornecedor_id, telefone, regra_envio, dias_envio, 
                 tempo_vencimento_dias, emails_adicionais)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    prestador.nome,
                    prestador.email,
                    prestador.fornecedor_id,
                    prestador.telefone,
                    prestador.regra_envio,
                    prestador.dias_envio,
                    prestador.tempo_vencimento_dias,
                    prestador.emails_adicionais
                )
            )
            prestador_id = cur.fetchone()[0]
            return {
                "id": prestador_id,
                "message": "Prestador criado com sucesso"
            }
        except psycopg2.IntegrityError as e:
            raise HTTPException(
                status_code=400,
                detail="Fornecedor ID ou Nome já existe"
            )

@router.put("/{prestador_id}")
def atualizar_prestador(prestador_id: int, prestador: PrestadorUpdate):
    """Atualiza um prestador existente"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Verificar se existe
        cur.execute("SELECT id FROM prestadores WHERE id = %s", (prestador_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Prestador não encontrado")
        
        # Construir query de update dinamicamente
        campos = []
        valores = []
        
        for campo, valor in prestador.dict(exclude_unset=True).items():
            campos.append(f"{campo} = %s")
            valores.append(valor)
        
        if not campos:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
        
        valores.append(prestador_id)
        query = f"UPDATE prestadores SET {', '.join(campos)}, updated_at = NOW() WHERE id = %s RETURNING *"
        
        cur.execute(query, valores)
        prestador_atualizado = cur.fetchone()
        
        return prestador_atualizado

@router.delete("/{prestador_id}", status_code=204)
def deletar_prestador(prestador_id: int):
    """Remove um prestador"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Verificar se existe
        cur.execute("SELECT id FROM prestadores WHERE id = %s", (prestador_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Prestador não encontrado")
        
        # Deletar
        cur.execute("DELETE FROM prestadores WHERE id = %s", (prestador_id,))
        
        return None
