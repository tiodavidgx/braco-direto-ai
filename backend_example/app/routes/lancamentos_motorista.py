"""
from app.utils.whatsapp_http import WA_HEADERS
Rotas para lançamentos do motorista (página pública)
Permite registrar despesas de abastecimento, manutenção e outros
"""

import os
import uuid
import json
import requests
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from app.database import get_db_connection
from app.routes.sistema_auth import get_current_user
import psycopg2.extras

router = APIRouter()


def require_motorista(current_user: dict = Depends(get_current_user)) -> dict:
    """Permite acesso para motorista e admin"""
    if current_user.get('role') not in ('motorista', 'admin'):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return current_user

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "motorista")
os.makedirs(UPLOAD_DIR, exist_ok=True)

WHATSAPP_BASE_URL = "http://localhost:3000"


def enviar_whatsapp_despesa(lancamento: dict, telefone: str):
    """Envia confirmação WhatsApp para o motorista sobre despesa recebida"""
    try:
        if not telefone:
            print("⚠️ Motorista sem telefone cadastrado, WhatsApp não enviado")
            return
        
        # Limpar telefone - manter apenas dígitos
        telefone_limpo = ''.join(c for c in telefone if c.isdigit())
        if not telefone_limpo.startswith('55'):
            telefone_limpo = f"55{telefone_limpo}"
        
        valor_fmt = f"R$ {lancamento['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        mensagem = f"✅ Despesa no valor de {valor_fmt} recebida."
        
        # Verificar status do WhatsApp
        status_response = requests.get(f"{WHATSAPP_BASE_URL}/status", timeout=2, headers=WA_HEADERS)
        status_data = status_response.json()
        
        if status_data.get('status') != 'connected':
            print(f"⚠️ WhatsApp não conectado para notificação de despesa")
            return
        
        # Enviar para o motorista
        response = requests.post(
            f"{WHATSAPP_BASE_URL}/send",
            json={"number": telefone_limpo, "message": mensagem},
            timeout=10, headers=WA_HEADERS)
        
        if response.status_code == 200:
            print(f"✅ Notificação WhatsApp enviada para motorista ({telefone_limpo}): despesa recebida")
        else:
            print(f"⚠️ Erro ao enviar WhatsApp: {response.text}")
            
    except Exception as e:
        print(f"⚠️ Erro ao enviar notificação WhatsApp de despesa: {e}")


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Permite acesso apenas para admin"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Acesso negado")
    return current_user


def serialize_lancamento(l: dict) -> dict:
    """Serializa um lançamento para JSON, incluindo comprovantes_urls"""
    item = dict(l)
    item['valor'] = float(item['valor'])
    if item.get('created_at'):
        item['created_at'] = item['created_at'].isoformat()
    if item.get('pago_em'):
        item['pago_em'] = item['pago_em'].isoformat()
    if item.get('recebido_em'):
        item['recebido_em'] = item['recebido_em'].isoformat()
    # Parse comprovantes_urls JSON
    urls_raw = item.get('comprovantes_urls')
    if urls_raw and isinstance(urls_raw, str):
        try:
            item['comprovantes_urls'] = json.loads(urls_raw)
        except (json.JSONDecodeError, TypeError):
            item['comprovantes_urls'] = []
    elif not urls_raw:
        # Retrocompatibilidade: se comprovantes_urls vazio, usar comprovante_url
        item['comprovantes_urls'] = [item['comprovante_url']] if item.get('comprovante_url') else []
    return item


