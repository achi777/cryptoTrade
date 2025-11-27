#!/bin/bash

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}🧹 Cleaning CryptoTrade Application...${NC}"
echo ""
echo -e "${RED}⚠️  WARNING: This will remove all containers, volumes, and data!${NC}"
echo -e "${YELLOW}Press Ctrl+C to cancel or Enter to continue...${NC}"
read

echo -e "${YELLOW}Stopping and removing containers...${NC}"
docker-compose down -v

echo -e "${YELLOW}Removing uploaded files...${NC}"
rm -rf backend/uploads/kyc/*

echo -e "${YELLOW}Removing logs...${NC}"
rm -rf backend/logs/*

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo -e "   Run ${GREEN}./install.sh${NC} to reinstall"
echo ""
