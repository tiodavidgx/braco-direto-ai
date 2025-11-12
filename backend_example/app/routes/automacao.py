from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from ..database import get_db_connection

router = APIRouter()


class Template(BaseModel):
    nome: str
    tipo: str
    template: str
    ativo: bool = True


class TemplateUpdate(BaseModel):
    template: str


class Trigger(BaseModel):
    evento: str
    template_id: str
    ativo: bool
    condicoes: Optional[dict] = None


@router.get("/templates")
def get_templates():
    """Lista todos os templates ativos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, nome, tipo, template, ativo, variaveis
            FROM templates_whatsapp
            WHERE ativo = TRUE
            ORDER BY tipo, nome
        """)
        
        templates = []
        for row in cursor.fetchall():
            templates.append({
                "id": row[0],
                "nome": row[1],
                "tipo": row[2],
                "template": row[3],
                "ativo": row[4],
                "variaveis": row[5]
            })
        
        return templates
    finally:
        cursor.close()
        conn.close()


@router.post("/templates")
def create_template(template: Template):
    """Cria um novo template"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        variaveis = ["nome_prestador", "periodo", "valor"] if template.tipo == "prestador" else ["nome_montador", "periodo_relatorio", "valor_total"]
        
        cursor.execute("""
            INSERT INTO templates_whatsapp (nome, tipo, template, ativo, variaveis)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (template.nome, template.tipo, template.template, template.ativo, variaveis))
        
        template_id = cursor.fetchone()[0]
        conn.commit()
        
        return {"id": template_id, "message": "Template criado com sucesso"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.put("/templates/{template_id}")
def update_template(template_id: int, update: TemplateUpdate):
    """Atualiza um template existente"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE templates_whatsapp
            SET template = %s
            WHERE id = %s
        """, (update.template, template_id))
        
        conn.commit()
        return {"message": "Template atualizado com sucesso"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/templates/{template_id}")
def delete_template(template_id: int):
    """Desativa um template"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE templates_whatsapp
            SET ativo = FALSE
            WHERE id = %s
        """, (template_id,))
        
        conn.commit()
        return {"message": "Template deletado com sucesso"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/triggers")
def get_triggers():
    """Lista todos os gatilhos configurados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT evento, template_id, ativo, condicoes
            FROM automacao_whatsapp
            ORDER BY evento
        """)
        
        triggers = []
        for row in cursor.fetchall():
            triggers.append({
                "evento": row[0],
                "template_id": row[1],
                "ativo": row[2],
                "condicoes": row[3]
            })
        
        return triggers
    finally:
        cursor.close()
        conn.close()


@router.post("/triggers")
def save_trigger(trigger: Trigger):
    """Salva ou atualiza um gatilho automático"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO automacao_whatsapp (evento, template_id, ativo, condicoes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (evento) 
            DO UPDATE SET 
                template_id = EXCLUDED.template_id,
                ativo = EXCLUDED.ativo,
                condicoes = EXCLUDED.condicoes
        """, (trigger.evento, trigger.template_id, trigger.ativo, trigger.condicoes))
        
        conn.commit()
        return {"message": "Gatilho salvo com sucesso"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
