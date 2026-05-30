import os
import base64
import datetime
import re
from pathlib import Path
import json
import time

import streamlit as st
import pandas as pd
import requests
from dotenv import load_dotenv
from msal import PublicClientApplication, SerializableTokenCache
from jinja2 import Template
# weasyprint importado apenas quando necessário (lazy import)

import database as db
from templates.variaveis import mostrar_variaveis_disponiveis
from notificacoes_widget import mostrar_badge_notificacoes, mostrar_modal_notificacoes
from painel_jobs import mostrar_painel_jobs
from notificacoes_toast import processar_notificacoes_toast, badge_contador_notificacoes, marcar_todas_como_lidas
from pagina_pagamentos_vencidos import pagina_pagamentos_vencidos
from painel_whatsapp import mostrar_painel_whatsapp
from automacao_whatsapp import mostrar_automacao_whatsapp
from pagina_relatorios import mostrar_pagina_relatorios

# --- Novas Funções de Configuração ---
CONFIG_FILE = Path("config.json")
DIAS_SEMANA_MAP = {
    "Monday": "Segunda-feira",
    "Tuesday": "Terça-feira", 
    "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira",
    "Friday": "Sexta-feira",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

def load_config():
    """Carrega as configurações salvas do arquivo JSON."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config():
    """Salva as configurações atuais da session_state no arquivo JSON."""
    config_data = {
        "prestador_cc": st.session_state.get("prestador_cc", ""),
        "prestador_subject": st.session_state.get("prestador_subject", ""),
        "prestador_body": st.session_state.get("prestador_body", ""),
        "montador_cc": st.session_state.get("montador_cc", ""),
        "montador_subject": st.session_state.get("montador_subject", ""),
        "montador_body": st.session_state.get("montador_body", "")
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

def convert_plain_text_to_html(text):
    """Converte texto com quebras de linha em HTML simples com <br>."""
    if not text:
        return ""
    # Envolve o texto em parágrafos e substitui quebras de linha por <br>
    return f"<p>{text.replace(chr(10), '<br>')}</p>"

def verificar_pendencias(entidades, tipo):
    pendentes = []
    hoje = datetime.date.today()
    ano_atual, semana_atual, dia_semana_hoje_num = hoje.isocalendar()
    dia_semana_hoje_en = hoje.strftime('%A')
    dia_do_mes_hoje = hoje.day

    for entidade in entidades:
        regra, dias = entidade.get('regra_envio'), entidade.get('dias_envio')
        if not regra or regra == "Nenhuma" or not dias:
            continue
        
        entidade_id = entidade['id']
        pendente = False
        
        if regra == 'Semanal' and DIAS_SEMANA_MAP.get(dia_semana_hoje_en) == dias:
            if not db.get_envios_na_semana(tipo, entidade_id, ano_atual, semana_atual) and not db.foi_ignorado_na_semana(tipo, entidade_id, ano_atual, semana_atual):
                pendente = True
        elif regra in ['Mensal (Dia Fixo)', 'Quinzenal']:
            dias_envio_mes = [int(d.strip()) for d in dias.split(',')]
            if dia_do_mes_hoje in dias_envio_mes:
                # (Lógica simplificada, pode ser melhorada para não mostrar se já foi enviado no dia)
                pendente = True
        
        if pendente:
            pendentes.append(entidade)
            
    return pendentes

st.set_page_config(page_title="Braço Direito", layout="wide", page_icon="🤝")
TOKEN_CACHE_PATH = Path("token_cache.json")
cache = SerializableTokenCache()
if TOKEN_CACHE_PATH.exists():
    cache.deserialize(TOKEN_CACHE_PATH.read_text())

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.Send", "Mail.ReadWrite"]

pca = PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY, token_cache=cache)

# --- FLUXO DE LOGIN ---
if "access_token" not in st.session_state:
    accounts = pca.get_accounts()
    if accounts:
        result = pca.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            st.session_state.access_token = result["access_token"]
            st.session_state.user = accounts[0].get("username")

def login_callback():
    flow = pca.initiate_device_flow(scopes=SCOPES)
    st.info(flow["message"])
    auth = pca.acquire_token_by_device_flow(flow)
    if "access_token" in auth:
        st.session_state.access_token = auth["access_token"]
        TOKEN_CACHE_PATH.write_text(cache.serialize())
        me = requests.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {auth['access_token']}"}).json()
        st.session_state.user = me.get("userPrincipalName", "")
        st.rerun() # Força o recarregamento da página após o login
    else:
        st.session_state.login_error = auth.get("error_description", "desconhecido")

if "access_token" not in st.session_state:
    st.title("🔐 Login com Office 365")
    st.write("Exclua o arquivo 'token_cache.json' se precisar re-autorizar permissões.")
    st.button("Entrar com Office 365", on_click=login_callback)
    if "login_error" in st.session_state: st.error(f"❌ Falha no login: {st.session_state.login_error}")
    st.stop() # Interrompe a execução aqui se não estiver logado

# --- APLICAÇÃO PRINCIPAL (SÓ EXECUTA SE LOGADO) ---
config = load_config()

# 🔔 PROCESSAR NOTIFICAÇÕES TOAST (exibe automaticamente)
processar_notificacoes_toast()

st.sidebar.title("MENU")

# Mostrar contador de notificações no sidebar
count_notif = badge_contador_notificacoes()
if count_notif > 0:
    col_notif1, col_notif2 = st.sidebar.columns([2, 1])
    with col_notif1:
        st.markdown(f"### 🔔 {count_notif}")
    with col_notif2:
        if st.button("✓", help="Marcar todas como lidas", key="clear_all_notif"):
            qtd = marcar_todas_como_lidas()
            st.toast(f"✅ {qtd} notificação(ões) marcadas como lidas", icon="✅")
            st.rerun()

app_mode = st.sidebar.selectbox("Selecione a Página", [
    "Dashboard de Pendências", 
    "Serviços (Prestadores)", 
    "Montagem (Montadores)", 
    "Pagamentos Vencidos",
    "Relatórios de Pagamentos",
    "Upload de Notas Fiscais",
    "WhatsApp",
    "Automação WhatsApp",
    "Jobs Automáticos", 
    "Integrações",
    "Backups do Banco"
])
st.sidebar.info(f"**Conectado como:** \n{st.session_state.user}")

if app_mode == "Dashboard de Pendências":
    st.title("Dashboard de Pendências de Envio")
    
    st.subheader("Prestadores com Envios Pendentes Oggi")
    pendencias_prestadores = verificar_pendencias(db.get_all_prestadores(), 'prestador')
    if not pendencias_prestadores:
        st.success("Nenhum prestador com pendências para hoje!")
    else:
        for p in pendencias_prestadores:
            cols = st.columns([3, 2, 1])
            cols[0].write(f"**{p['nome']}**")
            cols[1].write(f"Regra: {p['regra_envio']} ({p['dias_envio']})")
            if cols[2].button("Ignorar Envio", key=f"ign_p_{p['id']}"):
                hoje = datetime.date.today()
                ano, semana, _ = hoje.isocalendar()
                if p['regra_envio'] == 'Semanal':
                    db.ignorar_envio_semanal('prestador', p['id'], ano, semana)
                    st.success(f"Envio para {p['nome']} ignorado nesta semana.")
                    st.rerun()
    
    st.subheader("Montadores com Envios Pendentes Oggi")
    pendencias_montadores = verificar_pendencias(db.get_all_montadores(apenas_ativos=True), 'montador')
    if not pendencias_montadores:
        st.success("Nenhum montador com pendências para hoje!")
    else:
        for m in pendencias_montadores:
            cols = st.columns([3, 2, 1])
            cols[0].write(f"**{m['nome']}**")
            cols[1].write(f"Regra: {m['regra_envio']} ({m['dias_envio']})")
            if cols[2].button("Ignorar Envio", key=f"ign_m_{m['id']}"):
                hoje = datetime.date.today()
                ano, semana, _ = hoje.isocalendar()
                if m['regra_envio'] == 'Semanal':
                    db.ignorar_envio_semanal('montador', m['id'], ano, semana)
                    st.success(f"Envio para {m['nome']} ignorado nesta semana.")
                    st.rerun()

elif app_mode == "Serviços (Prestadores)":
    st.sidebar.divider()
    page = st.sidebar.radio("Navegar", ["Enviar Boletins", "Gerenciar Prestadores", "Histórico de Envios", "Editor de PDF (Serviços)"])

    if page == "Enviar Boletins":
        st.title("Envio de Boletins de Serviço")
        input_method = st.tabs(["Lançamento Manual", "Importar via Excel"])
        df_para_envio = None

        with input_method[0]:
            st.header("Adicionar Boletim Manualmente")
            if 'manual_entries' not in st.session_state: 
                st.session_state.manual_entries = []
            
            with st.form("manual_entry_form", clear_on_submit=True):
                prestador_nomes = [p['nome'] for p in db.get_all_prestadores()]
                if not prestador_nomes:
                    st.warning("Nenhum prestador cadastrado.")
                else:
                    nome_prestador = st.selectbox("Prestador", options=prestador_nomes)
                    periodo, o_s = st.text_input("Período"), st.text_input("O.S")
                    cliente = st.text_input("Cliente")
                    localidade = st.text_input("Localidade")
                    modalidade = st.text_input("Modalidade")
                    data_execucao = st.date_input("Data de Execução")
                    valor, valor_extra = st.number_input("Valor", 0.0, format="%.2f"), st.number_input("Valor Extra", 0.0, format="%.2f")
                    motivo_valor_extra = st.text_input("Motivo Valor Extra")
                    valor_total = valor + valor_extra
                    st.metric("Valor Total", f"R$ {valor_total:.2f}")
                    
                    if st.form_submit_button("Adicionar à Lista"):
                        st.session_state.manual_entries.append({
                            "nome_prestador": nome_prestador, 
                            "periodo": periodo, 
                            "o_s": o_s, 
                            "cliente": cliente,
                            "localidade": localidade,
                            "modalidade": modalidade, 
                            "data_execucao": data_execucao, 
                            "valor_custo_prestador": valor, 
                            "valor_extra": valor_extra, 
                            "motivo_extra": motivo_valor_extra, 
                            "valor_total": valor_total
                        })
                        
            if st.session_state.manual_entries:
                df_para_envio = pd.DataFrame(st.session_state.manual_entries)
                st.subheader("Lista para Envio")
                st.dataframe(df_para_envio)
                if st.button("Limpar Lista"):
                    st.session_state.manual_entries = []
                    st.rerun()

        with input_method[1]:
            uploader = st.file_uploader("Carregue a planilha", type=["xlsx"], label_visibility="collapsed")
            if uploader:
                df = pd.read_excel(uploader)
                df.columns = [re.sub(r"\W+", "_", c.strip()).lower() for c in df.columns]
                required = ["nome_prestador", "periodo", "data_execucao", "o_s"]
                if not all(c in df.columns for c in required): 
                    st.error(f"Excel precisa das colunas: {', '.join(required)}")
                else:
                    for col in ["valor_custo_prestador", "valor_extra", "valor_total"]:
                        if col in df.columns: 
                            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                    df_para_envio = df
        
        st.divider()
        st.header("🚀 Disparar E-mails de Serviço")
        if df_para_envio is not None and not df_para_envio.empty:
            df_para_envio['o_s'] = df_para_envio['o_s'].astype(str)
            all_os_numbers = df_para_envio['o_s'].dropna().tolist()
            sent_os = db.check_os_list(all_os_numbers)
            blacklisted_os = db.check_os_blacklist(all_os_numbers)
            
            def get_os_status(row):
                os_numero = row['o_s']
                if os_numero in blacklisted_os:
                    return "Na blacklist"
                elif os_numero in sent_os:
                    return "Já enviado"
                return "Pendente"
            
            df_para_envio['status_envio'] = df_para_envio.apply(get_os_status, axis=1)
            
            st.subheader("Pré-visualização")
            st.dataframe(df_para_envio[['nome_prestador', 'o_s', 'status_envio']])
            
            if sent_os: 
                st.warning(f"{len(sent_os)} O.S. já enviadas serão ignoradas.")
            if blacklisted_os:
                st.warning(f"{len(blacklisted_os)} O.S. na blacklist serão ignoradas.")
            
            df_final = df_para_envio[df_para_envio['status_envio'] == 'Pendente']
            
            if df_final.empty: 
                st.error("Nenhuma O.S. nova para enviar.")
            else:
                st.success(f"Tudo pronto para enviar {len(df_final)} novas O.S.")
                
                st.sidebar.divider()
                st.sidebar.title("⚙️ Configurações de Envio (Serviços)")
                
                default_subject = "Novo Mundo Resolve | Nota Fiscal | Período: {{periodo}} | Prestador: {{nome_prestador}}"
                default_body = """Segue a relação de boletins para emissão da nota fiscal de serviços entre **{{periodo}}**.

{% if link_upload %}
📎 Para anexar a Nota Fiscal, acesse o link abaixo:
{{link_upload}}

⚠️ Este link é válido por 30 dias.
{% else %}
📧 O link para anexar a Nota Fiscal será enviado em breve.
{% endif %}

Obrigado."""

                mostrar_variaveis_disponiveis()
                st.text_input("CC", value=config.get("prestador_cc", "projetos.qualidade@novomundo.com.br"), key="prestador_cc", on_change=save_config)
                st.text_input("Assunto", value=config.get("prestador_subject", default_subject), key="prestador_subject", on_change=save_config)
                st.text_area("Corpo do E-mail", value=config.get("prestador_body", default_body), key="prestador_body", on_change=save_config, height=200)
                
                # 📱 Opção de enviar WhatsApp
                enviar_whatsapp = st.checkbox("📱 Enviar notificação por WhatsApp também?", value=True, help="Se ativado, enviará WhatsApp junto com o email (conforme templates configurados em Automação WhatsApp)")
                
                if st.button("▶️ ENVIAR E-MAILS PENDENTES", type="primary"):
                    report = []
                    saudacao = "Bom dia" if datetime.datetime.now().hour < 12 else "Boa tarde" if datetime.datetime.now().hour < 18 else "Boa noite"
                    invoice_tpl = Template(Path("templates/invoice_template.html").read_text(encoding="utf-8"))
                    
                    cc_list = [e.strip() for e in st.session_state.prestador_cc.split(",") if e.strip()]
                    
                    with st.spinner("Enviando e-mails..."):
                        for key, group in df_final.groupby(["nome_prestador", "periodo"]):
                            nome_prestador, periodo = key
                            prestador_info = db.get_prestador_by_name(nome_prestador)
                            if not prestador_info:
                                report.append({"Prestador": nome_prestador, "Status": "❌ Prestador não cadastrado no DB"})
                                continue
                            
                            items_raw = [r.to_dict() for _, r in group.iterrows()]
                            total_geral = float(group["valor_total"].sum())
                            items_fmt = []
                            
                            for item in items_raw:
                                data_exec = item.get('data_execucao')
                                items_fmt.append({
                                    "OS": item.get('o_s'), 
                                    "Cliente": item.get('cliente', '-'),
                                    "Localidade": item.get('localidade', '-'),
                                    "Modalidade": item.get('modalidade'), 
                                    "Data_execucao": data_exec.strftime('%d/%m/%Y') if hasattr(data_exec, 'strftime') else str(data_exec), 
                                    "Valor": f"{item.get('valor_custo_prestador', 0):.2f}", 
                                    "Valor_extra": f"{item.get('valor_extra', 0):.2f}", 
                                    "Motivo_valor_extra": item.get("motivo_extra", "-"), 
                                    "Valor_total": f"{item.get('valor_total', 0):.2f}"
                                })
                            
                            items_to_log = []
                            for item in items_raw:
                                log_item = {k: (v.isoformat() if isinstance(v, (datetime.date, datetime.datetime)) else (None if pd.isna(v) else v)) for k, v in item.items()}
                                items_to_log.append(log_item)
                            
                            lote_id = db.criar_lote_servico(prestador_info['id'], nome_prestador, periodo, total_geral, items_to_log)
                            
                            # 🔗 Gerar link de upload ANTES de enviar o email
                            link_upload = ''
                            try:
                                from api_upload_client import enviar_lote_para_api
                                
                                # Aguardar até 15 segundos pelo link
                                max_tentativas = 15
                                tentativa = 0
                                
                                sucesso, mensagem, dados = enviar_lote_para_api(lote_id)
                                
                                if sucesso and dados:
                                    link_upload = dados.get('link', '')
                                    
                                    # Se não veio no retorno imediato, fazer polling
                                    if not link_upload:
                                        while tentativa < max_tentativas and not link_upload:
                                            time.sleep(1)
                                            tentativa += 1
                                            lote_salvo = db.get_lote_by_id(lote_id)
                                            if lote_salvo and lote_salvo.get('link_upload'):
                                                link_upload = lote_salvo['link_upload']
                                                print(f"   ✅ Link prestador obtido em {tentativa}s: {link_upload[:50]}...")
                                                break
                                
                                if not link_upload:
                                    print(f"   ⚠️  Link do prestador não gerado após {max_tentativas}s")
                                    
                            except Exception as e:
                                print(f"⚠️ Erro ao gerar link: {str(e)}")
                            
                            ctx = {
                                "nome_prestador": nome_prestador, 
                                "periodo": periodo, 
                                "items": items_fmt, 
                                "total_geral": total_geral, 
                                "saudacao": saudacao, 
                                "lote_id": lote_id,
                                "link": link_upload if link_upload else "⚠️ Link em processamento - consulte o histórico"  # ✅ Usar 'link' não 'link_upload'
                            }
                            
                            subj_template = Template(st.session_state.prestador_subject)
                            body_template = Template(st.session_state.prestador_body)
                            
                            subj, body_plain = subj_template.render(**ctx), body_template.render(**ctx)
                            body_html = convert_plain_text_to_html(body_plain)
                            html_pdf = invoice_tpl.render(**ctx)
                            
                            # Lazy import do weasyprint (só quando necessário para gerar PDF)
                            import os
                            os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')
                            from weasyprint import HTML
                            pdf_bytes = HTML(string=html_pdf, base_url="templates").write_pdf()

                            # Obter todos os emails do prestador (principal + adicionais)
                            prestador_emails = db.get_prestador_emails(prestador_info)
                            recipients = [{"emailAddress": {"address": email}} for email in prestador_emails]
                            
                            message_data = {
                                "subject": subj, 
                                "body": {"contentType": "HTML", "content": body_html}, 
                                "toRecipients": recipients, 
                                "attachments": [{"@odata.type": "#microsoft.graph.fileAttachment", "name": f"Relatorio_{nome_prestador.replace(' ', '_')}_Lote_{lote_id}.pdf", "contentBytes": base64.b64encode(pdf_bytes).decode()}]
                            }
                            
                            if cc_list:
                                message_data["ccRecipients"] = [{"emailAddress": {"address": cc}} for cc in cc_list]
                            
                            final_payload = { "message": message_data, "saveToSentItems": "true" }

                            resp = requests.post("https://graph.microsoft.com/v1.0/me/sendMail", headers={"Authorization": f"Bearer {st.session_state.access_token}", "Content-Type": "application/json"}, json=final_payload)
                            
                            if resp.status_code == 202:
                                time.sleep(2)
                                headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                                sent_items_url = "https://graph.microsoft.com/v1.0/me/mailfolders/sentitems/messages?$top=1&$select=conversationId"
                                sent_resp = requests.get(sent_items_url, headers=headers).json()
                                conversation_id = sent_resp['value'][0]['conversationId']
                                db.atualizar_lote_com_conversation_id(lote_id, conversation_id)
                                
                                # 📱 Enviar WhatsApp se opção marcada
                                whatsapp_status = ""
                                if enviar_whatsapp:
                                    try:
                                        print(f"\n🔵 Iniciando envio WhatsApp para prestador {prestador_info['id']}")
                                        from whatsapp_triggers import WhatsAppAutomation
                                        wa_automation = WhatsAppAutomation()
                                        print(f"🔵 Chamando enviar_prestador_email_enviado...")
                                        resultado_wa = wa_automation.enviar_prestador_email_enviado(
                                            prestador_info['id'],
                                            periodo,
                                            total_geral,
                                            link_upload if link_upload else ""
                                        )
                                        print(f"🔵 Resultado WhatsApp: {resultado_wa}")
                                        
                                        if resultado_wa.get("success"):
                                            whatsapp_status = " 📱✅"
                                            print(f"✅ WhatsApp enviado com sucesso!")
                                        else:
                                            whatsapp_status = f" 📱⚠️ ({resultado_wa.get('error', 'erro desconhecido')})"
                                            print(f"⚠️ WhatsApp não enviado: {resultado_wa.get('error')}")
                                    except Exception as e:
                                        import traceback
                                        print(f"❌ ERRO ao enviar WhatsApp: {str(e)}")
                                        print(f"❌ Traceback: {traceback.format_exc()}")
                                        whatsapp_status = f" 📱❌ ({str(e)[:30]})"
                                
                                report.append({"Prestador": nome_prestador, "Status": f"✅ Lote #{lote_id} Enviado{whatsapp_status}"})
                            else:
                                report.append({"Prestador": nome_prestador, "Status": f"❌ Erro {resp.status_code} - {resp.text}"})
                                
                    st.subheader("📋 Relatório de Envio")
                    st.table(pd.DataFrame(report))
                    st.success("Processo concluído!")
                    st.session_state.manual_entries = []

    elif page == "Gerenciar Prestadores":
        st.title("📇 Gerenciar Prestadores de Serviço")
        
        # Seção de Blacklist de OS
        with st.expander("📋 Blacklist de O.S."):
            st.subheader("Adicionar O.S. à Blacklist")
            cols = st.columns([2, 2, 1])
            
            with cols[0]:
                prestadores = {p['nome']: p['id'] for p in db.get_all_prestadores()}
                prestador_selected = st.selectbox("Prestador", options=list(prestadores.keys()))
            
            with cols[1]:
                os_input = st.text_input("Números das O.S. (separados por vírgula)")
            
            with cols[2]:
                motivo = st.text_input("Motivo (opcional)")
            
            if st.button("Adicionar à Blacklist"):
                if os_input and prestador_selected:
                    prestador_id = prestadores[prestador_selected]
                    os_numbers = [o.strip() for o in os_input.split(",")]
                    for os_numero in os_numbers:
                        success, message = db.adicionar_os_blacklist(prestador_id, os_numero, motivo)
                        st.toast(f"O.S. {os_numero}: {message}")
                    st.rerun()
                else:
                    st.warning("Selecione um prestador e insira os números das O.S.")
            
            st.divider()
            st.subheader("O.S. na Blacklist")
            os_blacklist = db.get_os_blacklist()
            
            if not os_blacklist:
                st.info("Nenhuma O.S. na blacklist.")
            else:
                for o in os_blacklist:
                    cols = st.columns([2, 2, 2, 1])
                    cols[0].text(o['prestador_nome'])
                    cols[1].text(f"O.S.: {o['os_numero']}")
                    cols[2].text(f"Motivo: {o['motivo'] or '-'}")
                    if cols[3].button("🗑️", key=f"del_os_blacklist_{o['id']}"):
                        db.remover_os_blacklist(o['prestador_id'], o['os_numero'])
                        st.success(f"O.S. {o['os_numero']} removida da blacklist!")
                        st.rerun()
        
        st.divider()
        
        with st.form("novo_prestador_form", clear_on_submit=True):
            st.subheader("Adicionar Novo Prestador")
            nome = st.text_input("Nome")
            email = st.text_input("E-mail Principal")
            emails_adicionais = st.text_input("E-mails Adicionais (separados por vírgula)", 
                                            help="Digite os emails adicionais separados por vírgula. Ex: email2@empresa.com, email3@empresa.com")
            fornecedor_id = st.text_input("Número do Fornecedor")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                regra_envio = st.selectbox("Regra de Envio", ["Nenhuma", "Semanal", "Mensal (Dia Fixo)", "Quinzenal"], key="p_regra")
            with col2:
                tempo_vencimento_dias = st.selectbox("Prazo Pagamento", options=[3, 10], index=1, 
                                                    help="Prazo em dias úteis para pagamento após recebimento da NF")
            
            dias_envio = ""
            
            if regra_envio == "Semanal":
                dias_envio = st.selectbox("Dia da Semana", list(DIAS_SEMANA_MAP.values()), key="p_dia_sem")
            elif regra_envio in ["Mensal (Dia Fixo)", "Quinzenal"]:
                dias_envio = st.text_input("Dias do Mês (ex: 5 ou 5,20)", key="p_dia_mes")
            
            if st.form_submit_button("Adicionar"):
                if all([nome, email, fornecedor_id]):
                    success, message = db.add_prestador(nome, email, fornecedor_id, regra_envio, dias_envio, 
                                                       emails_adicionais.strip() if emails_adicionais.strip() else None,
                                                       tempo_vencimento_dias)
                    st.toast(message)
                else:
                    st.warning("Todos os campos obrigatórios devem ser preenchidos (Nome, E-mail Principal e Número do Fornecedor).")
                    
        st.divider()
        st.subheader("Prestadores Cadastrados")
        
        for p in db.get_all_prestadores():
            with st.expander(f"{p['nome']} - ID: {p['id']}"):
                # Mostrar emails atuais
                st.info(f"**E-mail Principal:** {p['email']}")
                if p.get('emails_adicionais'):
                    emails_extras = [email.strip() for email in p['emails_adicionais'].split(',') if email.strip()]
                    st.info(f"**E-mails Adicionais:** {', '.join(emails_extras)}")
                
                # Mostrar prazo de pagamento atual
                prazo_atual = p.get('tempo_vencimento_dias', 10)
                st.info(f"**⏰ Prazo de Pagamento:** {prazo_atual} dias úteis")
                
                with st.form(key=f"form_p_{p['id']}"):
                    st.text_input("Número do Fornecedor", value=p['fornecedor_id'], disabled=True)
                    
                    # Campo para editar emails adicionais
                    emails_adicionais_edit = st.text_input("E-mails Adicionais (separados por vírgula)", 
                                                         value=p.get('emails_adicionais', '') or '', 
                                                         key=f"p_emails_edit_{p['id']}",
                                                         help="Digite os emails adicionais separados por vírgula")
                    
                    regra_atual = p.get('regra_envio') or "Nenhuma"
                    dias_atuais = p.get('dias_envio') or ""
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        regra_edit = st.selectbox("Regra de Envio", ["Nenhuma", "Semanal", "Mensal (Dia Fixo)", "Quinzenal"], 
                                                 index=["Nenhuma", "Semanal", "Mensal (Dia Fixo)", "Quinzenal"].index(regra_atual), 
                                                 key=f"p_regra_edit_{p['id']}")
                    with col2:
                        tempo_vencimento_edit = st.selectbox("Prazo Pagamento", options=[3, 10], 
                                                            index=0 if prazo_atual == 3 else 1,
                                                            help="Prazo em dias úteis para pagamento",
                                                            key=f"p_tempo_venc_{p['id']}")
                    
                    dias_edit = ""
                    
                    if regra_edit == "Semanal":
                        dias_semana_list = list(DIAS_SEMANA_MAP.values())
                        index_sem = dias_semana_list.index(dias_atuais) if dias_atuais in dias_semana_list else 0
                        dias_edit = st.selectbox("Dia da Semana", dias_semana_list, index=index_sem, key=f"p_dia_sem_edit_{p['id']}")
                    elif regra_edit in ["Mensal (Dia Fixo)", "Quinzenal"]:
                        dias_edit = st.text_input("Dias do Mês", value=dias_atuais, key=f"p_dia_mes_edit_{p['id']}")

                    if st.form_submit_button("Salvar Alterações"):
                        db.update_prestador(p['id'], regra_edit, dias_edit, 
                                          emails_adicionais_edit.strip() if emails_adicionais_edit.strip() else None,
                                          tempo_vencimento_edit)
                        st.success("Dados do prestador atualizados!")
                        st.rerun()

    elif page == "Histórico de Envios":
        st.title("📚 Histórico de Lotes Enviados (Serviços)")
        status_filter = st.selectbox("Filtrar por Status", ["Todos", "Em Aberto", "Pago", "Cancelado", "N.F. RECEBIDA"])
        
        lotes_data = db.get_all_lotes_servico()
        
        if not lotes_data:
            st.info("Nenhum lote de serviço registrado ainda.")
        else:
            for lote in lotes_data:
                if status_filter != "Todos" and lote['status'] != status_filter:
                    continue
                
                # Determinar status do upload (API DV Processamento)
                upload_status_display = ""
                upload_emoji = ""
                import datetime as dt
                
                if lote.get('link_upload'):
                    # Link foi gerado pela API
                    status_api = lote.get('status_api', 0)
                    validade_link = lote.get('validade_link')
                    
                    # Verificar se link expirou
                    link_expirado = False
                    if validade_link:
                        if isinstance(validade_link, str):
                            validade_dt = dt.datetime.strptime(validade_link, '%Y-%m-%d').date()
                        else:
                            validade_dt = validade_link
                        link_expirado = validade_dt < dt.date.today()
                    
                    if status_api == 1:
                        upload_emoji = "✅"
                        upload_status_display = "N.F. RECEBIDA VIA UPLOAD"
                    elif link_expirado:
                        upload_emoji = "⏰"
                        upload_status_display = "Link de upload expirado"
                    else:
                        upload_emoji = "📤"
                        upload_status_display = "Link enviado ao prestador"
                else:
                    upload_emoji = "📧"
                    upload_status_display = "Aguardando N.F. (sem link)"
                
                with st.container():
                    st.markdown("---")
                    cols = st.columns([1, 2, 1, 1, 1])
                    cols[0].text(f"Lote #{lote['id']}")
                    cols[1].text(lote['prestador_nome'])
                    cols[2].text(f"R$ {lote['valor_total']:.2f}")
                    cols[3].text(lote['data_envio'].strftime('%d/%m/%Y'))
                    cols[4].markdown(f"**{lote['status']}**")

                    with st.expander("Ver O.S. do Lote e Gerenciar"):
                        # Informações do Upload
                        st.markdown("### 📤 Status do Upload da Nota Fiscal")
                        
                        col_upload1, col_upload2 = st.columns([1, 3])
                        
                        with col_upload1:
                            st.markdown(f"## {upload_emoji}")
                        
                        with col_upload2:
                            st.markdown(f"**{upload_status_display}**")
                            
                            if lote.get('link_upload'):
                                # Mostrar ID de controle da API
                                if lote.get('id_controle'):
                                    st.caption(f"ID Controle API: {lote['id_controle']}")
                                
                                # Mostrar validade do link
                                if lote.get('validade_link'):
                                    validade = lote['validade_link']
                                    if isinstance(validade, str):
                                        validade_dt = dt.datetime.strptime(validade, '%Y-%m-%d').date()
                                    else:
                                        validade_dt = validade
                                    
                                    dias_restantes = (validade_dt - dt.date.today()).days
                                    if dias_restantes < 0:
                                        st.error(f"⏰ Link expirou em {validade_dt.strftime('%d/%m/%Y')}")
                                    elif dias_restantes == 0:
                                        st.warning(f"⚠️ Link expira HOJE!")
                                    elif dias_restantes <= 3:
                                        st.warning(f"⚠️ Link expira em {dias_restantes} dia(s) - {validade_dt.strftime('%d/%m/%Y')}")
                                    else:
                                        st.info(f"✅ Válido até: {validade_dt.strftime('%d/%m/%Y')} ({dias_restantes} dias)")
                                
                                # Mostrar link com botão para copiar
                                st.markdown("---")
                                st.markdown("**🔗 Link de Upload da Nota Fiscal:**")
                                st.code(lote['link_upload'], language="text")
                                if st.button("📋 Copiar Link", key=f"copy_upload_{lote['id']}"):
                                    st.info("Link exibido acima - use Ctrl+C para copiar")
                                
                                # Mostrar mensagem da API se houver
                                if lote.get('api_message'):
                                    st.caption(f"💬 {lote['api_message']}")
                                
                                # Botão para reenviar link (gerar novo)
                                if lote.get('status_api', 0) == 0:
                                    if st.button("🔄 Reenviar para API (Gerar Novo Link)", key=f"resend_api_{lote['id']}"):
                                        try:
                                            from api_upload_client import enviar_lote_para_api
                                            
                                            with st.spinner("Reenviando para API..."):
                                                # Limpar id_controle para permitir reenvio
                                                conn = db.get_db_connection()
                                                with conn.cursor() as cur:
                                                    cur.execute('UPDATE lotes_servico SET id_controle = NULL WHERE id = %s', (lote['id'],))
                                                conn.commit()
                                                conn.close()
                                                
                                                sucesso, mensagem, dados = enviar_lote_para_api(lote['id'])
                                                
                                                if sucesso:
                                                    st.success(f"✅ {mensagem}")
                                                    if dados and dados.get('link'):
                                                        st.info(f"🔗 Novo link: {dados['link']}")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ {mensagem}")
                                        
                                        except Exception as e:
                                            st.error(f"❌ Erro: {str(e)}")
                                
                                # Se já recebeu, mostrar info do arquivo
                                if lote.get('nota_fiscal_path'):
                                    nota_path = Path(lote['nota_fiscal_path'])
                                    if nota_path.exists():
                                        st.success(f"✅ Arquivo salvo em: {lote['nota_fiscal_path']}")
                                        
                                        with open(nota_path, "rb") as f:
                                            st.download_button(
                                                label="⬇️ Baixar Nota Fiscal (Upload)",
                                                data=f,
                                                file_name=nota_path.name,
                                                mime="application/pdf",
                                                key=f"download_upload_nf_{lote['id']}"
                                            )
                            else:
                                # Link ainda não foi gerado
                                st.warning("⚠️ Link de upload ainda não foi gerado pela API")
                                
                                if st.button("🚀 Enviar para API Agora", key=f"send_api_{lote['id']}"):
                                    try:
                                        from api_upload_client import enviar_lote_para_api
                                        
                                        with st.spinner("Enviando para API..."):
                                            sucesso, mensagem, dados = enviar_lote_para_api(lote['id'])
                                            
                                            if sucesso:
                                                st.success(f"✅ {mensagem}")
                                                if dados and dados.get('link'):
                                                    st.info(f"🔗 Link: {dados['link']}")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {mensagem}")
                                    
                                    except Exception as e:
                                        st.error(f"❌ Erro: {str(e)}")
                        
                        # Seção de Arquivos Recebidos
                        if lote.get('status_arquivo', 0) >= 1 and lote.get('arquivos_nf'):
                            st.markdown("---")
                            st.markdown("### 📁 Arquivos da Nota Fiscal Recebidos")
                            
                            try:
                                import json
                                arquivos_data = lote['arquivos_nf']
                                
                                # Se for string JSON, converter
                                if isinstance(arquivos_data, str):
                                    arquivos_data = json.loads(arquivos_data)
                                
                                arquivos = arquivos_data.get('arquivos', [])
                                stats = arquivos_data.get('estatisticas', {})
                                data_consulta = arquivos_data.get('data_consulta', '')
                                
                                if arquivos:
                                    # Estatísticas
                                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                                    with col_stat1:
                                        st.metric("📦 Total de Arquivos", stats.get('total_arquivos', len(arquivos)))
                                    with col_stat2:
                                        st.metric("💾 Tamanho Total", stats.get('total_tamanho_formatado', '-'))
                                    with col_stat3:
                                        if stats.get('ultimo_upload'):
                                            st.metric("📅 Último Upload", stats['ultimo_upload'].split()[0])
                                    
                                    # Lista de arquivos
                                    for i, arq in enumerate(arquivos, 1):
                                        with st.container():
                                            col_arq1, col_arq2 = st.columns([3, 1])
                                            
                                            with col_arq1:
                                                st.markdown(f"**{i}. {arq.get('nome_original', 'Arquivo')}**")
                                                st.caption(f"📊 {arq.get('tamanho_formatado', '-')} • {arq.get('tipo_arquivo', '-')} • Upload: {arq.get('data_upload', '-')}")
                                            
                                            with col_arq2:
                                                # Verificar se arquivo existe localmente
                                                import os
                                                caminho_local = os.path.join('uploads', f"lote_{lote['id']}", arq.get('nome_original', ''))
                                                
                                                if os.path.exists(caminho_local):
                                                    with open(caminho_local, 'rb') as f:
                                                        st.download_button(
                                                            label="⬇️ Download",
                                                            data=f,
                                                            file_name=arq.get('nome_original', 'arquivo'),
                                                            mime=arq.get('tipo_arquivo', 'application/octet-stream'),
                                                            key=f"download_nf_{lote['id']}_{i}"
                                                        )
                                                else:
                                                    st.caption("🌐 [Download Online](" + arq.get('link_download', '#') + ")")
                                    
                                    if data_consulta:
                                        st.caption(f"🕐 Última verificação: {data_consulta}")
                                
                                else:
                                    st.info("⏳ Aguardando envio de arquivos pelo prestador")
                            
                            except Exception as e:
                                st.error(f"❌ Erro ao exibir arquivos: {str(e)}")
                        
                        st.markdown("---")
                        
                        # Lista de O.S.
                        st.markdown("### 📋 Ordens de Serviço do Lote")
                        os_do_lote = db.get_os_by_lote_id(lote['id'])
                        if os_do_lote:
                            df_os = pd.DataFrame([item['detalhes'] for item in os_do_lote])
                            st.dataframe(df_os)
                        else:
                            st.warning("Não há O.S. detalhadas para este lote.")
                        
                        # N.F. anexada manualmente (método antigo)
                        if lote['anexo_path'] and not lote.get('nota_fiscal_path'):
                            st.markdown("---")
                            st.markdown("### 📎 Nota Fiscal Anexada Manualmente")
                            with open(lote['anexo_path'], "rb") as file:
                                st.download_button(
                                    label="⬇️ Baixar N.F. (Anexo Manual)", 
                                    data=file, 
                                    file_name=Path(lote['anexo_path']).name,
                                    key=f"download_manual_nf_{lote['id']}"
                                )
                        
                        st.markdown("---")
                        
                        # Gerenciamento do Lote
                        st.markdown("### ⚙️ Gerenciar Lote")
                        sub_cols = st.columns(2)
                        
                        with sub_cols[0]:
                            status_options = ["Em Aberto", "Pago", "Cancelado", "N.F. RECEBIDA"]
                            try: 
                                current_status_index = status_options.index(lote['status'])
                            except ValueError: 
                                current_status_index = 0
                            
                            new_status = st.selectbox("Alterar status do lote:", options=status_options, index=current_status_index, key=f"status_lote_{lote['id']}")
                            if st.button("Salvar Status", key=f"save_lote_{lote['id']}"):
                                db.update_lote_servico_status(lote['id'], new_status)
                                st.success(f"Status do Lote #{lote['id']} atualizado!")
                                st.rerun()
                        
                        with sub_cols[1]:
                            st.write("")
                            st.write("")
                            if st.button("🚨 Excluir Lote", key=f"del_lote_{lote['id']}"):
                                db.delete_lote_servico(lote['id'])
                                st.success(f"Lote #{lote['id']} e todas as suas O.S. foram excluídos!")
                                st.rerun()

    elif page == "Editor de PDF (Serviços)":
        st.title("📄 Editor de Template do PDF (Serviços)")
        template_path = Path("templates/invoice_template.html")
        html_content = template_path.read_text(encoding="utf-8")
        new_html_content = st.text_area("Código HTML", value=html_content, height=600)
        if st.button("Salvar Template"):
            template_path.write_text(new_html_content, encoding="utf-8")
            st.success("Template salvo!")

elif app_mode == "Pagamentos Vencidos":
    # Página de pagamentos vencidos
    pagina_pagamentos_vencidos()

elif app_mode == "Relatórios de Pagamentos":
    # Página de relatórios de pagamentos
    mostrar_pagina_relatorios()

elif app_mode == "Montagem (Montadores)":
    st.sidebar.divider()
    page = st.sidebar.radio("Navegar", ["Enviar Pagamentos", "Gerenciar Montadores", "Histórico de Montagens"])
    
    if page == "Enviar Pagamentos":
        st.title("Enviar Pagamentos de Montagem")
        input_method = st.tabs(["Lançamento Manual", "Importar via Excel"])
        df_para_envio_montagem = None

        with input_method[0]:
            st.header("Adicionar Montagem Manualmente")
            if 'manual_montagem_entries' not in st.session_state:
                st.session_state.manual_montagem_entries = []
                
            with st.form("manual_montagem_form", clear_on_submit=True):
                montadores = db.get_all_montadores(apenas_ativos=True)
                montador_map = {m['nome']: m['identificador'] for m in montadores}
                
                if not montador_map:
                    st.warning("Nenhum montador ativo cadastrado.")
                else:
                    montador_nome = st.selectbox("Montador", options=montador_map.keys())
                    boletim, data_montagem = st.text_input("Boletim Montagem"), st.date_input("Data da Montagem")
                    valor_venda = st.number_input("Média de Valor Venda (R$)", 0.0, format="%.2f")
                    cliente, produto = st.text_input("Cliente"), st.text_input("Nome do Produto")
                    
                    if st.form_submit_button("Adicionar à Lista"):
                        st.session_state.manual_montagem_entries.append({
                            "identificador_do_montador": montador_map[montador_nome], 
                            "identificador_boletim_montagem": boletim, 
                            "data_da_montagem": data_montagem, 
                            "media_de_valor_venda": valor_venda, 
                            "nome_do_cliente": cliente, 
                            "nome_produto": produto, 
                            "nome_do_montador": montador_nome
                        })
                        
            if st.session_state.manual_montagem_entries:
                df_para_envio_montagem = pd.DataFrame(st.session_state.manual_montagem_entries)
                st.subheader("Lista para Envio")
                st.dataframe(df_para_envio_montagem[['nome_do_montador', 'identificador_boletim_montagem', 'media_de_valor_venda']])
                if st.button("Limpar Lista de Montagem"):
                    st.session_state.manual_montagem_entries = []
                    st.rerun()

        with input_method[1]:
            uploader = st.file_uploader("Carregue o relatório de montagem", type=["xlsx"])
            if uploader:
                df = pd.read_excel(uploader)
                df.columns = [re.sub(r"\W+", "_", c.strip()).lower() for c in df.columns]
                required_cols = ['identificador_do_montador', 'identificador_boletim_montagem', 'data_da_montagem', 'media_de_valor_venda', 'nome_produto']
                if not all(c in df.columns for c in required_cols):
                    st.error(f"Excel precisa das colunas: {', '.join(required_cols)}")
                else: 
                    df_para_envio_montagem = df
        
        st.divider()
        st.header("🚀 Processar e Disparar Pagamentos")
        
        if df_para_envio_montagem is not None and not df_para_envio_montagem.empty:
            df = df_para_envio_montagem
            df['identificador_boletim_montagem'] = df['identificador_boletim_montagem'].astype(str)
            df['identificador_do_montador'] = df['identificador_do_montador'].astype(str)
            df['data_da_montagem'] = pd.to_datetime(df['data_da_montagem'])
            
            all_boletins = df['identificador_boletim_montagem'].unique().tolist()
            sent_boletins = db.check_boletim_list(all_boletins)
            blacklisted_boletins = db.check_boletins_blacklist(all_boletins)
            
            def get_status(row):
                boletim = row['identificador_boletim_montagem']
                if boletim in blacklisted_boletins:
                    return "Na blacklist"
                elif boletim in sent_boletins:
                    return "Já enviado"
                return "Pendente"
            
            df['status_envio'] = df.apply(get_status, axis=1)
            st.dataframe(df[['identificador_do_montador', 'identificador_boletim_montagem', 'status_envio']])
            df_final = df[df['status_envio'] == 'Pendente']

            if df_final.empty:
                st.error("Nenhuma montagem nova para processar.")
            else:
                st.sidebar.divider()
                st.sidebar.title("⚙️ Configurações de E-mail (Montador)")
                
                default_subject_montador = "Relatório de Pagamento de Montagem - Período: {{periodo_relatorio}}"
                default_body_montador = """Olá, {{nome_montador}},

Segue em anexo o seu relatório de pagamento de montagens referente ao período de **{{periodo_relatorio}}**.

📎 **Link para upload de documentos:** {{link}}

Qualquer dúvida, estamos à disposição."""

                mostrar_variaveis_disponiveis()
                st.text_input("CC (Montadores)", value=config.get("montador_cc", "projetos.qualidade@novomundo.com.br"), key="montador_cc", on_change=save_config)
                st.text_input("Assunto (Montadores)", value=config.get("montador_subject", default_subject_montador), key="montador_subject", on_change=save_config)
                st.text_area("Corpo do E-mail (Montadores)", value=config.get("montador_body", default_body_montador), key="montador_body", on_change=save_config, height=200)
                
                # 📱 Opção de enviar WhatsApp
                enviar_whatsapp_montador = st.checkbox("📱 Enviar notificação por WhatsApp também?", value=True, help="Se ativado, enviará WhatsApp junto com o email (conforme templates configurados em Automação WhatsApp)")
                
                if st.button("▶️ PROCESSAR E ENVIAR E-MAILS", type="primary"):
                    report_summary = []
                    cc_list_montador = [e.strip() for e in st.session_state.montador_cc.split(",") if e.strip()]
                    
                    # Criar placeholder para feedback em tempo real
                    progress_placeholder = st.empty()
                    status_placeholder = st.empty()
                    
                    with st.spinner("Processando e enviando..."):
                        for idx, (montador_id_str, group) in enumerate(df_final.groupby('identificador_do_montador'), 1):
                            total_montadores = len(df_final['identificador_do_montador'].unique())
                            progress_placeholder.progress(idx / total_montadores, f"Processando montador {idx}/{total_montadores}...")
                            
                            montador_info = db.get_montador_by_identificador(montador_id_str)
                            if not montador_info:
                                report_summary.append({"Montador ID": montador_id_str, "Status": "❌ Não cadastrado"})
                                continue
                            
                            group['comissao_calculada'] = group['media_de_valor_venda'] * montador_info['percentual_comissao']
                            total_comissao = float(group['comissao_calculada'].sum())
                            semanas_trabalhadas = group['data_da_montagem'].dt.isocalendar().week.nunique()
                            total_auxilio = float(semanas_trabalhadas * montador_info['auxilio_semanal'])
                            total_geral = total_comissao + total_auxilio
                            items_para_pdf = []
                            
                            for _, row in group.iterrows():
                                # Garantir que data_da_montagem é datetime antes de formatar
                                data_montagem = row['data_da_montagem']
                                if pd.notna(data_montagem):
                                    if isinstance(data_montagem, (int, float)):
                                        # Se ainda for número do Excel, converter
                                        from datetime import datetime, timedelta
                                        base_date = datetime(1899, 12, 30)
                                        data_montagem = (base_date + timedelta(days=float(data_montagem))).strftime('%d/%m/%Y')
                                    elif hasattr(data_montagem, 'strftime'):
                                        data_montagem = data_montagem.strftime('%d/%m/%Y')
                                    else:
                                        data_montagem = str(data_montagem)
                                else:
                                    data_montagem = '-'
                                
                                items_para_pdf.append({
                                    'boletim': row['identificador_boletim_montagem'], 
                                    'data_montagem': data_montagem,
                                    'cliente': row.get('nome_do_cliente', '-'), 
                                    'nome_produto': row.get('nome_produto', '-'), 
                                    'valor_venda': row['media_de_valor_venda'], 
                                    'comissao_calculada': row['comissao_calculada'], 
                                    'comissao_editada': None, 
                                    'adicional': 0.0
                                })
                            
                            periodo_relatorio = f"{group['data_da_montagem'].min().strftime('%d/%m/%Y')} - {group['data_da_montagem'].max().strftime('%d/%m/%Y')}"
                            
                            # ✅ VERIFICAR SE JÁ EXISTE ENVIO ANTES DE PROCESSAR
                            from check_montagem_exists import check_montagem_exists
                            
                            if check_montagem_exists(montador_info['id'], periodo_relatorio):
                                report_summary.append({"Montador": montador_info['nome'], "Status": "❌ Já existe envio para este período"})
                                continue
                            
                            # 1️⃣ Criar contexto inicial e salvar no banco (para gerar link)
                            ctx_inicial = {
                                "nome_montador": montador_info['nome'], 
                                "periodo_relatorio": periodo_relatorio, 
                                "percentual_comissao": montador_info['percentual_comissao'] * 100, 
                                "items": items_para_pdf, 
                                "total_comissao": total_comissao, 
                                "total_adicionais": 0, 
                                "total_auxilio": total_auxilio, 
                                "total_geral": total_geral
                            }
                            
                            # 2️⃣ Salvar no banco e gerar link automaticamente
                            status_placeholder.info(f"⏳ Gerando link para {montador_info['nome']}...")
                            envio_id = db.log_sent_montagem(montador_info['id'], ctx_inicial, "temp_conversation_id")
                            
                            # 3️⃣ AGUARDAR o link ser gerado pela API (polling com timeout)
                            link_gerado = ''
                            max_tentativas = 15  # 15 tentativas = até 15 segundos
                            tentativa = 0
                            
                            status_placeholder.info(f"⏳ Aguardando API gerar o link para {montador_info['nome']}...")
                            while tentativa < max_tentativas and not link_gerado:
                                time.sleep(1)
                                tentativa += 1
                                envio_salvo = db.get_envio_montagem_by_id(envio_id)
                                if envio_salvo and envio_salvo.get('link_upload'):
                                    link_gerado = envio_salvo['link_upload']
                                    status_placeholder.success(f"✅ Link obtido em {tentativa}s: {link_gerado[:40]}...")
                                    time.sleep(0.5)  # Pausa para mostrar mensagem
                                    break
                                else:
                                    status_placeholder.warning(f"⏳ Aguardando link... ({tentativa}/{max_tentativas}s)")
                            
                            if not link_gerado:
                                status_placeholder.error(f"⚠️ AVISO: Link não foi gerado após {max_tentativas}s. Email será enviado sem link.")
                                time.sleep(1)
                            
                            # 4️⃣ Atualizar contexto com o link
                            ctx = ctx_inicial.copy()
                            ctx['link'] = link_gerado if link_gerado else "⚠️ Link em processamento - consulte o histórico em alguns instantes"
                            
                            # 5️⃣ Gerar PDF
                            template = Template(Path("templates/montador_template.html").read_text(encoding="utf-8"))
                            html_pdf = template.render(**ctx)
                            
                            # Lazy import do weasyprint (só quando necessário para gerar PDF)
                            import os
                            os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')
                            from weasyprint import HTML
                            pdf_bytes = HTML(string=html_pdf, base_url="templates").write_pdf()
                            
                            # 6️⃣ Preparar email com templates (agora com link disponível)
                            subj_template = Template(st.session_state.montador_subject)
                            body_template = Template(st.session_state.montador_body)
                            subj = subj_template.render(**ctx)
                            body_plain = body_template.render(**ctx)
                            body_html = convert_plain_text_to_html(body_plain)

                            # 7️⃣ Obter todos os emails do montador (principal + adicionais)
                            montador_emails = db.get_montador_emails(montador_info)
                            recipients = [{"emailAddress": {"address": email}} for email in montador_emails]

                            # 8️⃣ Montar payload do email
                            message_data = {
                                "subject": subj,
                                "body": {"contentType": "HTML", "content": body_html},
                                "toRecipients": recipients,
                                "attachments": [{"@odata.type": "#microsoft.graph.fileAttachment", "name": f"Relatorio_Montagem_{montador_info['nome']}.pdf", "contentBytes": base64.b64encode(pdf_bytes).decode()}]
                            }
                            
                            if cc_list_montador:
                                message_data["ccRecipients"] = [{"emailAddress": {"address": cc}} for cc in cc_list_montador]
                            
                            final_payload = { "message": message_data, "saveToSentItems": "true" }

                            # 9️⃣ ENVIAR EMAIL
                            status_placeholder.info(f"📧 Enviando email para {montador_info['nome']}...")
                            resp = requests.post("https://graph.microsoft.com/v1.0/me/sendMail", headers={"Authorization": f"Bearer {st.session_state.access_token}", "Content-Type": "application/json"}, json=final_payload)
                                
                            if resp.status_code == 202:
                                time.sleep(2)
                                headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                                sent_items_url = "https://graph.microsoft.com/v1.0/me/mailfolders/sentitems/messages?$top=1&$select=id,conversationId"
                                sent_resp = requests.get(sent_items_url, headers=headers).json()
                                message_id = sent_resp['value'][0]['id']
                                conversation_id = sent_resp['value'][0]['conversationId']
                                
                                # 🔟 Atualizar conversation_id no banco
                                conn = db.get_db_connection()
                                with conn.cursor() as cur:
                                    cur.execute('UPDATE envios_montagem SET conversation_id = %s WHERE id = %s', (conversation_id, envio_id))
                                conn.commit()
                                conn.close()
                                
                                status_msg = f"✅ Enviado"
                                if link_gerado:
                                    status_msg += f" com link ({link_gerado[:30]}...)"
                                else:
                                    status_msg += " ⚠️ SEM LINK (consulte histórico)"
                                
                                # 📱 Enviar WhatsApp se opção marcada
                                if enviar_whatsapp_montador:
                                    try:
                                        print(f"\n🔵 Iniciando envio WhatsApp para montador {montador_info['id']}")
                                        from whatsapp_triggers import WhatsAppAutomation
                                        wa_automation = WhatsAppAutomation()
                                        print(f"🔵 Chamando enviar_montador_email_enviado...")
                                        resultado_wa = wa_automation.enviar_montador_email_enviado(
                                            montador_info['id'],
                                            periodo_relatorio,
                                            total_geral,
                                            len(items_para_pdf)  # quantidade de OS/boletins
                                        )
                                        print(f"🔵 Resultado WhatsApp: {resultado_wa}")
                                        
                                        if resultado_wa.get("success"):
                                            status_msg += " 📱✅"
                                            print(f"✅ WhatsApp enviado com sucesso!")
                                        else:
                                            status_msg += f" 📱⚠️ ({resultado_wa.get('error', 'erro desconhecido')})"
                                            print(f"⚠️ WhatsApp não enviado: {resultado_wa.get('error')}")
                                    except Exception as e:
                                        import traceback
                                        print(f"❌ ERRO ao enviar WhatsApp: {str(e)}")
                                        print(f"❌ Traceback: {traceback.format_exc()}")
                                        status_msg += f" 📱❌ ({str(e)[:30]})"
                                    
                                report_summary.append({"Montador": montador_info['nome'], "Status": status_msg})
                                status_placeholder.success(f"✅ Email enviado para {montador_info['nome']}")
                            else:
                                report_summary.append({"Montador": montador_info['nome'], "Status": f"❌ Erro {resp.status_code} - {resp.text}"})
                                status_placeholder.error(f"❌ Erro ao enviar para {montador_info['nome']}")
                        
                        # Limpar placeholders ao final
                        progress_placeholder.empty()
                        status_placeholder.empty()
                                
                    st.subheader("📋 Relatório de Envio")
                    st.table(pd.DataFrame(report_summary))
                    st.session_state.manual_montagem_entries = []

    elif page == "Gerenciar Montadores":
        st.title("👷 Gerenciar Montadores")
        
        # Seção de Blacklist
        with st.expander("📋 Blacklist de Boletins"):
            st.subheader("Adicionar Boletins à Blacklist")
            cols = st.columns([2, 2, 1])
            
            with cols[0]:
                montadores = {m['nome']: m['id'] for m in db.get_all_montadores()}
                montador_selected = st.selectbox("Montador", options=list(montadores.keys()))
            
            with cols[1]:
                boletins_input = st.text_input("Números dos Boletins (separados por vírgula)")
            
            with cols[2]:
                motivo = st.text_input("Motivo (opcional)")
            
            if st.button("Adicionar à Blacklist"):
                if boletins_input and montador_selected:
                    montador_id = montadores[montador_selected]
                    boletins = [b.strip() for b in boletins_input.split(",")]
                    for boletim in boletins:
                        success, message = db.adicionar_boletim_blacklist(montador_id, boletim, motivo)
                        st.toast(f"Boletim {boletim}: {message}")
                    st.rerun()
                else:
                    st.warning("Selecione um montador e insira os números dos boletins.")
            
            st.divider()
            st.subheader("Boletins na Blacklist")
            boletins_blacklist = db.get_boletins_blacklist()
            
            if not boletins_blacklist:
                st.info("Nenhum boletim na blacklist.")
            else:
                for b in boletins_blacklist:
                    cols = st.columns([2, 2, 2, 1])
                    cols[0].text(b['montador_nome'])
                    cols[1].text(f"Boletim: {b['boletim']}")
                    cols[2].text(f"Motivo: {b['motivo'] or '-'}")
                    if cols[3].button("🗑️", key=f"del_blacklist_{b['id']}"):
                        db.remover_boletim_blacklist(b['montador_id'], b['boletim'])
                        st.success(f"Boletim {b['boletim']} removido da blacklist!")
                        st.rerun()
        
        st.divider()
        
        with st.form("novo_montador_form", clear_on_submit=True):
            st.subheader("Adicionar Novo Montador")
            nome = st.text_input("Nome Completo")
            identificador = st.text_input("Identificador do Montador (ID único)")
            fornecedor_id = st.text_input("Número do Fornecedor")
            email = st.text_input("E-mail Principal")
            emails_adicionais = st.text_input("E-mails Adicionais (separados por vírgula)", 
                                            help="Digite os emails adicionais separados por vírgula. Ex: email2@empresa.com, email3@empresa.com")
            
            col1, col2 = st.columns(2)
            with col1:
                percentual_comissao = st.number_input("Comissão (%)", 0.0, 100.0, 5.0, 0.1, "%.2f")
            with col2:
                auxilio_semanal = st.number_input("Auxílio Semanal (R$)", 0.0, value=100.0, step=10.0, format="%.2f")
            
            col3, col4 = st.columns([2, 1])
            with col3:
                regra_envio = st.selectbox("Regra de Envio", ["Nenhuma", "Semanal", "Mensal (Dia Fixo)", "Quinzenal"], key="m_regra")
            with col4:
                tempo_vencimento_dias = st.selectbox("Prazo Pagamento", options=[3, 10], index=1,
                                                    help="Prazo em dias úteis para pagamento após recebimento da NF")
            
            dias_envio = ""
            
            if regra_envio == "Semanal":
                dias_envio = st.selectbox("Dia da Semana", list(DIAS_SEMANA_MAP.values()), key="m_dia_sem")
            elif regra_envio in ["Mensal (Dia Fixo)", "Quinzenal"]:
                dias_envio = st.text_input("Dias do Mês (ex: 5 ou 5,20)", key="m_dia_mes")

            if st.form_submit_button("Adicionar"):
                if all([nome, identificador, email, fornecedor_id]):
                    success, message = db.add_montador(nome, identificador, email, percentual_comissao / 100.0, auxilio_semanal, 
                                                      fornecedor_id, regra_envio, dias_envio, 
                                                      emails_adicionais.strip() if emails_adicionais.strip() else None,
                                                      tempo_vencimento_dias)
                    st.toast(message)
                else:
                    st.warning("Todos os campos obrigatórios devem ser preenchidos (Nome, Identificador, E-mail Principal e Número do Fornecedor).")
                    
        st.divider()
        st.subheader("Montadores Cadastrados")
        
        for m in db.get_all_montadores():
            with st.expander(f"{m['nome']} ({'Ativo' if m['ativo'] else 'Inativo'}) - ID: {m['id']}"):
                # Informações básicas do montador
                st.info(f"**ID do Montador:** {m['id']} | **Identificador:** {m['identificador']}")
                
                # Mostrar emails atuais
                st.info(f"**E-mail Principal:** {m['email']}")
                if m.get('emails_adicionais'):
                    emails_extras = [email.strip() for email in m['emails_adicionais'].split(',') if email.strip()]
                    st.info(f"**E-mails Adicionais:** {', '.join(emails_extras)}")
                
                # Mostrar prazo de pagamento atual
                prazo_atual = m.get('tempo_vencimento_dias', 10)
                st.info(f"**⏰ Prazo de Pagamento:** {prazo_atual} dias úteis")
                
                with st.form(key=f"form_montador_{m['id']}"):
                    # Permitir edição do número do fornecedor
                    fornecedor_id = st.text_input("Número do Fornecedor", value=m['fornecedor_id'], key=f"fornecedor_{m['id']}")
                    email = st.text_input("E-mail Principal", value=m['email'], key=f"email_{m['id']}")
                    
                    # Campo para editar emails adicionais
                    emails_adicionais_edit = st.text_input("E-mails Adicionais (separados por vírgula)", 
                                                         value=m.get('emails_adicionais', '') or '', 
                                                         key=f"m_emails_edit_{m['id']}",
                                                         help="Digite os emails adicionais separados por vírgula")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        comissao = st.number_input("Comissão (%)", value=m['percentual_comissao'] * 100, key=f"com_{m['id']}")
                    with col2:
                        auxilio = st.number_input("Auxílio Semanal (R$)", value=m['auxilio_semanal'], key=f"aux_{m['id']}")
                    with col3:
                        ativo = st.toggle("Ativo", value=m['ativo'], key=f"ativo_{m['id']}")
                    
                    regra_atual = m.get('regra_envio') or "Nenhuma"
                    dias_atuais = m.get('dias_envio') or ""
                    
                    col4, col5 = st.columns([2, 1])
                    with col4:
                        regra_edit = st.selectbox("Regra de Envio", ["Nenhuma", "Semanal", "Mensal (Dia Fixo)", "Quinzenal"], 
                                                 index=["Nenhuma", "Semanal", "Mensal (Dia Fixo)", "Quinzenal"].index(regra_atual), 
                                                 key=f"m_regra_edit_{m['id']}")
                    with col5:
                        tempo_vencimento_edit = st.selectbox("Prazo Pagamento", options=[3, 10],
                                                            index=0 if prazo_atual == 3 else 1,
                                                            help="Prazo em dias úteis para pagamento",
                                                            key=f"m_tempo_venc_{m['id']}")
                    
                    dias_edit = ""
                    
                    if regra_edit == "Semanal":
                        dias_semana_list = list(DIAS_SEMANA_MAP.values())
                        index_sem = dias_semana_list.index(dias_atuais) if dias_atuais in dias_semana_list else 0
                        dias_edit = st.selectbox("Dia da Semana", dias_semana_list, index=index_sem, key=f"m_dia_sem_edit_{m['id']}")
                    elif regra_edit in ["Mensal (Dia Fixo)", "Quinzenal"]:
                        dias_edit = st.text_input("Dias do Mês", value=dias_atuais, key=f"m_dia_mes_edit_{m['id']}")

                    if st.form_submit_button("Salvar Alterações"):
                        db.update_montador(m['id'], email, comissao / 100.0, auxilio, ativo, regra_edit, dias_edit, 
                                         fornecedor_id, 
                                         emails_adicionais_edit.strip() if emails_adicionais_edit.strip() else None,
                                         tempo_vencimento_edit)
                        st.success(f"Dados de {m['nome']} atualizados!")
                        st.rerun()
                
                # Histórico de montagens do montador
                st.divider()
                st.subheader(f"📋 Histórico de Montagens - {m['nome']}")
                
                historico_montador = db.get_montagens_by_montador_id(m['id'])
                
                if not historico_montador:
                    st.info("Nenhuma montagem enviada ainda para este montador.")
                else:
                    st.write(f"**Total de envios:** {len(historico_montador)}")
                    
                    # Mostrar resumo dos últimos envios
                    for idx, envio in enumerate(historico_montador[:3]):  # Mostra apenas os 3 mais recentes
                        details = envio.get('detalhes', {})
                        cols = st.columns([2, 2, 1, 1])
                        
                        cols[0].text(f"📅 {envio['data_envio'].strftime('%d/%m/%Y')}")
                        cols[1].text(f"Período: {details.get('periodo_relatorio', 'N/A')}")
                        cols[2].text(f"R$ {details.get('total_geral', 0):.2f}")
                        cols[3].markdown(f"**{envio['status']}**")
                    
                    if len(historico_montador) > 3:
                        st.write(f"... e mais {len(historico_montador) - 3} envios anteriores.")
                    
                    # Botão para ver histórico completo
                    if st.button(f"Ver Histórico Completo", key=f"hist_{m['id']}"):
                        st.session_state[f"show_full_history_{m['id']}"] = True
                    
                    # Mostrar histórico completo se solicitado
                    if st.session_state.get(f"show_full_history_{m['id']}", False):
                        st.markdown("#### Histórico Completo")
                        
                        for envio in historico_montador:
                            details = envio.get('detalhes', {})
                            
                            with st.container():
                                st.markdown("---")
                                cols = st.columns([2, 2, 1, 1, 1])
                                cols[0].text(f"📅 {envio['data_envio'].strftime('%d/%m/%Y')}")
                                cols[1].text(f"Período: {details.get('periodo_relatorio', 'N/A')}")
                                cols[2].text(f"R$ {details.get('total_geral', 0):.2f}")
                                cols[3].markdown(f"**{envio['status']}**")
                                
                                # Mostrar detalhes dos boletins
                                if details and 'items' in details:
                                    # Usar checkbox para controlar a visualização
                                    show_boletins = st.checkbox(f"👁️ Ver {len(details['items'])} boletins", key=f"show_boletins_{envio['id']}")
                                    
                                    if show_boletins:
                                        df_boletins = pd.DataFrame(details['items'])
                                        st.dataframe(df_boletins[['boletim', 'data_montagem', 'valor_venda', 'comissao_calculada']])
                        
                        if st.button(f"Ocultar Histórico", key=f"hide_hist_{m['id']}"):
                            st.session_state[f"show_full_history_{m['id']}"] = False
                            st.rerun()

    elif page == "Histórico de Montagens":
        st.title("📚 Histórico e Status de Pagamentos (Montagem)")
        status_filter = st.selectbox("Filtrar por Status", ["Todos", "Em Aberto", "Pago", "Cancelado", "N.F. RECEBIDA"])
        
        history_data = db.get_all_sent_montagens()

        if not history_data:
            st.info("Nenhum pagamento de montador registrado ainda.")
        else:
            for item in history_data:
                details = item['detalhes']
                if status_filter != "Todos" and item['status'] != status_filter:
                    continue

                montador_info = db.get_montador_by_id(item['montador_id'])
                
                with st.container():
                    st.markdown("---")
                    cols = st.columns([2, 2, 1, 1, 1])
                    cols[0].text(montador_info['nome'] if montador_info else "Montador não encontrado")
                    
                    if details:
                        cols[1].text(f"Período: {details.get('periodo_relatorio', 'N/A')}")
                        cols[2].text(f"R$ {details.get('total_geral', 0):.2f}")
                    else:
                        cols[1].text("Período: N/A"), cols[2].text("R$ N/A")

                    cols[3].text(item['data_envio'].strftime('%d/%m/%Y'))
                    cols[4].markdown(f"**{item['status']}**")

                    with st.expander("Ver Detalhes e Gerenciar"):
                        # Informações do Upload (igual ao módulo de prestadores)
                        st.markdown("### 📤 Status do Upload da Nota Fiscal")
                        
                        # Determinar status do upload
                        upload_status_display = ""
                        upload_emoji = ""
                        import datetime as dt
                        
                        if item.get('link_upload'):
                            # Link foi gerado pela API
                            status_api = item.get('status_api', 0)
                            validade_link = item.get('validade_link')
                            
                            # Verificar se link expirou
                            link_expirado = False
                            if validade_link:
                                if isinstance(validade_link, str):
                                    validade_dt = dt.datetime.strptime(validade_link, '%Y-%m-%d').date()
                                else:
                                    validade_dt = validade_link
                                link_expirado = validade_dt < dt.date.today()
                            
                            if status_api == 1:
                                upload_emoji = "✅"
                                upload_status_display = "N.F. RECEBIDA VIA UPLOAD"
                            elif link_expirado:
                                upload_emoji = "⏰"
                                upload_status_display = "Link de upload expirado"
                            else:
                                upload_emoji = "📤"
                                upload_status_display = "Link enviado ao montador"
                        else:
                            upload_emoji = "📧"
                            upload_status_display = "Aguardando N.F. (sem link)"
                        
                        col_upload1, col_upload2 = st.columns([1, 3])
                        
                        with col_upload1:
                            st.markdown(f"## {upload_emoji}")
                        
                        with col_upload2:
                            st.markdown(f"**{upload_status_display}**")
                            
                            if item.get('link_upload'):
                                # Mostrar ID de controle da API
                                if item.get('id_controle'):
                                    st.caption(f"ID Controle API: {item['id_controle']}")
                                
                                # Mostrar validade do link
                                if item.get('validade_link'):
                                    validade = item['validade_link']
                                    if isinstance(validade, str):
                                        validade_dt = dt.datetime.strptime(validade, '%Y-%m-%d').date()
                                    else:
                                        validade_dt = validade
                                    
                                    dias_restantes = (validade_dt - dt.date.today()).days
                                    if dias_restantes < 0:
                                        st.error(f"⏰ Link expirou em {validade_dt.strftime('%d/%m/%Y')}")
                                    elif dias_restantes == 0:
                                        st.warning(f"⚠️ Link expira HOJE!")
                                    elif dias_restantes <= 3:
                                        st.warning(f"⚠️ Link expira em {dias_restantes} dia(s) - {validade_dt.strftime('%d/%m/%Y')}")
                                    else:
                                        st.info(f"✅ Válido até: {validade_dt.strftime('%d/%m/%Y')} ({dias_restantes} dias)")
                                
                                # Mostrar link com botão para copiar
                                st.markdown("---")
                                st.markdown("**🔗 Link de Upload da Nota Fiscal:**")
                                st.code(item['link_upload'], language="text")
                                if st.button("📋 Copiar Link", key=f"copy_upload_mont_{item['id']}"):
                                    st.info("Link exibido acima - use Ctrl+C para copiar")
                                
                                # Mostrar mensagem da API se houver
                                if item.get('api_message'):
                                    st.caption(f"💬 {item['api_message']}")
                                
                                # Botão para reenviar link (gerar novo)
                                if item.get('status_api', 0) == 0:
                                    if st.button("🔄 Reenviar para API (Gerar Novo Link)", key=f"resend_api_mont_{item['id']}"):
                                        try:
                                            from api_upload_client import APIUploadClient
                                            
                                            with st.spinner("Reenviando para API..."):
                                                # Limpar id_controle para permitir reenvio
                                                conn = db.get_db_connection()
                                                with conn.cursor() as cur:
                                                    cur.execute('UPDATE envios_montagem SET id_controle = NULL WHERE id = %s', (item['id'],))
                                                conn.commit()
                                                conn.close()
                                                
                                                client = APIUploadClient()
                                                sucesso, mensagem, dados = client.enviar_e_salvar(item['id'], tipo='montagem')
                                                
                                                if sucesso:
                                                    st.success(f"✅ {mensagem}")
                                                    if dados and dados.get('link'):
                                                        st.info(f"🔗 Novo link: {dados['link']}")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ {mensagem}")
                                        
                                        except Exception as e:
                                            st.error(f"❌ Erro: {str(e)}")
                                
                                # Se já recebeu, mostrar info do arquivo
                                if item.get('nota_fiscal_path'):
                                    nota_path = Path(item['nota_fiscal_path'])
                                    if nota_path.exists():
                                        st.success(f"✅ Arquivo salvo em: {item['nota_fiscal_path']}")
                                        
                                        with open(nota_path, "rb") as f:
                                            st.download_button(
                                                label="⬇️ Baixar Nota Fiscal (Upload)",
                                                data=f,
                                                file_name=nota_path.name,
                                                mime="application/pdf",
                                                key=f"download_upload_nf_mont_{item['id']}"
                                            )
                            else:
                                # Link ainda não foi gerado
                                st.warning("⚠️ Link de upload ainda não foi gerado pela API")
                                
                                if st.button("🚀 Enviar para API Agora", key=f"send_api_mont_{item['id']}"):
                                    try:
                                        from api_upload_client import APIUploadClient
                                        
                                        with st.spinner("Enviando para API..."):
                                            client = APIUploadClient()
                                            sucesso, mensagem, dados = client.enviar_e_salvar(item['id'], tipo='montagem')
                                            
                                            if sucesso:
                                                st.success(f"✅ {mensagem}")
                                                if dados and dados.get('link'):
                                                    st.info(f"🔗 Novo link gerado: {dados['link']}")
                                                    st.caption(f"Válido até: {dados.get('validade_link', 'N/A')}")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {mensagem}")
                                    
                                    except Exception as e:
                                        st.error(f"❌ Erro: {str(e)}")
                        
                        st.markdown("---")
                        
                        # Seção de edição de boletins
                        if details:
                            df_items = pd.DataFrame(details.get('items', []))
                            if 'comissao_editada' not in df_items.columns: 
                                df_items['comissao_editada'] = None
                            if 'adicional' not in df_items.columns: 
                                df_items['adicional'] = 0.0
                            
                            st.markdown("##### Editar Boletins")
                            edited_df = st.data_editor(df_items, key=f"editor_{item['id']}", disabled=['boletim', 'data_montagem', 'cliente', 'nome_produto', 'valor_venda', 'comissao_calculada'])
                            
                            if st.button("Salvar Alterações nos Boletins", key=f"save_details_{item['id']}"):
                                new_details = details.copy()
                                new_details['items'] = edited_df.to_dict('records')
                                
                                total_comissao_final = sum(row.get('comissao_editada') if pd.notna(row.get('comissao_editada')) and row.get('comissao_editada') is not None else row.get('comissao_calculada', 0) for row in new_details['items'])
                                total_adicionais = sum(row.get('adicional', 0) for row in new_details['items'])
                                new_details['total_comissao'] = total_comissao_final
                                new_details['total_adicionais'] = total_adicionais
                                new_details['total_geral'] = total_comissao_final + total_adicionais + new_details.get('total_auxilio', 0)
                                
                                db.update_montagem_details(item['id'], new_details)
                                st.success("Detalhes do pagamento atualizados!")
                                st.rerun()

                        else: 
                            st.warning("Não há detalhes salvos.")
                        
                        if item.get('anexo_path'):
                            with open(item['anexo_path'], "rb") as file:
                                st.download_button(label="📥 Baixar Anexo do Email", data=file, file_name=Path(item['anexo_path']).name, key=f"download_anexo_mont_{item['id']}")

                        st.markdown("---")
                        sub_cols = st.columns(2)
                        
                        with sub_cols[0]:
                            status_options = ["Em Aberto", "Pago", "Cancelado", "N.F. RECEBIDA"]
                            try: 
                                current_status_index = status_options.index(item['status'])
                            except ValueError: 
                                current_status_index = 0
                                
                            new_status = st.selectbox("Alterar status:", options=status_options, index=current_status_index, key=f"status_mont_{item['id']}")
                            if st.button("Salvar Status", key=f"save_status_mont_{item['id']}"):
                                db.update_montagem_status(item['id'], new_status)
                                st.success(f"Status atualizado!")
                                st.rerun()
                                
                        with sub_cols[1]:
                            st.write("")
                            st.write("")
                            if st.button("🚨 Excluir Pagamento", key=f"del_mont_{item['id']}"):
                                db.delete_envio_montagem(item['id'])
                                st.success("Pagamento excluído!")
                                st.rerun()

elif app_mode == "Upload de Notas Fiscais":
    st.title("Sistema de Upload de Notas Fiscais")
    
    st.markdown("""
    ### Como Funciona o Sistema de Upload
    
    1. **Disparo de Lote**: Quando um lote de serviços é enviado por email, um link único é gerado automaticamente
    2. **Prestador Acessa**: O prestador recebe o link no email e pode fazer upload da nota fiscal
    3. **Consulta Automática**: O sistema verifica periodicamente se o arquivo foi enviado
    4. **Download Automático**: Quando disponível, o arquivo é baixado e vinculado ao lote
    """)
    
    st.divider()
    
    # Tabs para organizar
    tab1, tab2, tab3 = st.tabs(["📊 Status dos Uploads", "📋 Histórico Completo", "⚙️ Configurações da API"])
    
    with tab1:
        st.header("📊 Status Atual dos Uploads")
        
        # Filtros
        col1, col2 = st.columns([2, 1])
        
        with col1:
            status_filter = st.selectbox(
                "Filtrar por Status:",
                ["Todos", "pending", "completed", "expired", "failed"]
            )
        
        with col2:
            ordenar_por = st.selectbox(
                "Ordenar por:",
                ["Mais Recentes", "Mais Antigos", "Prestador"]
            )
        
        # Buscar lotes com upload
        lotes_com_upload = []
        for lote in db.get_all_lotes_servico():
            if lote.get('upload_token'):
                if status_filter == "Todos" or lote.get('upload_status') == status_filter:
                    lotes_com_upload.append(lote)
        
        # Ordenar
        if ordenar_por == "Mais Recentes":
            lotes_com_upload.sort(key=lambda x: x.get('data_envio', datetime.datetime.min), reverse=True)
        elif ordenar_por == "Mais Antigos":
            lotes_com_upload.sort(key=lambda x: x.get('data_envio', datetime.datetime.min))
        else:  # Prestador
            lotes_com_upload.sort(key=lambda x: x.get('prestador_nome', ''))
        
        if not lotes_com_upload:
            st.info("ℹ️ Nenhum lote com sistema de upload encontrado.")
            st.markdown("""
            **💡 Dica**: O sistema de upload é ativado automaticamente quando você:
            1. Dispara um lote de serviços com a API configurada
            2. O link único é gerado e enviado no email ao prestador
            """)
        else:
            # Estatísticas rápidas
            st.subheader("📈 Estatísticas")
            
            total_lotes = len(lotes_com_upload)
            pendentes = sum(1 for l in lotes_com_upload if l.get('upload_status') == 'pending')
            completos = sum(1 for l in lotes_com_upload if l.get('upload_status') == 'completed')
            expirados = sum(1 for l in lotes_com_upload if l.get('upload_status') == 'expired')
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Lotes", total_lotes)
            
            with col2:
                st.metric("⏳ Pendentes", pendentes, delta=f"{(pendentes/total_lotes*100):.0f}%" if total_lotes > 0 else "0%")
            
            with col3:
                st.metric("✅ Recebidos", completos, delta=f"{(completos/total_lotes*100):.0f}%" if total_lotes > 0 else "0%")
            
            with col4:
                st.metric("⏰ Expirados", expirados)
            
            st.divider()
            
            # Lista de lotes
            st.subheader(f"📋 Lotes com Upload ({len(lotes_com_upload)})")
            
            for lote in lotes_com_upload:
                # Determinar cor do status
                status = lote.get('upload_status', 'pending')
                status_emoji = {
                    'pending': '⏳',
                    'completed': '✅',
                    'expired': '⏰',
                    'failed': '❌'
                }.get(status, '❓')
                
                status_label = {
                    'pending': 'Aguardando Upload',
                    'completed': 'Nota Fiscal Recebida',
                    'expired': 'Link Expirado',
                    'failed': 'Falha no Upload'
                }.get(status, 'Desconhecido')
                
                with st.container():
                    st.markdown("---")
                    
                    # Linha principal
                    cols = st.columns([1, 2, 2, 2, 1])
                    
                    cols[0].markdown(f"### Lote #{lote['id']}")
                    cols[1].markdown(f"**{lote['prestador_nome']}**")
                    cols[2].text(f"Período: {lote.get('periodo', 'N/A')}")
                    cols[3].text(f"Enviado: {lote['data_envio'].strftime('%d/%m/%Y %H:%M')}")
                    cols[4].markdown(f"### {status_emoji}")
                    
                    # Detalhes do upload
                    with st.expander(f"{status_emoji} {status_label} - Ver Detalhes"):
                        col_info1, col_info2 = st.columns(2)
                        
                        with col_info1:
                            st.markdown("**📊 Informações do Lote**")
                            st.text(f"ID do Lote: {lote['id']}")
                            st.text(f"Prestador: {lote['prestador_nome']}")
                            st.text(f"Valor Total: R$ {lote['valor_total']:.2f}")
                            st.text(f"Data Envio: {lote['data_envio'].strftime('%d/%m/%Y %H:%M:%S')}")
                        
                        with col_info2:
                            st.markdown("**📤 Informações do Upload**")
                            st.text(f"Status: {status_label}")
                            st.text(f"Token: {lote.get('upload_token', 'N/A')[:20]}...")
                            
                            if lote.get('upload_url'):
                                st.markdown(f"**Link de Upload:**")
                                st.code(lote['upload_url'], language="text")
                                
                                # Botão para copiar link
                                if st.button("📋 Copiar Link", key=f"copy_link_{lote['id']}"):
                                    st.code(lote['upload_url'])
                                    st.success("✅ Link copiado! (Ctrl+C para copiar da caixa acima)")
                        
                        st.divider()
                        
                        # Ações disponíveis
                        st.markdown("**🔧 Ações**")
                        
                        col_action1, col_action2, col_action3 = st.columns(3)
                        
                        with col_action1:
                            if status == 'pending':
                                if st.button("🔄 Consultar Status Agora", key=f"check_{lote['id']}", use_container_width=True):
                                    try:
                                        from upload_api_client import upload_api
                                        
                                        with st.spinner("Consultando API..."):
                                            success, result = upload_api.consultar_status(lote['upload_token'])
                                            
                                            if success:
                                                novo_status = result.get('status')
                                                st.info(f"Status da API: {novo_status}")
                                                
                                                # Atualizar no banco
                                                db.atualizar_status_upload(lote['id'], novo_status)
                                                
                                                if novo_status == 'completed':
                                                    st.success("✅ Nota fiscal disponível! Baixando arquivo...")
                                                    
                                                    # Fazer download
                                                    save_path = Path("uploads") / f"nota_fiscal_lote_{lote['id']}.pdf"
                                                    save_path.parent.mkdir(exist_ok=True)
                                                    
                                                    download_success, file_path = upload_api.download_arquivo(
                                                        lote['upload_token'],
                                                        str(save_path)
                                                    )
                                                    
                                                    if download_success:
                                                        db.salvar_nota_fiscal(lote['id'], file_path)
                                                        st.success(f"✅ Arquivo salvo em: {file_path}")
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Erro ao baixar arquivo: {file_path}")
                                                else:
                                                    st.rerun()
                                            else:
                                                st.error(f"❌ Erro na consulta: {result.get('message', 'Erro desconhecido')}")
                                    
                                    except ImportError:
                                        st.error("❌ Cliente de API não disponível. Verifique se upload_api_client.py existe.")
                                    except Exception as e:
                                        st.error(f"❌ Erro: {str(e)}")
                        
                        with col_action2:
                            if lote.get('nota_fiscal_path'):
                                nota_path = Path(lote['nota_fiscal_path'])
                                if nota_path.exists():
                                    with open(nota_path, "rb") as f:
                                        st.download_button(
                                            label="⬇️ Baixar N.F.",
                                            data=f,
                                            file_name=nota_path.name,
                                            mime="application/pdf",
                                            key=f"download_nf_{lote['id']}",
                                            use_container_width=True
                                        )
                                else:
                                    st.warning("Arquivo não encontrado")
                        
                        with col_action3:
                            if st.button("🔗 Reenviar Link", key=f"resend_{lote['id']}", use_container_width=True):
                                st.info("💡 Funcionalidade em desenvolvimento. Por enquanto, copie o link acima e envie manualmente.")
    
    with tab2:
        st.header("📋 Histórico Completo de Uploads")
        
        # Buscar todos os lotes
        todos_lotes = db.get_all_lotes_servico()
        
        # Filtrar lotes com upload
        lotes_historico = [l for l in todos_lotes if l.get('upload_token')]
        
        if not lotes_historico:
            st.info("Nenhum histórico de upload disponível.")
        else:
            # Criar dataframe para histórico
            historico_data = []
            
            for lote in lotes_historico:
                status = lote.get('upload_status', 'pending')
                status_label = {
                    'pending': '⏳ Pendente',
                    'completed': '✅ Recebido',
                    'expired': '⏰ Expirado',
                    'failed': '❌ Falha'
                }.get(status, '❓ Desconhecido')
                
                historico_data.append({
                    "Lote": f"#{lote['id']}",
                    "Prestador": lote['prestador_nome'],
                    "Período": lote.get('periodo', 'N/A'),
                    "Data Envio": lote['data_envio'].strftime('%d/%m/%Y'),
                    "Status Upload": status_label,
                    "Nota Fiscal": "✅ Sim" if lote.get('nota_fiscal_path') else "❌ Não",
                    "Valor": f"R$ {lote['valor_total']:.2f}"
                })
            
            df_historico = pd.DataFrame(historico_data)
            
            # Mostrar dataframe
            st.dataframe(
                df_historico,
                use_container_width=True,
                hide_index=True
            )
            
            # Exportar para Excel
            st.divider()
            
            if st.button("📊 Exportar para Excel"):
                import io
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_historico.to_excel(writer, index=False, sheet_name='Histórico Uploads')
                
                output.seek(0)
                
                st.download_button(
                    label="⬇️ Download Relatório Excel",
                    data=output,
                    file_name=f"historico_uploads_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    with tab3:
        st.header("⚙️ Configurações da API de Upload")
        
        st.markdown("""
        ### 🔗 Integração com Sistema Externo
        
        Configure aqui a URL da API e a chave de autenticação fornecidas pelo desenvolvedor
        do sistema externo que gerencia os uploads das notas fiscais.
        """)
        
        st.divider()
        
        # Verificar se a API está configurada
        load_dotenv()
        api_url_atual = os.getenv("UPLOAD_API_URL", "")
        api_key_atual = os.getenv("UPLOAD_API_KEY", "")
        
        # Status da configuração
        if not api_url_atual or not api_key_atual:
            st.warning("⚠️ API de Upload não configurada!")
        else:
            st.success("✅ API Configurada!")
        
        st.subheader("📝 Configurar Credenciais da API")
        
        with st.form("config_api_form"):
            st.markdown("**Preencha as informações fornecidas pelo desenvolvedor do sistema externo:**")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                api_url_input = st.text_input(
                    "🔗 URL da API",
                    value=api_url_atual,
                    placeholder="https://api-externa.novomundo.com.br",
                    help="URL base da API do sistema externo (sem barra no final)"
                )
            
            with col2:
                mostrar_api_key = st.checkbox("Mostrar API Key", value=False)
            
            if mostrar_api_key:
                api_key_input = st.text_input(
                    "🔑 API Key (Chave de Autenticação)",
                    value=api_key_atual,
                    placeholder="nmrj_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    help="Chave de autenticação fornecida pelo sistema externo"
                )
            else:
                # Mascarar a chave atual
                if api_key_atual and len(api_key_atual) > 8:
                    masked_key = f"{api_key_atual[:4]}{'*' * (len(api_key_atual) - 8)}{api_key_atual[-4:]}"
                else:
                    masked_key = "*" * len(api_key_atual) if api_key_atual else ""
                
                api_key_input = st.text_input(
                    "🔑 API Key (Chave de Autenticação)",
                    value=api_key_atual,
                    placeholder="nmrj_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    help="Chave de autenticação fornecida pelo sistema externo",
                    type="password"
                )
            
            st.markdown("---")
            
            col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])
            
            with col_btn1:
                submit_button = st.form_submit_button("� Salvar Configurações", type="primary", use_container_width=True)
            
            with col_btn2:
                clear_button = st.form_submit_button("🗑️ Limpar Configurações", use_container_width=True)
            
            with col_btn3:
                st.markdown("")  # Espaço
        
        # Processar formulário
        if submit_button:
            if not api_url_input or not api_key_input:
                st.error("❌ Por favor, preencha todos os campos!")
            else:
                # Salvar no arquivo .env
                env_path = Path(".env")
                
                # Ler .env existente ou criar novo
                env_vars = {}
                if env_path.exists():
                    with open(env_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                env_vars[key] = value.strip('"').strip("'")
                
                # Atualizar variáveis
                env_vars["UPLOAD_API_URL"] = api_url_input.rstrip("/")
                env_vars["UPLOAD_API_KEY"] = api_key_input
                
                # Escrever de volta
                with open(env_path, "w") as f:
                    for key, value in env_vars.items():
                        f.write(f'{key}="{value}"\n')
                
                st.success("✅ Configurações salvas com sucesso!")
                st.info("🔄 Recarregando variáveis de ambiente...")
                
                # Recarregar .env
                load_dotenv(override=True)
                
                time.sleep(1)
                st.rerun()
        
        if clear_button:
            # Remover do .env
            env_path = Path(".env")
            
            if env_path.exists():
                env_vars = {}
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            if key not in ["UPLOAD_API_URL", "UPLOAD_API_KEY"]:
                                env_vars[key] = value.strip('"').strip("'")
                
                with open(env_path, "w") as f:
                    for key, value in env_vars.items():
                        f.write(f'{key}="{value}"\n')
            
            st.success("✅ Configurações removidas!")
            time.sleep(1)
            st.rerun()
        
        st.divider()
        
        # Exibir configuração atual (somente leitura)
        if api_url_atual or api_key_atual:
            st.subheader("📊 Configuração Atual")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔗 URL da API**")
                if api_url_atual:
                    st.code(api_url_atual, language="text")
                else:
                    st.text("Não configurada")
            
            with col2:
                st.markdown("**🔑 API Key**")
                if api_key_atual:
                    # Mascarar a chave
                    if len(api_key_atual) > 8:
                        masked_key = f"{api_key_atual[:4]}{'*' * (len(api_key_atual) - 8)}{api_key_atual[-4:]}"
                    else:
                        masked_key = "*" * len(api_key_atual)
                    st.code(masked_key, language="text")
                else:
                    st.text("Não configurada")
            
            st.divider()
            
            # Testar conexão
            st.subheader("🔍 Testar Conexão com a API")
            
            if st.button("🚀 Testar Conexão", type="primary"):
                try:
                    from upload_api_client import upload_api
                    
                    with st.spinner("Testando conexão..."):
                        if upload_api.verificar_conexao():
                            st.success("✅ Conexão com a API está funcionando!")
                        else:
                            st.error("❌ Não foi possível conectar à API. Verifique a URL e a chave.")
                
                except ImportError:
                    st.error("❌ Cliente de API não encontrado. Verifique se upload_api_client.py existe.")
                except Exception as e:
                    st.error(f"❌ Erro ao testar conexão: {str(e)}")
            
            st.divider()
            
            # Job de consulta automática
            st.subheader("🤖 Consulta Automática")
            
            st.markdown("""
            **Job de Consulta Automática de Notas Fiscais**
            
            O sistema possui um job (`job_consultar_notas.py`) que verifica automaticamente
            se os prestadores fizeram o upload das notas fiscais.
            
            **Para ativar a consulta automática:**
            
            ```bash
            # Configurar cron para executar a cada hora
            crontab -e
            
            # Adicionar esta linha:
            0 * * * * cd /caminho/projeto && source .venv/bin/activate && python job_consultar_notas.py >> logs/consulta_notas.log 2>&1
            ```
            
            **Ou executar manualmente:**
            ```bash
            python job_consultar_notas.py
            ```
            """)
            
            if st.button("▶️ Executar Consulta Manual Agora"):
                st.info("💡 Execute o comando no terminal: `python job_consultar_notas.py`")
            
            st.divider()
            
            # Documentação
            st.subheader("📚 Documentação")
            
            docs_disponiveis = {
                "API_UPLOAD_NOTAS_ESPECIFICACAO.md": "Especificação completa da API para o desenvolvedor externo",
                "IMPLEMENTACAO_UPLOAD_NOTAS.md": "Guia de implementação e integração",
                "teste_upload_api.py": "Script de teste da API",
                "job_consultar_notas.py": "Job automático de consulta"
            }
            
            st.markdown("**Arquivos de Documentação:**")
            
            for arquivo, descricao in docs_disponiveis.items():
                arquivo_path = Path(arquivo)
                if arquivo_path.exists():
                    col_doc1, col_doc2 = st.columns([3, 1])
                    col_doc1.text(f"📄 {arquivo}")
                    col_doc1.caption(descricao)
                    
                    with col_doc2:
                        if st.button("📖 Ver", key=f"doc_{arquivo}"):
                            with open(arquivo_path, "r", encoding="utf-8") as f:
                                st.code(f.read(), language="markdown" if arquivo.endswith(".md") else "python")

elif app_mode == "Jobs Automáticos":
    mostrar_painel_jobs()

elif app_mode == "WhatsApp":
    mostrar_painel_whatsapp()

elif app_mode == "Automação WhatsApp":
    mostrar_automacao_whatsapp()

elif app_mode == "Integrações":
    from painel_integracoes import mostrar_painel_integracoes
    mostrar_painel_integracoes()

elif app_mode == "Backups do Banco":
    st.title("Sistema de Backup do Banco de Dados")
    
    backup_dir = Path("backups")
    
    # Criar diretório se não existir
    if not backup_dir.exists():
        backup_dir.mkdir()
    
    # Tabs para organizar a interface
    tab1, tab2, tab3 = st.tabs(["📋 Listar Backups", "➕ Criar Backup", "⚙️ Configurações"])
    
    with tab1:
        st.header("📋 Backups Disponíveis")
        
        # Listar backups
        backups = sorted(backup_dir.glob("backup_*.sql"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not backups:
            st.info("📭 Nenhum backup encontrado. Crie seu primeiro backup!")
        else:
            st.success(f"✅ {len(backups)} backup(s) disponível(eis)")
            
            # Criar dataframe com informações dos backups
            backup_data = []
            for backup in backups:
                stat = backup.stat()
                size_mb = stat.st_size / (1024 * 1024)
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                
                backup_data.append({
                    "Arquivo": backup.name,
                    "Data/Hora": mtime.strftime("%d/%m/%Y %H:%M:%S"),
                    "Tamanho (MB)": f"{size_mb:.2f}",
                    "Caminho": str(backup)
                })
            
            df_backups = pd.DataFrame(backup_data)
            
            # Mostrar tabela
            st.dataframe(df_backups[["Arquivo", "Data/Hora", "Tamanho (MB)"]], use_container_width=True)
            
            st.divider()
            
            # Opções para cada backup
            st.subheader("🔧 Ações nos Backups")
            
            backup_selecionado = st.selectbox(
                "Selecione um backup:",
                options=[b.name for b in backups],
                format_func=lambda x: f"{x} - {next((b['Data/Hora'] for b in backup_data if b['Arquivo'] == x), '')}"
            )
            
            if backup_selecionado:
                backup_path = backup_dir / backup_selecionado
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Download backup
                    with open(backup_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Backup",
                            data=f,
                            file_name=backup_selecionado,
                            mime="application/octet-stream",
                            use_container_width=True
                        )
                
                with col2:
                    # Visualizar informações
                    if st.button("ℹ️ Ver Detalhes", use_container_width=True):
                        st.session_state.show_backup_details = backup_selecionado
                
                with col3:
                    # Excluir backup
                    if st.button("🗑️ Excluir Backup", use_container_width=True, type="secondary"):
                        st.session_state.confirmar_exclusao = backup_selecionado
                
                # Mostrar detalhes se solicitado
                if st.session_state.get('show_backup_details') == backup_selecionado:
                    st.info(f"""
                    **📊 Detalhes do Backup**
                    
                    - **Arquivo**: {backup_selecionado}
                    - **Caminho Completo**: {backup_path}
                    - **Tamanho**: {backup_path.stat().st_size / (1024 * 1024):.2f} MB
                    - **Criado em**: {datetime.datetime.fromtimestamp(backup_path.stat().st_mtime).strftime("%d/%m/%Y às %H:%M:%S")}
                    - **Formato**: PostgreSQL Custom Format (comprimido)
                    """)
                
                # Confirmação de exclusão
                if st.session_state.get('confirmar_exclusao') == backup_selecionado:
                    st.warning(f"⚠️ Tem certeza que deseja excluir o backup **{backup_selecionado}**?")
                    col_sim, col_nao = st.columns(2)
                    
                    with col_sim:
                        if st.button("✅ Sim, excluir", type="primary", use_container_width=True):
                            backup_path.unlink()
                            st.success(f"✅ Backup {backup_selecionado} excluído!")
                            del st.session_state.confirmar_exclusao
                            time.sleep(1)
                            st.rerun()
                    
                    with col_nao:
                        if st.button("❌ Cancelar", use_container_width=True):
                            del st.session_state.confirmar_exclusao
                            st.rerun()
    
    with tab2:
        st.header("➕ Criar Novo Backup")
        
        st.info("""
        💡 **Sobre os Backups**
        
        - Backups são criados no formato PostgreSQL Custom (comprimido)
        - Incluem todas as tabelas e dados do sistema
        - Podem ser restaurados usando `pg_restore` ou o script de backup
        """)
        
        if st.button("🚀 Criar Backup Agora", type="primary", use_container_width=True):
            with st.spinner("Criando backup..."):
                import subprocess
                
                # Gerar nome do backup
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"backup_email_{timestamp}.sql"
                
                try:
                    # Executar pg_dump
                    load_dotenv()
                    cmd = [
                        "pg_dump",
                        "-h", os.getenv("DB_HOST", "localhost"),
                        "-p", os.getenv("DB_PORT", "5432"),
                        "-U", os.getenv("DB_USER", "davidgabriel"),
                        "-F", "c",  # Formato custom (comprimido)
                        "-b",  # Incluir large objects
                        "-f", str(backup_file),
                        os.getenv("DB_NAME", "email")
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        size_mb = backup_file.stat().st_size / (1024 * 1024)
                        st.success(f"""
                        ✅ **Backup criado com sucesso!**
                        
                        - **Arquivo**: {backup_file.name}
                        - **Tamanho**: {size_mb:.2f} MB
                        - **Local**: {backup_file}
                        """)
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Erro ao criar backup: {result.stderr}")
                
                except Exception as e:
                    st.error(f"❌ Erro ao criar backup: {str(e)}")
        
        st.divider()
        
        # Backup manual via script
        st.subheader("📝 Backup via Terminal")
        st.code("""
# Criar backup manualmente
python backup_database.py --auto

# Ou usar o script rápido
./backup.sh
        """, language="bash")
    
    with tab3:
        st.header("⚙️ Configurações de Backup")
        
        # Importar o scheduler
        try:
            from backup_scheduler import scheduler
            scheduler_available = True
        except:
            scheduler_available = False
        
        # Configuração do agendamento automático
        st.subheader("🤖 Agendamento Automático de Backup")
        
        if not scheduler_available:
            st.warning("⚠️ Módulo de agendamento não disponível. Certifique-se de que backup_scheduler.py existe.")
        else:
            # Verificar agendamento atual
            current_schedule = scheduler.get_current_schedule()
            
            if current_schedule:
                st.success(f"✅ **Backup automático está ATIVO**")
                st.code(current_schedule, language="bash")
                
                # Tentar interpretar o agendamento
                parts = current_schedule.strip().split()
                if len(parts) >= 5:
                    cron_expr = " ".join(parts[:5])
                    descricao = scheduler.get_schedule_description(cron_expr)
                    st.info(f"📅 Frequência: **{descricao}**")
                
                if st.button("🗑️ Remover Agendamento", type="secondary"):
                    success, message = scheduler.remove_schedule()
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.info("ℹ️ Nenhum backup automático configurado")
            
            st.divider()
            
            # Configurar novo agendamento
            st.subheader("➕ Configurar Novo Agendamento")
            
            # Opções pré-definidas
            opcao_agendamento = st.selectbox(
                "Escolha a frequência:",
                [
                    "Personalizado",
                    "Diário às 3h da manhã",
                    "A cada 6 horas",
                    "A cada 12 horas",
                    "Toda segunda-feira às 2h",
                    "Todo domingo às 23h",
                    "De hora em hora"
                ]
            )
            
            # Mapeamento de opções para expressões cron
            cron_presets = {
                "Diário às 3h da manhã": "0 3 * * *",
                "A cada 6 horas": "0 */6 * * *",
                "A cada 12 horas": "0 */12 * * *",
                "Toda segunda-feira às 2h": "0 2 * * 1",
                "Todo domingo às 23h": "0 23 * * 0",
                "De hora em hora": "0 * * * *"
            }
            
            if opcao_agendamento == "Personalizado":
                st.markdown("""
                **Formato Cron:** `minuto hora dia mês dia_da_semana`
                
                Exemplos:
                - `0 3 * * *` - Todo dia às 3h
                - `0 */6 * * *` - A cada 6 horas
                - `30 2 * * 1` - Toda segunda às 2:30
                """)
                
                cron_expression = st.text_input(
                    "Expressão Cron:",
                    value="0 3 * * *",
                    help="Digite a expressão cron personalizada"
                )
            else:
                cron_expression = cron_presets[opcao_agendamento]
                st.code(cron_expression, language="bash")
                descricao = scheduler.get_schedule_description(cron_expression)
                st.info(f"📅 Será executado: **{descricao}**")
            
            # Caminho do script
            script_path = Path.cwd() / "backup_auto.sh"
            
            if not script_path.exists():
                st.warning(f"⚠️ Script backup_auto.sh não encontrado em {script_path}")
            else:
                st.text_input("Script a executar:", value=str(script_path), disabled=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if st.button("💾 Salvar Agendamento", type="primary", use_container_width=True, disabled=not script_path.exists()):
                    success, message = scheduler.set_schedule(cron_expression, str(script_path))
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
            
            with col2:
                if st.button("ℹ️ Ajuda", use_container_width=True):
                    st.session_state.show_cron_help = not st.session_state.get('show_cron_help', False)
            
            # Ajuda sobre cron
            if st.session_state.get('show_cron_help', False):
                st.markdown("""
                ### � Guia de Expressões Cron
                
                **Formato:** `minuto hora dia mês dia_da_semana`
                
                **Valores:**
                - Minuto: 0-59
                - Hora: 0-23
                - Dia do mês: 1-31
                - Mês: 1-12
                - Dia da semana: 0-6 (0 = Domingo)
                
                **Caracteres especiais:**
                - `*` : qualquer valor
                - `/` : incremento (ex: */6 = a cada 6)
                - `,` : lista (ex: 1,3,5)
                - `-` : intervalo (ex: 1-5)
                
                **Exemplos:**
                - `0 3 * * *` - Todo dia às 3:00
                - `30 */2 * * *` - A cada 2 horas no minuto 30
                - `0 9-17 * * 1-5` - De hora em hora, das 9h às 17h, seg a sex
                - `0 0 1 * *` - Todo dia 1º do mês à meia-noite
                """)
        
        st.divider()
        
        # Informações sobre o sistema de backup
        st.markdown("""
        ### �📊 Política de Backups
        
        **Retenção de Backups:**
        - Máximo de backups mantidos: **30**
        - Backups mais antigos são automaticamente removidos
        - Backups podem ser baixados antes da exclusão
        
        **Frequência Recomendada:**
        - ✅ Diário: Para ambientes de produção
        - ✅ A cada 6 horas: Para dados críticos
        - ✅ Semanal: Para ambientes de teste
        """)
        
        st.divider()
        
        # Manual do crontab
        st.subheader("📝 Configuração Manual (Avançado)")
        
        with st.expander("📝 Ver instruções de configuração manual"):
            st.markdown("""
            Se preferir configurar manualmente no crontab:
            
            ```bash
            # Editar crontab
            crontab -e
            
            # Adicionar linha para backup diário às 3h
            0 3 * * * /Users/davidgabriel/projetos/disparador-email/backup_auto.sh
            ```
            
            **Outras frequências:**
            - A cada 6 horas: `0 */6 * * *`
            - Toda segunda às 2h: `0 2 * * 1`
            - De hora em hora: `0 * * * *`
            
            **Verificar crontab:**
            ```bash
            crontab -l
            ```
            """)
        
        st.divider()
        
        # Estatísticas
        st.subheader("📈 Estatísticas")
        
        total_backups = len(list(backup_dir.glob("backup_*.sql")))
        
        if total_backups > 0:
            backups_list = list(backup_dir.glob("backup_*.sql"))
            total_size = sum(b.stat().st_size for b in backups_list) / (1024 * 1024)
            oldest = min(backups_list, key=lambda x: x.stat().st_mtime)
            newest = max(backups_list, key=lambda x: x.stat().st_mtime)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Backups", total_backups)
            
            with col2:
                st.metric("Espaço Utilizado", f"{total_size:.2f} MB")
            
            with col3:
                avg_size = total_size / total_backups
                st.metric("Tamanho Médio", f"{avg_size:.2f} MB")
            
            st.markdown("---")
            
            st.info(f"""
            **📅 Backup mais antigo:** {oldest.name}  
            ({datetime.datetime.fromtimestamp(oldest.stat().st_mtime).strftime("%d/%m/%Y %H:%M")})
            
            **📅 Backup mais recente:** {newest.name}  
            ({datetime.datetime.fromtimestamp(newest.stat().st_mtime).strftime("%d/%m/%Y %H:%M")})
            """)
        else:
            st.warning("Nenhum backup encontrado para mostrar estatísticas.")
        
        st.divider()
        
        # Limpar backups antigos
        st.subheader("🧹 Manutenção")
        
        max_backups = st.number_input("Máximo de backups a manter:", min_value=5, max_value=100, value=30)
        
        if st.button("🧹 Limpar Backups Antigos", use_container_width=True):
            backups_list = sorted(backup_dir.glob("backup_*.sql"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(backups_list) > max_backups:
                backups_para_remover = backups_list[max_backups:]
                
                for backup in backups_para_remover:
                    backup.unlink()
                
                st.success(f"✅ {len(backups_para_remover)} backup(s) antigo(s) removido(s)! Mantidos os {max_backups} mais recentes.")
                time.sleep(1)
                st.rerun()
            else:
                st.info(f"✅ Nenhum backup removido. Total atual: {len(backups_list)}")
        
        # Informações sobre restauração
        st.divider()
        st.subheader("♻️ Como Restaurar um Backup")
        
        st.markdown("""
        **Via Interface Python:**
        ```bash
        python backup_database.py
        # Selecione opção 3 (Restaurar backup)
        ```
        
        **Via Terminal (pg_restore):**
        ```bash
        pg_restore -h localhost -p 5432 -U davidgabriel -d email -c -v backups/backup_email_XXXXXXXX_XXXXXX.sql
        ```
        
        ⚠️ **ATENÇÃO**: A restauração irá **substituir todos os dados** do banco atual!
        """)

