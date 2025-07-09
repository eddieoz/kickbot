#!/usr/bin/env python
"""
Test script for the Kick webhook handler.

This script runs the webhook handler and exposes it to the internet using ngrok,
making it possible to test with real webhook events from Kick.

Usage:
    python scripts/test_webhook.py

Requirements:
    - ngrok installed and in the system PATH
    - pyngrok package installed (pip install pyngrok)
"""

import os
import sys
import asyncio
import logging
import signal
import subprocess
import time
from pathlib import Path

# Add project root to PYTHONPATH if needed
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from kickbot.kick_webhook_handler import KickWebhookHandler, logger

# Configure logging
logging.basicConfig(level=logging.INFO)

# Example event handlers for testing
async def on_subscription(data):
    """Handle subscription events."""
    username = data.get("user", {}).get("username", "unknown")
    tier = data.get("tier", 1)
    logger.info(f"🎉 New subscription from {username} (Tier {tier})!")

async def on_gifted_subscription(data):
    """Handle gifted subscription events."""
    gifter = data.get("gifter", {}).get("username", "unknown")
    recipient = data.get("recipient", {}).get("username", "unknown")
    tier = data.get("tier", 1)
    logger.info(f"🎁 {gifter} gifted a Tier {tier} subscription to {recipient}!")

def start_ngrok(port):
    """Start ngrok and get the public URL."""
    try:
        from pyngrok import ngrok
        
        # Start ngrok tunnel
        public_url = ngrok.connect(port, "http").public_url
        logger.info(f"ngrok tunnel started at: {public_url}")
        
        # Extract the path from the webhook handler
        webhook_path = os.environ.get("KICK_WEBHOOK_PATH", "/kick/events")
        
        # Display the full URL to register for webhooks
        full_webhook_url = f"{public_url}{webhook_path}"
        logger.info(f"==========================================")
        logger.info(f"REGISTER THIS URL FOR KICK WEBHOOKS:")
        logger.info(f"{full_webhook_url}")
        logger.info(f"==========================================")
        
        return public_url
        
    except ImportError:
        logger.error("pyngrok package not found. Install it with: pip install pyngrok")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start ngrok: {e}")
        sys.exit(1)

def main():
    """Run the webhook handler with ngrok tunnel."""
    # Get configuration from environment variables or use defaults
    webhook_path = os.environ.get("KICK_WEBHOOK_PATH", "/kick/events")
    port = int(os.environ.get("KICK_WEBHOOK_PORT", "8000"))
    
    # Create the webhook handler
    handler = KickWebhookHandler(webhook_path=webhook_path, port=port, log_events=True)
    
    # Register event handlers
    handler.register_event_handler("channel.subscribed", on_subscription)
    handler.register_event_handler("channel.gifted_subscription", on_gifted_subscription)
    
    # Start ngrok
    start_ngrok(port)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        # ngrok tunnels are auto-closed when the script exits
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the webhook server
    logger.info("Starting webhook server...")
    handler.run_server()

if __name__ == "__main__":
    main() 