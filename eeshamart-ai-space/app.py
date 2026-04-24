# EeshaMart AI - Simple & Working (with Image Support)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import json
import re
import base64
from io import BytesIO

from transformers import AutoModelForCausalLM, AutoTokenizer, BlipProcessor, BlipForConditionalGeneration
import torch
from PIL import Image

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase
SUPABASE_URL = "https://tcwdbokruvlizkxcpkzj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg"

# Load models
print("Loading Qwen2.5-1.5B-Instruct...")
chat_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
chat_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", torch_dtype=torch.float32, low_cpu_mem_usage=True)
chat_model.eval()
print("Chat model ready!")

print("Loading BLIP for image understanding...")
vision_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
vision_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
vision_model.eval()
print("Vision model ready!")

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

def analyze_image(base64_image: str) -> str:
    """Analyze an image using BLIP and return a description."""
    try:
        # Strip data URI prefix if present (e.g. "data:image/jpeg;base64,")
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]

        image_bytes = base64.b64decode(base64_image)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        inputs = vision_processor(image, return_tensors="pt")
        with torch.no_grad():
            output = vision_model.generate(**inputs, max_length=100)

        caption = vision_processor.decode(output[0], skip_special_tokens=True)
        print(f"[BLIP] Image caption: {caption}")
        return caption
    except Exception as e:
        print(f"[BLIP] Error analyzing image: {e}")
        return "an image"

async def search_db(query: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc&limit=10"
        if query:
            url += f"&or=(name.ilike.%25{query}%25,description.ilike.%25{query}%25)"
        r = await client.get(url, headers={"apikey": SUPABASE_KEY})
        return r.json() if r.status_code == 200 else []

def ask_model(msg: str, image_description: str = None) -> dict:
    # Add image context to the prompt if an image was analyzed
    image_context = ""
    if image_description:
        image_context = f"""
[The user shared an image. BLIP vision model describes it as: "{image_description}"]
You MUST acknowledge the image and respond about what you see. If the user asks about the image, describe it and offer to find similar products.
"""

    prompt = f"""You are Eesha, a shopping assistant for EeshaMart Nigeria. Return ONLY JSON.

{image_context}
Rules:
- "show cart", "my cart", "what in cart", "view cart" = view_cart
- "checkout", "pay", "buy" = checkout
- "find", "search", "show me X" = search
- "add" = add_to_cart

IMPORTANT: "cart" questions = view_cart (seeing), NOT checkout (paying)!

Examples:
"What is in my cart?" -> {{"intent":"view_cart","response":"Checking your cart!"}}
"Show my cart" -> {{"intent":"view_cart","response":"Here's your cart!"}}
"Checkout" -> {{"intent":"checkout","response":"Going to checkout!"}}
"Find phones" -> {{"intent":"search","query":"phones","response":"Searching!"}}
"Add first" -> {{"intent":"add_to_cart","product_index":1,"quantity":1,"response":"Added!"}}
"What is this image?" -> {{"intent":"chat","response":"That looks like a [describe item]. Would you like me to find something similar?"}}
"This is what I want" (with image) -> {{"intent":"search","query":"[item from image]","response":"Searching for similar items!"}}

User: {msg}
JSON:"""

    inputs = chat_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        out = chat_model.generate(inputs["input_ids"], max_new_tokens=80, temperature=0.1, pad_token_id=chat_tokenizer.eos_token_id)

    text = chat_tokenizer.decode(out[0], skip_special_tokens=True)[len(prompt):]
    match = re.search(r'\{[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group().replace("'", '"'))
        except:
            pass
    return {"intent": "chat", "response": "Can you rephrase?"}

@app.get("/")
def home():
    return {"status": "online", "model": "Qwen2.5-1.5B-Instruct", "vision": "BLIP"}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    print(f"\nUSER: {req.message}")

    ctx = req.context or {}
    user_image = ctx.get("image")

    # Analyze image if provided
    image_description = None
    if user_image:
        print("[BLIP] Analyzing user image...")
        image_description = analyze_image(user_image)
        print(f"[BLIP] Result: {image_description}")

    ai = ask_model(req.message, image_description)
    print(f"AI: {ai}")

    intent = ai.get("intent", "chat")

    if intent == "search":
        query = ai.get("query", req.message)

        # Enhance search with image description keywords
        if image_description and image_description != "an image":
            desc_words = image_description.lower().split()
            for word in desc_words[:3]:
                if len(word) > 2 and word not in query.lower():
                    query += f" {word}"

        prods = await search_db(query)
        return {"success": True, "response": ai.get("response", "Found these!"), "products": prods, "action": None, "image_description": image_description}
    elif intent == "add_to_cart":
        return {"success": True, "response": ai.get("response", "Added!"), "products": None, "action": {"type": "add_to_cart", "product_index": ai.get("product_index", 1), "quantity": ai.get("quantity", 1)}, "image_description": image_description}
    elif intent == "view_cart":
        return {"success": True, "response": ai.get("response", "Checking cart!"), "products": None, "action": {"type": "view_cart"}, "image_description": image_description}
    elif intent == "checkout":
        return {"success": True, "response": ai.get("response", "Checking out!"), "products": None, "action": {"type": "checkout"}, "image_description": image_description}

    # Chat / general response
    response_text = ai.get("response", "How can I help?")
    return {"success": True, "response": response_text, "products": None, "action": None, "image_description": image_description}
