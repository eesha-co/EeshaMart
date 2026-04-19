# EeshaMart AI - Smart, Free, and Natural with Vision
# NO hardcoding, NO pattern matching - Pure AI understanding
# Supports: conversation memory, budget planning, IMAGE UNDERSTANDING

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import re
import base64
from io import BytesIO

from transformers import AutoModelForCausalLM, AutoTokenizer, BlipProcessor, BlipForConditionalGeneration
import torch
from PIL import Image

app = FastAPI(title="EeshaMart AI - Smart & Free with Vision")

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
    
    print("✅ All models loaded - AI can see and chat!")

def analyze_image(base64_image: str) -> str:
    """Analyze an image using BLIP and return description"""
    global vision_processor, vision_model
    
    try:
        # Decode base64 image
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]
        
        image_bytes = base64.b64decode(base64_image)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        # Generate caption
        inputs = vision_processor(image, return_tensors="pt")
        
        with torch.no_grad():
            output = vision_model.generate(**inputs, max_length=100)
        
        caption = vision_processor.decode(output[0], skip_special_tokens=True)
        print(f"Image analysis: {caption}")
        
        return caption
    except Exception as e:
        print(f"Image analysis error: {e}")
        return "an image"

async def db_search(query: str, max_price: int = None, category: str = None) -> List[Dict]:
    """Search products in database with optional filters"""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            terms = query.lower().split()
            filters = []
            
            for t in terms:
                filters.append(f"name.ilike.%25{t}%25")
                filters.append(f"category.ilike.%25{t}%25")
                filters.append(f"description.ilike.%25{t}%25")
            
            url = f"{SUPABASE_URL}/rest/v1/products?select=*&or=({','.join(filters)})&order=created_at.desc&limit=20"
            
            if max_price:
                url += f"&price.lte.{max_price}"
            
            r = await client.get(url, headers={"apikey": SUPABASE_KEY})
            products = r.json() if r.status_code == 200 else []
            
            return products
    except Exception as e:
        print(f"Search error: {e}")
        return []

async def ai_think(message: str, cart_items: List, shown_products: List, conversation_history: List, image_description: str = None) -> Dict:
    """AI thinks naturally - can understand images, no hardcoding"""
    global chat_model, chat_tokenizer
    
    if not chat_model:
        return {"reply": "AI is loading... please wait."}
    
    # Build context
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
    
    products_text = ""
    if shown_products and len(shown_products) > 0:
        products_text = "\n[PRODUCTS recently shown:]\n"
        for i, p in enumerate(shown_products, 1):
            products_text += f"{i}. {p.get('name', 'Product')} - ₦{p.get('price', 0):,}\n"

    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        history_text = "\n[CONVERSATION HISTORY:]\n"
        for msg in conversation_history[-6:]:
            role = "User" if msg.get("role") == "user" else "Eesha"
            history_text += f"{role}: {msg.get('content', '')[:200]}\n"
        history_text += "\n"

    # Image context - the AI can SEE now!
    image_text = ""
    if image_description:
        image_text = f"""
[!!! USER SHARED AN IMAGE !!!]
I can see: {image_description}
You MUST acknowledge this image in your response and offer to find similar products!
Use the image description to search: SEARCH: {image_description.split()[0]} 
[/END IMAGE CONTEXT]
"""

    system = f"""You are Eesha, a smart AI assistant for EeshaMart Nigeria. You can see images that users share!

{cart_text}{products_text}{history_text}{image_text}

You can discuss ANY topic freely - politics, geography, science, jokes, anything!

When user shares an image:
- Start by describing what you see: "I can see [description]"
- Then offer to find similar products: "Let me find similar products for you! SEARCH: [main object]"
- If they ask questions about the image, answer them

SHOPPING ACTIONS - Only for shopping requests:

SEARCH: [product to find]
BUDGET: [max price if mentioned]

CART: show
ADD: [number]
CHECKOUT: go

Examples:
User: "Show me phones under 50000" → "I'll find phones for you! SEARCH: phones BUDGET: 50000"
User: "What's in my cart?" → "Let me check. CART: show"
User: "Add the first one" → "Adding! ADD: 1"
User: "Who is the president?" → Just answer normally
User shares image of headphones → "I can see headphones on a yellow background! Let me find similar products for you. SEARCH: headphones"

The user says: "{message}"

Respond naturally. If they shared an image, acknowledge what you see. Only add action keywords for SHOPPING:"""

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
                max_new_tokens=200,
                temperature=0.7,
                do_sample=True,
                pad_token_id=chat_tokenizer.eos_token_id
            )
        
        response = chat_tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        print(f"AI raw: {response}")
        
        result = {"reply": response}
        
        # Parse SEARCH action
        search_match = re.search(r'SEARCH:\s*([^\n]+)', response)
        if search_match:
            result["action"] = "search"
            query = search_match.group(1).strip()
            query = re.sub(r'BUDGET:.*', '', query).strip()
            result["query"] = query
            budget_match = re.search(r'BUDGET:\s*(\d+)', response)
            if budget_match:
                result["budget"] = int(budget_match.group(1))
            clean_reply = re.sub(r'(SEARCH:|BUDGET:|CART:|ADD:|CHECKOUT:).*', '', response).strip()
            if clean_reply:
                result["reply"] = clean_reply
        
        # Parse CART action
        if re.search(r'CART:\s*show', response, re.IGNORECASE):
            result["action"] = "show_cart"
            result["reply"] = re.sub(r'CART:.*', '', response).strip()
        
        # Parse ADD action
        add_match = re.search(r'ADD:\s*(\d+|all)', response, re.IGNORECASE)
        if add_match:
            result["action"] = "add"
            result["index"] = add_match.group(1)
            result["reply"] = re.sub(r'ADD:.*', '', response).strip()
        
        # Parse CHECKOUT action
        if re.search(r'CHECKOUT:\s*go', response, re.IGNORECASE):
            result["action"] = "checkout"
            result["reply"] = re.sub(r'CHECKOUT:.*', '', response).strip()
        
        return result
        
    except Exception as e:
        print(f"AI error: {e}")
        return {"reply": "I'm thinking... could you try again?"}

