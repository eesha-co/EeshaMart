---
title: EeshaMart AI - Eesha
emoji: 🛒
colorFrom: yellow
colorTo: red
sdk: docker
pinned: false
license: apache-2.0
short_description: AI Shopping Assistant for EeshaMart Nigeria
---

# EeshaMart AI Shopping Assistant

100% AI-powered shopping assistant for EeshaMart Nigeria. No pattern matching - all natural language understanding powered by SmolLM-135M.

## Features
- Natural language product search
- Smart cart management
- Intent classification via AI
- Context-aware responses

## Usage
Send POST requests to `/api/chat` with:
```json
{
  "message": "Show me phones under 50000",
  "context": {
    "lastShownProducts": [],
    "cartItems": []
  }
}
```

## Intents Supported
- `search` - Find products
- `add_to_cart` - Add items to cart
- `view_cart` - See cart contents (NOT checkout)
- `checkout` - Proceed to payment
- `chat` - General conversation
