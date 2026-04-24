/**
 * EeshaMart AI Buyer Assistant - "Eesha"
 * FREE & OPEN SOURCE - No API keys required!
 * 
 * Supports TWO modes:
 * 1. Widget mode (index.html) — creates floating chat widget
 * 2. Full-page mode (ai-chat.html) — attaches to existing page UI
 * 
 * The AI backend handles natural language understanding
 * Frontend just sends context and executes actions
 */

(function() {
    'use strict';

    const CONFIG = {
        apiUrl: 'https://fuhaddesmond-eeshamart-ai.hf.space/api/chat',
        sessionKey: 'eeshamart_ai_session',
        debug: true
    };

    // Detect full-page mode: ai-chat.html has #chatContainer
    const isFullPage = !!document.getElementById('chatContainer');

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
        if (isFullPage) {
            initFullPage();
        } else {
            setTimeout(createWidget, 500);
        }
    }

    // ============================================
    // FULL-PAGE MODE (ai-chat.html)
    // ============================================

    function initFullPage() {
        console.log('[Eesha AI] Full-page mode activated');

        // Wire suggestion chips to sendMessage
        document.querySelectorAll('.chip[data-query], .chip[onclick]').forEach(btn => {
            // Chips already have onclick="sendSuggestion('...')" in HTML
        });

        // Wire image upload button
        const fileInput = document.getElementById('ai-file-input');
        if (fileInput) {
            fileInput.addEventListener('change', handleFileSelect);
        }

        // Wire image remove button
        const removeBtn = document.getElementById('ai-remove-image');
        if (removeBtn) {
            removeBtn.addEventListener('click', removeSelectedImage);
        }

        // Make sendMessage available globally (needed by onclick/onkeypress in HTML)
        window.sendMessage = sendMessage;

        // Make sendSuggestion available globally
        window.sendSuggestion = function(text) {
            document.getElementById('chatInput').value = text;
            sendMessage();
        };

        // Make clearChat available globally
        window.clearChat = clearConversation;
    }

    function fullPage_addMessage(role, content, data = {}) {
        const chatContainer = document.getElementById('chatContainer');
        if (!chatContainer) return;
        const now = new Date();
        const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const isUser = role === 'user';
        const parsed = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        // Build image HTML if provided
        let imageHtml = '';
        if (data.image) {
            imageHtml = `<div style="margin-bottom:8px"><img src="${data.image}" alt="Shared image" style="max-width:200px;max-height:150px;border-radius:8px;object-fit:cover;box-shadow:0 2px 8px rgba(0,0,0,.1)"></div>`;
        }

        if (isUser) {
            const div = document.createElement('div');
            div.className = 'flex justify-end mb-3';
            div.innerHTML = `
                <div class="message-bubble bg-gradient-to-br from-orange-400 to-orange-500 rounded-2xl rounded-tr-md p-3.5 shadow-sm max-w-[80%]">
                    ${imageHtml}
                    <p class="text-sm text-white leading-relaxed">${parsed}</p>
                    <p class="text-[10px] text-orange-100 mt-1.5 text-right">${time}</p>
                </div>`;
            chatContainer.appendChild(div);
        } else {
            const div = document.createElement('div');
            div.className = 'flex items-start gap-2.5 mb-3';
            div.innerHTML = `
                <div class="w-8 h-8 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm">
                    <i class="fas fa-robot text-white text-xs"></i>
                </div>
                <div class="message-bubble bg-white rounded-2xl rounded-tl-md p-3.5 shadow-sm border border-gray-100 max-w-[80%]">
                    ${imageHtml}
                    <div class="text-sm text-gray-700 leading-relaxed">${parsed}</div>
                    ${renderProductsFullPage(data.products)}
                    ${renderActionResultFullPage(data.actionResult)}
                    <p class="text-[10px] text-gray-400 mt-1.5">${time}</p>
                </div>`;
            chatContainer.appendChild(div);
        }

        fullPageScrollToBottom();
        addProductHandlers();

        // Hide suggestion chips after first interaction
        if (conversationHistory.length > 0 || role === 'user') {
            const chips = document.getElementById('suggestionChips');
            if (chips) chips.style.display = 'none';
        }
    }

    function renderProductsFullPage(products) {
        if (!products || products.length === 0) return '';
        let html = '<div class="mt-2 space-y-2">';
        products.slice(0, 5).forEach((p, i) => {
            const name = p.name || 'Product';
            const price = (p.price || 0).toLocaleString();
            const image = p.image_url || 'https://via.placeholder.com/50';
            html += `
                <div class="ai-product-card flex items-center gap-2.5 p-2 bg-gray-50 rounded-lg cursor-pointer border border-transparent hover:border-orange-300 transition-all" data-product-id="${p.id}" data-index="${i + 1}">
                    <img src="${image}" alt="${name}" class="w-12 h-12 rounded-lg object-cover flex-shrink-0" onerror="this.src='https://via.placeholder.com/50'">
                    <div class="flex-1 min-w-0">
                        <div class="text-xs font-semibold text-gray-800 truncate">${i + 1}. ${name}</div>
                        <div class="text-sm font-bold text-orange-600">₦${price}</div>
                        <div class="text-[10px] text-gray-400">${p.category || ''}</div>
                    </div>
                    <div class="flex gap-1.5 flex-shrink-0">
                        <button class="ai-action-btn px-2.5 py-1 rounded-md text-[10px] font-semibold bg-gradient-to-r from-orange-400 to-orange-500 text-gray-900 hover:scale-105 transition-transform" data-action="add" data-product-id="${p.id}"><i class="fas fa-cart-plus"></i> Add</button>
                        <button class="ai-action-btn px-2.5 py-1 rounded-md text-[10px] font-semibold bg-gray-100 text-gray-600 hover:scale-105 transition-transform" data-action="view" data-product-id="${p.id}"><i class="fas fa-eye"></i> View</button>
                    </div>
                </div>`;
        });
        html += '</div>';
        return html;
    }

    function renderActionResultFullPage(result) {
        if (!result) return '';
        const isSuccess = result.success;
        const isWarning = result.requiresAuth;
        let bgClass, textColor, iconClass;
        if (isSuccess) {
            bgClass = 'bg-green-50 border-green-200';
            textColor = 'text-green-700';
            iconClass = 'fa-check-circle text-green-500';
        } else if (isWarning) {
            bgClass = 'bg-yellow-50 border-yellow-200';
            textColor = 'text-yellow-700';
            iconClass = 'fa-exclamation-triangle text-yellow-500';
        } else {
            bgClass = 'bg-red-50 border-red-200';
            textColor = 'text-red-700';
            iconClass = 'fa-times-circle text-red-500';
        }
        return `<div class="flex items-center gap-2 p-2.5 rounded-lg mt-2 text-xs ${bgClass} border ${textColor}"><i class="fas ${iconClass}"></i> <span>${result.message}</span></div>`;
    }

    function fullPage_showTypingIndicator() {
        const chatContainer = document.getElementById('chatContainer');
        if (!chatContainer) return;
        const div = document.createElement('div');
        div.id = 'typingIndicator';
        div.className = 'flex items-start gap-2.5 mb-3';
        div.innerHTML = `
            <div class="w-8 h-8 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm">
                <i class="fas fa-robot text-white text-xs"></i>
            </div>
            <div class="bg-white rounded-2xl rounded-tl-md p-3.5 shadow-sm border border-gray-100">
                <div class="flex items-center gap-1 py-1">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>`;
        chatContainer.appendChild(div);
        fullPageScrollToBottom();
    }

    function fullPage_removeTypingIndicator() {
        document.getElementById('typingIndicator')?.remove();
    }

    function fullPage_updateTypingText(text) {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            const bubble = indicator.querySelector('.bg-white');
            if (bubble) {
                bubble.innerHTML = `<p class="text-sm text-orange-500">${text}</p>`;
            }
        }
    }

    function fullPageScrollToBottom() {
        const chatContainer = document.getElementById('chatContainer');
        if (chatContainer) {
            requestAnimationFrame(() => {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            });
        }
    }

    // ============================================
    // WIDGET MODE (index.html) — original code
    // ============================================

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
        if (isFullPage) return; // Welcome already in HTML
        addMessage('assistant', `<strong>Hi! I'm Eesha, your AI shopping assistant!</strong><br><br>
I can help you with:<br>
- Finding products within your budget<br>
- Planning your shopping list<br>
- Answering any questions<br><br>
Just talk to me naturally!<br>
<strong>100% FREE & Open Source!</strong>`);
    }

    function addMessage(role, content, data = {}) {
        if (isFullPage) {
            fullPage_addMessage(role, content, data);
            return;
        }

        const messagesContainer = document.getElementById('ai-messages');
        const isUser = role === 'user';
        const parsed = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
        
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
                    ${renderProductsWidget(data.products)}
                    ${renderActionResultWidget(data.actionResult)}
                </div>
            </div>`;
        
        messagesContainer.insertAdjacentHTML('beforeend', html);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        addProductHandlers();
        
        if (conversationHistory.length > 0 || role === 'user') {
            document.getElementById('ai-quick-actions').style.display = 'none';
        }
    }

    function renderProductsWidget(products) {
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

    function renderActionResultWidget(result) {
        if (!result) return '';
        const cls = result.success ? '' : (result.requiresAuth ? 'warning' : 'error');
        const icon = result.success ? 'fa-check-circle' : (result.requiresAuth ? 'fa-exclamation-triangle' : 'fa-times-circle');
        return `<div class="ai-action-result ${cls}"><i class="fas ${icon}"></i> ${result.message}</div>`;
    }

    function addProductHandlers() {
        const parentEl = isFullPage ? document.getElementById('chatContainer') : document.getElementById('ai-messages');
        if (!parentEl) return;

        parentEl.querySelectorAll('.ai-product-card:not([data-handled])').forEach(card => {
            card.setAttribute('data-handled', 'true');
            card.addEventListener('click', e => {
                if (!e.target.closest('.ai-action-btn')) {
                    window.location.href = `Eesha buying folder/product.html?id=${card.dataset.productId}`;
                }
            });
        });

        parentEl.querySelectorAll('.ai-action-btn:not([data-handled])').forEach(btn => {
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
                            addMessage('assistant', 'Please <a href="Eesha buying folder/login.html" style="color:#f59e0b;font-weight:600;">login</a> to add items.');
                        }
                    }
                } else if (action === 'view') {
                    window.location.href = `Eesha buying folder/product.html?id=${productId}`;
                }
            });
        });
    }

    function addLoading() {
        if (isFullPage) {
            fullPage_showTypingIndicator();
            return;
        }
        const c = document.getElementById('ai-messages');
        c.insertAdjacentHTML('beforeend', `<div class="ai-message" id="ai-loading-msg">
            <div class="ai-avatar ai-avatar-assistant"><i class="fas fa-wand-magic-sparkles"></i></div>
            <div class="ai-bubble ai-bubble-assistant"><div class="ai-loading"><span></span><span></span><span></span></div></div>
        </div>`);
        c.scrollTop = c.scrollHeight;
    }

    function removeLoading() {
        if (isFullPage) {
            fullPage_removeTypingIndicator();
            return;
        }
        document.getElementById('ai-loading-msg')?.remove();
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        console.log('[Eesha AI] File selected:', file?.name, file?.type, file?.size);
        if (!file?.type.startsWith('image/')) return;

        // Compress image to max 512px before sending (phone photos are too large for HF Space)
        const img = new Image();
        img.onload = function() {
            const MAX = 512;
            let w = img.width, h = img.height;
            if (w > MAX || h > MAX) {
                if (w > h) { h = Math.round(h * MAX / w); w = MAX; }
                else { w = Math.round(w * MAX / h); h = MAX; }
            }
            const canvas = document.createElement('canvas');
            canvas.width = w; canvas.height = h;
            canvas.getContext('2d').drawImage(img, 0, 0, w, h);
            selectedImage = canvas.toDataURL('image/jpeg', 0.7);
            console.log('[Eesha AI] Image compressed. Original:', file.size, 'bytes. Base64 length:', selectedImage.length);

            if (isFullPage) {
                const preview = document.getElementById('ai-image-preview');
                if (preview) {
                    document.getElementById('ai-preview-img').src = selectedImage;
                    preview.classList.remove('hidden');
                }
            } else {
                document.getElementById('ai-preview-img').src = selectedImage;
                document.getElementById('ai-image-preview').classList.remove('ai-hidden');
            }
        };
        img.onerror = function() {
            // Fallback: use original file
            const reader = new FileReader();
            reader.onload = ev => {
                selectedImage = ev.target.result;
                if (isFullPage) {
                    const preview = document.getElementById('ai-image-preview');
                    if (preview) {
                        document.getElementById('ai-preview-img').src = selectedImage;
                        preview.classList.remove('hidden');
                    }
                } else {
                    document.getElementById('ai-preview-img').src = selectedImage;
                    document.getElementById('ai-image-preview').classList.remove('ai-hidden');
                }
            };
            reader.readAsDataURL(file);
        };
        img.src = URL.createObjectURL(file);
        e.target.value = '';
    }

    function removeSelectedImage() {
        selectedImage = null;
        if (isFullPage) {
            const preview = document.getElementById('ai-image-preview');
            if (preview) preview.classList.add('hidden');
        } else {
            document.getElementById('ai-image-preview').classList.add('ai-hidden');
        }
    }

    function handleKeyPress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }

    // ============================================
    // SHARED LOGIC — used by BOTH modes
    // ============================================

    async function updateContext() {
        try {
            console.log('[Eesha AI] Checking login status...');
            console.log('[Eesha AI] window.Cart exists:', !!window.Cart);
            console.log('[Eesha AI] window.supabase exists:', !!window.supabase);
            
            if (!window.Cart) {
                console.error('[Eesha AI] Cart module not loaded!');
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
            } else {
                context.cartItems = [];
                console.log('[Eesha AI] No user logged in - cart empty');
                
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
        const input = isFullPage ? document.getElementById('chatInput') : document.getElementById('ai-input');
        const text = input.value.trim();
        if ((!text && !selectedImage) || isLoading) return;

        // DEBUG COMMAND
        if (text && (text.toLowerCase() === 'debug' || text.toLowerCase() === '/debug')) {
            addMessage('user', text);
            input.value = '';
            
            let debugInfo = '**DEBUG INFO:**\n\n';
            debugInfo += `window.Cart: ${window.Cart ? 'Loaded' : 'NOT LOADED'}\n`;
            debugInfo += `window.supabase: ${window.supabase ? 'Loaded' : 'NOT LOADED'}\n`;
            
            if (window.Cart) {
                try {
                    const user = await window.Cart.getCurrentUser();
                    debugInfo += `\n**Login Status:**\n`;
                    debugInfo += `Logged in: ${user ? 'YES' : 'NO'}\n`;
                    if (user) debugInfo += `User ID: ${user.id}\n`;
                    
                    const items = await window.Cart.getCartItems();
                    debugInfo += `\n**Cart Data:**\n`;
                    debugInfo += `Items count: ${items ? items.length : 0}\n`;
                    if (items && items.length > 0) {
                        debugInfo += `Items:\n`;
                        items.forEach((item, i) => {
                            debugInfo += `  ${i+1}. ${item.products?.name || 'Unknown'} x${item.quantity}\n`;
                        });
                    }
                } catch (e) {
                    debugInfo += `\nError: ${e.message}\n`;
                }
            }
            
            const client = window.supabaseClient || window.supabase;
            if (client) {
                try {
                    const { data: { session } } = await client.auth.getSession();
                    debugInfo += `\n**Supabase Session:** ${session ? 'YES' : 'NO'}\n`;
                    if (session) debugInfo += `User ID: ${session.user?.id}\n`;
                } catch (e) {
                    debugInfo += `\nSupabase error: ${e.message}\n`;
                }
            }
            
            addMessage('assistant', debugInfo);
            return;
        }

        const imageToSend = selectedImage;
        const displayText = text || 'Shared an image';
        console.log('[Eesha AI] sendMessage called. Has image:', !!imageToSend, 'Text:', displayText);
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
                conversationHistory: conversationHistory.slice(-10)
            };

            if (imageToSend) {
                contextForAI.image = imageToSend;
                console.log('[Eesha AI] Image included in request. Base64 length:', imageToSend.length);
            }

            // Update typing status after 10s
            let statusTimer;
            if (isFullPage) {
                statusTimer = setTimeout(() => {
                    fullPage_updateTypingText('Thinking hard, please wait...');
                }, 10000);
            }

            // Build message text — tell AI this is a product they should search for
            const messageForAI = imageToSend
                ? `[User sent a product image] ${text || 'Find me this product or similar ones'}`
                : text;

            // Call HuggingFace Space AI (180s timeout for free tier)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 180000);

            const response = await fetch(CONFIG.apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageForAI, context: contextForAI }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (statusTimer) clearTimeout(statusTimer);

            const data = await response.json();
            if (CONFIG.debug) console.log('[Eesha AI] Response:', data);

            removeLoading();

            if (data.success) {
                conversationHistory.push({ role: 'user', content: text });
                conversationHistory.push({ role: 'assistant', content: data.response });
                
                if (conversationHistory.length > 20) {
                    conversationHistory = conversationHistory.slice(-20);
                }

                if (data.products?.length > 0) {
                    context.lastShownProducts = data.products;
                }

                let actionResult = null;
                let actionProducts = null;
                if (data.action) {
                    actionResult = await executeAction(data.action, data);
                    // If the action returned products (e.g. view_cart), include them for rendering
                    if (actionResult?.products?.length > 0) {
                        actionProducts = actionResult.products;
                    }
                }

                // Merge products from API response and action results
                const allProducts = data.products?.length > 0 ? data.products : actionProducts;

                // Show image debug info so user can see on phone (no laptop needed)
                let debugTag = '';
                if (imageToSend) {
                    const imgDesc = data.image_description || 'not processed';
                    debugTag = `\n\n🖼️ Image sent (${Math.round(imageToSend.length / 1024)}KB) → AI saw: "${imgDesc}"`;
                }
                addMessage('assistant', data.response + debugTag, { products: allProducts, actionResult });
            } else {
                addMessage('assistant', data.response || 'Sorry, an error occurred.');
            }
        } catch (error) {
            console.error('[Eesha AI] Error:', error);
            removeLoading();
            
            let errorMsg = "Connection error. Please try again.";
            if (error.name === 'AbortError') {
                errorMsg = "The AI assistant took too long to respond. The server might be busy — please try again.";
            }
            addMessage('assistant', errorMsg);
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
                message: `Added ${added} item(s) to cart${qty > 1 ? ` (${qty}x each)` : ''} - Total: ₦${total.toLocaleString()}`
            };
        }

        if (type === 'remove_from_cart') {
            if (action.product_id) {
                const result = await Cart.removeFromCart(action.product_id);
                if (result.success) {
                    return { success: true, message: 'Item removed from cart!' };
                }
                return { success: false, message: 'Could not remove item.' };
            }
            return { success: false, message: 'Which item would you like to remove?' };
        }

        if (type === 'view_cart') {
            const items = await Cart.getCartItems();
            
            if (!items || !items.length) {
                const user = await Cart.getCurrentUser();
                if (!user) {
                    return { success: false, requiresAuth: true, message: 'Please login to view your cart.' };
                }
                return { success: true, message: 'Your cart is empty. Would you like to browse some products?' };
            }
            
            let cartDetails = 'Your Cart:\n';
            let total = 0;
            // Build products array with images for rendering
            const cartProducts = items.map((item, i) => {
                const name = item.products?.name || 'Unknown';
                const price = item.products?.price || 0;
                const qty = item.quantity || 1;
                const subtotal = price * qty;
                total += subtotal;
                cartDetails += `${i+1}. ${name} x${qty} - ₦${subtotal.toLocaleString()}\n`;
                return {
                    id: item.product_id || item.products?.id,
                    name: name,
                    price: price,
                    image_url: item.products?.image_url || null,
                    category: item.products?.category || ''
                };
            });
            cartDetails += `\nTotal: ₦${total.toLocaleString()}`;
            
            // Store cart products so they render with images
            context.lastShownProducts = cartProducts;

            return { success: true, message: cartDetails, products: cartProducts };
        }

        if (type === 'checkout') {
            window.location.href = 'Eesha buying folder/checkout.html';
            return { success: true, message: 'Redirecting to checkout...' };
        }

        return null;
    }

    async function clearConversation() {
        conversationHistory = [];
        context.lastShownProducts = [];

        if (isFullPage) {
            const chatContainer = document.getElementById('chatContainer');
            chatContainer.innerHTML = '';

            // Re-add welcome message
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'flex items-start gap-2.5 mb-4 mt-4 animate-fade-in';
            welcomeDiv.innerHTML = `
                <div class="w-8 h-8 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm">
                    <i class="fas fa-robot text-white text-xs"></i>
                </div>
                <div class="message-bubble bg-white rounded-2xl rounded-tl-md p-3.5 shadow-sm border border-gray-100">
                    <p class="text-sm text-gray-700 leading-relaxed">Hi! I'm your <strong class="text-orange-500">EeshaMart AI Assistant</strong>. I can help you find products, compare prices, track deals, and more! What are you looking for today?</p>
                    <p class="text-[10px] text-gray-400 mt-1.5">Just now</p>
                </div>`;
            chatContainer.appendChild(welcomeDiv);

            // Re-add suggestion chips
            const chipsDiv = document.createElement('div');
            chipsDiv.id = 'suggestionChips';
            chipsDiv.className = 'flex flex-wrap gap-2 mb-4 ml-10';
            chipsDiv.innerHTML = `
                <button onclick="sendSuggestion('Show me phones under ₦50,000')" class="chip inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:text-orange-600 shadow-sm">
                    <i class="fas fa-mobile-alt text-orange-400"></i> Phones under ₦50k
                </button>
                <button onclick="sendSuggestion('Best deals today')" class="chip inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:text-orange-600 shadow-sm">
                    <i class="fas fa-bolt text-orange-400"></i> Best deals today
                </button>
                <button onclick="sendSuggestion('Farm fresh produce')" class="chip inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:text-orange-600 shadow-sm">
                    <i class="fas fa-leaf text-orange-400"></i> Farm fresh produce
                </button>
                <button onclick="sendSuggestion('Electronics')" class="chip inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 rounded-full text-xs text-gray-600 hover:text-orange-600 shadow-sm">
                    <i class="fas fa-laptop text-orange-400"></i> Electronics
                </button>`;
            chatContainer.appendChild(chipsDiv);
        } else {
            document.getElementById('ai-messages').innerHTML = '';
            document.getElementById('ai-quick-actions').style.display = 'block';
            showWelcomeMessage();
        }
    }

    // Expose globally
    window.EeshaAI = {
        open: toggleWidget,
        close: () => { if (isOpen) toggleWidget(); },
        clearHistory: clearConversation
    };
    window.sendMessage = sendMessage;
})();
