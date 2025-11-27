#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting CryptoTrade Application...${NC}"
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Start all services
docker-compose up -d

# Wait for services to initialize
sleep 3

# Check container status
echo ""
echo -e "${BLUE}📊 Container Status:${NC}"
docker-compose ps

echo ""
echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo -e "${BLUE}📌 Services:${NC}"
echo -e "   🌐 Frontend:        ${GREEN}http://localhost:3000${NC}"
echo -e "   🔧 Backend API:     ${GREEN}http://localhost:5001${NC}"
echo -e "   📊 Swagger Docs:    ${GREEN}http://localhost:5001/api/docs${NC}"
echo -e "   🗄️  PostgreSQL:      ${GREEN}localhost:5432${NC}"
echo -e "   💾 Redis:           ${GREEN}localhost:6379${NC}"
echo ""
echo -e "${BLUE}📝 View logs:${NC}"
echo -e "   ${GREEN}./logs.sh${NC}              # All logs"
echo -e "   ${GREEN}./logs.sh backend${NC}      # Backend only"
echo -e "   ${GREEN}./logs.sh frontend${NC}     # Frontend only"
echo ""
