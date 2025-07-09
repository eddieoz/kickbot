# Webhooks & Signature Verification

Sr_Botoshi now supports receiving webhooks from Kick.com via the official API, with optional signature verification for enhanced security.

## Table of Contents

- [Overview](#overview)
- [Setting Up Webhooks](#setting-up-webhooks)
- [Event Handling with Pydantic Models](#event-handling-with-pydantic-models)
  - [Supported Event Types and Models](#supported-event-types-and-models)
  - [Accessing Event Data](#accessing-event-data)
  - [Adding New Event Handlers](#adding-new-event-handlers)
- [Signature Verification](#signature-verification)
- [Example Usage (Conceptual)](#example-usage-conceptual)
- [Troubleshooting](#troubleshooting)
- [Operating the New Webhook Event System (Phased Rollout & Troubleshooting)](#operating-the-new-webhook-event-system-phased-rollout-and-troubleshooting)

## Overview

Webhooks provide a way for Kick.com to notify Sr_Botoshi in real-time about various events that occur in your stream. Sr_Botoshi uses Pydantic models for robust parsing and type-safe access to event data.

## Setting Up Webhooks

To use webhooks with Sr_Botoshi:

1.  Ensure the `KickWebhookHandler` is integrated into the bot (typically managed by the `KickBot` class).
2.  Make your webhook endpoint publicly accessible (using ngrok, Cloudflare Tunnel, or a public server). The default path is `/kick/events`.
3.  Register your public webhook URL with Kick.com for the desired events via their API (this requires OAuth authentication with appropriate scopes like `events:subscribe`). Refer to `KickEventManager` for how Sr_Botoshi manages these subscriptions.

## Event Handling with Pydantic Models

Sr_Botoshi uses Pydantic models defined in `kickbot/event_models.py` to parse incoming webhook payloads. This provides strong data validation and convenient, type-hinted access to event attributes.

### Supported Event Types and Models

Currently, Sr_Botoshi has built-in parsing and handler stubs for the following Kick events:

-   **`channel.followed`**: Parsed into `FollowEvent`.
    -   Data available via `event.data` (an instance of `FollowEventData`), including `follower` info and `followed_at` timestamp.
-   **`channel.subscribed`**: Parsed into `SubscriptionEvent`.
    -   Data available via `event.data` (an instance of `SubscriptionEventData`), including `subscriber` info, `subscription_tier`, `is_gift` status, `months_subscribed`, and `subscribed_at` timestamp.
-   **`channel.subscription.gifted`**: Parsed into `GiftedSubscriptionEvent`.
    -   Data available via `event.data` (an instance of `GiftedSubscriptionEventData`), including `gifter` info (optional), a list of `recipients`, `subscription_tier`, and `gifted_at` timestamp.

Each top-level event model (e.g., `FollowEvent`) inherits from `KickEventBase` and includes common fields like:
-   `id`: The unique ID of the event from Kick.
-   `event`: The event type string (e.g., "channel.followed").
-   `channel_id`: The ID of the channel the event pertains to.
-   `created_at`: Timestamp when Kick created the event.
-   `data`: An object containing the event-specific Pydantic model (e.g., `FollowEventData`).

For the detailed structure of these models, please refer to the source file: `kickbot/event_models.py`.

### Accessing Event Data

When an event is received, it's parsed into the corresponding Pydantic model. Handler methods in `KickWebhookHandler` (e.g., `handle_follow_event`) receive this parsed model as an argument.

Example of a handler method signature and accessing data:

```python
# (Inside KickWebhookHandler class)
from kickbot.event_models import SubscriptionEvent # Or other specific event types
import logging
logger = logging.getLogger(__name__)

async def handle_custom_subscription_logic(self, event: SubscriptionEvent):
    subscriber_name = event.data.subscriber.username
    tier = event.data.subscription_tier
    logger.info(f"New subscription from {subscriber_name} at {tier}!")
    # Your custom logic here
```

The built-in handlers in `KickWebhookHandler` already log event details. You can modify these directly or use them as a template for more complex actions.

### Adding New Event Handlers

To add support for a new Kick event type not yet covered:

1.  **Define Pydantic Models:**
    *   In `kickbot/event_models.py`, create a new data model for the `data` part of the event (e.g., `NewEventData(BaseEventData): ...`).
    *   Create the main event model (e.g., `NewEvent(KickEventBase): event: Literal["kick.new.event.name"]; data: NewEventData`).
    *   Add your new main event model (e.g., `NewEvent`) to the `AnyKickEvent = Union[...]` type alias in `kickbot/event_models.py`.

2.  **Create a Handler Method:**
    *   In `kickbot/kick_webhook_handler.py`, add a new asynchronous method to handle the parsed event, for example:
        ```python
        from kickbot.event_models import NewEvent # Your new event model

        async def handle_newly_added_event(self, event: NewEvent):
            logger.info(f"Received new event type {event.event} for channel {event.channel_id}")
            # Add your custom processing logic here
        ```

3.  **Register the Handler:**
    *   In the `__init__` method of `KickWebhookHandler` (in `kickbot/kick_webhook_handler.py`), register your new handler method:
        ```python
        self.register_event_handler("kick.new.event.name", self.handle_newly_added_event)
        ```

This will enable the `KickWebhookHandler` to parse the new event type using your defined models and dispatch it to your custom handler method.

### Configuring Specific Event Actions

Beyond just parsing and logging, Sr_Botoshi allows for specific actions to be configured for certain events. These configurations are typically found in your `settings.json` file.

**Master Control for New Webhook Actions:**

All actions triggered by the new webhook event system (follow, new subscription, gifted subscription, renewal) are globally controlled by the `EnableNewWebhookEventSystem` feature flag in `settings.json` under the `FeatureFlags` object:

```json
{
  // ... other settings ...
  "FeatureFlags": {
    "EnableNewWebhookEventSystem": true, // Master switch for all new webhook actions
    "DisableLegacyGiftEventHandling": false 
    // ... other flags ...
  },
  // ... other settings ...
}
```

-   **`EnableNewWebhookEventSystem`** (boolean):
    -   If `true`, the new webhook-based event handlers in `KickWebhookHandler` will process incoming events and attempt to perform actions based on their specific configurations (detailed below).
    -   If `false`, all event-specific actions described in the following sections (chat messages, point logging, etc.) for the new webhook system will be skipped, regardless of their individual settings. The webhook server will still receive events if `KickWebhookEnabled` is true, but the handlers will not perform their primary actions.
    -   Defaults to `true` if the key or `FeatureFlags` object is missing.

-   **`DisableLegacyGiftEventHandling`** (boolean):
    -   This flag is intended to disable any old, chat-based or WebSocket-based logic for handling gifted subscriptions if such logic were active and conflicting with the new webhook system.
    -   Current analysis indicates no active legacy system for processing gifted subscription events that would be gated by this flag. The old WebSocket event `gifted_subscriptions` had a `pass` statement, and no specific chat parsing for gifts has been identified.
    -   This flag remains for future-proofing or if an overlooked legacy path is discovered. It currently has no direct effect on disabling known legacy code.
    -   Defaults to `false` if the key is missing.

**Individual Event Action Configurations:**

The following sections describe configurations for actions related to specific events. **These actions are only performed if `EnableNewWebhookEventSystem` is `true`.**

**Example: Follow Event Actions**

When a `channel.followed` event is received, you can configure Sr_Botoshi to automatically send a "thank you" message in the chat.

This is controlled by the `HandleFollowEventActions` object in `settings.json`:

```json
{
  // ... other settings ...
  "FeatureFlags": {
    "EnableNewWebhookEventSystem": true,
    "DisableLegacyGiftEventHandling": false
  },
  "HandleFollowEventActions": {
    "SendChatMessage": true
  }
  // ... other settings ...
}
```

-   **`HandleFollowEventActions`**: This object contains settings specific to actions for follow events.
    -   **`SendChatMessage`** (boolean): 
        -   If `true` (and `FeatureFlags.EnableNewWebhookEventSystem` is also `true`), the bot will attempt to send a chat message like "Thanks for following, {username}!" when a new follow event is processed.
        -   If `false`, no chat message will be sent for new follows, even if `EnableNewWebhookEventSystem` is `true`.
        -   If this setting or the `HandleFollowEventActions` object is entirely missing from `settings.json`, `SendChatMessage` defaults to `true`.

To disable the follow thank you message (while `EnableNewWebhookEventSystem` is true):
```json
{
  "HandleFollowEventActions": {
    "SendChatMessage": false
  }
}
```

**Example: New Subscription Event Actions**

When a `channel.subscription.new` event (a new, non-gifted subscription) is received, you can configure Sr_Botoshi to perform specific actions like sending a thank you message and (in the future) awarding points.

This is controlled by the `HandleSubscriptionEventActions` object in `settings.json`. **These actions only occur if `FeatureFlags.EnableNewWebhookEventSystem` is `true`.**

```json
{
  // ... other settings ...
  "FeatureFlags": {
    "EnableNewWebhookEventSystem": true,
    "DisableLegacyGiftEventHandling": false
  },
  "HandleSubscriptionEventActions": {
    "SendChatMessage": true,
    "AwardPoints": true,
    "PointsToAward": 100
  }
  // ... other settings ...
}
```

-   **`HandleSubscriptionEventActions`**: This object contains settings specific to actions for new, non-gifted subscription events.
    -   **`SendChatMessage`** (boolean):
        -   If `true` (and `FeatureFlags.EnableNewWebhookEventSystem` is `true`), the bot will attempt to send a chat message like "Welcome to the sub club, {username}! Thanks for subscribing." when a new subscription event is processed.
        -   If `false`, no chat message will be sent for new subscriptions.
        -   Defaults to `true` if the key is missing or the `HandleSubscriptionEventActions` object is not present.
    -   **`AwardPoints`** (boolean):
        -   If `true` (and `FeatureFlags.EnableNewWebhookEventSystem` is `true`), the bot will attempt to award points to the subscriber. (Currently, this logs a placeholder message; actual point awarding is a future implementation.)
        -   If `false`, no points will be awarded (or logged for awarding).
        -   Defaults to `true` if the key is missing.

To disable chat messages for new subscriptions but keep point awarding (once fully implemented), assuming `EnableNewWebhookEventSystem` is true:
```json
{
  "HandleSubscriptionEventActions": {
    "SendChatMessage": false,
    "AwardPoints": true,
    "PointsToAward": 150
  }
}
```

**Example: Gifted Subscription Event Actions**

When a `channel.subscription.gifts` event (gifted subscriptions) is received, Sr_Botoshi can perform several actions. These are controlled by the `HandleGiftedSubscriptionEventActions` object in `settings.json` and **only occur if `FeatureFlags.EnableNewWebhookEventSystem` is `true`.**

```json
{
  // ... other settings ...
  "FeatureFlags": {
    "EnableNewWebhookEventSystem": true,
    "DisableLegacyGiftEventHandling": false
  },
  "HandleGiftedSubscriptionEventActions": {
    "SendThankYouChatMessage": true,
    "AwardPointsToGifter": true,
    "PointsToGifterPerSub": 50,
    "AwardPointsToRecipients": true,
    "PointsToRecipient": 25
  }
  // ... other settings ...
}
```

-   **`HandleGiftedSubscriptionEventActions`**: This object contains settings specific to actions for gifted subscription events.
    -   **`SendThankYouChatMessage`** (boolean):
        -   If `true` (and `FeatureFlags.EnableNewWebhookEventSystem` is `true`), the bot will send a chat message thanking the gifter and acknowledging the recipients.
        -   Defaults to `true`.
    -   **`AwardPointsToGifter`** (boolean):
        -   If `true` (and `EnableNewWebhookEventSystem` is `true`, and gifter is not Anonymous), the bot will award points to the gifter.
        -   Defaults to `true`.
    -   **`PointsToGifterPerSub`** (integer):
        -   The number of points awarded to the gifter *for each sub gifted* if `AwardPointsToGifter` is `true`.
        -   Defaults to `50`.
    -   **`AwardPointsToRecipients`** (boolean):
        -   If `true` (and `EnableNewWebhookEventSystem` is `true`), the bot will award points to each recipient of a gifted sub.
        -   Defaults to `true`.
    -   **`PointsToRecipient`** (integer):
        -   The number of points awarded to each recipient if `AwardPointsToRecipients` is `true`.
        -   Defaults to `25`.

**Example: Subscription Renewal Event Actions**

When a `channel.subscription.renewal` event is received, Sr_Botoshi can perform actions like sending a congratulatory message and awarding points for continued support.

This is controlled by the `HandleSubscriptionRenewalEventActions` object in `settings.json` and **only occur if `FeatureFlags.EnableNewWebhookEventSystem` is `true`.**

```json
{
  // ... other settings ...
  "FeatureFlags": {
    "EnableNewWebhookEventSystem": true,
    "DisableLegacyGiftEventHandling": false
  },
  "HandleSubscriptionRenewalEventActions": {
    "SendChatMessage": true,
    "AwardPoints": true,
    "PointsToAward": 120
  }
  // ... other settings ...
}
```

-   **`HandleSubscriptionRenewalEventActions`**: This object contains settings specific to actions for subscription renewal events.
    -   **`SendChatMessage`** (boolean):
        -   If `true` (and `FeatureFlags.EnableNewWebhookEventSystem` is `true`), the bot will send a chat message like "Thanks {username} for renewing your Tier {tier} sub for {months_subscribed} months!".
        -   Defaults to `true`.
    -   **`AwardPoints`** (boolean):
        -   If `true` (and `EnableNewWebhookEventSystem` is `true`), the bot will (currently log) awarding points to the renewing subscriber.
        -   Defaults to `true`.

As more event-specific actions are added, their configurations will be documented here and will typically reside in `settings.json` under similar dedicated objects, all contingent on `EnableNewWebhookEventSystem` being active.

## Operating the New Webhook Event System (Phased Rollout & Troubleshooting)

The new webhook event system is designed for flexibility, allowing you to enable or disable its functionality globally or for specific actions. This is useful for phased rollouts, testing, or troubleshooting.

**Key Configuration File:** `settings.json`

**1. Global Control (Master Switch):**

   - **Flag:** `FeatureFlags.EnableNewWebhookEventSystem` (boolean)
   - **Purpose:** This is the primary switch for the entire new webhook-based event action system.
   - **Behavior:**
     - `true`: The `KickWebhookHandler` will process incoming webhook events (follows, new subscriptions, gifted subscriptions, renewals) and attempt to perform actions based on the specific configurations detailed in the sections above (e.g., sending chat messages, logging point awards).
     - `false`: All event-specific actions performed by the `KickWebhookHandler` will be skipped. The webhook server might still receive events from Kick (if `KickWebhookEnabled` is also true in `settings.json`), but no automated actions like chat messages or point awards will be triggered by the new system.
   - **Default:** `true` (if the flag or `FeatureFlags` object is missing).
   - **Use Cases:**
     - **Full Rollout:** Set to `true` for normal operation.
     - **Temporarily Disable All New Actions:** Set to `false` if you suspect an issue with the new webhook system and want to quickly revert to only legacy behaviors (if any) or stop all webhook-driven actions.
     - **Testing:** Can be toggled to observe behavior with and without the new system active.

**2. Fine-Grained Control (Per-Event, Per-Action):**

   - **Flags:** Located within specific objects like `HandleFollowEventActions`, `HandleSubscriptionEventActions`, `HandleGiftedSubscriptionEventActions`, and `HandleSubscriptionRenewalEventActions`.
   - **Purpose:** These allow you to enable or disable individual actions (e.g., sending a chat message for a new follow, awarding points for a new sub) *while the global `EnableNewWebhookEventSystem` is `true`*.
   - **Behavior:** For an action to occur:
     1. `EnableNewWebhookEventSystem` must be `true`.
     2. The relevant specific action flag (e.g., `HandleFollowEventActions.SendChatMessage`) must also be `true` (or default to `true` if not specified).
   - **Examples:**
     - To stop sending chat messages for new follows but keep other webhook actions active:
       ```json
       "FeatureFlags": {
         "EnableNewWebhookEventSystem": true 
       },
       "HandleFollowEventActions": {
         "SendChatMessage": false 
       }
       ```
     - To disable awarding points for new subscriptions but still send the chat message (assuming `EnableNewWebhookEventSystem` is `true`):
       ```json
       "HandleSubscriptionEventActions": {
         "SendChatMessage": true,
         "AwardPoints": false,
         "PointsToAward": 100 
       }
       ```
   - **Use Cases:**
     - **Phased Feature Introduction:** Enable a new action (e.g., awarding points for renewals) only after thorough testing, while other established actions remain active.
     - **Troubleshooting Specific Actions:** If a particular action (e.g., the thank you message for gifted subs) is causing issues, you can disable just that action without turning off the entire webhook system or other event handlers.

**3. Legacy System Interaction:**

   - **Flag:** `FeatureFlags.DisableLegacyGiftEventHandling` (boolean)
   - **Purpose:** This flag was intended to gate any old system logic for handling gifted subscriptions if it conflicted with the new webhook system.
   - **Current Status:** As detailed earlier, no active conflicting legacy gift processing has been identified in the current codebase. Thus, this flag currently has minimal direct effect. It defaults to `false`.
   - **Recommendation:** Generally, this can be left as `false` unless a specific legacy conflict related to gifts is identified.

**Troubleshooting Steps with Flags:**

1.  **Problem: No webhook actions are occurring.**
    *   Verify `KickWebhookEnabled` is `true` in `settings.json` (this enables the webhook server itself).
    *   Verify `EnableNewWebhookEventSystem` is `true` in `FeatureFlags`.
    *   Check bot logs for errors during webhook handler initialization or event processing.
    *   Ensure the specific action flag (e.g., `HandleFollowEventActions.SendChatMessage`) is `true` or not present (to use its default `true` value).

2.  **Problem: A specific webhook action is not occurring (e.g., no chat message for new subs, but follows work).**
    *   Ensure `EnableNewWebhookEventSystem` is `true`.
    *   Check the relevant `Handle...EventActions` object (e.g., `HandleSubscriptionEventActions`) and ensure the specific action key (e.g., `SendChatMessage`) is `true`.
    *   Review bot logs for errors specific to that event handler.

3.  **Problem: Suspected conflict or undesired behavior from a new webhook action.**
    *   To quickly isolate, set the specific action flag to `false` (e.g., `HandleGiftedSubscriptionEventActions.SendThankYouChatMessage: false`).
    *   If the issue is broader or affects multiple new actions, consider setting `EnableNewWebhookEventSystem` to `false` temporarily while investigating.

By using these flags, you can manage the rollout and operation of the new webhook event system effectively.

## Signature Verification

For enhanced security, Sr_Botoshi supports verifying the signatures of incoming webhooks. This ensures that the webhooks are genuinely from Kick.com and haven't been tampered with.

For detailed documentation on the signature verification process, see [Webhook Signature Verification](webhook_signature_verification.md).

## Example Usage (Conceptual)

This section previously showed manual setup. With the `KickBot` class managing the `KickWebhookHandler`, usage is more about ensuring the bot is configured correctly in `settings.json` (webhook enabled, path, port) and that your Kick application has events subscribed via `KickEventManager`.

The core interaction with event data now happens within the handler methods in `KickWebhookHandler` or custom handlers you might add, which receive parsed Pydantic models as shown in the "Accessing Event Data" section.

```python
# Conceptual: How KickBot might use KickWebhookHandler (simplified)
# Actual setup is within KickBot.run() and _start_webhook_server()

# from .kick_webhook_handler import KickWebhookHandler
# from .kick_event_manager import KickEventManager

# class KickBot:
#     async def run(self):
#         # ... other setup ...
#         if self.config.get("webhook_enabled"):
#             self.webhook_handler = KickWebhookHandler(
#                 webhook_path=self.config.get("webhook_path", "/kick/events"),
#                 port=self.config.get("webhook_port", 8000)
#             )
#             # Server is started in a separate task by _start_webhook_server
#             await self._start_webhook_server()

#         # ... event manager subscribes to events ...
#         if self.event_manager:
#             await self.event_manager.resubscribe_to_configured_events()
```

Focus on implementing logic within the `handle_..._event` methods in `kickbot.kick_webhook_handler.py`.

## Troubleshooting

If you're having issues with webhooks:

1.  **Check that your webhook endpoint is publicly accessible**
    -   Use a tool like ngrok or Cloudflare Tunnel to make your local endpoint accessible.
    -   Ensure your firewall allows incoming connections on the configured port (default 8000).

2.  **Verify Kick API Subscriptions & OAuth Tokens**
    -   Ensure Sr_Botoshi has successfully subscribed to the desired events via `KickEventManager`. Check bot logs for messages from `KickEventManager` regarding subscriptions.
    -   Ensure your OAuth tokens (`kickbot_tokens.json`) are valid and have the required scopes (e.g., `events:subscribe`).
    -   If tokens are invalid, you may need to re-run the authentication flow.

3.  **Inspect Webhook Payloads & Parsing**
    -   Enable `log_events=True` in your `KickWebhookHandler` settings (or if debugging, directly in its instantiation) to see the raw JSON payloads received by Sr_Botoshi. This is logged by `kickbot.kick_webhook_handler` before Pydantic parsing.
    -   If `parse_kick_event_payload` in `kickbot.event_models` fails to parse an event (indicated by warnings like "Could not parse webhook payload into a known event model"), compare the logged raw payload structure with the Pydantic models in `kickbot/event_models.py`. The Pydantic validation error (printed to console/logs by the default `parse_kick_event_payload` if parsing fails) will give clues.
    -   Ensure the `event` type string in the incoming JSON matches one of the `Literal` values in your Pydantic event models.

4.  **Signature Verification Issues**
   - If using signature verification, ensure your internet connection is stable to fetch the public key
   - Check that the `X-Kick-Signature` header is being received correctly
   - Consider temporarily disabling signature verification for testing 