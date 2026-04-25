# EeshaMart AI - Smart Conversational AI
# Fully dynamic - NO hardcoded intents, NO pattern matching
# Real conversation memory, image understanding, smart shopping

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

app = FastAPI(title="EeshaMart AI - Smart Conversational")

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
    
    print("All models loaded - Smart AI ready!")

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
    """Search products in database"""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            terms = query.lower().replace("-", " ").split()
            stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", 
                         "have", "has", "had", "do", "does", "did", "will", "would", "could",
                         "should", "may", "might", "must", "shall", "can", "need", "dare",
                         "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
                         "from", "up", "about", "into", "over", "after", "show", "me", "find",
                         "search", "looking", "want", "please", "you", "get", "i", "this",
                         "that", "it", "and", "or", "but", "not", "no", "yes", "what", "how",
                         "why", "when", "where", "which", "who", "some", "any", "all", "each",
                         "more", "also", "very", "much", "many", "too", "just", "only"}
            
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

async def ai_chat(message: str, cart_items: List, shown_products: List, 
                   conversation_history: List, all_products: List,
                   image_description: str = None) -> Dict:
    """
    Fully dynamic AI - understands intent naturally from conversation context.
    Uses real conversation history as chat turns (not just system prompt text).
    """
    global chat_model, chat_tokenizer
    
    if not chat_model:
        return {"reply": "AI is loading... please wait.", "intent": None}
    
    # Build dynamic context that changes based on what's relevant
    context_sections = []
    
    # Cart context - show quantity totals properly
    if cart_items and len(cart_items) > 0:
        total_qty = sum(item.get("quantity", 1) or 1 for item in cart_items)
        total_cost = sum((item.get("price") or 0) * (item.get("quantity", 1) or 1) for item in cart_items)
        cart_lines = []
        for i, item in enumerate(cart_items, 1):
            name = item.get("product_name") or "Item"
            price = item.get("price") or 0
            qty = item.get("quantity", 1) or 1
            cart_lines.append(f"  {i}. {name} x{qty} = N{price*qty:,}")
        cart_text = "\n".join(cart_lines)
        context_sections.append(
            f"[CURRENT CART - {total_qty} total products ({len(cart_items)} different types), total value N{total_cost:,}:]\n{cart_text}"
        )
    
    # Recently shown products
    if shown_products and len(shown_products) > 0:
        prod_lines = []
        for i, p in enumerate(shown_products, 1):
            prod_lines.append(f"  {i}. {p.get('name', 'Product')} - N{p.get('price', 0):,} (ID: {p.get('id')})")
        context_sections.append(
            f"[RECENTLY SHOWN PRODUCTS - User can pick by number:]\n" + "\n".join(prod_lines)
        )
    
    # Image context
    if image_description:
        context_sections.append(
            f"[USER SHARED AN IMAGE: {image_description}]"
        )
    
    # Build the full context block
    context_block = ""
    if context_sections:
        context_block = "\n\n" + "\n\n".join(context_sections)
    
    # Available products (compact)
    available_block = ""
    if all_products:
        avail_lines = [f"- {p.get('name')} (N{p.get('price',0):,}, {p.get('category','General')})" for p in all_products[:25]]
        available_block = "\n\n[AVAILABLE PRODUCTS IN STORE:]\n" + "\n".join(avail_lines)
    
    # Build system prompt - smart and flexible, not rigid
    system = f"""You are Eesha, the friendly AI assistant for EeshaMart, a Nigerian online store. You are naturally smart and handle conversations intelligently - you understand context, remember what was discussed, and respond appropriately.

You can talk about ANYTHING - shopping, general knowledge, jokes, advice, recommendations, comparisons, calculations, and more. Be warm, helpful, and conversational. Use Nigerian Naira (N) for prices.

When the user wants to shop:
- Search for products they ask about
- Help them compare options
- Add items to their cart when they clearly want to buy
- Show cart contents and totals accurately
- Suggest alternatives if what they want isn't found

IMPORTANT RULES:
- Always count TOTAL products (sum of quantities), not just different types
- If user says "how many items in my cart" and there are ChatGPT x2, Grok x3, Gemini x5, answer is 10 total products (3 different types)
- If user sends a product image, IMMEDIATELY search for matching or similar products - do NOT ask clarifying questions first
- If user says "that one" or "the first one" or "number 3", refer to the recently shown products list
- If user asks to remove something, decrease quantity or remove from cart
- Respect negatives: "don't show me phones" means NO phones, "I don't want that" means do NOT add it

RESPOND AS JSON: {{"reply": "your response text", "intent": {{"type": "...", ...}}}}

Intent types (only set when user clearly wants to take an action):
- search: {{"type": "search", "query": "what to search for", "max_price": optional_number}}
- add_to_cart: {{"type": "add_to_cart", "product_number": N}}
- remove_from_cart: {{"type": "remove_from_cart", "product_number": N}}
- view_cart: {{"type": "view_cart"}}
- clear_cart: {{"type": "clear_cart"}}
- checkout: {{"type": "checkout"}}
- null or omitted: when just chatting, no action needed

Only set intent when user is clearly requesting an action. For general questions, comparisons, or casual chat, set intent to null.{context_block}{available_block}"""

    # Build messages with REAL conversation history as chat turns
    messages = [{"role": "system", "content": system}]
    
    # Add conversation history as actual user/assistant turns
    if conversation_history and len(conversation_history) > 0:
        # Use up to last 10 messages (5 turns) to keep context window manageable
        recent = conversation_history[-10:]
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and role in ("user", "assistant"):
                # Clean content - strip any JSON artifacts from AI responses
                if role == "assistant":
                    # AI responses from history may have JSON, extract just the reply text
                    if content.strip().startswith("{"):
                        try:
                            parsed = json.loads(content)
                            content = parsed.get("reply", content)
                        except:
                            pass
                messages.append({"role": role, "content": content})
    
    # Add the current user message
    messages.append({"role": "user", "content": message})
    
    try:
        # Apply chat template with full history
        text = chat_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = chat_tokenizer(text, return_tensors="pt", truncation=True, max_length=3072)
        
        with torch.no_grad():
            out = chat_model.generate(
                inputs["input_ids"],
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=chat_tokenizer.eos_token_id
            )
        
        response = chat_tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        print(f"AI raw response: {response}")
        
        # Parse JSON response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                # Ensure reply exists
                if "reply" not in result:
                    # Maybe the whole thing is the reply
                    result = {"reply": response, "intent": None}
                return result
            else:
                return {"reply": response, "intent": None}
        except json.JSONDecodeError:
            return {"reply": response, "intent": None}
        
    except Exception as e:
        print(f"AI error: {e}")
        return {"reply": "I'm thinking... could you try again?", "intent": None}

