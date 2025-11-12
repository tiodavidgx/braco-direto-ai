"""Pagina de Pagamentos Pendentes"""
import streamlit as st
import database as db
import pandas as pd

def obter_status_urgencia(dias_para_vencimento):
    if dias_para_vencimento < 0:
        dias_atrasado = abs(dias_para_vencimento)
        return ("🔴", f"Vencido ha {dias_atrasado} dia(s)", 1)
    elif dias_para_vencimento == 0:
        return ("⚠️", "Vence HOJE", 2)
    elif dias_para_vencimento == 1:
        return ("🟡", "Vence amanha", 3)
    elif dias_para_vencimento <= 3:
        return ("🟢", f"Vence em {dias_para_vencimento} dias", 4)
    elif dias_para_vencimento <= 10:
        return ("🔵", f"Vence em {dias_para_vencimento} dias", 5)
    else:
        return ("⚪", f"Vence em {dias_para_vencimento} dias", 6)

def pagina_pagamentos_vencidos():
    st.title("Pagamentos Pendentes")
    
    # Botões de ação em massa no topo
    st.markdown("### Ações em Massa")
    col_acao1, col_acao2, col_acao3 = st.columns([2, 2, 2])
    
    with col_acao1:
        if st.button("✅ Marcar Todos com NF como Pagos", use_container_width=True, type="primary"):
            with st.spinner("Marcando como pagos..."):
                resultado = db.marcar_todos_nao_pendentes_como_pagos()
                st.success(f"✅ {resultado['total']} pagamentos marcados! ({resultado['lotes']} lotes + {resultado['montagens']} montagens)")
                st.rerun()
    
    with col_acao2:
        if st.button("🔄 Desfazer TODOS os Pagamentos", use_container_width=True, type="secondary"):
            if st.session_state.get('confirmar_rollback'):
                with st.spinner("Desfazendo pagamentos..."):
                    resultado = db.desmarcar_todos_como_pagos()
                    st.warning(f"🔄 {resultado['total']} pagamentos desfeitos! ({resultado['lotes']} lotes + {resultado['montagens']} montagens)")
                    st.session_state.confirmar_rollback = False
                    st.rerun()
            else:
                st.session_state.confirmar_rollback = True
                st.warning("⚠️ Clique novamente para CONFIRMAR o rollback!")
                st.rerun()
    
    with col_acao3:
        if st.session_state.get('confirmar_rollback'):
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.confirmar_rollback = False
                st.rerun()
    
    st.divider()
    
    pagamentos = db.get_todos_pagamentos_pendentes()
    total_servicos = len(pagamentos['servicos'])
    total_montagens = len(pagamentos['montagens'])
    total_geral = total_servicos + total_montagens
    vencidos = sum(1 for p in pagamentos['servicos'] if p['dias_para_vencimento'] < 0) + sum(1 for p in pagamentos['montagens'] if p['dias_para_vencimento'] < 0)
    urgentes = sum(1 for p in pagamentos['servicos'] if p['dias_para_vencimento'] <= 1) + sum(1 for p in pagamentos['montagens'] if p['dias_para_vencimento'] <= 1)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔴 Vencidos", vencidos)
    with col2:
        st.metric("⚠️ Urgentes", urgentes)
    with col3:
        st.metric("📊 Total", total_geral)
    with col4:
        st.metric("📦/🔧", f"{total_servicos}/{total_montagens}")
    if total_geral == 0:
        st.success("🎉 Nao ha pagamentos pendentes!")
        return
    st.divider()
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        tipo_filtro = st.selectbox("Tipo:", ["Todos", "Servicos", "Montagens"])
    with col_filtro2:
        status_filtro = st.selectbox("Status:", ["Todos", "Vencidos", "Urgentes (0-1d)", "Proximos (2-10d)", "Futuros (>10d)"])
    dados_tabela = []
    for lote in pagamentos['servicos']:
        emoji, status, prioridade = obter_status_urgencia(lote['dias_para_vencimento'])
        fornecedor_id = lote.get('prestador_fornecedor_id') or '-'
        dados_tabela.append({'prioridade': prioridade, 'Status': f"{emoji} {status}", 'Tipo': '📦 Servico', 'ID': lote['id'], 'Nome': lote['prestador_nome'], 'Fornecedor ID': fornecedor_id, 'Periodo': lote.get('periodo', 'N/A'), 'Valor': f"R$ {lote['valor_total']:.2f}" if lote.get('valor_total') else '-', 'Vencimento': lote['data_vencimento_pagamento'].strftime('%d/%m/%Y') if lote.get('data_vencimento_pagamento') else '-', 'NF': lote['data_recebimento_nf'].strftime('%d/%m/%Y') if lote.get('data_recebimento_nf') else '❌', '_tipo_original': 'servico', '_id': lote['id'], '_dias': lote['dias_para_vencimento']})
    for envio in pagamentos['montagens']:
        emoji, status, prioridade = obter_status_urgencia(envio['dias_para_vencimento'])
        detalhes = envio.get('detalhes', {})
        periodo = detalhes.get('periodo_relatorio', envio.get('periodo', 'N/A'))
        fornecedor_id = envio.get('montador_fornecedor_id') or '-'
        dados_tabela.append({'prioridade': prioridade, 'Status': f"{emoji} {status}", 'Tipo': '🔧 Montagem', 'ID': envio['id'], 'Nome': envio['montador_nome'], 'Fornecedor ID': fornecedor_id, 'Periodo': periodo, 'Valor': f"R$ {envio['valor_total']:.2f}" if envio.get('valor_total') else '-', 'Vencimento': envio['data_vencimento_pagamento'].strftime('%d/%m/%Y') if envio.get('data_vencimento_pagamento') else '-', 'NF': envio['data_recebimento_nf'].strftime('%d/%m/%Y') if envio.get('data_recebimento_nf') else '❌', '_tipo_original': 'montagem', '_id': envio['id'], '_dias': envio['dias_para_vencimento']})
    dados_tabela.sort(key=lambda x: x['prioridade'])
    dados_filtrados = dados_tabela.copy()
    if tipo_filtro == "Servicos":
        dados_filtrados = [d for d in dados_filtrados if d['_tipo_original'] == 'servico']
    elif tipo_filtro == "Montagens":
        dados_filtrados = [d for d in dados_filtrados if d['_tipo_original'] == 'montagem']
    if status_filtro == "Vencidos":
        dados_filtrados = [d for d in dados_filtrados if d['_dias'] < 0]
    elif status_filtro == "Urgentes (0-1d)":
        dados_filtrados = [d for d in dados_filtrados if 0 <= d['_dias'] <= 1]
    elif status_filtro == "Proximos (2-10d)":
        dados_filtrados = [d for d in dados_filtrados if 2 <= d['_dias'] <= 10]
    elif status_filtro == "Futuros (>10d)":
        dados_filtrados = [d for d in dados_filtrados if d['_dias'] > 10]
    if not dados_filtrados:
        st.info("Nenhum pagamento encontrado.")
        return
    st.write(f"**Mostrando {len(dados_filtrados)} de {len(dados_tabela)} pagamentos**")
    st.divider()
    
    # Mostrar cada pagamento com botao ao lado
    for idx, item in enumerate(dados_filtrados):
        col_info, col_btn = st.columns([6, 1])
        
        with col_info:
            # Linha com informacoes principais
            st.markdown(f"""
            **{item['Status']}** | {item['Tipo']} | **ID: {item['ID']}** | {item['Nome']} | **Fornecedor ID:** {item['Fornecedor ID']} | {item['Periodo']}  
            💰 {item['Valor']} | ⏰ Vence: {item['Vencimento']} | 📄 NF: {item['NF']}
            """)
        
        with col_btn:
            if st.button("✅ Pago", key=f"pagar_{item['_tipo_original']}_{item['_id']}", use_container_width=True):
                try:
                    if item['_tipo_original'] == 'servico':
                        db.marcar_lote_como_pago(item['_id'])
                        st.success(f"✅ Pago!")
                    else:
                        db.marcar_montagem_como_paga(item['_id'])
                        st.success(f"✅ Pago!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")
        
        if idx < len(dados_filtrados) - 1:
            st.divider()
