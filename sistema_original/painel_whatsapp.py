"""
Painel de controle WhatsApp para Streamlit
"""

import streamlit as st
import requests
from datetime import datetime


class WhatsAppClientSimple:
    """Cliente simples para o serviço WhatsApp"""
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
    
    def get_status(self):
        try:
            response = requests.get(f"{self.base_url}/status", timeout=2)
            return response.json()
        except:
            return {"status": "error", "error": "Serviço não está rodando"}
    
    def get_info(self):
        try:
            response = requests.get(f"{self.base_url}/info", timeout=2)
            return response.json()
        except:
            return {"success": False, "error": "Não foi possível obter informações"}
    
    def send_message(self, number, message):
        try:
            response = requests.post(
                f"{self.base_url}/send",
                json={"number": number, "message": message},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_bulk_messages(self, numbers, message, delay=3000):
        try:
            response = requests.post(
                f"{self.base_url}/send-bulk",
                json={"numbers": numbers, "message": message, "delay": delay},
                timeout=300
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}


def mostrar_painel_whatsapp():
    """Exibe o painel de controle do WhatsApp na interface"""
    
    # Debug - sempre mostrar algo
    st.title("WhatsApp")
    st.write("🔄 Carregando painel WhatsApp...")
    
    # Importar database aqui para evitar erros de importação circular
    try:
        import database as db
        db_disponivel = True
    except Exception as e:
        db_disponivel = False
        st.warning(f"⚠️ Banco de dados não disponível: {e}")
    
    # Criar cliente
    whatsapp = WhatsAppClientSimple()
    
    # Verificar status
    status = whatsapp.get_status()
    
    # Tabs principais
    tab_status, tab_enviar, tab_config = st.tabs([
        "🔌 Status & Conexão",
        "📤 Enviar Mensagens",
        "⚙️ Configurações"
    ])
    
    # ========== TAB STATUS ==========
    with tab_status:
        st.subheader("Status da Conexão")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if status.get("status") == "error":
                st.error("❌ **Serviço Offline**")
                st.warning("O serviço WhatsApp não está rodando!")
                with st.expander("Como iniciar o serviço?"):
                    st.code("""
# No terminal, execute:
npm start

# Ou use o script:
./start_whatsapp.sh
                    """, language="bash")
            elif status.get("status") == "connected":
                st.success("✅ **Conectado**")
            else:
                st.warning("⏳ **Aguardando Conexão**")
        
        with col2:
            if status.get("hasQrCode"):
                st.info("📱 **QR Code Disponível**")
                st.markdown("[🔍 Ver QR Code](http://localhost:3000/qr)")
            elif status.get("status") == "connected":
                st.success("🔗 **Autenticado**")
        
        with col3:
            if st.button("🔄 Atualizar Status", use_container_width=True):
                st.rerun()
        
        # Informações do usuário conectado
        if status.get("status") == "connected":
            st.divider()
            info = whatsapp.get_info()
            
            if info.get("success"):
                user_info = info.get("info", {})
                st.subheader("👤 Usuário Conectado")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Nome", user_info.get("name", "N/A"))
                col2.metric("Número", user_info.get("number", "N/A"))
                col3.metric("Plataforma", user_info.get("platform", "N/A").title())
        
        # Instruções
        if status.get("status") != "connected":
            st.divider()
            st.subheader("📱 Como Conectar")
            
            with st.expander("Ver instruções passo a passo"):
                st.markdown("""
                ### Passo 1: Inicie o serviço
                
                No terminal, execute:
                ```bash
                npm start
                ```
                
                ### Passo 2: Acesse o QR Code
                
                Abra em uma nova aba: [http://localhost:3000/qr](http://localhost:3000/qr)
                
                ### Passo 3: Escaneie com WhatsApp
                
                1. Abra o WhatsApp no celular
                2. Menu → Aparelhos conectados
                3. Conectar um aparelho
                4. Aponte a câmera para o QR Code
                
                ### Passo 4: Aguarde
                
                Volte aqui e clique em "Atualizar Status"
                """)
    
    # ========== TAB ENVIAR ==========
    with tab_enviar:
        if status.get("status") != "connected":
            st.warning("⚠️ WhatsApp não está conectado. Conecte primeiro na aba 'Status & Conexão'.")
        else:
            st.subheader("Enviar Mensagem")
            
            # Escolher tipo de envio
            tipo_envio = st.radio(
                "Tipo de Envio",
                ["📱 Número Manual", "👤 Prestador", "🔧 Montador", "📋 Lista (Múltiplos)"],
                horizontal=True
            )
            
            destinatarios = []
            nomes = []
            
            if tipo_envio == "📱 Número Manual":
                numero = st.text_input(
                    "Número do WhatsApp",
                    placeholder="5511999999999",
                    help="Digite com código do país + DDD + número"
                )
                if numero:
                    destinatarios = [numero]
                    nomes = ["Manual"]
            
            elif tipo_envio == "👤 Prestador" and db_disponivel:
                try:
                    prestadores = db.get_all_prestadores()
                    prestadores_com_tel = [p for p in prestadores if p.get('telefone')]
                    
                    if not prestadores_com_tel:
                        st.warning("Nenhum prestador com telefone cadastrado!")
                        st.info("Cadastre telefones na aba 'Configurações'")
                    else:
                        prestador_selecionado = st.selectbox(
                            "Selecione o Prestador",
                            options=prestadores_com_tel,
                            format_func=lambda x: f"{x['nome']} - {x.get('telefone', '')}"
                        )
                        if prestador_selecionado:
                            destinatarios = [prestador_selecionado.get('telefone')]
                            nomes = [prestador_selecionado['nome']]
                except Exception as e:
                    st.error(f"Erro ao carregar prestadores: {e}")
            
            elif tipo_envio == "🔧 Montador" and db_disponivel:
                try:
                    montadores = db.get_all_montadores()
                    montadores_com_tel = [m for m in montadores if m.get('telefone')]
                    
                    if not montadores_com_tel:
                        st.warning("Nenhum montador com telefone cadastrado!")
                        st.info("Cadastre telefones na aba 'Configurações'")
                    else:
                        montador_selecionado = st.selectbox(
                            "Selecione o Montador",
                            options=montadores_com_tel,
                            format_func=lambda x: f"{x['nome']} - {x.get('telefone', '')}"
                        )
                        if montador_selecionado:
                            destinatarios = [montador_selecionado.get('telefone')]
                            nomes = [montador_selecionado['nome']]
                except Exception as e:
                    st.error(f"Erro ao carregar montadores: {e}")
            
            elif tipo_envio == "📋 Lista (Múltiplos)":
                st.info("Digite um número por linha (com código do país)")
                numeros_texto = st.text_area(
                    "Lista de Números",
                    placeholder="5511999999999\n5511988888888\n5511977777777",
                    height=150
                )
                if numeros_texto:
                    destinatarios = [n.strip() for n in numeros_texto.split('\n') if n.strip()]
                    nomes = ["Manual"] * len(destinatarios)
                
                st.caption(f"📊 Total de números: {len(destinatarios)}")
            
            # Mensagem
            st.divider()
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                mensagem = st.text_area(
                    "Mensagem",
                    placeholder="Digite a mensagem...",
                    height=200,
                    help="Use *texto* para negrito e _texto_ para itálico"
                )
            
            with col2:
                st.markdown("**Formatação:**")
                st.markdown("""
                - `*negrito*`
                - `_itálico_`
                - `~riscado~`
                """)
                
                if len(destinatarios) > 1:
                    delay = st.number_input(
                        "Delay (segundos)",
                        min_value=2,
                        max_value=10,
                        value=3,
                        help="Tempo entre mensagens"
                    )
                else:
                    delay = 3
            
            # Botão enviar
            st.divider()
            if st.button("📤 Enviar Mensagem", type="primary", use_container_width=True):
                if not destinatarios:
                    st.error("❌ Selecione ao menos um destinatário!")
                elif not mensagem:
                    st.error("❌ Digite uma mensagem!")
                else:
                    with st.spinner("Enviando..."):
                        if len(destinatarios) == 1:
                            # Envio único
                            resultado = whatsapp.send_message(
                                number=destinatarios[0],
                                message=mensagem
                            )
                            
                            if resultado.get("success"):
                                st.success(f"✅ Mensagem enviada para {nomes[0]}!")
                            else:
                                st.error(f"❌ Erro: {resultado.get('error')}")
                        else:
                            # Envio em massa
                            resultado = whatsapp.send_bulk_messages(
                                numbers=destinatarios,
                                message=mensagem,
                                delay=delay * 1000  # Converter para milissegundos
                            )
                            
                            if resultado.get("success"):
                                enviados = resultado.get("sent", 0)
                                falhas = resultado.get("failed", 0)
                                
                                st.success(f"✅ Enviadas: {enviados}/{len(destinatarios)}")
                                
                                if falhas > 0:
                                    st.warning(f"⚠️ Falhas: {falhas}")
                                    
                                    with st.expander("Ver detalhes das falhas"):
                                        for item in resultado.get("results", []):
                                            if not item.get("success"):
                                                st.error(f"❌ {item['number']}: {item.get('error', 'Erro desconhecido')}")
                            else:
                                st.error(f"❌ Erro: {resultado.get('error')}")
    
    # ========== TAB CONFIGURAÇÕES ==========
    with tab_config:
        st.subheader("⚙️ Configurações")
        
        st.markdown("### 🔗 URLs do Serviço")
        col1, col2 = st.columns(2)
        with col1:
            st.code("http://localhost:3000/status")
            st.code("http://localhost:3000/qr")
        with col2:
            st.code("http://localhost:3000/info")
            st.code("http://localhost:3000/send")
        
        st.divider()
        
        st.markdown("### 📚 Documentação")
        
        docs = {
            "WHATSAPP_QUICKSTART.md": "Guia Rápido de Início",
            "WHATSAPP_INTEGRATION.md": "Documentação Completa",
            "WHATSAPP_LOCALIZACAO.md": "Onde Encontrar Cada Coisa"
        }
        
        for arquivo, descricao in docs.items():
            col1, col2 = st.columns([3, 1])
            col1.write(f"📄 **{arquivo}**")
            col1.caption(descricao)
            if col2.button("📖 Ver", key=f"doc_{arquivo}"):
                try:
                    with open(arquivo, "r", encoding="utf-8") as f:
                        st.code(f.read(), language="markdown")
                except:
                    st.error(f"Arquivo {arquivo} não encontrado")
        
        st.divider()
        
        if db_disponivel:
            st.markdown("### 📱 Adicionar Telefones")
            
            tab_prest, tab_mont = st.tabs(["Prestadores", "Montadores"])
            
            with tab_prest:
                try:
                    prestadores = db.get_all_prestadores()
                    prestadores_sem_tel = [p for p in prestadores if not p.get('telefone')]
                    
                    if prestadores_sem_tel:
                        st.warning(f"⚠️ {len(prestadores_sem_tel)} prestador(es) sem telefone")
                        
                        for p in prestadores_sem_tel[:10]:  # Mostrar até 10
                            col1, col2, col3 = st.columns([2, 2, 1])
                            col1.write(p['nome'])
                            telefone = col2.text_input(
                                "Telefone",
                                key=f"tel_prest_{p['id']}",
                                placeholder="5511999999999",
                                label_visibility="collapsed"
                            )
                            if col3.button("💾", key=f"save_prest_{p['id']}"):
                                if telefone:
                                    try:
                                        conn = db.get_db_connection()
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            "UPDATE prestadores SET telefone = %s WHERE id = %s",
                                            (telefone, p['id'])
                                        )
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ Salvo!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro: {e}")
                    else:
                        st.success("✅ Todos têm telefone cadastrado!")
                except Exception as e:
                    st.error(f"Erro: {e}")
            
            with tab_mont:
                try:
                    montadores = db.get_all_montadores()
                    montadores_sem_tel = [m for m in montadores if not m.get('telefone')]
                    
                    if montadores_sem_tel:
                        st.warning(f"⚠️ {len(montadores_sem_tel)} montador(es) sem telefone")
                        
                        for m in montadores_sem_tel[:10]:  # Mostrar até 10
                            col1, col2, col3 = st.columns([2, 2, 1])
                            col1.write(m['nome'])
                            telefone = col2.text_input(
                                "Telefone",
                                key=f"tel_mont_{m['id']}",
                                placeholder="5511999999999",
                                label_visibility="collapsed"
                            )
                            if col3.button("💾", key=f"save_mont_{m['id']}"):
                                if telefone:
                                    try:
                                        conn = db.get_db_connection()
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            "UPDATE montadores SET telefone = %s WHERE id = %s",
                                            (telefone, m['id'])
                                        )
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ Salvo!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro: {e}")
                    else:
                        st.success("✅ Todos têm telefone cadastrado!")
                except Exception as e:
                    st.error(f"Erro: {e}")
