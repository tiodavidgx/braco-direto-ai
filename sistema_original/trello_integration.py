"""
Integração com Trello
Cria cards automaticamente quando arquivos são baixados
"""

import requests
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
import database as db


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
        conn = db.get_db_connection()
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
                # Retorna configuração vazia se não existir
                return {
                    'trello_api_key': None,
                    'trello_token': None,
                    'trello_board_id': None,
                    'trello_list_id': None,
                    'trello_ativo': False
                }
        except Exception as e:
            print(f"❌ Erro ao carregar config Trello: {e}")
            return {}
        finally:
            cur.close()
            conn.close()
    
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
        lote_id: int,
        prestador_nome: str,
        montador_nome: str,
        arquivos_baixados: list,
        nota_fiscal: Optional[str] = None,
        arquivos_para_anexar: Optional[list] = None,  # lista de caminhos de arquivos locais
        valor_lote: Optional[float] = None  # valor total do lote
    ) -> Optional[Dict[str, Any]]:
        """
        Cria um card no Trello quando arquivos são baixados
        
        Args:
            lote_id: ID do lote
            prestador_nome: Nome do prestador
            montador_nome: Nome do montador
            arquivos_baixados: Lista de nomes dos arquivos baixados
            nota_fiscal: Número da nota fiscal (opcional)
            valor_lote: Valor total do lote (opcional)
            
        Returns:
            Dados do card criado ou None se falhar
        """
        
        if not self.is_configured():
            print("⚠️  Integração Trello não configurada. Card não será criado.")
            return None
        
        try:
            # Determinar o nome a ser usado no título (prestador ou montador)
            nome_entidade = prestador_nome if prestador_nome else montador_nome
            
            # Monta o título do card com o valor
            if valor_lote and valor_lote > 0:
                titulo = f"📦 Lote #{lote_id} - {nome_entidade} - R$ {valor_lote:,.2f}"
            else:
                titulo = f"📦 Lote #{lote_id} - {nome_entidade}"
            
            # Monta a descrição do card
            descricao = self._montar_descricao(
                lote_id, 
                prestador_nome, 
                montador_nome, 
                arquivos_baixados, 
                nota_fiscal
            )
            # Cria o card via API com timeout aumentado e retry
            url = f"{self.base_url}/cards"
            
            # Usar query params apenas para auth, dados no body JSON
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            # Dados do card no body (reduz tamanho da URL)
            data = {
                'idList': self.list_id,
                'name': titulo,
                'desc': descricao,
                'pos': 'top'
            }
            
            # Tentar até 3 vezes com timeout progressivo
            max_tentativas = 3
            timeouts = [30, 60, 90]  # Timeouts progressivos
            
            for tentativa in range(max_tentativas):
                try:
                    print(f"🔄 Tentativa {tentativa + 1}/{max_tentativas} - Criando card no Trello...")
                    response = requests.post(
                        url, 
                        params=params, 
                        json=data,  # Envia no body como JSON
                        timeout=timeouts[tentativa]
                    )
                    response.raise_for_status()
                    card_data = response.json()
                    card_id = card_data['id']
                    card_url = card_data['shortUrl']
                    print(f"✅ Card Trello criado: {card_url}")
                    break  # Sucesso, sai do loop
                    
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
                        raise  # Re-lança a exceção na última tentativa
            # Adiciona label (se configurado)
            self._adicionar_label(card_id, 'green')
            # Cria checklist automática
            self._criar_checklist(card_id, arquivos_baixados)
            # Anexa arquivos reais, se fornecidos
            import logging
            logger = logging.getLogger('TrelloIntegration')
            
            if arquivos_para_anexar:
                print(f"📎 Anexando {len(arquivos_para_anexar)} arquivo(s) ao card...")
                logger.info(f"📎 Anexando {len(arquivos_para_anexar)} arquivo(s) ao card...")
                for idx, caminho in enumerate(arquivos_para_anexar, 1):
                    print(f"   [{idx}/{len(arquivos_para_anexar)}] Anexando: {os.path.basename(caminho)}")
                    logger.info(f"   [{idx}/{len(arquivos_para_anexar)}] Anexando: {os.path.basename(caminho)}")
                    self._anexar_arquivo(card_id, caminho)
            else:
                print(f"⚠️  Nenhum arquivo para anexar (lista vazia ou None)")
                logger.warning(f"⚠️  Nenhum arquivo para anexar - lista: {arquivos_para_anexar}")
            # Salva no banco que o card foi criado
            self._salvar_card_criado(lote_id, card_id, card_url)
            return card_data
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao criar card no Trello: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro inesperado ao criar card: {e}")
            return None

    def _anexar_arquivo(self, card_id: str, caminho_arquivo: str):
        """Faz upload de um arquivo real como anexo ao card do Trello, com logs detalhados"""
        import os
        import logging
        logger = logging.getLogger('TrelloIntegration')
        
        print(f"🔧 [DEBUG] Iniciando anexação de arquivo...")
        print(f"   Card ID: {card_id}")
        print(f"   Caminho: {caminho_arquivo}")
        logger.info(f"Tentando anexar arquivo: {caminho_arquivo}")

        if not os.path.isfile(caminho_arquivo):
            msg = f"⚠️  Arquivo não encontrado para anexo: {caminho_arquivo}"
            print(msg)
            logger.warning(msg)
            return False

        print(f"   ✅ Arquivo existe no disco")
        tamanho = os.path.getsize(caminho_arquivo)
        print(f"   📊 Tamanho: {tamanho} bytes")

        url = f"{self.base_url}/cards/{card_id}/attachments"
        params = {
            'key': self.api_key,
            'token': self.token
        }

        # Tentar até 2 vezes para anexar arquivo
        max_tentativas = 2
        
        for tentativa in range(max_tentativas):
            try:
                print(f"   🌐 Upload tentativa {tentativa + 1}/{max_tentativas}: {url}")
                with open(caminho_arquivo, 'rb') as f:
                    files = {'file': (os.path.basename(caminho_arquivo), f)}
                    response = requests.post(
                        url, 
                        params=params, 
                        files=files,
                        timeout=120  # 2 minutos para upload de arquivo
                    )

                    print(f"   📡 Resposta HTTP: {response.status_code}")
                    
                    if response.status_code == 200:
                        msg = f"📎 Anexo enviado com sucesso: {os.path.basename(caminho_arquivo)}"
                        print(f"   ✅ {msg}")
                        logger.info(msg)
                        return True
                    else:
                        msg = f"❌ Falha ao anexar {caminho_arquivo}: {response.status_code} - {response.text[:200]}"
                        print(f"   {msg}")
                        logger.error(msg)
                        if tentativa < max_tentativas - 1:
                            print(f"   🔄 Tentando novamente...")
                            continue
                        return False
                        
            except requests.exceptions.Timeout:
                msg = f"⏱️  Timeout ao anexar {caminho_arquivo}"
                print(f"   {msg}")
                logger.error(msg)
                if tentativa < max_tentativas - 1:
                    print(f"   🔄 Tentando novamente...")
                    continue
                return False
                
            except Exception as e:
                msg = f"❌ Exceção ao anexar {caminho_arquivo}: {e}"
                print(f"   {msg}")
                logger.error(msg)
                if tentativa < max_tentativas - 1:
                    print(f"   🔄 Tentando novamente...")
                    continue
                else:
                    import traceback
                    traceback.print_exc()
                    return False
        
        return False
    
    def _montar_descricao(
        self, 
        lote_id: int, 
        prestador_nome: str, 
        montador_nome: str, 
        arquivos_baixados: list,
        nota_fiscal: Optional[str]
    ) -> str:
        """Monta a descrição formatada do card"""
        
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        
        descricao = f"""## 📋 Informações do Lote

**Lote:** #{lote_id}
"""
        
        # Adicionar apenas prestador OU montador, não ambos
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
            # Primeiro, busca as labels disponíveis no board
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
                # Adiciona a label ao card
                url = f"{self.base_url}/cards/{card_id}/idLabels"
                params['value'] = label_id
                
                response = requests.post(url, params=params, timeout=30)
                response.raise_for_status()
                print(f"   🏷️  Label '{cor}' adicionada")
                
        except requests.exceptions.Timeout:
            print(f"⚠️  Timeout ao adicionar label")
        except Exception as e:
            print(f"⚠️  Não foi possível adicionar label: {e}")
    
    def _criar_checklist(self, card_id: str, arquivos: list):
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
            
            # Adiciona cada arquivo como item da checklist
            for arquivo in arquivos:
                url = f"{self.base_url}/checklists/{checklist_id}/checkItems"
                params = {
                    'key': self.api_key,
                    'token': self.token,
                    'name': arquivo
                }
                
                requests.post(url, params=params, timeout=30)
            
            print(f"   ✅ Checklist criada com {len(arquivos)} itens")
            
        except requests.exceptions.Timeout:
            print(f"⚠️  Timeout ao criar checklist")
        except Exception as e:
            print(f"⚠️  Não foi possível criar checklist: {e}")
    
    def _salvar_card_criado(self, lote_id: int, card_id: str, card_url: str):
        """Salva no banco que o card foi criado para este lote"""
        conn = db.get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO trello_cards 
                (lote_id, card_id, card_url, data_criacao)
                VALUES (%s, %s, %s, NOW())
            """, (lote_id, card_id, card_url))
            
            conn.commit()
            
        except Exception as e:
            print(f"⚠️  Erro ao salvar card no banco: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    
    def listar_boards(self) -> list:
        """Lista todos os boards do usuário (útil para configuração)"""
        if not self.api_key or not self.token:
            raise ValueError("API Key e Token não configurados")
        
        try:
            url = f"{self.base_url}/members/me/boards"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("API Key ou Token inválidos. Gere novas credenciais em https://trello.com/power-ups/admin")
            else:
                raise ValueError(f"Erro HTTP {e.response.status_code}: {e.response.text[:100]}")
        except Exception as e:
            raise ValueError(f"Erro ao conectar com Trello: {str(e)}")
    
    def listar_listas(self, board_id: str) -> list:
        """Lista todas as listas de um board (útil para configuração)"""
        if not self.api_key or not self.token:
            return []
        
        try:
            url = f"{self.base_url}/boards/{board_id}/lists"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"❌ Erro ao listar listas: {e}")
            return []
