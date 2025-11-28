#!/usr/bin/env python3
"""
Run Telegram bot in polling mode.

Usage:
    python run_telegram_bot.py

Requires TELEGRAM_BOT_TOKEN environment variable.
"""
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.services.telegram_bot import run_bot

if __name__ == "__main__":
    run_bot()

