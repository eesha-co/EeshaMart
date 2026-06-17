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
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EeshaMart Telegram Bot - Full AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tcwdbokruvlizkxcpkzj.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg")
AI_BACKEND_URL = os.environ.get("AI_BACKEND_URL", "https://eeshaai-eeshamart-ai.hf.space/api/chat")

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
    payload = {"chat_id": chat_id, "text": "🤔 <i>Thinking...</i>", "parse_mode": "HTML"}
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
    """Send message via Telegram API (HTML mode)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    logger.info(f"📤 Sending to {chat_id}: {text[:50]}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            return response.json()
    except Exception as e:
        logger.error(f"❌ Send error: {e}")
        return {"ok": False, "error": str(e)}


def escape_html(text: str) -> str:
    """Escape special characters for Telegram HTML parse mode"""
    return (str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;"))


async def send_product_photo(chat_id: int, image_url: str, caption: str) -> bool:
    """Send product photo with caption via Telegram API.

    Telegram only supports JPG/PNG/GIF/BMP/WEBP. Many product images
    (especially from Google Shopping) are in AVIF format, which Telegram
    rejects. We download the image, convert it to JPEG with Pillow, then
    upload the JPEG bytes. This handles any input format.

    Fallback: If conversion fails, try passing the URL directly to Telegram
    (Telegram's servers may handle some formats our code can't).
    """
    import io
    from PIL import Image as PILImage

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    # ---- Strategy 1: Download, convert to JPEG, upload as binary ----
    try:
        download_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if "supabase.co" in image_url:
            download_headers["apikey"] = SUPABASE_KEY

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=download_headers) as dl_client:
            img_response = await dl_client.get(image_url)

        if img_response.status_code == 200 and len(img_response.content) > 100:
            # Open with Pillow (handles AVIF, WebP, PNG, JPG, etc.)
            img = PILImage.open(io.BytesIO(img_response.content)).convert("RGB")

            # Resize if too large (Telegram limit: 10MB, but keep it reasonable)
            MAX_DIM = 800
            w, h = img.size
            if w > MAX_DIM or h > MAX_DIM:
                if w > h:
                    h = round(h * MAX_DIM / w)
                    w = MAX_DIM
                else:
                    w = round(w * MAX_DIM / h)
                    h = MAX_DIM
                img = img.resize((w, h))

            # Save as JPEG bytes
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            image_bytes = buf.getvalue()

            logger.info(f"📸 Image converted to JPEG: {len(img_response.content)} -> {len(image_bytes)} bytes")

            async with httpx.AsyncClient(timeout=60.0) as client:
                files = {"photo": ("product.jpg", image_bytes, "image/jpeg")}
                data = {
                    "chat_id": str(chat_id),
                    "caption": caption,
                    "parse_mode": "HTML"
                }
                response = await client.post(url, data=data, files=files)
                logger.info(f"📸 Binary upload response: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"✅ Product photo sent (JPEG conversion)")
                    return True
                else:
                    logger.warning(f"⚠️ Binary upload failed: {response.text[:200]}")
        else:
            logger.warning(f"⚠️ Image download failed: HTTP {img_response.status_code}, size={len(img_response.content)}")
    except Exception as e:
        logger.warning(f"⚠️ Download/convert/upload failed: {e}")

    # ---- Strategy 2: Pass URL directly to Telegram (fallback) ----
    try:
        logger.info(f"📸 Trying URL fallback: {image_url[:80]}...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "chat_id": chat_id,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML"
            }
            response = await client.post(url, json=payload)
            logger.info(f"📸 URL fallback response: {response.status_code}")
            if response.status_code == 200:
                logger.info(f"✅ Product photo sent (URL fallback)")
                return True
            else:
                logger.warning(f"⚠️ URL fallback failed: {response.text[:200]}")
    except Exception as e:
        logger.error(f"❌ URL fallback error: {e}")

    return False


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
    url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}&select=id,quantity,product_id,products(id,name,price,image_url,category)"
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


async def clear_cart_db(user_id: str, access_token: str) -> bool:
    """Clear all items from user's cart in Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Prefer": "return=minimal"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}"
            response = await client.delete(url, headers=headers)
            logger.info(f"Clear cart: {response.status_code}")
            return response.status_code in [200, 204]
    except Exception as e:
        logger.error(f"Clear cart error: {e}")
    return False


