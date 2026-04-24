# EeshaMart AI - Pure Natural Language Understanding
# NO keywords, NO pattern matching - AI understands intent naturally
# Supports: conversation memory, budget planning, image understanding

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import base64
from io import BytesIO

from transformers import AutoModelForCausalLM, AutoTokenizer, BlipProcessor, BlipForConditionalGeneration
import torch
from PIL import Image

app = FastAPI(title="EeshaMart AI - Natural Understanding")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = "https://tcwdbokruvlizkxcpkzj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg"

# Models
chat_model = None
chat_tokenizer = None
vision_processor = None
vision_model = None

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict] = None

@app.on_event("startup")
async def load():
    global chat_model, chat_tokenizer, vision_processor, vision_model
    
    print("Loading AI models...")
    
    # Load chat model (Qwen 3B)
    print("Loading Qwen2.5-3B for chat...")
    chat_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct", trust_remote_code=True)
    chat_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-3B-Instruct", torch_dtype=torch.float32, trust_remote_code=True)
    chat_model.eval()
    
    # Load vision model (BLIP for image understanding)
    print("Loading BLIP for image understanding...")
    vision_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    vision_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    vision_model.eval()
    
    print("✅ All models loaded - Pure natural language AI ready!")

def analyze_image(base64_image: str) -> str:
    """Analyze an image using BLIP and return description"""
    global vision_processor, vision_model
    
    try:
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]
        
        image_bytes = base64.b64decode(base64_image)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        inputs = vision_processor(image, return_tensors="pt")
        
        with torch.no_grad():
            output = vision_model.generate(**inputs, max_length=100)
        
        caption = vision_processor.decode(output[0], skip_special_tokens=True)
        print(f"Image analysis: {caption}")
        
        return caption
    except Exception as e:
        print(f"Image analysis error: {e}")
        return "an image"

async def db_search(query: str, max_price: int = None) -> List[Dict]:
    """Search products in database - more flexible search"""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Clean and split query
            terms = query.lower().replace("-", " ").split()
            # Filter out common words that don't help search
            stop_words = ["the", "a", "an", "is", "are", "was", "were", "be", "been", "being", 
                         "have", "has", "had", "do", "does", "did", "will", "would", "could",
                         "should", "may", "might", "must", "shall", "can", "need", "dare",
                         "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
                         "from", "up", "about", "into", "over", "after", "show", "me", "find",
                         "search", "looking", "want", "please", "can", "you", "get", "i"]
            
            search_terms = [t for t in terms if t not in stop_words and len(t) > 1]
            
            if not search_terms:
                search_terms = terms[-3:]  # Use last few words if all were stop words
            
            filters = []
            for t in search_terms:
                filters.append(f"name.ilike.%25{t}%25")
                filters.append(f"category.ilike.%25{t}%25")
                filters.append(f"description.ilike.%25{t}%25")
            
            url = f"{SUPABASE_URL}/rest/v1/products?select=*&or=({','.join(filters)})&order=created_at.desc&limit=20"
            
            if max_price:
                url += f"&price.lte.{max_price}"
            
            print(f"Search URL: {url}")
            r = await client.get(url, headers={"apikey": SUPABASE_KEY})
            products = r.json() if r.status_code == 200 else []
            
            print(f"Found {len(products)} products for: {search_terms}")
            return products
    except Exception as e:
        print(f"Search error: {e}")
        return []

async def db_get_all_products() -> List[Dict]:
    """Get all products for reference"""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            url = f"{SUPABASE_URL}/rest/v1/products?select=id,name,price,category&order=created_at.desc&limit=100"
            r = await client.get(url, headers={"apikey": SUPABASE_KEY})
            return r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"Get all products error: {e}")
        return []

