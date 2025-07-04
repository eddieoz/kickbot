# KickBot OAuth Webhook Migration EPIC

## Overview
Transform KickBot from WebSocket polling to OAuth-based webhook event system for better reliability, official API compliance, and real-time event processing.

## Business Value
- **Compliance**: Use official Kick API instead of unofficial WebSocket polling
- **Reliability**: OAuth tokens with refresh mechanisms vs session-based authentication
- **Real-time**: Webhook events are pushed immediately vs polling delays
- **Scalability**: Single webhook server handles multiple event types
- **Maintainability**: Centralized authentication and event processing

## Definition of Done
- [ ] Bot authenticates only via OAuth 2.0 with PKCE
- [ ] All chat messages received via `chat.message.sent` webhook events
- [ ] Single webhook server on port 8080 handles `/callback` and `/events`
- [ ] All existing commands (`!b`, `!following`, sound alerts, etc.) work via webhooks
- [ ] WebSocket polling completely removed
- [ ] All tests pass
- [ ] Integration tests validate end-to-end webhook flow

---

## Epic Stories

### Story 1: OAuth Token Management Enhancement
**As a** bot operator  
**I want** OAuth tokens to be properly managed with refresh capability  
**So that** the bot maintains authentication without manual intervention

**Acceptance Criteria:**
- [ ] OAuth token automatically refreshes when expired
- [ ] Token storage includes all required scopes: `user:read channel:read chat:read chat:write events:subscribe`
- [ ] Token validation before making API calls
- [ ] Graceful fallback when token refresh fails

**Test Cases:**
```python
def test_oauth_token_refresh():
    # Given: Expired OAuth token
    # When: API call is made
    # Then: Token is automatically refreshed
    pass

def test_oauth_scopes_validation():
    # Given: OAuth token with required scopes
    # When: Token is validated
    # Then: All required scopes are present
    pass
```

**Definition of Done:**
- OAuth manager handles token lifecycle automatically
- All required scopes included in token requests
- Integration test validates token refresh flow

---

### Story 2: Unified Webhook Server Setup
**As a** system operator  
**I want** a single webhook server handling both OAuth callbacks and event webhooks  
**So that** all webhook traffic is centralized and manageable

**Acceptance Criteria:**
- [ ] Single server process listens on port 8080
- [ ] `/callback` endpoint handles OAuth authorization codes
- [ ] `/events` endpoint receives Kick API webhook events
- [ ] Server validates webhook signatures (if enabled)
- [ ] Health check endpoint for monitoring

**Test Cases:**
```python
def test_webhook_server_startup():
    # Given: Server configuration
    # When: Server starts
    # Then: Both endpoints are accessible on port 8080
    pass

def test_oauth_callback_handling():
    # Given: OAuth authorization code
    # When: POST to /callback
    # Then: Token is exchanged and stored
    pass

def test_webhook_event_processing():
    # Given: Valid webhook payload
    # When: POST to /events
    # Then: Event is processed and returns 200
    pass
```

**Definition of Done:**
- Single webhook server handles both OAuth and events
- All endpoints respond correctly to valid requests
- Error handling for malformed requests

---

### Story 3: Chat Message Webhook Processing
**As a** bot user  
**I want** chat messages to be received via webhook events  
**So that** commands and responses work in real-time

**Acceptance Criteria:**
- [ ] `chat.message.sent` events trigger message processing
- [ ] Webhook payload correctly parsed to KickMessage objects
- [ ] All existing message handlers work with webhook data
- [ ] Message deduplication prevents double processing
- [ ] Bot ignores its own messages

**Test Cases:**
```python
def test_chat_message_webhook_parsing():
    # Given: chat.message.sent webhook payload
    # When: Webhook is processed
    # Then: KickMessage object is created correctly
    pass

def test_command_processing_via_webhook():
    # Given: !b command in webhook payload
    # When: Message is processed
    # Then: MarkovChain response is generated and sent
    pass

def test_message_deduplication():
    # Given: Duplicate webhook events
    # When: Events are processed
    # Then: Only first event triggers handler
    pass
```

**Definition of Done:**
- Chat messages received via webhooks instead of WebSocket
- All existing commands work without modification
- No duplicate message processing

---

### Story 4: Remove WebSocket Polling System
**As a** maintainer  
**I want** WebSocket polling code removed  
**So that** the codebase is simplified and only uses official APIs

