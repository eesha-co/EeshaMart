"""
EeshaMart Telegram Bot - Full AI Chat + Vision
Natural conversation on ANY topic + Smart shopping intent understanding
Powered by Qwen2.5-3B via Hugging Face backend

Bot: https://t.me/eeshamart_bot
"""

import httpx
import os
import json
import logging
from typing import Dict, List, Optional
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EeshaMart Telegram Bot - Full AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8142562507:AAG-_UExIh18e6mz-0URKmv67-CQOk_cuA4")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tcwdbokruvlizkxcpkzj.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg")
AI_BACKEND_URL = os.environ.get("AI_BACKEND_URL", "https://fuhaddesmond-eeshamart-ai.hf.space/api/chat")

logger.info("🤖 EeshaMart Telegram Bot Starting...")

# Storage - NOW stores access_token for authenticated requests
linked_accounts: Dict[int, dict] = {}  # {chat_id: {user_id, email, access_token, ...}}
auth_sessions: Dict[int, dict] = {}
user_sessions: Dict[int, dict] = {}

AUTH_STATE_EMAIL = "waiting_email"
AUTH_STATE_PASSWORD = "waiting_password"


# ==================== TELEGRAM API ====================

async def send_typing_action(chat_id: int):
    """Send 'typing' action to show user the bot is thinking"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    payload = {"chat_id": chat_id, "action": "typing"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        logger.error(f"Typing action error: {e}")


async def send_thinking_message(chat_id: int) -> Optional[int]:
    """Send a 'thinking...' message visible in chat, returns message_id for deletion"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": "🤔 _Thinking..._", "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return response.json().get("result", {}).get("message_id")
    except Exception as e:
        logger.error(f"Thinking message error: {e}")
    return None


async def delete_message(chat_id: int, message_id: int):
    """Delete a message from chat"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        logger.error(f"Delete message error: {e}")


async def send_telegram(chat_id: int, text: str):
    """Send message via Telegram API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    logger.info(f"📤 Sending to {chat_id}: {text[:50]}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            return response.json()
    except Exception as e:
        logger.error(f"❌ Send error: {e}")
        return {"ok": False, "error": str(e)}


async def download_telegram_photo(file_id: str) -> Optional[bytes]:
    """Download photo from Telegram"""
    try:
        file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(file_url)
            if response.status_code == 200:
                file_path = response.json().get("result", {}).get("file_path")
                if file_path:
                    photo_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                    photo_response = await client.get(photo_url)
                    if photo_response.status_code == 200:
                        return photo_response.content
    except Exception as e:
        logger.error(f"❌ Photo download error: {e}")
    return None


# ==================== SUPABASE WITH AUTH ====================

async def verify_supabase_auth(email: str, password: str) -> Optional[dict]:
    """Verify user credentials with Supabase Auth"""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json={"email": email, "password": password})
            if response.status_code == 200:
                data = response.json()
                return {
                    "user_id": data.get("user", {}).get("id"),
                    "email": data.get("user", {}).get("email"),
                    "access_token": data.get("access_token")
                }
    except Exception as e:
        logger.error(f"Auth error: {e}")
    return None


async def get_cart(user_id: str, access_token: str) -> List[dict]:
    """Get user's cart from Supabase using authenticated request"""
    url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}&select=id,quantity,product_id,products(id,name,price)"
    # IMPORTANT: Use Authorization header with user's access token
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token}"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            logger.info(f"🛒 Get cart response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"🛒 Cart items: {len(data) if data else 0}")
                return data
            else:
                logger.error(f"Cart error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Cart error: {e}")
    return []


