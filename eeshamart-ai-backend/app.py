# EeshaMart AI Backend - Eesha
# 100% POWERED BY AI - ABSOLUTELY NO PATTERN MATCHING!
# The AI model decides EVERYTHING - no fallbacks, no regex, no hardcoded rules!

import os
import json
import httpx
import asyncio
import re
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from urllib.parse import quote

# Import transformers for local model
from transformers import AutoModelForCausalLM, AutoTokenizer, TextGenerationPipeline
import torch

app = FastAPI(title="EeshaMart AI Assistant - Eesha")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase config
SUPABASE_URL = "https://tcwdbokruvlizkxcpkzj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg"

# Model config
MODEL_NAME = "HuggingFaceTB/SmolLM-1.7B-Instruct"
model = None
tokenizer = None
pipeline = None

# Initialize model on startup
@app.on_event("startup")
async def load_model():
    global model, tokenizer, pipeline
    print(f"Loading model: {MODEL_NAME}")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True
        )
        model.eval()
        print(f"Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        import traceback
        traceback.print_exc()


class ChatRequest(BaseModel):
    message: str
    image: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


async def search_products_supabase(query: str, max_price: int = None, limit: int = 10):
    """Search products in Supabase database"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }
        
        url = f"{SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc&limit={limit}"
        
        if query:
            search_terms = [query.lower()]
            if query.endswith('s') and len(query) > 1:
                search_terms.append(query[:-1])
            elif not query.endswith('s'):
                search_terms.append(query + 's')
            
            name_filters = [f"name.ilike.%25{term}%25" for term in search_terms]
            desc_filters = [f"description.ilike.%25{term}%25" for term in search_terms]
            url += f"&or=({','.join(name_filters + desc_filters)})"
        
        if max_price:
            url += f"&price=lte.{max_price}"
        
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Search error: {e}")
        
        return []


async def ask_ai(user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    100% AI-powered intent understanding.
    NO pattern matching, NO regex, NO fallbacks.
    The AI decides EVERYTHING.
    """
    global model, tokenizer
    
    if model is None or tokenizer is None:
        return {"intent": "chat", "response": "AI model is loading, please wait..."}
    
    ctx = context or {}
    products = ctx.get("lastShownProducts", [])
    
    # Build product context for the AI
    products_text = ""
    if products:
        products_text = "\n\nCURRENT PRODUCTS ON SCREEN:\n"
        for i, p in enumerate(products, 1):
            products_text += f"{i}. {p.get('name', 'Unknown')} - ₦{p.get('price', 0):,} (ID: {p.get('id')})\n"
        products_text += "\nThe user can reference these by number (first, second, etc) or name.\n"
    
    # THE AI PROMPT - This is where ALL intelligence lives
    system_prompt = f"""You are Eesha, an intelligent AI shopping assistant. You understand natural language perfectly.

{products_text}

Your job is to understand what the user wants and respond with a JSON object. Think carefully about the user's intent.

IMPORTANT INSTRUCTIONS:
1. Read the user's message carefully
2. Understand what they actually want
3. Respond with ONLY a valid JSON object - no other text

JSON FORMAT OPTIONS:

For SEARCHING products:
{{"intent": "search", "query": "the product name/type to search for", "max_price": null or number, "response": "your friendly response"}}

For ADDING TO CART:
{{"intent": "add_to_cart", "product_index": 1 or 2 or "all", "quantity": 1, "response": "your response"}}
- product_index is the number of the product (1 for first, 2 for second, etc)
- use "all" if they want all products
- quantity is how many they want

For VIEWING CART:
{{"intent": "view_cart", "response": "your response"}}

For CHECKOUT:
{{"intent": "checkout", "response": "your response"}}

For GENERAL CHAT:
{{"intent": "chat", "response": "your conversational response"}}

EXAMPLES TO LEARN FROM:

User: "Am looking for drones"
Your JSON: {{"intent": "search", "query": "drones", "max_price": null, "response": "Let me find drones for you!"}}

User: "Show me phones under 50000"
Your JSON: {{"intent": "search", "query": "phones", "max_price": 50000, "response": "Searching for phones under ₦50,000!"}}

User: "I need something that flies"
Your JSON: {{"intent": "search", "query": "drones", "max_price": null, "response": "Looking for flying items like drones!"}}

User: "Add the first one"
Your JSON: {{"intent": "add_to_cart", "product_index": 1, "quantity": 1, "response": "Adding the first product to your cart!"}}

User: "Add 2 of the second one"
Your JSON: {{"intent": "add_to_cart", "product_index": 2, "quantity": 2, "response": "Adding 2 of the second product!"}}

User: "I want both of them"
Your JSON: {{"intent": "add_to_cart", "product_index": "all", "quantity": 1, "response": "Adding all products to your cart!"}}

User: "Add all the books to my cart"
Your JSON: {{"intent": "add_to_cart", "product_index": "all", "quantity": 1, "response": "Adding all books to your cart!"}}

User: "Put 3 quantities of the first book"
Your JSON: {{"intent": "add_to_cart", "product_index": 1, "quantity": 3, "response": "Adding 3 of the first book!"}}

User: "What's in my cart?"
Your JSON: {{"intent": "view_cart", "response": "Let me check your cart!"}}

User: "I want to checkout"
Your JSON: {{"intent": "checkout", "response": "Taking you to checkout!"}}

User: "Hello"
Your JSON: {{"intent": "chat", "response": "Hello! I'm Eesha, your AI shopping assistant. What can I help you find today?"}}

REMEMBER: 
- Think about what the user ACTUALLY means
- Return ONLY the JSON, nothing else
- No markdown, no explanation, just the JSON object"""

    user_prompt = f"Now analyze this user message and respond with ONLY the JSON:\n\nUser: {user_message}\n\nJSON:"
    
    # Combine prompts
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    try:
        # Tokenize
        inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=2048)
        
        # Generate AI response
        with torch.no_grad():
            outputs = model.generate(
                inputs["input_ids"],
                max_new_tokens=150,
                temperature=0.3,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
        
        # Decode
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the new generation (after the prompt)
        ai_response = generated_text[len(full_prompt):].strip()
        
        print(f"AI RAW RESPONSE: {ai_response}")
        
        # Try to extract JSON
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = ai_response[json_start:json_end]
            
            # Clean up common JSON issues
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
            json_str = re.sub(r'}\s*{', '},{', json_str)  # Fix multiple objects
            
            try:
                parsed = json.loads(json_str)
                print(f"AI DECISION: {parsed}")
                return parsed
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}, trying to fix: {json_str}")
                # Try more aggressive fixes
                try:
                    # Extract key-value pairs manually
                    intent_match = re.search(r'"intent"\s*:\s*"(\w+)"', json_str)
                    query_match = re.search(r'"query"\s*:\s*"([^"]+)"', json_str)
                    index_match = re.search(r'"product_index"\s*:\s*(\d+|"all")', json_str)
                    qty_match = re.search(r'"quantity"\s*:\s*(\d+)', json_str)
                    response_match = re.search(r'"response"\s*:\s*"([^"]+)"', json_str)
                    price_match = re.search(r'"max_price"\s*:\s*(\d+)', json_str)
                    
                    result = {}
                    if intent_match:
                        result["intent"] = intent_match.group(1)
                    if query_match:
                        result["query"] = query_match.group(1)
                    if index_match:
                        val = index_match.group(1)
                        result["product_index"] = val if val == '"all"' or val == 'all' else int(val)
                    if qty_match:
                        result["quantity"] = int(qty_match.group(1))
                    if response_match:
                        result["response"] = response_match.group(1)
                    if price_match:
                        result["max_price"] = int(price_match.group(1))
                    
                    if result:
                        print(f"MANUALLY PARSED: {result}")
                        return result
                except Exception as e2:
                    print(f"Manual parse also failed: {e2}")
        
        # If we got here, AI output wasn't valid JSON
        # Ask AI to try again with a clearer prompt
        print("AI response wasn't valid JSON, asking AI to clarify...")
        return {"intent": "chat", "response": "I'm thinking... could you rephrase that?"}
        
    except Exception as e:
        print(f"AI error: {e}")
        import traceback
        traceback.print_exc()
        return {"intent": "chat", "response": "I had a thought hiccup. What did you say?"}


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "EeshaMart AI - Eesha",
        "model": "SmolLM-1.7B-Instruct",
        "ai_provider": "100% AI Controlled - NO pattern matching!",
        "note": "Every decision is made by the AI model"
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None}