**Acceptance Criteria:**
- [ ] `_poll()` method and WebSocket connection code removed
- [ ] `_recv()` and WebSocket message parsing removed
- [ ] Traditional client authentication code deprecated
- [ ] OAuth-only mode becomes the default
- [ ] Bot runs in webhook-only mode

**Test Cases:**
```python
def test_websocket_code_removed():
    # Given: Bot codebase
    # When: Code is reviewed
    # Then: No WebSocket connection code exists
    pass

def test_oauth_only_mode():
    # Given: Bot configuration
    # When: Bot starts
    # Then: Only OAuth authentication is used
    pass
```

**Definition of Done:**
- No WebSocket dependencies in bot code
- Bot operates entirely via webhooks and OAuth API
- Cleaner, more maintainable codebase

---

### Story 5: Event Subscription Management
**As a** bot operator  
**I want** the bot to automatically subscribe to required Kick events  
**So that** webhooks are received for all necessary event types

**Acceptance Criteria:**
- [ ] Bot subscribes to events on startup: `channel.followed`, `channel.subscription.*`, `chat.message.sent`
- [ ] Event subscriptions use correct webhook URL
- [ ] Subscription status is verified periodically
- [ ] Failed subscriptions are retried with backoff
- [ ] Subscription cleanup on bot shutdown

**Test Cases:**
```python
def test_event_subscription_on_startup():
    # Given: Bot with OAuth token
    # When: Bot starts
    # Then: All required events are subscribed
    pass

def test_subscription_verification():
    # Given: Running bot
    # When: Periodic verification runs
    # Then: Missing subscriptions are re-created
    pass

def test_subscription_cleanup():
    # Given: Bot with active subscriptions
    # When: Bot shuts down
    # Then: Subscriptions are cleaned up
    pass
```

**Definition of Done:**
- Bot automatically manages event subscriptions
- Robust error handling for subscription failures
- Clean shutdown removes subscriptions

---

### Story 6: Webhook Event Routing and Processing
**As a** bot developer  
**I want** webhook events routed to appropriate handlers  
**So that** all bot functionality works via webhook events

**Acceptance Criteria:**
- [ ] `chat.message.sent` events route to `_handle_chat_message()`
- [ ] Follow events trigger follow handlers
- [ ] Subscription events trigger subscription handlers
- [ ] Event data correctly transformed for existing handlers
- [ ] Unknown events are logged but don't crash the bot

**Test Cases:**
```python
def test_chat_event_routing():
    # Given: chat.message.sent webhook
    # When: Event is received
    # Then: _handle_chat_message() is called
    pass

def test_follow_event_processing():
    # Given: channel.followed webhook
    # When: Event is received
    # Then: Follow handler processes event
    pass

def test_unknown_event_handling():
    # Given: Unknown event type
    # When: Webhook is received
    # Then: Event is logged, no error thrown
    pass
```

**Definition of Done:**
- All webhook events properly routed
- Existing bot handlers work without modification
- Graceful handling of unexpected events

---

### Story 7: MarkovChain Integration via Webhooks
**As a** chat user  
**I want** MarkovChain commands to work via webhook events  
**So that** I can generate responses using `!b` and other commands

**Acceptance Criteria:**
- [ ] `!b` command triggers MarkovChain generation via webhook
- [ ] MarkovChain database updates from webhook chat messages
- [ ] Generated responses sent via OAuth API
- [ ] Response rate limiting and cooldowns respected
- [ ] MarkovChain special handling (gerard detection) works

**Test Cases:**
```python
def test_markov_command_via_webhook():
    # Given: !b command in webhook
    # When: Command is processed
    # Then: MarkovChain response is generated and sent
    pass

def test_markov_learning_from_webhooks():
    # Given: Chat messages via webhooks
    # When: Messages are processed
    # Then: MarkovChain database is updated
    pass

def test_markov_gerard_detection():
    # Given: Message containing 'gerard' via webhook
    # When: Message is processed
    # Then: Special gerard handling is triggered
    pass
```

**Definition of Done:**
- All MarkovChain functionality works via webhooks
- Chat learning continues via webhook messages
- Special features (gerard detection) maintained

---

### Story 8: Sound Alert Commands via Webhooks
**As a** streamer  
**I want** sound alert commands to work via webhook events  
**So that** viewers can trigger alerts using chat commands

