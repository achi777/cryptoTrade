#!/bin/bash

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Stopping CryptoTrade Application...${NC}"
echo ""

# Stop all services
docker-compose down

echo ""
echo -e "${RED}✅ All services stopped${NC}"
echo ""
echo -e "${BLUE}📌 Next steps:${NC}"
echo -e "   ${YELLOW}./start.sh${NC}                              # Start services"
echo -e "   ${YELLOW}docker-compose down -v${NC}                  # Remove containers and volumes"
echo -e "   ${YELLOW}./clean.sh${NC}                              # Clean all data"
echo ""
