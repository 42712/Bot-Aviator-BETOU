import json
import time
import random
import sqlite3
import math
from datetime import datetime, timedelta
from collections import deque

# --- Configurações do Bot ---
TELEGRAM_BOT_TOKEN = '8795312239:AAG5O0l_anyQN-3_ED2BZqNTjCSxjuOoqz8'
TELEGRAM_CHAT_ID = '8795312239'

# Carregar configurações do cérebro
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

# --- Banco de dados SQLite para histórico de rodadas ---
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

# --- Simulação do contador de rodadas ---
class RodadaCounter:
    def __init__(self):
        self.current_round = 47897589  # Número da rodada inicial

    def next_round(self):
        self.current_round += random.randint(1, 5)
        return self.current_round

rodada_counter = RodadaCounter()

# --- Função para enviar mensagem ao Telegram (REAL) ---
import requests

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[OK] Mensagem enviada: {message[:50]}...")
        else:
            print(f"[ERRO] Telegram: {response.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar: {e}")

# --- Cálculo da Soma de Velas Recentes ---
def calcular_soma_velas_recentes():
    rodadas = db.get_ultimas_rodadas(10)
    soma = sum(r[0] for r in rodadas if r[0] < 50)  # ignora outliers >50x
    return round(soma, 2)

# --- Lógica de Machine Learning (Markov + Bayes) ---
class AetheriusML:
    def __init__(self):
        self.historico_multipliers = deque(maxlen=30)
        self.acertos = 0
        self.erros = 0

    def markov_probability(self, ultimos_estados):
        # Simula cadeia de Markov ordem 1/2/3
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
        # Inferência Bayesiana simplificada
        media = sum(ultimos_multipliers) / len(ultimos_multipliers) if ultimos_multipliers else 1.5
        if media < 1.8:
            return 0.80
        elif media < 2.5:
            return 0.70
        else:
            return 0.60

    def shannon_entropy(self, sequencia):
        # Mede o caos das últimas rodadas
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
        
        # Classifica estados
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
        
        # Calibração de viés
        total_predicoes = self.acertos + self.erros
        if total_predicoes > 10:
            bias = self.acertos / total_predicoes
            confidence = confidence * (0.8 + bias * 0.4)
        
        return min(0.95, max(0.55, confidence))

ml_engine = AetheriusML()

# --- Modo Sniper com Cronômetro ---
class SniperMode:
    def __init__(self):
        self.active = False
        self.trigger_time = None
        self.window_minutes = None  # 3, 5 ou 10
        self.alertas_cronometro = {5: False, 2: False, 1: False}
        self.sinal_enviado = False

    def activate(self, window_minutes):
        self.active = True
        self.trigger_time = datetime.now()
        self.window_minutes = window_minutes
        self.alertas_cronometro = {5: False, 2: False, 1: False}
        self.sinal_enviado = False
        send_telegram_message(f"🎯 *MODO SNIPER ATIVADO!*\n⏱️ Janela de {window_minutes} minutos.\n📈 Confiança esperada: {self.get_confidence()}%")
    
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
        
        # Alertas de cronômetro (5, 2, 1 minuto)
        for min_alerta in [5, 2, 1]:
            if min_alerta <= self.window_minutes:
                if (min_alerta - 0.2) < minutos_faltando <= min_alerta and not self.alertas_cronometro.get(min_alerta, False):
                    proxima_janela = datetime.now() + timedelta(minutes=minutos_faltando)
                    send_telegram_message(
                        f"⏳ *AETHERIUS PREDICTOR:* Janela de oportunidade em {min_alerta} minutos.\n"
                        f"⏰ Previsão: {proxima_janela.strftime('%H:%M')}"
                    )
                    self.alertas_cronometro[min_alerta] = True
        
        # Sinal de entrada (últimos 10 segundos da janela)
        if -0.2 < minutos_faltando <= 0.1 and not self.sinal_enviado:
            soma_velas = calcular_soma_velas_recentes()
            confianca = self.get_confidence()
            
            # Determina alvo e proteção baseado na confiança
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
                f"🚀 *AETHERIUS PREDICTOR: ENTRADA CONFIRMADA!* 🚀\n"
                f"------------------------------------------\n"
                f"🎯 *Alvo Sugerido:* {alvo}x\n"
                f"🛡️ *Proteção:* {protecao}x\n"
                f"📊 *Soma de Velas Recente:* {soma_velas:.2f}\n"
                f"💎 *Confiança do ML:* {confianca}%\n"
                f"🆔 *Número da Rodada:* {numero_rodada}"
            )
            send_telegram_message(msg)
            self.sinal_enviado = True
            return True
        
        # Reseta se passou da janela
        if minutos_faltando < -0.5:
            self.active = False
            send_telegram_message(f"✅ *MODO SNIPER FINALIZADO*\n⏱️ Janela de {self.window_minutes} minutos encerrada.")
        
        return None