**Acceptance Criteria:**
- [ ] All sound commands (`!aplauso`, `!burro`, etc.) work via webhooks
- [ ] Alert system integration maintained
- [ ] Command cooldowns and permissions respected
- [ ] Alert API calls succeed with proper error handling

**Test Cases:**
```python
def test_sound_alert_command_via_webhook():
    # Given: !aplauso command in webhook
    # When: Command is processed
    # Then: Alert is sent to alert system
    pass

def test_alert_cooldown_via_webhook():
    # Given: Rapid sound commands
    # When: Commands are processed
    # Then: Cooldown is respected
    pass
```

**Definition of Done:**
- All 20+ sound alert commands work via webhooks
- Alert system integration maintained
- Performance similar to WebSocket version

---

### Story 9: Timed Events and Periodic Tasks
**As a** bot operator  
**I want** timed events to continue working in webhook mode  
**So that** periodic messages and tasks execute as scheduled

**Acceptance Criteria:**
- [ ] Timed events (links, greetings) execute in webhook mode
- [ ] Event scheduling not dependent on WebSocket connection
- [ ] Bot remains active to process timed events
- [ ] Timed event cleanup on shutdown
- [ ] Live status detection for conditional events

**Test Cases:**
```python
def test_timed_events_in_webhook_mode():
    # Given: Bot in webhook mode with timed events
    # When: Time intervals elapse
    # Then: Timed events execute correctly
    pass

def test_live_status_conditional_events():
    # Given: Timed event with live status condition
    # When: Event should trigger
    # Then: Event only runs if stream is live
    pass
```

**Definition of Done:**
- All timed events work in webhook mode
- Bot maintains active state for scheduling
- Conditional events respect live status

---

### Story 10: Integration Testing and Validation
**As a** quality assurance engineer  
**I want** comprehensive integration tests  
**So that** the webhook-based bot works end-to-end

**Acceptance Criteria:**
- [ ] End-to-end test simulates complete webhook flow
- [ ] Mock webhook server for testing
- [ ] OAuth token lifecycle testing
- [ ] Performance testing vs WebSocket version
- [ ] Error scenario testing (network failures, invalid payloads)

**Test Cases:**
```python
def test_complete_webhook_flow():
    # Given: Running bot with webhook server
    # When: Mock webhook event is sent
    # Then: Event is processed and response is sent
    pass

def test_oauth_failure_recovery():
    # Given: Bot with expired token
    # When: API call fails
    # Then: Token is refreshed and call retried
    pass

def test_webhook_server_resilience():
    # Given: Invalid webhook payload
    # When: Payload is received
    # Then: Server responds gracefully without crashing
    pass
```

**Definition of Done:**
- 100% test coverage for webhook flow
- Performance meets or exceeds WebSocket version
- All error scenarios handled gracefully
- Documentation updated with new architecture

---

## Technical Implementation Notes

### Architecture Changes
1. **Remove**: WebSocket connection, `_poll()`, `_recv()`, session-based auth
2. **Add**: Unified webhook server, OAuth-only authentication, event subscription management
3. **Modify**: Message processing to use webhook payloads, chat sending via OAuth API

### Configuration Updates
```json
{
    "FeatureFlags": {
        "EnableNewWebhookEventSystem": true,
        "DisableInternalWebhookServer": false,
        "UseOAuthOnly": true,
        "DisableWebSocketPolling": true
    },
    "KickWebhookEnabled": true,
    "KickWebhookPort": 8080,
    "KickWebhookPath": "/events"
}
```

### Dependencies
- OAuth scopes: `user:read channel:read chat:read chat:write events:subscribe`  
- Webhook URL: `https://webhook.botoshi.sats4.life/events`
- Callback URL: `https://webhook.botoshi.sats4.life/callback`

### Security Considerations
- Webhook signature verification (optional)
- OAuth token secure storage
- Rate limiting on webhook endpoints
- Input validation on all webhook payloads

### Performance Targets
- Webhook response time: < 100ms
- Command processing time: < 500ms (same as WebSocket)
- Memory usage: Similar or lower than WebSocket version
- Event processing reliability: > 99.5%

---

## Success Metrics
- [ ] 100% of existing commands work via webhooks
- [ ] < 1s latency for chat command responses
- [ ] Zero manual token management required
- [ ] All integration tests pass
- [ ] Bot runs stably for 24+ hours without intervention