#!/bin/bash

echo "🚀 Starting CryptoTrade Application..."

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start containers
docker-compose up -d

# Wait a moment for services to initialize
sleep 3

# Check container status
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "✅ CryptoTrade is starting..."
echo ""
echo "📌 Services:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:5001"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "📝 View logs: docker-compose logs -f [service_name]"
echo "   Example: docker-compose logs -f backend"
echo ""