async def remove_from_cart_db(user_id: str, product_id: int, access_token: str) -> bool:
    """Remove a specific product from user's cart in Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Prefer": "return=minimal"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}&product_id=eq.{product_id}"
            response = await client.delete(url, headers=headers)
            logger.info(f"Remove from cart: {response.status_code}")
            return response.status_code in [200, 204]
    except Exception as e:
        logger.error(f"Remove from cart error: {e}")
    return False


async def update_cart_quantity_db(user_id: str, product_id: int, access_token: str, new_quantity: int) -> bool:
    """Update quantity of a product in cart. If new_quantity <= 0, removes the item."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            check_url = f"{SUPABASE_URL}/rest/v1/cart_items?user_id=eq.{user_id}&product_id=eq.{product_id}&select=id"
            check_response = await client.get(check_url, headers=headers)
            existing = check_response.json() if check_response.status_code == 200 else []
            
            if existing:
                if new_quantity <= 0:
                    url = f"{SUPABASE_URL}/rest/v1/cart_items?id=eq.{existing[0]['id']}"
                    response = await client.delete(url, headers=headers)
                else:
                    url = f"{SUPABASE_URL}/rest/v1/cart_items?id=eq.{existing[0]['id']}"
                    response = await client.patch(url, headers=headers, json={"quantity": new_quantity})
                logger.info(f"Update cart qty: {response.status_code}")
                return response.status_code in [200, 204]
            return False
    except Exception as e:
        logger.error(f"Update cart qty error: {e}")
    return False


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
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(AI_BACKEND_URL, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"AI backend error: {response.status_code}")
    except Exception as e:
        logger.error(f"AI chat error: {e}")
    
    return {"success": False, "response": "Connection issue. Try again?"}


# ==================== MESSAGE PROCESSING ====================

def format_product_caption(product: dict, index: int) -> str:
    """Format a single product for photo caption (HTML mode)"""
    name = escape_html(product.get('name', 'Product'))
    text = f"<b>{index}. {name}</b>\n\n"
    text += f"💰 Price: ₦{product.get('price', 0):,}\n"
    if product.get('category'):
        cat = escape_html(product['category'])
        text += f"📁 Category: {cat}\n"
    if product.get('description'):
        desc = escape_html(product['description'][:100])
        if len(str(product.get('description', ''))) > 100:
            desc += "..."
        text += f"📝 {desc}\n"
    text += f"\n<i>Reply '{index}' to add to cart!</i>"
    return text


def format_products(products: List[dict]) -> str:
    """Format products for display (used when no images available) - HTML mode"""
    if not products:
        return ""
    
    text = f"\n\n🔍 <b>Found {len(products)} products:</b>\n\n"
    for i, p in enumerate(products, 1):
        name = escape_html(p.get('name', 'Product'))
        text += f"{i}. <b>{name}</b>\n"
        text += f"   💰 ₦{p.get('price', 0):,}\n"
        if p.get('category'):
            cat = escape_html(p['category'])
            text += f"   📁 {cat}\n"
        text += "\n"
    text += "<i>Reply with a number to add to cart!</i>"
    return text


