FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=7860
ENV HOST=0.0.0.0

# Wir verlinken den Ordner auf sich selbst, damit team04.Frontend gefunden wird
RUN ln -s . team04

EXPOSE 7860

CMD ["python", "main.py"]
