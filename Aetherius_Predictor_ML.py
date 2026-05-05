import os
import json
import time
import random
import sqlite3
import math
from datetime import datetime, timedelta
from collections import deque

# ============================================
# CONFIGURAÇÕES DO TELEGRAM (DO RENDER)
# ============================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# VALIDAÇÃO DAS CREDENCIAIS
if not TELEGRAM_BOT_TOKEN:
    print("❌ ERRO FATAL: TELEGRAM_BOT_TOKEN não configurado!")
    print("Configure a variável de ambiente no Render.")
    TELEGRAM_BOT_TOKEN = '8795312239:AAF-yVGNQpq90Hs5fAGstj4Wve2-IwrtKBk'

if not TELEGRAM_CHAT_ID:
    print("❌ ERRO FATAL: TELEGRAM_CHAT_ID não configurado!")
    print("Configure a variável de ambiente no Render.")
    TELEGRAM_CHAT_ID = '8795312239'

print(f"✅ Bot configurado com token: {TELEGRAM_BOT_TOKEN[:20]}...")
print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")

# ============================================
# FUNÇÃO PARA ENVIAR MENSAGENS COM FORMATAÇÃO HTML
# ============================================
import requests

def send_telegram_message(message, parse_mode='HTML'):
    """Envia mensagem para o Telegram com formatação HTML"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado. Mensagem não enviada.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Mensagem enviada para o Telegram")
        else:
            print(f"[ERRO] Telegram: {response.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar: {e}")

# ============================================
# BANCO DE DADOS SQLITE
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
        tipo = "roxa" if multiplicador < 2.0 else "rosa" if multiplicador >= 10.0 else "normal"
        self.cursor.execute('''
            INSERT OR REPLACE INTO rodadas (numero_rodada, multiplicador, timestamp, tipo)
            VALUES (?, ?, ?, ?)
        ''', (numero_rodada, multiplicador, datetime.now(), tipo))
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
        self.current_round = 47897589

    def next_round(self):
        self.current_round += random.randint(1, 5)
        return self.current_round

rodada_counter = RodadaCounter()

# ============================================
# CARREGAR CONFIGURAÇÕES DO CÉREBRO
# ============================================
def load_brain_config(config_path='aetherius_brain_config.json'):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "estatisticas_gerais": {"total_rodadas": 0, "percentual_roxas": 0.0, "percentual_rosas": 0.0},
            "intervalos_medios": {"roxa_segundos": 0.0, "rosa_segundos": 0.0},
            "melhores_horas": [],
            "padrao_100x": 1,
            "high_multiplier_threshold": 50.0,
            "sniper_mode_confidence_3min": 85,
            "sniper_mode_confidence_5min": 80,
            "sniper_mode_confidence_10min": 75
        }

config = load_brain_config()

# ============================================
# CÁLCULO DA SOMA DE VELAS RECENTES
# ============================================
def calcular_soma_velas_recentes():
    rodadas = db.get_ultimas_rodadas(10)
    soma = sum(r[0] for r in rodadas if r[0] < 50)
    return round(soma, 2)

# ============================================
# MACHINE LEARNING (MARKOV + BAYES)
# ============================================
class AetheriusML:
    def __init__(self):
        self.historico_multipliers = deque(maxlen=30)
        self.acertos = 0
        self.erros = 0

    def markov_probability(self, ultimos_estados):
        if len(ultimos_estados) < 2:
            return 0.65
        padrao = tuple(ultimos_estados[-3:])
        padroes_conhecidos = {
            ('baixo', 'baixo', 'medio'): 0.75,
            ('medio', 'alto', 'baixo'): 0.70,
            ('baixo', 'medio', 'baixo'): 0.68,
        }
        return padroes_conhecidos.get(padrao, 0.65)

    def bayesian_inference(self, ultimos_multipliers):
        media = sum(ultimos_multipliers) / len(ultimos_multipliers) if ultimos_multipliers else 1.5
        if media < 1.8:
            return 0.80
        elif media < 2.5:
            return 0.70
        else:
            return 0.60

    def shannon_entropy(self, sequencia):
        if not sequencia:
            return 0.5
        freq = {}
        for s in sequencia:
            freq[s] = freq.get(s, 0) + 1
        entropy = 0
        for f in freq.values():
            p = f / len(sequencia)
            entropy -= p * math.log2(p)
        return min(1.0, entropy / math.log2(len(freq))) if len(freq) > 1 else 0.5

    def predict(self, rodadas_recentes):
        if not rodadas_recentes:
            return 0.70
        
        estados = []
        for mult, tipo in rodadas_recentes[:10]:
            if mult < 1.5:
                estados.append('baixo')
            elif mult < 3.0:
                estados.append('medio')
            else:
                estados.append('alto')
        
        markov_score = self.markov_probability(estados)
        multipliers = [m for m, _ in rodadas_recentes[:10]]
        bayes_score = self.bayesian_inference(multipliers)
        entropy = self.shannon_entropy(estados)
        confidence = (markov_score * 0.35 + bayes_score * 0.25 + entropy * 0.20 + 0.20)
        
        total_predicoes = self.acertos + self.erros
        if total_predicoes > 10:
            bias = self.acertos / total_predicoes
            confidence = confidence * (0.8 + bias * 0.4)
        
        return min(0.95, max(0.55, confidence))

ml_engine = AetheriusML()

# ============================================
# MODO SNIPER COM CORES DIFERENTES
# ============================================
class SniperMode:
    def __init__(self):
        self.active = False
        self.trigger_time = None
        self.window_minutes = None
        self.alertas_cronometro = {5: False, 2: False, 1: False}
        self.sinal_enviado = False

    def activate(self, window_minutes):
        self.active = True
        self.trigger_time = datetime.now()
        self.window_minutes = window_minutes
        self.alertas_cronometro = {5: False, 2: False, 1: False}
        self.sinal_enviado = False
        
        # MENSAGEM VERDE para ativação
        msg = (
            "🟢🟢🟢 <b>MODO SNIPER ATIVADO!</b> 🟢🟢🟢\n"
            f"⏱️ <b>Janela de {window_minutes} minutos</b>\n"
            f"📈 <b>Confiança esperada: {self.get_confidence()}%</b>\n"
            "🟢🟢🟢 <b>PREPARE-SE!</b> 🟢🟢🟢"
        )
        send_telegram_message(msg, parse_mode='HTML')
    
    def get_confidence(self):
        if self.window_minutes == 3:
            return config.get('sniper_mode_confidence_3min', 85)
        elif self.window_minutes == 5:
            return config.get('sniper_mode_confidence_5min', 80)
        else:
            return config.get('sniper_mode_confidence_10min', 75)
    
    def check_and_alert(self, numero_rodada):
        if not self.active or self.sinal_enviado:
            return None
        
        elapsed = datetime.now() - self.trigger_time
        minutos_faltando = self.window_minutes - (elapsed.total_seconds() / 60)
        
        # ALERTAS DE CRONÔMETRO (AMARELO)
        for min_alerta in [5, 2, 1]:
            if min_alerta <= self.window_minutes:
                if (min_alerta - 0.2) < minutos_faltando <= min_alerta and not self.alertas_cronometro.get(min_alerta, False):
                    proxima_janela = datetime.now() + timedelta(minutes=minutos_faltando)
                    msg = (
                        "🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡\n"
                        f"⏰ <b>Janela em {min_alerta} MINUTOS!</b> ⏰\n"
                        f"📅 <b>Previsão:</b> {proxima_janela.strftime('%H:%M:%S')}\n"
                        f"🎯 <b>Prepare o cashout!</b>\n"
                        "🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡"
                    )
                    send_telegram_message(msg, parse_mode='HTML')
                    self.alertas_cronometro[min_alerta] = True
        
        # SINAL DE ENTRADA (VERMELHO + DESTAQUE MÁXIMO)
        if -0.2 < minutos_faltando <= 0.1 and not self.sinal_enviado:
            soma_velas = calcular_soma_velas_recentes()
            confianca = self.get_confidence()
            
            if confianca >= 85:
                alvo = 2.50
                protecao = 1.60
            elif confianca >= 75:
                alvo = 2.00
                protecao = 1.50
            else:
                alvo = 1.80
                protecao = 1.40
            
            # MENSAGEM VERMELHA ESTRIDENTE COM EMOJIS DE FOGO
            msg = (
                "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n"
                "🔥🚀🔥 <b>ENTRADA CONFIRMADA! HORA DE APOSTAR!</b> 🔥🚀🔥\n"
                "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n\n"
                f"🎯 <b>ALVO SUGERIDO:</b> <code>{alvo}x</code> 🎯\n"
                f"🛡️ <b>PROTEÇÃO:</b> <code>{protecao}x</code>\n\n"
                f"📊 <b>Soma de Velas Recente:</b> <code>{soma_velas:.2f}</code>\n"
                f"💎 <b>Confiança do ML:</b> <code>{confianca}%</code>\n"
                f"🆔 <b>Número da Rodada:</b> <code>{numero_rodada}</code>\n\n"
                "⚠️ <b>⏰ ENTRAR AGORA! ÚLTIMOS 30 SEGUNDOS!</b> ⚠️\n"
                "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴"
            )
            send_telegram_message(msg, parse_mode='HTML')
            self.sinal_enviado = True
            return True
        
        # MODO SNIPER FINALIZADO (AZUL)
        if minutos_faltando < -0.5:
            self.active = False
            msg = (
                "🔵🔵🔵 <b>MODO SNIPER FINALIZADO</b> 🔵🔵🔵\n"
                f"⏱️ Janela de {self.window_minutes} minutos encerrada.\n"
                "🔵🔵🔵 <b>AGUARDANDO PRÓXIMA VELA GIGANTE</b> 🔵🔵🔵"
            )
            send_telegram_message(msg, parse_mode='HTML')
        
        return None

sniper = SniperMode()

# ============================================
# SIMULAÇÃO DE MULTIPLICADOR
# ============================================
def get_current_multiplier():
    return round(random.uniform(1.00, 150.00), 2)

# ============================================
# ANÁLISE E PREDIÇÃO PRINCIPAL
# ============================================
def analyze_and_predict():
    current_multiplier = get_current_multiplier()
    numero_rodada = rodada_counter.next_round()
    
    db.add_rodada(numero_rodada, current_multiplier)
    
    HIGH_MULTIPLIER_THRESHOLD = config.get('high_multiplier_threshold', 50.0)
    
    if current_multiplier >= HIGH_MULTIPLIER_THRESHOLD:
        if current_multiplier >= 100:
            window = 3
        elif current_multiplier >= 70:
            window = 5
        else:
            window = 10
        
        # MENSAGEM VERDE DESTACADA
        msg = (
            "🟢🟢🟢 <b>VELA GIGANTE DETECTADA!</b> 🟢🟢🟢\n"
            f"📈 <b>Multiplicador: {current_multiplier}x</b>\n"
            f"🎯 <b>Ativando MODO SNIPER para {window} minutos</b>\n"
            "🟢🟢🟢 <b>PREPARE-SE PARA ENTRADA!</b> 🟢🟢🟢"
        )
        send_telegram_message(msg, parse_mode='HTML')
        sniper.activate(window)
        return
    
    if sniper.active:
        sniper.check_and_alert(numero_rodada)
        return
    
    rodadas_recentes = db.get_ultimas_rodadas(15)
    confidence = ml_engine.predict(rodadas_recentes)
    
    if confidence >= 0.75:
        soma_velas = calcular_soma_velas_recentes()
        alvo = round(2.00 + (confidence - 0.70) * 2, 2)
        protecao = round(1.40 + (confidence - 0.70), 2)
        
        msg = (
            "📊 <b>AETHERIUS PREDICTOR - Análise Preditiva</b>\n"
            "------------------------------------------\n"
            f"🎯 <b>Alvo Sugerido:</b> {alvo}x\n"
            f"🛡️ <b>Proteção:</b> {protecao}x\n"
            f"📊 <b>Soma de Velas Recente:</b> {soma_velas:.2f}\n"
            f"💎 <b>Confiança do ML:</b> {int(confidence*100)}%\n"
            f"🆔 <b>Número da Rodada:</b> {numero_rodada}"
        )
        send_telegram_message(msg, parse_mode='HTML')

# ============================================
# SERVIDOR HEALTH CHECK PARA O RENDER
# ============================================
def run_health_server():
    """Mantém o bot vivo no Render"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'AETHERIUS PREDICTOR ML v4.0 - Bot is running!')
        
        def log_message(self, format, *args):
            pass  # Silencia os logs do health check
    
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

