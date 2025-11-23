"""
Serviço de Integração com Trello
Baseado no sistema original: sistema_original/trello_integration.py
"""

import requests
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.database import get_db_connection
from app.services.trello_card_crud import TrelloCardCRUD


class TrelloIntegration:
    """
    Cliente para integração com a API do Trello
    
    Funcionalidades:
    - Criar cards quando arquivos são baixados
    - Anexar informações do lote ao card
    - Adicionar labels personalizadas
    - Criar checklists automáticas
    """
    
    def __init__(self):
        """Inicializa a integração com as credenciais do banco"""
        self.config = self._load_config()
        self.api_key = self.config.get('trello_api_key')
        self.token = self.config.get('trello_token')
        self.board_id = self.config.get('trello_board_id')
        self.list_id = self.config.get('trello_list_id')
        self.base_url = 'https://api.trello.com/1'
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do Trello do banco de dados"""
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            try:
                cur.execute("""
                    SELECT 
                        trello_api_key, 
                        trello_token, 
                        trello_board_id, 
                        trello_list_id,
                        trello_ativo
                    FROM integracoes_config 
                    WHERE id = 1
                """)
                
                result = cur.fetchone()
                
                if result:
                    return {
                        'trello_api_key': result[0],
                        'trello_token': result[1],
                        'trello_board_id': result[2],
                        'trello_list_id': result[3],
                        'trello_ativo': result[4]
                    }
                else:
                    return {
                        'trello_api_key': None,
                        'trello_token': None,
                        'trello_board_id': None,
                        'trello_list_id': None,
                        'trello_ativo': False
                    }
            except Exception as e:
                print(f"❌ Erro ao carregar config Trello: {e}")
                return {
                    'trello_api_key': None,
                    'trello_token': None,
                    'trello_board_id': None,
                    'trello_list_id': None,
                    'trello_ativo': False
                }
    
    def is_configured(self) -> bool:
        """Verifica se a integração está configurada"""
        return all([
            self.api_key,
            self.token,
            self.board_id,
            self.list_id,
            self.config.get('trello_ativo', False)
        ])
    
    def criar_card_download(
        self, 
        lote_id: Optional[int] = None,
        prestador_nome: Optional[str] = None,
        montador_nome: Optional[str] = None,
        arquivos_baixados: Optional[List[str]] = None,
        nota_fiscal: Optional[str] = None,
        arquivos_para_anexar: Optional[List[str]] = None,
        valor_lote: Optional[float] = None,
        envio_montagem_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cria um card no Trello quando arquivos são baixados
        GARANTE QUE NÃO HAVERÁ DUPLICAÇÃO
        
        Args:
            lote_id: ID do lote (opcional se for montador)
            prestador_nome: Nome do prestador (opcional)
            montador_nome: Nome do montador (opcional)
            arquivos_baixados: Lista de nomes dos arquivos baixados
            nota_fiscal: Número da nota fiscal (opcional)
            arquivos_para_anexar: Lista de caminhos de arquivos locais (opcional)
            valor_lote: Valor total do lote (opcional)
            envio_montagem_id: ID do envio de montagem (opcional)
            
        Returns:
            Dados do card criado ou None se falhar ou já existir
        """
        
        if not self.is_configured():
            print("⚠️  Integração Trello não configurada. Card não será criado.")
            return None
        
        # VERIFICAÇÃO CRÍTICA: Card já existe no banco?
        if lote_id and TrelloCardCRUD.card_existe_para_lote(lote_id):
            card_existente = TrelloCardCRUD.obter_card_lote(lote_id)
            print(f"⚠️  Card já existe para lote #{lote_id}: {card_existente.get('card_url')}")
            return None
        
        if envio_montagem_id and TrelloCardCRUD.card_existe_para_montador(envio_montagem_id):
            card_existente = TrelloCardCRUD.obter_card_montador(envio_montagem_id)
            print(f"⚠️  Card já existe para montador #{envio_montagem_id}: {card_existente.get('card_url')}")
            return None
        
        if arquivos_baixados is None:
            arquivos_baixados = []
        
        try:
            # Determinar o nome a ser usado no título
            nome_entidade = prestador_nome if prestador_nome else montador_nome
            
            # Monta o título do card com o valor
            if lote_id:
                prefixo = f"📦 Lote #{lote_id}"
            elif envio_montagem_id:
                prefixo = f"� Lote #{envio_montagem_id}"
            else:
                prefixo = "📦 Lote"

            if valor_lote and valor_lote > 0:
                titulo = f"{prefixo} - {nome_entidade} - R$ {valor_lote:,.2f}"
            else:
                titulo = f"{prefixo} - {nome_entidade}"
            
            # Monta a descrição do card
            descricao = self._montar_descricao(
                lote_id, 
                prestador_nome, 
                montador_nome, 
                arquivos_baixados, 
                nota_fiscal
            )
            
            # Cria o card via API com retry
            url = f"{self.base_url}/cards"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            data = {
                'idList': self.list_id,
                'name': titulo,
                'desc': descricao,
                'pos': 'top'
            }
            
            # Tentar até 3 vezes
            max_tentativas = 3
            timeouts = [30, 60, 90]
            
            card_id = None
            card_url = None
            
            for tentativa in range(max_tentativas):
                try:
                    print(f"🔄 Tentativa {tentativa + 1}/{max_tentativas} - Criando card no Trello...")
                    response = requests.post(
                        url, 
                        params=params, 
                        json=data,
                        timeout=timeouts[tentativa]
                    )
                    response.raise_for_status()
                    card_data = response.json()
                    card_id = card_data['id']
                    card_url = card_data['shortUrl']
                    print(f"✅ Card Trello criado: {card_url}")
                    break
                    
                except requests.exceptions.Timeout:
                    if tentativa < max_tentativas - 1:
                        print(f"⏱️  Timeout - Tentando novamente com timeout de {timeouts[tentativa + 1]}s...")
                        continue
                    else:
                        print(f"❌ Timeout após {max_tentativas} tentativas")
                        return None
                        
                except requests.exceptions.RequestException as e:
                    if tentativa < max_tentativas - 1:
                        print(f"⚠️  Erro: {e} - Tentando novamente...")
                        continue
                    else:
                        raise
            
            if not card_id:
                return None
            
            # Adiciona label
            self._adicionar_label(card_id, 'green')
            
            # Cria checklist
            if arquivos_baixados:
                self._criar_checklist(card_id, arquivos_baixados)
            
            # Enviar notificação de integração com Trello
            try:
                import asyncio
                from app.routes.notifications import notification_manager
                
                nome_entidade = prestador_nome if prestador_nome else montador_nome
                tipo_entidade = "Prestador" if prestador_nome else "Montador"
                
                # Criar e executar a tarefa assíncrona
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    notification_manager.send_notification(
                        tipo="info",
                        titulo="🔗 Integrado no Trello",
                        mensagem=f"{tipo_entidade} {nome_entidade} - Lote #{lote_id}",
                        dados={
                            "lote_id": lote_id,
                            "tipo": tipo_entidade.lower(),
                            "nome": nome_entidade,
                            "card_url": card_url,
                            "valor": valor_lote
                        }
                    )
                )
                loop.close()
                print(f"✅ Notificação Trello enviada: {nome_entidade}")
            except Exception as e:
                print(f"⚠️  Erro ao enviar notificação Trello: {e}")
                import traceback
                traceback.print_exc()
            
            # Anexa arquivos reais
            if arquivos_para_anexar:
                print(f"📎 Anexando {len(arquivos_para_anexar)} arquivo(s) ao card...")
                for idx, caminho in enumerate(arquivos_para_anexar, 1):
                    print(f"   [{idx}/{len(arquivos_para_anexar)}] Anexando: {os.path.basename(caminho)}")
                    self._anexar_arquivo(card_id, caminho)
            
            # Salva no banco usando CRUD (com verificação atômica)
            salvou = False
            if lote_id:
                salvou = TrelloCardCRUD.criar_card_lote(lote_id, card_id, card_url)
            elif envio_montagem_id:
                salvou = TrelloCardCRUD.criar_card_montador(envio_montagem_id, card_id, card_url)
            
            if not salvou:
                # Card duplicado foi criado no Trello mas não registrado no banco
                # Isso pode acontecer em race conditions
                print(f"⚠️  Card criado no Trello mas já existe no banco - possível duplicação")
                return None
            
            return {'id': card_id, 'shortUrl': card_url}
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao criar card no Trello: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro inesperado ao criar card: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _anexar_arquivo(self, card_id: str, caminho_arquivo: str) -> bool:
        """Faz upload de um arquivo real como anexo ao card do Trello"""
        
        if not os.path.isfile(caminho_arquivo):
            print(f"⚠️  Arquivo não encontrado: {caminho_arquivo}")
            return False

        print(f"   📊 Tamanho: {os.path.getsize(caminho_arquivo)} bytes")

        url = f"{self.base_url}/cards/{card_id}/attachments"
        params = {
            'key': self.api_key,
            'token': self.token
        }

        # Tentar até 2 vezes
        max_tentativas = 2
        
        for tentativa in range(max_tentativas):
            try:
                with open(caminho_arquivo, 'rb') as f:
                    files = {'file': (os.path.basename(caminho_arquivo), f)}
                    response = requests.post(
                        url, 
                        params=params, 
                        files=files,
                        timeout=120
                    )

                    if response.status_code == 200:
                        print(f"   ✅ Anexo enviado: {os.path.basename(caminho_arquivo)}")
                        return True
                    else:
                        print(f"   ❌ Falha ao anexar: {response.status_code}")
                        if tentativa < max_tentativas - 1:
                            continue
                        return False
                        
            except requests.exceptions.Timeout:
                print(f"   ⏱️  Timeout ao anexar arquivo")
                if tentativa < max_tentativas - 1:
                    continue
                return False
                
            except Exception as e:
                print(f"   ❌ Exceção ao anexar: {e}")
                if tentativa < max_tentativas - 1:
                    continue
                return False
        
        return False
    
    def _montar_descricao(
        self, 
        lote_id: int, 
        prestador_nome: Optional[str], 
        montador_nome: Optional[str], 
        arquivos_baixados: List[str],
        nota_fiscal: Optional[str]
    ) -> str:
        """Monta a descrição formatada do card"""
        
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        
        descricao = f"""## 📋 Informações do Lote

**Lote:** #{lote_id}
"""
        
        if prestador_nome:
            descricao += f"**Prestador:** {prestador_nome}\n"
        if montador_nome:
            descricao += f"**Montador:** {montador_nome}\n"
        
        descricao += f"**Data/Hora:** {data_hora}\n"
        
        if nota_fiscal:
            descricao += f"**Nota Fiscal:** {nota_fiscal}\n"
        
        descricao += f"\n## 📎 Arquivos Baixados ({len(arquivos_baixados)})\n\n"
        
        for i, arquivo in enumerate(arquivos_baixados, 1):
            descricao += f"{i}. `{arquivo}`\n"
        
        descricao += """
---
*Card criado automaticamente pelo Sistema de Disparador de Emails*
"""
        
        return descricao
    
    def _adicionar_label(self, card_id: str, cor: str = 'green'):
        """Adiciona uma label colorida ao card"""
        try:
            # Busca labels do board
            url = f"{self.base_url}/boards/{self.board_id}/labels"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            labels = response.json()
            
            # Encontra a label da cor desejada
            label_id = None
            for label in labels:
                if label['color'] == cor:
                    label_id = label['id']
                    break
            
            if label_id:
                url = f"{self.base_url}/cards/{card_id}/idLabels"
                params['value'] = label_id
                
                response = requests.post(url, params=params, timeout=30)
                response.raise_for_status()
                print(f"   🏷️  Label '{cor}' adicionada")
                
        except Exception as e:
            print(f"⚠️  Não foi possível adicionar label: {e}")
    
    def _criar_checklist(self, card_id: str, arquivos: List[str]):
        """Cria uma checklist no card com os arquivos baixados"""
        try:
            # Cria a checklist
            url = f"{self.base_url}/checklists"
            params = {
                'key': self.api_key,
                'token': self.token,
                'idCard': card_id,
                'name': 'Arquivos para Processar'
            }
            
            response = requests.post(url, params=params, timeout=30)
            response.raise_for_status()
            
            checklist_data = response.json()
            checklist_id = checklist_data['id']
            
            # Adiciona cada arquivo como item
            for arquivo in arquivos:
                url = f"{self.base_url}/checklists/{checklist_id}/checkItems"
                params = {
                    'key': self.api_key,
                    'token': self.token,
                    'name': arquivo
                }
                
                requests.post(url, params=params, timeout=30)
            
            print(f"   ✅ Checklist criada com {len(arquivos)} itens")
            
        except Exception as e:
            print(f"⚠️  Não foi possível criar checklist: {e}")
    
    def listar_boards(self) -> List[Dict[str, Any]]:
        """Lista todos os boards do usuário (útil para configuração)"""
        if not self.api_key or not self.token:
            raise ValueError("API Key e Token não configurados")
        
        try:
            url = f"{self.base_url}/members/me/boards"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("API Key ou Token inválidos")
            else:
                raise ValueError(f"Erro HTTP {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Erro ao conectar com Trello: {str(e)}")
    
    def listar_listas(self, board_id: str) -> List[Dict[str, Any]]:
        """Lista todas as listas de um board"""
        if not self.api_key or not self.token:
            raise ValueError("API Key e Token não configurados")
        
        try:
            url = f"{self.base_url}/boards/{board_id}/lists"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            raise ValueError(f"Erro ao listar listas: {str(e)}")
