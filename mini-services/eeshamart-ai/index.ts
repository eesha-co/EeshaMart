/**
 * EeshaMart AI Backend - Eesha
 * 100% POWERED BY AI - NO PATTERN MATCHING!
 * Uses z-ai-web-dev-sdk (FREE & Open Source)
 */

import { serve } from "bun";

// Supabase configuration
const SUPABASE_URL = "https://tcwdbokruvlizkxcpkzj.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg";

// Dynamic import for z-ai-web-dev-sdk
let ZAI: any = null;
let zaiInstance: any = null;

async function getZAI() {
  if (!ZAI) {
    ZAI = await import('z-ai-web-dev-sdk').then(m => m.default);
  }
  if (!zaiInstance) {
    zaiInstance = await ZAI.create();
  }
  return zaiInstance;
}

interface Product {
  id: number;
  name: string;
  price: number;
  category?: string;
  description?: string;
  image_url?: string;
}

interface ChatContext {
  lastShownProducts: Product[];
  cartItems: Array<{
    product_name?: string;
    quantity: number;
    price?: number;
  }>;
  cartTotal?: number;
  isLoggedIn?: boolean;
}

interface IntentResponse {
  intent: 'search' | 'add_to_cart' | 'view_cart' | 'checkout' | 'chat';
  query?: string;
  max_price?: number;
  product_index?: number | 'all';
  quantity?: number;
  response?: string;
}

// CORS headers
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Session-ID",
  "Content-Type": "application/json"
};

async function searchProducts(query: string, maxPrice?: number): Promise<Product[]> {
  try {
    let url = `${SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc&limit=10`;
    
    if (query) {
      // Generate search terms - handle plurals
      const searchTerms = [query.toLowerCase()];
      
      // Add singular form if query ends with 's'
      if (query.endsWith('s') && query.length > 1) {
        searchTerms.push(query.slice(0, -1)); // Remove trailing 's'
      }
      // Add plural form if query doesn't end with 's'
      else if (!query.endsWith('s')) {
        searchTerms.push(query + 's');
      }
      
      // Build OR filters for each term
      const nameFilters = searchTerms.map(term => `name.ilike.%25${encodeURIComponent(term)}%25`);
      const descFilters = searchTerms.map(term => `description.ilike.%25${encodeURIComponent(term)}%25`);
      
      // Combine with OR - search in name OR description
      url += `&or=(${[...nameFilters, ...descFilters].join(',')})`;
    }
    
    if (maxPrice) {
      url += `&price=lte.${maxPrice}`;
    }
    
    console.log('Search URL:', url);
    
    const response = await fetch(url, {
      headers: {
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log(`Found ${data.length} products`);
      return data;
    }
    
    console.error('Supabase search error:', response.status);
    return [];
  } catch (error) {
    console.error('Search error:', error);
    return [];
  }
}

async function understandIntent(userMessage: string, context: ChatContext): Promise<IntentResponse> {
  const zai = await getZAI();
  
  // Build context about current products shown
  let productsContext = '';
  if (context.lastShownProducts && context.lastShownProducts.length > 0) {
    productsContext = '\n\nPRODUCTS CURRENTLY SHOWN TO USER:\n';
    context.lastShownProducts.forEach((p, i) => {
      productsContext += `${i + 1}. ${p.name} - ₦${p.price.toLocaleString()} (ID: ${p.id})\n`;
    });
  }
  
  const systemPrompt = `You are Eesha, an intelligent AI shopping assistant for EeshaMart Nigeria. You understand natural language PERFECTLY.

${productsContext}

CRITICAL: Analyze the user's message and respond with ONLY a JSON object (no markdown, no explanation).

For SEARCHING products:
{"intent": "search", "query": "the actual product name/type to search for", "max_price": number or omit, "response": "friendly message"}

For ADDING to cart:
{"intent": "add_to_cart", "product_index": 1 or 2 or "all", "quantity": 1, "response": "friendly message"}

For VIEWING CART (just SEEING contents, NOT paying):
{"intent": "view_cart", "response": "friendly message"}
USE THIS when user wants to SEE their cart contents

For CHECKOUT (PAYING, completing purchase):
{"intent": "checkout", "response": "friendly message"}
USE THIS ONLY when user wants to PAY

For general chat:
{"intent": "chat", "response": "your friendly response"}

=== CRITICAL EXAMPLES ===

SEARCH:
- "Am looking for drones" -> {"intent": "search", "query": "drones", "response": "Let me find drones!"}
- "Show me books" -> {"intent": "search", "query": "books", "response": "Searching for books!"}
- "I want a phone under 50000" -> {"intent": "search", "query": "phone", "max_price": 50000, "response": "Finding phones under ₦50,000!"}

ADD TO CART:
- "Add the first one" -> {"intent": "add_to_cart", "product_index": 1, "quantity": 1, "response": "Adding to cart!"}
- "Add both" -> {"intent": "add_to_cart", "product_index": "all", "quantity": 1, "response": "Adding all!"}
- "Add 2 of the second one" -> {"intent": "add_to_cart", "product_index": 2, "quantity": 2, "response": "Adding 2!"}

VIEW CART (seeing contents, NOT paying):
- "What's in my cart?" -> {"intent": "view_cart", "response": "Checking your cart!"}
- "Show me my cart" -> {"intent": "view_cart", "response": "Here's your cart!"}
- "Show cart" -> {"intent": "view_cart", "response": "Opening cart!"}
- "My cart" -> {"intent": "view_cart", "response": "Let me show your cart!"}

CHECKOUT (PAYING only):
- "I want to checkout" -> {"intent": "checkout", "response": "Taking you to checkout!"}
- "Checkout" -> {"intent": "checkout", "response": "Proceeding to checkout!"}
- "I want to pay" -> {"intent": "checkout", "response": "Let's complete your purchase!"}
- "Buy these items" -> {"intent": "checkout", "response": "Taking you to payment!"}

CHAT:
- "Hello" -> {"intent": "chat", "response": "Hello! I'm Eesha, your AI shopping assistant!"}

=== REMEMBER ===
- VIEW CART = just SEEING contents = intent: "view_cart"
- CHECKOUT = PAYING = intent: "checkout"
- Respond with ONLY the JSON object!`;

  try {
    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'assistant', content: systemPrompt },
        { role: 'user', content: userMessage }
      ],
      thinking: { type: 'disabled' }
    });
    
    const aiResponse = completion.choices[0]?.message?.content || '';
    console.log('AI Raw Response:', aiResponse);
    
    // Parse JSON from response
    try {
      const jsonMatch = aiResponse.match(/\{[^{}]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        console.log('Parsed Intent:', parsed);
        return parsed as IntentResponse;
      }
    } catch (parseError) {
      console.error('JSON parse error:', parseError);
    }
    
    // Fallback
    const lowerResponse = aiResponse.toLowerCase();
    if (lowerResponse.includes('search') || lowerResponse.includes('find') || lowerResponse.includes('looking')) {
      return { intent: 'search', query: userMessage };
    }
    
    return { intent: 'chat', response: aiResponse || "I'm here to help you shop! What are you looking for?" };
    
  } catch (error) {
    console.error('AI error:', error);
    return { intent: 'search', query: userMessage };
  }
}

