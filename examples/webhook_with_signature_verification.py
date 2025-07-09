#!/usr/bin/env python3

"""
Example of using the KickWebhookHandler with signature verification.

This example demonstrates how to set up a webhook handler for Kick.com events
with signature verification enabled to enhance security.

Usage:
    python webhook_with_signature_verification.py
"""

import asyncio
import json
import logging

from kickbot import KickWebhookHandler, KickSignatureVerifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("webhook_example")

# Event handlers
async def on_subscription(data):
    """Handle subscription events"""
    user = data.get("user", {})
    username = user.get("username", "unknown")
    logger.info(f"New subscription from {username}!")
    # You can add custom logic here, like updating a database or sending a thank you message

async def on_livestream_status(data):
    """Handle livestream status changes"""
    status = data.get("status", "unknown")
    logger.info(f"Livestream status changed to: {status}")
    # You could trigger actions based on stream starting or ending

def main():
    # Create the signature verifier
    verifier = KickSignatureVerifier()
    
    # Create the webhook handler with signature verification enabled
    handler = KickWebhookHandler(
        webhook_path="/kick/webhooks",
        port=8000,
        log_events=True,
        signature_verification=True
    )
    
    # Assign the signature verifier to the webhook handler
    handler.signature_verifier = verifier
    
    # Register event handlers
    handler.register_event_handler("channel.subscribed", on_subscription)
    handler.register_event_handler("livestream.status", on_livestream_status)
    
    # Print setup information
    logger.info("Webhook handler configured with signature verification")
    logger.info("Endpoint: http://your-server:8000/kick/webhooks")
    logger.info("Make sure to configure this URL in your Kick dashboard")
    
    # Start the server
    handler.run_server()

if __name__ == "__main__":
    main() 