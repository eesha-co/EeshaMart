# EeshaMart AI - Dynamic Function Calling AI
# Works like ChatGPT/Gemini/Grok: AI decides what functions to call based on context
# NO hardcoded intents, NO pattern matching, NO rigid rules
# Real conversation memory, image understanding, dynamic tool use

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

app = FastAPI(title="EeshaMart AI - Dynamic")

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
    
    print("Loading Qwen2.5-3B for chat...")
    chat_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct", trust_remote_code=True)
    chat_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-3B-Instruct", torch_dtype=torch.float32, trust_remote_code=True)
    chat_model.eval()
    
    print("Loading BLIP for image understanding...")
    vision_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    vision_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    vision_model.eval()
    
    print("All models loaded - Dynamic AI ready!")

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
                search_terms = terms[-3:]
            
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
    Dynamic AI with function calling - like ChatGPT/Gemini/Grok.
    AI sees available functions and decides WHEN to use them based on context.
    No hardcoded intents. No pattern matching. Pure understanding.
    """
    global chat_model, chat_tokenizer
    
    if not chat_model:
        return {"reply": "AI is loading... please wait.", "calls": []}
    
    # Build dynamic context
    context_parts = []
    
    # Cart context
    if cart_items and len(cart_items) > 0:
        total_qty = sum(item.get("quantity", 1) or 1 for item in cart_items)
        total_cost = sum((item.get("price") or 0) * (item.get("quantity", 1) or 1) for item in cart_items)
        lines = []
        for i, item in enumerate(cart_items, 1):
            name = item.get("product_name") or "Item"
            price = item.get("price") or 0
            qty = item.get("quantity", 1) or 1
            lines.append(f"  {i}. {name} x{qty} = N{price*qty:,}")
        context_parts.append(
            f"[CURRENT CART: {total_qty} total products ({len(cart_items)} types), value N{total_cost:,}]\n" +
            "\n".join(lines)
        )
    else:
        context_parts.append("[CURRENT CART: empty]")
    
    # Recently shown products
    if shown_products and len(shown_products) > 0:
        lines = []
        for i, p in enumerate(shown_products, 1):
            lines.append(f"  {i}. {p.get('name', 'Product')} - N{p.get('price', 0):,}")
        context_parts.append(
            "[RECENTLY SHOWN PRODUCTS (user can refer to by number)]\n" + "\n".join(lines)
        )
    
    # Image context
    if image_description:
        context_parts.append(f"[USER SENT IMAGE showing: {image_description}]")
    
    context_block = "\n\n".join(context_parts)
    
    # Available products
    available_block = ""
    if all_products:
        lines = [f"- {p.get('name')} (N{p.get('price',0):,}, {p.get('category','General')})" for p in all_products[:25]]
        available_block = "\n\n[STORE PRODUCTS:]\n" + "\n".join(lines)
    
    # System prompt - describes available functions, NOT rigid rules
    system = f"""You are Eesha, a smart AI assistant for EeshaMart (Nigerian online store, prices in Naira N).
You are helpful, friendly, and knowledgeable. You can discuss ANY topic naturally.
You have real conversation memory - you remember what was said before.

You have ACCESS TO FUNCTIONS. When you decide a function should be called, include it in your JSON response.
When NO function is needed (just chatting, answering questions, etc.), respond with only a reply.

AVAILABLE FUNCTIONS:
1. search_products(query: str, max_price?: number) - Search store for products matching the query
2. add_to_cart(product_number: int) - Add a product to cart (use number from RECENTLY SHOWN PRODUCTS)
3. remove_from_cart(product_number: int) - Remove a product from cart (use number from CURRENT CART)
4. clear_cart() - Empty the entire cart, remove everything
5. view_cart() - Show cart contents
6. checkout() - Start the checkout process

RESPONSE FORMAT - You MUST respond as valid JSON:

For normal chat (no action needed):
{{"reply": "your response here"}}

When you want to call a function:
{{"reply": "what you say to the user", "calls": [{{"function": "function_name", "args": {{"param": "value"}}}}]}}

You can call MULTIPLE functions at once if needed.
You can also respond with NO calls - just a reply - when the user is chatting, asking questions, or no action is needed.

