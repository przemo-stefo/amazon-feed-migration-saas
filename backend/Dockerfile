FROM python:3.11-slim

WORKDIR /app

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie plików requirements
COPY requirements.txt .

# Instalacja zależności Python
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu aplikacji
COPY . .

# Tworzenie katalogów
RUN mkdir -p uploads logs

# Ustawienie uprawnień
RUN chmod +x celery_worker.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Domyślna komenda
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]