// Sample product data (will be replaced with actual data from backend)
const sampleProducts = [
    {
        id: 1,
        name: "Wireless Headphones",
        price: 59.99,
        image: "path/to/headphones.jpg",
        category: "Electronics"
    },
    // More products will be added
];

// Hero slider functionality
function initializeHeroSlider() {
    const heroSlider = document.querySelector('.hero-slider');
    // Add slider implementation here
}

// Product display functionality
function displayProducts(products) {
    const productGrid = document.getElementById('featuredProducts');
    productGrid.innerHTML = '';

    products.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'product-card';
        productCard.innerHTML = `
            <img src="${product.image}" alt="${product.name}">
            <h3>${product.name}</h3>
            <p class="price">$${product.price}</p>
            <button onclick="viewProduct(${product.id})" class="view-btn">View Details</button>
        `;
        productGrid.appendChild(productCard);
    });
}

// Product view functionality
function viewProduct(productId) {
    // Check if user is logged in
    const isLoggedIn = checkLoginStatus();
    if (!isLoggedIn) {
        window.location.href = 'Eesha buying folder/login.html';
        return;
    }
    // If logged in, show product details
    // Implementation will be added
}

// Login status check
function checkLoginStatus() {
    // This will be implemented with actual session management
    return false;
}

// AI Shopping Assistant - DOM elements are queried after DOMContentLoaded

// Add message to chat
function addMessageToChat(sender, message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Simulate AI response (will be replaced with actual AI implementation)
function simulateAIResponse(userMessage) {
    setTimeout(() => {
        const response = "I can help you find products based on your preferences. Could you tell me more about what you're looking for?";
        addMessageToChat('ai', response);
    }, 1000);
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    initializeHeroSlider();
    displayProducts(sampleProducts);

    // Initialize AI chat elements safely (guard against missing elements)
    const aiChatModal = document.getElementById('ai-chat-modal');
    const openAIChatBtn = document.getElementById('openAIChat');
    const closeModal = document.querySelector('.close-modal');
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendMessageBtn = document.getElementById('sendMessage');

    if (openAIChatBtn && aiChatModal) {
        openAIChatBtn.addEventListener('click', () => {
            aiChatModal.style.display = 'block';
        });
    }

    if (closeModal && aiChatModal) {
        closeModal.addEventListener('click', () => {
            aiChatModal.style.display = 'none';
        });
    }

    // Close modal when clicking outside (guarded)
    if (aiChatModal) {
        window.addEventListener('click', (event) => {
            if (event.target === aiChatModal) aiChatModal.style.display = 'none';
        });
    }

    // Send message in AI chat (guarded)
    if (sendMessageBtn && userInput && chatMessages) {
        sendMessageBtn.addEventListener('click', () => {
            const message = userInput.value.trim();
            if (message) {
                addMessageToChat('user', message);
                simulateAIResponse(message);
                userInput.value = '';
            }
        });
    }
});