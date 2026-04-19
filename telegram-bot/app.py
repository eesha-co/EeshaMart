"""
EeshaMart Telegram Bot - Production Ready with AI Chat + Vision
Natural conversation powered by Qwen2.5-3B (via Hugging Face backend)
Low memory - all AI processing happens on Hugging Face!

Bot: https://t.me/eeshamart_bot
"""

import httpx
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import string
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EeshaMart Telegram Bot with AI Chat + Vision")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8142562507:AAG-_UExIh18e6mz-0URKmv67-CQOk_cuA4")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tcwdbokruvlizkxcpkzj.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg")
AI_BACKEND_URL = os.environ.get("AI_BACKEND_URL", "https://fuhaddesmond-eeshamart-ai.hf.space/api/chat")

logger.info("🤖 EeshaMart Telegram Bot with AI Chat Starting...")

# Storage
linked_accounts: Dict[int, dict] = {}
auth_sessions: Dict[int, dict] = {}
user_sessions: Dict[int, dict] = {}

AUTH_STATE_NONE = "none"
AUTH_STATE_EMAIL = "waiting_email"
AUTH_STATE_PASSWORD = "waiting_password"

async def send_telegram(chat_id: int, text: str):
    """Send message via Telegram API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    logger.info(f"📤 Sending to {chat_id}")
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

async def chat_with_ai(message: str, chat_id: int, image_base64: str = None) -> dict:
    """Send message to AI backend and get response with actions"""
    session = user_sessions.get(chat_id, {})
    
    payload = {
        "message": message,
        "context": {
            "cartItems": session.get("cart_items", []),
            "lastShownProducts": session.get("last_products", []),
            "conversationHistory": session.get("history", []),
            "isLoggedIn": chat_id in linked_accounts
        }
    }
    
    if image_base64:
        payload["context"]["image"] = image_base64
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(AI_BACKEND_URL, json=payload)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"AI chat error: {e}")
    
    return {"success": False, "response": "Connection issue. Try again?"}

async def search_products_db(query: str, limit: int = 5) -> List[dict]:
    """Search products from Supabase"""
    search_terms = query.lower().split()
    or_conditions = []
    for term in search_terms:
        or_conditions.append(f"name.ilike.%25{term}%25")
        or_conditions.append(f"description.ilike.%25{term}%25")
        or_conditions.append(f"category.ilike.%25{term}%25")
    
    url = f"{SUPABASE_URL}/rest/v1/products?or=({','.join(or_conditions)})&select=id,name,price,description,category,image_url&limit={limit}"
    headers = {"apikey": SUPABASE_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Search error: {e}")
    return []

async def get_cart(user_id: str) -> List[dict]:
    """Get user's cart"""
    url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}&select=id,quantity,product_id,products(id,name,price)"
    headers = {"apikey": SUPABASE_KEY}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            return response.json() if response.status_code == 200 else []
    except Exception as e:
        logger.error(f"Cart error: {e}")
        return []

async def add_to_cart_db(user_id: str, product_id: int, quantity: int = 1) -> bool:
    """Add product to cart"""
    url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}&product_id=eq.{product_id}&select=*"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json", "Prefer": "return=minimal"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            existing = response.json()
            if existing:
                await client.patch(f"{SUPABASE_URL}/rest/v1/cart_items?id=eq.{existing[0]['id']}", headers=headers, json={"quantity": existing[0]["quantity"] + quantity})
            else:
                await client.post(f"{SUPABASE_URL}/rest/v1/cart_items", headers=headers, json={"user_id": user_id, "product_id": product_id, "quantity": quantity})
        return True
    except Exception as e:
        logger.error(f"Add to cart error: {e}")
        return False

async def verify_supabase_auth(email: str, password: str) -> Optional[dict]:
    """Verify user credentials with Supabase Auth"""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json={"email": email, "password": password})
            if response.status_code == 200:
                data = response.json()
                return {"user_id": data.get("user", {}).get("id"), "email": data.get("user", {}).get("email"), "access_token": data.get("access_token")}
    except Exception as e:
        logger.error(f"Auth error: {e}")
    return None

def format_products_message(products: List[dict]) -> str:
    """Format products for Telegram message"""
    if not products:
        return "No products found."
    
    response = f"🔍 *Found {len(products)} products:*\n\n"
    for i, p in enumerate(products, 1):
        response += f"{i}. *{p['name']}*\n"
        response += f"   💰 ₦{p['price']:,}\n"
        if p.get('category'):
            response += f"   📁 {p['category']}\n"
        response += "\n"
    response += "_Reply with a number to add to cart, or chat with me!_"
    return response

