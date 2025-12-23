"""
Cliente para consultar API externa de uploads de notas fiscais
Baseado no sistema original: sistema_original/consulta_nf_client.py

Inclui:
- Retry automático com backoff exponencial usando tenacity
- Logging estruturado
- Tratamento robusto de erros
"""

import requests
import logging
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configurar logger
logger = logging.getLogger('ConsultaNFClient')


class ConsultaNFClient:
    """
    Cliente para consultar status de uploads na API externa (api.link.dev.br)
    Com retry automático e logging estruturado
    """
    
    def __init__(self):
        self.base_url = "https://api.link.dev.br/dvprocessamento"
        self.api_key = "DV_API_2025_CTRL_NOTAS_f8e9d2c1b4a6"
        self.timeout_consulta = 30
        self.timeout_download = 120
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Tentativa {retry_state.attempt_number} falhou, aguardando para retry..."
        )
    )
    def _fazer_requisicao_api(self, url: str, payload: Dict, headers: Dict) -> requests.Response:
        """Faz requisição à API com retry automático"""
        return requests.post(url, json=payload, headers=headers, timeout=self.timeout_consulta, verify=False)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Download - Tentativa {retry_state.attempt_number} falhou, aguardando para retry..."
        )
    )
    def _fazer_download(self, url: str, headers: Dict) -> requests.Response:
        """Faz download com retry automático"""
        return requests.get(url, headers=headers, timeout=self.timeout_download, stream=True, verify=False)
    
    def consultar_e_processar(self, upload_hash: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Consulta status de um upload específico na API externa
        
        Args:
            upload_hash: Hash único do upload gerado pela API
            
        Returns:
            Tupla (sucesso, dados, erro)
            - sucesso: True se consulta foi bem-sucedida
            - dados: Dicionário com informações da nota e arquivos
            - erro: Mensagem de erro caso sucesso seja False
        """
        try:
            # Endpoint de consulta (POST, não GET!)
            url = f"{self.base_url}/consulta-nf/"
            
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                "X-API-Key": self.api_key
            }
            
            # Payload com o hash
            payload = {
                "hash": upload_hash
            }
            
            # Log da requisição
            logger.debug(f"Consultando API: {url}")
            logger.debug(f"Payload: {payload}")
            
            # POST request com retry automático
            response = self._fazer_requisicao_api(url, payload, headers)
            
            # Log da resposta
            logger.debug(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # A API retorna estrutura diferente
                if not data.get('success'):
                    return False, None, data.get('message', 'API retornou success=false')
                
                nota_fiscal = data.get('nota_fiscal', {})
                arquivos_raw = data.get('arquivos', [])
                stats = data.get('estatisticas', {})
                status_info = data.get('status_info', {})
                
                # Processar resposta
                nota_info = {
                    'hash': upload_hash,
                    'status': 1 if arquivos_raw else 0,  # 1=recebido, 0=aguardando
                    'status_descricao': status_info.get('descricao', 'Aguardando upload'),
                    'link_valido': status_info.get('link_valido', False),
                    'dias_restantes': status_info.get('dias_restantes', 0),
                    'numero_nota': None,  # Não vem na resposta
                    'data_upload': arquivos_raw[0].get('data_upload') if arquivos_raw else None
                }
                
                # Processar arquivos
                arquivos = []
                for arq in arquivos_raw:
                    arquivos.append({
                        'nome_original': arq.get('nome_original'),
                        'tamanho': arq.get('tamanho_arquivo', 0),
                        'tamanho_formatado': arq.get('tamanho_formatado', '0 B'),
                        'link_download': arq.get('link_download'),
                        'data_upload': arq.get('data_upload')
                    })
                
                # Estatísticas
                estatisticas = {
                    'total_arquivos': stats.get('total_arquivos', len(arquivos)),
                    'total_tamanho': stats.get('total_tamanho', 0),
                    'total_tamanho_formatado': stats.get('total_tamanho_formatado', '0 B')
                }
                
                resultado = {
                    'nota': nota_info,
                    'arquivos': arquivos,
                    'estatisticas': estatisticas
                }
                
                return True, resultado, None
            
            elif response.status_code == 404:
                return True, {
                    'nota': {
                        'hash': upload_hash,
                        'status': 0,
                        'status_descricao': 'Não encontrado',
                        'link_valido': False,
                        'dias_restantes': 0
                    },
                    'arquivos': [],
                    'estatisticas': {
                        'total_arquivos': 0,
                        'total_tamanho': 0,
                        'total_tamanho_formatado': '0 B'
                    }
                }, None
            
            else:
                return False, None, f"Erro HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            return False, None, "Timeout na requisição"
        except requests.exceptions.RequestException as e:
            return False, None, f"Erro de rede: {str(e)}"
        except Exception as e:
            return False, None, f"Erro inesperado: {str(e)}"
    
    def baixar_arquivo(self, url_download: str, caminho_destino: str) -> Tuple[bool, str]:
        """
        Baixa um arquivo da API externa
        
        Args:
            url_download: URL completa para download
            caminho_destino: Caminho local onde salvar o arquivo
            
        Returns:
            Tupla (sucesso, mensagem)
        """
        try:
            headers = {
                "User-Agent": "NovoMundo-DisparadorEmail/1.0",
                "X-API-Key": self.api_key
            }
            
            # GET request com retry automático
            response = self._fazer_download(url_download, headers)
            
            if response.status_code == 200:
                with open(caminho_destino, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return True, f"Arquivo baixado com sucesso"
            else:
                return False, f"Erro HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            return False, "Timeout no download"
        except Exception as e:
            return False, f"Erro ao baixar: {str(e)}"
    
    def _get_status_descricao(self, status: int) -> str:
        """Retorna descrição do status"""
        status_map = {
            0: 'Aguardando upload',
            1: 'Arquivo(s) recebido(s)',
            2: 'Link expirado'
        }
        return status_map.get(status, 'Desconhecido')
    
    def _formatar_tamanho(self, tamanho_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível"""
        for unidade in ['B', 'KB', 'MB', 'GB']:
            if tamanho_bytes < 1024.0:
                return f"{tamanho_bytes:.2f} {unidade}"
            tamanho_bytes /= 1024.0
        return f"{tamanho_bytes:.2f} TB"