@app.get("/")
async def root():
    return {
        "online": True, 
        "ai": "Eesha Smart AI with Vision", 
        "features": ["memory", "budget_planning", "natural_chat", "image_understanding"]
    }

@app.get("/api/health")
async def health():
    return {"ok": True, "vision": True}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    print(f"\n{'='*50}\nUSER: {req.message}")
    
    ctx = req.context or {}
    cart_items = ctx.get("cartItems", [])
    shown_products = ctx.get("lastShownProducts", [])
    conversation_history = ctx.get("conversationHistory", [])
    is_logged_in = ctx.get("isLoggedIn", False)
    user_image = ctx.get("image")  # Base64 image
    
    print(f"History: {len(conversation_history)} msgs, Image: {bool(user_image)}")
    
    # Analyze image if provided
    image_description = None
    if user_image:
        print("Analyzing image...")
        image_description = analyze_image(user_image)
        print(f"Image contains: {image_description}")
    
    # AI processes with image context
    ai = await ai_think(req.message, cart_items, shown_products, conversation_history, image_description)
    print(f"AI response: {ai}")
    
    result = {
        "success": True,
        "response": ai.get("reply", "How can I help?"),
        "products": None,
        "action": None,
        "image_description": image_description
    }
    
    action = ai.get("action")
    
    if action == "search":
        query = ai.get("query", req.message)
        budget = ai.get("budget")
        
        # If we have an image description, enhance the search
        if image_description and image_description != "an image":
            # Extract keywords from image description
            desc_words = image_description.lower().split()
            for word in desc_words:
                if len(word) > 3 and word not in query.lower():
                    query += f" {word}"
        
        products = await db_search(query, max_price=budget)
        result["products"] = products
        if not products:
            result["response"] = f"I couldn't find any {query}. Want to try different keywords?"
        elif not ai.get("reply"):
            result["response"] = f"Found {len(products)} products for you!"
    
    elif action == "show_cart":
        result["action"] = {"type": "view_cart"}
        if not is_logged_in:
            result["response"] = "Please login to view your cart."
            result["action"] = {"type": "login_required"}
        elif cart_items and len(cart_items) > 0:
            cart_msg = "Here's your cart:\n"
            total = 0
            for i, item in enumerate(cart_items, 1):
                name = item.get("product_name") or "Item"
                price = item.get("price") or 0
                qty = item.get("quantity", 1) or 1
                total += price * qty
                cart_msg += f"{i}. {name} x{qty} = ₦{price*qty:,}\n"
            cart_msg += f"\nTotal: ₦{total:,}"
            result["response"] = cart_msg
        else:
            result["response"] = "Your cart is empty. Want me to help you find something?"
    
    elif action == "add":
        index = ai.get("index", 1)
        result["action"] = {
            "type": "add_to_cart",
            "product_index": int(index) if str(index).isdigit() else 1,
            "quantity": 1,
            "all": str(index).lower() == "all"
        }
    
    elif action == "checkout":
        result["action"] = {"type": "checkout"}
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
