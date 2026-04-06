#!/bin/bash
# Deep Pulse — Crawler Infrastructure Setup
echo "Initializing Crawler Dependencies..."

# 1. Update System
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Playwright System Dependencies
# This handles the libgbm, libasound, and other headless requirements
pip install playwright
sudo playwright install-deps

# 3. Install Browsers (Chromium only for lower CPU overhead)
playwright install chromium

# 4. Initialize Crawl4AI Models (Optional but recommended for speed)
# This caches local extraction models for the SLM sieve
crawl4ai-download-models

echo "Sovereign Intelligence Cost Shield: READY."
