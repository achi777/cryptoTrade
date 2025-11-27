#!/bin/bash

# Colors
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE=${1:-""}

if [ -z "$SERVICE" ]; then
    echo -e "${BLUE}📋 Viewing all logs (Ctrl+C to exit)...${NC}"
    echo ""
    docker-compose logs -f
else
    echo -e "${BLUE}📋 Viewing ${SERVICE} logs (Ctrl+C to exit)...${NC}"
    echo ""
    docker-compose logs -f "$SERVICE"
fi