async def add_to_cart_db(user_id: str, product_id: int, access_token: str, quantity: int = 1) -> bool:
    """Add product to cart in Supabase using authenticated request"""
    # Headers with Authorization
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First check if item exists
            check_url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}&product_id=eq.{product_id}&select=*"
            check_response = await client.get(check_url, headers=headers)
            logger.info(f"🛒 Check existing: {check_response.status_code}")
            
            existing = check_response.json() if check_response.status_code == 200 else []
            
            if existing and len(existing) > 0:
                # Update quantity
                new_qty = existing[0]["quantity"] + quantity
                update_url = f"{SUPABASE_URL}/rest/v1/cart_items?id=eq.{existing[0]['id']}"
                update_response = await client.patch(update_url, headers=headers, json={"quantity": new_qty})
                logger.info(f"🛒 Update cart: {update_response.status_code}")
                return update_response.status_code in [200, 204]
            else:
                # Insert new item
                insert_url = f"{SUPABASE_URL}/rest/v1/cart_items"
                insert_response = await client.post(insert_url, headers=headers, json={"user_id": user_id, "product_id": product_id, "quantity": quantity})
                logger.info(f"🛒 Insert cart: {insert_response.status_code}")
                return insert_response.status_code in [200, 201, 204]
    except Exception as e:
        logger.error(f"Add to cart error: {e}")
    return False


# ==================== AI BACKEND ====================

async def chat_with_ai(message: str, chat_id: int, image_base64: str = None) -> dict:
    """Send message to Qwen AI backend"""
    session = user_sessions.get(chat_id, {})
    
    cart_items = session.get("cart_items", [])
    formatted_cart = []
    for item in cart_items:
        p = item.get("products", {})
        formatted_cart.append({
            "product_name": p.get("name", "Item"),
            "price": p.get("price", 0),
            "quantity": item.get("quantity", 1)
        })
    
    payload = {
        "message": message,
        "context": {
            "cartItems": formatted_cart,
            "lastShownProducts": session.get("last_products", []),
            "conversationHistory": session.get("history", []),
            "isLoggedIn": chat_id in linked_accounts
        }
    }
    
    if image_base64:
        payload["context"]["image"] = image_base64
    
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(AI_BACKEND_URL, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"AI backend error: {response.status_code}")
    except Exception as e:
        logger.error(f"AI chat error: {e}")
    
    return {"success": False, "response": "Connection issue. Try again?"}


# ==================== MESSAGE PROCESSING ====================

def format_products(products: List[dict]) -> str:
    """Format products for display"""
    if not products:
        return ""
    
    text = f"\n\n🔍 *Found {len(products)} products:*\n\n"
    for i, p in enumerate(products, 1):
        text += f"{i}. *{p.get('name', 'Product')}*\n"
        text += f"   💰 ₦{p.get('price', 0):,}\n"
        if p.get('category'):
            text += f"   📁 {p['category']}\n"
        text += "\n"
    text += "_Reply with a number to add to cart!_"
    return text


