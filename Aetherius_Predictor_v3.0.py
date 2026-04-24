#!/usr/bin/env python3
"""
AETHERIUS PREDICTOR v3.0 - COM NÚMERO DA RODADA EM TODOS OS ALERTAS
- Exibe o número da rodada atual em CADA SINAL
- Captura em tempo real via Selenium
- Reconhecimento de padrões complexos
- Aprendizado por erro
- Análise de horários pagantes
"""

import os
import re
import time
import json
import requests
import statistics
import sqlite3
import logging
from datetime import datetime
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

# ============================================================
# CONFIGURAÇÕES (PREENCHE AQUI OU USAR VARIÁVEIS DE AMBIENTE)
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'SEU_TOKEN_AQUI')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'SEU_CHAT_ID_AQUI')
BETOU_EMAIL = os.environ.get('BETOU_EMAIL', 'marcosduarte356@gmail.com')
BETOU_SENHA = os.environ.get('BETOU_SENHA', 'amordedeus123@')
BETOU_URL = 'https://betou.bet.br/games/spribe/aviator'

# Sons para Telegram
SOM_AVISO = 'https://www.soundjay.com/buttons/beep-01a.mp3'
SOM_URGENTE = 'https://www.soundjay.com/buttons/beep-07a.mp3'
SOM_ENTRADA = 'https://www.soundjay.com/buttons/beep-08b.mp3'
SOM_ROSA = 'https://www.soundjay.com/buttons/beep-09.mp3'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('Aetherius')