# ============================================
# MENSAGEM DE BOAS-VINDAS COLORIDA
# ============================================
def send_welcome_message():
    msg = (
        "🎰🎰🎰 <b>AETHERIUS PREDICTOR ML v4.0</b> 🎰🎰🎰\n\n"
        "✅ <b>Bot iniciado com sucesso no Render!</b>\n\n"
        "🎯 <b>Modo Sniper ativado</b> (Velas >50x)\n"
        "📊 <b>Machine Learning:</b> Markov + Bayes + Entropia\n"
        "⏰ <b>Monitorando rodadas 24/7</b>\n\n"
        "🟢 <b>VELHA GIGANTE</b> = Ativa sniper\n"
        "🟡 <b>ALERTA AMARELO</b> = Prepare-se\n"
        "🔴 <b>ALERTA VERMELHO</b> = ENTRAR AGORA!\n"
        "🔵 <b>ALERTA AZUL</b> = Janela encerrada\n\n"
        "<b>Boa sorte! 🍀</b>"
    )
    send_telegram_message(msg, parse_mode='HTML')

# ============================================
# MAIN
# ============================================
def main():
    print("🚀 AETHERIUS PREDICTOR ML v4.0 (Aprimorado) iniciado...")
    print(f"✅ Bot do Telegram ativo: @betouaviator_bot")
    print(f"📊 Configurações carregadas")
    print("⏳ Aguardando rodadas...\n")
    
    # Envia mensagem de boas-vindas colorida
    send_welcome_message()
    
    while True:
        analyze_and_predict()
        intervalo = random.uniform(25, 45)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Aguardando {intervalo:.1f} segundos...")
        time.sleep(intervalo)

if __name__ == "__main__":
    # Inicia o servidor de health check em uma thread separada
    import threading
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Inicia o bot principal
    main()
