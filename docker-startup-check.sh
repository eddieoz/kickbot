#!/bin/bash
# Docker startup validation script for KickBot webhook server
# This script helps verify that the container is running correctly

echo "🚀 KickBot Docker Startup Validation"
echo "===================================="

# Check if container is running
echo "📦 Checking container status..."
if docker ps | grep -q "kickbot_botoshi"; then
    echo "✅ Container 'kickbot_botoshi' is running"
else
    echo "❌ Container 'kickbot_botoshi' is not running"
    echo "💡 Try: docker compose up -d"
    exit 1
fi

# Check if port 5009 is accessible
echo "🌐 Checking port accessibility..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5009/health | grep -q "200"; then
    echo "✅ Health endpoint responding on port 5009"
else
    echo "⚠️  Health endpoint not responding on port 5009"
    echo "💡 This might be normal if the bot is still starting up"
fi

# Check container logs for key startup messages
echo "📋 Checking startup logs..."
if docker logs kickbot_botoshi 2>&1 | grep -q "🚀 Starting KickBot with Unified Webhook Server"; then
    echo "✅ Bot started in unified webhook server mode"
else
    echo "⚠️  Bot may not have started in webhook mode"
fi

if docker logs kickbot_botoshi 2>&1 | grep -q "✅ Successfully subscribed to all configured Kick events"; then
    echo "✅ Event subscriptions completed successfully"
else
    echo "⚠️  Event subscriptions may not have completed"
    echo "💡 Check logs with: docker logs kickbot_botoshi"
fi

if docker logs kickbot_botoshi 2>&1 | grep -q "🌐 Starting unified webhook server on port 8080"; then
    echo "✅ Webhook server started on port 8080"
else
    echo "⚠️  Webhook server may not have started"
fi

echo ""
echo "📋 Quick Status Summary:"
echo "  Container: $(docker ps --filter name=kickbot_botoshi --format 'table {{.Status}}' | tail -n 1)"
echo "  External URL: https://webhook.botoshi.sats4.life"
echo "  Health Check: http://localhost:5009/health"
echo ""
echo "💡 Useful commands:"
echo "  View logs: docker logs kickbot_botoshi"
echo "  Follow logs: docker logs -f kickbot_botoshi"
echo "  Enter container: docker exec -it kickbot_botoshi bash"
echo "  Restart: docker compose restart"