async def ai_understand(message: str, cart_items: List, shown_products: List, 
                        conversation_history: List, all_products: List,
                        image_description: str = None) -> Dict:
    """
    AI understands user intent naturally without keywords or pattern matching.
    Returns the AI's response AND the detected intent.
    """
    global chat_model, chat_tokenizer
    
    if not chat_model:
        return {"reply": "AI is loading... please wait.", "intent": None}
    
    # Build cart context
    cart_text = ""
    if cart_items and len(cart_items) > 0:
        cart_text = f"\n[USER'S CART - {len(cart_items)} items:]\n"
        total = 0
        for i, item in enumerate(cart_items, 1):
            name = item.get("product_name") or "Item"
            price = item.get("price") or 0
            qty = item.get("quantity", 1) or 1
            total += price * qty
            cart_text += f"{i}. {name} x{qty} = ₦{price*qty:,}\n"
        cart_text += f"CART TOTAL: ₦{total:,}\n"
    else:
        cart_text = "\n[USER'S CART is EMPTY]\n"
    
    # Build recently shown products context
    products_text = ""
    if shown_products and len(shown_products) > 0:
        products_text = "\n[PRODUCTS YOU JUST SHOWED THE USER:]\n"
        for i, p in enumerate(shown_products, 1):
            products_text += f"{i}. {p.get('name', 'Product')} - ₦{p.get('price', 0):,} (ID: {p.get('id')})\n"
        products_text += "[If user wants to add/choose a product, use these numbers]\n"

    # Build available products list
    available_text = ""
    if all_products:
        available_text = "\n[SAMPLE PRODUCTS IN STORE (name - price - category):]\n"
        for p in all_products[:30]:  # Show first 30
            available_text += f"- {p.get('name')} - ₦{p.get('price', 0):,} - {p.get('category', 'General')}\n"

    # Build conversation history
    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        history_text = "\n[RECENT CONVERSATION:]\n"
        for msg in conversation_history[-6:]:
            role = "User" if msg.get("role") == "user" else "Eesha"
            history_text += f"{role}: {msg.get('content', '')[:200]}\n"
        history_text += "\n"

    # Image context
    image_text = ""
    if image_description:
        image_text = f"""
[USER SHARED AN IMAGE - You can see: {image_description}]
Acknowledge what you see in the image and offer to help find similar products.
[/END IMAGE]
"""

    system = f"""You are Eesha, a friendly AI assistant for EeshaMart Nigeria online store.

{cart_text}{products_text}{available_text}{history_text}{image_text}

You are a NATURAL conversational AI. You can discuss ANY topic - not just shopping!
- Answer questions about politics, science, geography, jokes, anything
- Be friendly, helpful, and conversational
- Only talk about shopping when the user CLEARLY wants to shop

CRITICAL: Understand what the user ACTUALLY means, not just keywords!

SHOPPING - Only when user clearly wants to shop:
- User wants to find products: They ask to see, find, search, or browse products
- User wants to add to cart: They clearly say "add to cart", "I want this", "buy this"
- User wants to see cart: They ask "what's in my cart", "show my cart", "my cart"
- User wants to checkout: They say "checkout", "pay", "complete order"

BE CAREFUL: 
- "I don't want to add this" → They do NOT want to add (respect their choice!)
- "Don't show me phones" → They do NOT want phones
- "What's the price of..." → They're asking a question, not necessarily buying
- "Can I see..." → They want to see/view, not buy yet

Respond naturally as JSON with this format:
{{"reply": "your natural response", "intent": {{"type": "...", "data": "..."}}}}

Possible intents:
- {{"type": "search", "query": "product name", "max_price": 50000}} - User wants to find products
- {{"type": "add_to_cart", "product_number": 1}} - User wants to add a product (use number from shown products)
- {{"type": "view_cart"}} - User wants to see their cart
- {{"type": "checkout"}} - User wants to checkout
- {{"type": "chat"}} - Normal conversation (no shopping action)
- null - No specific action needed

REMEMBER: If no products have been shown yet, you cannot add to cart!
REMEMBER: Only use product numbers from the [PRODUCTS YOU JUST SHOWED THE USER] list!

The user says: "{message}"

Respond naturally as JSON:"""

    try:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": message}
        ]
        
        text = chat_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = chat_tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
        
        with torch.no_grad():
            out = chat_model.generate(
                inputs["input_ids"],
                max_new_tokens=300,
                temperature=0.7,
                do_sample=True,
                pad_token_id=chat_tokenizer.eos_token_id
            )
        
        response = chat_tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        print(f"AI raw response: {response}")
        
        # Parse JSON response
        try:
            # Find JSON in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                # No JSON found, treat as plain text
                return {"reply": response, "intent": None}
        except json.JSONDecodeError:
            # Failed to parse JSON, use response as-is
            return {"reply": response, "intent": None}
        
    except Exception as e:
        print(f"AI error: {e}")
        return {"reply": "I'm thinking... could you try again?", "intent": None}

@app.get("/")
async def root():
    return {
        "online": True, 
        "ai": "EeshaMart Natural AI", 
        "features": ["natural_understanding", "no_keywords", "vision", "memory"]
    }

@app.get("/api/health")
async def health():
    return {"ok": True, "vision": True, "mode": "natural"}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    print(f"\n{'='*50}\nUSER: {req.message}")
    
    ctx = req.context or {}
    cart_items = ctx.get("cartItems", [])
    shown_products = ctx.get("lastShownProducts", [])
    conversation_history = ctx.get("conversationHistory", [])
    is_logged_in = ctx.get("isLoggedIn", False)
    user_image = ctx.get("image")
    
    print(f"History: {len(conversation_history)} msgs, Image: {bool(user_image)}")
    
    # Analyze image if provided
    image_description = None
    if user_image:
        print("Analyzing image...")
        image_description = analyze_image(user_image)
        print(f"Image contains: {image_description}")
    
    # Get all available products for reference
    all_products = await db_get_all_products()
    
    # AI understands the message naturally
    ai = await ai_understand(
        req.message, 
        cart_items, 
        shown_products, 
        conversation_history,
        all_products,
        image_description
    )
    print(f"AI result: {ai}")
    
    result = {
        "success": True,
        "response": ai.get("reply", "How can I help?"),
        "products": None,
        "action": None,
        "image_description": image_description
    }
    
    intent = ai.get("intent")
    
    if intent:
        intent_type = intent.get("type")
        print(f"Intent: {intent_type}")
        
        if intent_type == "search":
            query = intent.get("query", req.message)
            max_price = intent.get("max_price")
            
            # If we have an image description, enhance search
            if image_description and image_description != "an image":
                desc_words = image_description.lower().split()
                for word in desc_words[:3]:  # Use first 3 words
                    if len(word) > 2 and word not in query.lower():
                        query += f" {word}"
            
            products = await db_search(query, max_price)
            result["products"] = products
            
            if not products:
                result["response"] = f"I searched for '{query}' but couldn't find any products. Would you like to try different keywords?"
            else:
                result["response"] = ai.get("reply", f"I found {len(products)} products for you!")
        
        elif intent_type == "add_to_cart":
            product_number = intent.get("product_number", 1)
            result["action"] = {
                "type": "add_to_cart",
                "product_index": product_number,
                "quantity": 1
            }
        
        elif intent_type == "view_cart":
            result["action"] = {"type": "view_cart"}
            if not is_logged_in:
                result["response"] = "Please login to view your cart."
                result["action"] = {"type": "login_required"}
        
        elif intent_type == "checkout":
            result["action"] = {"type": "checkout"}
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
