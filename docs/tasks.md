# EPIC: Implement New Kick Event System using Webhooks and OAuth

**Goal:** Transition Sr_Botoshi to use the official Kick API with webhooks and OAuth for reliable event handling (subscriptions, gifts, etc.), running in parallel with the existing system until proven stable.

---

## User Story 1: Setup Kick App and Basic OAuth Token Management

**As a** developer,
**I want to** set up a Kick application in the developer portal and implement a basic mechanism to obtain and store an App Access Token,
**So that** the bot can authenticate with the new Kick API.

**Given-When-Then (Behavior):**
*   **Given** I have access to the Kick Developer Portal,
*   **When** I create a new application for Sr_Botoshi and configure a redirect URI,
*   **Then** I should receive App credentials (Client ID, Client Secret).
*   **Given** the bot has App credentials and a redirect URI,
*   **When** the bot initiates the Authorization Code Flow with PKCE (requiring one-time user interaction via browser to grant `code`),
*   **Then** it should be able to exchange the `code` for a User Access Token (including a refresh token) with the necessary scopes (e.g., `events:subscribe`).
*   **Given** the bot has obtained tokens,
*   **When** the access token is nearing expiry or has expired,
*   **Then** it should use the refresh token to obtain a new access token.
*   **Given** the bot stores tokens,
*   **When** it restarts,
*   **Then** it should load and utilize the stored tokens if still valid.

