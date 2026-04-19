# EeshaMart AI - Simple & Working
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import json
import re

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

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

# Load model
print("Loading Qwen2.5-1.5B-Instruct...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", torch_dtype=torch.float32, low_cpu_mem_usage=True)
model.eval()
print("Model ready!")

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

async def search_db(query: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc&limit=10"
        if query:
            url += f"&or=(name.ilike.%25{query}%25,description.ilike.%25{query}%25)"
        r = await client.get(url, headers={"apikey": SUPABASE_KEY})
        return r.json() if r.status_code == 200 else []

def ask_model(msg: str) -> dict:
    prompt = f"""You are Eesha, a shopping assistant. Return ONLY JSON.

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

User: {msg}
JSON:"""

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        out = model.generate(inputs["input_ids"], max_new_tokens=60, temperature=0.1, pad_token_id=tokenizer.eos_token_id)

    text = tokenizer.decode(out[0], skip_special_tokens=True)[len(prompt):]
    match = re.search(r'\{[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group().replace("'", '"'))
        except:
            pass
    return {"intent": "chat", "response": "Can you rephrase?"}

@app.get("/")
def home():
    return {"status": "online", "model": "Qwen2.5-1.5B-Instruct"}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    print(f"USER: {req.message}")
    ai = ask_model(req.message)
    print(f"AI: {ai}")

    intent = ai.get("intent", "chat")

    if intent == "search":
        prods = await search_db(ai.get("query", req.message))
        return {"success": True, "response": ai.get("response", "Found these!"), "products": prods, "action": None}
    elif intent == "add_to_cart":
        return {"success": True, "response": ai.get("response", "Added!"), "products": None, "action": {"type": "add_to_cart", "product_index": ai.get("product_index", 1), "quantity": ai.get("quantity", 1)}}
    elif intent == "view_cart":
        return {"success": True, "response": ai.get("response", "Checking cart!"), "products": None, "action": {"type": "view_cart"}}
    elif intent == "checkout":
        return {"success": True, "response": ai.get("response", "Checking out!"), "products": None, "action": {"type": "checkout"}}
    return {"success": True, "response": ai.get("response", "How can I help?"), "products": None, "action": None}
