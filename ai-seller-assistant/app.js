/**
 * Eeshamart Seller Assistant - Frontend Application
 * Connects to Qwen LLM + VLM backend for text and image processing
 */

// Configuration
const API_PORT = 5005;
const SESSION_ID = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// State
let isLoading = false;
let selectedImages = [];
let imagePreviews = [];
let serviceOnline = false;

// Quick action prompts
const quickActions = {
    branding: "I need help creating a strong brand identity for my products on Eeshamart. Can you guide me?",
    packaging: "What's the best packaging approach for my products? I want something affordable but professional.",
    pricing: "How should I price my products on Eeshamart to be competitive while still making profit?",
    listing: "Help me create better product listings on Eeshamart. What should I include in my descriptions?",
    growth: "What strategies can I use to increase my sales and grow my business on Eeshamart?"
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkServiceStatus();
    setupEventListeners();
    showWelcomeMessage();
});

// Event Listeners
function setupEventListeners() {
    // File input
    document.getElementById('file-input').addEventListener('change', handleFileSelect);
    
    // Message input
    const input = document.getElementById('message-input');
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// Check if backend service is online
async function checkServiceStatus() {
    try {
        const response = await fetch(`/api/info?XTransformPort=${API_PORT}`, {
            headers: { 'X-Session-ID': SESSION_ID }
        });
        const data = await response.json();
        
        if (data.status === 'online') {
            serviceOnline = true;
            document.getElementById('status-badge').classList.remove('offline');
            document.querySelector('.status-text').textContent = 'Online';
            document.getElementById('model-name').textContent = data.model || 'Qwen + VLM';
            document.getElementById('model-badge').textContent = data.model || 'Qwen + VLM';
        }
    } catch (e) {
        console.log('Service not available:', e);
        serviceOnline = false;
        document.getElementById('status-badge').classList.add('offline');
        document.querySelector('.status-text').textContent = 'Offline';
    }
}

// Show welcome message
function showWelcomeMessage() {
    const welcomeContent = `# Welcome to Eeshamart Seller Assistant! 🛍️

I'm your AI-powered business advisor, here to help you succeed on **Eeshamart**.

## How I Can Help You:

• **Branding Advice** - Build a strong brand identity
• **Packaging Guidance** - Professional, affordable packaging
• **Pricing Strategy** - Competitive pricing that profits
• **Product Listing Optimization** - Better descriptions and visibility
• **Business Growth Tips** - Scale your business
• **Product Image Analysis** - Upload photos for insights

## 📸 Upload Product Photos

You can upload photos of your products for:
- Product identification & description
- Pricing recommendations
- Packaging suggestions
- Quality assessment

*What would you like help with today?*`;
    
    addMessage('assistant', welcomeContent);
}

// Handle file selection
function handleFileSelect(e) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    Array.from(files).forEach(file => {
        if (!file.type.startsWith('image/')) return;
        
        const reader = new FileReader();
        reader.onload = (event) => {
            const base64 = event.target.result;
            selectedImages.push(base64);
            
            // Create preview
            const preview = URL.createObjectURL(file);
            imagePreviews.push(preview);
            
            updateImagePreviews();
        };
        reader.readAsDataURL(file);
    });
    
    // Reset input
    e.target.value = '';
}

// Update image previews UI
function updateImagePreviews() {
    const container = document.getElementById('image-previews');
    const grid = document.getElementById('previews-grid');
    const count = document.getElementById('image-count');
    
    if (selectedImages.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    count.textContent = selectedImages.length;
    
    grid.innerHTML = imagePreviews.map((preview, index) => `
        <div class="preview-item">
            <img src="${preview}" alt="Preview ${index + 1}">
            <button class="preview-remove" onclick="removeImage(${index})">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
}

// Remove image
function removeImage(index) {
    selectedImages.splice(index, 1);
    URL.revokeObjectURL(imagePreviews[index]);
    imagePreviews.splice(index, 1);
    updateImagePreviews();
}

// Send quick action
function sendQuickAction(action) {
    const prompt = quickActions[action];
    if (prompt) {
        document.getElementById('message-input').value = prompt;
        sendMessage();
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    
    if ((!text && selectedImages.length === 0) || isLoading) return;
    
    // Add user message with images
    addMessage('user', text || 'Please analyze this product image', selectedImages.length > 0 ? [...imagePreviews] : null);
    
    // Clear input and images
    input.value = '';
    const imagesToSend = [...selectedImages];
    selectedImages.forEach((_, i) => URL.revokeObjectURL(imagePreviews[i]));
    selectedImages = [];
    imagePreviews = [];
    updateImagePreviews();
    
    // Show loading
    isLoading = true;
    showLoading();
    
    try {
        const response = await fetch(`/api/chat?XTransformPort=${API_PORT}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify({
                message: text || 'Please analyze this product image',
                images: imagesToSend
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.success) {
            addMessage('assistant', data.response);
        } else {
            addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
        }
    } catch (e) {
        hideLoading();
        addMessage('assistant', 'I\'m having trouble connecting right now. Please make sure the AI service is running.');
        console.error('Send message error:', e);
    }
    
    isLoading = false;
}

// Add message to chat
function addMessage(role, content, images = null) {
    const container = document.getElementById('messages-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatarIcon = role === 'assistant' 
        ? '<i class="fas fa-store"></i>' 
        : '<i class="fas fa-user"></i>';
    
    let imagesHtml = '';
    if (images && images.length > 0) {
        imagesHtml = `<div class="message-images">
            ${images.map(img => `<img src="${img}" alt="Attached image">`).join('')}
        </div>`;
    }
    
    // Parse markdown for assistant messages
    const displayContent = role === 'assistant' ? parseMarkdown(content) : escapeHtml(content);
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarIcon}</div>
        <div class="message-content">
            ${imagesHtml}
            <div class="message-bubble">${displayContent}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
    
    // Hide quick actions after first user message
    if (role === 'user') {
        const quickActions = document.getElementById('quick-actions');
        if (container.children.length > 2) {
            quickActions.style.display = 'none';
        }
    }
}

// Show loading indicator
function showLoading() {
    const container = document.getElementById('messages-container');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.id = 'loading-message';
    loadingDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-store"></i></div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    container.appendChild(loadingDiv);
    scrollToBottom();
}

// Hide loading indicator
function hideLoading() {
    const loading = document.getElementById('loading-message');
    if (loading) loading.remove();
}

// Clear conversation
async function clearConversation() {
    try {
        await fetch(`/api/clear?XTransformPort=${API_PORT}`, {
            method: 'POST',
            headers: { 'X-Session-ID': SESSION_ID }
        });
    } catch (e) {}
    
    document.getElementById('messages-container').innerHTML = '';
    document.getElementById('quick-actions').style.display = 'block';
    showWelcomeMessage();
}

// Scroll to bottom of messages
function scrollToBottom() {
    const container = document.getElementById('messages-container');
    container.scrollTop = container.scrollHeight;
}

// Simple markdown parser
function parseMarkdown(text) {
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    
    // Fallback simple parser
    return text
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^• (.*$)/gm, '<li>$1</li>')
        .replace(/^- (.*$)/gm, '<li>$1</li>')
        .replace(/\n/g, '<br>');
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
