import os
import json
import sqlite3
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Banco de dados
conn = sqlite3.connect('aetherius_history.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS rodadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_rodada INTEGER,
        multiplicador REAL,
        horario TEXT,
        timestamp DATETIME,
        source TEXT
    )
''')
conn.commit()

# Config Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8795312239:AAG5O0l_anyQN-3_ED2BZqNTjCSxjuOoqz8')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5786799110')

# Estado do sniper
sniper_active = False
sniper_trigger_time = None
sniper_window = None
sniper_multiplier = None
sniper_rodada = None
sniper_horario = None
sniper_alerts = {3: False, 2: False, 1: False}
sniper_sent = False

def send_telegram_message(message, sound_alert=False):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if sound_alert:
        message = "🔊🔊🔊 *SINAL FORTE!* 🔊🔊🔊\n\n" + message
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"[TELEGRAM] {r.status_code}")
    except Exception as e:
        print(f"[ERRO] {e}")

@app.route('/api/rodada', methods=['POST'])
def receber_rodada():
    global sniper_active, sniper_trigger_time, sniper_window
    global sniper_multiplier, sniper_rodada, sniper_horario, sniper_alerts, sniper_sent
    
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data'}), 400
    
    rodada = data.get('rodada')
    multiplier = data.get('multiplier')
    horario = data.get('horario')
    source = data.get('source', 'extension')
    
    print(f"📥 RECEBIDO: Rodada {rodada} | {multiplier}x | {horario}")
    
    # Salvar no banco
    cursor.execute('''
        INSERT INTO rodadas (numero_rodada, multiplicador, horario, timestamp, source)
        VALUES (?, ?, ?, ?, ?)
    ''', (rodada, multiplier, horario, datetime.now(), source))
    conn.commit()
    
    # VERIFICA MODO SNIPER (vela gigante)
    if multiplier >= 30:
        if multiplier >= 100:
            window = 3
        elif multiplier >= 70:
            window = 5
        elif multiplier >= 50:
            window = 7
        else:
            window = 10
        
        sniper_active = True
        sniper_trigger_time = datetime.now()
        sniper_window = window
        sniper_multiplier = multiplier
        sniper_rodada = rodada
        sniper_horario = horario
        sniper_alerts = {3: False, 2: False, 1: False}
        sniper_sent = False
        
        msg = f"""🟢 *VELA GIGANTE CAPTURADA!*
📈 {multiplier}x
🆔 Rodada: {rodada}
⏰ {horario}
🎯 Modo Sniper ativado por {window} minutos!"""
        send_telegram_message(msg)
        
        # Inicia thread de monitoramento
        threading.Thread(target=monitorar_sniper, daemon=True).start()
    
    return jsonify({'status': 'ok', 'sniper_active': sniper_active})

def monitorar_sniper():
    global sniper_active, sniper_sent, sniper_alerts
    global sniper_window, sniper_trigger_time, sniper_multiplier
    
    start_time = sniper_trigger_time
    window_min = sniper_window
    
    while sniper_active:
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        remaining = window_min - elapsed
        
        # Alertas progressivos
        for alert_min in [3, 2, 1]:
            if alert_min <= window_min:
                if remaining <= alert_min and remaining > (alert_min - 0.2) and not sniper_alerts.get(alert_min, False):
                    msg = f"⏰ *ALERTA PROGRESSIVO*\n⏳ Faltam {alert_min} minuto(s)!\n🎯 Prepare o cashout automático!"
                    send_telegram_message(msg)
                    sniper_alerts[alert_min] = True
        
        # Sinal de entrada
        if remaining <= 0.05 and not sniper_sent:
            confianca = 85 if window_min == 3 else 80 if window_min == 5 else 75
            alvo = 2.50 if confianca >= 85 else 2.00 if confianca >= 75 else 1.80
            protecao = 1.60 if confianca >= 85 else 1.50 if confianca >= 75 else 1.40
            
            msg = f"""🚀 *AETHERIUS: ENTRADA CONFIRMADA!* 🚀

🎯 *Entrar AGORA!*
📊 *Vela gatilho:* {sniper_multiplier}x
🎯 *Alvo:* {alvo}x
🛡️ *Proteção:* {protecao}x
💎 *Confiança:* {confianca}%

⏰ *Janela encerrando AGORA!*"""
            send_telegram_message(msg, sound_alert=True)
            sniper_sent = True
        
        if remaining < -0.1:
            sniper_active = False
            send_telegram_message(f"✅ *SNIPER FINALIZADO*\nJanela de {window_min} min encerrada.")
            break
        
        time.sleep(1)

@app.route('/api/status', methods=['GET'])
def status():
    cursor.execute('SELECT COUNT(*) FROM rodadas')
    total = cursor.fetchone()[0]
    return jsonify({
        'status': 'online',
        'total_rodadas': total,
        'sniper_active': sniper_active
    })

@app.route('/api/ultimas', methods=['GET'])
def ultimas():
    cursor.execute('SELECT numero_rodada, multiplicador, horario FROM rodadas ORDER BY id DESC LIMIT 20')
    rows = cursor.fetchall()
    return jsonify([{'rodada': r[0], 'multiplier': r[1], 'horario': r[2]} for r in rows])

@app.route('/')
def home():
    return "AETHERIUS PREDICTOR API - Online!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