async def send_products_with_images(chat_id: int, products: List[dict], intro_text: str):
    """Send products with their images to Telegram"""
    if not products:
        await send_telegram(chat_id, intro_text + "\n\n❌ No products found.")
        return
    
    logger.info(f"📦 Sending {len(products)} products with images")
    
    # Send intro message first
    if intro_text:
        await send_telegram(chat_id, intro_text)
    
    # Send each product with its image (limit to first 5 to avoid spam)
    products_to_show = products[:5]
    
    for i, product in enumerate(products_to_show, 1):
        # Get image URL - check multiple possible field names
        image_url = product.get('image_url') or product.get('image') or product.get('imageUrl') or product.get('image_link')
        
        logger.info(f"📦 Product {i}: {product.get('name')} - Image: {image_url[:50] if image_url else 'None'}")
        
        caption = format_product_caption(product, i)
        
        if image_url:
            # Send photo with caption
            success = await send_product_photo(chat_id, image_url, caption)
            
            if not success:
                # Fallback to text if image fails
                logger.warning(f"⚠️ Image failed for product {i}, sending text only")
                await send_telegram(chat_id, caption)
        else:
            # No image, send text only
            logger.info(f"📝 No image for product {i}, sending text only")
            await send_telegram(chat_id, caption)
        
        # Small delay between messages to avoid rate limiting
        await asyncio.sleep(0.5)
    
    # Send summary if there are more products
    if len(products) > 5:
        remaining = len(products) - 5
        summary = f"\n<i>...and {remaining} more products found.</i>\n\n<i>Reply with a number (1-{len(products)}) to add to cart!</i>"
        await send_telegram(chat_id, summary)
    else:
        await send_telegram(chat_id, f"\n<i>Reply with a number (1-{len(products_to_show)}) to add to cart!</i>")


async def send_cart_with_images(chat_id: int, cart_items: List[dict]) -> bool:
    """Send cart items with their product images to Telegram"""
    if not cart_items:
        await send_telegram(chat_id, "🛒 Your cart is empty. Tell me what you're looking for!")
        return False
    
    total_qty = sum(item.get("quantity", 1) or 1 for item in cart_items)
    total = sum((item.get("products", {}) or {}).get("price", 0) * (item.get("quantity", 1) or 1) for item in cart_items)
    
    # Send header
    await send_telegram(chat_id, f"🛒 <b>Your Cart ({total_qty} items):</b>")
    
    # Send each cart item with its product image
    for i, item in enumerate(cart_items, 1):
        p = item.get("products", {}) or {}
        name = p.get("name", "Item")
        price = p.get("price", 0)
        qty = item.get("quantity", 1)
        image_url = p.get("image_url") or p.get("image") or p.get("imageUrl")
        
        caption = f"<b>{i}. {escape_html(name)}</b> x{qty}\n💰 ₦{price * qty:,}"
        
        if image_url:
            success = await send_product_photo(chat_id, image_url, caption)
            if not success:
                await send_telegram(chat_id, caption)
        else:
            await send_telegram(chat_id, caption)
        
        await asyncio.sleep(0.3)
    
    # Send total
    await send_telegram(chat_id, f"\n💰 <b>Total: ₦{total:,}</b>\n\n<i>checkout</i> to complete your order!")
    return True


async def process_message(chat_id: int, user_id: int, text: str, username: str = None, first_name: str = None, image_base64: str = None) -> str:
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
                    "username": username,
                    "first_name": first_name
                }
                del auth_sessions[chat_id]
                
                # Load cart using access token
                cart = await get_cart(auth_result["user_id"], auth_result["access_token"])
                user_sessions[chat_id]["cart_items"] = cart
                
                display_name = first_name or username or "there"
                return f"""✅ <b>Welcome, {escape_html(display_name)}!</b>

🎉 Account linked!

🤖 I'm Eesha, your AI assistant. I can:
• Chat about ANY topic (ask me anything!)
• Help you find products
• Understand photos you share
• Manage your cart

<i>What's on your mind?</i>"""
            else:
                del auth_sessions[chat_id]
                return "❌ Login failed. Send /start to retry."
    
    # ==================== COMMANDS ====================
    
    if text_lower.startswith('/start'):
        if chat_id in linked_accounts:
            display_name = linked_accounts[chat_id].get("first_name") or linked_accounts[chat_id].get("username") or first_name or "back"
            return f"""✅ <b>Welcome back, {escape_html(display_name)}!</b>

🤖 I'm Eesha! Chat with me about anything or send a photo to find products."""
        auth_sessions[chat_id] = {"state": AUTH_STATE_EMAIL}
        return """👋 <b>Welcome to EeshaMart AI!</b>

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
        return """🆘 <b>Help</b>

