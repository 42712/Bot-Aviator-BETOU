FROM python:3.11-slim

# Instala dependências do sistema e Chromium
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl \
    libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 \
    libdbus-1-3 libx11-6 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 \
    libxss1 libxtst6 fonts-liberation libasound2 \
    libatk-bridge2.0-0 libgtk-3-0 \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Aetherius_Predictor_v3.0.py .

# Volume para persistência do banco de dados
VOLUME ["/app/data"]

# Comando para executar o bot
CMD ["python", "-u", "Aetherius_Predictor_v3.0.py"]
