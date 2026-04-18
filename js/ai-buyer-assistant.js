/**
 * EeshaMart AI Buyer Assistant - "Eesha"
 * FREE & OPEN SOURCE - No API keys required!
 * 
 * The AI backend handles natural language understanding
 * Frontend just sends context and executes actions
 */

(function() {
    'use strict';

    const CONFIG = {
        // Use HuggingFace Space AI (FREE, live, and working!)
        apiUrl: 'https://fuhaddesmond-eeshamart-ai.hf.space/api/chat',
        sessionKey: 'eeshamart_ai_session',
        debug: true
    };

    // State
    let isOpen = false;
    let isLoading = false;
    let conversationHistory = [];
    let sessionId = localStorage.getItem(CONFIG.sessionKey) || `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    let container = null;
    let selectedImage = null;
    let context = {
        lastShownProducts: [],
        cartItems: [],
        user: null
    };

    const CATEGORIES = [
        { name: 'Electronics', icon: 'fa-laptop', query: 'Show me electronics' },
        { name: 'Fashion', icon: 'fa-tshirt', query: 'Show me fashion' },
        { name: 'Home', icon: 'fa-couch', query: 'Show me home products' },
        { name: 'Beauty', icon: 'fa-spa', query: 'Show me beauty products' },
        { name: 'Sports', icon: 'fa-futbol', query: 'Show me sports gear' },
        { name: 'Books', icon: 'fa-book', query: 'Show me books' }
    ];

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        setTimeout(createWidget, 500);
    }

    function createWidget() {
        container = document.createElement('div');
        container.id = 'ai-buyer-assistant';
        container.innerHTML = getWidgetHTML();
        document.body.appendChild(container);

        document.getElementById('ai-toggle-btn').addEventListener('click', toggleWidget);
        document.getElementById('ai-close-btn')?.addEventListener('click', toggleWidget);
        document.getElementById('ai-send-btn').addEventListener('click', sendMessage);
        document.getElementById('ai-input').addEventListener('keypress', handleKeyPress);
        document.getElementById('ai-file-input').addEventListener('change', handleFileSelect);
        document.getElementById('ai-clear-btn')?.addEventListener('click', clearConversation);

        container.querySelectorAll('.ai-category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('ai-input').value = btn.dataset.query;
                sendMessage();
            });
        });

        document.getElementById('ai-remove-image')?.addEventListener('click', removeSelectedImage);
    }

    function getWidgetHTML() {
        return `
            <style>${getWidgetStyles()}</style>
            
            <button id="ai-toggle-btn" class="ai-toggle-btn" title="Open AI Shopping Assistant">
                <i class="fas fa-wand-magic-sparkles"></i>
                <span class="ai-pulse"></span>
            </button>

            <div id="ai-widget" class="ai-widget ai-hidden">
                <div class="ai-header">
                    <div class="ai-header-left">
                        <div class="ai-logo"><i class="fas fa-wand-magic-sparkles"></i></div>
                        <div class="ai-header-info">
                            <h3>Eesha AI</h3>
                            <span class="ai-status">
                                <span class="ai-status-dot"></span>
                                <span id="ai-status-text">FREE & Open Source</span>
                            </span>
                        </div>
                    </div>
                    <div class="ai-header-actions">
                        <button id="ai-clear-btn" class="ai-header-btn" title="Clear"><i class="fas fa-refresh"></i></button>
                        <button id="ai-close-btn" class="ai-header-btn" title="Close"><i class="fas fa-times"></i></button>
                    </div>
                </div>

                <div id="ai-messages" class="ai-messages"></div>

                <div id="ai-image-preview" class="ai-image-preview ai-hidden">
                    <div class="ai-preview-container">
                        <img id="ai-preview-img" src="" alt="Preview">
                        <button id="ai-remove-image" class="ai-remove-image"><i class="fas fa-times"></i></button>
                    </div>
                </div>

                <div id="ai-quick-actions" class="ai-quick-actions">
                    <p class="ai-quick-title">Try these:</p>
                    <div class="ai-categories">
                        ${CATEGORIES.map(cat => `
                            <button class="ai-category-btn" data-query="${cat.query}">
                                <i class="fas ${cat.icon}"></i> ${cat.name}
                            </button>
                        `).join('')}
                    </div>
                </div>

                <div class="ai-input-area">
                    <div class="ai-input-container">
                        <input type="file" id="ai-file-input" accept="image/*" hidden>
                        <button id="ai-upload-btn" class="ai-upload-btn" onclick="document.getElementById('ai-file-input').click()">
                            <i class="fas fa-camera"></i>
                        </button>
                        <input type="text" id="ai-input" placeholder="Tell me what you need..." autocomplete="off">
                        <button id="ai-send-btn" class="ai-send-btn"><i class="fas fa-paper-plane"></i></button>
                    </div>
                </div>
            </div>
        `;
    }

    function getWidgetStyles() {
        return `
            .ai-toggle-btn{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#f59e0b);border:none;cursor:pointer;box-shadow:0 4px 20px rgba(245,158,11,0.4);z-index:9998;display:flex;align-items:center;justify-content:center;transition:all .3s;color:#0f172a;font-size:22px}
            .ai-toggle-btn:hover{transform:scale(1.1);box-shadow:0 6px 30px rgba(245,158,11,0.5)}
            .ai-pulse{position:absolute;top:-2px;right:-2px;width:14px;height:14px;background:#22c55e;border-radius:50%;border:2px solid white;animation:pulse 2s infinite}
            @keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.2);opacity:.7}}
            .ai-widget{position:fixed;bottom:96px;right:24px;width:380px;max-width:calc(100vw - 48px);height:560px;max-height:calc(100vh - 140px);background:white;border-radius:16px;box-shadow:0 10px 50px rgba(0,0,0,.15);z-index:9999;display:flex;flex-direction:column;overflow:hidden;transition:all .3s;font-family:'Plus Jakarta Sans',system-ui,sans-serif}
            .ai-hidden{transform:translateY(20px);opacity:0;pointer-events:none}
            .ai-header{background:linear-gradient(135deg,#0f172a,#1e293b);color:white;padding:14px 18px;display:flex;align-items:center;justify-content:space-between}
            .ai-header-left{display:flex;align-items:center;gap:10px}
            .ai-logo{width:36px;height:36px;background:linear-gradient(135deg,#fbbf24,#f59e0b);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:16px;color:#0f172a}
            .ai-header-info h3{margin:0;font-size:16px;font-weight:700}
            .ai-status{display:flex;align-items:center;gap:5px;font-size:11px;opacity:.8}
            .ai-status-dot{width:6px;height:6px;background:#22c55e;border-radius:50%}
            .ai-header-actions{display:flex;gap:6px}
            .ai-header-btn{width:28px;height:28px;border-radius:6px;border:none;background:rgba(255,255,255,.1);color:white;cursor:pointer;font-size:12px}
            .ai-header-btn:hover{background:rgba(255,255,255,.2)}
            .ai-messages{flex:1;overflow-y:auto;padding:16px;background:#f8fafc}
            .ai-message{display:flex;gap:10px;margin-bottom:14px;animation:fadeIn .3s}
            @keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
            .ai-message-user{flex-direction:row-reverse}
            .ai-avatar{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:13px}
            .ai-avatar-assistant{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a}
            .ai-avatar-user{background:#0f172a;color:#fbbf24}
            .ai-bubble{max-width:260px;padding:10px 14px;border-radius:14px;font-size:13px;line-height:1.5}
            .ai-bubble-assistant{background:white;color:#1e293b;border-bottom-left-radius:4px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
            .ai-bubble-user{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a;border-bottom-right-radius:4px}
            .ai-bubble strong{font-weight:600}
            .ai-message-image{margin-bottom:8px}
            .ai-message-image img{max-width:200px;max-height:150px;border-radius:8px;object-fit:cover;box-shadow:0 2px 8px rgba(0,0,0,.1)}
            .ai-product-card{background:white;border-radius:10px;padding:10px;margin-top:10px;box-shadow:0 2px 8px rgba(0,0,0,.06);display:flex;gap:10px;cursor:pointer;transition:all .2s;border:2px solid transparent}
            .ai-product-card:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1);border-color:#f59e0b}
            .ai-product-img{width:50px;height:50px;border-radius:6px;object-fit:cover;background:#f1f5f9}
            .ai-product-info{flex:1;min-width:0}
            .ai-product-name{font-weight:600;font-size:12px;margin-bottom:2px;color:#1e293b}
            .ai-product-price{color:#d97706;font-weight:700;font-size:13px}
            .ai-product-meta{font-size:10px;color:#64748b;margin-top:2px}
            .ai-product-actions{display:flex;gap:4px;margin-top:6px}
            .ai-action-btn{padding:4px 8px;border-radius:4px;border:none;font-size:10px;font-weight:600;cursor:pointer}
            .ai-action-btn-primary{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a}
            .ai-action-btn-secondary{background:#f1f5f9;color:#475569}
            .ai-action-btn:hover{transform:scale(1.05)}
            .ai-action-result{display:flex;align-items:center;gap:6px;padding:8px 12px;background:#f0fdf4;border-radius:8px;margin-top:8px;font-size:12px;color:#166534;border:1px solid #bbf7d0}
            .ai-action-result.error{background:#fef2f2;color:#991b1b;border-color:#fecaca}
            .ai-action-result.warning{background:#fffbeb;color:#92400e;border-color:#fde68a}
            .ai-quick-actions{padding:10px 16px;border-top:1px solid #e2e8f0;background:white}
            .ai-quick-title{font-size:11px;color:#64748b;margin:0 0 6px 0}
            .ai-categories{display:flex;gap:6px;flex-wrap:wrap}
            .ai-category-btn{display:flex;align-items:center;gap:4px;padding:5px 10px;border-radius:16px;border:1px solid #e2e8f0;background:white;font-size:11px;cursor:pointer;color:#475569}
            .ai-category-btn:hover{border-color:#f59e0b;background:#fffbeb;color:#b45309}
            .ai-image-preview{padding:10px 16px;background:#f8fafc;border-top:1px solid #e2e8f0}
            .ai-preview-container{position:relative;display:inline-block}
            .ai-preview-container img{max-width:80px;max-height:80px;border-radius:6px;object-fit:cover}
            .ai-remove-image{position:absolute;top:-6px;right:-6px;width:20px;height:20px;border-radius:50%;border:none;background:#ef4444;color:white;cursor:pointer;font-size:10px}
            .ai-input-area{padding:10px 16px;background:white;border-top:1px solid #e2e8f0}
            .ai-input-container{display:flex;gap:6px;align-items:center;background:#f1f5f9;border-radius:20px;padding:4px}
            .ai-upload-btn{width:36px;height:36px;border-radius:50%;border:none;background:transparent;color:#64748b;cursor:pointer}
            .ai-upload-btn:hover{background:#e2e8f0;color:#f59e0b}
            #ai-input{flex:1;border:none;background:transparent;padding:6px;font-size:13px;outline:none}
            .ai-send-btn{width:36px;height:36px;border-radius:50%;border:none;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#0f172a;cursor:pointer}
            .ai-send-btn:hover{transform:scale(1.05)}
            .ai-loading{display:flex;gap:4px;padding:12px}
            .ai-loading span{width:6px;height:6px;background:#f59e0b;border-radius:50%;animation:bounce 1.4s infinite}
            .ai-loading span:nth-child(1){animation-delay:-.32s}
            .ai-loading span:nth-child(2){animation-delay:-.16s}
            @keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
            @media(max-width:480px){.ai-widget{bottom:0;right:0;width:100%;height:100%;max-height:100%;border-radius:0}.ai-toggle-btn{bottom:80px}}
        `;
    }

    function toggleWidget() {
        isOpen = !isOpen;
        const widget = document.getElementById('ai-widget');
        const toggleBtn = document.getElementById('ai-toggle-btn');
        
        if (isOpen) {
            widget.classList.remove('ai-hidden');
            toggleBtn.style.display = 'none';
            document.getElementById('ai-input').focus();
            if (conversationHistory.length === 0) showWelcomeMessage();
        } else {
            widget.classList.add('ai-hidden');
            toggleBtn.style.display = 'flex';
        }
    }

    function showWelcomeMessage() {
        addMessage('assistant', `<strong>👋 Hi! I'm Eesha, your AI shopping assistant!</strong><br><br>
I can help you with:<br>
• Finding products within your budget<br>
• Planning your shopping list<br>
• Answering any questions<br><br>
Just talk to me naturally!<br>
<strong>100% FREE & Open Source!</strong>`);
    }

    function addMessage(role, content, data = {}) {
        const messagesContainer = document.getElementById('ai-messages');
        const isUser = role === 'user';
        const parsed = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
        
        // Build image HTML if provided
        let imageHtml = '';
        if (data.image) {
            imageHtml = `<div class="ai-message-image"><img src="${data.image}" alt="Shared image"></div>`;
        }
        
        let html = `
            <div class="ai-message ${isUser ? 'ai-message-user' : ''}">
                <div class="ai-avatar ${isUser ? 'ai-avatar-user' : 'ai-avatar-assistant'}">
                    <i class="fas ${isUser ? 'fa-user' : 'fa-wand-magic-sparkles'}"></i>
                </div>
                <div class="ai-message-content">
                    ${imageHtml}
                    <div class="ai-bubble ${isUser ? 'ai-bubble-user' : 'ai-bubble-assistant'}">${parsed}</div>
                    ${renderProducts(data.products)}
                    ${renderActionResult(data.actionResult)}
                </div>
            </div>`;
        
        messagesContainer.insertAdjacentHTML('beforeend', html);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        addProductHandlers();
        
        if (conversationHistory.length > 0 || role === 'user') {
            document.getElementById('ai-quick-actions').style.display = 'none';
        }
    }

    function renderProducts(products) {
        if (!products || products.length === 0) return '';
        return products.slice(0, 5).map((p, i) => `
            <div class="ai-product-card" data-product-id="${p.id}" data-index="${i + 1}">
                <img src="${p.image_url || 'https://via.placeholder.com/50'}" class="ai-product-img">
                <div class="ai-product-info">
                    <div class="ai-product-name">${i + 1}. ${p.name}</div>
                    <div class="ai-product-price">₦${(p.price || 0).toLocaleString()}</div>
                    <div class="ai-product-meta">${p.category || ''}</div>
                    <div class="ai-product-actions">
                        <button class="ai-action-btn ai-action-btn-primary" data-action="add" data-product-id="${p.id}"><i class="fas fa-cart-plus"></i> Add</button>
                        <button class="ai-action-btn ai-action-btn-secondary" data-action="view" data-product-id="${p.id}"><i class="fas fa-eye"></i> View</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    function renderActionResult(result) {
        if (!result) return '';
        const cls = result.success ? '' : (result.requiresAuth ? 'warning' : 'error');
        const icon = result.success ? 'fa-check-circle' : (result.requiresAuth ? 'fa-exclamation-triangle' : 'fa-times-circle');
        return `<div class="ai-action-result ${cls}"><i class="fas ${icon}"></i> ${result.message}</div>`;
    }

    function addProductHandlers() {
        const container = document.getElementById('ai-messages');
        
        container.querySelectorAll('.ai-product-card:not([data-handled])').forEach(card => {
            card.setAttribute('data-handled', 'true');
            card.addEventListener('click', e => {
                if (!e.target.closest('.ai-action-btn')) {
                    window.location.href = `/Eesha buying folder/product.html?id=${card.dataset.productId}`;
                }
            });
        });

        container.querySelectorAll('.ai-action-btn:not([data-handled])').forEach(btn => {
            btn.setAttribute('data-handled', 'true');
            btn.addEventListener('click', async e => {
                e.stopPropagation();
                const action = btn.dataset.action;
                const productId = parseInt(btn.dataset.productId);
                
                if (action === 'add') {
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    const result = await window.Cart?.addToCart(productId, 1);
                    
                    if (result?.success) {
                        btn.innerHTML = '<i class="fas fa-check"></i> Added';
                        btn.classList.remove('ai-action-btn-primary');
                        btn.classList.add('ai-action-btn-secondary');
                    } else {
                        btn.innerHTML = '<i class="fas fa-cart-plus"></i> Add';
                        if (result?.requiresAuth) {
                            addMessage('assistant', 'Please <a href="/Eesha buying folder/login.html" style="color:#f59e0b;font-weight:600;">login</a> to add items.');
                        }
                    }
                } else if (action === 'view') {
                    window.location.href = `/Eesha buying folder/product.html?id=${productId}`;
                }
            });
        });
    }

    function addLoading() {
        const c = document.getElementById('ai-messages');
        c.insertAdjacentHTML('beforeend', `<div class="ai-message" id="ai-loading-msg">
            <div class="ai-avatar ai-avatar-assistant"><i class="fas fa-wand-magic-sparkles"></i></div>
            <div class="ai-bubble ai-bubble-assistant"><div class="ai-loading"><span></span><span></span><span></span></div></div>
        </div>`);
        c.scrollTop = c.scrollHeight;
    }

    function removeLoading() {
        document.getElementById('ai-loading-msg')?.remove();
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file?.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = ev => {
            selectedImage = ev.target.result;
            document.getElementById('ai-preview-img').src = selectedImage;
            document.getElementById('ai-image-preview').classList.remove('ai-hidden');
        };
        reader.readAsDataURL(file);
        e.target.value = '';
    }

    function removeSelectedImage() {
        selectedImage = null;
        document.getElementById('ai-image-preview').classList.add('ai-hidden');
    }

    function handleKeyPress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }

    async function updateContext() {
        try {
            console.log('[Eesha AI] Checking login status...');
            console.log('[Eesha AI] window.Cart exists:', !!window.Cart);
            console.log('[Eesha AI] window.supabaseClient exists:', !!window.supabaseClient);
            console.log('[Eesha AI] window.supabase exists:', !!window.supabase);
            
            // Check if Cart module exists
            if (!window.Cart) {
                console.error('[Eesha AI] Cart module not loaded!');
                // Try to wait a bit and check again
                await new Promise(resolve => setTimeout(resolve, 500));
                if (!window.Cart) {
                    console.error('[Eesha AI] Cart module still not loaded after waiting');
                    context.user = null;
                    context.cartItems = [];
                    return;
                }
            }
            
            context.user = await window.Cart.getCurrentUser();
            console.log('[Eesha AI] User object:', context.user ? `ID: ${context.user.id}` : 'null');
            
            if (context.user) {
                console.log('[Eesha AI] Fetching cart items for user...');
                const items = await window.Cart.getCartItems();
                context.cartItems = items || [];
                console.log('[Eesha AI] Cart items fetched:', context.cartItems.length);
                console.log('[Eesha AI] Cart items raw:', JSON.stringify(context.cartItems, null, 2));
            } else {
                context.cartItems = [];
                console.log('[Eesha AI] No user logged in - cart empty');
                
                // Try to get session directly from supabase as fallback
                const client = window.supabaseClient || window.supabase;
                if (client) {
                    const { data: { session } } = await client.auth.getSession();
                    console.log('[Eesha AI] Direct supabase session check:', session ? `User: ${session.user?.id}` : 'No session');
                }
            }
        } catch (e) {
            console.error('[Eesha AI] Error updating context:', e);
            console.error('[Eesha AI] Error stack:', e.stack);
        }
    }

    async function sendMessage() {
        const input = document.getElementById('ai-input');
        const text = input.value.trim();
        if ((!text && !selectedImage) || isLoading) return;

        // DEBUG COMMAND - Type "debug" to see cart status
        if (text.toLowerCase() === 'debug' || text.toLowerCase() === '/debug') {
            addMessage('user', text);
            input.value = '';
            
            let debugInfo = '🔧 **DEBUG INFO:**\n\n';
            debugInfo += `• window.Cart: ${window.Cart ? '✅ Loaded' : '❌ NOT LOADED'}\n`;
            debugInfo += `• window.supabase: ${window.supabase ? '✅ Loaded' : '❌ NOT LOADED'}\n`;
            debugInfo += `• window.supabaseClient: ${window.supabaseClient ? '✅ Loaded' : '❌ NOT LOADED'}\n`;
            
            if (window.Cart) {
                try {
                    const user = await window.Cart.getCurrentUser();
                    debugInfo += `\n**Login Status:**\n`;
                    debugInfo += `• Logged in: ${user ? '✅ YES' : '❌ NO'}\n`;
                    if (user) {
                        debugInfo += `• User ID: ${user.id}\n`;
                    }
                    
                    const items = await window.Cart.getCartItems();
                    debugInfo += `\n**Cart Data:**\n`;
                    debugInfo += `• Items count: ${items ? items.length : 0}\n`;
                    if (items && items.length > 0) {
                        debugInfo += `• Items:\n`;
                        items.forEach((item, i) => {
                            debugInfo += `  ${i+1}. ${item.products?.name || 'Unknown'} x${item.quantity}\n`;
                        });
                    }
                    
                    const count = await window.Cart.getCartCount();
                    debugInfo += `• Cart count badge: ${count}\n`;
                } catch (e) {
                    debugInfo += `\n❌ Error: ${e.message}\n`;
                }
            }
            
            // Check supabase directly
            const client = window.supabaseClient || window.supabase;
            if (client) {
                try {
                    const { data: { session } } = await client.auth.getSession();
                    debugInfo += `\n**Direct Supabase Check:**\n`;
                    debugInfo += `• Has session: ${session ? '✅ YES' : '❌ NO'}\n`;
                    if (session) {
                        debugInfo += `• User ID: ${session.user?.id}\n`;
                    }
                } catch (e) {
                    debugInfo += `\n❌ Supabase error: ${e.message}\n`;
                }
            }
            
            addMessage('assistant', debugInfo);
            return;
        }

        // Store image before clearing
        const imageToSend = selectedImage;
        
        // Show user message with image if provided (handle image-only messages)
        const displayText = text || '📷 Shared an image';
        addMessage('user', displayText, { image: imageToSend });
        input.value = '';
        removeSelectedImage();

        isLoading = true;
        addLoading();

        try {
            await updateContext();

            const contextForAI = {
                lastShownProducts: context.lastShownProducts.map(p => ({
                    id: p.id, name: p.name, price: p.price, category: p.category
                })),
                cartItems: context.cartItems.map(i => ({
                    product_name: i.products?.name || i.product_name || 'Unknown', 
                    quantity: i.quantity || 1, 
                    price: i.products?.price || i.price || 0
                })),
                cartTotal: context.cartItems.reduce((s, i) => s + ((i.products?.price || i.price || 0) * (i.quantity || 1)), 0),
                isLoggedIn: !!context.user,
                // Add conversation history for memory
                conversationHistory: conversationHistory.slice(-10) // Last 10 messages
            };

            // Add image if selected (for VLM)
            if (imageToSend) {
                contextForAI.image = imageToSend;
            }

            // Call HuggingFace Space AI
            const response = await fetch(CONFIG.apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, context: contextForAI })
            });
            const data = await response.json();
            if (CONFIG.debug) console.log('HF Space AI response:', data);

            removeLoading();

            if (data.success) {
                // Store in conversation history
                conversationHistory.push({ role: 'user', content: text });
                conversationHistory.push({ role: 'assistant', content: data.response });
                
                // Keep only last 20 messages (10 exchanges)
                if (conversationHistory.length > 20) {
                    conversationHistory = conversationHistory.slice(-20);
                }

                if (data.products?.length > 0) {
                    context.lastShownProducts = data.products;
                }

                let actionResult = null;
                if (data.action) {
                    actionResult = await executeAction(data.action, data);
                }

                addMessage('assistant', data.response, { products: data.products, actionResult });
            } else {
                addMessage('assistant', data.response || 'Sorry, an error occurred.');
            }
        } catch (error) {
            console.error('Error:', error);
            removeLoading();
            addMessage('assistant', 'Connection error. Please try again.');
        }

        isLoading = false;
    }

    async function executeAction(action, data) {
        const Cart = window.Cart;
        if (!Cart) return { success: false, message: 'Cart unavailable' };

        const user = await Cart.getCurrentUser();
        if (!user) return { success: false, requiresAuth: true, message: 'Please login first.' };

        const type = action.type;

        if (type === 'add_to_cart') {
            let toAdd = [];
            const qty = action.quantity || 1;

            // AI can specify product_id directly
            if (action.product_id) {
                const p = context.lastShownProducts.find(p => p.id === action.product_id);
                if (p) toAdd = [p];
            } else if (action.all) {
                toAdd = context.lastShownProducts;
            } else if (action.product_index !== undefined) {
                const p = context.lastShownProducts[action.product_index - 1];
                if (p) toAdd = [p];
            } else if (action.productIndex !== undefined) {
                const p = context.lastShownProducts[action.productIndex - 1];
                if (p) toAdd = [p];
            } else if (action.productIds) {
                toAdd = context.lastShownProducts.filter(p => action.productIds.includes(p.id));
            } else if (context.lastShownProducts.length > 0) {
                toAdd = context.lastShownProducts.slice(0, 1);
            }

            if (toAdd.length === 0) {
                return { success: false, message: 'Which product would you like to add?' };
            }

            let added = 0, total = 0;
            for (const p of toAdd) {
                const r = await Cart.addToCart(p.id, qty);
                if (r.success) { added++; total += (p.price || 0) * qty; }
            }

            return {
                success: true,
                message: `✅ Added ${added} item(s) to cart${qty > 1 ? ` (${qty}x each)` : ''} - Total: ₦${total.toLocaleString()}`
            };
        }

        if (type === 'remove_from_cart') {
            if (action.product_id) {
                // Remove specific product
                const result = await Cart.removeFromCart(action.product_id);
                if (result.success) {
                    return { success: true, message: '✅ Item removed from cart!' };
                }
                return { success: false, message: 'Could not remove item.' };
            }
            return { success: false, message: 'Which item would you like to remove?' };
        }

        if (type === 'view_cart') {
            console.log('[Eesha AI] view_cart action - fetching items...');
            const items = await Cart.getCartItems();
            console.log('[Eesha AI] view_cart items:', items?.length || 0, items);
            
            if (!items || !items.length) {
                // Check if user is logged in first
                const user = await Cart.getCurrentUser();
                console.log('[Eesha AI] view_cart - user check:', user ? user.id : 'not logged in');
                if (!user) {
                    return { success: false, requiresAuth: true, message: 'Please login to view your cart.' };
                }
                return { success: true, message: 'Your cart is empty. Would you like to browse some products?' };
            }
            
            let cartDetails = '🛒 Your Cart:\n';
            let total = 0;
            items.forEach((item, i) => {
                const name = item.products?.name || 'Unknown';
                const price = item.products?.price || 0;
                const qty = item.quantity || 1;
                const subtotal = price * qty;
                total += subtotal;
                cartDetails += `${i+1}. ${name} x${qty} - ₦${subtotal.toLocaleString()}\n`;
            });
            cartDetails += `\nTotal: ₦${total.toLocaleString()}`;
            
            return { success: true, message: cartDetails };
        }

        if (type === 'checkout') {
            window.location.href = '/Eesha buying folder/checkout.html';
            return { success: true, message: 'Redirecting to checkout...' };
        }

        return null;
    }

    async function clearConversation() {
        conversationHistory = [];
        context.lastShownProducts = [];
        document.getElementById('ai-messages').innerHTML = '';
        document.getElementById('ai-quick-actions').style.display = 'block';
        showWelcomeMessage();
    }

    window.EeshaAI = {
        open: toggleWidget,
        close: () => { if (isOpen) toggleWidget(); },
        clearHistory: clearConversation
    };
})();
