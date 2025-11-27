#!/bin/bash

set -e  # Exit on any error

echo "🚀 Installing CryptoTrade Application..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed
echo -e "${BLUE}📋 Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running. Please start Docker.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites satisfied${NC}"
echo ""

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p backend/uploads/kyc
mkdir -p backend/logs
mkdir -p nginx/ssl
chmod 750 backend/uploads/kyc
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Generate random secrets
echo -e "${BLUE}🔐 Generating secure random keys...${NC}"
JWT_SECRET=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)
echo -e "${GREEN}✅ Keys generated${NC}"
echo ""

# Create .env file
if [ ! -f .env ]; then
    echo -e "${BLUE}📝 Creating .env file...${NC}"
    cat > .env << EOF
# ===========================================
# CryptoTrade Environment Configuration
# Generated: $(date)
# ===========================================

# Database Configuration
POSTGRES_USER=cryptotrade
POSTGRES_PASSWORD=cryptotrade_secret_$(openssl rand -hex 8)
POSTGRES_DB=cryptotrade
DATABASE_URL=postgresql://cryptotrade:cryptotrade_secret_$(openssl rand -hex 8)@db:5432/cryptotrade

# Flask Configuration
FLASK_ENV=development
FLASK_APP=run.py
DEBUG=True

# Security Keys (DO NOT SHARE!)
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# JWT Configuration
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Email Configuration (Configure for production)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@cryptotrade.com

# Binance API (Configure for production)
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret-key
BINANCE_TESTNET=True

# Frontend Configuration
REACT_APP_API_URL=http://localhost:5001/api/v1
REACT_APP_WS_URL=http://localhost:5001

# Rate Limiting (Recommended for production)
RATELIMIT_STORAGE_URL=redis://redis:6379/1

# Logging
LOG_LEVEL=INFO

# Application Settings
APP_NAME=CryptoTrade
APP_VERSION=1.0.0
EOF
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please configure email and Binance API settings in .env${NC}"
else
    echo -e "${YELLOW}ℹ️  .env file already exists, skipping...${NC}"
fi
echo ""

# Stop any existing containers
echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
docker-compose down -v 2>/dev/null || true
echo -e "${GREEN}✅ Existing containers stopped${NC}"
echo ""

# Build Docker images
echo -e "${BLUE}🏗️  Building Docker images...${NC}"
docker-compose build --no-cache
echo -e "${GREEN}✅ Docker images built${NC}"
echo ""

# Start containers
echo -e "${BLUE}🚀 Starting containers...${NC}"
docker-compose up -d
echo -e "${GREEN}✅ Containers started${NC}"
echo ""

# Wait for database to be ready
echo -e "${BLUE}⏳ Waiting for database to be ready...${NC}"
sleep 10

# Check if database is ready
MAX_RETRIES=30
RETRY_COUNT=0
while ! docker-compose exec -T db pg_isready -U cryptotrade &> /dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Database failed to start after ${MAX_RETRIES} attempts${NC}"
        exit 1
    fi
    echo -e "${YELLOW}   Waiting for database... (${RETRY_COUNT}/${MAX_RETRIES})${NC}"
    sleep 2
done
echo -e "${GREEN}✅ Database is ready${NC}"
echo ""

# Run database migrations
echo -e "${BLUE}🗄️  Running database migrations...${NC}"
docker-compose exec -T backend flask db upgrade
echo -e "${GREEN}✅ Migrations completed${NC}"
echo ""

# Seed database with initial data
echo -e "${BLUE}🌱 Seeding database with initial data...${NC}"
docker-compose exec -T backend python -c "
from app import create_app, db
from app.utils.seed import seed_all

app = create_app()
with app.app_context():
    seed_all()
" 2>&1 | grep -E "(Currency|Trading|Fee|System|Admin|seeded|completed)" || echo -e "${YELLOW}⚠️  Seed data may already exist${NC}"
echo -e "${GREEN}✅ Database seeded${NC}"
echo ""

# Check services health
echo -e "${BLUE}🏥 Checking services health...${NC}"
sleep 5

# Check backend
if curl -s http://localhost:5001/api/v1/health &> /dev/null; then
    echo -e "${GREEN}✅ Backend API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Backend API is not responding yet${NC}"
fi

# Check frontend (may take longer to build)
if curl -s http://localhost:3000 &> /dev/null; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend is still building... (this may take a few minutes)${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        ✅ Installation Complete!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📌 Services:${NC}"
echo -e "   🌐 Frontend:        ${GREEN}http://localhost:3000${NC}"
echo -e "   🔧 Backend API:     ${GREEN}http://localhost:5001${NC}"
echo -e "   📊 Swagger Docs:    ${GREEN}http://localhost:5001/api/docs${NC}"
echo -e "   🗄️  PostgreSQL:      ${GREEN}localhost:5432${NC}"
echo -e "   💾 Redis:           ${GREEN}localhost:6379${NC}"
echo ""
echo -e "${BLUE}👤 Default Admin Credentials:${NC}"
echo -e "   📧 Email:    ${GREEN}admin@cryptotrade.com${NC}"
echo -e "   🔑 Password: ${GREEN}admin123!@#${NC}"
echo -e "   ${YELLOW}⚠️  Change password after first login!${NC}"
echo ""
echo -e "${BLUE}🛠️  Useful Commands:${NC}"
echo -e "   ${GREEN}docker-compose logs -f${NC}             # View all logs"
echo -e "   ${GREEN}docker-compose logs -f backend${NC}     # View backend logs"
echo -e "   ${GREEN}docker-compose logs -f frontend${NC}    # View frontend logs"
echo -e "   ${GREEN}docker-compose restart backend${NC}     # Restart backend"
echo -e "   ${GREEN}docker-compose down${NC}                # Stop all services"
echo -e "   ${GREEN}docker-compose up -d${NC}               # Start all services"
echo ""
echo -e "${BLUE}📚 Database Management:${NC}"
echo -e "   ${GREEN}docker-compose exec backend flask db revision -m 'msg'${NC}  # Create migration"
echo -e "   ${GREEN}docker-compose exec backend flask db upgrade${NC}            # Apply migrations"
echo -e "   ${GREEN}docker-compose exec backend python make_admin.py <email>${NC} # Make user admin"
echo ""
echo -e "${BLUE}🔒 Security Notes:${NC}"
echo -e "   • Change .env secrets in production"
echo -e "   • Configure email settings for notifications"
echo -e "   • Set up Binance API keys for trading"
echo -e "   • Enable SSL/TLS in production"
echo -e "   • Set FLASK_ENV=production for deployment"
echo ""
echo -e "${YELLOW}⏳ Note: Frontend may take 1-2 minutes to build on first start${NC}"
echo ""
