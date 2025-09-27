# Przewodnik wdrożenia Amazon Feed Migration SaaS

## 🚀 Szybki start z Docker

### Wymagania minimalne
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM
- 10GB wolnego miejsca na dysku

### 1. Sklonowanie i uruchomienie

```bash
# Klonowanie repozytorium
git clone <repository-url>
cd amazon-feed-migration-saas

# Uruchomienie całego stack'a
docker-compose up -d

# Sprawdzenie statusu
docker-compose ps
```

### 2. Inicjalizacja bazy danych

```bash
# Wejście do kontenera backend
docker-compose exec backend bash

# Uruchomienie migracji
alembic upgrade head

# Utworzenie pierwszego użytkownika (opcjonalne)
python scripts/create_admin_user.py
```

### 3. Sprawdzenie działania

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🏭 Wdrożenie produkcyjne

### AWS Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Route53   │    │     ALB     │    │     ECS     │
│    (DNS)    │───▶│ Load Balancer│───▶│  Fargate    │
└─────────────┘    └─────────────┘    └─────────────┘
                                             │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│     S3      │    │     RDS     │    │ ElastiCache │
│   (Files)   │    │ PostgreSQL  │    │   Redis     │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 1. Przygotowanie infrastruktury AWS

#### RDS PostgreSQL

```bash
# Tworzenie RDS instance
aws rds create-db-instance \
    --db-instance-identifier amazon-feeds-db \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --engine-version 13.7 \
    --master-username postgres \
    --master-user-password "SecurePassword123!" \
    --allocated-storage 100 \
    --storage-type gp2 \
    --vpc-security-group-ids sg-xxxxxxxxx \
    --db-subnet-group-name default \
    --backup-retention-period 7 \
    --storage-encrypted
```

#### ElastiCache Redis

```bash
# Tworzenie Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id amazon-feeds-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --security-group-ids sg-xxxxxxxxx
```

#### S3 Bucket

```bash
# Tworzenie S3 bucket
aws s3 mb s3://amazon-feeds-uploads-bucket

# Konfiguracja CORS
aws s3api put-bucket-cors \
    --bucket amazon-feeds-uploads-bucket \
    --cors-configuration file://s3-cors.json
```

### 2. ECS/Fargate Deployment

#### Task Definition

```json
{
  "family": "amazon-feeds-backend",
  "networkMode": "awsvpc",
  "requiresAttributes": [
    {
      "name": "com.amazonaws.ecs.capability.docker-remote-api.1.25"
    }
  ],
  "placementConstraints": [],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-registry/amazon-feeds-backend:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://postgres:password@your-rds-endpoint:5432/amazon_feeds"
        },
        {
          "name": "REDIS_URL",
          "value": "redis://your-elasticache-endpoint:6379/0"
        },
        {
          "name": "SECRET_KEY",
          "value": "your-production-secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/amazon-feeds-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Service Definition

```json
{
  "serviceName": "amazon-feeds-backend-service",
  "cluster": "default",
  "taskDefinition": "amazon-feeds-backend",
  "desiredCount": 2,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxxxxxxxx", "subnet-yyyyyyyyy"],
      "securityGroups": ["sg-xxxxxxxxx"],
      "assignPublicIp": "ENABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/amazon-feeds-tg/1234567890123456",
      "containerName": "backend",
      "containerPort": 8000
    }
  ]
}
```

### 3. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1

    - name: Build, tag, and push backend image to Amazon ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: amazon-feeds-backend
        IMAGE_TAG: ${{ github.sha }}
      run: |
        cd backend
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

    - name: Build, tag, and push frontend image to Amazon ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: amazon-feeds-frontend
        IMAGE_TAG: ${{ github.sha }}
      run: |
        cd frontend
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

    - name: Update ECS service
      run: |
        aws ecs update-service \
          --cluster default \
          --service amazon-feeds-backend-service \
          --force-new-deployment

    - name: Deploy frontend to S3 and CloudFront
      run: |
        cd frontend
        npm ci
        npm run build
        aws s3 sync build/ s3://your-frontend-bucket --delete
        aws cloudfront create-invalidation \
          --distribution-id YOUR_DISTRIBUTION_ID \
          --paths "/*"
```

## 🔧 Konfiguracja produkcyjna

### Environment Variables

```bash
# Backend
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-256-bit-secret-key
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-uploads-bucket
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
ENVIRONMENT=production

# Frontend
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_SENTRY_DSN=your-frontend-sentry-dsn
REACT_APP_ENVIRONMENT=production
```

### SSL/TLS Konfiguracja

```nginx
# nginx/production.conf
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    add_header Strict-Transport-Security "max-age=63072000" always;

    # Frontend
    location / {
        try_files $uri $uri/ /index.html;
        root /usr/share/nginx/html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Upload limits
        client_max_body_size 50M;
    }
}
```

## 📊 Monitoring i Alerting

