#!/bin/bash

# AgriMind AI – One-Command Startup Script

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ─────────────────────────────────────────────────────────────────────────────
# Colors for output
# ─────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─────────────────────────────────────────────────────────────────────────────
# Check for .env file
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}🌾 AgriMind AI – Starting...${NC}\n"

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}Please create a .env file with:${NC}"
    echo -e "${YELLOW}GROQ_API_KEY=your_api_key_here${NC}\n"
    echo -e "Get your API key from: ${BLUE}https://console.groq.com${NC}\n"
    exit 1
fi

# Check if GROQ_API_KEY is set
if ! grep -q "GROQ_API_KEY=" .env; then
    echo -e "${RED}❌ Error: GROQ_API_KEY not found in .env${NC}\n"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Check virtual environment
# ─────────────────────────────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# ─────────────────────────────────────────────────────────────────────────────
# Activate virtual environment and start server
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${GREEN}✓ Configuration verified${NC}"
echo -e "${BLUE}🚀 Starting AgriMind AI server...${NC}\n"

source venv/bin/activate

# Start uvicorn
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 2>&1 | while IFS= read -r line; do
    if [[ "$line" == *"Uvicorn running on"* ]]; then
        echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✓ AgriMind AI is ready!${NC}\n"
        echo -e "   ${BLUE}🌐 Open in browser:${NC}"
        echo -e "   ${BLUE}→ http://127.0.0.1:8000${NC}\n"
        echo -e "   ${BLUE}📚 API Documentation:${NC}"
        echo -e "   ${BLUE}→ http://127.0.0.1:8000/docs${NC}\n"
        echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}Press CTRL+C to stop the server${NC}\n"
    fi
    echo "$line"
done
