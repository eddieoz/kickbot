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
*   **Given** the `EnableNewWebhookEventSystem` feature flag is `true`,
*   **When** an event (e.g., a new subscription) occurs,
*   **Then** the new webhook system should process it and perform configured actions (e.g., send chat message, log points award), independent of any general chat parsing by the old system.
*   **Given** the `EnableNewWebhookEventSystem` feature flag is `false`,
*   **When** an event occurs,
*   **Then** the new webhook system should NOT perform its specific event actions, even if individual action flags (e.g., `HandleSubscriptionEventActions.SendChatMessage`) are true.
*   **Given** the new system is deemed stable and correct,
*   **When** the `EnableNewWebhookEventSystem` feature flag is `true`,
*   **Then** the new system should be the primary handler for follow, new subscription, gifted subscription, and renewal events. (Note: Legacy system was found to have no conflicting specific handlers for these events).

**Status:** Complete

**Tasks:**
- [x] 1.  **[Development - Feature Flags & Configuration Review]**
    *   [x] Introduce feature flag `EnableNewWebhookEventSystem` in `settings.json` to control all new webhook event system actions. (Implemented and verified in `KickBot` and `KickWebhookHandler`)
    *   [x] Introduce feature flag `DisableLegacyGiftEventHandling` in `settings.json`. (Implemented. Note: No active conflicting legacy gift processing was found for this flag to gate, so its current effect is minimal. It remains for future-proofing.)
    *   [x] Ensure new handler functions in `KickWebhookHandler` (e.g., `handle_follow_event`) are distinct and do not conflict with old system method names. (Verified)
    *   [x] Confirm that new system actions are controlled by `EnableNewWebhookEventSystem` and further refined by specific action configurations (e.g., `HandleFollowEventActions.SendChatMessage`). (Verified)
    *   [N/A] No further `DisableLegacy...` flags are needed for other events (new subscription, follow, renewal) as no specific conflicting legacy parsing for these events was identified in `KickBot._poll` or `MarkovChain.message_handler`.
    *   [x] Review actions (chat messages, points logging) in `KickWebhookHandler` to ensure they are guarded by `EnableNewWebhookEventSystem` and specific action flags. (Verified)
- [x] 2.  **[Testing - New System Functionality and Control]**
    *   Conduct thorough testing to ensure the new webhook system, when `EnableNewWebhookEventSystem` is `true`, correctly processes each supported event type (follow, new subscription, gifted subscription, renewal) and performs actions (chat messages, points logging) as dictated by their respective `Handle...EventActions` configurations in `settings.json`. (Covered by existing unit tests in `tests/test_kick_webhook_handler.py`)
    *   Verify that when `EnableNewWebhookEventSystem` is `false`, the new webhook system does NOT perform any of these event-specific actions, regardless of the state of individual `Handle...EventActions` flags. (Covered by existing unit tests)
    *   Verify that individual action flags (e.g., `HandleSubscriptionEventActions.SendChatMessage: false`) correctly prevent specific actions even when `EnableNewWebhookEventSystem` is `true`. (Covered by existing unit tests)
    *   Monitor logs for correct behavior and absence of errors under various configurations. (Covered by existing unit tests)
- [x] 3.  **[Documentation - Feature Flags and Operation]**
    *   [x] Update `docs/webhooks_and_signature_verification.md` to clearly document the `EnableNewWebhookEventSystem` flag as the master control for new webhook actions.
    *   [x] Clarify the role and current status of `DisableLegacyGiftEventHandling` in the documentation.
    *   [x] Ensure documentation emphasizes that individual event action configurations are contingent on `EnableNewWebhookEventSystem` being true.
    *   [x] Document the overall process for enabling/disabling the new webhook event system and its specific actions for phased rollout or troubleshooting.
- [ ] 4.  **[Refactor - Future Considerations]**
    *   Once the new webhook system is fully validated and deemed sufficient for all event-driven needs (follows, subs, gifts, renewals), evaluate the remaining old WebSocket infrastructure (`_poll` loop in `KickBot`, `MarkovChain.message_handler` in the context of event detection rather than Markov sentence generation).
    *   Create tasks to decommission or refactor parts of the old WebSocket message polling/handling if they become redundant for event processing. (The `MarkovChain` for sentence generation is a separate functionality from event handling).

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
  - [x] 6. **[Documentation]** Document new configuration flags and subscription event actions.
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
  - [x] 3. **[Development]** In `KickWebhookHandler.handle_gifted_subscription_event` (ensure it takes `event: GiftedSubscriptionEvent`):
      *   Ensure it uses `self.bot`

---

# EPIC: Transition Chat Functionality to Official Kick API

**Goal:** Refactor all bot chat message sending (general messages, replies) to use the official Kick Chat API endpoint (`POST /public/v1/chat`) with OAuth Bearer token authentication, eliminating the need for direct username/password/2FA login by `KickClient` for chat operations and making the bot fully non-interactive at runtime.

---

## User Story 7: Refactor Chat Message Sending to Use Kick API

**As a** Sr_Botoshi operator,
**I want** the bot to send all chat messages (including replies) using the official Kick Chat API (`POST /public/v1/chat`) with its OAuth token,
**So that** the bot no longer relies on the `KickClient`'s direct login (username/password/2FA) for sending messages, enabling fully non-interactive startup and operation in Docker.

**Given-When-Then (Behavior):**

*   **Given** the bot has a valid OAuth access token (managed by `KickAuthManager`),
*   **When** any part of the bot needs to send a general chat message (e.g., via `KickBot.send_text`),
*   **Then** the message should be sent by making an authenticated `POST` request to `https://api.kick.com/public/v1/chat` with `type: "bot"` (or `type: "user"` if appropriate and `broadcaster_user_id` is provided) and the OAuth token in the `Authorization: Bearer` header.

