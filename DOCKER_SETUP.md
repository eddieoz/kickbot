# KickBot Docker Setup (Updated for Webhook Mode)

## Quick Start

The bot now runs in unified webhook mode with OAuth authentication and automatic event subscriptions.

### 1. Start the Bot
```bash
docker compose up -d
```

### 2. Verify Everything is Working
```bash
./docker-startup-check.sh
```

### 3. View Logs
```bash
docker logs -f kickbot_botoshi
```

## What Happens When You Start the Bot

When you run `docker compose up`, the bot will:

1. **🔐 Initialize OAuth Authentication** (Story 1)
   - Load OAuth tokens from `kickbot_tokens.json`
   - Refresh tokens automatically if needed
   - Fallback to direct auth if OAuth fails

2. **🌐 Start Unified Webhook Server** (Story 2)
   - Single server on port 8080 (mapped to host port 5009)
   - `/callback` endpoint for OAuth authorization
   - `/events` endpoint for Kick API webhooks
   - `/health` endpoint for monitoring

3. **📡 Subscribe to Events Automatically** (Story 5)
   - Subscribe to: `chat.message.sent`, `channel.followed`, `channel.subscription.*`
   - Retry failed subscriptions with exponential backoff
   - Schedule periodic verification every 30 minutes

4. **🤖 Process Commands via Webhooks**
   - All bot commands (`!b`, `!github`, sound alerts, etc.) work via webhooks
   - No more WebSocket polling
   - Real-time event processing

## Architecture

```
Internet → nginx → localhost:5009 → Docker Container Port 8080 → KickBot
```

- **External URL**: `https://webhook.botoshi.sats4.life`
- **Host Port**: `5009` 
- **Container Port**: `8080`
- **Health Check**: `http://localhost:5009/health`

## Configuration Files

- **`.env`**: OAuth credentials and webhook URLs
- **`settings.json`**: Bot configuration and events to subscribe
- **`docker-compose.yml`**: Container configuration
- **`kickbot_tokens.json`**: OAuth tokens (auto-generated)

## Troubleshooting

### Bot Won't Start
```bash
# Check container status
docker ps

# View startup logs
docker logs kickbot_botoshi

# Restart container
docker compose restart
```

### Webhook Events Not Working
```bash
# Check event subscriptions in logs
docker logs kickbot_botoshi | grep -i "subscrib"

# Verify webhook URL is accessible
curl https://webhook.botoshi.sats4.life/health

# Check nginx configuration
```

### OAuth Issues
```bash
# Re-authorize OAuth (if needed)
docker exec -it kickbot_botoshi bash
conda activate kickbot
python scripts/kick_auth_example.py --authorize
```

## Monitoring

- **Health Check**: `http://localhost:5009/health`
- **Container Logs**: `docker logs -f kickbot_botoshi`
- **Event Subscriptions**: Check logs for subscription status
- **Command Processing**: Look for chat message processing in logs

## Development

### Enter Container
```bash
docker exec -it kickbot_botoshi bash
# Conda environment is auto-activated
```

### Rebuild After Changes
```bash
docker compose down
docker compose build
docker compose up -d
```

### Test Webhook Locally
```bash
# Send test webhook event
curl -X POST http://localhost:5009/events \
  -H "Content-Type: application/json" \
  -d '{"event":{"type":"chat.message.sent"},"data":{"sender":{"username":"testuser"},"content":"!github"}}'
```