IMPORTANT:
- When user sends a product image, IMMEDIATELY call search_products with what you see
- Always count TOTAL products (sum quantities), not types. If cart has item1 x2 and item2 x3, total is 5
- When user says "clear cart", "empty cart", "remove everything", "I don't want any products" - call clear_cart
- When user says "remove X" or "take out X" - call remove_from_cart with the cart item number
- When user says "that one", "the first one", "number 3" - refer to the products lists above
- Respect negatives: "don't" means do NOT do it, "no" means no
- Be natural and conversational. Do not robotic or templated.{context_block}{available_block}"""

    # Build messages with REAL conversation history as chat turns
    messages = [{"role": "system", "content": system}]
    
    if conversation_history and len(conversation_history) > 0:
        recent = conversation_history[-10:]
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and role in ("user", "assistant"):
                # Clean JSON artifacts from assistant history
                if role == "assistant" and content.strip().startswith("{"):
                    try:
                        parsed = json.loads(content)
                        content = parsed.get("reply", content)
                    except:
                        pass
                messages.append({"role": role, "content": content})
    
    messages.append({"role": "user", "content": message})
    
    try:
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
        
        # Parse JSON
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                if "reply" not in result:
                    result = {"reply": response, "calls": []}
                if "calls" not in result:
                    result["calls"] = []
                return result
        except json.JSONDecodeError:
            pass
        
        return {"reply": response, "calls": []}
        
    except Exception as e:
        print(f"AI error: {e}")
        return {"reply": "I'm thinking... could you try again?", "calls": []}


async def execute_function_call(call: Dict, shown_products: List, 
                                 message: str, image_description: str = None) -> Dict:
    """
    Dynamically execute ANY function the AI decides to call.
    No hardcoded intent matching - just look up the function and run it.
    """
    func_name = call.get("function", "")
    args = call.get("args", {})
    
    print(f"Executing function: {func_name} with args: {args}")
    
    result = {"function": func_name, "success": False, "data": None}
    
    if func_name == "search_products":
        query = args.get("query", message)
        max_price = args.get("max_price")
        
        # Enhance with image description if available
        if image_description and image_description != "an image":
            for word in image_description.lower().split()[:4]:
                if len(word) > 2 and word not in query.lower():
                    query += f" {word}"
        
        products = await db_search(query, max_price)
        result["success"] = True
        result["data"] = products
    
    elif func_name == "add_to_cart":
        product_number = args.get("product_number", 1)
        result["success"] = True
        result["data"] = {"type": "add_to_cart", "product_index": product_number, "quantity": 1}
    
    elif func_name == "remove_from_cart":
        product_number = args.get("product_number", 1)
        result["success"] = True
        result["data"] = {"type": "remove_from_cart", "product_index": product_number}
    
    elif func_name == "clear_cart":
        result["success"] = True
        result["data"] = {"type": "clear_cart"}
    
    elif func_name == "view_cart":
        result["success"] = True
        result["data"] = {"type": "view_cart"}
    
    elif func_name == "checkout":
        result["success"] = True
        result["data"] = {"type": "checkout"}
    
    else:
        print(f"Unknown function: {func_name}")
        result["success"] = False
        result["data"] = {"error": f"Unknown function: {func_name}"}
    
    return result


@app.get("/")
async def root():
    return {
        "online": True, 
        "ai": "EeshaMart Dynamic AI", 
        "features": ["conversation_memory", "function_calling", "vision", "dynamic"]
    }

@app.get("/api/health")
async def health():
    return {"ok": True, "vision": True, "mode": "dynamic"}

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
    
    reply = ai.get("reply", "How can I help?")
    calls = ai.get("calls", [])
    
    result = {
        "success": True,
        "response": reply,
        "products": None,
        "action": None,
        "image_description": image_description
    }
    
    # Execute all function calls dynamically
    if calls and len(calls) > 0:
        for call in calls:
            exec_result = await execute_function_call(
                call, shown_products, req.message, image_description
            )
            
            func_name = exec_result.get("function", "")
            func_data = exec_result.get("data")
            
            if func_name == "search_products" and exec_result["success"]:
                products = func_data
                result["products"] = products
                if not products:
                    result["response"] = reply or f"I couldn't find products matching that. Try different keywords?"
            
            elif func_name in ("add_to_cart", "remove_from_cart", "clear_cart", 
                               "view_cart", "checkout") and exec_result["success"]:
                action_data = func_data
                
                # Handle login requirement for cart operations
                if func_name in ("view_cart",) and not is_logged_in:
                    result["response"] = "Please login to view your cart."
                    result["action"] = {"type": "login_required"}
                else:
                    result["action"] = action_data
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
