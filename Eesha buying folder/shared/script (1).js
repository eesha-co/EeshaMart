document.addEventListener('DOMContentLoaded', () => {
    // --- DATABASE SIMULATION (using localStorage) ---
    // Initialize users and products from localStorage or with default values
    const users = JSON.parse(localStorage.getItem('eeshaUsers')) || [];
    const products = JSON.parse(localStorage.getItem('eeshaProducts')) || [
        { id: 1, name: 'Stylish Sneakers', description: 'Comfortable and stylish sneakers for casual wear.', price: 49.99, imageUrl: 'https://via.placeholder.com/200x200.png?text=Fashion+Shoe', seller: 'system' },
        { id: 2, name: 'Smart Watch', description: 'A modern smart watch with health tracking features.', price: 199.99, imageUrl: 'https://via.placeholder.com/200x200.png?text=Gadget', seller: 'system' },
        { id: 3, name: 'Classic Blue T-Shirt', description: 'A 100% cotton blue t-shirt, perfect for summer.', price: 15.00, imageUrl: 'https://via.placeholder.com/200x200.png?text=Blue+T-Shirt', seller: 'system' },
        { id: 4, name: 'Ultra-Slim Laptop', description: 'A powerful and portable laptop for work and play.', price: 799.00, imageUrl: 'https://via.placeholder.com/200x200.png?text=Laptop', seller: 'system' }
    ];
    let currentUser = JSON.parse(sessionStorage.getItem('eeshaCurrentUser'));

    // --- UTILITY FUNCTIONS ---
    const saveUsers = () => localStorage.setItem('eeshaUsers', JSON.stringify(users));
    const saveProducts = () => localStorage.setItem('eeshaProducts', JSON.stringify(products));
    const saveCurrentUser = () => sessionStorage.setItem('eeshaCurrentUser', JSON.stringify(currentUser));

    // --- PAGE-SPECIFIC LOGIC ---
    const page = window.location.pathname.split("/").pop();

    if (page === 'index.html' || page === '') {
        // --- HOMEPAGE LOGIC ---
        const productGrid = document.getElementById('product-grid');
        
        // Display products on homepage
        if (productGrid) {
            productGrid.innerHTML = products.map(p => `
                <div class="product-card" data-product-id="${p.id}">
                    <img src="${p.imageUrl}" alt="${p.name}">
                    <h3>${p.name}</h3>
                    <p class="price">$${p.price.toFixed(2)}</p>
                </div>
            `).join('');

            // Add click listener to prompt login/signup
            document.querySelectorAll('.product-card').forEach(card => {
                card.addEventListener('click', () => {
                    alert('Please log in or sign up to view product details and purchase!');
                    window.location.href = 'auth.html';
                });
            });
        }
    } else if (page === 'auth.html') {
        // --- AUTHENTICATION LOGIC ---
        const loginForm = document.getElementById('login');
        const signupForm = document.getElementById('signup');
        const showSignupBtn = document.getElementById('show-signup');
        const showLoginBtn = document.getElementById('show-login');

        showSignupBtn.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('login-form').style.display = 'none';
            document.getElementById('signup-form').style.display = 'block';
        });

        showLoginBtn.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('signup-form').style.display = 'none';
            document.getElementById('login-form').style.display = 'block';
        });

        signupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('signup-name').value;
            const email = document.getElementById('signup-email').value;
            const password = document.getElementById('signup-password').value;
            const type = document.querySelector('input[name="user_type"]:checked').value;

            if (users.find(u => u.email === email)) {
                alert('User with this email already exists!');
                return;
            }

            const newUser = { id: Date.now(), name, email, password, type };
            users.push(newUser);
            saveUsers();
            alert('Signup successful! Please log in.');
            showLoginBtn.click(); // Switch to login form
        });

        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;

            const user = users.find(u => u.email === email && u.password === password);
            if (user) {
                currentUser = user;
                saveCurrentUser();
                window.location.href = 'dashboard.html';
            } else {
                alert('Invalid email or password.');
            }
        });
    } else if (page === 'dashboard.html') {
        // --- DASHBOARD LOGIC ---
        if (!currentUser) {
            window.location.href = 'auth.html';
            return;
        }

        // --- Common Dashboard Elements ---
        document.getElementById('welcome-msg').textContent = `Welcome, ${currentUser.name}!`;
        document.getElementById('logout-btn').addEventListener('click', () => {
            currentUser = null;
            sessionStorage.removeItem('eeshaCurrentUser');
            window.location.href = 'index.html';
        });
        
        // --- Role-Specific Dashboards ---
        if (currentUser.type === 'seller') {
            displaySellerDashboard();
        } else {
            displayBuyerDashboard();
        }
    }

    function displaySellerDashboard() {
        document.getElementById('seller-dashboard').style.display = 'block';
        const addProductForm = document.getElementById('add-product-form');
        const sellerProductsContainer = document.getElementById('seller-products');

        // Function to render seller's products
        const renderSellerProducts = () => {
            const myProducts = products.filter(p => p.seller === currentUser.email);
            if(myProducts.length === 0) {
                 sellerProductsContainer.innerHTML = "<p>You haven't posted any products yet.</p>";
                 return;
            }
            sellerProductsContainer.innerHTML = myProducts.map(p => `
                <div class="product-card">
                    <img src="${p.imageUrl}" alt="${p.name}">
                    <h3>${p.name}</h3>
                    <p>${p.description.substring(0, 50)}...</p>
                    <p class="price">$${p.price.toFixed(2)}</p>
                </div>
            `).join('');
        };

        // Handle adding a new product
        addProductForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const newProduct = {
                id: Date.now(),
                name: document.getElementById('product-name').value,
                description: document.getElementById('product-desc').value,
                price: parseFloat(document.getElementById('product-price').value),
                imageUrl: document.getElementById('product-image').value,
                seller: currentUser.email
            };
            products.push(newProduct);
            saveProducts();
            addProductForm.reset();
            renderSellerProducts();
        });

        renderSellerProducts();
    }

    function displayBuyerDashboard() {
        document.getElementById('buyer-dashboard').style.display = 'block';
        const buyerProductsContainer = document.getElementById('buyer-products');
        const aiSearchBtn = document.getElementById('ai-search-btn');
        const aiInput = document.getElementById('ai-input');
        const aiResultsContainer = document.getElementById('ai-results');
        
        // Render all available products for the buyer
        const renderAllProducts = (productList = products) => {
             if(productList.length === 0) {
                 buyerProductsContainer.innerHTML = "<p>No products available right now.</p>";
                 return;
            }
            buyerProductsContainer.innerHTML = productList.map(p => `
                <div class="product-card">
                    <img src="${p.imageUrl}" alt="${p.name}">
                    <h3>${p.name}</h3>
                    <p>${p.description.substring(0, 50)}...</p>
                    <p class="price">$${p.price.toFixed(2)}</p>
                    <p><small>Sold by: ${p.seller}</small></p>
                </div>
            `).join('');
        };
        
        // AI Assistant Logic
        aiSearchBtn.addEventListener('click', () => {
            const query = aiInput.value.toLowerCase().trim();
            if (!query) return;

            const keywords = query.split(' ');
            
            const filteredProducts = products.filter(p => {
                const productText = `${p.name.toLowerCase()} ${p.description.toLowerCase()}`;
                // Return true if at least one keyword is found in the product text
                return keywords.some(keyword => productText.includes(keyword));
            });

            if (filteredProducts.length > 0) {
                aiResultsContainer.innerHTML = `<h4>AI Suggestions for "${query}":</h4>`;
                renderAllProducts(filteredProducts); // Re-render the grid with filtered products
            } else {
                aiResultsContainer.innerHTML = `<p>Sorry, I couldn't find any products matching your description. Try being more general.</p>`;
                renderAllProducts(); // Show all products again
            }
        });

        renderAllProducts();
    }
});