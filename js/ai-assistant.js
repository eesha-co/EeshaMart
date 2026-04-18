// AI Shopping Assistant
class AIShoppingAssistant {
    constructor() {
        this.assistantWindow = null;
        this.createAssistantWindow();
        this.bindEvents();
    }

    createAssistantWindow() {
        // Create modal HTML
        const modalHTML = `
            <div id="ai-assistant-modal" class="ai-modal">
                <div class="ai-modal-content">
                    <div class="ai-modal-header">
                        <h3><i class="fas fa-robot"></i> Shopping Assistant</h3>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="ai-chat-container">
                        <div class="ai-messages" id="aiMessages">
                            <div class="ai-message">
                                Hello! I'm your shopping assistant. Tell me what you're looking for, and I'll help you find the perfect product.
                            </div>
                        </div>
                        <div class="ai-input">
                            <input type="text" id="userInput" placeholder="Describe what you're looking for...">
                            <button id="sendMessage"><i class="fas fa-paper-plane"></i></button>
                        </div>
                    </div>
                </div>
            </div>`;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.assistantWindow = document.getElementById('ai-assistant-modal');

        // Add styles
        const styles = `
            .ai-modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                z-index: 1001;
            }

            .ai-modal-content {
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                width: 350px;
                height: 500px;
                background-color: white;
                border-radius: 12px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                display: flex;
                flex-direction: column;
            }

            .ai-modal-header {
                padding: 1rem;
                background-color: #f0474a;
                color: white;
                border-radius: 12px 12px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .ai-modal-header h3 {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin: 0;
                font-size: 1.1rem;
            }

            .close-modal {
                background: none;
                border: none;
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
                padding: 0;
            }

            .ai-chat-container {
                flex: 1;
                display: flex;
                flex-direction: column;
                padding: 1rem;
            }

            .ai-messages {
                flex: 1;
                overflow-y: auto;
                padding: 1rem;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }

            .ai-message, .user-message {
                max-width: 80%;
                padding: 0.8rem;
                border-radius: 12px;
                font-size: 0.9rem;
            }

            .ai-message {
                background-color: #f0f2f5;
                align-self: flex-start;
                border-bottom-left-radius: 4px;
            }

            .user-message {
                background-color: #f0474a;
                color: white;
                align-self: flex-end;
                border-bottom-right-radius: 4px;
            }

            .ai-input {
                display: flex;
                gap: 0.5rem;
                padding: 1rem;
                background-color: white;
                border-top: 1px solid #eee;
            }

            .ai-input input {
                flex: 1;
                padding: 0.8rem;
                border: 1px solid #ddd;
                border-radius: 20px;
                font-size: 0.9rem;
            }

            .ai-input button {
                background-color: #f0474a;
                color: white;
                border: none;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.3s;
            }

            .ai-input button:hover {
                background-color: #d63d40;
            }

            .product-suggestion {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 0.8rem;
                margin-top: 0.5rem;
                cursor: pointer;
                transition: transform 0.2s;
            }

            .product-suggestion:hover {
                transform: translateY(-2px);
            }
        `;

        const styleSheet = document.createElement('style');
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }

    bindEvents() {
        // Open assistant
        document.querySelector('.ai-button').addEventListener('click', () => this.open());

        // Close assistant
        document.querySelector('.close-modal').addEventListener('click', () => this.close());

        // Send message
        document.getElementById('sendMessage').addEventListener('click', () => this.sendMessage());
        document.getElementById('userInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }

    open() {
        this.assistantWindow.style.display = 'block';
        document.getElementById('userInput').focus();
    }

    close() {
        this.assistantWindow.style.display = 'none';
    }

    sendMessage() {
        const input = document.getElementById('userInput');
        const message = input.value.trim();
        
        if (message) {
            this.addMessage(message, 'user');
            input.value = '';
            
            // Process the message and generate a response
            this.processUserInput(message);
        }
    }

    addMessage(message, sender) {
        const messagesContainer = document.getElementById('aiMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = sender === 'user' ? 'user-message' : 'ai-message';
        messageDiv.textContent = message;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async processUserInput(message) {
        // Simulate AI processing
        const keywords = this.extractKeywords(message);
        const suggestions = this.findRelevantProducts(keywords);
        
        // Simulate typing delay
        await this.delay(1000);
        
        // Generate and display response
        const response = this.generateResponse(message, suggestions);
        this.addMessage(response, 'ai');
        
        // Display product suggestions if any
        if (suggestions.length > 0) {
            await this.delay(500);
            this.displayProductSuggestions(suggestions);
        }
    }

    extractKeywords(message) {
        // Simple keyword extraction (can be enhanced with NLP)
        return message.toLowerCase()
            .replace(/[^\w\s]/g, '')
            .split(' ')
            .filter(word => word.length > 2);
    }

    findRelevantProducts(keywords) {
        // This should be replaced with actual product filtering logic
        return products.filter(product => 
            keywords.some(keyword => 
                product.name.toLowerCase().includes(keyword) ||
                product.description.toLowerCase().includes(keyword) ||
                product.category.toLowerCase().includes(keyword)
            )
        );
    }

    generateResponse(message, suggestions) {
        if (suggestions.length === 0) {
            return "I couldn't find any products matching your description. Could you please provide more details about what you're looking for?";
        }

        return `I found ${suggestions.length} products that might interest you. Here are some suggestions:`;
    }

    displayProductSuggestions(suggestions) {
        const messagesContainer = document.getElementById('aiMessages');
        
        suggestions.forEach(product => {
            const suggestionDiv = document.createElement('div');
            suggestionDiv.className = 'product-suggestion';
            suggestionDiv.innerHTML = `
                <strong>${product.name}</strong>
                <p>${product.description}</p>
                <p class="price">$${product.price}</p>
            `;
            
            suggestionDiv.addEventListener('click', () => {
                // Navigate to product details or add to cart
                this.addMessage(`Would you like to add ${product.name} to your cart?`, 'ai');
            });
            
            messagesContainer.appendChild(suggestionDiv);
        });
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize AI Shopping Assistant when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.aiAssistant = new AIShoppingAssistant();
});