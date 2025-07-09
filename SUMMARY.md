# Sr_Botoshi Kick Integration - Development Summary

## What We've Accomplished

### User Story 1: OAuth Token Management
- Created `kick_auth_manager.py` with:
  - PKCE helper functions for OAuth 2.0 authorization
  - Authorization URL generation
  - Token exchange implementation (authorization code for tokens)
  - Simple file-based token storage (e.g., `kickbot_tokens.json`), loaded on startup
  - Token validation (expiry check) and refresh mechanism
    - If refresh fails critically (e.g., invalid refresh token), tokens are cleared, requiring user re-authorization
  - Comprehensive unit tests for the above functionalities
- Added `scripts/kick_auth_example.py` to demonstrate and facilitate the one-time OAuth authorization flow.
- Updated and finalized `docs/authentication.md` and `docs/tasks.md` to reflect the complete OAuth 2.0 PKCE implementation, including simplified token management for local execution and instructions for initial authorization.

### User Story 2: Webhook Endpoint for Events
- Implemented `kick_webhook_handler.py` with:
  - Async HTTP server using aiohttp
  - Event validation and basic dispatching (initially to raw data handlers)
  - Comprehensive test coverage for basic endpoint functionality.
- Created `scripts/test_webhook.py` for testing with ngrok tunnel.
- Integrated the webhook server into `KickBot`'s lifecycle.

### User Story 3: Subscribe to Kick Events via API
- Created `kickbot/kick_event_manager.py` with `KickEventManager` class for:
  - Listing current event subscriptions.
  - Subscribing to a list of events (e.g., `channel.subscribed`, `channel.subscription.gifted`, `channel.followed`).
  - Unsubscribing from events.
- Integrated `KickEventManager` into `KickBot` for automatic re-subscription on startup and clearing subscriptions on shutdown.
- Added configuration for events to subscribe to in `settings.json`.
- Wrote unit tests for `KickEventManager` and its integration with `KickBot`.

### User Story 4 & EPIC: Event Handling and New System Implementation
- **Event Parsing & Dispatch (User Story 4):**
  - Created `kickbot/event_models.py` with Pydantic models for `channel.followed`, `channel.subscription.new`, `channel.subscription.gifts`, and `channel.subscription.renewal` events, providing robust data validation and type-safe access.
  - Updated `kickbot/kick_webhook_handler.py` to parse incoming JSON webhook payloads into these Pydantic models and dispatch them to specific typed event handlers.
- **New Event System Actions (User Stories 6.1, 6.2, 6.3, 6.4):**
  - Implemented initial actions (e.g., sending chat messages and logging point awards) in `KickWebhookHandler` for:
    - Follow events (`channel.followed`)
    - New subscription events (`channel.subscription.new`)
    - Gifted subscription events (`channel.subscription.gifts`)
    - Subscription renewal events (`channel.subscription.renewal`)
  - These actions are controlled by new configuration settings in `settings.json` (e.g., `HandleFollowEventActions`, `HandleSubscriptionEventActions`, `HandleGiftedSubscriptionEventActions`, `HandleSubscriptionRenewalEventActions`).
  - Ensured `KickBot` instance is passed to `KickWebhookHandler` to facilitate these actions.
- **Parallel Operation & Control (User Story 5):**
  - Implemented a master feature flag `EnableNewWebhookEventSystem` in `settings.json` to globally enable/disable all actions within the new webhook system.
  - Confirmed individual action configurations (e.g., `SendChatMessage`) are respected when the new system is enabled.
  - Investigated legacy system: Found no directly conflicting WebSocket event parsing for follows, new subscriptions, gifted subscriptions, or renewals that would require complex gating. The `DisableLegacyGiftEventHandling` flag remains for future-proofing but has no current active target.
- **Testing & Documentation:**
  - Developed comprehensive unit tests in `tests/test_kick_webhook_handler.py` covering event parsing, dispatch logic, action execution based on configuration flags (for all new event types), and error handling.
  - Updated `docs/webhooks_and_signature_verification.md` to detail Pydantic-based event handling, supported events, instructions for adding new handlers, documentation for all new event action configurations, and operational guidance for the feature flags.
  - Updated `docs/tasks.md` to reflect completion of User Stories 1-5 and 6.1-6.4.

