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
- [x] Bot authenticates only via OAuth 2.0 with PKCE
- [x] All chat messages received via `chat.message.sent` webhook events
- [x] Single webhook server on port 8080 handles `/callback` and `/events`
- [x] All existing commands (`!b`, `!following`, sound alerts, etc.) work via webhooks
- [x] WebSocket polling completely removed
- [x] All tests pass
- [x] Integration tests validate end-to-end webhook flow

---

## Epic Stories

### Story 1: OAuth Token Management Enhancement
**As a** bot operator  
**I want** OAuth tokens to be properly managed with refresh capability  
**So that** the bot maintains authentication without manual intervention

**Acceptance Criteria:**
- [x] OAuth token automatically refreshes when expired
- [x] Token storage includes all required scopes: `user:read channel:read chat:write events:subscribe`
- [x] Token validation before making API calls
- [x] Graceful fallback when token refresh fails

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
- [x] Single server process listens on port 8080
- [x] `/callback` endpoint handles OAuth authorization codes
- [x] `/events` endpoint receives Kick API webhook events
- [x] Server validates webhook signatures (if enabled)
- [x] Health check endpoint for monitoring

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
- [x] `chat.message.sent` events trigger message processing
- [x] Webhook payload correctly parsed to KickMessage objects
- [x] All existing message handlers work with webhook data
- [x] Message deduplication prevents double processing
- [x] Bot ignores its own messages

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
- [x] `_poll()` method and WebSocket connection code removed
- [x] `_recv()` and WebSocket message parsing removed
- [x] Traditional client authentication code deprecated
- [x] OAuth-only mode becomes the default
- [x] Bot runs in webhook-only mode

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
- [x] Bot subscribes to events on startup: `channel.followed`, `channel.subscription.*`, `chat.message.sent`
- [x] Event subscriptions use correct webhook URL
- [x] Subscription status is verified periodically
- [x] Failed subscriptions are retried with backoff
- [x] Subscription cleanup on bot shutdown

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
- [x] `chat.message.sent` events route to `_handle_chat_message()`
- [x] Follow events trigger follow handlers
- [x] Subscription events trigger subscription handlers
- [x] Event data correctly transformed for existing handlers
- [x] Unknown events are logged but don't crash the bot

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
- [x] `!b` command triggers MarkovChain generation via webhook
- [x] MarkovChain database updates from webhook chat messages
- [x] Generated responses sent via OAuth API
- [x] Response rate limiting and cooldowns respected
- [x] MarkovChain special handling (gerard detection) works

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
- [x] All sound commands (`!aplauso`, `!burro`, etc.) work via webhooks
- [x] Alert system integration maintained
- [x] Command cooldowns and permissions respected
- [x] Alert API calls succeed with proper error handling

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
- [x] Timed events (links, greetings) execute in webhook mode
- [x] Event scheduling not dependent on WebSocket connection
- [x] Bot remains active to process timed events
- [x] Timed event cleanup on shutdown
- [x] Live status detection for conditional events

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
- [x] End-to-end test simulates complete webhook flow
- [x] Mock webhook server for testing
- [x] OAuth token lifecycle testing
- [x] Performance testing vs WebSocket version
- [x] Error scenario testing (network failures, invalid payloads)

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
- OAuth scopes: `user:read channel:read chat:write events:subscribe`  
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
- [x] 100% of existing commands work via webhooks
- [x] < 1s latency for chat command responses
- [x] Zero manual token management required
- [x] All integration tests pass
- [x] Bot runs stably for 24+ hours without intervention

---

# Sub-Gift Points System Integration EPIC

## Overview
Restore the working sub-gift points system that was functional before the OAuth webhook migration. The migration created two separate systems: the old working points system and a new webhook handler with placeholder code that doesn't actually award points.

## Business Value
- **User Experience**: Gifters receive points as expected for their generous contributions
- **Feature Parity**: Maintains functionality that existed before OAuth migration
- **System Integrity**: Eliminates duplicate processing and ensures single source of truth
- **Reliability**: Uses existing tested points system instead of rebuilding from scratch

## Problem Statement
During the OAuth migration, the new webhook system (`handle_gifted_subscription_event`) was implemented with placeholder logging code, while the existing working points system (`_handle_gifted_subscriptions`) was left disconnected. This results in:
- Sub-gift events detected but no points awarded
- Placeholder logs instead of actual database operations
- Risk of duplicate processing if both systems trigger
- Broken user experience for gifters expecting points

## Definition of Done
- [x] Webhook events trigger the existing `_handle_gifted_subscriptions` method
- [x] Points are actually awarded to gifters (not just logged as placeholders)
- [x] No duplicate processing between old chat parsing and new webhook systems
- [x] Anonymous gifters handled correctly
- [x] All existing points functionality preserved
- [x] Integration tests validate end-to-end flow from webhook to points award

