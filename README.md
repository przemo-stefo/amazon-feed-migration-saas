# Amazon Feed Migration SaaS

Aplikacja SaaS do migracji legacy feedów Amazon (XML/Flat File, XLSB/SFTP) do nowego standardu Amazon SP-API (Listings Item API i JSON_LISTINGS_FEED).

## 🚀 Funkcjonalności

- **Multi-tenant SaaS**: Obsługa wielu użytkowników z izolacją danych
- **Import Excel/XLSB**: Automatyczne parsowanie plików z feedami
- **Mapowanie danych**: Inteligentne mapowanie legacy formatów do Amazon SP-API JSON
- **Amazon SP-API**: Pełna integracja z najnowszym API Amazon
- **Async processing**: Przetwarzanie w tle z Celery i Redis
- **Real-time status**: Monitoring statusu feedów w czasie rzeczywistym
- **Error handling**: Szczegółowe logowanie i obsługa błędów

## 🏗️ Architektura

```
Frontend (React)
    ↓
API Gateway (FastAPI)
    ↓
Business Logic Layer
    ↓
┌─────────────┬─────────────┬─────────────┐
│   Queue     │  Database   │  External   │
│  (Celery)   │(PostgreSQL) │   APIs      │
│             │             │(Amazon SP)  │
└─────────────┴─────────────┴─────────────┘
```

## 📋 Wymagania

### Środowisko deweloperskie
- Python 3.9+
- Node.js 18+
- PostgreSQL 13+
- Redis 6+

### Produkcja
- Docker & Docker Compose
- PostgreSQL (AWS RDS zalecane)
- Redis (AWS ElastiCache zalecane)
- AWS S3 (dla przechowywania plików)

## 🛠️ Instalacja i uruchomienie

### 1. Klonowanie repozytorium

```bash
git clone <repository-url>
cd amazon-feed-migration-saas
```

### 2. Backend Setup

```bash
cd backend

# Tworzenie środowiska wirtualnego
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub venv\Scripts\activate  # Windows

# Instalacja zależności
pip install -r requirements.txt

# Konfiguracja zmiennych środowiskowych
cp .env.example .env
# Edytuj .env z właściwymi wartościami
```

#### Konfiguracja .env

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/amazon_feeds

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30 dni

# Amazon SP-API (dla testów)
AMAZON_SANDBOX_URL=https://sandbox.sellingpartnerapi-na.amazon.com
AMAZON_PRODUCTION_URL=https://sellingpartnerapi-na.amazon.com

# Logging
LOG_LEVEL=INFO

# Uploads
UPLOAD_DIR=uploads
MAX_FILE_SIZE=52428800  # 50MB
```

#### Uruchomienie bazy danych

```bash
# PostgreSQL z Docker
docker run --name postgres-amazon-feeds \
  -e POSTGRES_DB=amazon_feeds \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:13

# Redis z Docker
docker run --name redis-amazon-feeds \
  -p 6379:6379 \
  -d redis:6
```

#### Migracja bazy danych

```bash
# Inicjalizacja Alembic (tylko pierwszy raz)
alembic init alembic

# Tworzenie migracji
alembic revision --autogenerate -m "Initial migration"

# Aplikowanie migracji
alembic upgrade head
```

#### Uruchomienie serwera

```bash
# Development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Uruchomienie Celery Worker

```bash
# W osobnym terminalu
celery -A tasks.feed_processing worker --loglevel=info

# Uruchomienie Celery Beat (scheduler)
celery -A tasks.feed_processing beat --loglevel=info
```

### 3. Frontend Setup

```bash
cd frontend

# Instalacja zależności
npm install

# Uruchomienie dev server
npm start
```

## 🐳 Docker Deployment

### Docker Compose dla developmentu

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: amazon_feeds
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/amazon_feeds
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
      - uploads_data:/app/uploads
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  celery:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/amazon_feeds
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
      - uploads_data:/app/uploads
    depends_on:
      - postgres
      - redis
    command: celery -A tasks.feed_processing worker --loglevel=info

  celery-beat:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/amazon_feeds
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis
    command: celery -A tasks.feed_processing beat --loglevel=info

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      REACT_APP_API_URL: http://localhost:8000

volumes:
  postgres_data:
  uploads_data:
```

### Uruchomienie z Docker

```bash
# Build i uruchomienie
docker-compose -f docker-compose.dev.yml up --build

# W tle
docker-compose -f docker-compose.dev.yml up -d
```

## 🏭 Deployment produkcyjny

### 1. Przygotowanie środowiska

```bash
# Tworzenie użytkownika aplikacji
sudo useradd -m -s /bin/bash amazon-feeds
sudo usermod -aG docker amazon-feeds

