#!/bin/bash

echo "🚀 Installing CryptoTrade Application..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/uploads/kyc
mkdir -p nginx/ssl

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Database
DB_USER=cryptotrade
DB_PASSWORD=cryptotrade_secret
DB_NAME=cryptotrade

# Flask
FLASK_ENV=development
JWT_SECRET_KEY=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
EOF
    echo "✅ .env file created with random secret keys"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

# Build Docker images
echo "🏗️  Building Docker images..."
docker-compose build

# Create and start containers
echo "🚀 Starting containers..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T backend flask db upgrade || echo "⚠️  Migration failed or already up to date"

echo ""
echo "✅ Installation complete!"
echo ""
echo "📌 Services running:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:5001"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "🛠️  Useful commands:"
echo "   - Start services: ./start.sh"
echo "   - Stop services: ./stop.sh"
echo "   - View logs: docker-compose logs -f"
echo ""
