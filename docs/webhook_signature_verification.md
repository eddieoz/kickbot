# Kick Webhook Signature Verification

This document explains how Sr_Botoshi implements signature verification for webhooks from Kick.com, ensuring that webhook events are authentic and have not been tampered with.

## Overview

Webhook signature verification adds an important security layer to our webhook processing. When Kick sends a webhook to Sr_Botoshi, it includes a signature in the `X-Kick-Signature` header. This signature is created by signing the webhook payload with Kick's private key. Sr_Botoshi verifies this signature using Kick's public key, which is available from their API.

## Implementation

The signature verification is implemented through two main components:

1. **KickSignatureVerifier**: A class dedicated to handling signature verification
2. **KickWebhookHandler**: Enhanced to use the signature verifier when enabled

### How It Works

1. Kick signs each webhook payload with their private key and includes the signature in the `X-Kick-Signature` header
2. When Sr_Botoshi receives a webhook, it:
   - Retrieves Kick's public key from `https://api.kick.com/public/v1/public-key` (cached after first fetch)
   - Decodes the base64-encoded signature from the `X-Kick-Signature` header
   - Verifies the signature against the raw payload data using RSA with PKCS1v15 padding and SHA-256 hashing
3. If verification succeeds, the webhook is processed; otherwise, it's rejected

### Technical Details

- **Public Key Endpoint**: `https://api.kick.com/public/v1/public-key`
- **Signature Algorithm**: RSA with PKCS1v15 padding and SHA-256 hashing
- **Signature Format**: Base64-encoded
- **Required Header**: `X-Kick-Signature`

## Usage

The signature verification is optional and can be enabled when creating a `KickWebhookHandler` instance:

```python
from kickbot import KickWebhookHandler, KickSignatureVerifier

# Create a signature verifier
verifier = KickSignatureVerifier()

# Create a webhook handler with signature verification enabled
handler = KickWebhookHandler(
    webhook_path="/kick/webhooks",
    port=8000,
    signature_verification=True  # Enable signature verification
)

# Assign the verifier to the handler
handler.signature_verifier = verifier
```

## Response Codes

When signature verification is enabled, the webhook handler will respond with:

- **200 OK**: Webhook accepted and processed
- **400 Bad Request**: Missing signature header
- **401 Unauthorized**: Invalid signature
- **500 Internal Server Error**: Server error during processing

## Security Considerations

- The signature verification process protects against:
  - Forged webhooks from unauthorized sources
  - Tampered webhook content
  - Replay attacks (assuming Kick includes timestamps in their payloads)

- The `cryptography` library is used for secure cryptographic operations
- The public key is cached after the first fetch to improve performance

## Testing

The signature verification functionality is thoroughly tested using unittest. The tests include:

- Fetching the public key from Kick's API
- Verifying valid and invalid signatures
- Testing webhook handling with valid signatures, invalid signatures, and missing signatures

## Dependencies

This feature requires the `cryptography` package, which has been added to the project's requirements.txt file.

```
cryptography>=44.0.0
```

## Future Improvements

Potential future improvements to the signature verification include:

- Adding a time-based cache expiration for the public key
- Implementing a retry mechanism for public key fetching in case of temporary failures
- Adding support for webhook payload validation against a JSON schema 