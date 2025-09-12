"""
Script para contornar a proteção do CloudFlare usando SeleniumBase em modo undetected
e monitorar o status dos servidores em tempo real.
"""

from seleniumbase import SB
import time
import random
import json
import requests
import os
from datetime import datetime

# Configurações
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://unlockpay.com.br/api/webhook')
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 60))  # segundos

def delay(min_seconds, max_seconds):
    """Função para adicionar um delay aleatório entre min e max segundos."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def send_webhook_data(data):
    """Função para enviar dados via webhook."""
    try:
        print(f"Enviando dados via webhook para: {WEBHOOK_URL}")
        response = requests.post(WEBHOOK_URL, json=data)
        print(f"Webhook enviado com sucesso: {response.status_code}")
        return True
    except Exception as e:
        print(f"Erro ao enviar webhook: {e}")
        return False

def extract_server_data(sb):
    """Função para extrair dados da tabela de servidores."""
    try:
        # Usar JavaScript para extrair os dados da tabela
        server_data = sb.execute_script("""
            var servers = [];
            var tables = document.querySelectorAll('table');
            var targetTable = null;
            
            // Procurar a tabela correta
            for (var i = 0; i < tables.length; i++) {
                var headers = tables[i].querySelectorAll('thead th');
                for (var j = 0; j < headers.length; j++) {
                    if (headers[j].textContent.includes('Server Name')) {
                        targetTable = tables[i];
                        break;
                    }
                }
                if (targetTable) break;
            }
            
            if (targetTable) {
                var rows = targetTable.querySelectorAll('tbody tr');
                for (var i = 0; i < rows.length; i++) {
                    var cells = rows[i].querySelectorAll('td');
                    if (cells.length >= 2) {
                        var name = cells[0].textContent.trim();
                        var statusElement = cells[1].querySelector('.badge');
                        var status = statusElement ? statusElement.textContent.trim() : 'Unknown';
                        servers.push({name: name, status: status});
                    }
                }
            }
            
            return servers;
        """)
        
        return server_data
    except Exception as e:
        print(f"Erro ao extrair dados da tabela: {e}")
        return []

def save_server_data_to_file(server_data):
    """Função para salvar dados dos servidores em um arquivo JSON."""
    try:
        with open('server_status.json', 'w') as f:
            json.dump(server_data, f, indent=2)
        print("Dados dos servidores salvos em server_status.json")
    except Exception as e:
        print(f"Erro ao salvar dados dos servidores: {e}")

def load_server_data_from_file():
    """Função para carregar dados dos servidores de um arquivo JSON."""
    try:
        if os.path.exists('server_status.json'):
            with open('server_status.json', 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Erro ao carregar dados dos servidores: {e}")
        return []

def compare_server_status(old_data, new_data):
    """Função para comparar status dos servidores e identificar mudanças."""
    changes = []
    
    # Converter listas em dicionários para facilitar a comparação
    old_dict = {server['name']: server['status'] for server in old_data}
    new_dict = {server['name']: server['status'] for server in new_data}
    
    # Verificar mudanças
    for name, new_status in new_dict.items():
        old_status = old_dict.get(name, 'Unknown')
        if old_status != new_status:
            changes.append({
                'name': name,
                'old_status': old_status,
                'new_status': new_status
            })
    
    return changes

def main():
    # Iniciar o navegador em modo undetected
    with SB(uc=True, test=True, locale="en") as sb:
        try:
            print("Iniciando navegador em modo undetected...")
            print(f"URL de webhook configurada: {WEBHOOK_URL}")
            print(f"Intervalo de verificação: {CHECK_INTERVAL} segundos")
            
            # URL do site que queremos acessar
            url = "https://www.androidmultitool.com/"
            
            # Ativar o modo CDP (Chrome DevTools Protocol) para evitar detecção
            print("Ativando modo CDP...")
            sb.activate_cdp_mode(url)
            
            # Aguardar um momento para a página carregar
            delay(2, 5)
            
            # Verificar se estamos em uma página do CloudFlare
            title = sb.get_title()
            print(f"Título da página: {title}")
            
            # Verificar se é uma página do CloudFlare
            if title and ("Just a moment" in title or "Checking your browser" in title):
                print("Página do CloudFlare detectada. Tentando contornar...")
                
                # Tentar clicar no CAPTCHA automaticamente
                try:
                    sb.uc_gui_click_captcha()
                    print("CAPTCHA clicado automaticamente!")
                except Exception as e:
                    print(f"Não foi possível clicar no CAPTCHA automaticamente: {e}")
                    
                    # Se o clique automático não funcionar, tentar métodos alternativos
                    try:
                        # Procurar elementos específicos do CloudFlare
                        if sb.is_element_visible("input[type='checkbox']"):
                            sb.cdp.gui_click_element("input[type='checkbox']")
                            print("Checkbox do CloudFlare clicado!")
                        elif sb.is_element_visible("#checkbox"):
                            sb.cdp.gui_click_element("#checkbox")
                            print("Checkbox do CloudFlare clicado!")
                        elif sb.is_element_visible(".ctp-checkbox-label"):
                            sb.cdp.gui_click_element(".ctp-checkbox-label")
                            print("Checkbox do CloudFlare clicado!")
                    except Exception as e2:
                        print(f"Tentativa alternativa também falhou: {e2}")
                
                # Aguardar para ver se o desafio foi resolvido
                delay(10, 15)
                
                # Verificar novamente o título
                new_title = sb.get_title()
                if new_title and ("Just a moment" not in new_title and "Checking your browser" not in new_title):
                    print("Desafio do CloudFlare resolvido com sucesso!")
                else:
                    print("Ainda na página do CloudFlare. Pode ser necessário intervenção manual.")
            else:
                print("Não estamos em uma página do CloudFlare.")
            
            # Carregar dados anteriores dos servidores
            previous_server_data = load_server_data_from_file()
            
            # Loop de monitoramento
            while True:
                try:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Atualizando página...")
                    
                    # Recarregar a página
                    sb.refresh()
                    
                    # Aguardar um momento para a página carregar
                    delay(3, 7)
                    
                    # Verificar se estamos em uma página do CloudFlare novamente após o refresh
                    title = sb.get_title()
                    if title and ("Just a moment" in title or "Checking your browser" in title):
                        print("Página do CloudFlare detectada após refresh. Tentando contornar...")
                        
                        # Tentar clicar no CAPTCHA automaticamente
                        try:
                            sb.uc_gui_click_captcha()
                            print("CAPTCHA clicado automaticamente!")
                        except Exception as e:
                            print(f"Não foi possível clicar no CAPTCHA automaticamente: {e}")
                        
                        # Aguardar para ver se o desafio foi resolvido
                        delay(10, 15)
                    
                    # Verificar se a página principal carregou
                    if sb.is_element_visible("table"):
                        print("Página principal carregada com sucesso!")
                        
                        # Extrair dados da tabela de servidores
                        current_server_data = extract_server_data(sb)
                        
                        if current_server_data:
                            print(f"Encontrados {len(current_server_data)} servidores na tabela")
                            
                            # Exibir os dados dos servidores
                            for i, server in enumerate(current_server_data):
                                print(f"Servidor {i+1}: {server['name']} - Status: {server['status']}")
                            
                            # Salvar dados atuais em arquivo
                            save_server_data_to_file(current_server_data)
                            
                            # Comparar com dados anteriores
                            if previous_server_data:
                                changes = compare_server_status(previous_server_data, current_server_data)
                                
                                if changes:
                                    print(f"\nDetectadas {len(changes)} mudanças no status dos servidores:")
                                    for change in changes:
                                        print(f"  {change['name']}: {change['old_status']} -> {change['new_status']}")
                                    
                                    # Enviar dados completos via webhook quando há mudanças
                                    webhook_data = {
                                        'timestamp': datetime.now().isoformat(),
                                        'type': 'status_change',
                                        'changes': changes,
                                        'current_servers': current_server_data
                                    }
                                    send_webhook_data(webhook_data)
                                else:
                                    print("Nenhuma mudança no status dos servidores.")
                            else:
                                # Primeira execução - enviar status inicial via webhook
                                print("Enviando status inicial dos servidores...")
                                webhook_data = {
                                    'timestamp': datetime.now().isoformat(),
                                    'type': 'initial_status',
                                    'servers': current_server_data
                                }
                                send_webhook_data(webhook_data)
                            
                            # Atualizar dados anteriores
                            previous_server_data = current_server_data
                        else:
                            print("Não foi possível extrair dados dos servidores.")
                    else:
                        print("Tabela de servidores não encontrada.")
                    
                    # Aguardar até a próxima verificação
                    print(f"Aguardando {CHECK_INTERVAL} segundos para a próxima verificação...")
                    time.sleep(CHECK_INTERVAL)
                    
                except Exception as e:
                    print(f"Erro durante o monitoramento: {e}")
                    import traceback
                    traceback.print_exc()
                    # Aguardar antes de tentar novamente
                    time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Erro durante a execução: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()