#!/bin/bash

echo "🛑 Stopping CryptoTrade Application..."

# Stop containers
docker-compose stop

echo ""
echo "✅ All services stopped."
echo ""
echo "📌 To start again: ./start.sh"
echo "📌 To remove containers: docker-compose down"
echo "📌 To remove containers and volumes: docker-compose down -v"
echo ""