**Tasks:**
- [x] 1.  **[Documentation Review & Clarification]** Confirm from Kick docs ([App Setup](https://docs.kick.com/getting-started/kick-apps-setup), [OAuth 2.1](https://docs.kick.com/getting-started/generating-tokens-oauth2-flow), [Scopes](https://docs.kick.com/getting-started/scopes)) that Authorization Code Flow with PKCE is required for `events:subscribe` scope, yielding a User Access Token. Note that App Access Tokens (Client Credentials) are "Not yet implemented".
- [x] 2.  **[Development]** Create/update a module (e.g., `kick_auth_manager.py`) responsible for:
    *   [x] Storing Kick App Client ID and Client Secret securely (from `.env` file: `KICK_CLIENT_ID`, `KICK_CLIENT_SECRET`).
    *   [x] Managing the configured `redirectURL`.
    *   **Phase 1: Initial Token Acquisition (Manual step for `code` grant via browser):**
        *   [x] Generating `code_verifier` and `code_challenge` for PKCE.
        *   [x] Constructing the authorization URL for `https://id.kick.com` (including `client_id`, `redirect_uri`, `scope`, `response_type=code`, `code_challenge`, `code_challenge_method=S256`).
        *   [x] Exchanging the authorization `code` and `code_verifier` for an access token and refresh token at Kick's token endpoint.
    *   **Phase 2: Token Storage and Refresh:**
        *   [x] ✓ Basic implementation of token refresh mechanism using `refresh_token` (partially implemented in `kick_auth_manager.py`, needs full integration and testing)
        *   [x] ✓ Simple file-based token storage implemented (`kickbot_tokens.json`). Considered sufficient for local execution.
        *   [x] ✓ Loading stored tokens on bot startup implemented.
        *   [x] ✓ Token validation (checking expiry) implemented.
- [x] 3.  **[Test (TDD)]** Write unit tests for the `kick_auth_manager.py`:
    *   [x] Test `code_verifier` and `code_challenge` generation.
    *   [x] Test construction of the authorization URL.
    *   [x] Test the token exchange process (mocking HTTP requests to Kick's token endpoint).
    *   [x] ✓ Test handling of OAuth errors during token acquisition and refresh.
    *   [x] ✓ Test file-based storage and retrieval of tokens.
    *   [x] ✓ Test the token refresh mechanism, including proactive refresh and handling of invalid refresh tokens.
- [x] 4.  **[Configuration]**
    *   [x] Ensure `KICK_CLIENT_ID` and `KICK_CLIENT_SECRET` are loaded from `.env`.
    *   [x] Add configuration for the `redirectURL` used by the bot.
    *   [x] Add configuration for the required OAuth scopes (e.g., "events:subscribe user:read").

**Remaining Tasks for User Story 1 Completion:**
- [x] 1. **[Development]** Implement secure storage of access and refresh tokens.
   *   [x] Current simple file-based storage (`kickbot_tokens.json`) is deemed sufficient as the bot runs locally. No further "secure" storage implementation needed.
- [x] 2. **[Development]** Complete and integrate token refresh functionality.
   *   [x] `KickAuthManager` implements `refresh_access_token` and `get_valid_token`.
   *   [x] `get_valid_token` attempts refresh if current token is invalid/expired.
   *   [x] If refresh fails (e.g., invalid refresh token), tokens are cleared, and an error is raised, signaling a need for manual user re-authorization. This simplified flow is considered complete.
- [x] 3. **[Test (TDD)]** Write tests for token storage and the completed refresh logic.
   *   [x] Tests for file-based saving/loading tokens exist and pass.
   *   [x] Tests for token refresh conditions and failure handling (leading to re-auth requirement) exist and pass.
- [x] 4. **[Documentation]** Create a helper script or clear instructions for the one-time manual step of obtaining the initial authorization `code` via the browser. Document the OAuth flow as implemented for Sr_Botoshi.
   *   [x] `scripts/kick_auth_example.py` serves as the helper script.
   *   [x] `docs/authentication.md` has been updated with clear instructions and explanation of this flow.
- [x] 5. **[Documentation]** Update overall authentication documentation regarding the new OAuth 2.0 PKCE flow, reflecting the current simplified token management.
   *   [x] `docs/authentication.md` and `SUMMARY.md` updated to reflect current state.

---

## User Story 2: Implement Webhook Endpoint for Event Reception

**As a** developer,
**I want to** create a secure HTTP webhook endpoint in the bot,
**So that** it can receive event notifications from Kick.

**Given-When-Then (Behavior):**
*   **Given** the bot is running and has a publicly accessible URL,
*   **When** Kick sends an event POST request to the bot's webhook URL,
*   **Then** the bot should successfully receive the request, validate it (optional but recommended: verify signature using Kick's public key), and acknowledge it with a 2xx status code.

**Tasks:**
- [x] 1.  **[Research/Documentation]** Review Kick documentation on "Verify event payloads using the public key."
  * Note: Public key signature verification is not fully documented yet in Kick docs, will implement later when available.
- [x] 2.  **[Development]** Set up a lightweight HTTP server (e.g., using Flask or FastAPI) in a new module (e.g., `kick_webhook_handler.py`).
    *   Define an endpoint (e.g., `/kick/events`) to receive POST requests.
    *   Implement basic request logging.
    *   ⬜ Implement payload signature verification (pending Kick documentation).
- [x] 3.  **[Test (TDD)]** Write integration tests for the webhook endpoint:
    *   Test successful reception of a valid mock Kick event.
    *   ⬜ Test rejection of requests with invalid signatures (pending Kick documentation).
    *   Test that the endpoint returns the correct HTTP status codes.
- [x] 4.  **[Setup/Deployment]** Configure a way to expose the local webhook endpoint to the public internet for testing (e.g., using ngrok or Cloudflare Tunnel, as suggested by Kick docs).
    *   Created `scripts/test_webhook.py` to run the webhook handler with ngrok tunnel.
- [x] 5.  **[Configuration]** Add configuration for the webhook path and port.
    *   Added environment variables `KICK_WEBHOOK_PATH` and `KICK_WEBHOOK_PORT`.

**Remaining Tasks:**
- [x] 6. **[Development]** Implement signature verification once Kick documentation is available.
- [x] 7. **[Development]** Add more sophisticated error handling and retry mechanisms.
  - Webhook handler logs errors from individual event handlers.
  - Main bot loop (`_poll`) has improved error handling and timeouts.
  - Retry mechanisms for incoming webhooks are typically handled by the sender (Kick) based on HTTP 5xx responses; bot provides appropriate status codes.
- [x] 8. **[Integration]** Integrate the webhook handler into the main bot startup/shutdown process.
  - `KickWebhookHandler` instance created in `KickBot`.
  - Server started/stopped using `aiohttp.web.AppRunner` within `KickBot.run()` and `KickBot.shutdown()`.
  - Configuration for webhook (enable, path, port) loaded from settings.

---

## User Story 3: Subscribe to Kick Events via API

**As a** developer,
**I want to** enable the bot to subscribe and unsubscribe to specific Kick events (e.g., new follower, subscription, gifted subs, chat messages) using the Kick API,
**So that** Kick knows where to send event notifications.

**Given-When-Then (Behavior):**
*   **Given** the bot has a valid App Access Token and a configured webhook URL,
*   **When** the bot starts, it calls the Kick API to subscribe to desired events (e.g., `channel.subscribed`, `channel.gifted_subscription`),
*   **Then** Kick should confirm the subscription, and future events of that type should be sent to the webhook URL.
*   **Given** the bot is subscribed to events,
*   **When** the bot shuts down (or is instructed to), it calls the Kick API to unsubscribe from events,
*   **Then** Kick should confirm the unsubscription.

**Tasks:**
- [x] 1.  **[Research/Documentation]** Identify the exact event names and versions required for subscriptions, gifted subscriptions, and any other relevant events from the "Webhook Payloads page" (need to find this page or its equivalent).
    - Identified: `channel.subscribed` v1, `channel.subscription.gifted` v1. Optional: `channel.followed` v1.
    - API endpoint: `https://api.kick.com/public/v1/events/subscriptions`.
    - Scope: `events:subscribe`.
- [x] 2.  **[Development]** In a new module (e.g., `kick_event_manager.py` or extend `kick_auth_manager.py`):
    - Created `kickbot/kick_event_manager.py` with `KickEventManager` class.
    *   [x] Implement a function to list current event subscriptions (`list_subscriptions`).
    *   [x] Implement a function to subscribe to a list of events (`subscribe_to_events` and `resubscribe_to_configured_events` for startup).
    *   [x] Implement a function to unsubscribe from events (`_unsubscribe_by_ids` and `clear_all_my_broadcaster_subscriptions` for shutdown).
- [x] 3.  **[Test (TDD)]** Write unit tests for the event subscription functions:
    *   Test `KickEventManager` methods (list, subscribe, unsubscribe, resubscribe) with mocked dependencies (`tests/test_kick_event_manager.py`).
    *   Test `KickBot` integration points (initialization, calls in run/shutdown) regarding `KickEventManager` (`tests/test_kick_bot.py`).
- [x] 4.  **[Integration]** Integrate these functions into the bot's startup and shutdown sequences.
    - `KickBot` now manages an `aiohttp.ClientSession`.
    - `KickClient` and `KickAuthManager` are initialized with this session in `KickBot.run()`.
    - `KickEventManager` is initialized in `KickBot.run()` (after `set_streamer` populates `streamer_info`) and uses the shared client/session.
    - `event_manager.resubscribe_to_configured_events()` called in `KickBot.run()`.
    - `event_manager.clear_all_my_broadcaster_subscriptions()` called in `KickBot.shutdown()`.
- [x] 5.  **[Configuration]** Add configuration for the list of events to subscribe to.
    - Added `KickEventsToSubscribe` to `settings.json` (e.g., `[{"name": "channel.subscribed", "version": 1}]`).
    - `KickBot` loads this configuration.

---

## User Story 4: Parse New Event Payloads and Dispatch to Handlers

**As a** developer,
**I want to** parse the incoming JSON payloads for subscribed events (like gifted subscriptions and new subscriptions) and dispatch them to appropriate new handler functions,
**So that** the bot can react to these events correctly.

**Given-When-Then (Behavior):**
*   **Given** the webhook endpoint receives a valid event payload from Kick (e.g., for a gifted subscription),
*   **When** the payload is processed,
*   **Then** the relevant information (e.g., gifter username, number of gifts, recipient details for gifted subs; subscriber username for new subs) should be extracted accurately using Pydantic models.
*   **Given** event data is extracted into a Pydantic model,
*   **When** it's dispatched,
*   **Then** a new, dedicated handler function (e.g., `handle_gifted_subscription_event` in `KickWebhookHandler`) should be invoked with this parsed model.

**Tasks:**
- [x] 1.  **[Research/Documentation]** Obtain and study the detailed JSON structure for each event type we subscribe to (from the "Webhook Payloads page" or infer based on API responses and common patterns).
    - Researched Kick API for `channel.followed`, `channel.subscribed`, `channel.subscription.gifted`. Where full official schemas were unavailable, structures were inferred for Pydantic modeling.
- [x] 2.  **[Development]**
    *   [x] Create new Pydantic models in `kickbot/event_models.py` to represent the structure of each incoming event payload (`FollowEvent`, `SubscriptionEvent`, `GiftedSubscriptionEvent`, and their associated data models like `FollowEventData`).
    *   [x] In `kickbot/kick_webhook_handler.py`, add logic to identify the event type from the payload and parse it into the corresponding Pydantic model (using `parse_kick_event_payload` which leverages Pydantic's discriminated unions).
    *   [x] Create new handler functions in `KickWebhookHandler` (e.g., `async def handle_follow_event(self, event: FollowEvent):`) that take these parsed Pydantic event objects as input.
    *   [x] Implement a dispatch mechanism in `KickWebhookHandler` (`dispatch_event` method) to call the appropriate new event handler based on the event type, passing the parsed Pydantic model.
- [x] 3.  **[Test (TDD)]** Write unit tests (`tests/test_kick_webhook_handler.py`):
    *   [x] For parsing mock JSON payloads for each event type into the Pydantic data models.
    *   [x] For the correct dispatching of parsed events to their new handlers (mocking the handlers).
    *   [x] For graceful handling of invalid/unknown JSON payloads and Pydantic validation errors.
    *   [x] For error propagation if a specific event handler raises an exception.
- [x] 4.  **[Refactor/Adapt (Basic Implementation)]** Implement basic logic in the new handler functions.
    *   [x] For User Story 4, this involved implementing enhanced, structured logging of event details using the parsed Pydantic models in `handle_follow_event`, `handle_subscription_event`, and `handle_gifted_subscription_event` in `KickWebhookHandler`.
    *   More complex adaptation of old logic (e.g., sending `!subgift_add`) is deferred to User Story 5, which deals with parallel operation and feature flagging.
- [x] 5.  **[Documentation]** Update webhook documentation (`docs/webhooks_and_signature_verification.md`) to reflect Pydantic-based event handling, list new supported events, describe model structure at a high level, and explain how to add new event handlers.

---

## User Story 5: Parallel Operation and Phased Rollout

**As a** developer,
**I want to** ensure the new event system can operate in parallel with the old WebSocket-based system,
**So that** we can test thoroughly and switch over with minimal disruption.

**Given-When-Then (Behavior):**
*   **Given** both the old WebSocket listener and the new webhook event system are active,
*   **When** an event (e.g., a gifted subscription) occurs that *could* be detected by both,
*   **Then** both systems might process it, but actions (like awarding points) should be designed to be idempotent or be controlled by a feature flag during transition.
*   **Given** the new system is deemed stable and correct,
*   **When** a feature flag is switched,
*   **Then** the old event detection/handling logic for those events (e.g., parsing "Kicklet" messages for gifts) should be disabled, and only the new system should act on them.

**Status:** In Progress

**Tasks:**
- [ ] 1.  **[Development]**
    *   [x] Introduce feature flags in the configuration (`settings.json`) to control the new webhook event system and disable legacy handlers (e.g., `FeatureFlags.EnableNewWebhookEventSystem`, `FeatureFlags.DisableLegacyGiftEventHandling`).
    *   Ensure new handler functions (e.g., `new_handle_gifted_subscriptions_event`) have distinct names or are in separate modules to avoid conflicts.
    *   Introduce feature flags in the configuration (e.g., `USE_WEBHOOK_FOR_GIFTS: true/false`) to control whether the new system's actions are enabled or if the old system's specific event parsing is disabled.
    *   Review actions taken by event handlers (e.g., sending chat messages, updating databases) to ensure they can be safely run by the new system, potentially in parallel during testing, or are guarded by the feature flags.
- [ ] 2.  **[Testing]**
    *   Conduct thorough testing with both systems running to compare behavior and ensure the new system correctly captures all relevant events.
    *   Monitor logs for any duplicated actions if not handled by idempotency or feature flags.
- [ ] 3.  **[Documentation]** Document the feature flags and the process for switching over.
- [ ] 4.  **[Refactor]** Once the new system is fully validated, create tasks to decommission and remove the old WebSocket event parsing logic for events now handled by webhooks.

---

# EPIC: Migrate Legacy Event Actions to New Webhook System
Goal: To transfer all meaningful actions previously performed by the old WebSocket-based event processing in KickBot (or intended to be performed) to the new Pydantic-based event handlers in KickWebhookHandler, ensuring they are controlled by feature flags for a phased rollout.
User Stories:

## User Story 6.1: Implement Follow Event Actions in New System
As a Sr_Botoshi operator,
I want the bot to perform defined actions (e.g., send a thank you message in chat, update follower stats) when a `channel.followed` event is received via webhook,
So that new followers are acknowledged appropriately by the new event system.

**Legacy Mechanism:**
*   The old system (in `KickBot._poll`) had a placeholder (`pass`) for `App\Events\FollowEvent` from WebSockets, indicating no specific follow actions were implemented there. This story is primarily about *new* functionality.

**Given-When-Then (Behavior):**
  Given the `EnableNewWebhookEventSystem` feature flag is `true`.
  And the bot is subscribed to `channel.followed` events.
  And the bot receives a valid `channel.followed` webhook event.
  When `KickWebhookHandler.handle_follow_event` processes the event.
  Then it should [Action 1: Log the follow event with details (already partially implemented for logging)].
  And Then it should [Action 2: If configured, attempt to send a "Thanks for the follow, {username}!" message to the Kick chat].
  And Then it should [Action 3: If a stats module exists or is planned, increment a follower counter or store follower data].

**TDD Tasks:**
  - [x] 1. **[Refactor/Test]** Ensure `kickbot/event_models.py` has an accurate `FollowEvent` Pydantic model matching the `channel.followed` payload from Kick docs.
  - [x] 2. **[Refactor/Test]** Ensure `settings.json` includes `{"name": "channel.followed", "version": 1}` in `KickEventsToSubscribe`.
  - [x] 3. **[Planning/Design]** Determine how `KickWebhookHandler` will send chat messages.
      *   Option A: Pass the `KickBot` instance to `KickWebhookHandler` during its initialization. `KickWebhookHandler` can then call `bot.send_text(...)`.
      *   Option B: Create a shared "Chat Service" or "Action Dispatcher" accessible by both.
      *   *Decision for now: Assume Option A for simplicity; `KickWebhookHandler` will need a `bot` attribute.*
  - [x] 4. **[Development]** In `KickWebhookHandler.__init__`, accept a `kick_bot_instance: KickBot` argument and store it as `self.bot`. Update instantiation in `KickBot.run()`.
  - [x] 5. **[Development]** In `KickWebhookHandler.handle_follow_event`:
      *   Implement logic to send a chat message: `await self.bot.send_text(f"Thanks for following, {event.data.follower.username}!")`.
      *   This action must be within the `if self.enable_new_webhook_system:` block (already present).
      *   (Optional Future) Implement stat update logic if a stats system is introduced.
  - [x] 6. **[Test]** Write unit tests for `KickWebhookHandler.handle_follow_event` in `tests/test_kick_webhook_handler.py`:
      *   Mock `self.bot.send_text`.
      *   Test that if `enable_new_webhook_system` is `true` and follow alert is enabled (see next step), `send_text` is called with the correct content.
      *   Test that if `enable_new_webhook_system` is `false`, `send_text` is not called.
      *   Test any stat update logic if implemented.
  - [x] 7. **[Configuration]** Add a setting in `settings.json` under `FeatureFlags` or a new section to enable/disable the chat message for new follows (e.g., `HandleFollowEventActions.SendChatMessage: true/false`).
      *   Update `KickWebhookHandler.handle_follow_event` to check this new flag in addition to `enable_new_webhook_system`.
  - [ ] 8. **[Documentation]** Document the new configuration flag and follow event actions.

## User Story 6.2: Implement New Subscription Event Actions in New System
As a Sr_Botoshi operator,
I want the bot to perform defined actions (e.g., send a thank you message, award points) when a `channel.subscription.new` event is received via webhook,
So that new subscribers are acknowledged and rewarded by the new event system.

**Legacy Mechanism:**
*   The old system did not explicitly handle a WebSocket event for new subscriptions. Acknowledgements, if any, would have relied on parsing general chat messages (e.g., "UserX just subscribed!"). This story is primarily about *new* specific functionality based on a dedicated event.

**Given-When-Then (Behavior):**
  Given the `EnableNewWebhookEventSystem` feature flag is `true`.
  And the bot is subscribed to `channel.subscription.new` events.
  And the bot receives a valid `channel.subscription.new` webhook event.
  When `KickWebhookHandler.handle_subscription_event` processes the event.
  Then it should [Action 1: Log the new subscription details (already partially implemented for logging)].
  And Then it should [Action 2: If configured, attempt to send a "Welcome to the sub club, {username}!" message to Kick chat].
  And Then it should [Action 3: If a points system exists, award "Blokitos" or other points to the subscriber].

**TDD Tasks:**
  - [x] 1. **[Refactor/Test]** Ensure `settings.json` subscribes to `{"name": "channel.subscription.new", "version": 1}`.
  - [x] 2. **[Refactor/Test]** Ensure `kickbot/event_models.py` has an accurate `SubscriptionEvent` Pydantic model for `channel.subscription.new`, aligning its fields (`subscriber`, `subscription_tier`, `months_subscribed`, `created_at`, `expires_at`, `is_gift` property) with the Kick docs.
  - [x] 3. **[Development]** In `KickWebhookHandler.handle_subscription_event` (ensure it takes `event: SubscriptionEventKick`):
      *   Ensure it uses `self.bot` (from US6.1 Task 4) for sending messages.
      *   Implement logic for sending chat messages (e.g., `await self.bot.send_text(...)`).
      *   (Future/Placeholder) Implement logic for awarding points. This requires:
          *   Access to a points system (e.g., `self.bot.db.add_points(user_id, amount)` or a new service) - Placeholder logged.
          *   Identifying the user (e.g., `event.data.subscriber.id`, `event.data.subscriber.username`).
      *   All new actions must be within the `if self.enable_new_webhook_system:` block.
  - [x] 4. **[Test]** Write unit tests for `KickWebhookHandler.handle_subscription_event` in `tests/test_kick_webhook_handler.py`:
      *   Mock `self.bot.send_text` and any points system calls.
      *   Test that actions are performed if `enable_new_webhook_system` is `true` and specific action flags (see next step) are enabled.
      *   Test correct message content and points awarded based on event data.
      *   Test that actions are not performed if `enable_new_webhook_system` is `false`.
  - [x] 5. **[Configuration]** Add settings in `settings.json` (e.g., under `FeatureFlags` or a new section `HandleSubscriptionEventActions`):
      *   `SendChatMessage: true/false`
      *   `AwardPoints: true/false`
      *   `PointsToAward: <number>`
      *   Update `KickWebhookHandler.handle_subscription_event` to check these.
  - [ ] 6. **[Documentation]** Document new configuration flags and subscription event actions.
    *   Update relevant docs (e.g., `docs/webhooks_and_signature_verification.md`, `SUMMARY.md`, potentially a new section for feature flags or event action configurations) to describe `HandleSubscriptionEventActions` and how new subscription events are processed.

## User Story 6.3: Implement Gifted Subscription Event Actions in New System
As a Sr_Botoshi operator,
I want the bot to perform defined actions (e.g., thank the gifter, award points to gifter and recipients) when a `channel.subscription.gifts` event is received via webhook,
So that gift subscriptions are properly acknowledged and rewarded by the new event system, and the old system's gift processing can be disabled.

**Legacy Mechanism:**
*   The old system (in `KickBot._poll`) had a placeholder (`pass`) for a `gifted_subscriptions` WebSocket event type.
*   Primary legacy handling is assumed to be via parsing "Kicklet" messages or similar system messages in `KickBot._handle_chat_message` (method not fully visible but inferred). The `DisableLegacyGiftEventHandling` flag is intended to gate this old parsing logic.

**Given-When-Then (Behavior):**
  Given the `EnableNewWebhookEventSystem` feature flag is `true`.
  And the bot is subscribed to `channel.subscription.gifts` events.
  And the bot receives a valid `channel.subscription.gifts` webhook event.
  When `KickWebhookHandler.handle_gifted_subscription_event` processes the event.
  Then it should [Action 1: Log the gift details (already partially implemented for logging)].
  And Then it should [Action 2: If configured, send a chat message thanking the gifter: "Thanks {gifter_username} for gifting {count} subs to {recipient_usernames}!"].
  And Then it should [Action 3: If a points system exists and configured, award "Blokitos" to the gifter, possibly scaled by number of gifts].
  And Then it should [Action 4: If a points system exists and configured, award "Blokitos" or a "welcome" status to each recipient].

  Given the `DisableLegacyGiftEventHandling` feature flag is `true`.
  When the old system part of `KickBot` (e.g., in `_handle_chat_message` parsing Kicklet messages) would have detected a gift.
  Then the old system should NOT perform its gift processing actions (e.g., awarding Blokitos, sending its own thank you message).

**TDD Tasks:**
  - [x] 1. **[Refactor/Test]** Ensure `settings.json` subscribes to `{"name": "channel.subscription.gifts", "version": 1}`.
  - [x] 2. **[Refactor/Test]** Ensure `kickbot/event_models.py` has an accurate `GiftedSubscriptionEvent` Pydantic model for `channel.subscription.gifts`, aligning its fields (`gifter`, `giftees` (or `recipients`), `tier`, `created_at`, `expires_at`) with Kick docs.
  - [ ] 3. **[Development]** In `KickWebhookHandler.handle_gifted_subscription_event` (ensure it takes `event: GiftedSubscriptionEvent`):
      *   Ensure it uses `self.bot` for sending messages and interacting with points.
      *   Implement logic for chat messages (thanking gifter, acknowledging recipients).
      *   Implement logic for awarding points (to gifter and each recipient).
      *   All new actions must be within the `if self.enable_new_webhook_system:` block.
  - [ ] 4. **[Test]** Write unit tests for `KickWebhookHandler.handle_gifted_subscription_event` in `tests/test_kick_webhook_handler.py`:
      *   Mock `self.bot.send_text` and points system calls.
      *   Test actions are performed if `enable_new_webhook_system` is `true` and specific action flags are enabled.
      *   Test correct thank you messages and points awarded to gifter/recipients.
      *   Test that actions are not performed if `enable_new_webhook_system` is `false`.
  - [ ] 5. **[Development - Legacy System]**
      *   **Locate:** Identify the exact code in `KickBot` (likely `_handle_chat_message` or a method it calls) that parses chat messages for gift notifications (e.g., "Kicklet" messages).
      *   **Gate:** Wrap this old logic with `if not self.disable_legacy_gift_handling:`. The `KickBot` instance needs `self.disable_legacy_gift_handling` correctly set by `set_settings`.
  - [ ] 6. **[Test - Legacy System]** Write/adapt integration tests for `KickBot`:
      *   Simulate a chat message that would trigger the old gift processing.
      *   Test that if `disable_legacy_gift_handling` is `true`, the old actions (mocked) are NOT performed.
      *   Test that if `disable_legacy_gift_handling` is `false`, the old actions ARE performed.
  - [ ] 7. **[Configuration]** Add settings in `settings.json` (e.g., under `FeatureFlags` or `HandleGiftedSubscriptionEventActions`):
      *   `SendThankYouChatMessage: true/false`
      *   `AwardPointsToGifter: true/false`
      *   `PointsToGifterPerSub: <number>`
      *   `AwardPointsToRecipients: true/false`
      *   `PointsToRecipient: <number>`
      *   The existing `GiftBlokitos` setting might need review/integration.
      *   Update `KickWebhookHandler.handle_gifted_subscription_event` to check these.
  - [ ] 8. **[Documentation]** Document new configuration flags and gifted subscription event actions.

## User Story 6.4: Implement Subscription Renewal Event Actions in New System (Optional)
As a Sr_Botoshi operator,
I want the bot to perform defined actions (e.g., send a thank you message for X months) when a `channel.subscription.renewal` event is received via webhook,
So that renewing subscribers are acknowledged by the new event system.

**Legacy Mechanism:**
*   No known legacy handling for specific subscription renewal events. This is entirely new functionality.

**Given-When-Then (Behavior):**
  Given the `EnableNewWebhookEventSystem` feature flag is `true`.
  And the bot is subscribed to `channel.subscription.renewal` events.
  And the bot receives a valid `channel.subscription.renewal` webhook event.
  When the corresponding handler `KickWebhookHandler.handle_subscription_renewal_event` processes the event.
  Then it should [Action 1: Log the renewal details].
  And Then it should [Action 2: If configured, send a chat message: "Thanks {username} for renewing your Tier {tier_level} sub for {cumulative_months} months!"].
  And Then it should [Action 3: If a points system exists and configured, award points, possibly scaled by renewal duration or tier].

**TDD Tasks:**
  - [ ] 1. **[Development]** In `settings.json`, add `{"name": "channel.subscription.renewal", "version": 1}` to `KickEventsToSubscribe`.
  - [ ] 2. **[Development]** In `kickbot/event_models.py`:
      *   Create Pydantic models `SubscriptionRenewalEventData` and `SubscriptionRenewalEvent` matching the `channel.subscription.renewal` payload from Kick docs (fields likely include `subscriber`, `tier`, `months_subscribed` (cumulative), `created_at`, `expires_at`).
      *   Add `SubscriptionRenewalEvent` to the `AnyKickEvent` Union and `parse_kick_event_payload`.
  - [ ] 3. **[Development]** In `KickWebhookHandler`:
      *   Create a new method `async def handle_subscription_renewal_event(self, event: SubscriptionRenewalEvent):`.
      *   Register this handler in `__init__`: `self.register_event_handler("channel.subscription.renewal", self.handle_subscription_renewal_event)`.
      *   Implement logic for sending chat messages (using `self.bot`) and (Future) awarding points.
      *   All new actions must be within the `if self.enable_new_webhook_system:` block.
  - [ ] 4. **[Test]** Write unit tests for `KickWebhookHandler.handle_subscription_renewal_event` in `tests/test_kick_webhook_handler.py`:
      *   Mock `self.bot.send_text` and points system calls.
      *   Test actions are performed if `enable_new_webhook_system` is `true` and specific action flags are enabled.
      *   Test correct message content based on event data (username, tier, duration).
      *   Test that actions are not performed if `enable_new_webhook_system` is `false`.
  - [ ] 5. **[Configuration]** Add settings in `settings.json` (e.g., under `FeatureFlags` or `HandleSubscriptionRenewalEventActions`):
      *   `SendChatMessage: true/false`
      *   `AwardPoints: true/false`
      *   `PointsToAward: <number>`
      *   Update `KickWebhookHandler.handle_subscription_renewal_event` to check these.
  - [ ] 6. **[Documentation]** Document new event, Pydantic models, configuration flags, and renewal event actions.

---

This plan should provide a good roadmap. The most critical initial step will be figuring out the precise OAuth flow for Kick's App Access Tokens. 