/start - Login
/cart - View cart
/logout - Sign out

🤖 <b>Natural AI Chat:</b>
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
            return {"send_cart_images": True, "cart_items": cart}
        return "🛒 Your cart is empty. Tell me what you're looking for!"
    
    if text_lower in ['checkout', '/checkout']:
        if chat_id not in linked_accounts:
            return "🔐 Login first. Send /start"
        return """💳 <b>Checkout</b>

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
                return f"✅ Added <b>{escape_html(product['name'])}</b> to cart!\n\n<i>Anything else?</i>"
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
                    response_text = f"✅ Added <b>{escape_html(product['name'])}</b> to cart!"
                else:
                    response_text = "❌ Failed to add. Try again."
            else:
                response_text = "Which product? Search for products first!"
        
        elif action_type == "view_cart":
            cart = await get_cart(account["user_id"], account["access_token"])
            user_sessions[chat_id]["cart_items"] = cart
            
            if cart:
                response_text = ""  # Will be sent as images with send_cart_with_images
            else:
                response_text = "🛒 Your cart is empty. Tell me what you're looking for!"
            
            # Return cart items so webhook can send them with images
            return {
                "response": response_text,
                "products": None,
                "cart_items": cart
            }
        
        elif action_type == "checkout":
            response_text = """💳 <b>Ready for checkout!</b>

