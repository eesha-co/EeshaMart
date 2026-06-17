# EeshaMart AI - Dynamic Function Calling AI (HF Inference API edition)
#
# Chat: Qwen2.5-72B-Instruct (or any model) via HF Router (OpenAI-compatible)
# Vision: Salesforce BLIP (local, small ~1GB) - kept local because HF Router
#         doesn't expose vision models on the free tier.
#
# Benefits over local-Qwen version:
#   - ~10x faster responses (2-5s vs 30-60s)
#   - Much better function-calling reliability (72B vs 3B)
#   - Smaller Docker image (no 6GB Qwen download)
#   - Free HF CPU tier handles it easily

import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import base64
from io import BytesIO

# BLIP still loaded locally (small, ~1GB)
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch
from PIL import Image

app = FastAPI(title="EeshaMart AI - Dynamic")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Configuration (loaded from environment variables / HF Space Secrets)
# ----------------------------------------------------------------------------
# Required
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Chat model - via HF Router (OpenAI-compatible)
HF_ROUTER_URL = os.environ.get("HF_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions")
HF_INFERENCE_MODEL = os.environ.get("HF_INFERENCE_MODEL", "Qwen/Qwen2.5-72B-Instruct")

# Vision model (BLIP) - kept local because HF Router doesn't expose vision models
VISION_MODEL_ID = os.environ.get("VISION_MODEL_ID", "Salesforce/blip-image-captioning-base")

# Optional - runtime tuning
PORT = int(os.environ.get("PORT", "7860"))
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "512"))
MAX_INPUT_TOKENS = int(os.environ.get("MAX_INPUT_TOKENS", "3072"))
AI_TIMEOUT = float(os.environ.get("AI_TIMEOUT", "60"))  # seconds for HF Router call

print(
    "Config: "
    f"SUPABASE_URL={'set' if SUPABASE_URL else 'MISSING'}, "
    f"SUPABASE_KEY={'set' if SUPABASE_KEY else 'MISSING'}, "
    f"HF_INFERENCE_MODEL={HF_INFERENCE_MODEL}, "
    f"VISION_MODEL_ID={VISION_MODEL_ID}, "
    f"HF_TOKEN={'set' if HF_TOKEN else 'MISSING'}, "
    f"PORT={PORT}"
)

# Vision model loaded at startup (chat model is remote - no local load)
vision_processor = None
vision_model = None


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict] = None


