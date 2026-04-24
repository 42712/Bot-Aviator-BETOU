aetherius-predictor/
├── Aetherius_Predictor_v3.0.py   # Código principal do bot
├── requirements.txt                # Dependências Python
├── Dockerfile                      # Configuração do container
├── README.md                       # Este arquivo
└── data/                           # Volume para banco de dados (criado automaticamente)
    └── aetherius_brain.db          # Banco de dados SQLite (persistente)


# 🚀 Aetherius Predictor v3.0

## 🆔 NOVIDADE: NÚMERO DA RODADA EM TODOS OS ALERTAS!

Cada sinal enviado no Telegram informará EXATAMENTE a rodada atual.

### Exemplo de alerta:

# 🚀 Aetherius Predictor v3.0 - Inteligência Completa

## 🧠 O que este bot faz?

| Módulo | Função |
|--------|--------|
| **Reconhecimento de Padrões** | Detecta sequências como 1.00x→1.05x→1.03x que precedem ROSA |
| **Aprendizado por Erro** | Se o bot errou, ele guarda o padrão e não repete |
| **Análise de Horário** | Sabe que 00h-04h pagam mais (seus dados) |
| **Minutagem** | Conta 4-5 minutos entre velas roxas |
| **Padrão de Espelhamento** | Reconhece sequências que se repetem |
| **Análise de Coluna** | Verifica quais colunas do histórico estão quentes |
| **Contagem por Rodadas** | Alerta: 3 rodadas → 1 rodada → ENTRE AGORA |

## ☁️ Deploy na Oracle Cloud

```bash
# 1. Instalar Docker
sudo apt update && sudo apt install docker.io -y

# 2. Clonar
git clone https://github.com/SEU_USUARIO/aetherius-v3.git
cd aetherius-v3

# 3. Construir
sudo docker build -t aetherius-v3 .

# 4. Rodar
sudo docker run -d \
  --name aetherius-v3 \
  --restart unless-stopped \
  -e TELEGRAM_TOKEN=SEU_TOKEN \
  -e TELEGRAM_CHAT_ID=SEU_CHAT_ID \
  -e BETOU_EMAIL=marcosduarte356@gmail.com \
  -e BETOU_SENHA=amordedeus123@ \
  -v ~/aetherius-data:/app/data \
  aetherius-v3
