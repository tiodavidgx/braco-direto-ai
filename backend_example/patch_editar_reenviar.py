#!/usr/bin/env python3
"""
Patch: Substitui o endpoint editar-reenviar para usar DELETE + INSERT
em vez de UPDATE, para que o check_boletins_sent não bloqueie os boletins
que já estavam no lote original.
"""

import re

FILE = '/var/www/braco-direto-ai/backend_example/app/routes/relatorios.py'

# Ler arquivo
with open(FILE, 'r') as f:
    content = f.read()

# O endpoint começa em "@router.put("/envio/{envio_id}/editar-reenviar")" 
# e termina antes do próximo bloco (que é o else do prestador + fim do with)
# Vamos encontrar e substituir tudo de "@router.put" até o final

OLD_START = '@router.put("/envio/{envio_id}/editar-reenviar")'
# Find the start
start_idx = content.find(OLD_START)
if start_idx == -1:
    print("❌ Não encontrou o endpoint editar-reenviar!")
    exit(1)

print(f"✅ Encontrou endpoint em posição {start_idx}")

# Find the end - look for the last line of the endpoint
# The endpoint ends with the prestador else clause
end_marker = '            raise HTTPException(status_code=501, detail="Edição de envio de prestador ainda não implementada")'
end_idx = content.find(end_marker, start_idx)
if end_idx == -1:
    print("❌ Não encontrou o final do endpoint!")
    exit(1)

end_idx = end_idx + len(end_marker)
print(f"✅ Encontrou final em posição {end_idx}")