### CloudWatch Alarms

```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "Amazon-Feeds-High-Error-Rate" \
    --alarm-description "Alert when error rate is too high" \
    --metric-name "5XXError" \
    --namespace "AWS/ApplicationELB" \
    --statistic "Sum" \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 10 \
    --comparison-operator "GreaterThanThreshold"

# Database connection alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "Amazon-Feeds-DB-Connections" \
    --alarm-description "Alert when DB connections are high" \
    --metric-name "DatabaseConnections" \
    --namespace "AWS/RDS" \
    --statistic "Average" \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator "GreaterThanThreshold"
```

### Sentry Integration

```python
# Backend monitoring
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FastApiIntegration(auto_enabling_integrations=False),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "development")
)
```

```javascript
// Frontend monitoring
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: process.env.REACT_APP_SENTRY_DSN,
  environment: process.env.REACT_APP_ENVIRONMENT,
  tracesSampleRate: 0.1,
});
```

## 🔒 Security Checklist

### Pre-deployment

- [ ] Zmiana domyślnych haseł
- [ ] Konfiguracja SSL/TLS certyfikatów
- [ ] Ustawienie strong secret keys
- [ ] Konfiguracja AWS IAM ról z minimalnymi uprawnieniami
- [ ] Włączenie WAF na ALB
- [ ] Konfiguracja Security Groups
- [ ] Szyfrowanie at-rest dla RDS i S3
- [ ] Włączenie logowania dostępu

### Post-deployment

- [ ] Regularne aktualizacje zależności
- [ ] Monitoring bezpieczeństwa
- [ ] Backup i disaster recovery testing
- [ ] Penetration testing
- [ ] Code security scans

## 🔄 Backup i Recovery

### Automated Backups

```bash
#!/bin/bash
# scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="amazon-feeds-backups"

# Database backup
pg_dump $DATABASE_URL | gzip > "/tmp/db_backup_$DATE.sql.gz"
aws s3 cp "/tmp/db_backup_$DATE.sql.gz" "s3://$S3_BUCKET/database/"

# Files backup (jeśli używasz lokalnego storage)
tar -czf "/tmp/files_backup_$DATE.tar.gz" /app/uploads
aws s3 cp "/tmp/files_backup_$DATE.tar.gz" "s3://$S3_BUCKET/files/"

# Cleanup local files
rm "/tmp/db_backup_$DATE.sql.gz" "/tmp/files_backup_$DATE.tar.gz"

# Cleanup old backups (keep 30 days)
aws s3 ls "s3://$S3_BUCKET/database/" --recursive | \
    awk '{if ($1 < "'$(date -d '30 days ago' '+%Y-%m-%d')'" && $1 != "") print $4}' | \
    xargs -I {} aws s3 rm "s3://$S3_BUCKET/{}"
```

### Disaster Recovery

```bash
#!/bin/bash
# scripts/restore.sh

BACKUP_DATE=$1
S3_BUCKET="amazon-feeds-backups"

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 YYYYMMDD_HHMMSS"
    exit 1
fi

# Download backup
aws s3 cp "s3://$S3_BUCKET/database/db_backup_$BACKUP_DATE.sql.gz" "/tmp/"

# Restore database
gunzip "/tmp/db_backup_$BACKUP_DATE.sql.gz"
psql $DATABASE_URL < "/tmp/db_backup_$BACKUP_DATE.sql"

# Cleanup
rm "/tmp/db_backup_$BACKUP_DATE.sql"

echo "Database restored from backup: $BACKUP_DATE"
```

## 📈 Performance Optimization

### Database Optimization

```sql
-- Indexes dla najczęściej używanych zapytań
CREATE INDEX CONCURRENTLY idx_feeds_user_status ON feeds(user_id, status);
CREATE INDEX CONCURRENTLY idx_feed_items_feed_id ON feed_items(feed_id);
CREATE INDEX CONCURRENTLY idx_feed_logs_feed_id_created ON feed_logs(feed_id, created_at DESC);

-- Partitioning dla dużych tabel (opcjonalne)
CREATE TABLE feed_logs_y2024m01 PARTITION OF feed_logs
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Application Optimization

```python
# Cache frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=100)
def get_user_credentials(user_id: int):
    # Cache user credentials for 5 minutes
    pass

# Database connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

## 🎯 Kolejne kroki

1. **Implementacja WebSocket** dla real-time updates
2. **API rate limiting** z Redis
3. **Multi-region deployment** dla wysokiej dostępności
4. **Advanced monitoring** z custom metrics
5. **Machine learning** dla auto-kategoryzacji produktów
6. **Webhook support** dla integracji z zewnętrznymi systemami

---

Po wdrożeniu pamiętaj o:
- Regularnym monitorowaniu metryk
- Aktualizacji dokumentacji
- Testowaniu backup/recovery procedures
- Reviewingu security logs