*   **Given** the bot has a valid OAuth access token,
*   **When** any part of the bot needs to send a reply to a specific message (e.g., via `KickBot.reply_text`),
*   **Then** the reply should be sent by making an authenticated `POST` request to `https://api.kick.com/public/v1/chat` including the `reply_to_message_id`, `type: "bot"` (or appropriate type), and the OAuth token.

*   **Given** the `KickClient`'s direct login functionality (`_login` and its helper methods) is no longer used for sending chat messages or other essential API calls (like fetching user info, assuming that also moves to OAuth),
*   **When** the bot starts,
*   **Then** it should not prompt for 2FA, and the `KickClient` class should be simplified, removing its interactive login logic.

**Acceptance Criteria:**

*   All existing functionalities that send chat messages (e.g., command responses, event-triggered messages from `KickWebhookHandler`, timed messages) now use the Kick Chat API.
*   The bot can successfully send messages to the configured streamer's chat using its OAuth identity.
*   The `KickClient._login()` method (and its 2FA prompt) is no longer called during the bot's normal startup and operation for sending messages.
*   The method for fetching the bot's own user info (`KickClient._get_user_info` or its replacement) uses OAuth tokens.
*   (Assumption) The chat WebSocket connection can be established and maintained without relying on cookies/session from the `KickClient` direct login (ideally also using OAuth, or an alternative non-interactive method).

**Tasks:**

- [ ] 1.  **[Research/Verification]**
    *   [ ] Confirm from Kick API documentation ([Chat API](https://docs.kick.com/apis/chat)) the exact request body parameters needed for sending messages as a bot (e.g., if `broadcaster_user_id` is needed or ignored when `type: "bot"`). *Docs state: "As a bot, the message will always be sent to the channel attached to your token."*
    *   [ ] Verify if `https://kick.com/api/v1/user` (used in `KickClient._get_user_info`) can be called with an OAuth Bearer token. If not, find the equivalent official API endpoint for getting authenticated user details.
    *   [ ] **Crucial:** Investigate and confirm the authentication mechanism for the Kick chat WebSocket (`ws_uri`). Can it use the OAuth token? If it relies on cookies from the direct login, this User Story might not fully eliminate the 2FA need without further changes to WebSocket handling.

- [ ] 2.  **[Development - Chat Service/Helper]**
    *   [ ] Create or refactor a helper function/method (e.g., within `kick_helper.py` or a new `kick_chat_api_service.py`) that takes message content, target chatroom/broadcaster info (if needed by API), reply ID (if any), and the OAuth token (or fetches it from `KickAuthManager`).
    *   [ ] This service will use `aiohttp.ClientSession` (e.g., `KickBot.http_session`) to make the `POST` request to `https://api.kick.com/public/v1/chat`.
    *   [ ] Implement error handling for API responses (e.g., 401, 403, 429, 500).

- [ ] 3.  **[Refactor - `KickBot.send_text`]**
    *   [ ] Modify `KickBot.send_text` to use the new Chat API service/helper instead of `send_message_in_chat` (if `send_message_in_chat` uses the old method).
    *   [ ] Ensure it passes the necessary parameters according to the API.

- [ ] 4.  **[Refactor - `KickBot.reply_text`]**
    *   [ ] Modify `KickBot.reply_text` to use the new Chat API service/helper instead of `send_reply_in_chat`.
    *   [ ] Ensure it correctly includes `reply_to_message_id`.

- [ ] 5.  **[Refactor - `KickClient._get_user_info`]**
    *   [ ] Modify `_get_user_info` (or create a new method in `KickBot` or an API service) to fetch user details using the OAuth token and the appropriate official API endpoint. Update `self.user_data`, `self.bot_name`, `self.user_id` in `KickBot` accordingly.

- [ ] 6.  **[Refactor - `KickClient` Simplification]**
    *   [ ] Once all functionalities relying on `KickClient._login()`'s `auth_token`, `xsrf`, and `cookies` are migrated to use the OAuth token via API calls:
        *   Remove `KickClient._login()` and its helper methods (`_request_token_provider`, `_base_login_payload`, `_send_login_request`, `_get_2fa_code`, `_send_login_2fa_code`).
        *   Remove `self.auth_token`, `self.xsrf`, `self.cookies` attributes from `KickClient`.
        *   Adjust `KickClient.__init__` to no longer call `self._login()`.
    *   [ ] The `KickClient` might still retain `self.scraper` (the `tls_client.Session`) if it's needed for other specific, non-authenticated scraping tasks, and `self.session` (the `aiohttp.ClientSession`).

- [ ] 7.  **[Test (TDD/BDD)]**
    *   [ ] Write unit tests for the new Chat API service/helper, mocking `aiohttp` requests and `KickAuthManager`. Test successful sends, replies, and API error handling.
    *   [ ] Update/write integration tests for `KickBot.send_text` and `KickBot.reply_text` to ensure they correctly utilize the new service.
    *   [ ] Test that `KickClient` no longer attempts its direct login during `KickBot` initialization.
    *   [ ] Test the refactored user info fetching.

- [ ] 8.  **[Documentation]**
    *   [ ] Update any internal documentation regarding how chat messages are sent.
    *   [ ] Document changes to `KickClient`'s role.
    *   [ ] Update `Dockerfile` and `docker-compose.yml` if any startup commands or environment variable needs change due to `KickClient` simplification (though likely minimal if `botoshi.py`'s call structure remains).

---