NEW_ENDPOINT = '''@router.put("/envio/{envio_id}/editar-reenviar")
async def editar_e_reenviar_envio(envio_id: int, request: Request):
    """
    Edita um envio: DELETA o lote original e CRIA um novo com os items revisados.
    Gera novo link na API e envia email com PDF atualizado.
    
    Body esperado:
    {
        "tipo": "montador" ou "prestador",
        "items_selecionados": [...],
        "email_destino": "email@exemplo.com"  // opcional
    }
    """
    from app.database import get_db_connection
    import psycopg2.extras
    
    data = await request.json()
    tipo = data.get('tipo')
    items_selecionados = data.get('items_selecionados', [])
    email_destino_override = data.get('email_destino')
    
    if not items_selecionados:
        raise HTTPException(status_code=400, detail="Pelo menos um item deve ser selecionado")
    
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if tipo == "montador":
            # ========== 1. BUSCAR DADOS DO ENVIO ORIGINAL ==========
            cur.execute("""
                SELECT em.*, m.nome as montador_nome, m.email, m.telefone, m.identificador,
                       m.percentual_montagem, m.percentual_assistencia, m.percentual_desmontagem,
                       m.tempo_vencimento_dias
                FROM envios_montagem em
                JOIN montadores m ON m.id = em.montador_id
                WHERE em.id = %s
            """, (envio_id,))
            
            envio = cur.fetchone()
            if not envio:
                raise HTTPException(status_code=404, detail="Envio não encontrado")
            
            # Guardar dados do envio original para o INSERT
            montador_id = envio['montador_id']
            email_destino = email_destino_override or envio['email']
            nome_destinatario = envio['montador_nome']
            data_vencimento = envio.get('data_vencimento_pagamento')
            
            # Percentuais
            percentual_montagem = float(envio['percentual_montagem'] or 0)
            percentual_assistencia = float(envio['percentual_assistencia'] or 0)
            percentual_desmontagem = float(envio['percentual_desmontagem'] or 0)
            
            # Função para formatar data
            def format_data_para_pdf(data_raw):
                if not data_raw:
                    return ''
                if isinstance(data_raw, str):
                    formatos = ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']
                    for fmt in formatos:
                        try:
                            data_obj = datetime.strptime(str(data_raw).split('T')[0], fmt)
                            return data_obj.strftime('%d/%m/%Y')
                        except:
                            continue
                return str(data_raw)
            
            # ========== 2. PROCESSAR ITEMS DA REVISÃO ==========
            items_processados = []
            total_montagem = 0
            total_assistencia = 0
            total_desmontagem = 0
            total_auxilio = 0
            
            for item in items_selecionados:
                tipo_servico = item.get('tipo_servico', 'MONTAGEM').upper()
                valor_venda = float(item.get('valor_venda', item.get('media_de_valor_venda', 0)))
                
                if 'ASSIST' in tipo_servico or 'TECNICA' in tipo_servico:
                    percentual = percentual_assistencia
                    tipo_servico = 'ASSISTENCIA_TECNICA'
                elif 'DESMONT' in tipo_servico:
                    percentual = percentual_desmontagem
                    tipo_servico = 'DESMONTAGEM'
                else:
                    percentual = percentual_montagem
                    tipo_servico = 'MONTAGEM'
                
                if item.get('comissao_editada') is not None:
                    comissao = float(item['comissao_editada'])
                elif item.get('comissao_calculada') is not None:
                    comissao = float(item['comissao_calculada'])
                else:
                    comissao = valor_venda * percentual
                
                if tipo_servico == 'MONTAGEM':
                    total_montagem += comissao
                elif tipo_servico == 'ASSISTENCIA_TECNICA':
                    total_assistencia += comissao
                elif tipo_servico == 'DESMONTAGEM':
                    total_desmontagem += comissao
                
                items_processados.append({
                    "boletim": item.get('boletim', item.get('identificador_boletim_montagem', '')),
                    "data_montagem": format_data_para_pdf(item.get('data_montagem', item.get('data_da_montagem', ''))),
                    "cliente": item.get('cliente', item.get('nome_do_cliente', '-')),
                    "nome_produto": item.get('nome_produto', '-'),
                    "valor_venda": valor_venda,
                    "comissao_calculada": comissao,
                    "comissao_editada": item.get('comissao_editada'),
                    "adicional": float(item.get('adicional', 0)),
                    "motivo_valor_extra": item.get('motivo_valor_extra', item.get('motivo', '')),
                    "tipo_servico": tipo_servico
                })
            
            total_adicionais = sum(float(item.get('adicional', 0)) for item in items_processados)
            total_comissoes = total_montagem + total_assistencia + total_desmontagem
            
            # Calcular período
            datas = []
            for item in items_processados:
                data_str = item.get('data_montagem', '')
                if data_str:
                    try:
                        data_obj = datetime.strptime(data_str, '%d/%m/%Y')
                        datas.append(data_obj)
                    except:
                        pass
            
            if datas:
                min_data = min(datas)
                max_data = max(datas)
                periodo_relatorio = f"{min_data.strftime('%d/%m/%Y')} a {max_data.strftime('%d/%m/%Y')}"
                periodo_mes = max_data.strftime('%m/%Y')
            else:
                periodo_relatorio = envio['periodo']
                periodo_mes = envio['periodo']
            
            # Montar detalhes JSON
            detalhes_json = {
                "nome_montador": nome_destinatario,
                "periodo_relatorio": periodo_relatorio,
                "percentual_montagem": percentual_montagem,
                "percentual_assistencia": percentual_assistencia,
                "percentual_desmontagem": percentual_desmontagem,
                "items": items_processados,
                "total_montagem": total_montagem,
                "total_assistencia": total_assistencia,
                "total_desmontagem": total_desmontagem,
                "total_comissao": total_comissoes,
                "total_adicionais": total_adicionais,
                "total_auxilio": total_auxilio,
                "total_geral": total_comissoes + total_adicionais + total_auxilio,
                "revisado": True,
                "envio_original_id": envio_id,
                "data_revisao": datetime.now().isoformat()
            }
            
            # ========== 3. DELETAR LOTE ORIGINAL ==========
            print(f"🗑️ Deletando lote original #{envio_id}...")
            
            # Deletar notificações relacionadas
            try:
                cur.execute('DELETE FROM notificacoes WHERE lote_id = %s AND tipo LIKE %s', (envio_id, '%montagem%'))
            except Exception as e:
                print(f"   ⚠️ Erro ao deletar notificações: {e}")
                conn.rollback()
            
            # Deletar cards do Trello (se tabela existir)
            try:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'trello_cards'
                    )
                """)
                if cur.fetchone()['exists']:
                    cur.execute('DELETE FROM trello_cards WHERE lote_id = %s', (envio_id,))
            except Exception as e:
                print(f"   ⚠️ Erro ao deletar cards Trello: {e}")
                conn.rollback()
            
            # Deletar o envio original
            cur.execute('DELETE FROM envios_montagem WHERE id = %s RETURNING id', (envio_id,))
            deleted = cur.fetchone()
            if deleted:
                print(f"   ✅ Lote original #{envio_id} deletado")
            else:
                print(f"   ⚠️ Lote #{envio_id} não encontrado para deletar")
            
            # ========== 4. INSERIR NOVO LOTE (REVISÃO) ==========
            cur.execute("""
                INSERT INTO envios_montagem 
                (montador_id, montador_nome, periodo, valor_total, data_envio, data_vencimento_pagamento, status, quantidade_os, detalhes)
                VALUES (%s, %s, %s, %s, NOW(), %s, 'Em Aberto', %s, %s)
                RETURNING id
            """, (
                montador_id,
                nome_destinatario,
                periodo_mes,
                detalhes_json['total_geral'],
                data_vencimento,
                len(items_processados),
                psycopg2.extras.Json(detalhes_json)
            ))
            
            novo_envio_id = cur.fetchone()['id']
            conn.commit()
            print(f"✅ Novo lote #{novo_envio_id} criado (revisão do #{envio_id}) com {len(items_processados)} items")
            
            # ========== 5. GERAR PDF ==========
            from app.routes.relatorios import gerar_pdf_montador_html_template
            
            envio_data = detalhes_json.copy()
            envio_data['id'] = novo_envio_id
            
            try:
                pdf_path = gerar_pdf_montador_html_template(envio_data)
                print(f"✅ PDF gerado: {pdf_path}")
            except Exception as e:
                print(f"❌ Erro ao gerar PDF com WeasyPrint: {e}")
                try:
                    from app.routes.relatorios import gerar_pdf_montador
                    pdf_path = gerar_pdf_montador(envio_data)
                    print(f"✅ PDF gerado (fallback pisa): {pdf_path}")
                except Exception as e2:
                    print(f"❌ Erro ao gerar PDF (fallback): {e2}")
                    raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
            
            # ========== 6. GERAR NOVO LINK NA API ==========
            import requests
            link_upload = None
            try:
                API_UPLOAD_URL = "https://api.link.dev.br/dvprocessamento/"
                API_UPLOAD_KEY = os.getenv("API_UPLOAD_KEY", "")
                
                print(f"   🆔 Novo lote_id para API: {novo_envio_id}")
                
                payload_api = {
                    "nome": nome_destinatario,
                    "email": email_destino,
                    "periodo": periodo_mes,
                    "valor_total": float(detalhes_json['total_geral']),
                    "quantidade_os": len(items_processados),
                    "data_envio": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "lote_id": novo_envio_id,
                    "tipo": "montagem"
                }
                
                print(f"   📦 Payload API: {payload_api}")
                
                headers_api = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                    "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                    "X-API-Key": API_UPLOAD_KEY
                }
                
                response_api = requests.post(
                    API_UPLOAD_URL,
                    json=payload_api,
                    headers=headers_api,
                    timeout=10,
                    verify=False
                )
                
                if response_api.status_code in [200, 201]:
                    resposta_api = response_api.json()
                    if resposta_api.get('success'):
                        link_upload = resposta_api.get('link')
                        upload_hash = resposta_api.get('hash')
                        validade_link = resposta_api.get('validade_link')
                        id_controle_api = resposta_api.get('id_controle') or resposta_api.get('id')
                        
                        print(f"   ✅ Novo link gerado: {link_upload}")
                        
                        # Atualizar link no novo envio
                        cur.execute("""
                            UPDATE envios_montagem 
                            SET link_upload = %s, upload_hash = %s, validade_link = %s, id_controle = %s
                            WHERE id = %s
                        """, (link_upload, upload_hash, validade_link, id_controle_api, novo_envio_id))
                        conn.commit()
                elif response_api.status_code == 409:
                    try:
                        resposta_api = response_api.json()
                        link_upload = resposta_api.get('link')
                        print(f"   ⚠️ Link da resposta 409: {link_upload}")
                    except:
                        print(f"   ⚠️ 409 sem JSON válido")
                else:
                    print(f"   ⚠️ API retornou status {response_api.status_code}")
                    try:
                        print(f"   ⚠️ Resposta: {response_api.text[:200]}")
                    except:
                        pass
            except Exception as e:
                print(f"   ⚠️ Erro ao gerar link via API: {e}")
            
            # Fallback: buscar link do banco (caso tenha sido salvo acima)
            if not link_upload:
                try:
                    cur.execute("SELECT link_upload FROM envios_montagem WHERE id = %s", (novo_envio_id,))
                    row_link = cur.fetchone()
                    if row_link and row_link.get('link_upload'):
                        link_upload = row_link['link_upload']
                        print(f"   ✅ Link recuperado do banco: {link_upload}")
                except Exception as e:
                    print(f"   ⚠️ Erro ao buscar link do banco: {e}")
            
            # ========== 7. ENVIAR EMAIL ==========
            cur.execute("SELECT * FROM email_config LIMIT 1")
            email_config_row = cur.fetchone()
            
            if not email_config_row:
                raise HTTPException(status_code=500, detail="Configuração de email não encontrada")
            
            # Template de email
            template = None
            try:
                cur.execute("SELECT * FROM email_templates WHERE tipo = 'montador' AND ativo = true LIMIT 1")
                template = cur.fetchone()
            except Exception as e:
                print(f"⚠️ Tabela email_templates não encontrada: {e}")
                conn.rollback()
            
            if template:
                assunto = template['assunto'].replace("{{periodo_relatorio}}", periodo_relatorio)
                corpo = template['corpo'].replace("{{periodo_relatorio}}", periodo_relatorio)
                assunto = assunto.replace("{{nome_montador}}", nome_destinatario)
                corpo = corpo.replace("{{nome_montador}}", nome_destinatario)
                link_para_email = link_upload if link_upload else "#"
                corpo = corpo.replace("{{link_upload}}", link_para_email)
                corpo = corpo.replace("{{link}}", link_para_email)
                assunto = f"[REVISADO] {assunto}"
            else:
                link_texto = f"<br><br><strong>Link para envio de NF:</strong> <a href='{link_upload}'>{link_upload}</a>" if link_upload else ""
                assunto = f"[REVISADO] Relatório de Comissões - {periodo_relatorio}"
                corpo = f"Prezado(a) {nome_destinatario},\\n\\nSegue em anexo o relatório **REVISADO** de comissões referente ao período {periodo_relatorio}.{link_texto}"
            
            corpo_html = corpo.replace("\\n", "<br>").replace("**", "<strong>").replace("**", "</strong>")
            
            from app.routes.relatorios import enviar_email_graph
            
            cc_email = email_config_row.get('cc', email_config_row.get('cc_email'))
            
            try:
                sucesso = enviar_email_graph(
                    destinatario=email_destino,
                    assunto=assunto,
                    corpo_html=f"<html><body>{corpo_html}</body></html>",
                    anexo_path=pdf_path,
                    cc=cc_email
                )
                
                if sucesso:
                    print(f"✅ Email enviado para {email_destino}")
                else:
                    raise HTTPException(status_code=500, detail="Falha ao enviar email")
                    
            except Exception as e:
                print(f"❌ Erro ao enviar email: {e}")
                raise HTTPException(status_code=500, detail=f"Erro ao enviar email: {str(e)}")
            
            return {
                "success": True,
                "message": f"Lote original #{envio_id} excluído. Novo lote #{novo_envio_id} criado e enviado com sucesso!",
                "envio_id_original": envio_id,
                "envio_id_novo": novo_envio_id,
                "quantidade_items": len(items_processados),
                "valor_total": detalhes_json['total_geral'],
                "email_enviado_para": email_destino,
                "link_upload": link_upload
            }
        
        else:
            # TODO: Implementar para prestador se necessário
            raise HTTPException(status_code=501, detail="Edição de envio de prestador ainda não implementada")'''

# Substituir
new_content = content[:start_idx] + NEW_ENDPOINT + content[end_idx:]

# Backup
with open(FILE + '.bak_editar', 'w') as f:
    f.write(content)

# Salvar
with open(FILE, 'w') as f:
    f.write(new_content)

print(f"✅ Endpoint editar-reenviar atualizado com sucesso!")
print(f"   - DELETE lote original + INSERT novo lote")
print(f"   - Backup salvo em {FILE}.bak_editar")
