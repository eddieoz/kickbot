#!/bin/bash

# Test script for webhook validation with various error cases
# Usage: ./test_webhook_all_cases.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

WEBHOOK_URL="https://webhook.botoshi.sats4.life/"

echo -e "${YELLOW}Starting comprehensive webhook tests...${NC}"

# Test 1: Normal message (baseline)
echo -e "\n${GREEN}Test 1: Normal message (should work)${NC}"
curl -s -X POST \
     -H "Content-Type: application/json" \
     -H "Kick-Event-Type: chat.message.sent" \
     -d '{"id":"test_normal_msg","broadcaster":{"user_id":1171684,"username":"eddieoz","channel_slug":"eddieoz"},"sender":{"user_id":12345,"username":"curl_user","channel_slug":"curl_user","identity":{"username_color":"#FF0000","badges":[]}},"content":"normal test message","created_at":"2024-05-10T17:00:00Z"}' \
     $WEBHOOK_URL
echo ""

sleep 2

# Test 2: Missing username
echo -e "\n${YELLOW}Test 2: Missing username${NC}"
curl -s -X POST \
     -H "Content-Type: application/json" \
     -H "Kick-Event-Type: chat.message.sent" \
     -d '{"id":"test_missing_username","broadcaster":{"user_id":1171684,"username":"eddieoz"},"sender":{"user_id":12345,"channel_slug":"curl_user","identity":{"username_color":"#FF0000"}},"content":"missing username test","created_at":"2024-05-10T17:00:00Z"}' \
     $WEBHOOK_URL
echo ""

sleep 2

# Test 3: Missing user_id
echo -e "\n${YELLOW}Test 3: Missing user_id${NC}"
curl -s -X POST \
     -H "Content-Type: application/json" \
     -H "Kick-Event-Type: chat.message.sent" \
     -d '{"id":"test_missing_userid","broadcaster":{"user_id":1171684,"username":"eddieoz"},"sender":{"username":"curl_user","channel_slug":"curl_user","identity":{"username_color":"#FF0000"}},"content":"missing user_id test","created_at":"2024-05-10T17:00:00Z"}' \
     $WEBHOOK_URL
echo ""

sleep 2

# Test 4: Missing sender
echo -e "\n${YELLOW}Test 4: Missing sender completely${NC}"
curl -s -X POST \
     -H "Content-Type: application/json" \
     -H "Kick-Event-Type: chat.message.sent" \
     -d '{"id":"test_missing_sender","broadcaster":{"user_id":1171684,"username":"eddieoz"},"content":"missing sender test","created_at":"2024-05-10T17:00:00Z"}' \
     $WEBHOOK_URL
echo ""

sleep 2

# Test 5: Null sender
echo -e "\n${YELLOW}Test 5: Null sender${NC}"
curl -s -X POST \
     -H "Content-Type: application/json" \
     -H "Kick-Event-Type: chat.message.sent" \
     -d '{"id":"test_null_sender","broadcaster":{"user_id":1171684,"username":"eddieoz"},"sender":null,"content":"null sender test","created_at":"2024-05-10T17:00:00Z"}' \
     $WEBHOOK_URL
echo ""

echo -e "\n${GREEN}All tests complete!${NC}" 