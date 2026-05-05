FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY Aetherius_Predictor_ML.py .

COPY aetherius_brain_config.json .

VOLUME ["/app/data"]

CMD ["python", "-u", "Aetherius_Predictor_ML.py"]