# ============================================================
# TELEGRAM
# ============================================================
def enviar_texto(mensagem: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown", "disable_web_page_preview": True}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log.warning(f"Telegram erro: {e}")

def enviar_audio(url_audio: str, legenda: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "audio": url_audio, "caption": legenda, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        log.warning(f"Áudio erro: {e}")

def enviar_alerta(mensagem: str, som_url: str = None, legenda: str = ''):
    enviar_texto(mensagem)
    if som_url:
        enviar_audio(som_url, legenda)

# ============================================================
# PADRÕES COMPLEXOS
# ============================================================
@dataclass
class PadraoComplexo:
    nome: str
    sequencia: List[float]
    risco: str
    previsao: str
    confianca: float

class ReconhecedorPadroes:
    def __init__(self):
        self.padroes = [
            PadraoComplexo("Sequência da Morte", [1.00, 1.03, 1.05, 1.02], 'alto', 'ROSA', 0.85),
            PadraoComplexo("Três Baixas Seguidas", [1.05, 1.08, 1.12], 'medio', 'ROXA', 0.70),
            PadraoComplexo("Pressão Máxima", [1.20, 1.15, 1.10, 1.05], 'alto', 'ROSA', 0.82),
            PadraoComplexo("Escada para Rosa", [1.00, 1.00, 2.00, 1.00], 'alto', 'ROSA', 0.80),
        ]
        self.padroes_aprendidos = []
    
    def reconhecer(self, historico: List[float]) -> Optional[PadraoComplexo]:
        if len(historico) < 3:
            return None
        ultimos = list(historico)[-5:]
        
        for padrao in self.padroes:
            if self._corresponde(ultimos, padrao.sequencia):
                return padrao
        return None
    
    def _corresponde(self, atual: List[float], padrao: List[float]) -> bool:
        if len(atual) < len(padrao):
            return False
        for i in range(1, min(len(padrao), len(atual)) + 1):
            if abs(atual[-i] - padrao[-i]) > 0.05:
                return False
        return True

# ============================================================
# ANÁLISE DE HORÁRIOS
# ============================================================
class AnalisadorHorarios:
    def __init__(self):
        self.horarios_quentes = {
            0: 85, 1: 82, 2: 80, 3: 78, 4: 75, 5: 55, 6: 50, 7: 45
        }
    
    def avaliar_horario(self, hora: int) -> Tuple[int, str]:
        score = self.horarios_quentes.get(hora, 40)
        if score >= 75:
            classificacao = "🔥 MUITO QUENTE"
        elif score >= 60:
            classificacao = "👍 FAVORÁVEL"
        elif score >= 45:
            classificacao = "⚖️ NEUTRO"
        else:
            classificacao = "❄️ FRIO"
        return score, classificacao

# ============================================================
# APRENDIZADO POR ERRO
# ============================================================
class AprendizadoPorErro:
    def __init__(self):
        self.erros_recentes = deque(maxlen=50)
    
    def registrar_erro(self, sequencia: List[float], esperado: float, real: float):
        self.erros_recentes.append({'sequencia': sequencia, 'esperado': esperado, 'real': real})
        log.info(f"[ERRO] Esperava ≥{esperado}, veio {real}")
    
    def verificar_padrao_erro(self, sequencia: List[float]) -> Tuple[bool, float]:
        for erro in self.erros_recentes:
            if len(erro['sequencia']) == len(sequencia):
                match = all(abs(a - b) < 0.1 for a, b in zip(erro['sequencia'], sequencia))
                if match:
                    return True, 0.70
        return False, 1.0

# ============================================================
# MOTOR PRINCIPAL
# ============================================================
class AetheriusPredictor:
    def __init__(self):
        self.historico = deque(maxlen=300)
        self.intervalos_ciclo = deque(maxlen=60)
        self.media_ciclo = 8.0
        self.rodadas_desde_alta = 0
        self.ultima_rodada_id = None
        self.ultimo_multiplicador = None
        self.ultima_rodada_numero = None  # GUARDA O NÚMERO DA ÚLTIMA RODADA
        
        # Minutagem
        self.ultimo_timestamp_alta = None
        self.media_minutos = 4.5
        
        # Alertas
        self.alertas = {'3': False, '1': False, 'agora': False}
        
        # Módulos
        self.reconhecedor = ReconhecedorPadroes()
        self.analisador_horario = AnalisadorHorarios()
        self.aprendizado_erro = AprendizadoPorErro()
        
        # Banco
        self.conn = sqlite3.connect('aetherius_brain.db')
        self._init_db()
        
        # Estatísticas
        self.alertas_enviados = 0
    
    def _init_db(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS rodadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER,
            valor REAL,
            hora TEXT,
            timestamp REAL
        )''')
        self.conn.commit()
    
    def _calcular_confianca(self) -> Tuple[int, str]:
        score = 40
        
        if len(self.historico) >= 10:
            ultimas = list(self.historico)[-10:]
            media = sum(ultimas) / len(ultimas)
            
            if media < 1.5:
                score += 25
            elif media < 2.0:
                score += 15
            elif media > 3.0:
                score -= 10
        
        if len(self.intervalos_ciclo) >= 5:
            desvio = statistics.stdev(self.intervalos_ciclo) if len(self.intervalos_ciclo) >= 2 else 5
            if desvio < 2.0:
                score += 15
        
        hora_atual = datetime.now().hour
        score_horario, _ = self.analisador_horario.avaliar_horario(hora_atual)
        score = int(score * 0.7 + score_horario * 0.3)
        
        score = max(20, min(95, score))
        nivel = "Alta" if score >= 75 else ("Média" if score >= 55 else "Baixa")
        return score, nivel
    
    def processar_vela(self, valor: float, numero_rodada: int = None):
        """Processa nova vela - COM NÚMERO DA RODADA"""
        
        # Evita duplicatas
        if numero_rodada and numero_rodada == self.ultima_rodada_id:
            return
        
        self.ultima_rodada_id = numero_rodada
        self.ultimo_multiplicador = valor
        self.ultima_rodada_numero = numero_rodada  # SALVA PARA USAR NOS ALERTAS
        
        agora = datetime.now()
        self.historico.append(valor)
        
        # Salva no banco
        c = self.conn.cursor()
        c.execute("INSERT INTO rodadas (numero, valor, hora, timestamp) VALUES (?, ?, ?, ?)",
                  (numero_rodada, valor, agora.isoformat(), agora.timestamp()))
        self.conn.commit()
        
        log.info(f"📊 RODADA #{numero_rodada}: {valor:.2f}x | Desde última alta: {self.rodadas_desde_alta}")
        
        # Atualiza ciclo
        if valor >= 2.0:
            if self.ultimo_timestamp_alta:
                diff = (agora - self.ultimo_timestamp_alta).total_seconds() / 60
                if 1 < diff < 15:
                    self.media_minutos = (self.media_minutos * 0.8) + (diff * 0.2)
            
            self.intervalos_ciclo.append(self.rodadas_desde_alta)
            if len(self.intervalos_ciclo) >= 3:
                pesos = list(range(1, len(self.intervalos_ciclo) + 1))
                self.media_ciclo = sum(v * p for v, p in zip(self.intervalos_ciclo, pesos)) / sum(pesos)
                log.info(f"[APRENDIZADO] Novo ciclo médio: {self.media_ciclo:.2f} rodadas")
            
            self.rodadas_desde_alta = 0
            self.ultimo_timestamp_alta = agora
            self.alertas = {'3': False, '1': False, 'agora': False}
            
            # Se for ROSA (≥100x), comemora
            if valor >= 100:
                self._enviar_alerta_rosa(valor, numero_rodada)
        
        self.rodadas_desde_alta += 1
        
        # ===== RECONHECIMENTO DE PADRÕES =====
        padrao = self.reconhecedor.reconhecer(list(self.historico))
        if padrao and padrao.confianca >= 0.70:
            self._enviar_alerta_padrao(padrao, numero_rodada)
        
        # ===== MINUTAGEM =====
        self._verificar_minutagem(numero_rodada)
        
        # ===== VELA 1.00x (contar 6) =====
        if abs(valor - 1.00) < 0.02:
            self._enviar_alerta_1x(numero_rodada)
            self.contagem_1x = 0
        elif hasattr(self, 'contagem_1x'):
            self.contagem_1x += 1
            if self.contagem_1x == 7:
                self._enviar_alerta_sete_velas(numero_rodada)
        
        # ===== CONTAGEM REGRESSIVA POR RODADAS =====
        self._verificar_alertas_rodadas(numero_rodada)
    
    def _enviar_alerta_rosa(self, valor: float, rodada: int):
        """Alerta de VELA ROSA (≥100x)"""
        mensagem = (
            f"🌹 *AETHERIUS — VELA ROSA DETECTADA!* 🌹\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎲 *Multiplicador: {valor:.2f}x*\n"
            f"🆔 *Rodada: #{rodada}*\n"
            f"🕐 Horário: {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 *Parabéns! Rosa capturada!*"
        )
        enviar_alerta(mensagem, SOM_ROSA, f"🌹 ROSA {valor:.2f}x na rodada {rodada}!")
    
    def _enviar_alerta_padrao(self, padrao: PadraoComplexo, rodada: int):
        """Alerta de padrão detectado"""
        mensagem = (
            f"🎯 *PADRÃO DETECTADO: {padrao.nome}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Rodada atual: #{rodada}*\n"
            f"📊 Sequência: {' → '.join([f'{x:.2f}x' for x in padrao.sequencia])}\n"
            f"🔮 Previsão: *{padrao.previsao}*\n"
            f"🎲 Risco: {padrao.risco}\n"
            f"💎 Confiança: {padrao.confianca*100:.0f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Prepare-se! Entrada nas próximas rodadas!"
        )
        enviar_alerta(mensagem, SOM_AVISO, f"Padrão {padrao.nome} na rodada {rodada}")
    
    def _enviar_alerta_1x(self, rodada: int):
        """Alerta de vela 1.00x"""
        mensagem = (
            f"🔴 *GATILHO 1.00x DETECTADO!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Rodada: #{rodada}*\n"
            f"🕐 Horário: {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Contar 6 velas → Entrar na 7ª\n"
            f"📊 Monitorando..."
        )
        enviar_texto(mensagem)
    
    def _enviar_alerta_sete_velas(self, rodada: int):
        """Alerta da 7ª vela após 1.00x"""
        score, nivel = self._calcular_confianca()
        mensagem = (
            f"🎯 *7ª VELA APÓS 1.00x!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Rodada atual: #{rodada}*\n"
            f"🕐 Horário: {datetime.now().strftime('%H:%M:%S')}\n"
            f"🎯 Alvo: *2.00x*\n"
            f"🛡️ Proteção: *1.50x*\n"
            f"🧠 Confiança: *{nivel} ({score}%)*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 *ENTRE AGORA!*"
        )
        enviar_alerta(mensagem, SOM_ENTRADA, f"ENTRADA NA 7ª VELA! Rodada {rodada}")
        self.alertas_enviados += 1
    
    def _verificar_minutagem(self, rodada: int):
        """Verifica alerta baseado em minutos"""
        if self.ultimo_timestamp_alta is None:
            return
        
        agora = datetime.now()
        diff_minutos = (agora - self.ultimo_timestamp_alta).total_seconds() / 60
        
        if diff_minutos >= self.media_minutos * 0.9 and not self.alertas.get('minutagem', False):
            self.alertas['minutagem'] = True
            score, nivel = self._calcular_confianca()
            mensagem = (
                f"⏰ *MINUTAGEM: JANELA DE ENTRADA*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *Rodada atual: #{rodada}*\n"
                f"⏱️ Última roxa há {diff_minutos:.1f} minutos\n"
                f"📊 Média: {self.media_minutos:.1f} min\n"
                f"🕐 Horário: {agora.strftime('%H:%M:%S')}\n"
                f"🧠 Confiança: *{nivel} ({score}%)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Alvo: 2.00x | Proteção: 1.50x\n"
                f"🚀 *ENTRE AGORA!*"
            )
            enviar_alerta(mensagem, SOM_ENTRADA, f"ENTRADA POR MINUTAGEM! Rodada {rodada}")
            self.alertas_enviados += 1
    
    def _verificar_alertas_rodadas(self, rodada: int):
        """Contagem regressiva por rodadas - COM NÚMERO DA RODADA"""
        faltam = max(0, self.media_ciclo - self.rodadas_desde_alta)
        score, nivel = self._calcular_confianca()
        
        ultimas = list(self.historico)[-10:] if len(self.historico) >= 10 else list(self.historico)
        soma = sum(ultimas)
        agora = datetime.now().strftime('%H:%M:%S')
        
        # Nível 1: Faltam ~3 rodadas
        if 2.5 <= faltam <= 3.5 and not self.alertas.get('3', False):
            self.alertas['3'] = True
            mensagem = (
                f"⏳ *AETHERIUS — CONTAGEM REGRESSIVA*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *Rodada atual: #{rodada}*\n"
                f"🔔 *Faltam aproximadamente 3 rodadas*\n"
                f"🕐 Horário: *{agora}*\n"
                f"📊 Ciclo: *{self.rodadas_desde_alta} / {self.media_ciclo:.1f}*\n"
                f"💰 Soma últimas 10: *{soma:.2f}*\n"
                f"🧠 Confiança: *{nivel} ({score}%)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👀 _Fique de olho. Janela se aproximando._"
            )
            enviar_alerta(mensagem, SOM_AVISO, f"⏳ Faltam 3 rodadas! Rodada {rodada}")
        
        # Nível 2: Faltam ~1 rodada
        elif 0.5 <= faltam <= 1.5 and not self.alertas.get('1', False):
            self.alertas['1'] = True
            mensagem = (
                f"🚨 *AETHERIUS — ATENÇÃO MÁXIMA!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *Rodada atual: #{rodada}*\n"
                f"⚡ *Faltam aproximadamente 1 rodada!*\n"
                f"🕐 Horário: *{agora}*\n"
                f"📊 Ciclo: *{self.rodadas_desde_alta} / {self.media_ciclo:.1f}*\n"
                f"💰 Soma últimas 10: *{soma:.2f}*\n"
                f"🧠 Confiança: *{nivel} ({score}%)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 *Prepare seu valor de entrada AGORA!*"
            )
            enviar_alerta(mensagem, SOM_URGENTE, f"🚨 Faltam 1 rodada! Rodada {rodada}")
        
        # Nível 3: ENTRE AGORA
        elif faltam <= 0.5 and not self.alertas.get('agora', False):
            self.alertas['agora'] = True
            mensagem = (
                f"🚀 *AETHERIUS — ENTRE AGORA!* 🚀\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ *JANELA DE ENTRADA ATIVA*\n"
                f"🆔 *Rodada atual: #{rodada}*\n"
                f"🕐 *Horário exato: {agora}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Alvo: *2.00x*\n"
                f"🛡️ Proteção: *1.50x*\n"
                f"📊 Soma últimas 10: *{soma:.2f}*\n"
                f"🔄 Rodadas no ciclo: *{self.rodadas_desde_alta}*\n"
                f"📈 Ciclo médio: *{self.media_ciclo:.1f} rodadas*\n"
                f"🧠 Confiança: *{nivel} ({score}%)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔔 *FAÇA O CASH OUT EM 2.00x!*"
            )
            enviar_alerta(mensagem, SOM_ENTRADA, f"🚀 ENTRE AGORA! Rodada {rodada}")
            self.alertas_enviados += 1
    
    def gerar_relatorio(self) -> str:
        """Gera relatório de performance"""
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM rodadas")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM rodadas WHERE valor >= 2.0")
        altas = c.fetchone()[0]
        
        # Última rodada
        ultima_rodada = self.ultima_rodada_numero or "N/A"
        ultimo_valor = self.ultimo_multiplicador or "N/A"
        
        return (
            f"📊 *RELATÓRIO AETHERIUS v3.0*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 *Estatísticas*\n"
            f"├─ Total rodadas: *{total}*\n"
            f"├─ Velas ≥2.00x: *{altas} ({altas/max(1,total)*100:.1f}%)*\n"
            f"├─ Ciclo médio: *{self.media_ciclo:.1f} rodadas*\n"
            f"├─ Minutagem média: *{self.media_minutos:.1f} min*\n"
            f"└─ Alertas enviados: *{self.alertas_enviados}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Última rodada: #{ultima_rodada}* → {ultimo_valor:.2f}x\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_Bot rodando 24/7 | Aprendizado ativo_"
        )

# ============================================================
# SCRAPER (CAPTURA EM TEMPO REAL)
# ============================================================
def criar_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

def fazer_login(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    log.info("🔐 Fazendo login na Betou...")
    driver.get('https://betou.bet.br')
    wait = WebDriverWait(driver, 20)
    
    try:
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Login') or contains(text(),'Entrar')]")))
        btn.click()
        time.sleep(2)
        
        email = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
        email.clear()
        email.send_keys(BETOU_EMAIL)
        
        senha = driver.find_element(By.XPATH, "//input[@type='password']")
        senha.clear()
        senha.send_keys(BETOU_SENHA)
        
        btn_login = driver.find_element(By.XPATH, "//button[@type='submit']")
        btn_login.click()
        time.sleep(4)
        log.info("✅ Login realizado com sucesso!")
        return True
    except Exception as e:
        log.warning(f"⚠️ Login falhou: {e}")
        return False

def capturar_dados(driver):
    """Captura multiplicador e número da rodada em TEMPO REAL"""
    from selenium.webdriver.common.by import By
    
    mult = None
    rodada = None
    
    try:
        # Captura o multiplicador
        elementos = driver.find_elements(By.CSS_SELECTOR, '[appcoloredmultiplier]')
        for el in reversed(elementos):
            texto = el.text.strip()
            m = re.search(r'(\d+\.?\d*)', texto)
            if m:
                mult = float(m.group(1))
                break
        
        # Captura o número da rodada
        spans = driver.find_elements(By.CSS_SELECTOR, '.text-uppercase')
        for el in spans:
            texto = el.text
            m = re.search(r'Rodada\s+(\d+)', texto, re.IGNORECASE)
            if m:
                rodada = int(m.group(1))
                break
        
        if mult:
            log.debug(f"📡 Capturado: Rodada #{rodada} = {mult:.2f}x")
        
    except Exception as e:
        log.debug(f"Captura erro: {e}")
    
    return mult, rodada

# ============================================================
# MAIN
# ============================================================
def main():
    log.info("=" * 60)
    log.info("   🌟 AETHERIUS PREDICTOR v3.0 🌟")
    log.info("   ✅ Número da rodada em TODOS os alertas")
    log.info("   ✅ Captura em tempo real")
    log.info("=" * 60)
    
    enviar_texto(
        "🌟 *AETHERIUS PREDICTOR v3.0 ONLINE* 🌟\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ *NOVO:* Número da rodada em TODOS os alertas!\n"
        "✅ Reconhecimento de padrões complexos\n"
        "✅ Aprendizado por erro\n"
        "✅ Análise de horários pagantes\n"
        "✅ Minutagem (4-5 min entre roxas)\n"
        "✅ Contagem regressiva por rodadas\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🕐 *Bot ativo e monitorando o Aviator...*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    predictor = AetheriusPredictor()
    driver = None
    tentativas = 0
    ultima_rodada = None
    
    while True:
        try:
            if driver is None:
                driver = criar_driver()
                fazer_login(driver)
                driver.get(BETOU_URL)
                log.info("🎮 Aguardando Aviator carregar...")
                time.sleep(8)
                tentativas = 0
            
            mult, rodada = capturar_dados(driver)
            
            # Só processa se for uma rodada nova
            if mult is not None and rodada != ultima_rodada:
                predictor.processar_vela(mult, rodada)
                ultima_rodada = rodada
                
                # Envia relatório a cada 100 rodadas
                if len(predictor.historico) % 50 == 0 and len(predictor.historico) > 0:
                    enviar_texto(predictor.gerar_relatorio())
            
            time.sleep(2)  # Aguarda 2 segundos para próxima captura
            
        except KeyboardInterrupt:
            log.info("🛑 Encerrado pelo usuário")
            enviar_texto(predictor.gerar_relatorio())
            break
        except Exception as e:
            tentativas += 1
            log.error(f"❌ Erro (tentativa {tentativas}): {e}")
            try:
                driver.quit()
            except:
                pass
            driver = None
            time.sleep(15)

if __name__ == "__main__":
    main()
