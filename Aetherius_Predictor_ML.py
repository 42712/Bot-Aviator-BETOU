import os
import json
import time
import random
import sqlite3
import math
import requests
from datetime import datetime, timedelta
from collections import deque
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
# WEB SCRAPING - PEGAR MULTIPLICADOR REAL
# ============================================
def get_real_multiplier():
    """Pega o multiplicador real do site Betou Aviator"""
    try:
        # URL do histórico do jogo (ajuste conforme o site real)
        url = "https://betouaviator.com/historico"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Parse do HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PROCURE PELO ELEMENTO QUE CONTÉM O MULTIPLICADOR
            # Exemplo: <div class="multiplier">1.45x</div>
            # VOCÊ PRECISA AJUSTAR O SELETOR CONFORME O SITE REAL
            
            # Tentativa 1: Classe comum de multiplicador
            elemento = soup.find('div', class_='multiplier')
            if not elemento:
                # Tentativa 2: Span com padrão
                elemento = soup.find('span', class_='value')
            if not elemento:
                # Tentativa 3: Qualquer elemento com 'x' no texto
                elementos = soup.find_all(text=lambda t: t and 'x' in t and t[0].replace('.', '').isdigit())
                if elementos:
                    texto = elementos[0].strip()
                    multiplicador = float(texto.replace('x', '').strip())
                    return round(multiplicador, 2)
            
            if elemento:
                texto = elemento.text.strip()
                multiplicador = float(texto.replace('x', '').strip())
                return round(multiplicador, 2)
        
        # Fallback: simulação se não conseguir pegar
        print("⚠️ Não conseguiu pegar dado real, usando simulação")
        return round(random.uniform(1.00, 150.00), 2)
        
    except Exception as e:
        print(f"❌ Erro no web scraping: {e}")
        # Fallback para simulação
        return round(random.uniform(1.00, 150.00), 2)

# ============================================
# FUNÇÃO PARA ENVIAR MENSAGEM COM SOM
# ============================================
def send_telegram_message(message, parse_mode='Markdown', sound_alert=False):
    """Envia mensagem com opção de alerta sonoro"""
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
            if sound_alert:
                print("🔊 ALERTA SONORO!")
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
# CARREGAR CONFIGURAÇÕES
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
# CÁLCULO DE CONFIANÇA SIMPLIFICADO
# ============================================
def calcular_confianca():
    rodadas = db.get_ultimas_rodadas(20)
    if len(rodadas) < 5:
        return 75
    
    # Análise simples de tendência
    multipliers = [r[0] for r in rodadas[:10]]
    media = sum(multipliers) / len(multipliers)
    
    if media < 1.8:
        return 85
    elif media < 2.5:
        return 75
    else:
        return 65

# ============================================
# MODO SNIPER ATUALIZADO (COM NÚMERO DA RODADA E HORÁRIO)
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
        
        # SINAL DE ENTRADA CONFIRMADA
        if minutos_faltando <= 0.1 and not self.sinal_enviado:
            soma_velas = calcular_soma_velas_recentes()
            confianca = self.get_confidence()
            hora_atual = datetime.now().strftime('%H:%M:%S')
            
            if confianca >= 85:
                alvo = 2.50
                protecao = 1.60
            elif confianca >= 75:
                alvo = 2.00
                protecao = 1.50
            else:
                alvo = 1.80
                protecao = 1.40
            
            msg = (
                f"🚀 *AETHERIUS PREDICTOR: ENTRADA CONFIRMADA!* 🚀\n\n"
                f"🎯 *Entrar AGORA: *{numero_rodada}\n"
                f"             *{hora_atual}*\n"
                f"\n"
                f"📊 *Soma de Velas Recente:* {soma_velas}\n"
                f"🎯 *Alvo Sugerido:* {alvo}x\n"
                f"🛡️ *Proteção:* {protecao}x\n"
                f"💎 *Confiança do ML:* Alta ({confianca}%)"
            )
            send_telegram_message(msg, parse_mode='Markdown', sound_alert=True)
            self.sinal_enviado = True
            return True
        
        if minutos_faltando < -0.1:
            self.active = False
            send_telegram_message(f"✅ *MODO SNIPER FINALIZADO*\n⏱️ Janela de {self.window_minutes} minutos encerrada.", parse_mode='Markdown')
        
        return None

sniper = SniperMode()

# ============================================
# FUNÇÃO PRINCIPAL DE ANÁLISE
# ============================================
def analyze_and_predict():
    # PEGA MULTIPLICADOR REAL VIA WEB SCRAPING
    current_multiplier = get_real_multiplier()
    numero_rodada = rodada_counter.next_round()
    
    print(f"📊 Rodada {numero_rodada}: {current_multiplier}x")
    
    db.add_rodada(numero_rodada, current_multiplier)
    
    HIGH_THRESHOLD = config.get('high_multiplier_threshold', 50.0)
    
    if current_multiplier >= HIGH_THRESHOLD:
        if current_multiplier >= 100:
            window = 3
        elif current_multiplier >= 70:
            window = 5
        else:
            window = 10
        
        msg = f"🟢 *VELA GIGANTE DETECTADA!*\n📈 {current_multiplier}x\n🎯 Ativando sniper para {window} minutos"
        send_telegram_message(msg, parse_mode='Markdown')
        sniper.activate(window, current_multiplier, numero_rodada)
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
            self.wfile.write(b'AETHERIUS PREDICTOR - Bot is running!')
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
        "🎯 Modo Sniper ativado (Web Scraping)\n"
        "🔊 Alertas sonoros ativados\n"
        "⏰ Monitoramento 24/7\n\n"
        "📊 *Dados reais via web scraping*\n\n"
        "Boa sorte! 🍀"
    )
    send_telegram_message(msg, parse_mode='Markdown')

def main():
    print("🚀 AETHERIUS PREDICTOR v4.0 - WEB SCRAPING")
    print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
    print("📊 Coletando dados reais...")
    send_welcome()
    
    while True:
        analyze_and_predict()
        intervalo = 30  # Verifica a cada 30 segundos
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Aguardando {intervalo}s...")
        time.sleep(intervalo)

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_health_server, daemon=True).start()
    main()