@router.post("")
async def criar_lancamento(
    tipo: str = Form(...),
    valor: float = Form(...),
    descricao: Optional[str] = Form(None),
    km_atual: int = Form(...),
    observacao: Optional[str] = Form(None),
    comprovantes: List[UploadFile] = File(...),
    current_user: dict = Depends(require_motorista)
):
    """Cria um novo lançamento de despesa do motorista (requer login motorista)"""
    
    tipos_validos = ['abastecimento', 'manutencao', 'outros']
    if tipo not in tipos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {tipos_validos}")
    
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")
    
    # Descrição obrigatória exceto para abastecimento
    if tipo != 'abastecimento' and not descricao:
        raise HTTPException(status_code=400, detail="Descrição é obrigatória para este tipo de despesa")
    
    # Upload dos comprovantes (obrigatório pelo menos 1)
    comprovantes_urls = []
    allowed_ext = ['.jpg', '.jpeg', '.png', '.pdf', '.heic', '.webp']
    
    valid_files = [f for f in comprovantes if f and f.filename]
    if not valid_files:
        raise HTTPException(status_code=400, detail="Comprovante/foto é obrigatório")
    
    for arquivo in valid_files:
        ext = os.path.splitext(arquivo.filename)[1] if arquivo.filename else '.jpg'
        if ext.lower() not in allowed_ext:
            raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido: {arquivo.filename}. Use: {allowed_ext}")
        
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        content = await arquivo.read()
        with open(filepath, "wb") as f:
            f.write(content)
        
        comprovantes_urls.append(f"/uploads/motorista/{filename}")
    
    # Manter comprovante_url com o primeiro arquivo para retrocompatibilidade
    comprovante_url = comprovantes_urls[0] if comprovantes_urls else None
    
    # Salvar no banco
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            INSERT INTO lancamentos_motorista (tipo, descricao, valor, km_atual, observacao, comprovante_url, comprovantes_urls, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (tipo, descricao, valor, km_atual, observacao, comprovante_url, json.dumps(comprovantes_urls), current_user.get('id')))
        
        lancamento = dict(cur.fetchone())
        conn.commit()
    
    # Criar card no Trello
    trello_card = None
    try:
        from app.services.trello_service import TrelloIntegration
        trello = TrelloIntegration()
        
        if trello.is_configured():
            tipo_label = {
                'abastecimento': '⛽ Abastecimento',
                'manutencao': '🔧 Manutenção',
                'outros': '📋 Outros'
            }.get(tipo, tipo)
            
            valor_fmt = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            nome_motorista = current_user.get('nome', 'Motorista')
            id_despesa = lancamento['id']
            titulo = f"🚗 #{id_despesa} - {nome_motorista} - {tipo_label} - {valor_fmt}"
            
            desc_lines = [
                f"## Despesa do Motorista",
                f"",
                f"- **ID:** #{id_despesa}",
                f"- **Motorista:** {nome_motorista}",
                f"- **Tipo:** {tipo_label}",
                f"- **Valor:** {valor_fmt}",
                f"- **KM Atual:** {km_atual:,}".replace(',', '.'),
            ]
            if descricao:
                desc_lines.append(f"- **Descrição:** {descricao}")
            if observacao:
                desc_lines.append(f"- **Observação:** {observacao}")
            
            desc_lines.append(f"")
            desc_lines.append(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            descricao_card = "\n".join(desc_lines)
            
            url = f"{trello.base_url}/cards"
            params = {'key': trello.api_key, 'token': trello.token}
            data = {
                'idList': trello.list_id,
                'name': titulo,
                'desc': descricao_card,
                'pos': 'top'
            }
            
            response = requests.post(url, params=params, json=data, timeout=30)
            response.raise_for_status()
            card_data = response.json()
            
            trello_card = {
                'id': card_data['id'],
                'url': card_data['shortUrl']
            }
            
            # Anexar comprovantes ao card
            for comp_url in comprovantes_urls:
                arquivo_path = os.path.join(UPLOAD_DIR, os.path.basename(comp_url))
                if os.path.exists(arquivo_path):
                    attach_url = f"{trello.base_url}/cards/{card_data['id']}/attachments"
                    with open(arquivo_path, 'rb') as f:
                        requests.post(
                            attach_url,
                            params=params,
                            files={'file': (os.path.basename(arquivo_path), f)},
                            timeout=30
                        )
            
            # Atualizar lançamento com dados do Trello
            with get_db_connection() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("""
                    UPDATE lancamentos_motorista
                    SET trello_card_id = %s, trello_card_url = %s
                    WHERE id = %s
                    RETURNING *
                """, (card_data['id'], card_data['shortUrl'], lancamento['id']))
                lancamento = dict(cur.fetchone())
                conn.commit()
            
            print(f"✅ Card Trello criado para despesa motorista: {card_data['shortUrl']}")
    except Exception as e:
        print(f"⚠️ Erro ao criar card Trello para despesa motorista: {e}")
    
    # Enviar notificação WhatsApp para o telefone do motorista logado
    try:
        telefone_motorista = current_user.get('telefone', '')
        enviar_whatsapp_despesa(lancamento, telefone_motorista)
    except Exception as e:
        print(f"⚠️ Erro ao enviar WhatsApp de despesa: {e}")
    
    # Converter Decimal/datetime para serialização
    lancamento['valor'] = float(lancamento['valor'])
    if lancamento.get('created_at'):
        lancamento['created_at'] = lancamento['created_at'].isoformat()
    
    return {
        "message": "Despesa registrada com sucesso!",
        "lancamento": lancamento,
        "trello": trello_card
    }


@router.get("")
def listar_lancamentos(limit: int = 50, offset: int = 0, current_user: dict = Depends(require_motorista)):
    """Lista os lançamentos do motorista logado (requer login motorista)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        user_id = current_user.get('id')
        is_admin = current_user.get('role') == 'admin'
        
        if is_admin:
            cur.execute("""
                SELECT lm.*, u.nome as motorista_nome
                FROM lancamentos_motorista lm
                LEFT JOIN users u ON u.id = lm.user_id
                ORDER BY lm.created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
        else:
            cur.execute("""
                SELECT lm.*, u.nome as motorista_nome
                FROM lancamentos_motorista lm
                LEFT JOIN users u ON u.id = lm.user_id
                WHERE lm.user_id = %s
                ORDER BY lm.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
        
        lancamentos = cur.fetchall()
        
        if is_admin:
            cur.execute("SELECT COUNT(*) as total FROM lancamentos_motorista")
        else:
            cur.execute("SELECT COUNT(*) as total FROM lancamentos_motorista WHERE user_id = %s", (user_id,))
        total = cur.fetchone()['total']
        
        result = [serialize_lancamento(l) for l in lancamentos]
        
        return {
            "lancamentos": result,
            "total": total
        }


@router.get("/admin")
def listar_lancamentos_admin(limit: int = 100, offset: int = 0, current_user: dict = Depends(require_admin)):
    """Lista TODOS os lançamentos de todos os motoristas (somente admin)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT lm.*, u.nome as motorista_nome, u.telefone as motorista_telefone
            FROM lancamentos_motorista lm
            LEFT JOIN users u ON u.id = lm.user_id
            ORDER BY lm.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        lancamentos = cur.fetchall()
        
        cur.execute("SELECT COUNT(*) as total FROM lancamentos_motorista")
        total = cur.fetchone()['total']
        
        # Totais por motorista
        cur.execute("""
            SELECT u.nome, COUNT(*) as qtd, SUM(lm.valor) as total_valor
            FROM lancamentos_motorista lm
            LEFT JOIN users u ON u.id = lm.user_id
            GROUP BY u.nome
            ORDER BY total_valor DESC
        """)
        resumo_motoristas = []
        for r in cur.fetchall():
            resumo_motoristas.append({
                'nome': r['nome'] or 'Sem motorista',
                'qtd': r['qtd'],
                'total_valor': float(r['total_valor'])
            })
        
        result = [serialize_lancamento(l) for l in lancamentos]
        
        return {
            "lancamentos": result,
            "total": total,
            "resumo_motoristas": resumo_motoristas
        }


@router.patch("/{id}/pago")
def toggle_pago(id: int, current_user: dict = Depends(require_admin)):
    """Marca/desmarca um lançamento como pago (somente admin)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT id, pago FROM lancamentos_motorista WHERE id = %s", (id,))
        lancamento = cur.fetchone()
        
        if not lancamento:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado")
        
        novo_pago = not lancamento['pago']
        pago_em = datetime.now() if novo_pago else None
        
        cur.execute("""
            UPDATE lancamentos_motorista
            SET pago = %s, pago_em = %s
            WHERE id = %s
            RETURNING *
        """, (novo_pago, pago_em, id))
        
        result = serialize_lancamento(cur.fetchone())
        conn.commit()
        
        return {"message": "Pago" if novo_pago else "Desmarcado", "lancamento": result}


@router.patch("/{id}/recebido")
def toggle_recebido(id: int, current_user: dict = Depends(require_motorista)):
    """Marca/desmarca um lançamento como recebido pelo motorista"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT id, recebido, user_id FROM lancamentos_motorista WHERE id = %s", (id,))
        lancamento = cur.fetchone()
        
        if not lancamento:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado")
        
        # Motorista só pode marcar os próprios; admin pode marcar qualquer um
        if current_user.get('role') != 'admin' and lancamento.get('user_id') != current_user.get('id'):
            raise HTTPException(status_code=403, detail="Você só pode alterar seus próprios lançamentos")
        
        novo_recebido = not lancamento['recebido']
        recebido_em = datetime.now() if novo_recebido else None
        
        cur.execute("""
            UPDATE lancamentos_motorista
            SET recebido = %s, recebido_em = %s
            WHERE id = %s
            RETURNING *
        """, (novo_recebido, recebido_em, id))
        
        result = serialize_lancamento(cur.fetchone())
        conn.commit()
        
        return {"message": "Recebido" if novo_recebido else "Desmarcado", "lancamento": result}


def verificar_prazo_edicao(lancamento: dict, current_user: dict):
    """Verifica se o lançamento pode ser editado/excluído (até 5 dias após criação)"""
    is_admin = current_user.get('role') == 'admin'
    if is_admin:
        return  # Admin pode sempre editar/excluir
    
    # Verificar se é do motorista logado
    if lancamento.get('user_id') != current_user.get('id'):
        raise HTTPException(status_code=403, detail="Você só pode alterar seus próprios lançamentos")
    
    # Verificar prazo de 5 dias
    created = lancamento.get('created_at')
    if created:
        dias = (datetime.now() - created).days
        if dias > 5:
            raise HTTPException(status_code=403, detail="Prazo de 5 dias para edição/exclusão expirado")


@router.put("/{id}")
async def editar_lancamento(
    id: int,
    tipo: str = Form(...),
    valor: float = Form(...),
    descricao: Optional[str] = Form(None),
    km_atual: int = Form(...),
    observacao: Optional[str] = Form(None),
    manter_urls: Optional[str] = Form(None),
    comprovantes: List[UploadFile] = File([]),
    current_user: dict = Depends(require_motorista)
):
    """Edita um lançamento (motorista: até 5 dias, admin: sempre)"""
    
    tipos_validos = ['abastecimento', 'manutencao', 'outros']
    if tipo not in tipos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {tipos_validos}")
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")
    if tipo != 'abastecimento' and not descricao:
        raise HTTPException(status_code=400, detail="Descrição é obrigatória para este tipo de despesa")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM lancamentos_motorista WHERE id = %s", (id,))
        lancamento = cur.fetchone()
        if not lancamento:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado")
        
        verificar_prazo_edicao(lancamento, current_user)
        
        # Determinar URLs existentes a manter
        urls_a_manter = []
        if manter_urls:
            try:
                urls_a_manter = json.loads(manter_urls)
            except (json.JSONDecodeError, TypeError):
                urls_a_manter = []
        
        # Obter URLs antigas do banco
        old_urls = []
        urls_raw = lancamento.get('comprovantes_urls')
        if urls_raw:
            try:
                old_urls = json.loads(urls_raw) if isinstance(urls_raw, str) else urls_raw
            except (json.JSONDecodeError, TypeError):
                pass
        if not old_urls and lancamento.get('comprovante_url'):
            old_urls = [lancamento['comprovante_url']]
        
        # Remover arquivos que não estão na lista de manter
        urls_removidas = [u for u in old_urls if u not in urls_a_manter]
        for url in urls_removidas:
            fp = os.path.join(UPLOAD_DIR, os.path.basename(url))
            if os.path.exists(fp):
                os.remove(fp)
        
        # Upload de novos comprovantes
        novas_urls = []
        valid_files = [f for f in (comprovantes or []) if f and f.filename]
        allowed_ext = ['.jpg', '.jpeg', '.png', '.pdf', '.heic', '.webp']
        for arquivo in valid_files:
            ext = os.path.splitext(arquivo.filename)[1] if arquivo.filename else '.jpg'
            if ext.lower() not in allowed_ext:
                raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido: {arquivo.filename}")
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            content = await arquivo.read()
            with open(filepath, "wb") as f:
                f.write(content)
            novas_urls.append(f"/uploads/motorista/{filename}")
        
        # Combinar: mantidas + novas
        todas_urls = urls_a_manter + novas_urls
        comprovante_url = todas_urls[0] if todas_urls else None
        
        cur.execute("""
            UPDATE lancamentos_motorista
            SET tipo=%s, descricao=%s, valor=%s, km_atual=%s, observacao=%s,
                comprovante_url=%s, comprovantes_urls=%s
            WHERE id=%s RETURNING *
        """, (tipo, descricao, valor, km_atual, observacao, comprovante_url, json.dumps(todas_urls), id))
        
        result = serialize_lancamento(cur.fetchone())
        conn.commit()
    
    return {"message": "Lançamento atualizado com sucesso", "lancamento": result}


@router.delete("/{id}")
def excluir_lancamento(id: int, current_user: dict = Depends(require_motorista)):
    """Exclui um lançamento (motorista: até 5 dias, admin: sempre)"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM lancamentos_motorista WHERE id = %s", (id,))
        lancamento = cur.fetchone()
        
        if not lancamento:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado")
        
        verificar_prazo_edicao(lancamento, current_user)
        
        # Remover arquivos se existirem
        comprovantes = []
        urls_raw = lancamento.get('comprovantes_urls')
        if urls_raw:
            try:
                comprovantes = json.loads(urls_raw) if isinstance(urls_raw, str) else urls_raw
            except (json.JSONDecodeError, TypeError):
                pass
        if not comprovantes and lancamento.get('comprovante_url'):
            comprovantes = [lancamento['comprovante_url']]
        
        for url in comprovantes:
            filepath = os.path.join(UPLOAD_DIR, os.path.basename(url))
            if os.path.exists(filepath):
                os.remove(filepath)
        
        cur.execute("DELETE FROM lancamentos_motorista WHERE id = %s", (id,))
        conn.commit()
        
        return {"message": "Lançamento excluído com sucesso"}
