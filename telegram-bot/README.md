# EeshaMart Telegram Bot

AI Shopping Assistant for Telegram - 100% FREE!

## Bot Link
https://t.me/eeshamart_bot

## Features
- 🛒 Product Search
- 🛍️ Add to Cart
- 📦 View Cart
- 💳 Checkout
- 📸 Photo Recognition
- 💬 Conversation Memory
- 🤖 AI-Powered Responses

## Deploy on Render.com (FREE)

### Step 1: Create Web Service
1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repo: `eesha000009-dev/Eesha-shop-Buying-and-Selling`
4. Set **Root Directory**: `telegram-bot`

### Step 2: Configure
| Setting | Value |
|---------|-------|
| Name | `eeshamart-telegram-bot` |
| Environment | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python app.py` |

### Step 3: Add Environment Variables
| Variable | Value |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | `8142562507:AAG-_UExIh18e6mz-0URKmv67-CQOk_cuA4` |
| `SUPABASE_URL` | `https://tcwdbokruvlizkxcpkzj.supabase.co` |
| `SUPABASE_KEY` | (your Supabase key) |

### Step 4: Deploy & Set Webhook
1. Click "Create Web Service"
2. Wait for deployment (2-3 min)
3. Visit: `https://eeshamart-telegram-bot.onrender.com/setwebhook`
4. Done! Bot is live! 🎉

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Health check |
| `/webhook/telegram` | POST | Telegram webhook |
| `/setwebhook` | GET | Set Telegram webhook |
| `/getme` | GET | Get bot info |
| `/getwebhookinfo` | GET | Get webhook info |
| `/api/link` | POST | Link account from website |

## License
MIT - FREE & Open Source
