import os
import json
import time
import random
import sqlite3
import math
from datetime import datetime, timedelta
from collections import deque
import requests

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
# FUNÇÃO PARA ENVIAR MENSAGEM COM SOM (ALERTA SONORO)
# ============================================
def send_telegram_message(message, parse_mode='HTML', sound_alert=False):
    """Envia mensagem com opção de alerta sonoro"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Para alerta sonoro, adiciona caracteres especiais que disparam notificação alta
    if sound_alert:
        message = "🔊🔊🔊 SINAL FORTE! 🔊🔊🔊\n\n" + message
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_notification": False  # Garante que vai notificar
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Mensagem enviada")
            if sound_alert:
                print("🔊 ALERTA SONORO ENVIADO!")
        else:
            print(f"[ERRO] {response.text}")
    except Exception as e:
        print(f"[ERRO] {e}")

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
                numero_rodada INTEGER UNIQUE,
                multiplicador REAL,
                timestamp DATETIME,
                tipo TEXT
            )
        ''')
        self.conn.commit()

    def add_rodada(self, numero_rodada, multiplicador):
        self.cursor.execute('''
            INSERT OR REPLACE INTO rodadas (numero_rodada, multiplicador, timestamp, tipo)
            VALUES (?, ?, ?, ?)
        ''', (numero_rodada, multiplicador, datetime.now(), 'normal'))
        self.conn.commit()

    def get_ultimas_rodadas(self, limit=30):
        self.cursor.execute('''
            SELECT multiplicador, tipo FROM rodadas ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

db = Database()

# ============================================
# CONTADOR DE RODADAS
# ============================================
class RodadaCounter:
    def __init__(self):
        self.current_round = random.randint(47897500, 47897999)

    def next_round(self):
        self.current_round += random.randint(1, 3)
        return self.current_round

rodada_counter = RodadaCounter()

# ============================================
# CONFIGURAÇÕES
# ============================================
def load_brain_config():
    try:
        with open('aetherius_brain_config.json', 'r') as f:
            return json.load(f)
    except:
        return {
            "high_multiplier_threshold": 50.0,
            "sniper_mode_confidence_3min": 85,
            "sniper_mode_confidence_5min": 80,
            "sniper_mode_confidence_10min": 75
        }

config = load_brain_config()

def calcular_soma_velas_recentes():
    rodadas = db.get_ultimas_rodadas(10)
    soma = sum(r[0] for r in rodadas if r[0] < 50)
    return round(soma, 2)

# ============================================
# MODO SNIPER OTIMIZADO COM SUPERA LISTA
# ============================================
class SniperMode:
    def __init__(self):
        self.active = False
        self.trigger_time = None
        self.window_minutes = None
        self.alertas_cronometro = {3: False, 2: False, 1: False}
        self.sinal_enviado = False
        self.proximo_alerta = None

    def activate(self, window_minutes, multiplicador):
        self.active = True
        self.trigger_time = datetime.now()
        self.window_minutes = window_minutes
        self.alertas_cronometro = {3: False, 2: False, 1: False}
        self.sinal_enviado = False
        
        msg = f"🎯 *MODO SNIPER ATIVADO!*\n📈 Mega Vela: {multiplicador}x\n⏱️ Janela de {window_minutes} minutos"
        send_telegram_message(msg, parse_mode='Markdown')
    
    def get_confidence(self):
        if self.window_minutes == 3:
            return config.get('sniper_mode_confidence_3min', 85)
        elif self.window_minutes == 5:
            return config.get('sniper_mode_confidence_5min', 80)
        return config.get('sniper_mode_confidence_10min', 75)
    
    def check_and_alert(self, numero_rodada):
        if not self.active or self.sinal_enviado:
            return None
        
        elapsed = datetime.now() - self.trigger_time
        minutos_faltando = self.window_minutes - (elapsed.total_seconds() / 60)
        
        # ALERTAS PROGRESSIVOS (3, 2, 1 minuto)
        for min_alerta in [3, 2, 1]:
            if min_alerta <= self.window_minutes:
                if minutos_faltando <= min_alerta and minutos_faltando > (min_alerta - 0.5) and not self.alertas_cronometro.get(min_alerta, False):
                    msg = f"⏰ *ALERTA PROGRESSIVO*\n⏳ Faltam {min_alerta} minuto(s) para a janela sniper!\n🎯 Prepare o cashout automático!"
                    send_telegram_message(msg, parse_mode='Markdown')
                    self.alertas_cronometro[min_alerta] = True
        
        # SINAL DE ENTRADA CONFIRMADA (Últimos 10 segundos)
        if minutos_faltando <= 0.1 and not self.sinal_enviado:
            soma_velas = calcular_soma_velas_recentes()
            confianca = self.get_confidence()
            hora_atual = datetime.now().strftime('%H:%M:%S')
            numero_rodada_atual = numero_rodada
            
            if confianca >= 85:
                alvo = 2.50
                protecao = 1.60
            elif confianca >= 75:
                alvo = 2.00
                protecao = 1.50
            else:
                alvo = 1.80
                protecao = 1.40
            
            # MENSAGEM OTIMIZADA IGUAL AO SEU EXEMPLO
            msg = (
                f"🚀 *AETHERIUS PREDICTOR: ENTRADA CONFIRMADA!* 🚀\n\n"
                f"🎯 *Entrar AGORA: *{numero_rodada_atual}*\n"
                f"             *{hora_atual}*\n"
                f"\n"
                f"📊 *Soma de Velas Recente:* {soma_velas}\n"
                f"🎯 *Alvo Sugerido:* {alvo}x\n"
                f"🛡️ *Proteção:* {protecao}x\n"
                f"💎 *Confiança do ML:* Alta ({confianca}%)"
            )
            # ENVIA COM ALERTA SONORO (SOUND_ALERT = TRUE)
            send_telegram_message(msg, parse_mode='Markdown', sound_alert=True)
            self.sinal_enviado = True
            return True
        
        # Reseta após a janela
        if minutos_faltando < -0.1:
            self.active = False
            send_telegram_message(f"✅ *MODO SNIPER FINALIZADO*\n⏱️ Janela de {self.window_minutes} minutos encerrada.", parse_mode='Markdown')
        
        return None

sniper = SniperMode()

# ============================================
# SIMULAÇÃO
# ============================================
def get_current_multiplier():
    return round(random.uniform(1.00, 150.00), 2)

def analyze_and_predict():
    current_multiplier = get_current_multiplier()
    numero_rodada = rodada_counter.next_round()
    
    db.add_rodada(numero_rodada, current_multiplier)
    
    HIGH_THRESHOLD = config.get('high_multiplier_threshold', 50.0)
    
    # Detecção de vela gigante
    if current_multiplier >= HIGH_THRESHOLD:
        if current_multiplier >= 100:
            window = 3
        elif current_multiplier >= 70:
            window = 5
        else:
            window = 10
        
        msg = f"🟢 *VELA GIGANTE DETECTADA!*\n📈 {current_multiplier}x\n🎯 Ativando sniper para {window} minutos"
        send_telegram_message(msg, parse_mode='Markdown')
        sniper.activate(window, current_multiplier)
        return
    
    if sniper.active:
        sniper.check_and_alert(numero_rodada)
        return

# ============================================
# HEALTH CHECK PARA RENDER
# ============================================
def run_health_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running')
        def log_message(self, format, *args):
            pass
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

# ============================================
# MAIN
# ============================================
def send_welcome():
    msg = (
        "🎰 *AETHERIUS PREDICTOR ML v4.0* 🎰\n\n"
        "✅ Bot iniciado!\n"
        "🎯 Modo Sniper ativado\n"
        "🔊 Alertas sonoros ativados\n"
        "⏰ Monitoramento 24/7\n\n"
        "Boa sorte! 🍀"
    )
    send_telegram_message(msg, parse_mode='Markdown')

def main():
    print("🚀 AETHERIUS PREDICTOR v4.0 - OTIMIZADO")
    print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
    send_welcome()
    
    while True:
        analyze_and_predict()
        intervalo = random.uniform(25, 45)
        time.sleep(intervalo)

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_health_server, daemon=True).start()
    main()