## What's Next

### Immediate Next Steps
1.  **Points System Integration:**
    *   The current implementation for awarding points in the new event handlers logs placeholders. The next major step is to integrate these with an actual points system/database.
    *   This will involve defining how points are stored, retrieved, and updated, and then modifying the `KickWebhookHandler` methods to call these new points system functions.
2.  **Signature Verification:**
    *   Implement and test payload signature verification for webhooks (User Story 2 task) once Kick provides clear documentation and mechanisms for public key retrieval.
3.  **Further Event Support & Actions:**
    *   Investigate and implement support for other potentially useful Kick webhook events as they become available or are prioritized (e.g., cheers, raids, channel updates).
    *   Expand the range of configurable actions for existing and new events based on user needs.

### Longer Term
-   **Refactor Old WebSocket Infrastructure:** As per User Story 5, Task 4, once the new webhook system is fully validated in production and deemed sufficient, evaluate the remaining old WebSocket infrastructure (`_poll` loop in `KickBot`, `MarkovChain.message_handler` for non-event purposes) for potential refactoring or decommissioning of redundant parts. The Markov chain sentence generation is separate and will likely remain.
-   **UI/Dashboard for Configuration:** Consider a more user-friendly way to manage configurations currently in `settings.json`, especially if the number of flags and options grows.
-   **Enhanced Bot Commands:** Expand bot commands that interact with data gathered from new events (e.g., `!top_gifter`, `!last_subscriber`).

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  **Points System Integration:**
    *   The current implementation for awarding points in the new event handlers logs placeholders. The next major step is to integrate these with an actual points system/database.
    *   This will involve defining how points are stored, retrieved, and updated, and then modifying the `KickWebhookHandler` methods to call these new points system functions.
2.  **Signature Verification:**
    *   Implement and test payload signature verification for webhooks (User Story 2 task) once Kick provides clear documentation and mechanisms for public key retrieval.
3.  **Further Event Support & Actions:**
    *   Investigate and implement support for other potentially useful Kick webhook events as they become available or are prioritized (e.g., cheers, raids, channel updates).
    *   Expand the range of configurable actions for existing and new events based on user needs.

### Longer Term
-   **Refactor Old WebSocket Infrastructure:** As per User Story 5, Task 4, once the new webhook system is fully validated in production and deemed sufficient, evaluate the remaining old WebSocket infrastructure (`_poll` loop in `KickBot`, `MarkovChain.message_handler` for non-event purposes) for potential refactoring or decommissioning of redundant parts. The Markov chain sentence generation is separate and will likely remain.
-   **UI/Dashboard for Configuration:** Consider a more user-friendly way to manage configurations currently in `settings.json`, especially if the number of flags and options grows.
-   **Enhanced Bot Commands:** Expand bot commands that interact with data gathered from new events (e.g., `!top_gifter`, `!last_subscriber`).

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  **Points System Integration:**
    *   The current implementation for awarding points in the new event handlers logs placeholders. The next major step is to integrate these with an actual points system/database.
    *   This will involve defining how points are stored, retrieved, and updated, and then modifying the `KickWebhookHandler` methods to call these new points system functions.
2.  **Signature Verification:**
    *   Implement and test payload signature verification for webhooks (User Story 2 task) once Kick provides clear documentation and mechanisms for public key retrieval.
3.  **Further Event Support & Actions:**
    *   Investigate and implement support for other potentially useful Kick webhook events as they become available or are prioritized (e.g., cheers, raids, channel updates).
    *   Expand the range of configurable actions for existing and new events based on user needs.

