#!/usr/bin/env python3
"""
Deep Pulse — Pre-flight Check
Verifies Ollama, Playwright, and Environment variables.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

def check_env():
    print("🔍 Checking Environment...")
    load_dotenv()
    node_id = os.getenv("NODE_ID")
    if node_id:
        print(f"  ✅ Node ID: {node_id}")
    else:
        print("  ❌ NODE_ID not found in .env")
        return False
        
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        print("  ✅ OpenRouter API Key: Found")
    else:
        print("  ❌ OPENROUTER_API_KEY not found in .env")
        return False
    return True

async def check_ollama():
    print("🔍 Checking Ollama Service...")
    url = os.getenv("LOCAL_DISTILL_URL", "http://localhost:11434/v1").replace("/v1", "")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                print(f"  ✅ Ollama Reachable: {models}")
                required = os.getenv("LOCAL_DISTILL_MODEL", "qwen2:0.5b")
                if required in models:
                    print(f"  ✅ Required Model '{required}': Found")
                else:
                    print(f"  ⚠️ Required Model '{required}': NOT FOUND (Available: {models})")
            else:
                print(f"  ❌ Ollama Error: HTTP {resp.status_code}")
                return False
    except Exception as e:
        print(f"  ❌ Ollama Connection Failed: {e}")
        return False
    return True

async def check_playwright():
    print("🔍 Checking Playwright...")
    try:
        from playwright.async_api import async_playwright
        print(f"  ✅ Playwright Library: Installed")
        # Simple check for browsers
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
                await browser.close()
                print("  ✅ Chromium Browser: Found")
                return True
            except Exception as e:
                print(f"  ❌ Chromium Browser: NOT FOUND ({e})")
                print("  💡 Run: playwright install chromium")
                return False
    except ImportError:
        print("  ❌ Playwright Library: NOT FOUND")
        return False

    return True

async def main():
    print("🚀 DEEP PULSE PRE-FLIGHT CHECK")
    print("="*30)
    
    env_ok = check_env()
    ollama_ok = await check_ollama()
    pw_ok = await check_playwright()
    
    print("="*30)
    if env_ok and ollama_ok and pw_ok:
        print("🎉 NODE READY FOR DEPLOYMENT")
        sys.exit(0)
    else:
        print("🧨 NODE VERIFICATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
