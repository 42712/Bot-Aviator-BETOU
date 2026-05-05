FROM python:3.9-slim

WORKDIR /app

# Copiar todos os arquivos da raiz
COPY requirements.txt .
COPY Aetherius_Predictor_ML.py .
COPY aetherius_brain_config.json .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando para rodar o bot
CMD ["python", "-u", "Aetherius_Predictor_ML.py"]
