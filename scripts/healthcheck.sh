#!/bin/bash
# Health check script for development environment
# Verifies all required services are running and pages load correctly

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

check_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    printf "Checking %-20s ... " "$name"

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "$expected_code" ] || [ "$HTTP_CODE" = "302" ]; then
        echo -e "${GREEN}OK${NC} (HTTP $HTTP_CODE)"
        return 0
    else
        echo -e "${RED}FAILED${NC} (HTTP $HTTP_CODE, expected $expected_code)"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

check_port() {
    local name=$1
    local port=$2

    printf "Checking %-20s ... " "$name (port $port)"

    if nc -z localhost "$port" 2>/dev/null; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}NOT RUNNING${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo "=========================================="
echo "  Development Environment Health Check"
echo "=========================================="
echo ""

echo "--- Infrastructure Services ---"
check_port "PostgreSQL" 5432
check_port "Redis" 6379

echo ""
echo "--- Application Services ---"
check_port "Django" 8000
check_port "Vite" 5173

echo ""
echo "--- Page Load Tests ---"
check_service "Homepage" "http://localhost:8000/"
check_service "Login page" "http://localhost:8000/accounts/login/"
check_service "Signup page" "http://localhost:8000/accounts/signup/"
check_service "Vite assets" "http://localhost:5173/"

echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS check(s) failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Infrastructure: make start-bg"
    echo "  - Application:    make dev"
    exit 1
fi
