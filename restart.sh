#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Restarting CryptoTrade Application...${NC}"
echo ""

# Restart all services
docker-compose restart

echo ""
echo -e "${GREEN}✅ All services restarted!${NC}"
echo ""
echo -e "${BLUE}📌 Services:${NC}"
echo -e "   🌐 Frontend:        ${GREEN}http://localhost:3000${NC}"
echo -e "   🔧 Backend API:     ${GREEN}http://localhost:5001${NC}"
echo -e "   📊 Swagger Docs:    ${GREEN}http://localhost:5001/api/docs${NC}"
echo ""
