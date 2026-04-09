#!/usr/bin/env bash
# ═══════════════════════════════════════════════════
# Deep Ledger — Environment Check Script
# Validates that all required tools and dependencies
# are available on this system.
# ═══════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo ""
echo -e "${CYAN}${BOLD}  ╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}  ║  Deep Ledger — Environment Check         ║${NC}"
echo -e "${CYAN}${BOLD}  ╚══════════════════════════════════════════╝${NC}"
echo ""

PASS=0
FAIL=0
WARN=0

check() {
    local name="$1"
    local cmd="$2"
    local required="$3"

    if command -v "$cmd" &> /dev/null; then
        local version
        version=$($cmd --version 2>/dev/null | head -n 1 || echo "installed")
        echo -e "  ${GREEN}✅${NC} ${name}: ${version}"
        PASS=$((PASS + 1))
    else
        if [ "$required" = "required" ]; then
            echo -e "  ${RED}❌${NC} ${name}: NOT FOUND (required)"
            FAIL=$((FAIL + 1))
        else
            echo -e "  ${YELLOW}⚠️ ${NC} ${name}: NOT FOUND (optional)"
            WARN=$((WARN + 1))
        fi
    fi
}

echo -e "  ${BOLD}─── Core Tools ───${NC}"
check "Python"       "python3"     "required"
check "pip"          "pip3"        "required"
check "Docker"       "docker"      "required"
check "Docker Comp." "docker-compose" "optional"

echo ""
echo -e "  ${BOLD}─── Python Version Check ───${NC}"
if command -v python3 &> /dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 12 ]; then
        echo -e "  ${GREEN}✅${NC} Python ${PY_VER} (>= 3.12 required)"
    else
        echo -e "  ${YELLOW}⚠️ ${NC} Python ${PY_VER} detected. 3.12+ recommended."
        WARN=$((WARN + 1))
    fi
fi

echo ""
echo -e "  ${BOLD}─── .env Check ───${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "  ${GREEN}✅${NC} .env file found"
    
    # Check for required keys
    for key in NODE_PRIVATE_KEY NODE_PUBLIC_KEY NODE_ID OPENROUTER_API_KEY; do
        value=$(grep "^${key}=" "$PROJECT_ROOT/.env" | cut -d= -f2-)
        if [ -n "$value" ]; then
            echo -e "  ${GREEN}✅${NC} ${key}: configured"
        else
            echo -e "  ${RED}❌${NC} ${key}: EMPTY"
            FAIL=$((FAIL + 1))
        fi
    done
else
    echo -e "  ${RED}❌${NC} .env file NOT FOUND"
    echo -e "     Run: python3 src/core/identity_generator.py"
    FAIL=$((FAIL + 1))
fi

echo ""
echo -e "  ${BOLD}─── Python Packages ───${NC}"
if command -v python3 &> /dev/null; then
    for pkg in cryptography dotenv crawl4ai httpx neo4j; do
        if python3 -c "import $pkg" 2>/dev/null; then
            echo -e "  ${GREEN}✅${NC} ${pkg}"
        else
            echo -e "  ${YELLOW}⚠️ ${NC} ${pkg}: not installed"
            WARN=$((WARN + 1))
        fi
    done
fi

echo ""
echo -e "  ${BOLD}═══ SUMMARY ═══${NC}"
echo -e "  ${GREEN}Passed:${NC}  ${PASS}"
echo -e "  ${RED}Failed:${NC}  ${FAIL}"
echo -e "  ${YELLOW}Warnings:${NC} ${WARN}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "  ${RED}${BOLD}⚠️  Some required checks FAILED. Fix them before proceeding.${NC}"
    exit 1
else
    echo -e "  ${GREEN}${BOLD}✅ Environment is ready for Deep Ledger.${NC}"
fi
echo ""
