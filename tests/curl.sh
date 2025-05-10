#!/bin/sh
    
curl -X POST \
        -H "Content-Type: application/json" \
        -H "Kick-Event-Type: chat.message.sent" \
        -d '{"id":"curl_test_bomdia_001","broadcaster":{"user_id":1171684,"username":"eddieoz","channel_slug":"eddieoz", "is_anonymous": false, "is_verified": true},"sender":{"user_id":12345,"username":"curl_user","channel_slug":"curl_user", "identity":{"username_color":"#FF0000", "badges":[]}, "is_anonymous": false, "is_verified": false},"content":"bom dia","created_at":"2024-05-10T17:00:00Z"}' \
        https://webhook.botoshi.sats4.life/

curl -X POST \
        -H "Content-Type: application/json" \
        -H "Kick-Event-Type: chat.message.sent" \
        -d '{"id":"curl_test_sons_001","broadcaster":{"user_id":1171684,"username":"eddieoz","channel_slug":"eddieoz", "is_anonymous": false, "is_verified": true},"sender":{"user_id":12345,"username":"curl_user","channel_slug":"curl_user", "identity":{"username_color":"#FF0000", "badges":[]}, "is_anonymous": false, "is_verified": false},"content":"!sons testarg","created_at":"2024-05-10T17:01:00Z"}' \
        https://webhook.botoshi.sats4.life/

curl -X POST \
     -H "Content-Type: application/json" \
     -H "Kick-Event-Type: chat.message.sent" \
     -d '{"id":"curl_test_bomdia_007","broadcaster":{"user_id":1171684,"username":"eddieoz","channel_slug":"eddieoz", "is_anonymous": false, "is_verified": true},"sender":{"user_id":12345,"username":"curl_user","channel_slug":"curl_user", "identity":{"username_color":"#FF0000", "badges":[]}, "is_anonymous": false, "is_verified": false},"content":"bom dia","created_at":"2024-05-10T18:00:00Z"}' \
     https://webhook.botoshi.sats4.life/