@app.on_event("startup")
async def load():
    """Only load BLIP locally. Chat model is called via HF Router (remote)."""
    global vision_processor, vision_model

    print(f"Loading {VISION_MODEL_ID} for image understanding (local)...")
    vision_processor = BlipProcessor.from_pretrained(VISION_MODEL_ID, token=HF_TOKEN or None)
    vision_model = BlipForConditionalGeneration.from_pretrained(VISION_MODEL_ID, token=HF_TOKEN or None)
    vision_model.eval()

    print(f"Chat model: {HF_INFERENCE_MODEL} via HF Router (remote, no local load)")
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
    Dynamic AI with function calling via HF Router (Qwen2.5-72B-Instruct or similar).

    Returns: {"reply": str, "calls": [{"function": str, "args": {...}}, ...]}
    """
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

    # System prompt
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
7. update_cart(cart_item_number: int, new_quantity: int) - Change quantity of a cart item (use number from CURRENT CART). Set new_quantity to 0 to remove it.

RESPONSE FORMAT - You MUST respond as valid JSON ONLY (no markdown, no code fences, no prose before or after):

For normal chat (no action needed):
{{"reply": "your response here"}}

When you want to call a function:
{{"reply": "what you say to the user", "calls": [{{"function": "function_name", "args": {{"param": "value"}}}}]}}

You can call MULTIPLE functions at once if needed.
You can also respond with NO calls - just a reply - when the user is chatting, asking questions, or no action is needed.

IMPORTANT:
- When user sends a product image, IMMEDIATELY call search_products with what you see in the image
- When user describes something abstractly (e.g. "something that flies and records video"), infer the product type and call search_products with a relevant query (e.g. "drone")
- Always count TOTAL products (sum quantities), not types. If cart has item1 x2 and item2 x3, total is 5
- When user says "clear cart", "empty cart", "remove everything", "I don't want any products" - call clear_cart
- When user says "remove X" or "take out X" - call remove_from_cart with the cart item number
- When user says "change quantity to X", "I want X of this", "update to X" - call update_cart
- When user says "that one", "the first one", "number 3" - refer to the products lists above
- Respect negatives: "don't" means do NOT do it, "no" means no
- Be natural and conversational. Do not be robotic or templated.{context_block}{available_block}"""

    # Build messages with conversation history
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

    # Call HF Router (OpenAI-compatible)
    try:
        payload = {
            "model": HF_INFERENCE_MODEL,
            "messages": messages,
            "max_tokens": MAX_NEW_TOKENS,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            resp = await client.post(HF_ROUTER_URL, json=payload, headers=headers)

        if resp.status_code != 200:
            print(f"HF Router HTTP {resp.status_code}: {resp.text[:500]}")
            return {"reply": "I'm having trouble connecting to my brain right now. Please try again in a moment.", "calls": []}

        data = resp.json()
        response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        print(f"AI raw response: {response_text}")
        print(f"Tokens used: {data.get('usage', {})}")

        # Parse JSON (large models are usually clean, but keep the robust parser for safety)
        result = parse_ai_response(response_text)
        if result is not None:
            return result

        # No JSON parseable - return raw text as reply
        return {"reply": response_text, "calls": []}

    except httpx.TimeoutException:
        print("HF Router timeout")
        return {"reply": "I'm thinking... could you try again?", "calls": []}
    except Exception as e:
        print(f"AI error: {e}")
        return {"reply": "I'm having trouble right now. Please try again.", "calls": []}


def parse_ai_response(response: str) -> Optional[Dict]:
    """
    Parse the AI's response into {reply, calls}.

    Large models (Qwen2.5-72B) usually emit clean JSON. We keep the robust
    multi-strategy parser as defensive coding for edge cases.
    """
    if not response:
        return None

    # Strip code fences if present (```json ... ```)
    stripped = response.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first fence line and last fence line
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
        response = stripped

    json_start = response.find('{')
    if json_start == -1:
        return None

    # Strategy 1: bracket-matched extraction (handles trailing garbage)
    balanced_end = _find_balanced_json_end(response, json_start)
    if balanced_end > json_start:
        json_str = response[json_start:balanced_end]
        result = _try_parse(json_str, response)
        if result is not None:
            return result

        repaired = _repair_json(json_str)
        if repaired != json_str:
            result = _try_parse(repaired, response, repair_log=True)
            if result is not None:
                return result

    # Strategy 2: first-{ to last-} (handles missing-quote case)
    json_end = response.rfind('}') + 1
    if json_end > json_start:
        json_str = response[json_start:json_end]
        result = _try_parse(json_str, response)
        if result is not None:
            return result

        repaired = _repair_json(json_str)
        if repaired != json_str:
            result = _try_parse(repaired, response, repair_log=True)
            if result is not None:
                return result

    return None


def _try_parse(json_str: str, raw_response: str, repair_log: bool = False) -> Optional[Dict]:
    try:
        result = json.loads(json_str)
        if not isinstance(result, dict):
            return None
        if "reply" not in result:
            # AI emitted JSON without a "reply" field (usually just {"calls": [...]}).
            # Use empty string - the chat endpoint will fill in a sensible default
            # if no reply is provided. Do NOT use raw_response as fallback because
            # that would leak JSON to the user.
            result["reply"] = ""
        if "calls" not in result:
            result["calls"] = []
        if repair_log:
            print(f"Auto-repaired JSON: {json_str}")
        return result
    except (json.JSONDecodeError, ValueError):
        return None


def _find_balanced_json_end(s: str, start: int) -> int:
    if start >= len(s) or s[start] != '{':
        return -1
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c in '{[':
            depth += 1
        elif c in '}]':
            depth -= 1
            if depth == 0:
                return i + 1
    return -1


def _repair_json(s: str) -> str:
    import re
    s = re.sub(r'"(\w+):\s', r'"\1": ', s)
    if "'" in s and not re.search(r'"[^"]*\'[^"]*"', s):
        s = s.replace("'", '"')
    s = re.sub(r',\s*([}\]])', r'\1', s)
    s = re.sub(r'(?<=[{,])\s*(\w+)\s*:', r' "\1":', s)
    return s


async def execute_function_call(call: Dict, shown_products: List,
                                 message: str, image_description: str = None) -> Dict:
    """Dynamically execute ANY function the AI decides to call."""
    func_name = call.get("function", "")
    args = call.get("args", {})

    print(f"Executing function: {func_name} with args: {args}")

    result = {"function": func_name, "success": False, "data": None}

    if func_name == "search_products":
        query = args.get("query", message)
        max_price = args.get("max_price")

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
        result["data"] = {
            "type": "remove_from_cart",
            "product_index": product_number,
            "product_number": product_number,
            "cart_item_number": product_number
        }

    elif func_name == "clear_cart":
        result["success"] = True
        result["data"] = {"type": "clear_cart"}

    elif func_name == "view_cart":
        result["success"] = True
        result["data"] = {"type": "view_cart"}

    elif func_name == "checkout":
        result["success"] = True
        result["data"] = {"type": "checkout"}

    elif func_name == "update_cart":
        cart_item_number = args.get("cart_item_number", 1)
        new_quantity = args.get("new_quantity", 1)
        result["success"] = True
        result["data"] = {
            "type": "update_cart",
            "cart_item_number": cart_item_number,
            "new_quantity": new_quantity
        }

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
        "chat_model": HF_INFERENCE_MODEL,
        "vision_model": VISION_MODEL_ID,
        "features": ["conversation_memory", "function_calling", "vision", "dynamic", "remote_llm"]
    }


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "vision": True,
        "mode": "dynamic",
        "chat_model": HF_INFERENCE_MODEL,
    }


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

    reply = ai.get("reply", "") or ""
    calls = ai.get("calls", [])

    # If the AI called functions but provided no reply text, construct a sensible default
    # so the user isn't left staring at an empty message.
    if not reply.strip() and calls:
        func_names = [c.get("function", "") for c in calls]
        if "search_products" in func_names:
            reply = "Let me search for that."
        elif "add_to_cart" in func_names:
            reply = "Added to your cart."
        elif "remove_from_cart" in func_names:
            reply = "Removed from your cart."
        elif "update_cart" in func_names:
            reply = "Your cart has been updated."
        elif "clear_cart" in func_names:
            reply = "Your cart has been cleared."
        elif "view_cart" in func_names:
            reply = "Here's your cart."
        elif "checkout" in func_names:
            reply = "Starting checkout."
        else:
            reply = "Done."
    elif not reply.strip():
        reply = "How can I help?"

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
                               "view_cart", "checkout", "update_cart") and exec_result["success"]:
                action_data = func_data

                if func_name in ("view_cart",) and not is_logged_in:
                    result["response"] = "Please login to view your cart."
                    result["action"] = {"type": "login_required"}
                else:
                    result["action"] = action_data

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