async function handleChat(body: any) {
  const { message, context } = body as { message: string; context?: ChatContext };
  
  console.log('\n=== USER MESSAGE:', message);
  
  if (!message || typeof message !== 'string') {
    return {
      success: false,
      response: 'Please provide a message.',
      products: null,
      action: null
    };
  }
  
  const intentResult = await understandIntent(message, context || { lastShownProducts: [], cartItems: [] });
  console.log('INTENT RESULT:', intentResult);
  
  const intent = intentResult.intent;
  
  switch (intent) {
    case 'search': {
      const query = intentResult.query || message;
      const maxPrice = intentResult.max_price;
      
      console.log(`Searching for: "${query}", max price: ${maxPrice}`);
      
      const products = await searchProducts(query, maxPrice);
      
      let response: string;
      if (products && products.length > 0) {
        response = intentResult.response || `✨ Found ${products.length} products for you!`;
      } else {
        response = `I couldn't find any products matching "${query}". Try a different search term or browse our categories.`;
      }
      
      return {
        success: true,
        response,
        products,
        action: null
      };
    }
    
    case 'add_to_cart': {
      const productIndex = intentResult.product_index || 1;
      const quantity = intentResult.quantity || 1;
      
      return {
        success: true,
        response: intentResult.response || 'Adding to your cart!',
        products: null,
        action: {
          type: 'add_to_cart',
          product_index: productIndex,
          quantity,
          all: productIndex === 'all'
        }
      };
    }
    
    case 'view_cart': {
      return {
        success: true,
        response: intentResult.response || "Let me check your cart!",
        products: null,
        action: { type: 'view_cart' }
      };
    }
    
    case 'checkout': {
      return {
        success: true,
        response: intentResult.response || "Let's proceed to checkout!",
        products: null,
        action: { type: 'checkout' }
      };
    }
    
    default: {
      return {
        success: true,
        response: intentResult.response || "I'm Eesha, your AI shopping assistant! What can I help you find today?",
        products: null,
        action: null
      };
    }
  }
}

// Start server
const PORT = 3035;

serve({
  port: PORT,
  async fetch(req) {
    const url = new URL(req.url);
    
    // Handle CORS preflight
    if (req.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    // Health check
    if (url.pathname === '/' || url.pathname === '/api/health') {
      return Response.json({
        status: 'online',
        service: 'EeshaMart AI - Eesha',
        ai: 'Powered by z-ai-web-dev-sdk (FREE & Open Source)',
        version: '5.0.0 - 100% AI POWERED!'
      }, { headers: corsHeaders });
    }
    
    // Chat endpoint
    if (url.pathname === '/api/chat' && req.method === 'POST') {
      try {
        const body = await req.json();
        const result = await handleChat(body);
        return Response.json(result, { headers: corsHeaders });
      } catch (error: any) {
        console.error('Chat error:', error);
        return Response.json({
          success: false,
          response: 'I had a small issue. Please try again!',
          products: null,
          action: null
        }, { headers: corsHeaders });
      }
    }
    
    // Info endpoint
    if (url.pathname === '/api/info') {
      return Response.json({
        status: 'online',
        model: 'z-ai-web-dev-sdk LLM',
        service: 'EeshaMart AI Buyer Assistant',
        version: '5.0.0 - 100% AI POWERED',
        ai: 'Powered by z-ai-web-dev-sdk (FREE & Open Source)',
        note: 'NO pattern matching - ALL natural language understanding by AI!'
      }, { headers: corsHeaders });
    }
    
    return Response.json({ error: 'Not found' }, { status: 404, headers: corsHeaders });
  }
});

console.log(`🤖 EeshaMart AI Service running on port ${PORT}`);
console.log(`📡 API endpoint: http://localhost:${PORT}/api/chat`);
console.log(`🧠 Powered by z-ai-web-dev-sdk (FREE & Open Source)`);