Visit eeshamart.com to complete your order."""
        
        elif action_type == "login_required":
            response_text = "🔐 Please login first. Send /start"
        
        elif action_type == "clear_cart":
            success = await clear_cart_db(account["user_id"], account["access_token"])
            if success:
                user_sessions[chat_id]["cart_items"] = []
                response_text = "Your cart has been cleared! It's now empty."
            else:
                response_text = "Failed to clear cart. Please try again."
        
        elif action_type == "remove_from_cart":
            cart_item_number = action.get("cart_item_number", 1)
            cart = user_sessions[chat_id].get("cart_items", [])
            if 1 <= cart_item_number <= len(cart):
                item = cart[cart_item_number - 1]
                product_id = item.get("product_id") or (item.get("products") or {}).get("id")
                if product_id:
                    success = await remove_from_cart_db(account["user_id"], product_id, account["access_token"])
                    if success:
                        cart = await get_cart(account["user_id"], account["access_token"])
                        user_sessions[chat_id]["cart_items"] = cart
                        response_text = "Item removed from your cart!"
                    else:
                        response_text = "Failed to remove. Try again."
                else:
                    response_text = "Could not find that item."
            elif cart:
                response_text = f"Choose a number between 1 and {len(cart)}"
            else:
                response_text = "Your cart is already empty."
        
        elif action_type == "update_cart":
            cart_item_number = action.get("cart_item_number", 1)
            new_quantity = action.get("new_quantity", 1)
            cart = user_sessions[chat_id].get("cart_items", [])
            if 1 <= cart_item_number <= len(cart):
                item = cart[cart_item_number - 1]
                product_id = item.get("product_id") or (item.get("products") or {}).get("id")
                if product_id:
                    success = await update_cart_quantity_db(account["user_id"], product_id, account["access_token"], new_quantity)
                    if success:
                        cart = await get_cart(account["user_id"], account["access_token"])
                        user_sessions[chat_id]["cart_items"] = cart
                        if new_quantity <= 0:
                            response_text = "Item removed from your cart!"
                        else:
                            response_text = f"Quantity updated to {new_quantity}!"
                    else:
                        response_text = "Failed to update. Try again."
                else:
                    response_text = "Could not find that item."
            elif cart:
                response_text = f"Choose a number between 1 and {len(cart)}"
            else:
                response_text = "Your cart is already empty."
    
    # ========== HANDLE PRODUCT SEARCH RESULTS ==========
    
    # Return dict with response and products for image handling
    return {
        "response": response_text,
        "products": products
    }


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
            "Product Images Display",
            "Conversation Memory",
            "Authenticated Cart Operations"
        ]
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


async def handle_telegram_message(body: dict):
    """Process a Telegram message update - runs in background to avoid webhook timeout"""
    try:
        if "message" not in body:
            return
        
        message = body["message"]
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        username = message.get("from", {}).get("username", "")
        first_name = message.get("from", {}).get("first_name", "")
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
            
            # Compress image to max 512px before sending to AI
            compressed_image = None
            if image_base64:
                try:
                    import io
                    from PIL import Image as PILImage
                    # Strip data URI prefix
                    img_data = image_base64
                    if "," in img_data:
                        img_data = img_data.split(",")[1]
                    img_bytes = base64.b64decode(img_data)
                    img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
                    MAX = 512
                    w, h = img.size
                    if w > MAX or h > MAX:
                        if w > h:
                            h = round(h * MAX / w); w = MAX
                        else:
                            w = round(w * MAX / h); h = MAX
                        img = img.resize((w, h))
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=70)
                    compressed_image = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                    logger.info(f"🖼️ Image compressed: {len(image_base64)} -> {len(compressed_image)} chars")
                except Exception as e:
                    logger.warning(f"⚠️ Image compression failed, using original: {e}")
                    compressed_image = image_base64
            
            # Tag image messages so AI knows to search
            ai_text = text
            if compressed_image and not text:
                ai_text = "[User sent a product image] Find me this product or similar ones"
            elif compressed_image and text:
                ai_text = f"[User sent a product image] {text}"
            
            result = await process_message(
                chat_id,
                user_id,
                ai_text,
                username,
                first_name,
                compressed_image
            )
            
            # Handle both old string return and new dict return
            if isinstance(result, dict):
                # Check for /cart command with images
                if result.get("send_cart_images"):
                    cart_items = result.get("cart_items", [])
                    if thinking_msg_id:
                        await delete_message(chat_id, thinking_msg_id)
                    await send_cart_with_images(chat_id, cart_items)
                # Check for AI view_cart action with cart items
                elif "cart_items" in result and result.get("cart_items"):
                    if thinking_msg_id:
                        await delete_message(chat_id, thinking_msg_id)
                    await send_cart_with_images(chat_id, result["cart_items"])
                    # Also send the AI response text if any
                    if result.get("response"):
                        await send_telegram(chat_id, result["response"])
                else:
                    response_text = result.get("response", "")
                    products = result.get("products")
                    
                    # Store products in session if found
                    if products and len(products) > 0:
                        if chat_id not in user_sessions:
                            user_sessions[chat_id] = {"last_products": [], "history": [], "cart_items": []}
                        user_sessions[chat_id]["last_products"] = products
                    
                    if thinking_msg_id:
                        await delete_message(chat_id, thinking_msg_id)
                    
                    # Send response with product images if products found
                    if products and len(products) > 0:
                        await send_products_with_images(chat_id, products, response_text)
                    elif products is not None and len(products) == 0:
                        await send_telegram(chat_id, response_text + "\n\n❌ No products found. Try different keywords?")
                    else:
                        await send_telegram(chat_id, response_text)
            else:
                # Old string response
                response_text = result
                if thinking_msg_id:
                    await delete_message(chat_id, thinking_msg_id)
                await send_telegram(chat_id, response_text)
    except Exception as e:
        logger.error(f"❌ Error handling message: {e}")
        import traceback
        traceback.print_exc()


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Webhook endpoint - responds immediately to Telegram to avoid timeout retries.
    Actual message processing happens in the background.
    """
    try:
        body = await request.json()
        logger.info(f"📬 Webhook received")
        
        # Process message in background - return OK immediately
        # Telegram retries webhook if no response within 60 seconds
        # AI inference takes ~56s + sending products, so we MUST respond fast
        asyncio.create_task(handle_telegram_message(body))
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
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
