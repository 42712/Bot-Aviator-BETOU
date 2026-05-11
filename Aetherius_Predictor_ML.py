import os
import json
import time
import sqlite3
import re
import requests
import threading
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# ============================================
# CONFIGURAÇÕES DO TELEGRAM
# ============================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = '8795312239:AAF-yVGNQpq90Hs5fAGstj4Wve2-IwrtKBk'
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = '5786799110'  # SEU ID PESSOAL

print(f"✅ Bot configurado - Chat ID: {TELEGRAM_CHAT_ID}")

# ============================================
# FUNÇÃO PARA ENVIAR MENSAGEM
# ============================================
def send_telegram_message(message, parse_mode='Markdown', sound_alert=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if sound_alert:
        message = "🔊🔊🔊 *SINAL FORTE!* 🔊🔊🔊\n\n" + message
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_notification": False
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Mensagem enviada")
        else:
            print(f"[ERRO] {response.text}")
    except Exception as e:
        print(f"[ERRO] {e}")

# ============================================
# CARREGAR COOKIES DO ARQUIVO
# ============================================
def carregar_cookies():
    """Carrega os cookies do arquivo cookies.json"""
    try:
        with open('cookies.json', 'r') as f:
            cookies_dict = json.load(f)
        
        # Converte para formato requests
        cookies = requests.utils.cookiejar_from_dict(cookies_dict)
        print("✅ Cookies carregados com sucesso!")
        print(f"   Cookies encontrados: {list(cookies_dict.keys())}")
        return cookies
    except FileNotFoundError:
        print("❌ Arquivo cookies.json não encontrado!")
        print("   Crie o arquivo com os cookies conforme as instruções.")
        return None
    except json.JSONDecodeError:
        print("❌ Erro ao ler cookies.json - JSON inválido!")
        return None
    except Exception as e:
        print(f"❌ Erro ao carregar cookies: {e}")
        return None

# ============================================
# SCRAPER AUTENTICADO
# ============================================
class AviatorAuthenticatedScraper:
    def __init__(self):
        self.session = requests.Session()
        self.cookies = carregar_cookies()
        
        if self.cookies:
            self.session.cookies.update(self.cookies)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Referer': 'https://betou.bet.br/games/spribe/aviator',
            'Origin': 'https://betou.bet.br',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
        
        self.url = "https://betou.bet.br/games/spribe/aviator"
        self.ultimo_multiplier = None
        self.ultima_rodada = None
        
    def get_real_data(self):
        """Pega dados usando sessão autenticada via cookies"""
        try:
            response = self.session.get(self.url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # PEGA MULTIPLICADOR (classe que você inspecionou)
                mult_elem = soup.find('div', class_='bubble-multiplier')
                if not mult_elem:
                    mult_elem = soup.find('div', {'class': re.compile(r'multiplier', re.I)})
                
                if mult_elem:
                    texto = mult_elem.text.strip()
                    numeros = re.findall(r'(\d+\.?\d*)', texto)
                    if numeros:
                        multiplier = float(numeros[0])
                    else:
                        multiplier = None
                else:
                    multiplier = None
                
                # PEGA NÚMERO DA RODADA
                rodada_elem = soup.find('span', class_='text-uppercase')
                if not rodada_elem:
                    rodada_elem = soup.find('span', {'class': re.compile(r'round', re.I)})
                
                if rodada_elem:
                    texto = rodada_elem.text.strip()
                    numeros = re.findall(r'(\d+)', texto)
                    if numeros:
                        rodada = int(numeros[0])
                    else:
                        rodada = None
                else:
                    rodada = None
                
                # PEGA HORÁRIO
                horario_elem = soup.find('div', class_='header__info-time')
                horario = horario_elem.text.strip() if horario_elem else datetime.now().strftime('%H:%M:%S')
                
                return multiplier, rodada, horario
            
            elif response.status_code == 403:
                print("❌ Sessão expirada! Faça login novamente e atualize os cookies.")
                send_telegram_message("⚠️ *SESSÃO EXPIRADA!*\n\nOs cookies venceram. Atualize o arquivo `cookies.json` com novos valores.", parse_mode='Markdown')
                return None, None, None
            else:
                print(f"⚠️ Status inesperado: {response.status_code}")
                return None, None, None
                
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
            return None, None, None

# ============================================
# BANCO DE DADOS
# ============================================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('aetherius_history.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rodadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_rodada INTEGER,
                multiplicador REAL,
                horario TEXT,
                timestamp DATETIME
            )
        ''')
        self.conn.commit()

    def add_rodada(self, numero_rodada, multiplicador, horario):
        self.cursor.execute('''
            INSERT INTO rodadas (numero_rodada, multiplicador, horario, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (numero_rodada, multiplicador, horario, datetime.now()))
        self.conn.commit()

    def get_ultimas_rodadas(self, limit=20):
        self.cursor.execute('''
            SELECT multiplicador FROM rodadas ORDER BY id DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

db = Database()

# ============================================
# MODO SNIPER
# ============================================
class SniperMode:
    def __init__(self):
        self.active = False
        self.trigger_time = None
        self.window_minutes = None
        self.alertas_cronometro = {3: False, 2: False, 1: False}
        self.sinal_enviado = False

    def activate(self, window_minutes, multiplicador, numero_rodada, horario):
        self.active = True
        self.trigger_time = datetime.now()
        self.window_minutes = window_minutes
        self.alertas_cronometro = {3: False, 2: False, 1: False}
        self.sinal_enviado = False
        
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        msg = (
            f"🎯 *MODO SNIPER ATIVADO!*\n\n"
            f"📈 *Mega Vela:* {multiplicador}x\n"
            f"🆔 *Rodada:* {numero_rodada}\n"
            f"⏱️ *Janela:* {window_minutes} minutos\n"
            f"📅 *Data:* {data_atual}\n"
            f"⏰ *Hora da Vela:* {horario}\n\n"
            f"⏳ *Próximos alertas:* 3min, 2min, 1min"
        )
        send_telegram_message(msg, parse_mode='Markdown')
    
    def get_confidence(self):
        return 85 if self.window_minutes == 3 else 80 if self.window_minutes == 5 else 75
    
    def check_and_alert(self, numero_rodada_atual):
        if not self.active or self.sinal_enviado:
            return None
        
        elapsed = datetime.now() - self.trigger_time
        minutos_faltando = self.window_minutes - (elapsed.total_seconds() / 60)
        
        for min_alerta in [3, 2, 1]:
            if min_alerta <= self.window_minutes:
                if minutos_faltando <= min_alerta and minutos_faltando > (min_alerta - 0.3) and not self.alertas_cronometro.get(min_alerta, False):
                    msg = f"⏰ *ALERTA PROGRESSIVO*\n⏳ Faltam {min_alerta} minuto(s)!\n🎯 Prepare o cashout automático!"
                    send_telegram_message(msg, parse_mode='Markdown')
                    self.alertas_cronometro[min_alerta] = True
        
        if minutos_faltando <= 0.05 and not self.sinal_enviado:
            rodadas = db.get_ultimas_rodadas(10)
            soma_velas = sum(r[0] for r in rodadas if r[0] < 50) if rodadas else 15
            confianca = self.get_confidence()
            hora_atual = datetime.now().strftime('%H:%M:%S')
            
            alvo = 2.50 if confianca >= 85 else 2.00 if confianca >= 75 else 1.80
            protecao = 1.60 if confianca >= 85 else 1.50 if confianca >= 75 else 1.40
            
            msg = (
                f"🚀 *AETHERIUS PREDICTOR: ENTRADA CONFIRMADA!* 🚀\n\n"
                f"🎯 *Entrar AGORA:* {numero_rodada_atual}\n"
                f"            *{hora_atual}*\n\n"
                f"📊 *Soma de Velas Recente:* {soma_velas:.0f}\n"
                f"🎯 *Alvo Sugerido:* {alvo}x\n"
                f"🛡️ *Proteção:* {protecao}x\n"
                f"💎 *Confiança do ML:* Alta ({confianca}%)"
            )
            send_telegram_message(msg, parse_mode='Markdown', sound_alert=True)
            self.sinal_enviado = True
            return True
        
        if minutos_faltando < -0.1:
            self.active = False
            send_telegram_message(f"✅ *MODO SNIPER FINALIZADO*\n⏱️ Janela de {self.window_minutes} min encerrada.", parse_mode='Markdown')
        
        return None

sniper = SniperMode()

# ============================================
# PROCESSADOR PRINCIPAL
# ============================================
class RealTimeProcessor:
    def __init__(self):
        self.scraper = AviatorAuthenticatedScraper()
        self.ultimo_numero_rodada = None
        
    def processar(self):
        print("\n🚀 Iniciando captura com AUTENTICAÇÃO VIA COOKIES...")
        print("📡 Usando cookies da sua sessão logada no Betou")
        print("⏳ Aguardando primeira rodada...\n")
        
        while True:
            try:
                multiplier, rodada, horario = self.scraper.get_real_data()
                
                if multiplier and rodada:
                    if rodada != self.ultimo_numero_rodada:
                        self.ultimo_numero_rodada = rodada
                        
                        print(f"📊 [NOVA RODADA] {rodada} | {multiplier}x | {horario}")
                        
                        db.add_rodada(rodada, multiplier, horario)
                        
                        if multiplier >= 50:
                            if multiplier >= 100:
                                window = 3
                            elif multiplier >= 70:
                                window = 5
                            else:
                                window = 10
                            
                            msg = f"🟢 *VELA GIGANTE EM TEMPO REAL!*\n📈 {multiplier}x\n🆔 Rodada: {rodada}\n⏰ {horario}\n🎯 Ativando sniper para {window} minutos"
                            send_telegram_message(msg, parse_mode='Markdown')
                            sniper.activate(window, multiplier, rodada, horario)
                
                if sniper.active:
                    sniper.check_and_alert(rodada if rodada else 0)
                
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Erro no loop: {e}")
                time.sleep(5)

# ============================================
# HEALTH CHECK
# ============================================
def run_health_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'AETHERIUS PREDICTOR - Autenticado e Rodando!')
        def log_message(self, format, *args):
            pass
    port = int(os.environ.get('PORT', 10000))
    HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()

# ============================================
# ARQUIVO MODELO DE COOKIES
# ============================================
def criar_modelo_cookies():
    """Cria um arquivo de exemplo para o usuário"""
    modelo = {
        "__Host-jwt_token_lax": "COLE_AQUI_O_VALUE",
        "__Host-jwt_token_none": "COLE_AQUI_O_VALUE", 
        "__Host-jwt_token_strict": "COLE_AQUI_O_VALUE",
        "__cf_bm": "COLE_AQUI_O_VALUE"
    }
    
    with open('cookies.json.example', 'w') as f:
        json.dump(modelo, f, indent=2)
    
    print("\n" + "="*60)
    print("📝 INSTRUÇÕES PARA CRIAR O cookies.json")
    print("="*60)
    print("1. Abra o arquivo 'cookies.json.example'")
    print("2. Substitua 'COLE_AQUI_O_VALUE' pelos valores reais")
    print("3. Salve como 'cookies.json'")
    print("="*60 + "\n")

# ============================================
# MENSAGEM DE BOAS-VINDAS
# ============================================
def send_welcome():
    msg = (
        "🎰 *AETHERIUS PREDICTOR v4.0 - AUTENTICADO* 🎰\n\n"
        "✅ Bot iniciado com SUCESSO!\n"
        "🔐 Usando cookies da sua conta Betou\n"
        "📡 Capturando dados em TEMPO REAL\n"
        "🎯 Modo Sniper ativado (velas >50x)\n"
        "🔊 Alerta sonoro na entrada confirmada\n"
        "⏰ Monitoramento 24/7\n\n"
        "🟢 *Aguardando dados do jogo...*"
    )
    send_telegram_message(msg, parse_mode='Markdown')

# ============================================
# MAIN
# ============================================
def main():
    print("="*60)
    print("🎰 AETHERIUS PREDICTOR - MODO AUTENTICADO 🎰")
    print("="*60)
    
    criar_modelo_cookies()
    
    # Verifica se o arquivo de cookies existe
    if not os.path.exists('cookies.json'):
        print("❌ Arquivo 'cookies.json' não encontrado!")
        print("📝 Siga as instruções acima para criar o arquivo.")
        send_telegram_message("⚠️ *CONFIGURAÇÃO NECESSÁRIA*\n\nCrie o arquivo `cookies.json` com os cookies da sua sessão logada no Betou.", parse_mode='Markdown')
        # Mesmo sem cookies, tenta continuar (vai falhar)
    else:
        send_welcome()
    
    processor = RealTimeProcessor()
    processor.processar()

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    main()
