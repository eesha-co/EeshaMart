"""
EeshaMart Telegram Bot - Production Ready with Vision
Email/Password Authentication + Direct Product Search + IMAGE UNDERSTANDING

Bot: https://t.me/eeshamart_bot
"""

import httpx
import os
import json
import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import string
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO

# Vision model imports
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EeshaMart Telegram Bot with Vision")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8142562507:AAG-_UExIh18e6mz-0URKmv67-CQOk_cuA4")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tcwdbokruvlizkxcpkzj.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg")
AI_BACKEND_URL = os.environ.get("AI_BACKEND_URL", "https://fuhaddesmond-eeshamart-ai.hf.space/api/chat")

logger.info("🤖 EeshaMart Telegram Bot Starting...")

# Vision Model - Same as Website
vision_processor = None
vision_model = None

@app.on_event("startup")
async def load_vision_model():
    global vision_processor, vision_model
    logger.info("Loading BLIP vision model...")
    vision_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    vision_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    vision_model.eval()
    logger.info("✅ Vision model loaded - Bot can see images!")

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
        # Get file path
        file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(file_url)
            if response.status_code == 200:
                file_path = response.json().get("result", {}).get("file_path")
                if file_path:
                    # Download the actual file
                    photo_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                    photo_response = await client.get(photo_url)
                    if photo_response.status_code == 200:
                        return photo_response.content
    except Exception as e:
        logger.error(f"❌ Photo download error: {e}")
    return None

def analyze_image(image_bytes: bytes) -> str:
    """Analyze image using BLIP - Same model as website"""
    global vision_processor, vision_model
    
    if vision_processor is None or vision_model is None:
        return "an image"
    
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        # Generate caption using BLIP
        inputs = vision_processor(image, return_tensors="pt")
        
        with torch.no_grad():
            output = vision_model.generate(**inputs, max_length=100)
        
        caption = vision_processor.decode(output[0], skip_special_tokens=True)
        logger.info(f"🖼️ Image analysis: {caption}")
        
        return caption
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return "an image"

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

async def search_products(query: str, limit: int = 5) -> List[dict]:
    """Search products directly from Supabase"""
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

async def add_to_cart(user_id: str, product_id: int, quantity: int = 1) -> bool:
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

async def process_message(chat_id: int, user_id: int, text: str, username: str = None, image_description: str = None) -> str:
    """Process incoming message"""
    logger.info(f"📩 From {chat_id}: {text}")
    
    text_lower = text.strip().lower() if text else ""
    
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"last_products": []}
    
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
                linked_accounts[chat_id] = {"user_id": auth_result["user_id"], "email": email, "telegram_id": chat_id, "username": username, "history": []}
                del auth_sessions[chat_id]
                return f"""✅ *Welcome!*

🎉 Account linked successfully!

🛒 *You can now:*
• Search for products
• Add items to cart
• View your cart
• Send photos to find similar products!

_What would you like?_"""
            else:
                del auth_sessions[chat_id]
                return "❌ Login failed. Send /start to retry."
    
    # ========== COMMANDS ==========
    
    if text_lower.startswith('/start'):
        if chat_id in linked_accounts:
            return """✅ *Welcome Back!*

🛒 What would you like to shop for?
📸 You can also send a photo to find similar products!"""
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
        return "✅ Logged out. /start to login."
    
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
            response += f"\n💰 *Total: ₦{total:,}*"
            return response
        return "🛒 Cart is empty. Search for products!"
    
    if text_lower in ['checkout', '/checkout']:
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        return """💳 *Checkout*

Visit eeshamart.com to complete payment!"""
    
    if text_lower in ['/help', 'help']:
        return """🆘 *Help*

/start - Login
/cart - View cart
/checkout - Checkout
/logout - Sign out

📸 Send a photo to find similar products!
Just type what you want to buy!"""
    
    # Check login
    if chat_id not in linked_accounts:
        return "🔐 Login first. Send /start"
    
    # ========== IMAGE SEARCH ==========
    
    if image_description:
        # User sent an image - search for similar products
        logger.info(f"🖼️ Searching for: {image_description}")
        products = await search_products(image_description)
        
        if products:
            user_sessions[chat_id]["last_products"] = products
            response = f"📸 *I can see: {image_description}*\n\n🔍 *Found {len(products)} similar products:*\n\n"
            for i, p in enumerate(products, 1):
                response += f"{i}. *{p['name']}*\n"
                response += f"   💰 ₦{p['price']:,}\n"
                if p.get('category'):
                    response += f"   📁 {p['category']}\n"
                response += "\n"
            response += "_Reply with a number to add to cart!_"
            return response
        else:
            return f"📸 *I can see: {image_description}*\n\n❌ No similar products found. Try a different image or search with text."
    
    # ========== PRODUCT SEARCH ==========
    
    # Check if adding to cart by number
    if text_lower.isdigit() or text_lower.startswith('add '):
        products = user_sessions[chat_id]["last_products"]
        
        # Parse "add 2" or just "2"
        if text_lower.startswith('add '):
            num = int(text_lower[4:].strip())
        else:
            num = int(text_lower)
        
        if 1 <= num <= len(products):
            product = products[num - 1]
            await add_to_cart(linked_accounts[chat_id]["user_id"], product["id"])
            return f"✅ Added *{product['name']}* to cart!"
        else:
            return f"❌ Invalid number. Choose 1-{len(products)}"
    
    # Search products
    products = await search_products(text)
    
    if products:
        user_sessions[chat_id]["last_products"] = products
        response = f"🔍 *Found {len(products)} products:*\n\n"
        for i, p in enumerate(products, 1):
            response += f"{i}. *{p['name']}*\n"
            response += f"   💰 ₦{p['price']:,}\n"
            if p.get('category'):
                response += f"   📁 {p['category']}\n"
            response += "\n"
        response += "_Reply with a number to add to cart!_"
        return response
    else:
        return f"❌ No products found for '{text}'. Try different keywords."

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "status": "online", 
        "service": "EeshaMart Telegram Bot with Vision", 
        "bot": "https://t.me/eeshamart_bot",
        "vision": vision_model is not None
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "vision_loaded": vision_model is not None}

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"📬 Webhook: {json.dumps(body)[:500]}...")
        
        if "message" in body:
            message = body["message"]
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            username = message.get("from", {}).get("username", "")
            text = message.get("text", "")
            
            # Handle photo messages
            image_description = None
            if "photo" in message and message["photo"]:
                # Get the largest photo (last in array)
                photo = message["photo"][-1]
                file_id = photo.get("file_id")
                
                # Send typing indicator
                await send_telegram(chat_id, "📸 _Analyzing image..._")
                
                # Download and analyze image
                image_bytes = await download_telegram_photo(file_id)
                if image_bytes:
                    image_description = analyze_image(image_bytes)
                    logger.info(f"🖼️ Image description: {image_description}")
            
            if text or image_description:
                reply = await process_message(
                    chat_id, 
                    user_id, 
                    text if text else "", 
                    username, 
                    image_description
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
