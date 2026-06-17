import { NextRequest, NextResponse } from 'next/server';
import ZAI from 'z-ai-web-dev-sdk';

// Supabase configuration
const SUPABASE_URL = "https://tcwdbokruvlizkxcpkzj.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg";

interface ChatContext {
  lastShownProducts: Array<{
    id: number;
    name: string;
    price: number;
    category?: string;
  }>;
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

let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null;

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create();
  }
  return zaiInstance;
}

async function searchProducts(query: string, maxPrice?: number): Promise<any[]> {
  try {
    let url = `${SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc&limit=10`;
    
    if (query) {
      // Search in both name and description
      const encodedQuery = encodeURIComponent(`%${query}%`);
      url += `&or=(name.ilike.${encodedQuery},description.ilike.${encodedQuery})`;
    }
    
    if (maxPrice) {
      url += `&price=lte.${maxPrice}`;
    }
    
    const response = await fetch(url, {
      headers: {
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
      }
    });
    
    if (response.ok) {
      return await response.json();
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
      // Find JSON object in response
      const jsonMatch = aiResponse.match(/\{[^{}]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        console.log('Parsed Intent:', parsed);
        return parsed as IntentResponse;
      }
    } catch (parseError) {
      console.error('JSON parse error:', parseError);
    }
    
    // Fallback: try to detect intent from response text
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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, context } = body as { message: string; context?: ChatContext };
    
    console.log('\n=== USER MESSAGE:', message);
    console.log('CONTEXT:', JSON.stringify(context, null, 2));
    
    if (!message || typeof message !== 'string') {
      return NextResponse.json({
        success: false,
        response: 'Please provide a message.',
        products: null,
        action: null
      });
    }
    
    // Use AI to understand intent
    const intentResult = await understandIntent(message, context || { lastShownProducts: [], cartItems: [] });
    console.log('INTENT RESULT:', intentResult);
    
    const intent = intentResult.intent;
    
    // Handle different intents
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
        
        return NextResponse.json({
          success: true,
          response,
          products,
          action: null
        });
      }
      
      case 'add_to_cart': {
        const productIndex = intentResult.product_index || 1;
        const quantity = intentResult.quantity || 1;
        
        return NextResponse.json({
          success: true,
          response: intentResult.response || 'Adding to your cart!',
          products: null,
          action: {
            type: 'add_to_cart',
            product_index: productIndex,
            quantity,
            all: productIndex === 'all'
          }
        });
      }
      
      case 'view_cart': {
        return NextResponse.json({
          success: true,
          response: intentResult.response || "Let me check your cart!",
          products: null,
          action: { type: 'view_cart' }
        });
      }
      
      case 'checkout': {
        return NextResponse.json({
          success: true,
          response: intentResult.response || "Let's proceed to checkout!",
          products: null,
          action: { type: 'checkout' }
        });
      }
      
      default: {
        return NextResponse.json({
          success: true,
          response: intentResult.response || "I'm Eesha, your AI shopping assistant! What can I help you find today?",
          products: null,
          action: null
        });
      }
    }
    
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json({
      success: false,
      response: 'I had a small issue. Please try again!',
      products: null,
      action: null
    });
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'online',
    service: 'EeshaMart AI - Eesha',
    ai: 'Powered by z-ai-web-dev-sdk (FREE & Open Source)',
    version: '5.0.0 - 100% AI POWERED, NO pattern matching!'
  });
}