### Longer Term
-   **Refactor Old WebSocket Infrastructure:** As per User Story 5, Task 4, once the new webhook system is fully validated in production and deemed sufficient, evaluate the remaining old WebSocket infrastructure (`_poll` loop in `KickBot`, `MarkovChain.message_handler` for non-event purposes) for potential refactoring or decommissioning of redundant parts. The Markov chain sentence generation is separate and will likely remain.
-   **UI/Dashboard for Configuration:** Consider a more user-friendly way to manage configurations currently in `settings.json`, especially if the number of flags and options grows.
-   **Enhanced Bot Commands:** Expand bot commands that interact with data gathered from new events (e.g., `!top_gifter`, `!last_subscriber`).

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  **Points System Integration:**
    *   The current implementation for awarding points in the new event handlers logs placeholders. The next major step is to integrate these with an actual points system/database.
    *   This will involve defining how points are stored, retrieved, and updated, and then modifying the `KickWebhookHandler` methods to call these new points system functions.
2.  **Signature Verification:**
    *   Implement and test payload signature verification for webhooks (User Story 2 task) once Kick provides clear documentation and mechanisms for public key retrieval.
3.  **Further Event Support & Actions:**
    *   Investigate and implement support for other potentially useful Kick webhook events as they become available or are prioritized (e.g., cheers, raids, channel updates).
    *   Expand the range of configurable actions for existing and new events based on user needs.

### Longer Term
-   **Refactor Old WebSocket Infrastructure:** As per User Story 5, Task 4, once the new webhook system is fully validated in production and deemed sufficient, evaluate the remaining old WebSocket infrastructure (`_poll` loop in `KickBot`, `MarkovChain.message_handler` for non-event purposes) for potential refactoring or decommissioning of redundant parts. The Markov chain sentence generation is separate and will likely remain.
-   **UI/Dashboard for Configuration:** Consider a more user-friendly way to manage configurations currently in `settings.json`, especially if the number of flags and options grows.
-   **Enhanced Bot Commands:** Expand bot commands that interact with data gathered from new events (e.g., `!top_gifter`, `!last_subscriber`).

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers, controlled by feature flags. (Note: Initial actions for follow, new subscription, and gifted subscription events, including chat messages and point logging, are now implemented with configurable flags. Full points system integration is a key next step for these actions.)
- Once the new webhook system is validated for all targeted events, plan and execute the decommissioning of the old WebSocket/chat-scraping logic for those events.

## Technical Improvements

- Fixed test suite to ensure all tests run cleanly individually and together
- Created a custom test runner script to run tests in isolation
- Added shell script for easy test execution
- Updated documentation with test instructions

## Running the Tests

To run the token management tests (including storage and refresh):
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
# Assuming tests are run via a script like tests/run_tests.py or directly:
python -m unittest tests.test_kick_auth_simple.py
```

To run the webhook handler tests:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m unittest tests.test_kick_webhook_handler
```

## Testing the OAuth Flow

To test the OAuth flow with token storage and refresh:
```bash
conda activate kickbot
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/kick_auth_example.py --authorize
```

This will start an authorization flow that saves tokens to a file. After authorization, you can test API requests:
```bash
python scripts/kick_auth_example.py --test-api
```

## Testing the Webhook Handler

To test the webhook handler with ngrok:
```bash
pip install pyngrok  # if not already installed
python scripts/test_webhook.py
```

This will start a local server and expose it via ngrok, providing a public URL that can be registered with Kick for webhook events. 

## What's Next

### Immediate Next Steps
1.  Begin User Story 5 (Parallel Operation and Phased Rollout), focusing on:
    *   Introducing feature flags in the configuration to control whether the new webhook-based event system's actions are enabled or if the old system's specific event parsing (e.g., for gifts via chat) is disabled.
    *   Reviewing actions taken by current webhook event handlers (currently logging) and planning how to integrate actions like sending chat messages or updating bot state, guarded by these feature flags.
    *   Conducting testing with both systems potentially active to ensure smooth transition.
2.  Address payload signature verification for webhooks (User Story 2 task) if/when Kick provides clear documentation.

### Longer Term
- Implement actual bot actions (beyond logging and chat messages) in the new Pydantic-based event handlers,