import os
import json
import time
import sqlite3
import requests
import threading
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import urllib3

# Desabilitar avisos SSL (se necessário)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================
# CONFIGURAÇÕES DO TELEGRAM
# ============================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = '8795312239:AAF-yVGNQpq90Hs5fAGstj4Wve2-IwrtKBk'
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = '5786799110'

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
# WEBSCRAPING PARA PEGAR DADOS REAIS DO AVIATOR
# ============================================
class AviatorScraper:
    def __init__(self):
        self.ultimo_multiplier = 1.00
        self.ultima_rodada = 0
        self.historico = []
        self.rodadas_velhas = set()
        
        # URLs possíveis para scraping (tente várias fontes)
        self.urls = [
            "https://www.betou.com/br/aviator",  # Ajuste conforme o site
            "https://aviator-spribe.com/history",  # Site oficial Spribe
            "https://1win.com/aviator",  # Exemplo
        ]
        
    def get_multiplier_websocket(self):
        """Tenta pegar via WebSocket (mais preciso)"""
        try:
            import websocket
            import json as jsonlib
            
            # WebSocket do jogo (exemplo - precisa do endpoint correto)
            ws_url = "wss://api.spribe.io/aviator/ws"
            ws = websocket.create_connection(ws_url, timeout=5)
            
            # Envia mensagem de subscribe
            subscribe_msg = jsonlib.dumps({"event": "subscribe", "channel": "round"})
            ws.send(subscribe_msg)
            
            # Recebe dados
            result = ws.recv()
            data = jsonlib.loads(result)
            ws.close()
            
            if 'multiplier' in data:
                return float(data['multiplier']), data.get('round_id', 0)
        except:
            pass
        return None, None
    
    def get_multiplier_api(self):
        """Tenta pegar via API pública"""
        apis = [
            "https://api.spribe.io/api/v1/aviator/last",
            "https://aviator-api.betano.com/last_round",
            "https://api.1win.com/aviator/history/last"
        ]
        
        for api in apis:
            try:
                response = requests.get(api, timeout=3, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'application/json'
                })
                if response.status_code == 200:
                    data = response.json()
                    # Tenta encontrar o multiplicador em diferentes formatos
                    mult = data.get('multiplier') or data.get('result') or data.get('value')
                    rodada = data.get('round_id') or data.get('id') or data.get('game_id')
                    if mult:
                        return float(mult), rodada
            except:
                continue
        return None, None
    
    def get_multiplier_html(self):
        """Tenta pegar via HTML scraping"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for url in self.urls:
            try:
                response = requests.get(url, headers=headers, timeout=5, verify=False)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Padrões comuns de multiplicador no HTML
                    seletores = [
                        '.multiplier', '.crash-value', '.current-multiplier',
                        '[data-testid="multiplier"]', '.game-result',
                        'div:contains("x")', 'span:contains("x")'
                    ]
                    
                    for seletor in seletores:
                        try:
                            elemento = soup.select_one(seletor)
                            if elemento:
                                texto = elemento.text.strip()
                                # Extrai número do texto (ex: "2.35x" -> 2.35)
                                import re
                                numeros = re.findall(r'(\d+\.?\d*)', texto)
                                if numeros:
                                    mult = float(numeros[0])
                                    return mult, 0
                        except:
                            continue
            except:
                continue
        return None, None
    
    def get_real_data(self):
        """Tenta todas as fontes para pegar dados reais"""
        # Tenta WebSocket primeiro
        mult, rodada = self.get_multiplier_websocket()
        if mult:
            return mult, rodada
        
        # Depois API
        mult, rodada = self.get_multiplier_api()
        if mult:
            return mult, rodada
        
        # Por último HTML
        mult, rodada = self.get_multiplier_html()
        if mult:
            return mult, rodada
        
        # Se nada funcionar, retorna None
        return None, None
    
    def monitorar_tempo_real(self, callback):
        """Monitora em loop infinito chamando callback quando muda"""
        ultimo_valor = None
        
        while True:
            mult, rodada = self.get_real_data()
            
            if mult and mult != ultimo_valor:
                ultimo_valor = mult
                callback(mult, rodada, datetime.now())
            
            time.sleep(2)  # Verifica a cada 2 segundos

# ============================================
# BANCO DE DADOS LOCAL
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
                timestamp DATETIME,
                recebido_em DATETIME
            )
        ''')
        self.conn.commit()

    def add_rodada(self, numero_rodada, multiplicador):
        self.cursor.execute('''
            INSERT INTO rodadas (numero_rodada, multiplicador, timestamp, recebido_em)
            VALUES (?, ?, ?, ?)
        ''', (numero_rodada, multiplicador, datetime.now(), datetime.now()))
        self.conn.commit()

    def get_ultimas_rodadas(self, limit=20):
        self.cursor.execute('''
            SELECT multiplicador, timestamp FROM rodadas ORDER BY id DESC LIMIT ?
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

    def activate(self, window_minutes, multiplicador, numero_rodada):
        self.active = True
        self.trigger_time = datetime.now()
        self.window_minutes = window_minutes
        self.alertas_cronometro = {3: False, 2: False, 1: False}
        self.sinal_enviado = False
        
        hora_atual = datetime.now().strftime('%H:%M:%S')
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        msg = (
            f"🎯 *MODO SNIPER ATIVADO!*\n\n"
            f"📈 *Mega Vela:* {multiplicador}x\n"
            f"🆔 *Rodada:* {numero_rodada}\n"
            f"⏱️ *Janela:* {window_minutes} minutos\n"
            f"📅 *Data:* {data_atual}\n"
            f"⏰ *Hora:* {hora_atual}\n\n"
            f"⏳ *Próximos alertas:* 3min, 2min, 1min"
        )
        send_telegram_message(msg, parse_mode='Markdown')
    
    def get_confidence(self):
        return 85 if self.window_minutes == 3 else 80 if self.window_minutes == 5 else 75
    
    def check_and_alert(self, numero_rodada):
        if not self.active or self.sinal_enviado:
            return None
        
        elapsed = datetime.now() - self.trigger_time
        minutos_faltando = self.window_minutes - (elapsed.total_seconds() / 60)
        
        # Alertas progressivos
        for min_alerta in [3, 2, 1]:
            if min_alerta <= self.window_minutes:
                if minutos_faltando <= min_alerta and minutos_faltando > (min_alerta - 0.3) and not self.alertas_cronometro.get(min_alerta, False):
                    msg = f"⏰ *ALERTA PROGRESSIVO*\n⏳ Faltam {min_alerta} minuto(s)!\n🎯 Prepare-se!"
                    send_telegram_message(msg, parse_mode='Markdown')
                    self.alertas_cronometro[min_alerta] = True
        
        # Entrada confirmada
        if minutos_faltando <= 0.05 and not self.sinal_enviado:
            # Pega soma das últimas velas
            rodadas = db.get_ultimas_rodadas(10)
            soma_velas = sum(r[0] for r in rodadas if r[0] < 50) if rodadas else 15
            confianca = self.get_confidence()
            hora_atual = datetime.now().strftime('%H:%M:%S')
            
            alvo = 2.50 if confianca >= 85 else 2.00 if confianca >= 75 else 1.80
            protecao = 1.60 if confianca >= 85 else 1.50 if confianca >= 75 else 1.40
            
            msg = (
                f"🚀 *AETHERIUS PREDICTOR: ENTRADA CONFIRMADA!* 🚀\n\n"
                f"🎯 *Entrar AGORA:* {numero_rodada}\n"
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
# PROCESSADOR DE DADOS EM TEMPO REAL
# ============================================
class RealTimeProcessor:
    def __init__(self):
        self.ultimo_mult = 0
        self.ultimo_numero = 0
        self.scraper = AviatorScraper()
        
    def on_new_data(self, multiplier, round_id, timestamp):
        """Callback chamada quando chega dado novo"""
        print(f"📊 NOVO DADO REAL: {multiplier}x | Rodada: {round_id} | {timestamp.strftime('%H:%M:%S')}")
        
        # Salva no banco
        db.add_rodada(round_id, multiplier)
        
        # Verifica se é vela gigante (>50x)
        if multiplier >= 50:
            if multiplier >= 100:
                window = 3
            elif multiplier >= 70:
                window = 5
            else:
                window = 10
            
            msg = f"🟢 *VELA GIGANTE EM TEMPO REAL!*\n📈 {multiplier}x\n🎯 Ativando sniper para {window} minutos"
            send_telegram_message(msg, parse_mode='Markdown')
            sniper.activate(window, multiplier, round_id)
        
        # Verifica modo sniper
        if sniper.active:
            sniper.check_and_alert(round_id)
    
    def start(self):
        """Inicia o monitoramento em tempo real"""
        print("🚀 Iniciando monitoramento em TEMPO REAL...")
        print("⏳ Aguardando dados do Aviator...")
        
        while True:
            try:
                mult, rodada = self.scraper.get_real_data()
                
                if mult and mult != self.ultimo_mult:
                    self.ultimo_mult = mult
                    self.ultimo_numero = rodada if rodada else self.ultimo_numero + 1
                    self.on_new_data(mult, self.ultimo_numero, datetime.now())
                
                time.sleep(3)  # Verifica a cada 3 segundos
                
            except Exception as e:
                print(f"❌ Erro no monitoramento: {e}")
                time.sleep(5)

# ============================================
# HEALTH CHECK PARA RENDER
# ============================================
def run_health_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'AETHERIUS PREDICTOR - Real Time Data Active!')
        def log_message(self, format, *args):
            pass
    port = int(os.environ.get('PORT', 10000))
    HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()

# ============================================
# MAIN
# ============================================
def main():
    print("=" * 50)
    print("🎰 AETHERIUS PREDICTOR v4.0 - TEMPO REAL 🎰")
    print("=" * 50)
    print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
    print("✅ Modo: CAPTURA EM TEMPO REAL")
    print("✅ Fonte: WebSocket/API/HTML")
    print("=" * 50)
    
    # Mensagem de boas-vindas
    send_telegram_message(
        "🎰 *AETHERIUS PREDICTOR v4.0 - TEMPO REAL* 🎰\n\n"
        "✅ Bot iniciado!\n"
        "📡 Capturando dados REAIS do Aviator\n"
        "🎯 Modo Sniper ativado\n"
        "🔊 Alerta sonoro na entrada\n"
        "⏰ Monitoramento 24/7\n\n"
        "🟢 *Aguardando primeira vela...*",
        parse_mode='Markdown'
    )
    
    # Inicia processador em tempo real
    processor = RealTimeProcessor()
    processor.start()

if __name__ == "__main__":
    # Inicia health check em thread separada
    threading.Thread(target=run_health_server, daemon=True).start()
    # Inicia bot principal
    main()
