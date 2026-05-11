import os
import json
import sqlite3
import threading
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Banco
conn = sqlite3.connect('aetherius.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS rodadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_rodada INTEGER,
        multiplicador REAL,
        horario TEXT,
        timestamp DATETIME
    )
''')
conn.commit()

# Telegram
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8795312239:AAG5O0l_anyQN-3_ED2BZqNTjCSxjuOoqz8')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5786799110')

def send_tg(msg, sound=False):
    if sound:
        msg = "🔊🔊🔊 *SINAL FORTE!* 🔊🔊🔊\n\n" + msg
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                     json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Erro: {e}")

# Sniper
sniper = {'active': False, 'trigger': None, 'window': 0, 'mult': 0, 'rodada': 0, 'alerts': {}, 'sent': False}

def monitor_sniper():
    while sniper['active']:
        elapsed = (datetime.now() - sniper['trigger']).total_seconds() / 60
        remaining = sniper['window'] - elapsed
        
        for m in [3,2,1]:
            if m <= sniper['window'] and remaining <= m and remaining > (m-0.2) and not sniper['alerts'].get(m, False):
                send_tg(f"⏰ Alerta! Faltam {m} minuto(s)!")
                sniper['alerts'][m] = True
        
        if remaining <= 0.05 and not sniper['sent']:
            conf = 85 if sniper['window'] == 3 else 80 if sniper['window'] == 5 else 75
            alvo = 2.50 if conf >= 85 else 2.00
            prot = 1.60 if conf >= 85 else 1.50
            send_tg(f"🚀 *ENTRADA CONFIRMADA!*\n🎯 Alvo: {alvo}x\n🛡️ Proteção: {prot}x\n💎 Confiança: {conf}%", sound=True)
            sniper['sent'] = True
        
        if remaining < -0.1:
            sniper['active'] = False
            send_tg(f"✅ Sniper finalizado - Janela de {sniper['window']} min encerrada.")
            break
        
        time.sleep(1)

@app.route('/api/rodada', methods=['POST'])
def rodada():
    global sniper
    data = request.json
    rodada = data.get('rodada')
    mult = data.get('multiplier')
    horario = data.get('horario')
    
    cursor.execute('INSERT INTO rodadas (numero_rodada, multiplicador, horario, timestamp) VALUES (?,?,?,?)',
                   (rodada, mult, horario, datetime.now()))
    conn.commit()
    
    print(f"📥 Rodada {rodada}: {mult}x")
    
    if mult >= 30:
        window = 3 if mult >= 100 else 5 if mult >= 70 else 7 if mult >= 50 else 10
        sniper = {
            'active': True, 'trigger': datetime.now(), 'window': window,
            'mult': mult, 'rodada': rodada, 'alerts': {3:False,2:False,1:False}, 'sent': False
        }
        send_tg(f"🟢 *VELA GIGANTE!* {mult}x\n🎯 Sniper ativado por {window} minutos")
        threading.Thread(target=monitor_sniper, daemon=True).start()
    
    return jsonify({'status': 'ok', 'sniper_active': sniper['active']})

@app.route('/api/status', methods=['GET'])
def status():
    cursor.execute('SELECT COUNT(*) FROM rodadas')
    total = cursor.fetchone()[0]
    return jsonify({'status': 'online', 'total_rodadas': total, 'sniper_active': sniper['active']})

@app.route('/')
def home():
    return 'AETHERIUS API Online'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)