#!/bin/bash
# Quick Demo Deployment Script

echo "🚀 Deploying Amazon Feed Migration SaaS Demo..."

# 1. Clone and setup
git clone https://github.com/yourusername/amazon-feed-migration-saas
cd amazon-feed-migration-saas

# 2. Quick config
cat > .env << EOF
DATABASE_URL=postgresql://postgres:demopass@postgres:5432/amazon_feeds
REDIS_URL=redis://redis:6379/0
SECRET_KEY=demo-secret-key-for-testing-only
ENVIRONMENT=demo
EOF

# 3. Start everything
docker-compose up -d

# 4. Wait for services
echo "⏳ Waiting for services to start..."
sleep 30

# 5. Initialize database
docker-compose exec backend alembic upgrade head

# 6. Create demo user
docker-compose exec backend python -c "
from models.database import User
from services.database import SessionLocal
from services.auth import AuthService

db = SessionLocal()
demo_user = User(
    username='demo',
    email='demo@amazonfeeds.com',
    hashed_password=AuthService.get_password_hash('Demo2024!'),
    is_active=True
)
db.add(demo_user)
db.commit()
print('Demo user created!')
"

echo "✅ Demo ready!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔗 Backend API: http://localhost:8000/docs"
echo "👤 Login: demo@amazonfeeds.com / Demo2024!"
echo ""
echo "📁 Upload the client's XLSB file to test!"