async def process_message(chat_id: int, user_id: int, text: str, username: str = None, image_base64: str = None) -> str:
    """Process incoming message with AI"""
    logger.info(f"📩 From {chat_id}: {text[:50] if text else 'image'}...")
    
    # Initialize session
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"last_products": [], "history": [], "cart_items": []}
    
    text_lower = text.strip().lower() if text else ""
    
    # ========== AUTHENTICATION ==========
    
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
                linked_accounts[chat_id] = {"user_id": auth_result["user_id"], "email": email, "telegram_id": chat_id, "username": username}
                del auth_sessions[chat_id]
                # Get cart items for context
                cart = await get_cart(auth_result["user_id"])
                user_sessions[chat_id]["cart_items"] = cart
                return f"""✅ *Welcome!*

🎉 Account linked successfully!

🤖 I'm Eesha, your AI shopping assistant! You can:
• Chat naturally with me about anything
• Search for products (just describe what you want)
• Send photos to find similar products
• Add items to cart

_What would you like?_"""
            else:
                del auth_sessions[chat_id]
                return "❌ Login failed. Send /start to retry."
    
    # ========== BASIC COMMANDS ==========
    
    if text_lower.startswith('/start'):
        if chat_id in linked_accounts:
            return """✅ *Welcome Back!*

🤖 I'm Eesha, your AI shopping assistant! Chat naturally with me or send a photo to find products."""
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
            if chat_id in user_sessions:
                user_sessions[chat_id]["cart_items"] = []
        return "✅ Logged out. /start to login."
    
    if text_lower in ['/help', 'help']:
        return """🆘 *Help*

/start - Login
/cart - View cart  
/logout - Sign out

🤖 *Just chat naturally!*
• "Show me phones under 50000"
• "I need something for gaming"
• "What's the weather like?"
• Send a photo to find similar products!"""
    
    # ========== CART COMMAND ==========
    
    if text_lower in ['/cart', 'cart', 'my cart']:
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        
        cart = await get_cart(linked_accounts[chat_id]["user_id"])
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
        return "🛒 Cart is empty. Tell me what you're looking for!"
    
    # ========== CHECKOUT ==========
    
    if text_lower in ['checkout', '/checkout']:
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        return """💳 *Checkout*

Visit eeshamart.com to complete payment!"""
    
    # ========== QUICK ADD TO CART ==========
    
    # Check if user is typing a number to add to cart
    if text_lower.isdigit() or text_lower.startswith('add '):
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        
        products = user_sessions[chat_id].get("last_products", [])
        
        if text_lower.startswith('add '):
            num_str = text_lower[4:].strip()
            if num_str.isdigit():
                num = int(num_str)
            else:
                num = 0
        else:
            num = int(text_lower)
        
        if 1 <= num <= len(products):
            product = products[num - 1]
            await add_to_cart_db(linked_accounts[chat_id]["user_id"], product["id"])
            # Update session cart
            cart = await get_cart(linked_accounts[chat_id]["user_id"])
            user_sessions[chat_id]["cart_items"] = cart
            return f"✅ Added *{product['name']}* to cart!\n\n_Anything else?_"
        elif products:
            return f"❌ Choose 1-{len(products)}"
    
    # ========== AI CHAT ==========
    
    # Check login for shopping actions
    if chat_id not in linked_accounts:
        return "🔐 Login first to chat and shop! Send /start"
    
    # Send to AI backend for natural conversation
    ai_response = await chat_with_ai(text, chat_id, image_base64)
    
    logger.info(f"AI Response: {ai_response}")
    
    # Store in conversation history
    user_sessions[chat_id]["history"].append({"role": "user", "content": text})
    user_sessions[chat_id]["history"].append({"role": "assistant", "content": ai_response.get("response", "")})
    # Keep only last 10 messages
    if len(user_sessions[chat_id]["history"]) > 10:
        user_sessions[chat_id]["history"] = user_sessions[chat_id]["history"][-10:]
    
    response_text = ai_response.get("response", "I'm here to help!")
    action = ai_response.get("action")
    products = ai_response.get("products")
    
    # Handle AI actions
    if action:
        action_type = action.get("type") if isinstance(action, dict) else None
        
        if action_type == "add_to_cart":
            # Add to cart
            product_index = action.get("product_index", 1)
            quantity = action.get("quantity", 1)
            add_all = action.get("all", False)
            
            last_products = user_sessions[chat_id].get("last_products", [])
            
            if add_all and last_products:
                for p in last_products:
                    await add_to_cart_db(linked_accounts[chat_id]["user_id"], p["id"])
                cart = await get_cart(linked_accounts[chat_id]["user_id"])
                user_sessions[chat_id]["cart_items"] = cart
                response_text = f"✅ Added all {len(last_products)} products to cart!"
            elif 1 <= product_index <= len(last_products):
                product = last_products[product_index - 1]
                await add_to_cart_db(linked_accounts[chat_id]["user_id"], product["id"], quantity)
                cart = await get_cart(linked_accounts[chat_id]["user_id"])
                user_sessions[chat_id]["cart_items"] = cart
                response_text = f"✅ Added *{product['name']}* to cart!"
        
        elif action_type == "view_cart":
            cart = await get_cart(linked_accounts[chat_id]["user_id"])
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
            response_text = """💳 *Ready to checkout!*

Visit eeshamart.com to complete your order."""
        
        elif action_type == "login_required":
            response_text = "🔐 Please login first. Send /start"
    
    # Handle product search results
    if products and len(products) > 0:
        user_sessions[chat_id]["last_products"] = products
        response_text += "\n\n" + format_products_message(products)
    
    return response_text

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "status": "online", 
        "service": "EeshaMart Telegram Bot with AI Chat + Vision", 
        "bot": "https://t.me/eeshamart_bot",
        "ai": "Qwen2.5-3B via Hugging Face"
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
            
            # Handle photo messages
            image_base64 = None
            if "photo" in message and message["photo"]:
                photo = message["photo"][-1]
                file_id = photo.get("file_id")
                
                await send_telegram(chat_id, "📸 _Analyzing image..._")
                
                image_bytes = await download_telegram_photo(file_id)
                if image_bytes:
                    image_base64 = f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
            if text or image_base64:
                reply = await process_message(
                    chat_id, 
                    user_id, 
                    text if text else "What's in this image?", 
                    username, 
                    image_base64
                )
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
