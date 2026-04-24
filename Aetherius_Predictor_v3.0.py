#!/usr/bin/env python3
"""
AETHERIUS PREDICTOR v3.0 - Bot de Análise Inteligente para Aviator (Spribe)
- Captura em tempo real (multiplicador + número da rodada)
- Reconhecimento de padrões complexos
- Contagem regressiva por rodadas (3 → 1 → ENTRE AGORA)
- Minutagem (4-5 minutos entre velas roxas)
- Aprendizado por erro
- Análise de horários pagantes
- Padrão de espelhamento
- Análise de coluna do histórico

Desenvolvido para: Betou.bet.br
Autor: Marcos Duarte / Manus AI
Versão: 3.0 - Abril 2026
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
# CONFIGURAÇÕES (Preencha aqui ou use variáveis de ambiente)
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'SEU_TOKEN_AQUI')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'SEU_CHAT_ID_AQUI')
BETOU_EMAIL = os.environ.get('BETOU_EMAIL', 'marcosduarte356@gmail.com')
BETOU_SENHA = os.environ.get('BETOU_SENHA', 'amordedeus123@')
BETOU_URL = os.environ.get('BETOU_URL', 'https://betou.bet.br/games/spribe/aviator')

# Sons para Telegram (arquivos .mp3 online)
SOM_AVISO = 'https://www.soundjay.com/buttons/beep-01a.mp3'
SOM_URGENTE = 'https://www.soundjay.com/buttons/beep-07a.mp3'
SOM_ENTRADA = 'https://www.soundjay.com/buttons/beep-08b.mp3'
SOM_ROSA = 'https://www.soundjay.com/buttons/beep-09.mp3'

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('Aetherius')

# ============================================================
# TELEGRAM - Envio de Mensagens e Áudios
# ============================================================
def enviar_texto(mensagem: str):
    """Envia mensagem de texto para o Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensagem,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            log.warning(f"Telegram erro {response.status_code}: {response.text[:100]}")
    except Exception as e:
        log.warning(f"Telegram texto erro: {e}")

