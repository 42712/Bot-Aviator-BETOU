FROM python:3.9-slim

WORKDIR /app

# Copia os arquivos
COPY requirements.txt .
COPY server.py .
COPY cookies.json .
COPY aetherius_brain_config.json .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta
EXPOSE 10000

# Comando para rodar
CMD ["python", "-u", "server.py"]