# Przygotowanie katalogów
sudo mkdir -p /opt/amazon-feeds
sudo chown amazon-feeds:amazon-feeds /opt/amazon-feeds
```

### 2. Nginx Configuration

```nginx
# /etc/nginx/sites-available/amazon-feeds
server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;

    # Frontend
    location / {
        try_files $uri $uri/ /index.html;
        root /opt/amazon-feeds/frontend/build;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support dla real-time updates (opcjonalne)
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3. Systemd Services

```ini
# /etc/systemd/system/amazon-feeds-api.service
[Unit]
Description=Amazon Feeds API
After=network.target

[Service]
Type=simple
User=amazon-feeds
WorkingDirectory=/opt/amazon-feeds/backend
Environment=PATH=/opt/amazon-feeds/backend/venv/bin
ExecStart=/opt/amazon-feeds/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/amazon-feeds-celery.service
[Unit]
Description=Amazon Feeds Celery Worker
After=network.target

[Service]
Type=simple
User=amazon-feeds
WorkingDirectory=/opt/amazon-feeds/backend
Environment=PATH=/opt/amazon-feeds/backend/venv/bin
ExecStart=/opt/amazon-feeds/backend/venv/bin/celery -A tasks.feed_processing worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4. Backup Strategy

```bash
#!/bin/bash
# /opt/amazon-feeds/scripts/backup.sh

BACKUP_DIR="/opt/amazon-feeds/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump amazon_feeds > "$BACKUP_DIR/db_backup_$DATE.sql"

# Files backup
tar -czf "$BACKUP_DIR/files_backup_$DATE.tar.gz" /opt/amazon-feeds/uploads

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -type f -mtime +30 -delete

# Upload to S3 (opcjonalne)
aws s3 cp "$BACKUP_DIR/db_backup_$DATE.sql" s3://your-backup-bucket/
aws s3 cp "$BACKUP_DIR/files_backup_$DATE.tar.gz" s3://your-backup-bucket/
```

## 📊 Monitoring i Logging

### Loguru Configuration

```python
# utils/logger.py
from loguru import logger
import sys

def setup_logger():
    logger.remove()

    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # File logging
    logger.add(
        "logs/app.log",
        rotation="100 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )

    return logger
```

### Prometheus Metrics (opcjonalne)

```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
feeds_processed = Counter('feeds_processed_total', 'Total feeds processed', ['status', 'feed_type'])
processing_time = Histogram('feed_processing_seconds', 'Time spent processing feeds')
active_users = Gauge('active_users', 'Number of active users')

# Usage example
feeds_processed.labels(status='completed', feed_type='inventory').inc()
```

## 🔧 Maintenance

### Regularne zadania

```bash
# Cron jobs (/etc/cron.d/amazon-feeds)

# Daily backup at 2 AM
0 2 * * * amazon-feeds /opt/amazon-feeds/scripts/backup.sh

# Weekly log cleanup
0 1 * * 0 amazon-feeds find /opt/amazon-feeds/logs -name "*.log" -mtime +7 -delete

# Monthly database optimization
0 3 1 * * amazon-feeds /opt/amazon-feeds/scripts/optimize_db.sh
```

### Database Maintenance

```sql
-- Cleanup old feeds (older than 90 days)
DELETE FROM feed_logs WHERE created_at < NOW() - INTERVAL '90 days';
DELETE FROM feed_items WHERE feed_id IN (
    SELECT id FROM feeds WHERE created_at < NOW() - INTERVAL '90 days'
);
DELETE FROM feeds WHERE created_at < NOW() - INTERVAL '90 days';

-- Update statistics
ANALYZE;
VACUUM;
```

## 🚨 Troubleshooting

### Częste problemy

1. **Celery worker nie przetwarza zadań**
   ```bash
   # Sprawdź status Redis
   redis-cli ping

   # Restart Celery
   sudo systemctl restart amazon-feeds-celery
   ```

2. **Błędy Amazon SP-API**
   ```bash
   # Sprawdź logi
   tail -f logs/app.log | grep "amazon"

   # Sprawdź credentials w bazie danych
   ```

3. **Problemy z uploadem plików**
   ```bash
   # Sprawdź uprawnienia
   ls -la uploads/

   # Sprawdź miejsce na dysku
   df -h
   ```

## 📈 Skalowanie

### Horizontal Scaling

1. **Load Balancer**: Nginx + multiple backend instances
2. **Database**: PostgreSQL read replicas
3. **Redis Cluster**: Dla wysokiej dostępności
4. **File Storage**: AWS S3 + CloudFront

### Vertical Scaling

1. **CPU**: Więcej worker processes Celery
2. **Memory**: Większe instancje dla dużych plików
3. **Storage**: SSD dla lepszej wydajności I/O

## 🔒 Security

### Checklist bezpieczeństwa

- [ ] HTTPS enabled (SSL/TLS)
- [ ] Strong JWT secret keys
- [ ] Database credentials encrypted
- [ ] Amazon API credentials secured
- [ ] File upload validation
- [ ] Rate limiting enabled
- [ ] Regular security updates
- [ ] Backup encryption
- [ ] Access logs monitoring

## 📝 API Documentation

API documentation jest dostępna pod `/docs` (Swagger UI) i `/redoc` (ReDoc) po uruchomieniu serwera.

## 🤝 Wsparcie

W przypadku problemów:
1. Sprawdź logi aplikacji
2. Przeczytaj dokumentację Amazon SP-API
3. Otwórz issue w repozytorium

## 📄 Licencja

[Licencja do określenia]