# AETHERIUS PREDICTOR ML v4.0 (Aprimorado)

### Bot de análise preditiva para Aviator (Spribe) com Modo Sniper

[![Versao](https://img.shields.io/badge/versao-4.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4)]()

## O QUE FAZ

Bot que monitora o jogo Aviator e envia alertas via Telegram com análise preditiva baseada em Machine Learning real (Markov Chains + Bayes + entropia) e **agora com o novo Modo Sniper para Velas Altas**.

## Novidade: Modo Sniper (Gatilho de Velas Altas)

A versão 4.0 aprimorada inclui uma lógica de detecção de padrões baseada em tempo e multiplicadores extremos.
- **Gatilho:** Quando uma vela atinge 50x ou mais, o bot entra em "Modo Sniper".
- **Janelas de Oportunidade:** O bot monitora ativamente as janelas de 3, 5 e 10 minutos após o gatilho.
- **Entrada Cirúrgica:** O alerta de entrada é enviado entre 1 e 30 segundos antes do fechamento da janela de tempo, maximizando a assertividade (esperada entre 75% e 85%).

## Funcionalidades

| Funcionalidade | Status | Descricao |
|----------------|--------|-----------|
| Markov Chains ordem 1/2/3 | OK | Probabilidade de transicao entre estados com backoff |
| Inferencia Bayesiana | OK | Ensemble ponderado: Markov (35%), ritmo (25%), historico (25%), media (15%) |
| Ritmo adaptativo | OK | Media + desvio padrao dos intervalos entre roxas, modelo Normal |
| Busca de padroes historicos | OK | SQLite com similaridade de sequencias reais |
| Entropia de Shannon | OK | Mede o caos das ultimas 30 rodadas para calibrar confianca |
| Auto-calibracao de vies | OK | Corrige overconfidence baseado em acertos/erros reais |
| Alertas Telegram 5/2/1min | OK | Contagem regressiva com score de confianca |
| **Modo Sniper (Novo)** | **OK** | **Gatilho >50x com janelas de entrada em 3, 5 e 10 min** |

## Instalacao Local

```bash
git clone https://github.com/seu-usuario/aetherius-bot.git
cd aetherius-bot
pip install -r requirements.txt
python Aetherius_Predictor_ML.py
```

## Configuração

Edite o arquivo `Aetherius_Predictor_ML.py` e insira suas credenciais do Telegram:
```python
TELEGRAM_BOT_TOKEN = 'SEU TOKEN AQUI'
TELEGRAM_CHAT_ID = 'SEU ID AQUI'
```
Os parâmetros de inteligência podem ser ajustados no arquivo `aetherius_brain_config.json`.