sniper = SniperMode()

# --- Função principal de análise ---
def get_current_multiplier():
    # Simula multiplicador atual
    return round(random.uniform(1.00, 150.00), 2)

def analyze_and_predict():
    current_multiplier = get_current_multiplier()
    numero_rodada = rodada_counter.next_round()
    
    # Salva no banco de dados
    db.add_rodada(numero_rodada, current_multiplier)
    
    # Detecção de Vela Gigante (>50x)
    HIGH_MULTIPLIER_THRESHOLD = config.get('high_multiplier_threshold', 50.0)
    
    if current_multiplier >= HIGH_MULTIPLIER_THRESHOLD:
        # Decide qual janela usar baseado no multiplicador
        if current_multiplier >= 100:
            window = 3
            confidence = 85
        elif current_multiplier >= 70:
            window = 5
            confidence = 80
        else:
            window = 10
            confidence = 75
        
        send_telegram_message(
            f"🚨 *VELA GIGANTE DETECTADA!*\n"
            f"📈 Multiplicador: {current_multiplier}x\n"
            f"🎯 Ativando MODO SNIPER para {window} minutos\n"
            f"💎 Confiança esperada: {confidence}%"
        )
        sniper.activate(window)
        return
    
    # Verifica se está em modo sniper
    if sniper.active:
        resultado = sniper.check_and_alert(numero_rodada)
        return
    
    # Predição normal (quando não está em sniper)
    rodadas_recentes = db.get_ultimas_rodadas(15)
    confidence = ml_engine.predict(rodadas_recentes)
    
    # Decide se envia alerta baseado na confiança
    if confidence >= 0.75:
        soma_velas = calcular_soma_velas_recentes()
        alvo = round(2.00 + (confidence - 0.70) * 2, 2)
        protecao = round(1.40 + (confidence - 0.70), 2)
        
        msg = (
            f"📊 *AETHERIUS PREDICTOR - Análise Preditiva*\n"
            f"------------------------------------------\n"
            f"🎯 *Alvo Sugerido:* {alvo}x\n"
            f"🛡️ *Proteção:* {protecao}x\n"
            f"📊 *Soma de Velas Recente:* {soma_velas:.2f}\n"
            f"💎 *Confiança do ML:* {int(confidence*100)}%\n"
            f"🆔 *Número da Rodada:* {numero_rodada}"
        )
        send_telegram_message(msg)

# --- Loop Principal ---
def main():
    print("🚀 Aetherius Predictor ML v4.0 (Aprimorado) iniciado...")
    print(f"✅ Bot do Telegram ativo: @betouaviator_bot")
    print(f"📊 Configurações carregadas: {config}")
    print("⏳ Aguardando rodadas...\n")
    
    while True:
        analyze_and_predict()
        # Intervalo entre rodadas (simula tempo real do jogo)
        intervalo = random.uniform(25, 45)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Aguardando {intervalo:.1f} segundos...")
        time.sleep(intervalo)

if __name__ == "__main__":
    main()