@app.get("/")
async def root():
    return {
        "online": True, 
        "ai": "EeshaMart Smart AI", 
        "features": ["conversation_memory", "dynamic_intent", "vision", "smart_cart"]
    }

@app.get("/api/health")
async def health():
    return {"ok": True, "vision": True, "mode": "smart"}

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
    
    # AI processes message with full context and real conversation history
    ai = await ai_chat(
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
                for word in desc_words[:4]:
                    if len(word) > 2 and word not in query.lower():
                        query += f" {word}"
            
            products = await db_search(query, max_price)
            result["products"] = products
            
            if not products:
                result["response"] = ai.get("reply", f"I searched for '{query}' but couldn't find any products. Would you like to try different keywords?")
            else:
                result["response"] = ai.get("reply", f"I found {len(products)} products for you!")
        
        elif intent_type == "add_to_cart":
            product_number = intent.get("product_number", 1)
            result["action"] = {
                "type": "add_to_cart",
                "product_index": product_number,
                "quantity": 1
            }
        
        elif intent_type == "remove_from_cart":
            product_number = intent.get("product_number", 1)
            result["action"] = {
                "type": "remove_from_cart",
                "product_index": product_number
            }
        
        elif intent_type == "view_cart":
            result["action"] = {"type": "view_cart"}
            if not is_logged_in:
                result["response"] = ai.get("reply", "Please login to view your cart.")
                result["action"] = {"type": "login_required"}
        
        elif intent_type == "clear_cart":
            result["action"] = {"type": "clear_cart"}
        
        elif intent_type == "checkout":
            result["action"] = {"type": "checkout"}
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
