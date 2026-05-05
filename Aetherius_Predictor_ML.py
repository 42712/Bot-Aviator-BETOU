import json
import time
import random
import os
import requests
from datetime import datetime, timedelta

# ==============================
# CONFIG TELEGRAM (SEGURO)
# ==============================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==============================
# CARREGAR CONFIG
# ==============================
def load_brain_config(config_path='aetherius_brain_config.json'):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar config: {e}")
        return {
            "estatisticas_gerais": {},
            "intervalos_medios": {},
            "melhores_horas": [],
            "padrao_100x": 1
        }

config = load_brain_config()

# ==============================
# TELEGRAM REAL (CORRIGIDO)
# ==============================
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Token ou Chat ID não configurados")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        })
        print(f"[TELEGRAM] {response.status_code} - {message}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

# ==============================
# SIMULAÇÃO
# ==============================
def get_current_multiplier():
    return round(random.uniform(1.00, 150.00), 2)

# ==============================
# LÓGICA
# ==============================
last_high_multiplier_event = None
HIGH_MULTIPLIER_THRESHOLD = 50.0

def analyze_and_predict(current_multiplier):
    global last_high_multiplier_event

    if current_multiplier >= HIGH_MULTIPLIER_THRESHOLD:
        send_telegram_message(f"🚨 VELA GIGANTE: {current_multiplier}x 🎯")
        last_high_multiplier_event = datetime.now()
        return

    if last_high_multiplier_event:
        elapsed = datetime.now() - last_high_multiplier_event

        for minutes, conf in [(3,85), (5,80), (10,75)]:
            if elapsed < timedelta(minutes=minutes):
                remaining = timedelta(minutes=minutes) - elapsed
                if timedelta(seconds=1) <= remaining <= timedelta(seconds=30):
                    send_telegram_message(
                        f"⏳ ENTRADA AGORA ({minutes}min) Confiança: {conf}%"
                    )
                    last_high_multiplier_event = None
                    return

        if elapsed > timedelta(minutes=10):
            last_high_multiplier_event = None

    if random.random() < 0.3:
        conf = random.randint(60, 75)
        target = random.choice([1.5, 2.0, 2.5])
        send_telegram_message(
            f"📊 Previsão: > {target}x | Confiança: {conf}%"
        )

# ==============================
# LOOP PRINCIPAL (FIX)
# ==============================
def main():
    print("🚀 Aetherius rodando...")
    print("TOKEN:", "OK" if TELEGRAM_BOT_TOKEN else "FALTA")
    print("CHAT_ID:", TELEGRAM_CHAT_ID)

    while True:
        try:
            mult = get_current_multiplier()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {mult}x")
            analyze_and_predict(mult)
            time.sleep(random.uniform(10, 20))
        except Exception as e:
            print(f"Erro no loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