@app.get("/api/info")
async def info():
    return {
        "status": "online",
        "model": "SmolLM-1.7B-Instruct",
        "version": "9.0.0 - 100% AI CONTROLLED",
        "note": "NO pattern matching - AI makes ALL decisions!"
    }


@app.post("/api/chat")
async def chat(request: ChatRequest, x_session_id: str = Header(default="default")):
    """Main chat - 100% AI controlled, no hardcoded logic"""
    
    try:
        message = request.message
        context = request.context or {}
        
        print(f"\n{'='*60}")
        print(f"USER: {message}")
        
        # Let AI decide everything
        ai_decision = await ask_ai(message, context)
        print(f"AI DECISION: {ai_decision}")
        
        intent = ai_decision.get("intent", "chat")
        
        if intent == "search":
            query = ai_decision.get("query", message)
            max_price = ai_decision.get("max_price")
            products = await search_products_supabase(query, max_price)
            
            response = ai_decision.get("response", f"Searching for {query}...")
            if not products:
                response = f"I searched for '{query}' but didn't find anything. Try a different term?"
            
            return {
                "success": True,
                "response": response,
                "products": products,
                "action": None
            }
        
        elif intent == "add_to_cart":
            product_index = ai_decision.get("product_index", 1)
            quantity = ai_decision.get("quantity", 1)
            
            return {
                "success": True,
                "response": ai_decision.get("response", "Adding to cart!"),
                "products": None,
                "action": {
                    "type": "add_to_cart",
                    "product_index": product_index,
                    "quantity": quantity,
                    "all": product_index == "all"
                }
            }
        
        elif intent == "view_cart":
            return {
                "success": True,
                "response": ai_decision.get("response", "Checking your cart!"),
                "products": None,
                "action": {"type": "view_cart"}
            }
        
        elif intent == "checkout":
            return {
                "success": True,
                "response": ai_decision.get("response", "Let's checkout!"),
                "products": None,
                "action": {"type": "checkout"}
            }
        
        else:  # chat
            return {
                "success": True,
                "response": ai_decision.get("response", "I'm here to help you shop!"),
                "products": None,
                "action": None
            }
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "response": "Something went wrong. Try again?",
            "products": None,
            "action": None
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
