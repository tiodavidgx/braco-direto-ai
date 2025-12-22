"""
Cliente Python para interagir com o serviço WhatsApp
"""

import requests
import json
from typing import List, Dict, Optional
import time


class WhatsAppClient:
    """Cliente para enviar mensagens via WhatsApp"""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        """
        Inicializa o cliente WhatsApp
        
        Args:
            base_url: URL base do serviço WhatsApp (padrão: http://localhost:3000)
        """
        self.base_url = base_url.rstrip('/')
        
    def get_status(self) -> Dict:
        """
        Verifica o status da conexão WhatsApp
        
        Returns:
            Dict com informações do status
        """
        try:
            response = requests.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "status": "error"
            }
    
    def is_connected(self) -> bool:
        """
        Verifica se o WhatsApp está conectado
        
        Returns:
            True se conectado, False caso contrário
        """
        status = self.get_status()
        return status.get("status") == "connected"
    
    def get_info(self) -> Dict:
        """
        Obtém informações do usuário WhatsApp conectado
        
        Returns:
            Dict com informações do usuário
        """
        try:
            response = requests.get(f"{self.base_url}/info")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def format_number(self, number: str) -> str:
        """
        Formata número de telefone para o padrão WhatsApp
        Remove o 9º dígito de celulares brasileiros para compatibilidade
        
        Args:
            number: Número de telefone (com ou sem código do país)
            
        Returns:
            Número formatado (ex: 5562991234567 -> 556291234567)
        """
        # Remove caracteres não numéricos
        number = ''.join(filter(str.isdigit, number))
        
        # Se não tem código do país, adiciona 55 (Brasil)
        if len(number) == 11 or len(number) == 10:
            number = f"55{number}"
        
        # Remover 9º dígito para números brasileiros
        # Formato: 55 + DDD (2 dígitos) + 9 + número (8 dígitos) = 13 dígitos
        # Resultado desejado: 55 + DDD (2 dígitos) + número (8 dígitos) = 12 dígitos
        if len(number) == 13 and number.startswith('55'):
            ddd = number[2:4]
            resto = number[4:]  # 9 + 8 dígitos
            
            # Se começa com 9 (celular), remove o 9
            if resto.startswith('9') and len(resto) == 9:
                numero_sem_9 = resto[1:]  # Remove o primeiro dígito (9)
                number = f"55{ddd}{numero_sem_9}"
                print(f"📞 WhatsApp Client - Telefone formatado: {ddd}9{numero_sem_9} -> {ddd}{numero_sem_9}")
        
        return number
    
    def send_message(
        self,
        number: str,
        message: str,
        media_path: Optional[str] = None
    ) -> Dict:
        """
        Envia uma mensagem para um número
        
        Args:
            number: Número de telefone (com ou sem código do país)
            message: Texto da mensagem
            media_path: Caminho opcional para arquivo de mídia
            
        Returns:
            Dict com resultado do envio
        """
        if not self.is_connected():
            return {
                "success": False,
                "error": "WhatsApp não está conectado"
            }
        
        # Formatar número
        formatted_number = self.format_number(number)
        
        # Preparar dados
        data = {
            "number": formatted_number,
            "message": message
        }
        
        if media_path:
            data["media"] = {"path": media_path}
        
        try:
            response = requests.post(
                f"{self.base_url}/send",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_bulk_messages(
        self,
        numbers: List[str],
        message: str,
        media_path: Optional[str] = None,
        delay: int = 2000
    ) -> Dict:
        """
        Envia mensagem para múltiplos números
        
        Args:
            numbers: Lista de números de telefone
            message: Texto da mensagem
            media_path: Caminho opcional para arquivo de mídia
            delay: Delay entre mensagens em milissegundos (padrão: 2000)
            
        Returns:
            Dict com resultado do envio em massa
        """
        if not self.is_connected():
            return {
                "success": False,
                "error": "WhatsApp não está conectado"
            }
        
        # Formatar todos os números
        formatted_numbers = [self.format_number(num) for num in numbers]
        
        # Preparar dados
        data = {
            "numbers": formatted_numbers,
            "message": message,
            "delay": delay
        }
        
        if media_path:
            data["media"] = {"path": media_path}
        
        try:
            response = requests.post(
                f"{self.base_url}/send-bulk",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def disconnect(self) -> Dict:
        """
        Desconecta o WhatsApp
        
        Returns:
            Dict com resultado da desconexão
        """
        try:
            response = requests.post(f"{self.base_url}/disconnect")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def wait_for_connection(self, timeout: int = 120, check_interval: int = 2) -> bool:
        """
        Aguarda até que o WhatsApp esteja conectado
        
        Args:
            timeout: Tempo máximo de espera em segundos (padrão: 120)
            check_interval: Intervalo entre verificações em segundos (padrão: 2)
            
        Returns:
            True se conectou, False se atingiu timeout
        """
        elapsed = 0
        while elapsed < timeout:
            if self.is_connected():
                return True
            time.sleep(check_interval)
            elapsed += check_interval
        
        return False


# Exemplo de uso
if __name__ == "__main__":
    # Criar cliente
    whatsapp = WhatsAppClient()
    
    print("🔍 Verificando status do WhatsApp...")
    status = whatsapp.get_status()
    print(f"Status: {status}")
    
    if not whatsapp.is_connected():
        print("\n⚠️  WhatsApp não está conectado!")
        print("📱 Acesse http://localhost:3000/qr para escanear o QR Code")
        print("⏳ Aguardando conexão...")
        
        if whatsapp.wait_for_connection(timeout=120):
            print("✅ WhatsApp conectado!")
        else:
            print("❌ Timeout: WhatsApp não foi conectado")
            exit(1)
    
    # Obter informações do usuário
    info = whatsapp.get_info()
    if info.get("success"):
        print(f"\n👤 Usuário conectado: {info['info']['name']}")
        print(f"📱 Número: {info['info']['number']}")
    
    # Exemplo de envio de mensagem
    print("\n📤 Exemplo de envio:")
    print("whatsapp.send_message('11999999999', 'Olá! Esta é uma mensagem de teste.')")
    
    # Exemplo de envio em massa
    print("\n📤 Exemplo de envio em massa:")
    print("whatsapp.send_bulk_messages(['11999999999', '11988888888'], 'Mensagem para todos!')")