async def process_message(chat_id: int, user_id: int, text: str, username: str = None, image_base64: str = None) -> str:
    """Process incoming message with full AI capabilities"""
    logger.info(f"📩 From {chat_id}: {text[:50] if text else 'image'}...")
    
    # Initialize session
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"last_products": [], "history": [], "cart_items": []}
    
    text_lower = text.strip().lower() if text else ""
    
    # ==================== AUTHENTICATION ====================
    
    if chat_id in auth_sessions:
        session = auth_sessions[chat_id]
        
        if text_lower in ['/cancel', 'cancel']:
            del auth_sessions[chat_id]
            return "❌ Cancelled. Send /start to try again."
        
        if session["state"] == AUTH_STATE_EMAIL:
            email = text.strip()
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return "❌ Invalid email. Please enter a valid email or /cancel"
            auth_sessions[chat_id] = {"state": AUTH_STATE_PASSWORD, "email": email}
            return "🔑 Enter your password:"
        
        if session["state"] == AUTH_STATE_PASSWORD:
            password = text.strip()
            email = session["email"]
            auth_result = await verify_supabase_auth(email, password)
            
            if auth_result:
                # Store user info INCLUDING access_token
                linked_accounts[chat_id] = {
                    "user_id": auth_result["user_id"],
                    "email": email,
                    "access_token": auth_result["access_token"],
                    "telegram_id": chat_id,
                    "username": username
                }
                del auth_sessions[chat_id]
                
                # Load cart using access token
                cart = await get_cart(auth_result["user_id"], auth_result["access_token"])
                user_sessions[chat_id]["cart_items"] = cart
                
                return f"""✅ *Welcome!*

🎉 Account linked!

🤖 I'm Eesha, your AI assistant. I can:
• Chat about ANY topic (ask me anything!)
• Help you find products
• Understand photos you share
• Manage your cart

_What's on your mind?_"""
            else:
                del auth_sessions[chat_id]
                return "❌ Login failed. Send /start to retry."
    
    # ==================== COMMANDS ====================
    
    if text_lower.startswith('/start'):
        if chat_id in linked_accounts:
            return """✅ *Welcome Back!*

🤖 I'm Eesha! Chat with me about anything or send a photo to find products."""
        auth_sessions[chat_id] = {"state": AUTH_STATE_EMAIL}
        return """👋 *Welcome to EeshaMart AI!*

🔐 Enter your email to login:"""
    
    if text_lower in ['/login', 'login']:
        if chat_id in linked_accounts:
            return "✅ Already logged in. /logout to unlink."
        auth_sessions[chat_id] = {"state": AUTH_STATE_EMAIL}
        return "🔐 Enter your email:"
    
    if text_lower in ['/logout', 'logout']:
        if chat_id in linked_accounts:
            del linked_accounts[chat_id]
            user_sessions[chat_id]["cart_items"] = []
        return "✅ Logged out. /start to login."
    
    if text_lower in ['/help', 'help']:
        return """🆘 *Help*

/start - Login
/cart - View cart
/logout - Sign out

🤖 *Natural AI Chat:*
• Ask me ANYTHING - politics, jokes, science!
• "Show me phones under 50000"
• "What's the capital of France?"
• "Tell me a joke"
• Send a photo to find similar products!"""
    
    # ==================== CART COMMAND ====================
    
    if text_lower in ['/cart', 'cart', 'my cart']:
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        
        account = linked_accounts[chat_id]
        cart = await get_cart(account["user_id"], account["access_token"])
        user_sessions[chat_id]["cart_items"] = cart
        
        if cart:
            response = "🛒 *Your Cart:*\n\n"
            total = 0
            for i, item in enumerate(cart, 1):
                p = item.get("products", {})
                name = p.get("name", "Item")
                price = p.get("price", 0)
                qty = item.get("quantity", 1)
                total += price * qty
                response += f"{i}. *{name}* x{qty} = ₦{price*qty:,}\n"
            response += f"\n💰 *Total: ₦{total:,}*\n\n_checkout_ to complete your order!"
            return response
        return "🛒 Your cart is empty. Tell me what you're looking for!"
    
    if text_lower in ['checkout', '/checkout']:
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        return """💳 *Checkout*

Visit eeshamart.com to complete payment!"""
    
    # ==================== QUICK ADD TO CART ====================
    
    if text_lower.isdigit():
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        
        account = linked_accounts[chat_id]
        products = user_sessions[chat_id].get("last_products", [])
        num = int(text_lower)
        
        if 1 <= num <= len(products):
            product = products[num - 1]
            success = await add_to_cart_db(account["user_id"], product["id"], account["access_token"])
            
            if success:
                cart = await get_cart(account["user_id"], account["access_token"])
                user_sessions[chat_id]["cart_items"] = cart
                return f"✅ Added *{product['name']}* to cart!\n\n_Anything else?_"
            else:
                return "❌ Failed to add to cart. Please try again."
        elif products:
            return f"❌ Choose 1-{len(products)}"
    
    # ==================== AI CHAT ====================
    
    if chat_id not in linked_accounts:
        return "🔐 Login first to chat! Send /start"
    
    account = linked_accounts[chat_id]
    
    # Send to AI backend
    ai_response = await chat_with_ai(text, chat_id, image_base64)
    logger.info(f"🤖 AI Response: {ai_response}")
    
    # Store in conversation history
    user_sessions[chat_id]["history"].append({"role": "user", "content": text})
    user_sessions[chat_id]["history"].append({"role": "assistant", "content": ai_response.get("response", "")})
    if len(user_sessions[chat_id]["history"]) > 12:
        user_sessions[chat_id]["history"] = user_sessions[chat_id]["history"][-12:]
    
    response_text = ai_response.get("response", "I'm here to help!")
    action = ai_response.get("action")
    products = ai_response.get("products")
    
    # ========== HANDLE AI ACTIONS ==========
    
    if action:
        action_type = action.get("type") if isinstance(action, dict) else None
        logger.info(f"🎯 Action: {action_type}")
        
        if action_type == "add_to_cart":
            product_index = action.get("product_index", 1)
            add_all = action.get("all", False)
            last_products = user_sessions[chat_id].get("last_products", [])
            
            if add_all and last_products:
                for p in last_products:
                    await add_to_cart_db(account["user_id"], p["id"], account["access_token"])
                cart = await get_cart(account["user_id"], account["access_token"])
                user_sessions[chat_id]["cart_items"] = cart
                response_text = f"✅ Added all {len(last_products)} products to cart!"
            elif 1 <= product_index <= len(last_products):
                product = last_products[product_index - 1]
                success = await add_to_cart_db(account["user_id"], product["id"], account["access_token"])
                if success:
                    cart = await get_cart(account["user_id"], account["access_token"])
                    user_sessions[chat_id]["cart_items"] = cart
                    response_text = f"✅ Added *{product['name']}* to cart!"
                else:
                    response_text = "❌ Failed to add. Try again."
            else:
                response_text = "Which product? Search for products first!"
        
        elif action_type == "view_cart":
            cart = await get_cart(account["user_id"], account["access_token"])
            user_sessions[chat_id]["cart_items"] = cart
            
            if cart:
                cart_msg = "🛒 *Your Cart:*\n\n"
                total = 0
                for i, item in enumerate(cart, 1):
                    p = item.get("products", {})
                    name = p.get("name", "Item")
                    price = p.get("price", 0)
                    qty = item.get("quantity", 1)
                    total += price * qty
                    cart_msg += f"{i}. *{name}* x{qty} = ₦{price*qty:,}\n"
                cart_msg += f"\n💰 *Total: ₦{total:,}*"
                response_text = cart_msg
            else:
                response_text = "🛒 Your cart is empty. Tell me what you're looking for!"
        
        elif action_type == "checkout":
            response_text = """💳 *Ready for checkout!*

Visit eeshamart.com to complete your order."""
        
        elif action_type == "login_required":
            response_text = "🔐 Please login first. Send /start"
    
    # ========== HANDLE PRODUCT SEARCH RESULTS ==========
    
    if products and len(products) > 0:
        user_sessions[chat_id]["last_products"] = products
        response_text += format_products(products)
    elif products is not None and len(products) == 0:
        response_text += "\n\n❌ No products found. Try different keywords?"
    
    return response_text


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "EeshaMart Telegram Bot",
        "bot": "https://t.me/eeshamart_bot",
        "features": [
            "Natural AI Chat (Qwen2.5-3B)",
            "Smart Intent Understanding",
            "Image Analysis (BLIP)",
            "Conversation Memory",
            "Authenticated Cart Operations"
        ]
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"📬 Webhook received")
        
        if "message" in body:
            message = body["message"]
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            username = message.get("from", {}).get("username", "")
            text = message.get("text", "")
            
            # Show typing indicator AND thinking message in chat
            await send_typing_action(chat_id)
            thinking_msg_id = await send_thinking_message(chat_id)
            
            # Handle photo messages
            image_base64 = None
            if "photo" in message and message["photo"]:
                photo = message["photo"][-1]
                file_id = photo.get("file_id")
                
                await send_typing_action(chat_id)
                
                image_bytes = await download_telegram_photo(file_id)
                if image_bytes:
                    image_base64 = f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
            if text or image_base64:
                await send_typing_action(chat_id)
                
                reply = await process_message(
                    chat_id,
                    user_id,
                    text if text else "What do you see in this image?",
                    username,
                    image_base64
                )
                
                if thinking_msg_id:
                    await delete_message(chat_id, thinking_msg_id)
                
                await send_telegram(chat_id, reply)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/setwebhook")
async def set_webhook(request: Request):
    host = request.headers.get("host", "")
    webhook_url = f"https://{host}/webhook/telegram"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json={"url": webhook_url})
        return {"webhook_url": webhook_url, "result": response.json()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
