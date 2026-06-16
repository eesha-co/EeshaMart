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

100% AI-powered shopping assistant for EeshaMart Nigeria. Uses dynamic function
calling (like ChatGPT/Gemini/Grok) — no hardcoded intents, no pattern matching.
Powered by Qwen2.5-3B-Instruct (chat) + Salesforce BLIP (vision).

## Features
- Natural language product search
- Smart cart management (add / remove / update / clear / view / checkout)
- Intent classification via AI dynamic function calling
- Real conversation memory (last 10 turns)
- Image understanding — user sends a product photo, AI searches by what it sees

## Environment Variables

All configuration is loaded from environment variables. Copy `.env.example`
to `.env` for local development, or set them as **Secrets** in the Hugging Face
Space settings (Settings → Repository secrets).

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | ✅ | Supabase project URL (e.g. `https://xxx.supabase.co`) |
| `SUPABASE_KEY` | ✅ | Supabase anon key (used for `apikey` header) |
| `CHAT_MODEL_ID` | ❌ | Hugging Face chat model ID. Default: `Qwen/Qwen2.5-3B-Instruct` |
| `VISION_MODEL_ID` | ❌ | Hugging Face vision model ID. Default: `Salesforce/blip-image-captioning-base` |
| `HF_TOKEN` | ❌ | Hugging Face token — only needed for gated/private models |
| `PORT` | ❌ | HTTP port. Default: `7860` (HF Spaces expects 7860) |
| `TORCH_DTYPE` | ❌ | `float32` or `float16`. Default: `float32` |
| `MAX_NEW_TOKENS` | ❌ | Max tokens to generate. Default: `512` |
| `MAX_INPUT_TOKENS` | ❌ | Max tokens for prompt. Default: `3072` |

## Usage

Send POST requests to `/api/chat` with:

```json
{
  "message": "Show me phones under 50000",
  "context": {
    "lastShownProducts": [],
    "cartItems": [],
    "conversationHistory": [],
    "isLoggedIn": false
  }
}
```

Response:

```json
{
  "success": true,
  "response": "Here are some phones under N50,000...",
  "products": [{ "id": "...", "name": "...", "price": 45000, ... }],
  "action": null,
  "image_description": null
}
```

## Function Calling

The AI dynamically decides which functions to call. Supported functions:

- `search_products(query, max_price?)`
- `add_to_cart(product_number)`
- `remove_from_cart(product_number)`
- `update_cart(cart_item_number, new_quantity)`
- `clear_cart()`
- `view_cart()`
- `checkout()`

## Endpoints

- `GET /` — service info
- `GET /api/health` — health check
- `POST /api/chat` — main chat endpoint