---

## Epic Stories

### Story 11: Integrate Existing Sub-Gift Points System with Webhook Handler
**As a** generous viewer who gifts subscriptions  
**I want** to receive points for my gifts immediately when detected via webhook events  
**So that** I'm rewarded for supporting the community and the feature works as expected

**Acceptance Criteria:**
- [x] Webhook `handle_gifted_subscription_event` calls existing `_handle_gifted_subscriptions` method
- [x] Placeholder logs in lines 522 and 537 of `kick_webhook_handler.py` replaced with actual method calls
- [x] Points are awarded using the existing `!subgift_add` command system
- [x] Anonymous gifters are handled correctly (no points awarded, proper logging)
- [x] Multiple recipient handling works correctly (points per recipient)
- [x] No duplicate processing when both webhook and chat message systems are active
- [x] Error handling preserves existing robustness

**Test Cases:**
```python
def test_webhook_triggers_existing_points_system():
    # Given: Webhook handler receives gifted subscription event
    # When: handle_gifted_subscription_event is called
    # Then: _handle_gifted_subscriptions method is called with correct parameters
    pass

def test_points_actually_awarded_via_webhook():
    # Given: User gifts 3 subscriptions detected via webhook
    # When: Event is processed
    # Then: !subgift_add command is sent with correct points calculation
    pass

def test_anonymous_gifter_webhook_handling():
    # Given: Anonymous user gifts subscriptions via webhook
    # When: Event is processed
    # Then: No points awarded but event is logged correctly
    pass

def test_no_duplicate_processing():
    # Given: Gift event triggers both webhook and chat message detection
    # When: Both systems process the same gift
    # Then: Points are only awarded once
    pass

def test_webhook_integration_error_handling():
    # Given: Webhook event with invalid gifter data
    # When: Integration attempts to call _handle_gifted_subscriptions
    # Then: Error is logged and webhook still returns 200
    pass
```

**Technical Implementation:**
```python
# In kick_webhook_handler.py, replace placeholder code with:
async def handle_gifted_subscription_event(self, event: GiftedSubscriptionEvent):
    # ... existing code ...
    
    # Replace placeholder logging with actual integration
    if self.award_points_to_gifter_for_gifted_sub and gifter_username != "Anonymous":
        try:
            await self.kick_bot_instance._handle_gifted_subscriptions(
                gifter_username, 
                num_gifted
            )
            logger.info(f"Awarded points to {gifter_username} for gifting {num_gifted} subs via webhook")
        except Exception as e:
            logger.error(f"Failed to award points to {gifter_username}: {e}", exc_info=True)
    
    # Handle recipients if needed (existing _handle_gifted_subscriptions focuses on gifter)
    # ... recipient handling logic ...
```

**Definition of Done:**
- Webhook events trigger existing points system without modification
- All existing points functionality preserved and working
- Integration test validates complete flow from webhook to points database
- No regression in chat message-based gift detection
- Error handling maintains system stability

**Story Points:** 1

**Dependencies:**
- Requires existing `_handle_gifted_subscriptions` method (already exists)
- Requires `GiftBlokitos` configuration setting (already exists)
- Requires `!subgift_add` command handler (already exists)

**Testing Strategy:**
- Unit tests for webhook handler integration
- Integration tests for end-to-end webhook-to-points flow
- Regression tests to ensure no duplicate processing
- Manual testing with actual gift events

---

## Technical Implementation Notes

### Integration Architecture
1. **Preserve Existing System**: Keep `_handle_gifted_subscriptions` method unchanged
2. **Connect Webhook Handler**: Modify `handle_gifted_subscription_event` to call existing method
3. **Maintain Configuration**: Use existing `GiftBlokitos` setting and `!subgift_add` command
4. **Prevent Duplication**: Ensure feature flags properly disable old chat parsing when webhooks are active

### Configuration Validation
```json
{
    "GiftBlokitos": 200,
    "FeatureFlags": {
        "EnableNewWebhookEventSystem": true,
        "DisableLegacyGiftEventHandling": true
    }
}
```

### Error Handling Strategy
- Webhook integration errors should not crash the webhook server
- Failed points awards should be logged but not prevent webhook acknowledgment
- Maintain existing error handling patterns from both systems

### Performance Considerations
- Integration should not add significant latency to webhook processing
- Existing database operations in `_handle_gifted_subscriptions` are already optimized
- Webhook should still return 200 quickly to prevent Kick API retries

---

## Success Metrics
- [ ] 100% of gifted subscriptions result in points being awarded
- [ ] < 100ms additional latency for webhook processing
- [ ] Zero duplicate point awards when both systems are active
- [ ] All existing gift point functionality preserved
- [ ] Integration tests achieve 100% coverage of the integration flow