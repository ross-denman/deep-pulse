#!/bin/bash
# Deep Pulse Gatekeeper — Mandatory Pre-Check for Subtree Push
# Usage: ./gatekeeper.sh

set -e

C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_RESET='\033[0m'

echo -e "${C_YELLOW}🛡️  Deep Pulse Gatekeeper: Initiating Pre-Check Protocol...${C_RESET}"

# 1. Check for sensitive files in src/public/
echo -e "🔎 Checking for sensitive files in src/public/..."
if [ -f "src/public/.env" ]; then
    echo -e "${C_RED}❌ ERROR: .env file found in src/public/ directory!${C_RESET}"
    exit 1
fi

# 2. Scan for secrets (Hardcoded Keys, PATs, Tokens) in src/public/
echo -e "🔍 Scanning src/public/ for leaked credentials..."
# Look for common assignment patterns followed by something that looks like a key/token
LEAK_FOUND=0
# 1. Look for hardcoded hex strings (64 chars usually)
if grep -rE "['\"][0-9a-fA-F]{32,128}['\"]" src/public/ --exclude-dir=__pycache__ --exclude=*.pyc -q; then
    echo -e "${C_YELLOW}⚠️ POSSIBLE LEAK: Hardcoded hex-string found! (Could be a CID or test ID, but verify.)${C_RESET}"
    grep -rE "['\"][0-9a-fA-F]{32,128}['\"]" src/public/ --exclude-dir=__pycache__ --exclude=*.pyc || true
    # We don't exit for this yet, just warn.
fi

# 2. Look for explicit secret assignments (e.g., SECRET = "...")
SECRETS=(
    "^[[:blank:]]*OUTPOST_KEY[[:blank:]]*=[[:blank:]]*['\"][^'\"]+['\"]"
    "^[[:blank:]]*OUTPOST_PUBLIC_KEY[[:blank:]]*=[[:blank:]]*['\"][^'\"]+['\"]"
    "^[[:blank:]]*GITHUB_TOKEN[[:blank:]]*=[[:blank:]]*['\"][^'\"]+['\"]"
    "^[[:blank:]]*PAT_[[:blank:]]*=[[:blank:]]*['\"][^'\"]+['\"]"
)

for secret in "${SECRETS[@]}"; do
    if grep -rE "$secret" src/public/ --exclude-dir=__pycache__ --exclude=*.pyc -q; then
        echo -e "${C_RED}❌ ERROR: Hardcoded sensitive assignment found: $secret${C_RESET}"
        grep -rE "$secret" src/public/ --exclude-dir=__pycache__ --exclude=*.pyc
        LEAK_FOUND=1
    fi
done

if [ $LEAK_FOUND -eq 1 ]; then
    echo -e "${C_RED}❌ PUSH ABORTED: Sensitive patterns found in src/public/ folder.${C_RESET}"
    exit 1
fi

# 3. Verify cross-directory imports
echo -e "🔗 Verifying that src/public/ is self-contained (no direct private/ imports)..."
if grep -r "from private." src/public/ -q; then
    echo -e "${C_RED}❌ ERROR: Public code is importing from private modules!${C_RESET}"
    grep -r "from private." src/public/
    exit 1
fi

# 4. Run Verification Suite
echo -e "🧪 Running high-integrity test suite..."
if [ -d "tests" ]; then
    # We run tests from the root, expecting PYTHONPATH to be set
    export PYTHONPATH=$PYTHONPATH:.:src/public
    if .venv/bin/python3 -m pytest tests/; then
        echo -e "${C_GREEN}✅ Tests passed.${C_RESET}"
    else
        echo -e "${C_RED}❌ Tests failed. Fix before pushing.${C_RESET}"
        exit 1
    fi
else
    echo -e "${C_YELLOW}⚠️ No tests folder found. Skipping...${C_RESET}"
fi

echo -e "${C_GREEN}✨ GATEKEEPER PASSED. Public mirror ready for distribution.${C_RESET}"
exit 0