def enviar_audio(url_audio: str, legenda: str):
    """Envia áudio para o Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "audio": url_audio,
            "caption": legenda,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code != 200:
            log.warning(f"Áudio erro {response.status_code}")
    except Exception as e:
        log.warning(f"Telegram áudio erro: {e}")

def enviar_alerta(mensagem: str, som_url: str = None, legenda: str = ''):
    """Envia texto e opcionalmente áudio"""
    enviar_texto(mensagem)
    if som_url:
        enviar_audio(som_url, legenda)

# ============================================================
# PADRÕES COMPLEXOS - Reconhecimento de Sequências
# ============================================================
@dataclass
class PadraoComplexo:
    nome: str
    sequencia: List[float]
    risco: str
    previsao: str
    confianca: float

class ReconhecedorPadroes:
    """Reconhece padrões complexos como 1.00x → 1.03x → 1.05x → ROSA"""
    
    def __init__(self):
        self.padroes = [
            PadraoComplexo("Sequência da Morte", [1.00, 1.03, 1.05, 1.02], 'alto', 'ROSA', 0.85),
            PadraoComplexo("Três Baixas Seguidas", [1.05, 1.08, 1.12], 'medio', 'ROXA', 0.70),
            PadraoComplexo("Pressão Máxima", [1.20, 1.15, 1.10, 1.05], 'alto', 'ROSA', 0.82),
            PadraoComplexo("Escada para Rosa", [1.00, 1.00, 2.00, 1.00], 'alto', 'ROSA', 0.80),
            PadraoComplexo("Recuperação", [1.50, 1.45, 1.48], 'baixo', 'AZUL', 0.60),
            PadraoComplexo("Espelho Rosa", [10.0, 1.0, 1.0, 1.0], 'alto', 'ROXA', 0.75),
        ]
        self.padroes_aprendidos = []
        self.historico_padroes = deque(maxlen=500)
    
    def reconhecer(self, historico: List[float]) -> Optional[PadraoComplexo]:
        """Verifica se o final do histórico corresponde a algum padrão conhecido"""
        if len(historico) < 3:
            return None
        
        ultimos = list(historico)[-5:]
        
        for padrao in self.padroes:
            if self._corresponde(ultimos, padrao.sequencia):
                return padrao
        
        # Verifica padrões aprendidos
        for padrao in self.padroes_aprendidos:
            if self._corresponde(ultimos, padrao['sequencia']):
                return PadraoComplexo(
                    nome=padrao['nome'],
                    sequencia=padrao['sequencia'],
                    risco=padrao['risco'],
                    previsao=padrao['previsao'],
                    confianca=padrao['confianca']
                )
        
        return None
    
    def _corresponde(self, atual: List[float], padrao: List[float]) -> bool:
        """Verifica se os valores atuais correspondem ao padrão (com tolerância)"""
        if len(atual) < len(padrao):
            return False
        
        for i in range(1, min(len(padrao), len(atual)) + 1):
            if abs(atual[-i] - padrao[-i]) > 0.05:  # tolerância 0.05
                return False
        return True
    
    def aprender_padrao(self, sequencia: List[float], resultado: float, acertou: bool):
        """Aprende novos padrões com base em acertos/erros"""
        if len(sequencia) < 3:
            return
        
        # Verifica se já conhece este padrão
        for p in self.padroes_aprendidos:
            if self._corresponde(sequencia, p['sequencia']):
                if acertou:
                    p['confianca'] = min(0.95, p['confianca'] + 0.05)
                else:
                    p['confianca'] = max(0.30, p['confianca'] - 0.10)
                return
        
        # Novo padrão detectado
        novo_padrao = {
            'nome': f"Padrão Aprendido {len(self.padroes_aprendidos)+1}",
            'sequencia': sequencia.copy(),
            'risco': 'medio',
            'previsao': 'ROXA' if resultado >= 2.0 else 'AZUL',
            'confianca': 0.50 if acertou else 0.30,
            'acertos': 1 if acertou else 0,
            'erros': 0 if acertou else 1
        }
        self.padroes_aprendidos.append(novo_padrao)
        
        # Mantém apenas os 20 padrões mais confiáveis
        self.padroes_aprendidos.sort(key=lambda x: x['confianca'], reverse=True)
        self.padroes_aprendidos = self.padroes_aprendidos[:20]

# ============================================================
# ANÁLISE DE COLUNA - Histórico em Grade
# ============================================================
class AnalisadorColuna:
    """Analisa posições das velas no histórico em grade"""
    
    def __init__(self, colunas: int = 6):
        self.colunas = colunas
        self.grade = []  # Grade de multiplicadores
        self.colunas_pagantes = defaultdict(int)
    
    def adicionar_vela(self, valor: float):
        """Adiciona uma vela à grade"""
        self.grade.append(valor)
        if len(self.grade) > 60:  # 10 linhas x 6 colunas
            self.grade.pop(0)
    
    def obter_coluna(self, indice: int) -> int:
        return indice % self.colunas
    
    def analisar_padrao_coluna(self, ultimo_indice: int, valor: float) -> Optional[Dict]:
        """Analisa se há padrão na coluna atual"""
        coluna = self.obter_coluna(ultimo_indice)
        
        valores_coluna = []
        for i in range(len(self.grade) - 1, -1, -1):
            if self.obter_coluna(i) == coluna:
                valores_coluna.append(self.grade[i])
                if len(valores_coluna) >= 3:
                    break
        
        if valores_coluna:
            altas_coluna = sum(1 for v in valores_coluna if v >= 2.0) / len(valores_coluna)
            
            if altas_coluna >= 0.5:
                return {
                    'coluna': coluna + 1,
                    'confianca': altas_coluna,
                    'previsao': 'ROXA',
                    'mensagem': f"📊 Coluna {coluna+1} está quente! {altas_coluna*100:.0f}% das últimas velas ≥2x"
                }
        
        return None

# ============================================================
# ANÁLISE DE HORÁRIOS PAGANTES
# ============================================================
class AnalisadorHorarios:
    """Identifica quais horários têm maior probabilidade de pagamento"""
    
    def __init__(self):
        # Dados baseados na sua tabela de 23/04/2026
        self.horarios_quentes = {
            0: 85, 1: 82, 2: 80, 3: 78, 4: 75,
            5: 55, 6: 50, 7: 45, 8: 40, 9: 40,
            10: 40, 11: 40, 12: 40, 13: 40, 14: 40,
            15: 40, 16: 40, 17: 40, 18: 40, 19: 40,
            20: 40, 21: 40, 22: 40, 23: 40
        }
        self.historico_horarios = defaultdict(list)
    
    def registrar_vela(self, valor: float, hora: int):
        """Registra nova vela para aprendizado contínuo"""
        self.historico_horarios[hora].append(valor)
        
        if len(self.historico_horarios[hora]) >= 10:
            altas = sum(1 for v in self.historico_horarios[hora][-100:] if v >= 2.0)
            self.horarios_quentes[hora] = int((altas / len(self.historico_horarios[hora][-100:])) * 100)
    
    def avaliar_horario(self, hora: int) -> Tuple[int, str]:
        """Retorna score e classificação do horário atual"""
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
# APRENDIZADO POR ERRO (Reforço negativo)
# ============================================================
class AprendizadoPorErro:
    """Sistema que aprende com os erros e evita repeti-los"""
    
    def __init__(self):
        self.erros_recentes = deque(maxlen=100)
        self.penalti_padroes = defaultdict(float)
    
    def registrar_erro(self, sequencia: List[float], contexto: Dict, esperado: float, real: float):
        """Registra um erro para aprendizado futuro"""
        seq_tuple = tuple(round(v, 2) for v in sequencia[-5:])
        self.penalti_padroes[seq_tuple] = min(0.50, self.penalti_padroes.get(seq_tuple, 1.0) - 0.10)
        
        self.erros_recentes.append({
            'sequencia': sequencia,
            'contexto': contexto,
            'esperado': esperado,
            'real': real,
            'hora': datetime.now()
        })
        
        log.info(f"[APRENDIZADO] Erro registrado: esperava ≥{esperado}, veio {real:.2f}x | Penalidade: {self.penalti_padroes[seq_tuple]:.2f}")
    
    def verificar_padrao_erro(self, sequencia: List[float]) -> Tuple[bool, float]:
        """Verifica se a sequência atual já causou erros no passado"""
        seq_tuple = tuple(round(v, 2) for v in sequencia[-5:])
        
        if seq_tuple in self.penalti_padroes:
            return True, self.penalti_padroes[seq_tuple]
        return False, 1.0
    
    def registrar_acerto(self, sequencia: List[float]):
        """Registra acerto para reforço positivo"""
        seq_tuple = tuple(round(v, 2) for v in sequencia[-5:])
        self.penalti_padroes[seq_tuple] = min(1.0, self.penalti_padroes.get(seq_tuple, 1.0) + 0.05)

# ============================================================
# MOTOR PRINCIPAL DO BOT
# ============================================================
class AetheriusPredictor:
    def __init__(self):
        # Histórico
        self.historico = deque(maxlen=300)
        self.historico_tempo = deque(maxlen=300)
        
        # Aprendizado de ciclo
        self.intervalos_ciclo = deque(maxlen=60)
        self.media_ciclo = 8.0
        self.rodadas_desde_alta = 0
        self.ultima_rodada_id = None
        self.ultimo_multiplicador = None
        self.ultima_rodada_numero = None
        
        # Minutagem
        self.ultimo_timestamp_alta = None
        self.media_minutos = 4.5
        
        # Alertas
        self.alertas = {'3': False, '1': False, 'agora': False}
        self.contagem_1x = 0
        self.sequencia_atual = []
        
        # Módulos de inteligência
        self.reconhecedor = ReconhecedorPadroes()
        self.analisador_coluna = AnalisadorColuna()
        self.aprendizado_erro = AprendizadoPorErro()
        self.analisador_horario = AnalisadorHorarios()
        
        # Banco de dados
        self.conn = sqlite3.connect('/app/data/aetherius_brain.db' if os.path.exists('/app') else 'aetherius_brain.db')
        self._init_db()
        self._carregar_historico()
        
        # Estatísticas
        self.alertas_enviados = 0
        self.acertos = 0
        self.erros = 0
        self.ultima_aposta_alertada = None
    
    def _init_db(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS rodadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER,
            valor REAL,
            hora TEXT,
            timestamp REAL,
            foi_alerta INTEGER DEFAULT 0,
            acertou INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            alertas INTEGER,
            acertos INTEGER,
            erros INTEGER,
            taxa REAL
        )''')
        self.conn.commit()
        log.info("✅ Banco de dados inicializado")
    
    def _carregar_historico(self):
        c = self.conn.cursor()
        c.execute("SELECT valor FROM rodadas ORDER BY id DESC LIMIT 300")
        rows = c.fetchall()
        for (v,) in reversed(rows):
            self.historico.append(v)
        log.info(f"📀 Banco carregado: {len(self.historico)} rodadas")
    
    def _calcular_confianca(self) -> Tuple[int, str]:
        """Calcula confiança baseada em múltiplos fatores"""
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
            elif desvio > 5.0:
                score -= 10
        
        # Fator de rodadas desde a última alta
        if self.rodadas_desde_alta > 0:
            fator_ciclo = min(self.rodadas_desde_alta / max(self.media_ciclo, 1), 2.0)
            score += int(fator_ciclo * 15)
        
        # Fator horário
        hora_atual = datetime.now().hour
        score_horario, _ = self.analisador_horario.avaliar_horario(hora_atual)
        score = int(score * 0.6 + score_horario * 0.4)
        
        # Penalidade por padrão de erro
        sequencia_atual = list(self.historico)[-5:] if len(self.historico) >= 5 else []
        tem_historico_erro, multiplicador = self.aprendizado_erro.verificar_padrao_erro(sequencia_atual)
        if tem_historico_erro:
            score = int(score * multiplicador)
        
        score = max(20, min(95, int(score)))
        nivel = "Alta" if score >= 75 else ("Média" if score >= 55 else "Baixa")
        return score, nivel
    
    def _analisar_espelhamento(self) -> Optional[Dict]:
        """Verifica se a sequência atual espelha alguma sequência conhecida"""
        if len(self.sequencia_atual) < 3:
            return None
        
        # Pega as últimas 3 rodadas
        ultimas = self.sequencia_atual[-3:]
        
        # Verifica se é uma sequência de baixas consecutivas
        if all(v < 1.5 for v in ultimas):
            return {
                'tipo': 'espelhamento',
                'proximo_esperado': 'ALTA',
                'confianca': 0.70,
                'mensagem': "🔄 Três baixas consecutivas! Alta probabilidade de reversão."
            }
        
        # Verifica padrão 1.00x + baixas
        if len(self.sequencia_atual) >= 4 and self.sequencia_atual[-4] == 1.00:
            if all(v < 1.5 for v in ultimas):
                return {
                    'tipo': 'espelhamento',
                    'proximo_esperado': 'ALTA FORTE',
                    'confianca': 0.85,
                    'mensagem': "🎯 Padrão 1.00x + 3 baixas! ROSA iminente!"
                }
        
        return None
    
    def _analisar_minutagem(self) -> Optional[Dict]:
        """Analisa baseado em minutos (4-5 min entre velas roxas)"""
        if self.ultimo_timestamp_alta is None:
            return None
        
        agora = datetime.now()
        diff_minutos = (agora - self.ultimo_timestamp_alta).total_seconds() / 60
        
        # Ajusta média com aprendizado
        if len(self.intervalos_ciclo) >= 5:
            # Converte rodadas para minutos (estimativa de 25s por rodada)
            media_minutos_estimada = self.media_ciclo * 0.42  # ~25 segundos por rodada
            self.media_minutos = (self.media_minutos * 0.7) + (media_minutos_estimada * 0.3)
        
        if diff_minutos >= self.media_minutos * 0.85 and not self.alertas.get('minutagem', False):
            self.alertas['minutagem'] = True
            return {
                'tipo': 'minutagem',
                'diff_minutos': diff_minutos,
                'media': self.media_minutos,
                'pronto': diff_minutos >= self.media_minutos
            }
        
        # Reseta alerta de minutagem se já passou muito tempo
        if diff_minutos > self.media_minutos * 1.5:
            self.alertas['minutagem'] = False
        
        return None
    
    def processar_vela(self, valor: float, numero_rodada: int = None):
        """Processa uma nova vela - COM NÚMERO DA RODADA EM TODOS OS ALERTAS"""
        
        # Evita duplicatas
        if numero_rodada and numero_rodada == self.ultima_rodada_id:
            return
        
        self.ultima_rodada_id = numero_rodada
        self.ultimo_multiplicador = valor
        self.ultima_rodada_numero = numero_rodada
        
        agora = datetime.now()
        self.historico.append(valor)
        self.historico_tempo.append(agora)
        self.sequencia_atual.append(valor)
        if len(self.sequencia_atual) > 10:
            self.sequencia_atual.pop(0)
        
        # Análise de coluna
        self.analisador_coluna.adicionar_vela(valor)
        
        # Registra horário (para aprendizado)
        self.analisador_horario.registrar_vela(valor, agora.hour)
        
        # Salva no banco
        c = self.conn.cursor()
        c.execute("INSERT INTO rodadas (numero, valor, hora, timestamp) VALUES (?, ?, ?, ?)",
                  (numero_rodada, valor, agora.isoformat(), agora.timestamp()))
        self.conn.commit()
        
        log.info(f"📊 RODADA #{numero_rodada}: {valor:.2f}x | Desde última alta: {self.rodadas_desde_alta}")
        
        # Atualiza ciclo e reseta alertas quando vem vela alta
        if valor >= 2.0:
            if self.ultimo_timestamp_alta:
                intervalo = (agora - self.ultimo_timestamp_alta).total_seconds() / 60
                if 1 < intervalo < 15:
                    self.media_minutos = (self.media_minutos * 0.7) + (intervalo * 0.3)
            
            self.intervalos_ciclo.append(self.rodadas_desde_alta)
            if len(self.intervalos_ciclo) >= 3:
                pesos = list(range(1, len(self.intervalos_ciclo) + 1))
                self.media_ciclo = sum(v * p for v, p in zip(self.intervalos_ciclo, pesos)) / sum(pesos)
                log.info(f"[APRENDIZADO] Novo ciclo médio: {self.media_ciclo:.2f} rodadas | Minutagem média: {self.media_minutos:.1f} min")
            
            # Registra acerto se houve alerta recente
            if self.ultima_aposta_alertada and (agora - self.ultima_aposta_alertada).total_seconds() < 120:
                self.acertos += 1
                self.aprendizado_erro.registrar_acerto(list(self.historico)[-8:-1] if len(self.historico) >= 8 else [])
                log.info(f"✅ ACERTO! Alerta seguido de vela ≥2.00x")
            
            self.rodadas_desde_alta = 0
            self.ultimo_timestamp_alta = agora
            self.ultima_aposta_alertada = None
            self.alertas = {'3': False, '1': False, 'agora': False}
            
            # Se for ROSA (≥100x)
            if valor >= 100:
                self._enviar_alerta_rosa(valor, numero_rodada)
        
        self.rodadas_desde_alta += 1
        
        # ===== 1. RECONHECIMENTO DE PADRÕES COMPLEXOS =====
        padrao = self.reconhecedor.reconhecer(list(self.historico))
        if padrao and padrao.confianca >= 0.70:
            self._enviar_alerta_padrao(padrao, numero_rodada)
        
        # ===== 2. ANÁLISE DE COLUNA =====
        coluna_atual = len(self.analisador_coluna.grade) - 1
        analise_coluna = self.analisador_coluna.analisar_padrao_coluna(coluna_atual, valor)
        if analise_coluna and analise_coluna['confianca'] >= 0.6:
            enviar_texto(f"{analise_coluna['mensagem']}\n🆔 Rodada atual: #{numero_rodada}")
        
        # ===== 3. MINUTAGEM =====
        analise_minuto = self._analisar_minutagem()
        if analise_minuto and analise_minuto.get('pronto', False):
            score, nivel = self._calcular_confianca()
            mensagem = (
                f"⏰ *MINUTAGEM: JANELA DE ENTRADA*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *Rodada atual: #{numero_rodada}*\n"
                f"⏱️ Última roxa há {analise_minuto['diff_minutos']:.1f} minutos\n"
                f"📊 Média: {analise_minuto['media']:.1f} min\n"
                f"🕐 Horário: {agora.strftime('%H:%M:%S')}\n"
                f"🧠 Confiança: *{nivel} ({score}%)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Alvo: 2.00x | Proteção: 1.50x\n"
                f"🚀 *ENTRE AGORA!*"
            )
            enviar_alerta(mensagem, SOM_ENTRADA, f"⏰ ENTRADA POR MINUTAGEM! Rodada {numero_rodada}")
            self.alertas_enviados += 1
            self.ultima_aposta_alertada = agora
        
        # ===== 4. PADRÃO DE ESPELHAMENTO =====
        espelhamento = self._analisar_espelhamento()
        if espelhamento and espelhamento['confianca'] >= 0.65:
            score, nivel = self._calcular_confianca()
            mensagem = (
                f"{espelhamento['mensagem']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Rodada atual: #{numero_rodada}\n"
                f"🔮 Previsão: {espelhamento['proximo_esperado']}\n"
                f"💎 Confiança: {espelhamento['confianca']*100:.0f}%\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ Prepare-se! Janela se aproximando."
            )
            enviar_alerta(mensagem, SOM_AVISO)
        
        # ===== 5. VELA 1.00x (Contar 6 velas) =====
        if abs(valor - 1.00) < 0.02:
            self._enviar_alerta_1x(numero_rodada)
            self.contagem_1x = 1  # Começa contar da próxima
        elif hasattr(self, 'contagem_1x') and self.contagem_1x > 0:
            self.contagem_1x += 1
            if self.contagem_1x == 7:  # 7ª vela após o 1.00x
                self._enviar_alerta_sete_velas(numero_rodada)
                self.contagem_1x = 0
        
        # ===== 6. CONTAGEM REGRESSIVA POR RODADAS =====
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
            f"💎 *Parabéns! Rosa capturada!*\n"
            f"🎯 Alvo atingido com sucesso!"
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
        enviar_alerta(mensagem, SOM_AVISO, f"🎯 Padrão {padrao.nome} na rodada {rodada}")
    
    def _enviar_alerta_1x(self, rodada: int):
        """Alerta de vela 1.00x"""
        mensagem = (
            f"🔴 *GATILHO 1.00x DETECTADO!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Rodada: #{rodada}*\n"
            f"🕐 Horário: {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Contar até a 7ª rodada → Entrar na 7ª\n"
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
        enviar_alerta(mensagem, SOM_ENTRADA, f"🚀 ENTRADA NA 7
