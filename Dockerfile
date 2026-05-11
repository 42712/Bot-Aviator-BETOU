FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY aetherius_brain_config.json .
COPY cookies.json .

EXPOSE 10000

CMD ["python", "-u", "server.py"]
